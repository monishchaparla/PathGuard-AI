import logging
import math
from typing import Dict, List, Optional, Tuple, Any

import cv2
import numpy as np
from pathlib import Path

DEFECT_CLASSES = {
    0: 'pothole',
    1: 'longitudinal_crack',
    2: 'transverse_crack',
    3: 'alligator_crack',
    4: 'rutting',
    5: 'raveling',
    6: 'patching'
}

try:
    import onnxruntime as ort
except ImportError:
    ort = None

logger = logging.getLogger(__name__)


class LensCalibrator:
    """Calibrates and undistorts camera images based on lens parameters."""

    def __init__(
        self,
        resolution: Tuple[int, int] = (1920, 1080),
        distortion_coeffs: List[float] = [-0.2, 0.1, 0.0, 0.0],
        focal_length_mm: float = 4.0,
        sensor_width_mm: float = 4.8,
        sensor_height_mm: float = 3.6,
    ):
        self.resolution = resolution
        self.distortion_coeffs = np.array(distortion_coeffs, dtype=np.float32)
        self.focal_length_mm = focal_length_mm
        self.sensor_width_mm = sensor_width_mm
        self.sensor_height_mm = sensor_height_mm

        w, h = resolution
        fx = (focal_length_mm / sensor_width_mm) * w
        fy = (focal_length_mm / sensor_height_mm) * h
        cx = w / 2.0
        cy = h / 2.0

        self.K = np.array([
            [fx, 0.0, cx],
            [0.0, fy, cy],
            [0.0, 0.0, 1.0]
        ], dtype=np.float32)

    def undistort(self, frame: np.ndarray) -> np.ndarray:
        """Apply OpenCV undistortion using K and D."""
        if frame is None or frame.size == 0:
            return frame
        return cv2.undistort(frame, self.K, self.distortion_coeffs)


