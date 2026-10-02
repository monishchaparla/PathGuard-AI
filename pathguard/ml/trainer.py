"""YOLOv8 Training Pipeline for Road Defect Detection.

Supports training, validation, export to TensorRT/ONNX,
and active learning on NVIDIA RTX 5050 (8GB VRAM).
"""
import os
import logging
import json
import time
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

try:
    from ultralytics import YOLO
    import torch
    HAS_ULTRALYTICS = True
except ImportError:
    HAS_ULTRALYTICS = False
    logger.warning('Ultralytics not installed. Training disabled.')


@dataclass
class TrainingConfig:
    model_size: str = 'yolov8s'  # 'yolov8n', 'yolov8s', 'yolov8m'
    dataset_yaml: str = 'data/road_defects/dataset.yaml'
    epochs: int = 100
    batch_size: int = 16  # Good for 8GB VRAM with yolov8s
    image_size: int = 640
    device: str = '0'  # GPU 0
    workers: int = 4
    patience: int = 20  # Early stopping
    save_dir: str = 'runs/train'
    pretrained: bool = True  # Start from COCO weights
    amp: bool = True  # Automatic Mixed Precision (FP16)
    optimizer: str = 'AdamW'
    lr0: float = 0.001
    lrf: float = 0.01
    warmup_epochs: int = 3
    mosaic: float = 1.0
    mixup: float = 0.1
    copy_paste: float = 0.1
    close_mosaic: int = 10
    freeze_layers: Optional[int] = None  # Freeze first N layers for fine-tuning


class PathGuardTrainer:
    def __init__(self, config: Optional[TrainingConfig] = None):
        self.config = config or TrainingConfig()
        if not HAS_ULTRALYTICS:
            logger.error("Ultralytics library is required for PathGuardTrainer.")
            
    def check_gpu(self) -> Dict[str, Any]:
        info = {'available': False, 'device_count': 0, 'vram_total_gb': 0.0, 'cuda_version': None}
        if HAS_ULTRALYTICS and torch.cuda.is_available():
            info['available'] = True
            info['device_count'] = torch.cuda.device_count()
            info['vram_total_gb'] = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            info['cuda_version'] = torch.version.cuda
            info['name'] = torch.cuda.get_device_name(0)
        return info

    def get_optimal_batch_size(self, model_size: str = 'yolov8s') -> int:
        gpu_info = self.check_gpu()
        vram = gpu_info['vram_total_gb']
        
        if vram >= 7.5: # 8GB class
            mapping = {'yolov8n': 32, 'yolov8s': 16, 'yolov8m': 8}
        elif vram >= 5.5: # 6GB class
            mapping = {'yolov8n': 24, 'yolov8s': 12, 'yolov8m': 4}
        else: # 4GB or less
            mapping = {'yolov8n': 16, 'yolov8s': 8, 'yolov8m': 2}
            
        return mapping.get(model_size, 8)

    def train(self, resume: bool = False) -> Dict[str, Any]:
        if not HAS_ULTRALYTICS:
            raise RuntimeError("Ultralytics not installed.")
        
        model_name = f"{self.config.model_size}.pt" if self.config.pretrained else f"{self.config.model_size}.yaml"
        model = YOLO(model_name)
        
        if self.config.freeze_layers:
            pass # Ultralytics train() accepts 'freeze' kwarg directly
            
        results = model.train(
            data=self.config.dataset_yaml,
            epochs=self.config.epochs,
            batch=self.config.batch_size,
            imgsz=self.config.image_size,
            device=self.config.device,
            workers=self.config.workers,
            patience=self.config.patience,
            project=self.config.save_dir,
            amp=self.config.amp,
            optimizer=self.config.optimizer,
            lr0=self.config.lr0,
            lrf=self.config.lrf,
            warmup_epochs=self.config.warmup_epochs,
            mosaic=self.config.mosaic,
            mixup=self.config.mixup,
            copy_paste=self.config.copy_paste,
            close_mosaic=self.config.close_mosaic,
            freeze=self.config.freeze_layers,
            resume=resume
        )
        return {"metrics": results.results_dict if hasattr(results, 'results_dict') else {}}

    def validate(self, model_path: Optional[str] = None, dataset_yaml: Optional[str] = None) -> Dict[str, Any]:
        if not HAS_ULTRALYTICS:
            raise RuntimeError("Ultralytics not installed.")
        model = YOLO(model_path or f"{self.config.save_dir}/train/weights/best.pt")
        metrics = model.val(data=dataset_yaml or self.config.dataset_yaml)
        return metrics.results_dict if hasattr(metrics, 'results_dict') else {}

    def predict(self, model_path: str, source: Any, conf: float = 0.25, save: bool = True) -> list:
        if not HAS_ULTRALYTICS:
            raise RuntimeError("Ultralytics not installed.")
        model = YOLO(model_path)
        results = model.predict(source=source, conf=conf, save=save)
        return results

    def export_onnx(self, model_path: str, imgsz: int = 640, half: bool = True, simplify: bool = True) -> str:
        if not HAS_ULTRALYTICS:
            raise RuntimeError("Ultralytics not installed.")
        model = YOLO(model_path)
        result = model.export(format='onnx', imgsz=imgsz, half=half, simplify=simplify)
        return result

    def export_tensorrt(self, model_path: str, imgsz: int = 640, half: bool = True) -> str:
        if not HAS_ULTRALYTICS:
            raise RuntimeError("Ultralytics not installed.")
        model = YOLO(model_path)
        result = model.export(format='engine', imgsz=imgsz, half=half, device=self.config.device)
        return result

    def export_all(self, model_path: str) -> Dict[str, str]:
        if not HAS_ULTRALYTICS:
            raise RuntimeError("Ultralytics not installed.")
        onnx_path = self.export_onnx(model_path)
        trt_path = self.export_tensorrt(model_path)
        model = YOLO(model_path)
        ov_path = model.export(format='openvino')
        return {'onnx': onnx_path, 'tensorrt': trt_path, 'openvino': ov_path}

    def benchmark(self, model_path: str, imgsz: int = 640) -> Dict[str, Any]:
        if not HAS_ULTRALYTICS:
            raise RuntimeError("Ultralytics not installed.")
        from ultralytics.utils.benchmarks import benchmark
        results = benchmark(model=model_path, imgsz=imgsz, half=True, device=self.config.device)
        return results

    def active_learning_score(self, model_path: str, unlabeled_dir: str, top_k: int = 50) -> List[str]:
        if not HAS_ULTRALYTICS:
            raise RuntimeError("Ultralytics not installed.")
        model = YOLO(model_path)
        import glob
        import numpy as np
        
        image_paths = glob.glob(os.path.join(unlabeled_dir, "*.*"))
        scores = []
        
        for img_path in image_paths:
            results = model.predict(img_path, verbose=False)
            if not results or len(results) == 0:
                continue
            
            probs = results[0].boxes.conf.cpu().numpy()
            if len(probs) > 0:
                # Basic entropy approx: -p * log(p)
                entropy = -np.sum(probs * np.log(probs + 1e-9))
            else:
                entropy = 0.0
                
            scores.append((entropy, img_path))
            
        scores.sort(key=lambda x: x[0], reverse=True)
        return [path for _, path in scores[:top_k]]

    def fine_tune(self, base_model: str, new_data_yaml: str, epochs: int = 30, freeze: int = 10) -> Dict[str, Any]:
        if not HAS_ULTRALYTICS:
            raise RuntimeError("Ultralytics not installed.")
        
        model = YOLO(base_model)
        results = model.train(
            data=new_data_yaml,
            epochs=epochs,
            freeze=freeze,
            project=self.config.save_dir,
            device=self.config.device
        )
        return {"metrics": results.results_dict if hasattr(results, 'results_dict') else {}}


