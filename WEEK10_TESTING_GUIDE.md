# Week 10 Testing Guide - Quick Start

## 🎯 5-Minute Quick Test

### Test 1: Record Your First Video (2 minutes)

```bash
# Start the capture tool
python tools/video_capture.py --scenario my_first_test
```

**What to do:**
1. Window opens showing your webcam
2. Press **SPACE** to start recording
3. Do something in front of camera (wave, turn head, use phone)
4. Press **SPACE** again to stop (after 10-15 seconds)
5. Press **q** to quit

**Expected output:**
```
📹 Started recording: my_first_test
   Output: data/test_videos/my_first_test_20250122_152045.mp4
✅ Recording stopped
   Duration: 12.5s
   Frames: 375
```

---

### Test 2: Process the Video (2 minutes)

```bash
# Find your video file
dir data\test_videos\my_first_test*.mp4

# Process it
python tools/video_replay.py data/test_videos/my_first_test_20250122_152045.mp4
```

**Expected output:**
```
📹 Processing video: my_first_test_20250122_152045.mp4
⏳ Processing frames...
   Progress: 100%
✅ Processing complete!
   Total time: 12.5s
   Average FPS: 10.2
   Flagged frames: 5
```

**Check the results:**
```bash
# Open the annotated video
data\test_videos\my_first_test_20250122_152045_annotated.mp4
```

---

### Test 3: Add Annotations (1 minute)

```bash
# Record with annotations
python tools/video_capture.py --scenario phone_test
```

**What to do:**
1. Press **SPACE** to start
2. Pull out your phone
3. Press **a** to add annotation (marks "phone_usage")
4. Press **n** to change annotation type
5. Press **a** again to mark different behavior
6. Press **SPACE** to stop
7. Press **q** to quit

**Check metadata:**
```bash
# View the metadata file
type data\test_videos\phone_test_*_metadata.json
```

---

## 📋 Complete Testing Scenarios

### Scenario 1: Normal Exam Behavior

```bash
python tools/video_capture.py --scenario normal_exam --description "Student working normally"
```

**Record this:**
- Sit normally
- Look at desk/paper
- Write/type
- Occasional glances up
- Duration: 30 seconds

**Process it:**
```bash
python tools/video_replay.py data/test_videos/normal_exam_*.mp4
```

**Expected:** Low suspicion scores (< 20)

---

### Scenario 2: Phone Usage

```bash
python tools/video_capture.py --scenario phone_usage --description "Using phone during exam"
```

**Record this:**
1. Start recording
2. Pull out phone (press **a** to annotate)
3. Look at phone screen
4. Type on phone
5. Put phone away
6. Duration: 20 seconds

**Process it:**
```bash
python tools/video_replay.py data/test_videos/phone_usage_*.mp4
```

**Expected:** High suspicion scores (80-100) when phone is visible

---

### Scenario 3: Head Turning

```bash
python tools/video_capture.py --scenario head_turning --description "Looking around"
```

**Record this:**
1. Start recording
2. Turn head left (press **a**)
3. Press **n** then **a** for next annotation
4. Turn head right
5. Look behind
6. Duration: 20 seconds

**Process it:**
```bash
python tools/video_replay.py data/test_videos/head_turning_*.mp4
```

**Expected:** Medium suspicion scores (30-60) during head turns

---

## 🔬 Advanced Testing

### Batch Processing Test

```bash
# Record 3 different scenarios
python tools/video_capture.py --scenario test1
python tools/video_capture.py --scenario test2
python tools/video_capture.py --scenario test3

# Process all at once
python tools/video_replay.py data/test_videos --batch --report batch_results.json
```

**Check results:**
```bash
type batch_results.json
```

---

### Performance Benchmark Test

```bash
# Test with pose detection
python tools/video_replay.py data/test_videos/normal_exam_*.mp4 --report with_pose.json

# Test without pose detection
python tools/video_replay.py data/test_videos/normal_exam_*.mp4 --no-pose --report no_pose.json

# Compare (manual check)
type with_pose.json | findstr avg_fps
type no_pose.json | findstr avg_fps
```

