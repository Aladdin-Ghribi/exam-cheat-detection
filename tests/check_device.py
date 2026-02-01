import torch
import sys

print("=" * 50)
print("CUDA/GPU CHECK")
print("=" * 50)

# CUDA availability
cuda_available = torch.cuda.is_available()
print(f"\nCUDA Available: {cuda_available}")

if cuda_available:
    print(f"CUDA Version: {torch.version.cuda}")
    print(f"GPU Device: {torch.cuda.get_device_name(0)}")
    print(f"GPU Count: {torch.cuda.device_count()}")
    print(f"Current Device: {torch.cuda.current_device()}")
else:
    print("⚠️  CUDA NOT AVAILABLE - Running on CPU")
    print("This will be MUCH slower for detection")

# Detector device
print("\n" + "=" * 50)
print("DETECTOR DEVICE CHECK")
print("=" * 50)

try:
    sys.path.insert(0, '.')
    from src.detection.yolo_detector import YOLODetector

    detector = YOLODetector()
    print(f"\nDetector will use: {detector.device}")
    print(f"Image size: {detector.img_size}px")

    if detector.device == 'cpu' and cuda_available:
        print("⚠️  WARNING: CUDA is available but detector is using CPU!")
    elif detector.device == 'cuda' and not cuda_available:
        print("❌ ERROR: Detector trying to use CUDA but it's not available!")
    elif detector.device == 'cuda':
        print(
            f"✅ Detector correctly using GPU with {detector.img_size}px images")
    else:
        print(
            f"ℹ️  Detector using CPU with {detector.img_size}px images (expected if no GPU)")

except Exception as e:
    print(f"Error checking detector: {e}")

print("\n" + "=" * 50)
