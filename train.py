"""PathGuard-AI ML Training CLI.

Complete training pipeline management:
  - Collect training data from dashcam
  - Auto-annotate with pre-trained models
  - Generate synthetic training data
  - Train YOLOv8 on RTX 5050
  - Export to TensorRT/ONNX
  - Benchmark inference speed

Usage:
    python train.py collect --camera 0 --duration 120
    python train.py synthetic --count 500
    python train.py annotate --source data/frames/
    python train.py train --model yolov8s --epochs 100
    python train.py export --format tensorrt
    python train.py benchmark --model models/best.pt
    python train.py full-pipeline  # End-to-end
"""
import argparse
import logging
import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f'training_{datetime.now():%Y%m%d_%H%M%S}.log')
    ]
)
logger = logging.getLogger('pathguard.train')

# ============================================================================
# BANNER
# ============================================================================
BANNER = r"""
╔═══════════════════════════════════════════════════════════════╗
║  ____       _   _      ____                     _            ║
║ |  _ \ __ _| |_| |__  / ___|_   _  __ _ _ __ __| |          ║
║ | |_) / _` | __| '_ \| |  _| | | |/ _` | '__/ _` |          ║
║ |  __/ (_| | |_| | | | |_| | |_| | (_| | | | (_| |          ║
║ |_|   \__,_|\__|_| |_|\____|\__,_|\__,_|_|  \__,_|          ║
║                                                               ║
║  ML Training Pipeline — RTX 5050 GPU Accelerated             ║
╚═══════════════════════════════════════════════════════════════╝
"""


def check_environment():
    """Check ML dependencies and GPU availability."""
    print("\n🔍 Checking environment...")

    status = {'gpu': False, 'ultralytics': False, 'torch': False}

    try:
        import torch
        status['torch'] = True
        status['torch_version'] = torch.__version__
        if torch.cuda.is_available():
            status['gpu'] = True
            status['gpu_name'] = torch.cuda.get_device_name(0)
            status['vram_gb'] = round(
                torch.cuda.get_device_properties(0).total_mem / 1024**3, 1
            )
            status['cuda_version'] = torch.version.cuda
            print(f"  ✅ PyTorch {torch.__version__} with CUDA {torch.version.cuda}")
            print(f"  ✅ GPU: {status['gpu_name']} ({status['vram_gb']} GB VRAM)")
        else:
            print(f"  ⚠️  PyTorch {torch.__version__} — CPU only (no CUDA)")
    except ImportError:
        print("  ❌ PyTorch not installed. Run: scripts/setup_gpu.ps1")

    try:
        from ultralytics import YOLO
        status['ultralytics'] = True
        print("  ✅ Ultralytics YOLOv8 available")
    except ImportError:
        print("  ❌ Ultralytics not installed")

    try:
        import cv2
        print(f"  ✅ OpenCV {cv2.__version__}")
    except ImportError:
        print("  ❌ OpenCV not installed")

    try:
        import albumentations
        print(f"  ✅ Albumentations {albumentations.__version__}")
    except ImportError:
        print("  ⚠️  Albumentations not installed (optional, for advanced augmentation)")

    return status


def cmd_collect(args):
    """Collect training data from dashcam."""
    from pathguard.ml.dataset import FrameExtractor

    print(f"\n📷 Collecting training frames from camera {args.camera}...")
    print(f"   Duration: {args.duration}s | Target FPS: {args.fps}")

    extractor = FrameExtractor(
        output_dir=args.output or 'data/frames',
        target_fps=args.fps
    )

    saved = extractor.extract_from_camera(
        camera_id=args.camera,
        duration_seconds=args.duration
    )

    print(f"\n✅ Collected {len(saved)} frames → {args.output or 'data/frames/'}")
    return saved


