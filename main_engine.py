"""PathGuard-AI Main Execution Engine.

Orchestrates the full pipeline: Camera → Vision → H3 → PostGIS → DLP → Notice
Supports both classical CV and GPU-accelerated ML inference.
"""
import cv2
import numpy as np
import logging
import sys
import time
import json
import os
import argparse
from datetime import datetime, date
from pathlib import Path

from pathguard.config import get_config
from pathguard.vision import VisionPipeline, EnhancedVisionPipeline, DEFECT_CLASSES
from pathguard.spatial import H3Engine
from pathguard.contracts import (
    DLPEngine, DLPType, classify_defect, severity_to_score,
    DefectClassification
)
from pathguard.notices import (
    NoticeDispatcher, estimate_repair_cost,
    generate_notice_body, generate_notice_payload, compute_cure_deadline
)
from pathguard.pdf_ingest import TenderParser
from pathguard.gps_relay import GPSReceiver, SimulatedGPS, GPSFix

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger('pathguard')


# ── Severity colour map for OpenCV overlay ───────────────────────────────────
SEVERITY_COLORS_BGR = {
    'LOW':      (0, 200, 0),      # green
    'MEDIUM':   (0, 200, 255),    # yellow-ish
    'HIGH':     (0, 140, 255),    # orange
    'CRITICAL': (0, 0, 255),      # red
}


