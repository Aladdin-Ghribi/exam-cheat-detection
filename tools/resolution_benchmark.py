#!/usr/bin/env python3
"""
Benchmark the detector at specific input resolutions.

This script replays a folder of test videos, resizes each frame to a target
resolution before inference, and reports only average FPS and average latency.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import cv2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.detection.yolo_detector import YOLODetector


def parse_resolution(value: str):
    width, height = value.lower().split('x')
    return int(width), int(height)


def run_benchmark(video_dir: str, resolution: tuple[int, int], no_output: bool = True):
    detector = YOLODetector(enable_pose=True, enable_tracking=True, enable_seat_mapping=False)
    results = []

    for video_path in sorted(Path(video_dir).glob('*.mp4')):
        if '_annotated' in str(video_path):
            continue

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            continue

        frame_times = []
        frame_count = 0
        start = time.time()

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.resize(frame, resolution)
            frame_start = time.time()
            _ = detector.detect_frame(frame)
            frame_times.append(time.time() - frame_start)
            frame_count += 1

        cap.release()

        elapsed = time.time() - start
        avg_fps = frame_count / elapsed if elapsed > 0 else 0.0
        avg_latency_ms = (sum(frame_times) / len(frame_times)) * 1000 if frame_times else 0.0

        results.append({
            'video_path': str(video_path),
            'frames': frame_count,
            'avg_fps': avg_fps,
            'avg_latency_ms': avg_latency_ms,
            'elapsed_seconds': elapsed,
        })

    if not results:
        return {
            'resolution': f'{resolution[0]}x{resolution[1]}',
            'avg_fps': 0.0,
            'avg_latency_ms': 0.0,
            'videos': 0,
        }

    total_frames = sum(r['frames'] for r in results)
    weighted_fps = sum(r['avg_fps'] * r['frames'] for r in results) / total_frames
    weighted_latency = sum(r['avg_latency_ms'] * r['frames'] for r in results) / total_frames

    return {
        'resolution': f'{resolution[0]}x{resolution[1]}',
        'avg_fps': weighted_fps,
        'avg_latency_ms': weighted_latency,
        'videos': len(results),
        'frames': total_frames,
    }


def main():
    parser = argparse.ArgumentParser(description='Benchmark detector at a fixed resolution')
    parser.add_argument('video_dir', help='Directory containing input videos')
    parser.add_argument('--resolution', required=True, help='Target resolution WIDTHxHEIGHT')
    parser.add_argument('--out', help='Optional JSON output path')
    args = parser.parse_args()

    resolution = parse_resolution(args.resolution)
    summary = run_benchmark(args.video_dir, resolution)

    print(f"Resolution: {summary['resolution']}")
    print(f"Avg FPS: {summary['avg_fps']:.2f}")
    print(f"Avg latency (ms): {summary['avg_latency_ms']:.2f}")

    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)


if __name__ == '__main__':
    main()