def cmd_synthetic(args):
    """Generate synthetic training data."""
    from pathguard.ml.dataset import DatasetManager

    print(f"\n🎨 Generating {args.count} synthetic training samples...")

    dm = DatasetManager(base_dir=args.output or 'data/road_defects')
    dm.create_dataset_structure()
    dm.create_synthetic_samples(num_samples=args.count)

    stats = dm.get_statistics()
    print(f"\n✅ Dataset statistics:")
    for key, val in stats.items():
        print(f"   {key}: {val}")

    return stats


def cmd_annotate(args):
    """Auto-annotate images with pre-trained detector."""
    from pathguard.ml.auto_annotate import get_auto_annotator

    print(f"\n🏷️  Auto-annotating images from {args.source}...")

    annotator = get_auto_annotator(
        detector_model_path=args.model,
        confidence_threshold=args.confidence
    )

    result = annotator.annotate_directory(
        image_dir=args.source,
        output_dir=args.output or 'data/road_defects/labels/train',
        format='yolo'
    )

    print(f"\n✅ Annotated {result.get('total_images', 0)} images")
    print(f"   Detections: {result.get('total_detections', 0)}")
    return result


def cmd_train(args):
    """Train YOLOv8 model on GPU."""
    from pathguard.ml.trainer import PathGuardTrainer, TrainingConfig
    from pathguard.ml.experiment import ExperimentTracker

    env = check_environment()
    if not env.get('ultralytics'):
        print("❌ Ultralytics required for training. Aborting.")
        return None

    config = TrainingConfig(
        model_size=args.model,
        dataset_yaml=args.dataset,
        epochs=args.epochs,
        batch_size=args.batch_size,
        image_size=args.imgsz,
        device='0' if env.get('gpu') else 'cpu',
        patience=args.patience,
        save_dir=args.save_dir or 'runs/train',
        pretrained=not args.scratch,
        amp=env.get('gpu', False),
        freeze_layers=args.freeze or None,
    )

    # Start experiment tracking
    tracker = ExperimentTracker()
    exp = tracker.start_experiment(
        name=args.name or f'pathguard_{args.model}_{datetime.now():%Y%m%d_%H%M%S}',
        model_size=args.model,
        dataset=args.dataset,
        config=vars(config) if hasattr(config, '__dict__') else {}
    )

    print(f"\n🚀 Starting training...")
    print(f"   Model:      {args.model}")
    print(f"   Dataset:    {args.dataset}")
    print(f"   Epochs:     {args.epochs}")
    print(f"   Batch Size: {config.batch_size}")
    print(f"   Device:     {'GPU (RTX 5050)' if env.get('gpu') else 'CPU'}")
    print(f"   Mixed Prec: {config.amp}")
    print(f"   Experiment: {exp.experiment_id}")
    print()

    trainer = PathGuardTrainer(config)
    results = trainer.train(resume=args.resume)

    # Log results
    if results:
        tracker.finish_experiment(
            exp.experiment_id,
            model_path=results.get('model_path'),
            final_metrics=results.get('metrics', {})
        )
        print(f"\n✅ Training complete!")
        print(f"   Best Model: {results.get('model_path', 'N/A')}")
        for key, val in results.get('metrics', {}).items():
            print(f"   {key}: {val}")
    else:
        tracker.finish_experiment(exp.experiment_id)
        print("\n⚠️  Training returned no results")

    return results


def cmd_export(args):
    """Export trained model to optimized format."""
    from pathguard.ml.trainer import PathGuardTrainer, TrainingConfig

    print(f"\n📦 Exporting model: {args.model}")
    print(f"   Format: {args.format}")
    print(f"   FP16: {args.fp16}")

    trainer = PathGuardTrainer()

    if args.format == 'all':
        results = trainer.export_all(args.model)
        print("\n✅ Exported to all formats:")
        for fmt, path in results.items():
            print(f"   {fmt}: {path}")
    elif args.format == 'tensorrt':
        path = trainer.export_tensorrt(args.model, half=args.fp16)
        print(f"\n✅ TensorRT engine: {path}")
    elif args.format == 'onnx':
        path = trainer.export_onnx(args.model, half=args.fp16)
        print(f"\n✅ ONNX model: {path}")
    else:
        print(f"❌ Unknown format: {args.format}")


