# Technology Stack

## Programming Languages
- **Python 3.8+** - Primary development language
- **JavaScript** - Frontend interactivity and WebSocket communication
- **HTML/CSS** - Web interface structure and styling

## Core Dependencies

### Computer Vision & AI
- **ultralytics>=8.3.0** - YOLO model implementation and training
- **mediapipe** - Google's pose estimation and face detection
- **opencv-python** - Image processing and video handling
- **torch>=1.8** - PyTorch deep learning framework
- **numpy** - Numerical computations and array operations

### Web Framework
- **Flask** - Lightweight web application framework
- **Flask-SocketIO** - Real-time bidirectional communication
- **Jinja2** - Template engine (included with Flask)

### Model Files
- **yolo11m.pt** - Medium YOLO model (primary)
- **yolo11n.pt** - Nano YOLO model (lightweight option)
- **yolo11s.pt** - Small YOLO model (balanced option)

## Development Commands

### Environment Setup
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Testing & Validation
```powershell
# YOLO smoke test
python src/detection/yolo_smoke_test.py

# Pose detection tests
python test_pose_metrics.py
python test_webcam_pose.py

# Seat management tests
python test_exam_seats.py
python test_webcam_seats.py
```

### Application Launch
```powershell
# Web dashboard
python src/cheat_detection_web_app/app.py

# Alternative with Streamlit (if available)
streamlit run dashboard.py
```

## Configuration Management
- **config.py** - Centralized settings
  - Model paths and selection
  - Confidence thresholds (default: 0.5)
  - Image processing size (1344px)
  - Directory structure definitions

## Hardware Requirements
- **RAM**: 16GB+ recommended for real-time processing
- **GPU**: Optional but recommended for faster inference
- **Camera**: Webcam or CCTV feed for live monitoring
- **Storage**: Minimal (only flagged events retained)