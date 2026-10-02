"""Monocular Depth Estimation using MiDaS.

Replaces naive intensity-based depth heuristic with ML-based
dense depth prediction. Runs on GPU at 30+ FPS.
"""
import cv2
import numpy as np
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger(__name__)

try:
    import torch
    import torch.nn.functional as F
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


class MiDaSDepthEstimator:
    def __init__(self, model_type='DPT_Hybrid', device=None, camera_height_cm=130.0):
        self.camera_height_cm = camera_height_cm
        self.calibration_factor = None
        self.ground_reference_depth = None
        
        if not HAS_TORCH:
            raise RuntimeError("PyTorch is not available. Cannot use MiDaSDepthEstimator.")
            
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)
            
        logger.info(f"Loading MiDaS model {model_type} on {self.device}...")
        self.model = torch.hub.load("intel-isl/MiDaS", model_type)
        self.model.to(self.device)
        self.model.eval()
        
        midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
        if model_type == "DPT_Large" or model_type == "DPT_Hybrid":
            self.transform = midas_transforms.dpt_transform
        else:
            self.transform = midas_transforms.small_transform

    def estimate_depth_map(self, frame: np.ndarray) -> np.ndarray:
        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        input_batch = self.transform(img).to(self.device)
        
        with torch.no_grad():
            prediction = self.model(input_batch)
            prediction = F.interpolate(
                prediction.unsqueeze(1),
                size=img.shape[:2],
                mode="bicubic",
                align_corners=False,
            ).squeeze()
            
        depth_map = prediction.cpu().numpy()
        return depth_map

    def get_depth_at_bbox(self, depth_map: np.ndarray, bbox: tuple) -> Dict[str, float]:
        x1, y1, x2, y2 = map(int, bbox)
        h, w = depth_map.shape
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        
        if x1 >= x2 or y1 >= y2:
            return {'mean_depth': 0.0, 'max_depth': 0.0, 'min_depth': 0.0, 'std_depth': 0.0}
            
        roi = depth_map[y1:y2, x1:x2]
        return {
            'mean_depth': float(np.mean(roi)),
            'max_depth': float(np.max(roi)),
            'min_depth': float(np.min(roi)),
            'std_depth': float(np.std(roi))
        }

    def relative_to_absolute_depth(self, relative_depth: float, reference_depth: Optional[float] = None) -> float:
        if self.calibration_factor is None or self.ground_reference_depth is None:
            logger.warning("Depth estimator not calibrated, returning raw difference.")
            ref = reference_depth if reference_depth is not None else 0.0
            diff = relative_depth - ref
            return max(1.5, min(30.0, float(diff)))
            
        ref = reference_depth if reference_depth is not None else self.ground_reference_depth
        diff = relative_depth - ref
        depth_cm = diff * self.calibration_factor
        return max(1.5, min(30.0, float(depth_cm)))

    def calibrate(self, ground_frame: np.ndarray) -> float:
        depth_map = self.estimate_depth_map(ground_frame)
        h, w = depth_map.shape
        # Use lower 20% of image as ground plane
        ground_roi = depth_map[int(h*0.8):h, :]
        self.ground_reference_depth = float(np.median(ground_roi))
        # Arbitrarily set calibration factor (camera height / median depth)
        self.calibration_factor = self.camera_height_cm / (self.ground_reference_depth + 1e-6)
        logger.info(f"Calibrated ground depth: {self.ground_reference_depth}, factor: {self.calibration_factor}")
        return self.calibration_factor

    def estimate_defect_depth_cm(self, frame: np.ndarray, bbox: tuple) -> float:
        depth_map = self.estimate_depth_map(frame)
        defect_stats = self.get_depth_at_bbox(depth_map, bbox)
        defect_depth = defect_stats['mean_depth']
        
        # Surrounding ground depth
        x1, y1, x2, y2 = map(int, bbox)
        bw, bh = x2 - x1, y2 - y1
        h, w = depth_map.shape
        
        sx1 = max(0, x1 - int(bw*0.5))
        sy1 = max(0, y1 - int(bh*0.5))
        sx2 = min(w, x2 + int(bw*0.5))
        sy2 = min(h, y2 + int(bh*0.5))
        
        surround_roi = depth_map[sy1:sy2, sx1:sx2]
        ground_depth = float(np.median(surround_roi)) if surround_roi.size > 0 else defect_depth
        
        diff = ground_depth - defect_depth # Defect is deeper
        
        if self.calibration_factor is None:
            # Fallback simple scale if not calibrated
            depth_cm = abs(diff) * 0.1 
        else:
            depth_cm = abs(diff) * self.calibration_factor
            
        return max(1.5, min(30.0, float(depth_cm)))

    def visualize_depth_map(self, frame: np.ndarray, depth_map: np.ndarray) -> np.ndarray:
        depth_min = depth_map.min()
        depth_max = depth_map.max()
        if depth_max - depth_min > 0:
            depth_normalized = (depth_map - depth_min) / (depth_max - depth_min)
        else:
            depth_normalized = np.zeros_like(depth_map)
            
        depth_uint8 = (depth_normalized * 255).astype(np.uint8)
        depth_color = cv2.applyColorMap(depth_uint8, cv2.COLORMAP_INFERNO)
        return cv2.addWeighted(frame, 0.5, depth_color, 0.5, 0)


class FallbackDepthEstimator:
    def __init__(self, depth_min=1.5, depth_max=30.0):
        self.depth_min = depth_min
        self.depth_max = depth_max
        self.calibration_factor = None

    def estimate_depth_map(self, frame: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return 255.0 - gray.astype(np.float32)

    def get_depth_at_bbox(self, depth_map: np.ndarray, bbox: tuple) -> Dict[str, float]:
        x1, y1, x2, y2 = map(int, bbox)
        h, w = depth_map.shape
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        
        if x1 >= x2 or y1 >= y2:
            return {'mean_depth': 0.0, 'max_depth': 0.0, 'min_depth': 0.0, 'std_depth': 0.0}
            
        roi = depth_map[y1:y2, x1:x2]
        return {
            'mean_depth': float(np.mean(roi)),
            'max_depth': float(np.max(roi)),
            'min_depth': float(np.min(roi)),
            'std_depth': float(np.std(roi))
        }

    def estimate_defect_depth_cm(self, frame: np.ndarray, bbox: tuple) -> float:
        depth_map = self.estimate_depth_map(frame)
        x1, y1, x2, y2 = map(int, bbox)
        defect_roi = depth_map[max(0, y1):min(depth_map.shape[0], y2), max(0, x1):min(depth_map.shape[1], x2)]
        if defect_roi.size == 0:
            return self.depth_min
            
        mean_intensity = np.mean(defect_roi)
        # Simple heuristic mapping from intensity to depth
        depth = self.depth_min + (mean_intensity / 255.0) * (self.depth_max - self.depth_min)
        return max(self.depth_min, min(self.depth_max, float(depth)))

    def calibrate(self, ground_frame: np.ndarray) -> float:
        return 1.0


def get_depth_estimator(model_type='DPT_Hybrid', **kwargs):
    if HAS_TORCH:
        try:
            return MiDaSDepthEstimator(model_type=model_type, **kwargs)
        except Exception as e:
            logger.error(f"Failed to initialize MiDaSDepthEstimator: {e}. Using fallback.")
            return FallbackDepthEstimator()
    return FallbackDepthEstimator()