class PathGuardEngine:
    """Core orchestration engine tying all modules together."""

    def __init__(
        self,
        config=None,
        use_simulated_gps: bool = True,
        camera_source=0,
        tender_dir: str = 'tenders/',
        use_ml: bool = True,
    ):
        self.config = config or get_config()
        self.camera_source = camera_source
        self.tender_dir = Path(tender_dir)
        self.running = False

        logger.info("Initializing PathGuard engine …")

        # ── Vision pipeline (ML-enhanced or classical) ────────────────────
        if use_ml:
            try:
                self.vision = EnhancedVisionPipeline(self.config)
                logger.info("Using EnhancedVisionPipeline (ML + classical fallback)")
            except Exception as exc:
                logger.warning(f"ML pipeline init failed ({exc}), falling back to classical")
                self.vision = VisionPipeline(self.config)
        else:
            self.vision = VisionPipeline(self.config)

        # ── Geospatial ────────────────────────────────────────────────────
        h3_cfg = self.config.get('h3', {})
        self.h3 = H3Engine(
            corridor_res=h3_cfg.get('corridor_resolution', 11),
            defect_res=h3_cfg.get('defect_resolution', 12),
            kring_k=h3_cfg.get('kring_k', 1),
        )

        # ── Contract & Notice ─────────────────────────────────────────────
        dlp_cfg = self.config.get('dlp', {})
        self.dlp = DLPEngine(
            esal_overload_threshold=dlp_cfg.get('esal_overload_threshold', 1.5),
        )
        notice_cfg = self.config.get('notice', {})
        self.notice_dispatcher = NoticeDispatcher(
            smtp_server=notice_cfg.get('smtp_server', 'smtp.gmail.com'),
            smtp_port=notice_cfg.get('smtp_port', 587),
        )

        # ── PDF ingestion ─────────────────────────────────────────────────
        self.tender_parser = TenderParser(tender_dir=str(self.tender_dir))

        # ── GPS ───────────────────────────────────────────────────────────
        if use_simulated_gps:
            self.gps = SimulatedGPS()
        else:
            gps_port = self.config.get('gps', {}).get('port', 5000)
            self.gps = GPSReceiver(port=gps_port)
            self.gps.start()

        # ── Database (deferred) ───────────────────────────────────────────
        self.db = None
        self.db_connected = False

        # ── Runtime state ─────────────────────────────────────────────────
        self.captures_dir = Path('captures')
        self.captures_dir.mkdir(exist_ok=True)

        self.state = {
            'detections': [],
            'total_new': 0,
            'total_merged': 0,
            'tickets_issued': 0,
            'last_gps': None,
            'fps': 0.0,
        }

    # ── Database ──────────────────────────────────────────────────────────
    def connect_database(self) -> bool:
        """Try connecting to PostGIS. Non-fatal on failure (demo mode)."""
        try:
            from pathguard.database import DatabaseEngine
            db_cfg = self.config.get('database', {})
            self.db = DatabaseEngine(
                host=db_cfg.get('host', 'localhost'),
                port=db_cfg.get('port', 5432),
                dbname=db_cfg.get('name', 'pathguard'),
                user=db_cfg.get('user', 'pathguard'),
                password=db_cfg.get('password', 'pathguard_dev'),
            )
            self.db_connected = self.db.connect()
            if self.db_connected:
                logger.info("PostGIS database connected ✓")
            else:
                logger.warning("PostGIS connection returned False — demo mode")
            return self.db_connected
        except Exception as exc:
            logger.warning(f"Database unavailable ({exc}). Running in demo mode.")
            self.db_connected = False
            return False

    # ── Tender ingestion ──────────────────────────────────────────────────
    def ingest_tenders(self) -> list:
        """Parse all PDFs in the tender directory."""
        if not self.tender_dir.exists():
            logger.warning(f"Tender directory {self.tender_dir} does not exist.")
            return []
        contracts = self.tender_parser.ingest_directory()
        logger.info(f"Ingested {len(contracts)} tender contract(s)")
        return contracts

    # ── Per-frame pipeline ────────────────────────────────────────────────
    def process_frame(
        self,
        frame: np.ndarray,
        gps_fix: GPSFix = None,
        imu_data: dict = None,
    ) -> list[dict]:
        """Run full detection → geospatial → DLP → notice pipeline on one frame."""
        fix = gps_fix or self.gps.get_latest()
        if fix is None:
            return []

        self.state['last_gps'] = {'lat': fix.latitude, 'lon': fix.longitude}

        # 1. Vision pipeline
        detections = self.vision.process_frame(frame, imu_data)

        results = []
        for det in detections:
            # 2. H3 spatial index
            cell = self.h3.resolve(fix.latitude, fix.longitude)
            ticket_id = self.h3.generate_ticket_id(cell.res12)

            # 3. Repair cost estimate
            w_cm = det.get('width_cm', det.get('real_width_cm', 0))
            h_cm = det.get('height_cm', det.get('real_height_cm', 0))
            d_cm = det.get('depth_cm', 0)
            volume_m3, cost_inr = estimate_repair_cost(w_cm, h_cm, d_cm)

            result = {
                **det,
                'ticket_id': ticket_id,
                'lat': fix.latitude,
                'lon': fix.longitude,
                'h3_res11': cell.res11,
                'h3_res12': cell.res12,
                'is_pentagon': cell.is_pentagon,
                'volume_m3': round(volume_m3, 6),
                'cost_inr': round(cost_inr, 2),
                'timestamp': datetime.now().isoformat(),
            }

            # 4. Database dedup (if connected)
            if self.db_connected and self.db is not None:
                dedup_radius = 15.0 if cell.is_pentagon else 3.0
                try:
                    existing = self.db.find_nearby_defect(
                        fix.longitude, fix.latitude, dedup_radius
                    )
                    if existing:
                        result['status'] = 'MERGED_EXISTING'
                        result['merged_ticket_id'] = existing['ticket_id']
                        self.state['total_merged'] += 1
                    else:
                        result['status'] = 'CREATED_NEW'
                        self.state['total_new'] += 1
                except Exception as exc:
                    logger.error(f"DB dedup error: {exc}")
                    result['status'] = 'DB_ERROR'
            else:
                result['status'] = 'DEMO_NEW'
                self.state['total_new'] += 1

            # 5. Save best crop
            x, y, bw, bh = det['bbox']
            crop = frame[max(0, y):y + bh, max(0, x):x + bw]
            if crop.size > 0:
                img_name = f"{ticket_id}_{int(time.time())}.jpg"
                img_path = self.captures_dir / img_name
                cv2.imwrite(str(img_path), crop)
                result['image_path'] = str(img_path)

            results.append(result)

        self.state['detections'] = results
        return results

    # ── Draw overlays ─────────────────────────────────────────────────────
    @staticmethod
    def draw_overlays(frame: np.ndarray, detections: list[dict]) -> np.ndarray:
        """Draw bounding boxes, labels, and dimensions on the frame."""
        display = frame.copy()
        for det in detections:
            x, y, w, h = det['bbox']
            sev = det.get('severity', 'MEDIUM')
            color = SEVERITY_COLORS_BGR.get(sev, (0, 255, 0))

            cv2.rectangle(display, (x, y), (x + w, y + h), color, 2)

            # Label line 1: class + confidence
            cls_name = det.get('class_name', 'defect')
            conf = det.get('confidence', 0)
            label1 = f"{cls_name} {conf:.0%}"

            # Label line 2: dimensions
            w_cm = det.get('width_cm', det.get('real_width_cm', 0))
            h_cm = det.get('height_cm', det.get('real_height_cm', 0))
            d_cm = det.get('depth_cm', 0)
            label2 = f"{w_cm:.0f}x{h_cm:.0f}x{d_cm:.1f}cm [{sev}]"

            cv2.putText(display, label1, (x, y - 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
            cv2.putText(display, label2, (x, y - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

        return display

    # ── Camera loop ───────────────────────────────────────────────────────
    def run_camera_loop(self):
        """Main loop: capture → detect → overlay → display (OpenCV window)."""
        cap = cv2.VideoCapture(self.camera_source)
        if not cap.isOpened():
            logger.error(f"Cannot open camera source: {self.camera_source}")
            return

        self.running = True
        logger.info(f"Camera loop started (source={self.camera_source})")

        try:
            while self.running:
                t0 = time.perf_counter()

                ret, frame = cap.read()
                if not ret:
                    logger.warning("Frame grab failed, retrying …")
                    time.sleep(0.1)
                    continue

                results = self.process_frame(frame)
                display = self.draw_overlays(frame, results)

                fps = 1.0 / max(time.perf_counter() - t0, 1e-6)
                self.state['fps'] = round(fps, 1)
                cv2.putText(display, f"FPS: {fps:.1f}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

                cv2.imshow('PathGuard-AI', display)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            self.running = False
            cap.release()
            cv2.destroyAllWindows()

    def run_video_file(self, video_path: str):
        """Process a video file instead of a live camera."""
        self.camera_source = video_path
        self.run_camera_loop()

    def get_dashboard_state(self) -> dict:
        """Return current state dict for the Streamlit dashboard."""
        return self.state


# ── CLI entry point ───────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description='PathGuard-AI Engine')
    parser.add_argument('--camera', type=int, default=0,
                        help='Camera device index')
    parser.add_argument('--video', type=str, default=None,
                        help='Path to video file (overrides --camera)')
    parser.add_argument('--simulated-gps', action='store_true', default=True,
                        help='Use simulated GPS route')
    parser.add_argument('--no-db', action='store_true',
                        help='Skip database connection (demo mode)')
    parser.add_argument('--no-ml', action='store_true',
                        help='Use classical CV only, skip ML models')
    parser.add_argument('--tender-dir', type=str, default='tenders/',
                        help='Directory containing tender PDFs')
    args = parser.parse_args()

    engine = PathGuardEngine(
        use_simulated_gps=args.simulated_gps,
        camera_source=args.video if args.video else args.camera,
        tender_dir=args.tender_dir,
        use_ml=not args.no_ml,
    )

    if not args.no_db:
        engine.connect_database()

    engine.ingest_tenders()

    if args.video:
        engine.run_video_file(args.video)
    else:
        engine.run_camera_loop()


if __name__ == '__main__':
    main()
