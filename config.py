# config.py
import os

# Paths
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
SAMPLES_DIR = os.path.join(DATA_DIR, "samples")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")

# Model
YOLO_MODEL = "yolo11m.pt"   

# Inference
CONFIDENCE_THRESHOLD = 0.5
IMG_SIZE_GPU = 1344  # For GPU systems (RTX 3070, etc.)
IMG_SIZE_CPU = 640   # For CPU-only systems (i5 8th gen, etc.)
USE_HALF_PRECISION = False

# Ensure dirs exist
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(SAMPLES_DIR, exist_ok=True)
