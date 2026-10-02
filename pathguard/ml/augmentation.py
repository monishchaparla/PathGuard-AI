"""Advanced Data Augmentation for Road Defect Training.

Simulates real-world driving conditions: rain, fog, night, glare,
motion blur, and perspective distortion.
"""
import cv2
import numpy as np
import random
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

try:
    import albumentations as A
    from albumentations.pytorch import ToTensorV2
    HAS_ALBUMENTATIONS = True
except ImportError:
    HAS_ALBUMENTATIONS = False
    logger.warning('Albumentations not installed. Using basic augmentation.')

def get_training_transform(image_size=640):
    if HAS_ALBUMENTATIONS:
        return A.Compose([
            A.RandomResizedCrop(image_size, image_size, scale=(0.5, 1.0)),
            A.HorizontalFlip(p=0.5),
            A.RandomBrightnessContrast(brightness_limit=0.3, contrast_limit=0.3, p=0.5),
            A.HueSaturationValue(hue_shift_limit=20, sat_shift_limit=30, val_shift_limit=20, p=0.3),
            A.GaussNoise(var_limit=(10.0, 50.0), p=0.3),
            A.MotionBlur(blur_limit=7, p=0.3),
            A.GaussianBlur(blur_limit=7, p=0.2),
            A.CLAHE(p=0.3),
            A.RandomShadow(p=0.3),
            A.RandomRain(p=0.15),
            A.RandomFog(fog_coef_lower=0.1, fog_coef_upper=0.3, p=0.15),
            A.RandomSunFlare(p=0.1),
            A.Perspective(p=0.2),
            A.Normalize(mean=[0.485,0.456,0.406], std=[0.229,0.224,0.225])
        ], bbox_params=A.BboxParams(format='yolo', min_visibility=0.3, label_fields=['class_labels']))
    
    # Fallback basic transform callable
    def basic_transform(image, bboxes, class_labels):
        img = cv2.resize(image, (image_size, image_size))
        img = img.astype(np.float32) / 255.0
        return {"image": img, "bboxes": bboxes, "class_labels": class_labels}
    return basic_transform

def get_validation_transform(image_size=640):
    if HAS_ALBUMENTATIONS:
        return A.Compose([
            A.Resize(image_size, image_size),
            A.Normalize(mean=[0.485,0.456,0.406], std=[0.229,0.224,0.225])
        ], bbox_params=A.BboxParams(format='yolo', min_visibility=0.3, label_fields=['class_labels']))
    
    def basic_val_transform(image, bboxes, class_labels):
        img = cv2.resize(image, (image_size, image_size))
        img = img.astype(np.float32) / 255.0
        return {"image": img, "bboxes": bboxes, "class_labels": class_labels}
    return basic_val_transform

def simulate_rain(image, intensity=0.5) -> np.ndarray:
    """Add rain streaks using OpenCV line drawing with random angles."""
    img = image.copy()
    h, w = img.shape[:2]
    num_drops = int(intensity * 1000)
    for _ in range(num_drops):
        x = random.randint(0, w)
        y = random.randint(0, h)
        length = random.randint(10, 20)
        angle = random.randint(-15, 15)
        
        x2 = int(x + length * np.sin(np.radians(angle)))
        y2 = int(y + length * np.cos(np.radians(angle)))
        
        cv2.line(img, (x, y), (x2, y2), (200, 200, 200), 1)
    
    # Blur slightly for motion effect
    img = cv2.GaussianBlur(img, (3, 3), 0)
    return cv2.addWeighted(image, 0.7, img, 0.3, 0)

def simulate_fog(image, intensity=0.3) -> np.ndarray:
    """Blend with white overlay based on depth (closer = less fog)."""
    h, w = image.shape[:2]
    fog_layer = np.ones((h, w, 3), dtype=np.uint8) * 255
    
    # Gradient map simulating depth (top of image is further away/more fog)
    gradient = np.linspace(1, 0, h).reshape(-1, 1, 1)
    gradient = np.tile(gradient, (1, w, 3))
    
    fog_alpha = intensity * gradient
    fog_alpha = np.clip(fog_alpha, 0, 1)
    
    img = image.astype(np.float32) * (1 - fog_alpha) + fog_layer * fog_alpha
    return img.astype(np.uint8)

def simulate_night(image, brightness_factor=0.3) -> np.ndarray:
    """Reduce brightness, add headlight cone effect."""
    h, w = image.shape[:2]
    img = cv2.convertScaleAbs(image, alpha=brightness_factor, beta=0)
    
    # Create headlight cone (polygon mask)
    mask = np.zeros((h, w), dtype=np.uint8)
    pts = np.array([[w//2 - 100, h], [w//2 + 100, h], [w, h//2], [0, h//2]], np.int32)
    cv2.fillPoly(mask, [pts], 255)
    mask = cv2.GaussianBlur(mask, (101, 101), 0)
    
    mask_3d = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR) / 255.0
    headlight = np.clip(image.astype(np.float32) * 1.2, 0, 255)
    
    result = img.astype(np.float32) * (1 - mask_3d) + headlight * mask_3d
    return result.astype(np.uint8)

def simulate_motion_blur(image, kernel_size=15, angle=0) -> np.ndarray:
    """Directional motion blur kernel."""
    kernel = np.zeros((kernel_size, kernel_size))
    center = kernel_size // 2
    
    angle_rad = np.radians(angle)
    for i in range(kernel_size):
        offset = i - center
        x = int(center + offset * np.cos(angle_rad))
        y = int(center + offset * np.sin(angle_rad))
        if 0 <= x < kernel_size and 0 <= y < kernel_size:
            kernel[y, x] = 1.0
            
    kernel /= np.sum(kernel)
    return cv2.filter2D(image, -1, kernel)

def augment_batch(images, labels, transform, num_augmented_per_image=3) -> tuple:
    """Apply transform to create augmented copies."""
    aug_images = []
    aug_labels = []
    
    for img, bboxes_classes in zip(images, labels):
        # bboxes_classes expected as list of (class_id, [x,y,w,h])
        class_labels = [bc[0] for bc in bboxes_classes]
        bboxes = [bc[1] for bc in bboxes_classes]
        
        # Add original
        aug_images.append(img)
        aug_labels.append(bboxes_classes)
        
        for _ in range(num_augmented_per_image):
            if HAS_ALBUMENTATIONS:
                try:
                    transformed = transform(image=img, bboxes=bboxes, class_labels=class_labels)
                    aug_images.append(transformed['image'])
                    new_labels = [(c, b) for c, b in zip(transformed['class_labels'], transformed['bboxes'])]
                    aug_labels.append(new_labels)
                except Exception as e:
                    logger.warning(f"Augmentation failed: {e}")
                    pass
            else:
                # Basic augmentation usage or custom fallbacks
                transformed = transform(img, bboxes, class_labels)
                # Apply manual effects randomly
                aug_img = transformed['image']
                if isinstance(aug_img, np.ndarray) and aug_img.dtype == np.float32:
                    aug_img = (aug_img * 255).astype(np.uint8)
                    
                if random.random() > 0.5: aug_img = simulate_rain(aug_img)
                elif random.random() > 0.5: aug_img = simulate_night(aug_img)
                
                aug_images.append(aug_img)
                new_labels = [(c, b) for c, b in zip(transformed['class_labels'], transformed['bboxes'])]
                aug_labels.append(new_labels)
                
    return aug_images, aug_labels