---

### Preview Mode Test

```bash
# Watch processing in real-time
python tools/video_replay.py data/test_videos/phone_usage_*.mp4 --preview
```

**What you'll see:**
- Live video with detections
- Bounding boxes
- Suspicion scores
- Press **q** to stop

---

## ✅ Verification Checklist

After testing, verify these files exist:

### Recorded Videos:
```bash
dir data\test_videos\*.mp4
```
Should show: `my_first_test_*.mp4`, `phone_usage_*.mp4`, etc.

### Metadata Files:
```bash
dir data\test_videos\*_metadata.json
```
Should show: `my_first_test_*_metadata.json`, etc.

### Annotated Videos:
```bash
dir data\test_videos\*_annotated.mp4
```
Should show: `my_first_test_*_annotated.mp4`, etc.

### Reports:
```bash
dir *.json
```
Should show: `batch_results.json`, `with_pose.json`, etc.

---

## 🐛 Troubleshooting

### Problem: "Could not open webcam"
**Solution:**
```bash
# Check if webcam is being used by another app
# Close other apps using camera
# Try again
```

### Problem: "Module not found"
**Solution:**
```bash
# Make sure you're in the project directory
cd c:\Users\Mega_pc\Desktop\Exam-cheat-detection

# Verify Python path
python tools/test_tools.py
```

### Problem: Video is too dark/bright
**Solution:**
```bash
# Adjust your lighting
# Or record in different location
```

### Problem: Processing is very slow
**Solution:**
```bash
# Use smaller model
# Edit config.py: YOLO_MODEL = "yolo11n.pt"

# Or disable pose detection
python tools/video_replay.py video.mp4 --no-pose
```

---

## 📊 Understanding the Output

### Processing Stats:
```json
{
  "avg_fps": 10.5,              // How fast it processes (higher = better)
  "avg_processing_time_ms": 95, // Time per frame (lower = better)
  "total_frames": 375            // Total frames processed
}
```

### Detection Stats:
```json
{
  "total_detections": 375,       // Total objects detected
  "avg_detections_per_frame": 1, // Average objects per frame
  "max_detections_per_frame": 2  // Most objects in one frame
}
```

### Suspicion Stats:
```json
{
  "avg_suspicion_score": 25.5,   // Average suspicion (0-100)
  "max_suspicion_score": 100,    // Highest suspicion
  "flagged_frames_count": 45     // How many frames flagged
}
```

---

## 🎯 Success Criteria

Your Week 10 implementation is working if:

- ✅ Can record videos with webcam
- ✅ Can add annotations during recording
- ✅ Metadata files are created
- ✅ Can process single videos
- ✅ Can batch process multiple videos
- ✅ Annotated videos are generated
- ✅ Performance reports are created
- ✅ Suspicion scores match expected behaviors

---

## 📝 Quick Commands Reference

```bash
# Record video
python tools/video_capture.py --scenario <name>

# Process video
python tools/video_replay.py <video_path>

# Batch process
python tools/video_replay.py data/test_videos --batch

# With preview
python tools/video_replay.py <video_path> --preview

# Save report
python tools/video_replay.py <video_path> --report results.json

# No pose detection
python tools/video_replay.py <video_path> --no-pose

# Test installation
python tools/test_tools.py

# List videos
dir data\test_videos\*.mp4
```

---

## 🎓 Next Steps

After completing these tests:

1. **Create a test suite** - Record 5 standard scenarios
2. **Baseline your system** - Process all and save reports
3. **Make improvements** - Optimize code, adjust thresholds
4. **Re-test** - Compare new results with baseline
5. **Document findings** - Note what works best

---

**Ready to start?** Run the first test now:
```bash
python tools/video_capture.py --scenario my_first_test
```
