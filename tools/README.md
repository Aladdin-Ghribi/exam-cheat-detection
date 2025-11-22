# Testing Tools - Exam Cheat Detection

This directory contains utilities for recording test videos and replaying them through the detection pipeline for consistent testing and debugging.

## 📹 Video Capture Tool

Records webcam video with annotations and metadata for creating test scenarios.

### Usage

**Basic recording:**
```bash
python tools/video_capture.py --scenario normal_exam --description "Student taking exam normally"
```

**Custom settings:**
```bash
python tools/video_capture.py \
  --scenario phone_usage \
  --description "Student using phone during exam" \
  --resolution 1920x1080 \
  --fps 30 \
  --output-dir data/test_videos
```

### Controls

- **SPACE** - Start/Stop recording
- **a** - Add annotation at current timestamp
- **n** - Next annotation type
- **p** - Previous annotation type
- **q** - Quit

### Annotation Types

- `phone_usage` - Student using phone
- `head_turn_left` - Head turned left
- `head_turn_right` - Head turned right
- `hand_to_face` - Hand near face
- `looking_down` - Looking down at desk
- `looking_up` - Looking up/around
- `suspicious_object` - Suspicious object detected
- `normal_behavior` - Normal exam behavior

### Output

Each recording creates two files:
- `{scenario}_{timestamp}.mp4` - Video file
- `{scenario}_{timestamp}_metadata.json` - Metadata with annotations

**Metadata structure:**
```json
{
  "filename": "phone_usage_20250121_143022.mp4",
  "scenario_name": "phone_usage",
  "description": "Student using phone during exam",
  "expected_behaviors": ["phone_usage"],
  "timestamp": "2025-01-21T14:30:22",
  "resolution": [1280, 720],
  "fps": 30,
  "duration_seconds": 45.5,
  "frame_count": 1365,
  "annotations": [
    {
      "frame": 150,
      "timestamp": 5.0,
      "behavior_type": "phone_usage",
      "description": ""
    }
  ]
}
```

---

## 🔄 Video Replay Script

Processes recorded videos through the detection pipeline and generates performance reports.

### Usage

**Process single video:**
```bash
python tools/video_replay.py data/test_videos/phone_usage_20250121_143022.mp4
```

**Process with preview:**
```bash
python tools/video_replay.py data/test_videos/phone_usage_20250121_143022.mp4 --preview
```

**Batch process all videos:**
```bash
python tools/video_replay.py data/test_videos --batch --report data/test_videos/batch_report.json
```

**Disable specific features:**
```bash
python tools/video_replay.py video.mp4 --no-pose --no-tracking
```

### Options

- `--batch` - Process all videos in directory
- `--no-pose` - Disable pose detection
- `--no-tracking` - Disable object tracking
- `--no-seat-mapping` - Disable seat mapping
- `--no-output` - Don't save annotated video
- `--preview` - Show live preview during processing
- `--report PATH` - Save report to JSON file

### Output

**Annotated video:**
- `{original_name}_annotated.mp4` - Video with detection overlays

**Performance report (JSON):**
```json
{
  "video_path": "data/test_videos/phone_usage_20250121_143022.mp4",
  "processing_stats": {
    "total_frames": 1365,
    "total_time_seconds": 136.5,
    "avg_fps": 10.0,
    "avg_processing_time_ms": 100.0,
    "min_processing_time_ms": 85.2,
    "max_processing_time_ms": 150.3
  },
  "detection_stats": {
    "total_detections": 1365,
    "avg_detections_per_frame": 1.0,
    "max_detections_per_frame": 2
  },
  "suspicion_stats": {
    "avg_suspicion_score": 45.2,
    "max_suspicion_score": 100.0,
    "flagged_frames_count": 234,
    "flagged_frames": [
      {
        "frame": 150,
        "timestamp": 5.0,
        "suspicion_score": 100.0,
        "detections": 1
      }
    ]
  }
}
```

---

## 📝 Recommended Test Scenarios

### 1. Normal Exam Behavior
```bash
python tools/video_capture.py --scenario normal_exam --description "Student working normally"
```
- Student looking at paper
- Writing
- Occasional glances around
- No suspicious behavior

### 2. Phone Usage
```bash
python tools/video_capture.py --scenario phone_usage --description "Student using phone"
```
- Student pulls out phone
- Looks at phone screen
- Types on phone
- Hides phone

### 3. Head Turning
```bash
python tools/video_capture.py --scenario head_turning --description "Student looking around"
```
- Student turns head left/right
- Looks at neighbors
- Looks behind
- Returns to normal position

### 4. Hand to Face
```bash
python tools/video_capture.py --scenario hand_to_face --description "Student with hand near face"
```
- Hand covering mouth
- Hand near ear
- Scratching face
- Resting head on hand

### 5. Multiple Students
```bash
python tools/video_capture.py --scenario multiple_students --description "Multiple students in frame"
```
- 2-3 students visible
- Different behaviors
- Test tracking and seat assignment

---

## 🔬 Testing Workflow

### 1. Record Test Scenarios
```bash
# Record various scenarios
python tools/video_capture.py --scenario normal_exam
python tools/video_capture.py --scenario phone_usage
python tools/video_capture.py --scenario head_turning
```

### 2. Process Videos
```bash
# Process all recorded videos
python tools/video_replay.py data/test_videos --batch --report results.json
```

### 3. Review Results
- Check annotated videos for accuracy
- Review performance metrics in report
- Verify flagged frames match expected behaviors
- Compare suspicion scores with annotations

### 4. Iterate and Improve
- Adjust detection thresholds based on results
- Fine-tune scoring algorithms
- Optimize performance bottlenecks
- Add new test scenarios

---

## 📊 Performance Benchmarking

Use these tools to benchmark system performance:

```bash
# Test different model sizes
python tools/video_replay.py video.mp4 --report nano_report.json
# (switch model in config to small)
python tools/video_replay.py video.mp4 --report small_report.json
# (switch model to medium)
python tools/video_replay.py video.mp4 --report medium_report.json

# Compare results
python -c "
import json
for model in ['nano', 'small', 'medium']:
    with open(f'{model}_report.json') as f:
        data = json.load(f)
        print(f'{model}: {data[\"processing_stats\"][\"avg_fps\"]:.2f} FPS')
"
```

---

## 🐛 Debugging Tips

### Verify Detection Accuracy
1. Record video with known behaviors
2. Add annotations at exact timestamps
3. Process video and check flagged frames
4. Compare flagged frames with annotations

### Test Edge Cases
- Poor lighting conditions
- Multiple people in frame
- Partial occlusions
- Fast movements
- Different camera angles

### Performance Testing
- Test on different hardware (CPU vs GPU)
- Test with different model sizes
- Test with/without pose detection
- Measure frame processing times

---

## 📁 Directory Structure

```
data/test_videos/
├── normal_exam_20250121_143022.mp4
├── normal_exam_20250121_143022_metadata.json
├── normal_exam_20250121_143022_annotated.mp4
├── phone_usage_20250121_143500.mp4
├── phone_usage_20250121_143500_metadata.json
├── phone_usage_20250121_143500_annotated.mp4
└── batch_report.json
```

---

## 🎯 Use Cases

1. **Regression Testing** - Ensure new changes don't break existing functionality
2. **Performance Benchmarking** - Measure processing speed on standardized videos
3. **Accuracy Validation** - Verify detection accuracy against ground truth
4. **Debugging** - Isolate and reproduce specific detection issues
5. **Demo Creation** - Create polished demo videos for presentations
6. **Training Data** - Collect labeled examples for future ML improvements
