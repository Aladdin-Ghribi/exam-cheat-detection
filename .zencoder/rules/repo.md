---
description: Repository Information Overview
alwaysApply: true
---

# Real-Time Cheating Detection System Information

## Summary
This repository implements a vision-driven proctoring prototype that combines Ultralytics YOLO object detection, MediaPipe pose landmarks, heuristic tracking, and a Flask-SocketIO dashboard to surface possible cheating behaviors during exams. The backend streams annotated frames and structured metrics to a single-page web client capable of ingesting webcam feeds or uploaded media while preserving privacy by retaining only flagged evidence. Operational guides emphasize rapid iteration toward a classroom-ready tool with seat mapping, temporal smoothing, and future roadmap items such as head-pose scoring and cheat likelihood aggregation.

## Structure
- **src/**: Python package root with detection logic, web application, and shared utilities.
- **src/cheat_detection_web_app/**: Flask-SocketIO server (`app.py`), Jinja2 template (`templates/index.html`), and static assets (Socket.IO-driven `static/script.js`, styling in `static/style.css`).
- **src/detection/**: Core computer-vision modules (`yolo_detector.py`, `object_tracker.py`, `exam_seat_manager.py`, `pose_detector.py`) plus package initializers.
- **src/utils/**: Placeholder package for shared helpers; currently empty scaffold for future utilities.
- **config.py**: Central configuration for model paths, inference parameters, and auto-created data/output directories.
- **data/**: Input assets, including `samples/` and a zipped archive (`samples - Copy.zip`) for reproducible experiments.
- **output/**: Default location for annotated media and generated artifacts such as seat-mapped recordings.
- **tests (root scripts)**: Manual verification entry points (`test_exam_seats.py`, `test_optimized_pose_detection.py`, `test_webcam_pose.py`, `test_webcam_seats.py`) that exercise detection components via CLI arguments.
- **docs/**: Written guides (notably `Cheating-Detection-System-Guide.md`) detailing architecture, runbooks, and export instructions.
- **venv/**: Local Python virtual environment directory (excluded from version control in typical workflows).
- **YOLO weight files**: `yolo11n.pt`, `yolo11s.pt`, `yolo11m.pt` stored at repository root for offline inference.
- **Ancillary assets**: `output_exam_seats.mp4` demo clip and `run_ngrok` launcher used for tunneled demos.

## Language & Runtime
**Language**: Python (core application and tooling).  
**Version**: README and docs target Python 3.8 or newer CPython interpreters; torch-based workflows benefit from GPU-enabled builds when available.  
**Runtime**: Long-running components execute under Flask-SocketIO with either the default threading engine or an async worker such as eventlet/gevent when installed.  
**Build System**: No compiled build step; direct script invocation orchestrates the runtime.  
**Package Manager**: pip using `requirements.txt`; repository practice relies on a virtual environment (`python -m venv venv`).

## Dependencies
**Main Dependencies**:
- `ultralytics>=8.3.0`: Provides YOLO model loading and inference used throughout `src/detection/yolo_detector.py`.
- `torch>=1.8`: Deep learning runtime required by Ultralytics models; GPU installations accelerate inference.
- `opencv-python`: Supplies frame capture, drawing primitives, and video IO across detection and test scripts.
- `numpy`: Backbone for numeric operations, centroid calculations, and pose smoothing buffers.
- `mediapipe`: Delivers the pose estimation pipeline wrapped by `PoseDetector` for head/shoulder/hand landmarks.
- `Flask` & `Flask-SocketIO`: Web server and realtime transport stack powering `src/cheat_detection_web_app/app.py` routes and Socket.IO events.
- `python-socketio`, `eventlet` or `gevent`: Required by Flask-SocketIO for websocket transport and async workers (implicit runtime dependency; ensure installation alongside Flask).
- `pyngrok`: Utilized by the `run_ngrok` helper to expose the dashboard over secure tunnels when remote demos are needed.

**Development & Operational Notes**:
- No explicit dev-only section exists in `requirements.txt`; linting, formatting, and testing tools must be installed manually if desired.
- Browser client depends on CDN-hosted Socket.IO 4.7.2 (see `templates/index.html`), so outbound internet access is necessary unless the asset is vendored.
- Pretrained YOLO weights bundled at root must match the `YOLO_MODEL` path configured in `config.py` to avoid runtime load failures.

## Build & Installation
```bash
python -m venv venv
venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Usage & Operations
1. **Launch the realtime dashboard**: `python src\cheat_detection_web_app\app.py` (ensure certificates exist if running the SSL-enabled block or switch to the commented non-SSL line for local development).
2. **Access the UI**: Navigate to `http://localhost:5000`, choose webcam streaming or upload media, and monitor annotated frames, metrics, and seat assignments live.
3. **Run tunneled demos**: Execute `python run_ngrok` after installing `pyngrok` and configuring auth tokens to expose the service externally.
4. **Configure inference**: Adjust `YOLO_MODEL`, `CONFIDENCE_THRESHOLD`, and `IMG_SIZE` within `config.py` to experiment with different weights or precision/recall trade-offs; directories are auto-created when the module is imported.
5. **Swap YOLO weights**: Replace or update `yolo11*.pt` files and keep the file name aligned with `YOLO_MODEL` to avoid FileNotFoundError at detector initialization.
6. **Front-end toggles**: The dashboard allows pose overlays to be toggled client-side; the flag is propagated through Socket.IO to temporarily disable MediaPipe inference for performance-sensitive scenarios.

## Application Entry Points & Components
- **Backend server (`src/cheat_detection_web_app/app.py`)**: Instantiates Flask-SocketIO, initializes a singleton `YOLODetector`, defines Socket.IO handlers for `video_frame` ingestion, and exposes REST endpoints for uploading and processing images or videos before broadcasting annotated frames back to the client.
- **Template & static assets**: `templates/index.html` renders the dashboard shell, pulling in `static/style.css` for layout and `static/script.js` to manage webcam capture, file uploads, Socket.IO communication, metrics visualization, and pose toggle UX.
- **Detection pipeline (`src/detection/yolo_detector.py`)**: Wraps Ultralytics YOLO inference, optional centroid tracking, seat zone management, and MediaPipe pose extraction; returns structured results consumed by the web tier and CLI scripts.
- **Tracking and seating (`src/detection/object_tracker.py`, `src/detection/exam_seat_manager.py`)**: Maintain persistent IDs, stability metrics, and adaptive seat zones used to contextualize detections and drive instructor-facing seat assignments.
- **Pose smoothing (`src/detection/pose_detector.py`)**: Abstracts MediaPipe Pose with temporal smoothing via landmark history buffers, enabling downstream head/hand analytics with reduced jitter.
- **Configuration (`config.py`)**: Centralizes filesystem paths and inference parameters, ensuring `data/` and `output/` directories exist before runtime.
- **Manual verification scripts**: Root-level `test_exam_seats.py`, `test_webcam_pose.py`, `test_webcam_seats.py`, and `test_optimized_pose_detection.py` provide CLI-driven harnesses to benchmark detection behaviors against webcams or prerecorded media.
- **Documentation (`docs/Cheating-Detection-System-Guide.md`)**: Extensive operations manual covering pipeline architecture, demo scripts, future roadmap, and glossary of domain concepts.

## Testing
- **Approach**: No automated test runner is configured; validation relies on interactive scripts that import the same detection modules used by the web app.
- **Primary scripts**:
  - `python test_exam_seats.py --source 0 --config seats.json` for seat assignment and tracking verification with optional output recording.
  - `python test_webcam_pose.py --source 0` to inspect pose overlay fidelity from a live webcam stream.
  - `python test_webcam_seats.py` and `python test_optimized_pose_detection.py` for iterative experiments around seat zoning and pose smoothing performance.
- **Dependencies**: These scripts expect the same runtime packages as the main application and assume local access to YOLO weights and compatible video capture hardware.

## Assets & Data
- **Input samples**: `data/samples/` and the accompanying zipped archive supply canned footage for regression testing without requiring live actors.
- **Generated media**: `output/` plus bundled `output_exam_seats.mp4` demonstrate typical annotated results and provide baselines for performance comparisons.
- **Model weights**: Multiple YOLO v11 weight tiers (nano, small, medium) enable trade-offs between speed and accuracy; ensure GPU memory can accommodate the selected variant.

## Operational Considerations
- **SSL configuration**: The default `socketio.run` call in `app.py` references `cert.pem` and `key.pem`; developers must supply valid certificates or revert to the non-SSL line for local testing.
- **Missing modules referenced in README**: `dashboard.py` and `src/detection/yolo_smoke_test.py` are not present; update documentation or restore the files to avoid confusion during onboarding.
- **Resource requirements**: MediaPipe and YOLO inference benefit from systems with discrete GPUs and 16GB RAM, especially when streaming multiple video feeds.
- **Privacy posture**: Guides recommend storing only flagged frames or pose metadata, aligning with the design objective of minimizing sensitive data retention.
