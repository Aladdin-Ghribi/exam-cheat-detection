#!/usr/bin/env python3
"""
Evaluate labeled exam-cheat scenarios against replay reports.

This script compares frame-level labels to per-frame raw and smoothed suspicion
scores exported by tools/video_replay.py and prints precision, recall, F1, and
false-positive rate for both modes.
"""

import argparse
import csv
import json
import os
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple


@dataclass
class ConfusionMatrix:
    tp: int = 0
    fp: int = 0
    tn: int = 0
    fn: int = 0

    def add(self, predicted: bool, actual: bool) -> None:
        if predicted and actual:
            self.tp += 1
        elif predicted and not actual:
            self.fp += 1
        elif not predicted and actual:
            self.fn += 1
        else:
            self.tn += 1

    def precision(self) -> float:
        denom = self.tp + self.fp
        return self.tp / denom if denom else 0.0

    def recall(self) -> float:
        denom = self.tp + self.fn
        return self.tp / denom if denom else 0.0

    def f1(self) -> float:
        p = self.precision()
        r = self.recall()
        denom = p + r
        return 2 * p * r / denom if denom else 0.0

    def false_positive_rate(self) -> float:
        denom = self.fp + self.tn
        return self.fp / denom if denom else 0.0


def load_labels(label_csv_path: str) -> List[Dict[str, object]]:
    labels = []
    with open(label_csv_path, newline='', encoding='utf-8') as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            labels.append({
                'video_path': row['video_path'],
                'start_sec': float(row['start_sec']),
                'end_sec': float(row['end_sec']),
                'label': int(row['label']),
                'scenario': row.get('scenario', ''),
                'notes': row.get('notes', '')
            })
    return labels


def load_report(report_path: str) -> Dict[str, object]:
    with open(report_path, 'r', encoding='utf-8') as handle:
        return json.load(handle)


def _normalize_video_path(value: str) -> str:
    return os.path.normpath(str(value)).lower()


def iter_matching_frames(frame_scores: Iterable[Dict[str, object]], start_sec: float, end_sec: float):
    for frame in frame_scores:
        timestamp = float(frame['timestamp'])
        if start_sec <= timestamp < end_sec:
            yield frame


def evaluate(report: Dict[str, object], labels: List[Dict[str, object]], threshold_percent: float):
    raw_cm = ConfusionMatrix()
    smoothed_cm = ConfusionMatrix()

    # Single report mode
    frame_scores = report.get('frame_scores', [])
    if frame_scores:
        report_video_path = _normalize_video_path(report.get('video_path', ''))
        matched_labels = [
            label for label in labels
            if _normalize_video_path(label.get('video_path', '')) == report_video_path
        ]

        if not matched_labels:
            raise ValueError(
                f'No labels matched report video_path={report.get("video_path", "")}. '
                'Add rows with the same video_path as the report you are evaluating.'
            )

        for label in matched_labels:
            actual = bool(label['label'])
            matching_frames = list(iter_matching_frames(frame_scores, label['start_sec'], label['end_sec']))
            if not matching_frames:
                continue

            raw_pred = any(float(frame['raw_suspicion_score']) >= threshold_percent for frame in matching_frames)
            smoothed_pred = any(float(frame['smoothed_suspicion_score']) >= threshold_percent for frame in matching_frames)

            raw_cm.add(raw_pred, actual)
            smoothed_cm.add(smoothed_pred, actual)

        return raw_cm, smoothed_cm

    # Batch report mode
    videos = report.get('videos', [])
    if not videos:
        raise ValueError(
            'Report does not contain frame_scores or videos. Use a single replay report or batch_report.json.'
        )

    video_map = {
        _normalize_video_path(video.get('video_path', '')): video
        for video in videos
    }

    matched_any = False
    for label in labels:
        key = _normalize_video_path(label.get('video_path', ''))
        video = video_map.get(key)
        if not video:
            continue
        matched_any = True
        v_frame_scores = video.get('frame_scores', [])
        if not v_frame_scores:
            continue

        actual = bool(label['label'])
        matching_frames = list(iter_matching_frames(v_frame_scores, label['start_sec'], label['end_sec']))
        if not matching_frames:
            continue

        raw_pred = any(float(frame['raw_suspicion_score']) >= threshold_percent for frame in matching_frames)
        smoothed_pred = any(float(frame['smoothed_suspicion_score']) >= threshold_percent for frame in matching_frames)

        raw_cm.add(raw_pred, actual)
        smoothed_cm.add(smoothed_pred, actual)

    if not matched_any:
        raise ValueError(
            'No labels matched any video_path in batch report. Ensure labels use paths from batch_report.json.'
        )

    return raw_cm, smoothed_cm


def print_metrics(title: str, cm: ConfusionMatrix):
    print(f"\n{title}")
    print(f"TP: {cm.tp}  FP: {cm.fp}  TN: {cm.tn}  FN: {cm.fn}")
    print(f"Precision: {cm.precision():.4f}")
    print(f"Recall: {cm.recall():.4f}")
    print(f"F1: {cm.f1():.4f}")
    print(f"FP rate: {cm.false_positive_rate():.4f}")


def main():
    parser = argparse.ArgumentParser(description='Evaluate labeled scenarios against replay reports')
    parser.add_argument('--labels', required=True, help='CSV file with labeled intervals')
    parser.add_argument('--report', required=True, help='Replay report JSON with frame_scores')
    parser.add_argument('--threshold', type=float, default=20.0, help='Alert threshold in percent')
    args = parser.parse_args()

    labels = load_labels(args.labels)
    report = load_report(args.report)
    raw_cm, smoothed_cm = evaluate(report, labels, args.threshold)

    print(f"Evaluated labels from: {args.labels}")
    print(f"Report: {args.report}")
    print(f"Threshold: {args.threshold:.1f}%")
    print_metrics('Raw scores', raw_cm)
    print_metrics('Smoothed scores', smoothed_cm)


if __name__ == '__main__':
    main()