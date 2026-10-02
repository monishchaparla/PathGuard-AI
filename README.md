# 🛡️ PathGuard-AI

**Autonomous Road Infrastructure Quality & Contractual Compliance Engine**

Detects road defects from live dashcam footage, computes real-world dimensions,
deduplicates via Uber H3 spatial indexing, and enforces contractor liability
under MoRTH/eMARG/CPWD regulations — all running locally on your GPU.

---

## Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| GPU | NVIDIA GTX 1650 (4 GB) | RTX 5050+ (8 GB VRAM) |
| CPU | 4-core | i5-13th Gen+ (8-core) |
| RAM | 8 GB | 16 GB |
| Camera | Any USB webcam | Wide-angle action cam |

---

## Project Structure

```
PATH_GUARD/
├── config/                  # Configuration files
│   └── default_config.yaml  #   Default settings (camera, GPU, training, DLP rules)
├── data/                    # Training datasets (generated / collected)
├── docs/                    # Documentation & reference PDFs
├── models/                  # Trained ML model weights
├── captures/                # Saved defect images from live detection
├── runs/                    # YOLOv8 training run outputs
├── experiments/             # ML experiment tracking logs
├── tenders/                 # PDF tender contracts for DLP parsing
├── scripts/                 # Setup & database scripts
│   ├── init_db.sql          #   PostGIS schema initialization
│   └── setup_gpu.ps1        #   One-click GPU environment setup
├── pathguard/               # Core Python package
│   ├── __init__.py
│   ├── config.py            #   YAML config loader with env overrides
│   ├── vision.py            #   Module 1: CV pipeline + enhanced ML detection
│   ├── spatial.py           #   Module 2: Uber H3 geospatial indexing
│   ├── database.py          #   Module 2: PostGIS deduplication engine
│   ├── contracts.py         #   Module 3: DLP aging & liability engine
│   ├── notices.py           #   Module 4: Statutory notice generation
│   ├── pdf_ingest.py        #   Tender document ingestion (PyMuPDF)
│   ├── gps_relay.py         #   GPS data interface (USB / simulated)
│   └── ml/                  #   Machine Learning subsystem
│       ├── __init__.py
│       ├── trainer.py       #     YOLOv8 training pipeline
│       ├── dataset.py       #     Dataset management & synthetic generation
│       ├── augmentation.py  #     Advanced data augmentation
│       ├── auto_annotate.py #     SAM2 auto-annotation pipeline
│       ├── depth_estimator.py #   MiDaS monocular depth estimation
│       ├── tensorrt_engine.py #   TensorRT / ONNX optimized inference
│       └── experiment.py    #     Experiment tracking
├── main_engine.py           # Orchestration engine (camera → detection → DB → notice)
├── dashboard.py             # Streamlit live in-car dashboard
├── train.py                 # ML training CLI
├── docker-compose.yml       # PostGIS database container
├── pyproject.toml           # Project metadata
├── requirements.txt         # Python dependencies
└── .gitignore
```

---

## Quick Start

### 1. Setup GPU Environment
```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_gpu.ps1
.\venv\Scripts\Activate.ps1
```

### 2. Start Database (optional)
```bash
docker-compose up -d
```

### 3. Train a Model (or use synthetic data)
```bash
python train.py full-pipeline
```

### 4. Run Live Detection
```bash
python main_engine.py --camera 0
```

### 5. Launch Dashboard
```bash
streamlit run dashboard.py
```

---

## Defect Classes (7-class taxonomy)

| ID | Type | IRC Reference |
|----|------|---------------|
| 0 | Pothole | IRC:82-2015 §3.1 |
| 1 | Longitudinal Crack | IRC:82-2015 §3.2 |
| 2 | Transverse Crack | IRC:82-2015 §3.3 |
| 3 | Alligator Crack | IRC:82-2015 §3.4 |
| 4 | Rutting | IRC:82-2015 §3.5 |
| 5 | Raveling | IRC:82-2015 §3.6 |
| 6 | Patching | IRC:82-2015 §3.7 |

---

## Legal Framework

- **MoRTH EPC**: 5-year DLP (bituminous), 10-year (concrete)
- **eMARG PMGSY**: 5-year DLP with bi-monthly geo-tagged inspections
- **CPWD**: 1-year DLP for civil works
- **Notice**: 14 business-day cure period under Clause 17

---

## License

Built for the Student Hackathon. All rights reserved.