def cmd_benchmark(args):
    """Benchmark inference speed."""
    from pathguard.ml.tensorrt_engine import get_inference_engine

    print(f"\n⚡ Benchmarking: {args.model}")
    print(f"   Iterations: {args.iterations}")

    engine = get_inference_engine(args.model)
    results = engine.benchmark(num_iterations=args.iterations)

    print(f"\n📊 Benchmark Results:")
    print(f"   Average: {results.get('avg_ms', 0):.2f} ms")
    print(f"   Min:     {results.get('min_ms', 0):.2f} ms")
    print(f"   Max:     {results.get('max_ms', 0):.2f} ms")
    print(f"   FPS:     {results.get('fps', 0):.1f}")

    return results


def cmd_full_pipeline(args):
    """Run the complete training pipeline end-to-end."""
    print(BANNER)
    env = check_environment()

    # Step 1: Generate synthetic data if no dataset exists
    dataset_dir = Path('data/road_defects')
    if not dataset_dir.exists() or not list((dataset_dir / 'images').rglob('*.jpg') if (dataset_dir / 'images').exists() else []):
        print("\n" + "="*60)
        print("📊 STEP 1: Generating synthetic training dataset...")
        print("="*60)
        from pathguard.ml.dataset import DatasetManager
        dm = DatasetManager()
        dm.create_dataset_structure()
        dm.create_synthetic_samples(num_samples=args.synthetic_count or 500)
        dm.generate_dataset_yaml()
        stats = dm.get_statistics()
        print(f"   Generated: {stats}")
    else:
        print("\n✅ STEP 1: Dataset exists, skipping generation.")

    # Step 2: Auto-annotate if needed
    frames_dir = Path('data/frames')
    if frames_dir.exists() and list(frames_dir.glob('*.jpg')):
        print("\n" + "="*60)
        print("🏷️  STEP 2: Auto-annotating collected frames...")
        print("="*60)
        try:
            cmd_annotate(argparse.Namespace(
                source=str(frames_dir),
                output='data/road_defects/labels/train',
                model=None,
                confidence=0.3
            ))
        except Exception as e:
            print(f"   ⚠️  Auto-annotation skipped: {e}")
    else:
        print("\n⚠️  STEP 2: No raw frames to annotate (use 'collect' first).")

    # Step 3: Train
    print("\n" + "="*60)
    print("🚀 STEP 3: Training YOLOv8 model...")
    print("="*60)
    model_size = args.model or 'yolov8s'
    train_args = argparse.Namespace(
        model=model_size,
        dataset='data/road_defects/dataset.yaml',
        epochs=args.epochs or 50,
        batch_size=args.batch_size or (16 if env.get('gpu') else 4),
        imgsz=640,
        patience=20,
        save_dir='runs/train',
        scratch=False,
        freeze=None,
        name=f'pathguard_full_{datetime.now():%Y%m%d}',
        resume=False,
    )
    results = cmd_train(train_args)

    # Step 4: Export
    if results and results.get('model_path'):
        print("\n" + "="*60)
        print("📦 STEP 4: Exporting optimized model...")
        print("="*60)
        best_model = results['model_path']
        try:
            cmd_export(argparse.Namespace(
                model=best_model, format='onnx', fp16=True
            ))
        except Exception as e:
            print(f"   ⚠️  Export failed: {e}")

        # Step 5: Benchmark
        print("\n" + "="*60)
        print("⚡ STEP 5: Benchmarking inference speed...")
        print("="*60)
        try:
            cmd_benchmark(argparse.Namespace(
                model=best_model, iterations=50
            ))
        except Exception as e:
            print(f"   ⚠️  Benchmark failed: {e}")

    print("\n" + "="*60)
    print("🎉 FULL PIPELINE COMPLETE!")
    print("="*60)
    print(f"   Next: streamlit run dashboard.py")
    print(f"   Or:   python main_engine.py --camera 0")


