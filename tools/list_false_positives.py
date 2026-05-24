#!/usr/bin/env python3
"""
List false-positive labeled clips from a batch report.

Outputs a CSV with columns: video_path,start_sec,end_sec,mode,timestamps
where timestamps is a semicolon-separated list of flagged frame timestamps.
"""
import argparse
import csv
import json
import os
from typing import List


def _normalize_video_path(value: str) -> str:
    return os.path.normpath(str(value)).lower()


def iter_matching_frames(frame_scores, start_sec: float, end_sec: float):
    for frame in frame_scores:
        ts = float(frame.get('timestamp', 0))
        if start_sec <= ts < end_sec:
            yield frame


def find_false_positives(labels_path: str, report_path: str, threshold: float, mode: str):
    with open(labels_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        labels = list(reader)

    with open(report_path, 'r', encoding='utf-8') as f:
        report = json.load(f)

    videos = report.get('videos', [])
    video_map = {_normalize_video_path(v.get('video_path', '')): v for v in videos}

    rows = []
    for label in labels:
        actual = int(label.get('label', '0'))
        if actual != 0:
            continue  # we only want negatives that were predicted positive

        key = _normalize_video_path(label.get('video_path', ''))
        video = video_map.get(key)
        if not video:
            continue
        frame_scores = video.get('frame_scores', [])
        if not frame_scores:
            continue

        start_sec = float(label.get('start_sec', 0))
        end_sec = float(label.get('end_sec', 0))
        matching = list(iter_matching_frames(frame_scores, start_sec, end_sec))
        if not matching:
            continue

        timestamps = []
        for frame in matching:
            if mode in ('raw', 'both'):
                if float(frame.get('raw_suspicion_score', 0)) >= threshold:
                    timestamps.append(str(frame.get('timestamp')))
                    continue
            if mode in ('smoothed', 'both'):
                if float(frame.get('smoothed_suspicion_score', 0)) >= threshold:
                    timestamps.append(str(frame.get('timestamp')))

        if timestamps:
            rows.append({
                'video_path': label.get('video_path', ''),
                'start_sec': label.get('start_sec', ''),
                'end_sec': label.get('end_sec', ''),
                'mode': mode,
                'timestamps': ';'.join(sorted(set(timestamps), key=float))
            })

    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--labels', required=True)
    parser.add_argument('--report', required=True)
    parser.add_argument('--threshold', type=float, default=30.0)
    parser.add_argument('--mode', choices=['raw', 'smoothed', 'both'], default='smoothed')
    parser.add_argument('--out', help='CSV output path', default=None)
    args = parser.parse_args()

    rows = find_false_positives(args.labels, args.report, args.threshold, args.mode)

    if args.out:
        with open(args.out, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['video_path', 'start_sec', 'end_sec', 'mode', 'timestamps'])
            writer.writeheader()
            for r in rows:
                writer.writerow(r)
    else:
        writer = csv.DictWriter(__import__('sys').stdout, fieldnames=['video_path', 'start_sec', 'end_sec', 'mode', 'timestamps'])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


if __name__ == '__main__':
    main()
