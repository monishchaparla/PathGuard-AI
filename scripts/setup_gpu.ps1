# PathGuard-AI GPU Environment Setup for NVIDIA RTX 5050
# Run: powershell -ExecutionPolicy Bypass -File scripts/setup_gpu.ps1

$ErrorActionPreference = "Stop"
$PYTHON = "C:\Users\chapa\.local\bin\python3.14.exe"

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  PathGuard-AI GPU Environment Setup" -ForegroundColor Cyan
Write-Host "  Target: NVIDIA RTX 5050 (8GB VRAM)" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# Check NVIDIA GPU
Write-Host "[1/6] Checking GPU..." -ForegroundColor Yellow
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
Write-Host ""

# Create virtual environment
Write-Host "[2/6] Creating virtual environment..." -ForegroundColor Yellow
if (-Not (Test-Path "venv")) {
    & $PYTHON -m venv venv
    Write-Host "  Virtual environment created." -ForegroundColor Green
} else {
    Write-Host "  Virtual environment already exists." -ForegroundColor Green
}

# Activate venv
$VENV_PIP = ".\venv\Scripts\pip.exe"
$VENV_PYTHON = ".\venv\Scripts\python.exe"

# Install PyTorch with CUDA
Write-Host "[3/6] Installing PyTorch with CUDA support..." -ForegroundColor Yellow
& $VENV_PIP install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

# Install Ultralytics (YOLOv8)
Write-Host "[4/6] Installing Ultralytics YOLOv8..." -ForegroundColor Yellow
& $VENV_PIP install ultralytics

# Install all project dependencies
Write-Host "[5/6] Installing project dependencies..." -ForegroundColor Yellow
& $VENV_PIP install -r requirements.txt

# Verify GPU setup
Write-Host "[6/6] Verifying GPU configuration..." -ForegroundColor Yellow
& $VENV_PYTHON -c @"
import torch
print(f'  PyTorch Version: {torch.__version__}')
print(f'  CUDA Available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'  GPU: {torch.cuda.get_device_name(0)}')
    print(f'  VRAM: {torch.cuda.get_device_properties(0).total_mem / 1024**3:.1f} GB')
    print(f'  CUDA Version: {torch.version.cuda}')
    # Quick benchmark
    import time
    x = torch.randn(1000, 1000, device='cuda')
    torch.cuda.synchronize()
    t0 = time.time()
    for _ in range(100):
        y = x @ x
    torch.cuda.synchronize()
    ms = (time.time() - t0) * 10
    print(f'  GPU MatMul Speed: {ms:.1f} ms per 1000x1000')
else:
    print('  WARNING: CUDA not available! Check driver installation.')

try:
    from ultralytics import YOLO
    print(f'  Ultralytics: OK')
except: print('  Ultralytics: FAILED')

try:
    import cv2
    print(f'  OpenCV: {cv2.__version__}')
except: print('  OpenCV: FAILED')

try:
    import h3
    print(f'  H3: OK')
except: print('  H3: FAILED')

try:
    import streamlit
    print(f'  Streamlit: {streamlit.__version__}')
except: print('  Streamlit: FAILED')
"@

Write-Host ""
Write-Host "=============================================" -ForegroundColor Green
Write-Host "  Setup Complete!" -ForegroundColor Green
Write-Host "  Activate: .\venv\Scripts\Activate.ps1" -ForegroundColor Green
Write-Host "  Train:    python -m pathguard.ml.trainer" -ForegroundColor Green
Write-Host "  Run:      python main_engine.py" -ForegroundColor Green
Write-Host "  Dashboard: streamlit run dashboard.py" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
