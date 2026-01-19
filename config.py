# config.py
import os

# Paths
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
SAMPLES_DIR = os.path.join(DATA_DIR, "samples")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")

# Model Selection
YOLO_MODEL = "yolo11l.pt"  # Upgrade to Large for distance
YOLO_MODEL_OPTIONS = {
    "nano": "yolo11n.pt",
    "small": "yolo11s.pt",
    "medium": "yolo11m.pt",
    "large": "yolo11l.pt"
}

# Inference
CONFIDENCE_THRESHOLD = 0.5
IMG_SIZE_GPU = 1024    # Optimal for RTX 3070 stability at 1080p
IMG_SIZE_CPU = 640
IMG_SIZE_NANO = 320
USE_HALF_PRECISION = False

# Performance Optimization
ENABLE_FRAME_SKIPPING = True
FRAME_SKIP_THRESHOLD_MS = 100
MAX_FRAME_SKIP = 3

# Ensure dirs exist
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(SAMPLES_DIR, exist_ok=True)
