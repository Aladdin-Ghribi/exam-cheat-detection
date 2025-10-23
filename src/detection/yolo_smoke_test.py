# src/detection/yolo_smoke_test.py
from ultralytics import YOLO
import cv2
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from config import YOLO_MODEL, SAMPLES_DIR, OUTPUT_DIR
import urllib.request


def run_smoke_test():
    print("🔍 Loading YOLO model...")
    model = YOLO(YOLO_MODEL)  # Auto-downloads if not present

    # Use a sample image (or generate a dummy one if none exists)
    test_img_path = os.path.join(SAMPLES_DIR, "sample1.jpg")
    if not os.path.exists(test_img_path):
        # Download a test image if missing
        print("📥 Downloading test image...")
        urllib.request.urlretrieve(
            "https://ultralytics.com/images/zidane.jpg", test_img_path)

    print("🖼️ Running inference...")
    results = model(test_img_path)

    # Save result
    output_path = os.path.join(OUTPUT_DIR, "smoke_test_result.jpg")
    results[0].save(filename=output_path)
    print(f"✅ Smoke test passed! Result saved to {output_path}")


if __name__ == "__main__":
    run_smoke_test()
