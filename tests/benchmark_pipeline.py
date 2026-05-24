import argparse
import csv
import json
import math
import os
import platform
import statistics
import time
from datetime import datetime

import cv2
import subprocess
import shutil

# Add project root to sys.path
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import YOLO_MODEL
from src.detection.yolo_detector import YOLODetector

try:
    import psutil
except Exception:
    psutil = None

try:
    from pynvml import (
        nvmlInit,
        nvmlShutdown,
        nvmlDeviceGetHandleByIndex,
        nvmlDeviceGetName,
        nvmlDeviceGetUtilizationRates,
        nvmlDeviceGetMemoryInfo,
    )
except Exception:
    nvmlInit = None
    nvmlShutdown = None
    nvmlDeviceGetHandleByIndex = None
    nvmlDeviceGetName = None
    nvmlDeviceGetUtilizationRates = None
    nvmlDeviceGetMemoryInfo = None


def parse_source(value):
    if value.isdigit():
        return int(value)
    return value


def percentile(values, p):
    if not values:
        return None
    values_sorted = sorted(values)
    k = (len(values_sorted) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return values_sorted[int(k)]
    d0 = values_sorted[f] * (c - k)
    d1 = values_sorted[c] * (k - f)
    return d0 + d1


def compute_stats(values):
    if not values:
        return {
            'count': 0,
            'mean': None,
            'stdev': None,
            'min': None,
            'max': None,
            'median': None,
            'p95': None
        }
    return {
        'count': len(values),
        'mean': statistics.mean(values),
        'stdev': statistics.pstdev(values) if len(values) > 1 else 0.0,
        'min': min(values),
        'max': max(values),
        'median': statistics.median(values),
        'p95': percentile(values, 95)
    }


class HardwareSampler:
    def __init__(self, interval_sec=1.0):
        self.interval_sec = interval_sec
        self.last_sample = 0.0
        self.samples = []
        self.gpu_handle = None
        self.gpu_name = None
        self.gpu_ready = False
        self.smi_available = False

        if nvmlInit is not None:
            try:
                nvmlInit()
                self.gpu_handle = nvmlDeviceGetHandleByIndex(0)
                name = nvmlDeviceGetName(self.gpu_handle)
                self.gpu_name = name.decode('utf-8') if isinstance(name, bytes) else str(name)
                self.gpu_ready = True
            except Exception:
                self.gpu_ready = False
        # Detect nvidia-smi availability as a fallback when NVML isn't usable
        try:
            self.smi_available = shutil.which("nvidia-smi") is not None
        except Exception:
            self.smi_available = False

    def _query_nvidia_smi(self):
        try:
            # Query GPU utilization and memory in a compact CSV without units
            out = subprocess.check_output([
                "nvidia-smi",
                "--query-gpu=utilization.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits"
            ], stderr=subprocess.DEVNULL, timeout=2)
            text = out.decode('utf-8').strip()
            if not text:
                return None
            # take first line (GPU 0)
            first = text.splitlines()[0]
            parts = [p.strip() for p in first.split(',')]
            if len(parts) < 3:
                return None
            gpu_util = float(parts[0])
            gpu_mem_used_mb = float(parts[1])
            gpu_mem_total_mb = float(parts[2])
            gpu_mem_percent = (gpu_mem_used_mb / gpu_mem_total_mb) * 100.0 if gpu_mem_total_mb else None
            return {
                'gpu_util_percent': gpu_util,
                'gpu_mem_used_mb': gpu_mem_used_mb,
                'gpu_mem_total_mb': gpu_mem_total_mb,
                'gpu_mem_percent': gpu_mem_percent
            }
        except Exception:
            return None

    def sample(self):
        now = time.time()
        if now - self.last_sample < self.interval_sec:
            return None
        self.last_sample = now

        cpu_percent = psutil.cpu_percent(interval=None) if psutil else None
        ram_percent = psutil.virtual_memory().percent if psutil else None

        gpu_util = None
        gpu_mem_used_mb = None
        gpu_mem_total_mb = None
        gpu_mem_percent = None

        # Prefer NVML if available, otherwise fallback to nvidia-smi
        if self.gpu_ready:
            try:
                util = nvmlDeviceGetUtilizationRates(self.gpu_handle)
                mem = nvmlDeviceGetMemoryInfo(self.gpu_handle)
                gpu_util = float(util.gpu)
                gpu_mem_used_mb = float(mem.used) / (1024 * 1024)
                gpu_mem_total_mb = float(mem.total) / (1024 * 1024)
                gpu_mem_percent = (gpu_mem_used_mb / gpu_mem_total_mb) * 100.0 if gpu_mem_total_mb else None
            except Exception:
                # NVML failed mid-run; try nvidia-smi as fallback
                gpu_util = None
                if self.smi_available:
                    smi = self._query_nvidia_smi()
                    if smi:
                        gpu_util = smi.get('gpu_util_percent')
                        gpu_mem_used_mb = smi.get('gpu_mem_used_mb')
                        gpu_mem_total_mb = smi.get('gpu_mem_total_mb')
                        gpu_mem_percent = smi.get('gpu_mem_percent')
                    else:
                        gpu_util = None
        else:
            # NVML not available; try nvidia-smi if present
            if self.smi_available:
                smi = self._query_nvidia_smi()
                if smi:
                    gpu_util = smi.get('gpu_util_percent')
                    gpu_mem_used_mb = smi.get('gpu_mem_used_mb')
                    gpu_mem_total_mb = smi.get('gpu_mem_total_mb')
                    gpu_mem_percent = smi.get('gpu_mem_percent')

        sample = {
            'timestamp': now,
            'cpu_percent': cpu_percent,
            'ram_percent': ram_percent,
            'gpu_util_percent': gpu_util,
            'gpu_mem_used_mb': gpu_mem_used_mb,
            'gpu_mem_total_mb': gpu_mem_total_mb,
            'gpu_mem_percent': gpu_mem_percent
        }
        self.samples.append(sample)
        return sample

    def shutdown(self):
        if nvmlShutdown is not None and self.gpu_ready:
            try:
                nvmlShutdown()
            except Exception:
                pass


def draw_detections(frame, detections, detector):
    for det in detections:
        bbox = det.get('bbox')
        if not bbox or len(bbox) != 4:
            continue
        x1, y1, x2, y2 = map(int, bbox)
        class_id = det.get('class_id')
        if class_id == 0:
            color = (0, 255, 0)
            behavior = det.get('behavior', {})
            suspicion = behavior.get('suspicion', {})
            score = suspicion.get('smoothed', 0.0)
            label = f"person {score * 100:.0f}%"
        else:
            color = (0, 165, 255)
            label = detector._class_label(class_id)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, label, (x1, max(20, y1 - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    return frame


def main():
    parser = argparse.ArgumentParser(description="Benchmark full pipeline with metrics logging")
    parser.add_argument("--source", type=str, default="0",
                        help="Video source: camera index or file path")
    parser.add_argument("--duration", type=int, default=60,
                        help="Run duration in seconds")
    parser.add_argument("--show", action="store_true",
                        help="Show live window with overlays")
    parser.add_argument("--output-dir", type=str, default="output/metrics",
                        help="Directory to store metrics logs")
    parser.add_argument("--width", type=int, default=0,
                        help="Optional capture width (pixels)")
    parser.add_argument("--height", type=int, default=0,
                        help="Optional capture height (pixels)")
    parser.add_argument("--cpu-name", type=str, default=None,
                        help="CPU model name for reporting")
    parser.add_argument("--gpu-name", type=str, default=None,
                        help="GPU model name for reporting")
    parser.add_argument("--ram-gb", type=float, default=None,
                        help="Total RAM in GB for reporting")
    parser.add_argument("--sample-interval", type=float, default=1.0,
                        help="Hardware sampling interval in seconds")
    args = parser.parse_args()

    source = parse_source(args.source)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(args.output_dir, f"run_{timestamp}")
    os.makedirs(run_dir, exist_ok=True)

    detector = YOLODetector(enable_tracking=True, enable_pose=True)
    detector.auto_save_enabled = False

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"Error: Unable to open source {source}")
        return 1

    if args.width > 0:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    if args.height > 0:
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)

    capture_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    capture_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    capture_fps = cap.get(cv2.CAP_PROP_FPS)

    sampler = HardwareSampler(interval_sec=args.sample_interval)

    frame_metrics = []
    frames_read = 0
    start_time = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frames_read += 1

        result = detector.detect_frame(frame, metrics=frame_metrics)
        detections = result.get('detections', []) if result else []

        # Enrich latest metrics row
        if frame_metrics:
            entry = frame_metrics[-1]
            entry['timestamp'] = time.time()
            entry['num_persons'] = sum(1 for d in detections if d.get('class_id') == 0)
            entry['num_objects'] = max(0, len(detections) - entry['num_persons'])
            max_suspicion = 0.0
            for det in detections:
                behavior = det.get('behavior', {})
                suspicion = behavior.get('suspicion', {})
                max_suspicion = max(max_suspicion, suspicion.get('smoothed', 0.0))
            entry['max_suspicion'] = max_suspicion

        sample = sampler.sample()
        if sample is not None and frame_metrics:
            entry = frame_metrics[-1]
            entry['cpu_percent'] = sample.get('cpu_percent')
            entry['ram_percent'] = sample.get('ram_percent')
            entry['gpu_util_percent'] = sample.get('gpu_util_percent')
            entry['gpu_mem_used_mb'] = sample.get('gpu_mem_used_mb')
            entry['gpu_mem_total_mb'] = sample.get('gpu_mem_total_mb')
            entry['gpu_mem_percent'] = sample.get('gpu_mem_percent')

        if args.show:
            annotated = draw_detections(frame.copy(), detections, detector)
            elapsed = time.time() - start_time
            fps = frames_read / elapsed if elapsed > 0 else 0.0
            cv2.putText(annotated, f"FPS: {fps:.1f}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.imshow("Pipeline Benchmark", annotated)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        if time.time() - start_time >= args.duration:
            break

    end_time = time.time()
    elapsed = max(1e-6, end_time - start_time)

    cap.release()
    if args.show:
        cv2.destroyAllWindows()
    sampler.shutdown()

    # Collect stats
    totals = [m['total_ms'] for m in frame_metrics if not m.get('skipped')]
    infer = [m['infer_ms'] for m in frame_metrics if not m.get('skipped')]
    tracking = [m['tracking_ms'] for m in frame_metrics if not m.get('skipped')]
    pose = [m.get('pose_ms', 0.0) for m in frame_metrics if not m.get('skipped')]
    face = [m['face_ms'] for m in frame_metrics if not m.get('skipped')]
    behavior = [m['behavior_ms'] for m in frame_metrics if not m.get('skipped')]
    evidence = [m['evidence_ms'] for m in frame_metrics if not m.get('skipped')]
    post = [m['post_ms'] for m in frame_metrics if not m.get('skipped')]
    filt = [m['filter_ms'] for m in frame_metrics if not m.get('skipped')]

    processed_frames = len(totals)
    stream_fps = frames_read / elapsed
    pipeline_fps = processed_frames / elapsed
    skip_rate = 1.0 - (processed_frames / frames_read if frames_read else 0.0)

    cpu_name = args.cpu_name or platform.processor() or "Unknown"
    ram_gb = args.ram_gb
    if ram_gb is None and psutil:
        ram_gb = round(psutil.virtual_memory().total / (1024 ** 3), 2)
    gpu_name = args.gpu_name or sampler.gpu_name or "Unknown"

    summary = {
        'source': str(source),
        'duration_sec': elapsed,
        'frames_read': frames_read,
        'frames_processed': processed_frames,
        'stream_fps': stream_fps,
        'pipeline_fps': pipeline_fps,
        'skip_rate': skip_rate,
        'hardware': {
            'cpu': cpu_name,
            'gpu': gpu_name,
            'ram_gb': ram_gb,
            'os': platform.platform(),
            'python': platform.python_version()
        },
        'model': {
            'weights': YOLO_MODEL,
            'model_size_setting': detector.model_size,
            'img_size': detector.img_size,
            'device': detector.device
        },
        'capture': {
            'width': capture_width,
            'height': capture_height,
            'fps': capture_fps
        },
        'total_ms': compute_stats(totals),
        'infer_ms': compute_stats(infer),
        'post_ms': compute_stats(post),
        'filter_ms': compute_stats(filt),
        'tracking_ms': compute_stats(tracking),
        'pose_ms': compute_stats(pose),
        'face_ms': compute_stats(face),
        'behavior_ms': compute_stats(behavior),
        'evidence_ms': compute_stats(evidence)
    }

    cpu_samples = [s['cpu_percent'] for s in sampler.samples if s.get('cpu_percent') is not None]
    ram_samples = [s['ram_percent'] for s in sampler.samples if s.get('ram_percent') is not None]
    gpu_util_samples = [s['gpu_util_percent'] for s in sampler.samples if s.get('gpu_util_percent') is not None]
    gpu_mem_samples = [s['gpu_mem_used_mb'] for s in sampler.samples if s.get('gpu_mem_used_mb') is not None]

    summary['cpu_percent'] = compute_stats(cpu_samples)
    summary['ram_percent'] = compute_stats(ram_samples)
    summary['gpu_util_percent'] = compute_stats(gpu_util_samples)
    summary['gpu_mem_used_mb'] = compute_stats(gpu_mem_samples)

    # Write per-frame CSV
    frame_csv = os.path.join(run_dir, "frame_metrics.csv")
    fieldnames = [
        'timestamp', 'frame_index', 'skipped',
        'num_detections', 'num_persons', 'num_objects', 'max_suspicion',
        'infer_ms', 'post_ms', 'filter_ms', 'tracking_ms', 'pose_ms', 'face_ms',
        'behavior_ms', 'evidence_ms', 'seat_ms', 'total_ms',
        'cpu_percent', 'ram_percent', 'gpu_util_percent',
        'gpu_mem_used_mb', 'gpu_mem_total_mb', 'gpu_mem_percent'
    ]
    with open(frame_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in frame_metrics:
            writer.writerow({k: row.get(k) for k in fieldnames})

    # Write hardware samples CSV
    hardware_csv = os.path.join(run_dir, "hardware_samples.csv")
    hardware_fields = [
        'timestamp', 'cpu_percent', 'ram_percent',
        'gpu_util_percent', 'gpu_mem_used_mb', 'gpu_mem_total_mb', 'gpu_mem_percent'
    ]
    with open(hardware_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=hardware_fields)
        writer.writeheader()
        for row in sampler.samples:
            writer.writerow({k: row.get(k) for k in hardware_fields})

    # Write summary JSON
    summary_json = os.path.join(run_dir, "summary.json")
    with open(summary_json, 'w') as f:
        json.dump(summary, f, indent=2)

    # Write summary CSV
    summary_csv = os.path.join(run_dir, "summary.csv")
    with open(summary_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "mean", "stdev", "min", "max", "median", "p95"])
        for key in [
            'total_ms', 'infer_ms', 'post_ms', 'filter_ms', 'tracking_ms',
            'face_ms', 'behavior_ms', 'evidence_ms', 'cpu_percent',
            'ram_percent', 'gpu_util_percent', 'gpu_mem_used_mb'
        ]:
            stats = summary.get(key, {})
            writer.writerow([key, stats.get('mean'), stats.get('stdev'), stats.get('min'), stats.get('max'), stats.get('median'), stats.get('p95')])

    # Snapshot config if available
    config_path = os.path.join(PROJECT_ROOT, 'data', 'config.json')
    if os.path.exists(config_path):
        with open(config_path, 'r') as src, open(os.path.join(run_dir, 'config_snapshot.json'), 'w') as dst:
            dst.write(src.read())

    print(f"Metrics saved to: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
