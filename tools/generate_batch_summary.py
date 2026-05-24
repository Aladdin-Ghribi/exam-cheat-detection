import json
import csv
from pathlib import Path

BATCH_PATH = Path('reports/batch_report.json')
OUT_CSV = Path('reports/batch_summary.csv')

if not BATCH_PATH.exists():
    print(f'Batch report not found: {BATCH_PATH}')
    raise SystemExit(1)

with open(BATCH_PATH, 'r', encoding='utf-8') as f:
    batch = json.load(f)

videos = batch.get('videos', [])
if not videos:
    print('No videos found in batch report')
    raise SystemExit(1)

fieldnames = [
    'video_path', 'total_frames', 'avg_fps', 'avg_processing_time_ms',
    'total_detections', 'avg_detections_per_frame', 'flagged_frames_count', 'avg_suspicion_score'
]

rows = []
frames_total = 0
sum_weighted_fps = 0.0
sum_weighted_proc = 0.0
sum_flagged = 0
sum_weighted_suspicion = 0.0

for v in videos:
    vp = v.get('video_path')
    ps = v.get('processing_stats', {})
    ds = v.get('detection_stats', {})
    ss = v.get('suspicion_stats', {})

    total_frames = int(ps.get('total_frames') or 0)
    avg_fps = float(ps.get('avg_fps') or 0.0)
    avg_proc = float(ps.get('avg_processing_time_ms') or 0.0)
    total_dets = int(ds.get('total_detections') or 0)
    avg_dets_pf = float(ds.get('avg_detections_per_frame') or 0.0)
    flagged = int(ss.get('flagged_frames_count') or 0)
    avg_susp = float(ss.get('avg_suspicion_score') or 0.0)

    rows.append({
        'video_path': vp,
        'total_frames': total_frames,
        'avg_fps': round(avg_fps, 3),
        'avg_processing_time_ms': round(avg_proc, 3),
        'total_detections': total_dets,
        'avg_detections_per_frame': round(avg_dets_pf, 3),
        'flagged_frames_count': flagged,
        'avg_suspicion_score': round(avg_susp, 3)
    })

    frames_total += total_frames
    sum_weighted_fps += avg_fps * total_frames
    sum_weighted_proc += avg_proc * total_frames
    sum_flagged += flagged
    sum_weighted_suspicion += avg_susp * total_frames

# Write CSV
OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for r in rows:
        writer.writerow(r)

# Compute overall weighted metrics
if frames_total > 0:
    weighted_avg_fps = sum_weighted_fps / frames_total
    weighted_avg_proc = sum_weighted_proc / frames_total
    weighted_avg_susp = sum_weighted_suspicion / frames_total
    flagged_rate = sum_flagged / frames_total
else:
    weighted_avg_fps = weighted_avg_proc = weighted_avg_susp = flagged_rate = 0.0

summary = {
    'videos_count': len(videos),
    'frames_total': frames_total,
    'weighted_avg_fps': round(weighted_avg_fps, 3),
    'weighted_avg_processing_time_ms': round(weighted_avg_proc, 3),
    'weighted_avg_suspicion_score': round(weighted_avg_susp, 3),
    'total_flagged_frames': sum_flagged,
    'flagged_rate': round(flagged_rate, 4)
}

print('Wrote:', OUT_CSV)
print('Summary:')
for k, v in summary.items():
    print(f'  {k}: {v}')

# Also save summary JSON
with open(OUT_CSV.with_suffix('.summary.json'), 'w', encoding='utf-8') as f:
    json.dump(summary, f, indent=2)

print('Done')
