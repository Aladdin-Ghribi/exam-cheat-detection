#!/usr/bin/env python3
"""
Run threshold sweep for suspicion scoring evaluation.

Outputs a CSV table with confusion counts and metrics for both raw and smoothed
scores across multiple thresholds.
"""

import argparse
import csv
from pathlib import Path

from evaluate_labels import load_labels, load_report, evaluate


def parse_thresholds(value: str):
    parts = [p.strip() for p in value.split(',') if p.strip()]
    return [float(p) for p in parts]


def metric_row(mode: str, threshold: float, cm):
    return {
        'mode': mode,
        'threshold': threshold,
        'tp': cm.tp,
        'fp': cm.fp,
        'tn': cm.tn,
        'fn': cm.fn,
        'precision': round(cm.precision(), 4),
        'recall': round(cm.recall(), 4),
        'f1': round(cm.f1(), 4),
        'fp_rate': round(cm.false_positive_rate(), 4),
    }


def main():
    parser = argparse.ArgumentParser(description='Threshold sweep for suspicion score evaluation')
    parser.add_argument('--labels', required=True, help='CSV labels file')
    parser.add_argument('--report', required=True, help='Single report JSON or batch report JSON')
    parser.add_argument('--thresholds', default='10,15,20,25,30',
                        help='Comma-separated threshold values (percent)')
    parser.add_argument('--out', default='reports/threshold_sweep.csv',
                        help='Output CSV file path')
    args = parser.parse_args()

    labels = load_labels(args.labels)
    report = load_report(args.report)
    thresholds = parse_thresholds(args.thresholds)

    rows = []
    for threshold in thresholds:
        raw_cm, smoothed_cm = evaluate(report, labels, threshold)
        rows.append(metric_row('raw', threshold, raw_cm))
        rows.append(metric_row('smoothed', threshold, smoothed_cm))

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        'mode', 'threshold', 'tp', 'fp', 'tn', 'fn',
        'precision', 'recall', 'f1', 'fp_rate'
    ]

    with out_path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f'Wrote threshold sweep: {out_path}')
    print('')
    print('mode      thr   TP FP TN FN   precision recall   f1     fp_rate')
    for row in rows:
        print(
            f"{row['mode']:<9} {row['threshold']:>4.0f}   "
            f"{row['tp']:>2} {row['fp']:>2} {row['tn']:>2} {row['fn']:>2}   "
            f"{row['precision']:.4f}    {row['recall']:.4f}  "
            f"{row['f1']:.4f}  {row['fp_rate']:.4f}"
        )


if __name__ == '__main__':
    main()
