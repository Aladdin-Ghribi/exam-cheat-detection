# config.py
import os

# Paths
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
SAMPLES_DIR = os.path.join(DATA_DIR, "samples")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")

# Model
YOLO_MODEL = "yolo11m.pt" # best spot atm

# Inference
CONFIDENCE_THRESHOLD = 0.5
IMG_SIZE = 832 # best spot atm

# Ensure dirs exist
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(SAMPLES_DIR, exist_ok=True)
