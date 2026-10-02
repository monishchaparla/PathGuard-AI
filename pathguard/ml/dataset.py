"""Dataset Management for Road Defect Detection Training.

Handles YOLO-format dataset creation, splitting, validation,
and frame extraction from dashcam footage.
"""
import os
import cv2
import json
import shutil
import random
import logging
import numpy as np
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# 7-class road defect taxonomy aligned with IRC:82-2015
DEFECT_CLASSES = {
    0: 'pothole',
    1: 'longitudinal_crack',
    2: 'transverse_crack', 
    3: 'alligator_crack',
    4: 'rutting',
    5: 'raveling',
    6: 'patching'
}

DEFECT_CLASS_NAMES = list(DEFECT_CLASSES.values())

@dataclass
class Annotation:
    image_path: str
    class_id: int
    bbox_normalized: tuple[float, float, float, float]  # YOLO format: cx,cy,w,h normalized
    confidence: float = 1.0
    mask_path: Optional[str] = None

class FrameExtractor:
    def __init__(self, output_dir='data/frames', target_fps=2.0):
        self.output_dir = Path(output_dir)
        self.target_fps = target_fps
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def _calculate_similarity(self, img1, img2):
        hist1 = cv2.calcHist([img1], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
        hist2 = cv2.calcHist([img2], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
        cv2.normalize(hist1, hist1)
        cv2.normalize(hist2, hist2)
        return cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)

    def extract_from_video(self, video_path: str, gps_log: list[dict] = None) -> list[str]:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"Could not open video {video_path}")
            return []
            
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0: fps = 30.0
        frame_interval = int(fps / self.target_fps)
        if frame_interval < 1: frame_interval = 1
        
        saved_paths = []
        count = 0
        last_saved_frame = None
        
        while True:
            ret, frame = cap.read()
            if not ret: break
            
            if count % frame_interval == 0:
                save_frame = True
                if last_saved_frame is not None:
                    sim = self._calculate_similarity(last_saved_frame, frame)
                    if sim > 0.95:
                        save_frame = False
                        
                if save_frame:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                    gps_str = ""
                    if gps_log and len(gps_log) > len(saved_paths):
                        gps = gps_log[len(saved_paths) % len(gps_log)]
                        gps_str = f"_lat{gps.get('lat',0)}_lon{gps.get('lon',0)}"
                        
                    filename = f"frame_{timestamp}{gps_str}.jpg"
                    out_path = self.output_dir / filename
                    cv2.imwrite(str(out_path), frame)
                    saved_paths.append(str(out_path))
                    last_saved_frame = frame
            count += 1
            
        cap.release()
        return saved_paths

    def extract_from_camera(self, camera_id=0, duration_seconds=60, gps_callback=None) -> list[str]:
        cap = cv2.VideoCapture(camera_id)
        if not cap.isOpened():
            logger.error(f"Could not open camera {camera_id}")
            return []
            
        saved_paths = []
        start_time = datetime.now()
        frame_delay = 1.0 / self.target_fps
        last_capture_time = datetime.now()
        last_saved_frame = None
        
        while (datetime.now() - start_time).total_seconds() < duration_seconds:
            ret, frame = cap.read()
            if not ret: continue
            
            now = datetime.now()
            if (now - last_capture_time).total_seconds() >= frame_delay:
                save_frame = True
                if last_saved_frame is not None:
                    sim = self._calculate_similarity(last_saved_frame, frame)
                    if sim > 0.95:
                        save_frame = False
                
                if save_frame:
                    timestamp = now.strftime("%Y%m%d_%H%M%S_%f")
                    gps_str = ""
                    if gps_callback:
                        gps = gps_callback()
                        if gps:
                            gps_str = f"_lat{gps.get('lat',0)}_lon{gps.get('lon',0)}"
                        
                    filename = f"cam_{timestamp}{gps_str}.jpg"
                    out_path = self.output_dir / filename
                    cv2.imwrite(str(out_path), frame)
                    saved_paths.append(str(out_path))
                    last_saved_frame = frame
                last_capture_time = now
                
        cap.release()
        return saved_paths

