"""Auto-Annotation Pipeline using Segment Anything Model 2 (SAM2).

Uses a pre-trained detector as prompt generator for SAM2 to produce
high-quality instance segmentation masks for training data.
"""
import cv2
import numpy as np
import logging
import json
import os
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass

logger = logging.getLogger(__name__)

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

class AutoAnnotator:
    def __init__(self, detector_model_path: Optional[str] = None, sam_model_type: str = 'vit_b', device: str = 'cuda', confidence_threshold: float = 0.3):
        self.detector_model_path = detector_model_path
        self.sam_model_type = sam_model_type
        self.device = device
        self.confidence_threshold = confidence_threshold
        
        if YOLO and detector_model_path:
            try:
                self.detector = YOLO(detector_model_path)
            except Exception as e:
                logger.error(f"Failed to load YOLO model: {e}")
                self.detector = None
        else:
            self.detector = None
            logger.warning("YOLO not installed or model path not provided.")
            
        # SAM2 would be initialized here
        self.sam = None 

    def detect_and_annotate(self, image_path: str) -> List[Dict[str, Any]]:
        if not self.detector:
            logger.error("Detector not initialized.")
            return []
            
        img = cv2.imread(image_path)
        if img is None:
            logger.error(f"Failed to read image {image_path}")
            return []
            
        results = self.detector(img, conf=self.confidence_threshold, device=self.device, verbose=False)
        annotations = []
        
        for result in results:
            boxes = result.boxes
            for i, box in enumerate(boxes):
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                cx, cy, w, h = box.xywh[0].cpu().numpy()
                conf = float(box.conf[0].cpu().numpy())
                cls_id = int(box.cls[0].cpu().numpy())
                
                # Mock SAM2 mask generation
                # In production, use sam predictor with box prompt
                mask_polygon = [[float(x1), float(y1)], [float(x2), float(y1)], [float(x2), float(y2)], [float(x1), float(y2)]]
                
                annotations.append({
                    'class_id': cls_id,
                    'bbox': [float(cx), float(cy), float(w), float(h)],
                    'mask_polygon': mask_polygon,
                    'confidence': conf
                })
        return annotations

    def annotate_directory(self, image_dir: str, output_dir: str, format: str = 'yolo') -> Dict[str, Any]:
        img_dir_path = Path(image_dir)
        out_dir_path = Path(output_dir)
        out_dir_path.mkdir(parents=True, exist_ok=True)
        
        results = {'processed': 0, 'failed': 0, 'annotations': 0}
        
        for img_path in img_dir_path.glob('*.[jp][pn]*[g]'):
            try:
                img_path_str = str(img_path)
                anns = self.detect_and_annotate(img_path_str)
                
                if format == 'yolo':
                    img = cv2.imread(img_path_str)
                    h, w = img.shape[:2]
                    yolo_txt = self.generate_yolo_labels(anns, (h, w))
                    label_path = out_dir_path / f"{img_path.stem}.txt"
                    with open(label_path, 'w') as f:
                        f.write(yolo_txt)
                results['processed'] += 1
                results['annotations'] += len(anns)
            except Exception as e:
                logger.error(f"Failed to annotate {img_path}: {e}")
                results['failed'] += 1
                
        return results

    def generate_yolo_labels(self, annotations: List[Dict[str, Any]], image_shape: tuple) -> str:
        lines = []
        img_h, img_w = image_shape[:2]
        for ann in annotations:
            cls_id = ann['class_id']
            # Convert pixel coords to normalized for segmentation
            norm_polygon = []
            for pt in ann.get('mask_polygon', []):
                norm_polygon.extend([pt[0]/img_w, pt[1]/img_h])
            
            line = f"{cls_id} " + " ".join([f"{x:.6f}" for x in norm_polygon])
            lines.append(line)
        return "\n".join(lines)

    def review_annotations(self, image_path: str, annotations: List[Dict[str, Any]]) -> np.ndarray:
        img = cv2.imread(image_path)
        if img is None:
            return np.zeros((100, 100, 3), dtype=np.uint8)
            
        for ann in annotations:
            poly = np.array(ann['mask_polygon'], np.int32).reshape((-1, 1, 2))
            cv2.polylines(img, [poly], isClosed=True, color=(0, 255, 0), thickness=2)
            
            cx, cy, w, h = ann['bbox']
            x = int(cx - w/2)
            y = int(cy - h/2)
            cv2.putText(img, f"cls:{ann['class_id']} {ann['confidence']:.2f}", (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1)
            
        return img


class SimpleAutoAnnotator:
    def __init__(self, min_area: int = 500, max_area: int = 50000):
        self.min_area = min_area
        self.max_area = max_area

    def detect_dark_regions(self, image: np.ndarray) -> List[Dict[str, Any]]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        thresh = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
        
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        regions = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if self.min_area < area < self.max_area:
                cls_id = self.classify_by_shape(cnt)
                x, y, w, h = cv2.boundingRect(cnt)
                cx, cy = x + w/2, y + h/2
                
                # Simplify polygon
                epsilon = 0.01 * cv2.arcLength(cnt, True)
                approx = cv2.approxPolyDP(cnt, epsilon, True)
                poly = approx.reshape(-1, 2).tolist()
                
                regions.append({
                    'class_id': cls_id,
                    'bbox': [cx, cy, w, h],
                    'mask_polygon': poly,
                    'confidence': 0.5,
                    'area': area
                })
        return regions

    def classify_by_shape(self, contour) -> int:
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = float(w) / h if h > 0 else 1.0
        
        if 0.8 < aspect_ratio < 1.2:
            return 0  # pothole
        elif aspect_ratio > 3.0:
            return 1  # longitudinal_crack (long thin, horizontal)
        elif aspect_ratio < 0.33:
            return 2  # transverse_crack (long thin, vertical)
        else:
            return 5  # raveling (default)

    def annotate_image(self, image_path: str) -> List[Dict[str, Any]]:
        img = cv2.imread(image_path)
        if img is None:
            return []
        return self.detect_dark_regions(img)

    def annotate_directory(self, image_dir: str, output_dir: str) -> Dict[str, Any]:
        img_dir_path = Path(image_dir)
        out_dir_path = Path(output_dir)
        out_dir_path.mkdir(parents=True, exist_ok=True)
        
        results = {'processed': 0, 'failed': 0, 'annotations': 0}
        
        for img_path in img_dir_path.glob('*.[jp][pn]*[g]'):
            try:
                anns = self.annotate_image(str(img_path))
                
                # Save as simple JSON
                out_file = out_dir_path / f"{img_path.stem}.json"
                with open(out_file, 'w') as f:
                    json.dump(anns, f)
                    
                results['processed'] += 1
                results['annotations'] += len(anns)
            except Exception as e:
                logger.error(f"Failed to annotate {img_path}: {e}")
                results['failed'] += 1
                
        return results

def get_auto_annotator(**kwargs) -> Union[AutoAnnotator, SimpleAutoAnnotator]:
    use_sam = kwargs.get('use_sam', False)
    if use_sam or kwargs.get('detector_model_path'):
        return AutoAnnotator(
            detector_model_path=kwargs.get('detector_model_path'),
            sam_model_type=kwargs.get('sam_model_type', 'vit_b'),
            device=kwargs.get('device', 'cuda'),
            confidence_threshold=kwargs.get('confidence_threshold', 0.3)
        )
    return SimpleAutoAnnotator(
        min_area=kwargs.get('min_area', 500),
        max_area=kwargs.get('max_area', 50000)
    )