def main():
    """Main entry point for PathGuard ML CLI."""
    parser = argparse.ArgumentParser(
        description='PathGuard-AI ML Training Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python train.py collect --camera 0 --duration 120
  python train.py synthetic --count 500
  python train.py train --model yolov8s --epochs 100
  python train.py export --model runs/train/best.pt --format tensorrt
  python train.py benchmark --model models/best.pt
  python train.py full-pipeline
        """
    )
    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Collect command
    collect_p = subparsers.add_parser('collect', help='Collect training frames from camera')
    collect_p.add_argument('--camera', type=int, default=0)
    collect_p.add_argument('--duration', type=int, default=60)
    collect_p.add_argument('--fps', type=float, default=2.0)
    collect_p.add_argument('--output', type=str, default=None)

    # Synthetic command
    synth_p = subparsers.add_parser('synthetic', help='Generate synthetic training data')
    synth_p.add_argument('--count', type=int, default=200)
    synth_p.add_argument('--output', type=str, default=None)

    # Annotate command
    annot_p = subparsers.add_parser('annotate', help='Auto-annotate images')
    annot_p.add_argument('--source', type=str, required=True)
    annot_p.add_argument('--model', type=str, default=None)
    annot_p.add_argument('--output', type=str, default=None)
    annot_p.add_argument('--confidence', type=float, default=0.3)

    # Train command
    train_p = subparsers.add_parser('train', help='Train YOLOv8 model')
    train_p.add_argument('--model', type=str, default='yolov8s',
                         choices=['yolov8n', 'yolov8s', 'yolov8m'])
    train_p.add_argument('--dataset', type=str, default='data/road_defects/dataset.yaml')
    train_p.add_argument('--epochs', type=int, default=100)
    train_p.add_argument('--batch-size', type=int, default=16)
    train_p.add_argument('--imgsz', type=int, default=640)
    train_p.add_argument('--patience', type=int, default=20)
    train_p.add_argument('--save-dir', type=str, default=None)
    train_p.add_argument('--scratch', action='store_true', help='Train from scratch (no pretrained)')
    train_p.add_argument('--freeze', type=int, default=None, help='Freeze first N layers')
    train_p.add_argument('--name', type=str, default=None)
    train_p.add_argument('--resume', action='store_true')

    # Export command
    export_p = subparsers.add_parser('export', help='Export model to optimized format')
    export_p.add_argument('--model', type=str, required=True)
    export_p.add_argument('--format', type=str, default='onnx',
                          choices=['onnx', 'tensorrt', 'all'])
    export_p.add_argument('--fp16', action='store_true', default=True)

    # Benchmark command
    bench_p = subparsers.add_parser('benchmark', help='Benchmark inference speed')
    bench_p.add_argument('--model', type=str, required=True)
    bench_p.add_argument('--iterations', type=int, default=100)

    # Full pipeline
    full_p = subparsers.add_parser('full-pipeline', help='Run complete end-to-end pipeline')
    full_p.add_argument('--model', type=str, default='yolov8s')
    full_p.add_argument('--epochs', type=int, default=50)
    full_p.add_argument('--batch-size', type=int, default=16)
    full_p.add_argument('--synthetic-count', type=int, default=500)

    args = parser.parse_args()

    if not args.command:
        print(BANNER)
        parser.print_help()
        return

    print(BANNER)

    commands = {
        'collect': cmd_collect,
        'synthetic': cmd_synthetic,
        'annotate': cmd_annotate,
        'train': cmd_train,
        'export': cmd_export,
        'benchmark': cmd_benchmark,
        'full-pipeline': cmd_full_pipeline,
    }

    cmd_fn = commands.get(args.command)
    if cmd_fn:
        try:
            cmd_fn(args)
        except KeyboardInterrupt:
            print("\n\n⏹️  Interrupted by user.")
        except Exception as e:
            logger.error(f"Command '{args.command}' failed: {e}", exc_info=True)
            print(f"\n❌ Error: {e}")
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