class DatasetManager:
    def __init__(self, base_dir='data/road_defects'):
        self.base_dir = Path(base_dir).resolve()
        
    def create_dataset_structure(self):
        for split in ['train', 'val', 'test']:
            (self.base_dir / 'images' / split).mkdir(parents=True, exist_ok=True)
            (self.base_dir / 'labels' / split).mkdir(parents=True, exist_ok=True)
        self.generate_dataset_yaml()
        
    def generate_dataset_yaml(self) -> str:
        yaml_content = f"path: {self.base_dir.as_posix()}\n"
        yaml_content += "train: images/train\n"
        yaml_content += "val: images/val\n"
        yaml_content += "test: images/test\n"
        yaml_content += f"nc: {len(DEFECT_CLASSES)}\n"
        yaml_content += f"names: {DEFECT_CLASS_NAMES}\n"
        
        yaml_path = self.base_dir / 'dataset.yaml'
        yaml_path.write_text(yaml_content)
        return str(yaml_path)

    def add_image(self, image_path: str, annotations: list[Annotation], split='train'):
        img_src = Path(image_path)
        if not img_src.exists():
            logger.error(f"Image {img_src} not found")
            return
            
        img_dest = self.base_dir / 'images' / split / img_src.name
        shutil.copy(img_src, img_dest)
        
        label_dest = self.base_dir / 'labels' / split / f"{img_src.stem}.txt"
        with open(label_dest, 'w') as f:
            for ann in annotations:
                cx, cy, w, h = ann.bbox_normalized
                f.write(f"{ann.class_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n")

    def split_dataset(self, train_ratio=0.7, val_ratio=0.2, test_ratio=0.1):
        if not abs((train_ratio + val_ratio + test_ratio) - 1.0) < 1e-5:
            logger.error("Ratios must sum to 1.0")
            return
            
        all_images = list((self.base_dir / 'images').glob('*.jpg'))
        if not all_images:
            return
            
        random.shuffle(all_images)
        n = len(all_images)
        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)
        
        splits = {
            'train': all_images[:n_train],
            'val': all_images[n_train:n_train+n_val],
            'test': all_images[n_train+n_val:]
        }
        
        for split, images in splits.items():
            for img_path in images:
                label_path = self.base_dir / 'labels' / f"{img_path.stem}.txt"
                if label_path.exists():
                    shutil.move(str(img_path), str(self.base_dir / 'images' / split / img_path.name))
                    shutil.move(str(label_path), str(self.base_dir / 'labels' / split / label_path.name))

    def get_statistics(self) -> dict:
        stats = {'splits': {}, 'classes': {i: 0 for i in DEFECT_CLASSES}}
        for split in ['train', 'val', 'test']:
            img_dir = self.base_dir / 'images' / split
            lbl_dir = self.base_dir / 'labels' / split
            if img_dir.exists():
                stats['splits'][split] = len(list(img_dir.glob('*.jpg')))
            if lbl_dir.exists():
                for lbl_file in lbl_dir.glob('*.txt'):
                    with open(lbl_file, 'r') as f:
                        for line in f:
                            class_id = int(line.split()[0])
                            if class_id in stats['classes']:
                                stats['classes'][class_id] += 1
        return stats

    def validate_dataset(self) -> list[str]:
        errors = []
        for split in ['train', 'val', 'test']:
            img_dir = self.base_dir / 'images' / split
            lbl_dir = self.base_dir / 'labels' / split
            
            if not img_dir.exists() or not lbl_dir.exists():
                continue
                
            images = {f.stem for f in img_dir.glob('*.jpg')}
            labels = {f.stem for f in lbl_dir.glob('*.txt')}
            
            missing_labels = images - labels
            missing_images = labels - images
            
            for m in missing_labels: errors.append(f"Missing label for image: {split}/{m}.jpg")
            for m in missing_images: errors.append(f"Missing image for label: {split}/{m}.txt")
            
            for lbl_file in lbl_dir.glob('*.txt'):
                with open(lbl_file, 'r') as f:
                    for line_num, line in enumerate(f, 1):
                        parts = line.strip().split()
                        if len(parts) != 5:
                            errors.append(f"Invalid format in {lbl_file.name} line {line_num}")
                            continue
                        try:
                            cls_id = int(parts[0])
                            coords = [float(x) for x in parts[1:]]
                            if cls_id not in DEFECT_CLASSES:
                                errors.append(f"Invalid class {cls_id} in {lbl_file.name}")
                            if any(c < 0 or c > 1 for c in coords):
                                errors.append(f"Out of bounds coordinate in {lbl_file.name}")
                        except ValueError:
                            errors.append(f"Non-numeric value in {lbl_file.name} line {line_num}")
        return errors

    def create_synthetic_samples(self, num_samples=100, output_dir=None):
        out_images = Path(output_dir) if output_dir else self.base_dir / 'images' / 'train'
        out_labels = Path(output_dir).parent / 'labels' / 'train' if output_dir else self.base_dir / 'labels' / 'train'
        
        out_images.mkdir(parents=True, exist_ok=True)
        out_labels.mkdir(parents=True, exist_ok=True)
        
        for i in range(num_samples):
            # Create gray asphalt background with random noise texture
            img = np.random.normal(100, 20, (640, 640, 3)).astype(np.uint8)
            img = cv2.GaussianBlur(img, (5, 5), 0)
            
            labels = []
            
            # Add synthetic pothole (class 0)
            if random.random() > 0.3:
                cx, cy = random.randint(100, 540), random.randint(100, 540)
                ax, ay = random.randint(30, 80), random.randint(20, 60)
                angle = random.randint(0, 180)
                cv2.ellipse(img, (cx, cy), (ax, ay), angle, 0, 360, (40, 40, 40), -1)
                
                nx, ny = cx / 640.0, cy / 640.0
                nw, nh = (ax * 2.2) / 640.0, (ay * 2.2) / 640.0
                labels.append(f"0 {nx:.6f} {ny:.6f} {nw:.6f} {nh:.6f}")
                
            # Add synthetic crack (class 1)
            if random.random() > 0.5:
                start_pt = (random.randint(50, 590), random.randint(50, 300))
                end_pt = (start_pt[0] + random.randint(-50, 50), start_pt[1] + random.randint(100, 300))
                pts = np.array([start_pt, 
                              (start_pt[0] + random.randint(-30, 30), (start_pt[1]+end_pt[1])//2), 
                              end_pt], np.int32)
                pts = pts.reshape((-1, 1, 2))
                cv2.polylines(img, [pts], isClosed=False, color=(30, 30, 30), thickness=random.randint(2, 5))
                
                min_x, min_y = np.min(pts, axis=0)[0]
                max_x, max_y = np.max(pts, axis=0)[0]
                cx, cy = (min_x + max_x) / 2.0, (min_y + max_y) / 2.0
                w, h = (max_x - min_x + 20), (max_y - min_y + 20)
                
                labels.append(f"1 {cx/640.0:.6f} {cy/640.0:.6f} {w/640.0:.6f} {h/640.0:.6f}")
                
            # Lighting variation
            if random.random() > 0.5:
                img = cv2.convertScaleAbs(img, alpha=random.uniform(0.7, 1.3), beta=random.randint(-30, 30))
                
            img_name = f"synth_{int(datetime.now().timestamp())}_{i:04d}"
            cv2.imwrite(str(out_images / f"{img_name}.jpg"), img)
            
            with open(out_labels / f"{img_name}.txt", 'w') as f:
                f.write("\n".join(labels) + "\n")

class COCOToYOLO:
    def convert(self, coco_json_path: str, output_dir: str):
        with open(coco_json_path, 'r') as f:
            coco_data = json.load(f)
            
        out_path = Path(output_dir)
        (out_path / 'images').mkdir(parents=True, exist_ok=True)
        (out_path / 'labels').mkdir(parents=True, exist_ok=True)
        
        images_info = {img['id']: img for img in coco_data.get('images', [])}
        
        # Assume coco categories map closely or can be transformed
        # This is a simplified direct mapping
        labels_map = {}
        for ann in coco_data.get('annotations', []):
            img_id = ann['image_id']
            if img_id not in labels_map:
                labels_map[img_id] = []
                
            img = images_info[img_id]
            width, height = img['width'], img['height']
            
            # COCO bbox: [x_min, y_min, width, height]
            bbox = ann['bbox']
            x_center = (bbox[0] + bbox[2] / 2) / width
            y_center = (bbox[1] + bbox[3] / 2) / height
            w_norm = bbox[2] / width
            h_norm = bbox[3] / height
            
            cat_id = ann['category_id'] # Simplified assumption: categories match
            labels_map[img_id].append(f"{cat_id} {x_center:.6f} {y_center:.6f} {w_norm:.6f} {h_norm:.6f}")
            
        for img_id, labels in labels_map.items():
            img_info = images_info[img_id]
            file_name = img_info['file_name']
            stem = Path(file_name).stem
            
            with open(out_path / 'labels' / f"{stem}.txt", 'w') as f:
                f.write("\n".join(labels) + "\n")