class DefectDetector:
    """Detects road defects using classical CV or ONNX YOLOv8 model."""

    def __init__(
        self,
        min_area: int = 500,
        max_area: int = 50000,
        ar_min: float = 0.5,
        ar_max: float = 2.5,
        onnx_model_path: Optional[str] = None,
    ):
        self.min_area = min_area
        self.max_area = max_area
        self.ar_min = ar_min
        self.ar_max = ar_max

        self.session = None
        if onnx_model_path and ort is not None:
            try:
                self.session = ort.InferenceSession(onnx_model_path)
                logger.info(f"Loaded ONNX model from {onnx_model_path}")
            except Exception as e:
                logger.warning(f"Failed to load ONNX model: {e}")

    def detect_classical(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """Classical detection pipeline using adaptive thresholding."""
        if frame is None or frame.size == 0:
            return []

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # Apply adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 15
        )
        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        detections = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if self.min_area < area < self.max_area:
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = float(w) / h if h > 0 else 0
                if self.ar_min < aspect_ratio < self.ar_max:
                    detections.append({
                        'bbox': (x, y, w, h),
                        'contour': contour,
                        'area': area,
                        'aspect_ratio': aspect_ratio
                    })
        return detections

    def detect_onnx(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """ONNX YOLOv8 inference pipeline."""
        if not self.session or frame is None or frame.size == 0:
            return []
        
        orig_h, orig_w = frame.shape[:2]
        
        # Preprocess: resize to 640x640, normalize to [0,1], transpose to NCHW
        img = cv2.resize(frame, (640, 640))
        img = img.astype(np.float32) / 255.0
        img = img.transpose(2, 0, 1)  # HWC to CHW
        img = np.expand_dims(img, axis=0)  # NCHW
        
        # Run inference
        input_name = self.session.get_inputs()[0].name
        outputs = self.session.run(None, {input_name: img})[0]
        
        # outputs shape: [1, num_classes+4, num_boxes]
        outputs = outputs[0].T  # [num_boxes, num_classes+4]
        
        boxes = []
        scores = []
        for out in outputs:
            cx, cy, w, h = out[0:4]
            # YOLOv8 class scores start from index 4
            class_scores = out[4:]
            max_score = np.max(class_scores)
            
            if max_score > 0.25:
                # Convert back to original image scale
                x1 = int((cx - w/2) / 640.0 * orig_w)
                y1 = int((cy - h/2) / 640.0 * orig_h)
                box_w = int(w / 640.0 * orig_w)
                box_h = int(h / 640.0 * orig_h)
                boxes.append([x1, y1, box_w, box_h])
                scores.append(float(max_score))
                
        # NMS
        indices = cv2.dnn.NMSBoxes(boxes, scores, 0.25, 0.45)
        
        detections = []
        if len(indices) > 0:
            for i in indices.flatten():
                x, y, w, h = boxes[i]
                # Ensure valid bbox
                if w <= 0 or h <= 0:
                    continue
                contour = np.array([
                    [[x, y]], [[x+w, y]], [[x+w, y+h]], [[x, y+h]]
                ], dtype=np.int32)
                area = w * h
                aspect_ratio = float(w) / h
                
                detections.append({
                    'bbox': (x, y, w, h),
                    'contour': contour,
                    'area': area,
                    'aspect_ratio': aspect_ratio,
                    'confidence': scores[i]
                })
        return detections

    def detect(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """Dispatches to ONNX or classical depending on model availability."""
        if self.session is not None:
            return self.detect_onnx(frame)
        return self.detect_classical(frame)


class MonocularGeometry:
    """Computes geometric properties from single camera images."""

    def __init__(
        self,
        focal_length_mm: float = 4.0,
        sensor_height_mm: float = 3.6,
        sensor_width_mm: float = 4.8,
        camera_height_cm: float = 130.0,
        frame_width: int = 1920,
        frame_height: int = 1080,
    ):
        self.focal_length_mm = focal_length_mm
        self.sensor_height_mm = sensor_height_mm
        self.sensor_width_mm = sensor_width_mm
        self.camera_height_cm = camera_height_cm
        self.frame_width = frame_width
        self.frame_height = frame_height

    def compute_distance(self, bbox_height_px: float) -> float:
        """Returns distance to defect D_obj in cm.
        
        Using formula: D_obj = (f * H * frame_height) / (h_pixel * S_h)
        Here H is camera height.
        """
        if bbox_height_px <= 0:
            return 0.0
        d_obj = (self.focal_length_mm * self.camera_height_cm * self.frame_height) / (bbox_height_px * self.sensor_height_mm)
        return float(d_obj)

    def compute_real_width(self, bbox_width_px: float, distance_cm: float) -> float:
        """Returns W_cm: real width of the defect in cm.
        
        W_cm = (w_pixel * D_obj * S_w) / (f * frame_width)
        """
        w_cm = (bbox_width_px * distance_cm * self.sensor_width_mm) / (self.focal_length_mm * self.frame_width)
        return float(w_cm)

    def compute_real_height(self, bbox_height_px: float, distance_cm: float) -> float:
        """Returns H_cm: real length/height of the defect in cm.
        
        H_cm = (h_pixel * D_obj * S_h) / (f * frame_height)
        """
        h_cm = (bbox_height_px * distance_cm * self.sensor_height_mm) / (self.focal_length_mm * self.frame_height)
        return float(h_cm)

    def estimate_depth(self, roi: np.ndarray, depth_min: float = 1.5, depth_max: float = 30.0) -> float:
        """Estimate depth from grayscale intensity drop."""
        if roi is None or roi.size == 0:
            return depth_min
            
        if len(roi.shape) == 3:
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        else:
            gray = roi

        h, w = gray.shape
        if h <= 2 or w <= 2:
            return depth_min

        # Create mask for border
        mask = np.zeros_like(gray, dtype=np.uint8)
        border_thickness = max(1, min(w, h) // 10)
        cv2.rectangle(mask, (0, 0), (w-1, h-1), 255, border_thickness)
        
        border_pixels = gray[mask == 255]
        center_pixels = gray[mask == 0]
        
        border_mean = np.mean(border_pixels) if border_pixels.size > 0 else 0
        center_mean = np.mean(center_pixels) if center_pixels.size > 0 else 0
        
        intensity_drop = border_mean - center_mean
        if intensity_drop < 0:
            intensity_drop = 0
            
        # Map intensity drop [0, 128] linearly to [depth_min, depth_max]
        depth = depth_min + (intensity_drop / 128.0) * (depth_max - depth_min)
        return float(np.clip(depth, depth_min, depth_max))


class IMUFusion:
    """Fuses IMU data with vision to estimate defect severity."""

    def __init__(self, severity_depth_threshold: float = 5.0, severity_imu_threshold: float = 2.5):
        self.severity_depth_threshold = severity_depth_threshold
        self.severity_imu_threshold = severity_imu_threshold

    def classify_severity(self, depth_cm: float, imu_az_g: float) -> str:
        """Returns severity string."""
        depth_critical = depth_cm > self.severity_depth_threshold
        imu_critical = abs(imu_az_g) > self.severity_imu_threshold

        if depth_critical and imu_critical:
            return 'CRITICAL' if depth_cm > 15 else 'HIGH'
        elif depth_critical and not imu_critical:
            return 'MEDIUM'
        elif not depth_critical and imu_critical:
            return 'MEDIUM'
        else:
            return 'LOW'


def compute_q_score(bbox_width_px: float, bbox_height_px: float, frame_roi: np.ndarray, area_weight: float = 0.3, laplacian_weight: float = 0.7) -> float:
    """Computes Q-score representing defect visual saliency and sharpness."""
    if frame_roi is None or frame_roi.size == 0:
        return 0.0
        
    if len(frame_roi.shape) == 3:
        gray_roi = cv2.cvtColor(frame_roi, cv2.COLOR_BGR2GRAY)
    else:
        gray_roi = frame_roi
        
    laplacian_variance = float(cv2.Laplacian(gray_roi, cv2.CV_64F).var())
    q_score = (bbox_width_px * bbox_height_px * area_weight) + (laplacian_variance * laplacian_weight)
    return float(q_score)


class VisionPipeline:
    """End-to-end vision pipeline for PathGuard-AI."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        self.calibrator = LensCalibrator(
            resolution=config.get('resolution', (1920, 1080)),
            distortion_coeffs=config.get('distortion_coeffs', [-0.2, 0.1, 0.0, 0.0]),
            focal_length_mm=config.get('focal_length_mm', 4.0),
            sensor_width_mm=config.get('sensor_width_mm', 4.8),
            sensor_height_mm=config.get('sensor_height_mm', 3.6),
        )
        
        self.detector = DefectDetector(
            min_area=config.get('min_area', 500),
            max_area=config.get('max_area', 50000),
            ar_min=config.get('ar_min', 0.5),
            ar_max=config.get('ar_max', 2.5),
            onnx_model_path=config.get('onnx_model_path', None),
        )
        
        self.geometry = MonocularGeometry(
            focal_length_mm=config.get('focal_length_mm', 4.0),
            sensor_height_mm=config.get('sensor_height_mm', 3.6),
            sensor_width_mm=config.get('sensor_width_mm', 4.8),
            camera_height_cm=config.get('camera_height_cm', 130.0),
            frame_width=config.get('resolution', (1920, 1080))[0],
            frame_height=config.get('resolution', (1920, 1080))[1],
        )
        
        self.fusion = IMUFusion(
            severity_depth_threshold=config.get('severity_depth_threshold', 5.0),
            severity_imu_threshold=config.get('severity_imu_threshold', 2.5),
        )

    def process_frame(self, frame: np.ndarray, imu_data: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
        """Processes a single frame and returns enriched detections."""
        if frame is None or frame.size == 0:
            return []

        # 1. Undistort frame
        undistorted = self.calibrator.undistort(frame)
        
        # 2. Detect defects
        detections = self.detector.detect(undistorted)
        
        imu_az_g = 0.0
        if imu_data and 'az' in imu_data:
            imu_az_g = imu_data['az']
            
        enriched_detections = []
        
        for det in detections:
            x, y, w, h = det['bbox']
            
            # Ensure ROI is within bounds
            img_h, img_w = undistorted.shape[:2]
            roi_x1 = max(0, x)
            roi_y1 = max(0, y)
            roi_x2 = min(img_w, x + w)
            roi_y2 = min(img_h, y + h)
            
            if roi_x2 <= roi_x1 or roi_y2 <= roi_y1:
                continue
                
            roi = undistorted[roi_y1:roi_y2, roi_x1:roi_x2]
            
            # 3. Compute geometry and depth
            distance_cm = self.geometry.compute_distance(h)
            real_width_cm = self.geometry.compute_real_width(w, distance_cm)
            real_height_cm = self.geometry.compute_real_height(h, distance_cm)
            depth_cm = self.geometry.estimate_depth(roi)
            
            # 4. Severity classification
            severity = self.fusion.classify_severity(depth_cm, imu_az_g)
            
            # 5. Q-score
            q_score = compute_q_score(w, h, roi)
            
            enriched_det = det.copy()
            enriched_det.update({
                'distance_cm': distance_cm,
                'real_width_cm': real_width_cm,
                'real_height_cm': real_height_cm,
                'depth_cm': depth_cm,
                'severity': severity,
                'q_score': q_score
            })
            enriched_detections.append(enriched_det)
            
        return enriched_detections


class EnhancedVisionPipeline:
    """Enhanced Vision Pipeline with ML-based detection and depth estimation.
    
    Uses YOLOv8 trained model for multi-class defect detection and
    MiDaS for accurate depth estimation. Falls back to classical
    pipeline if ML models are unavailable.
    """
    
    def __init__(self, config: dict):
        """Initialize enhanced pipeline with ML models."""
        # Initialize base pipeline (classical detection fallback)
        self.base_pipeline = VisionPipeline(config)
        self.config = config
        
        # Try to load ML inference engine
        self._ml_detector = None
        self._depth_estimator = None
        self._load_ml_models()
    
    def _load_ml_models(self):
        """Load ML models with graceful fallback."""
        try:
            from pathguard.ml.tensorrt_engine import get_inference_engine
            model_path = self.config.get('ml_model_path', 'models/best.pt')
            if Path(model_path).exists():
                self._ml_detector = get_inference_engine(model_path)
                logger.info(f'Loaded ML detector from {model_path}')
        except Exception as e:
            logger.warning(f'ML detector not available: {e}. Using classical detection.')
        
        try:
            from pathguard.ml.depth_estimator import get_depth_estimator
            model_type = self.config.get('depth_model_type', 'DPT_Hybrid')
            self._depth_estimator = get_depth_estimator(model_type)
            logger.info(f'Loaded depth estimator: {model_type}')
        except Exception as e:
            logger.warning(f'Depth estimator not available: {e}. Using intensity fallback.')
    
    def process_frame(self, frame: np.ndarray, imu_data: dict = None) -> list[dict]:
        """Process frame with ML models (falling back to classical if needed)."""
        # Step 1: Undistort
        undistorted = self.base_pipeline.calibrator.undistort(frame)
        
        # Step 2: Detection (ML or classical)
        if self._ml_detector is not None:
            result = self._ml_detector.infer(undistorted)
            detections = []
            for i in range(len(result.boxes)):
                x1, y1, x2, y2 = result.boxes[i]
                w = x2 - x1
                h = y2 - y1
                detections.append({
                    'bbox': (int(x1), int(y1), int(w), int(h)),
                    'area': int(w * h),
                    'aspect_ratio': w / max(h, 1),
                    'confidence': float(result.scores[i]),
                    'class_id': int(result.class_ids[i]),
                    'class_name': DEFECT_CLASSES.get(int(result.class_ids[i]), 'unknown'),
                    'inference_time_ms': result.inference_time_ms
                })
        else:
            detections = self.base_pipeline.detector.detect(undistorted)
            for d in detections:
                d['class_id'] = 0  # Default to pothole
                d['class_name'] = 'pothole'
                d['confidence'] = 0.5
        
        # Step 3: Enrich each detection with geometry and depth
        enriched = []
        geom = self.base_pipeline.geometry
        imu_fusion = self.base_pipeline.imu_fusion
        
        for det in detections:
            x, y, w, h = det['bbox']
            
            # Distance and real dimensions
            distance = geom.compute_distance(h)
            real_w = geom.compute_real_width(w, distance)
            real_h = geom.compute_real_height(h, distance)
            
            # Depth estimation (ML or fallback)
            if self._depth_estimator is not None:
                try:
                    depth_cm = self._depth_estimator.estimate_defect_depth_cm(undistorted, (x, y, w, h))
                except Exception:
                    roi = undistorted[max(0,y):y+h, max(0,x):x+w]
                    depth_cm = geom.estimate_depth(roi)
            else:
                roi = undistorted[max(0,y):y+h, max(0,x):x+w]
                depth_cm = geom.estimate_depth(roi)
            
            # IMU fusion severity
            imu_az = imu_data.get('az', 0.0) if imu_data else 0.0
            severity = imu_fusion.classify_severity(depth_cm, imu_az)
            
            # Q-score
            roi = undistorted[max(0,y):y+h, max(0,x):x+w]
            q_score = compute_q_score(w, h, roi) if roi.size > 0 else 0.0
            
            enriched.append({
                **det,
                'distance_cm': round(distance, 2),
                'width_cm': round(real_w, 2),
                'height_cm': round(real_h, 2),
                'depth_cm': round(depth_cm, 2),
                'severity': severity,
                'q_score': round(q_score, 2),
                'imu_az_g': imu_az
            })
        
        return enriched