class ModelRegistry:
    def __init__(self, registry_dir: str = 'models/'):
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.registry_file = self.registry_dir / 'registry.json'
        
        if self.registry_file.exists():
            with open(self.registry_file, 'r') as f:
                self.models = json.load(f)
        else:
            self.models = {}

    def _save_registry(self):
        with open(self.registry_file, 'w') as f:
            json.dump(self.models, f, indent=4)

    def register(self, model_path: str, metrics: Dict[str, Any], config: Dict[str, Any]) -> str:
        model_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.models[model_id] = {
            'path': str(model_path),
            'metrics': metrics,
            'config': config,
            'registered_at': datetime.now().isoformat()
        }
        self._save_registry()
        return model_id

    def get_best(self, metric: str = 'mAP50') -> Optional[str]:
        best_model = None
        best_score = -1.0
        
        for model_id, data in self.models.items():
            score = data.get('metrics', {}).get(metric, 0.0)
            if score > best_score:
                best_score = score
                best_model = data['path']
                
        return best_model

    def list_models(self) -> List[Dict[str, Any]]:
        return [{'id': k, **v} for k, v in self.models.items()]

    def load_model(self, model_id: Optional[str] = None) -> Any:
        if not HAS_ULTRALYTICS:
            raise RuntimeError("Ultralytics not installed.")
            
        if not self.models:
            logger.warning("Registry is empty.")
            return None
            
        if model_id is None:
            model_path = self.get_best()
        else:
            model_path = self.models.get(model_id, {}).get('path')
            
        if model_path and os.path.exists(model_path):
            return YOLO(model_path)
            
        logger.error(f"Model path not found: {model_path}")
        return None
