# Project Structure

## Directory Organization

### Core Application (`src/`)
- **`detection/`** - Core detection modules
  - `yolo_detector.py` - YOLO-based object detection engine
  - `pose_detector.py` - MediaPipe pose estimation and analysis
  - `exam_seat_manager.py` - Student seat assignment and tracking
  - `object_tracker.py` - Object tracking across frames
- **`cheat_detection_web_app/`** - Web interface
  - `app.py` - Flask application with SocketIO for real-time processing
  - `static/` - Frontend assets (CSS, JavaScript)
  - `templates/` - HTML templates
- **`utils/`** - Shared utilities and helper functions

### Data Management (`data/`)
- **`samples/`** - Test images and videos for development
- Sample files include `sample1.jpg` and `test1.mp4`

### Output Storage (`output/`)
- **`raw_detections/`** - Processed detection results
  - Annotated images with bounding boxes
  - JSON detection metadata
  - Original frames for comparison

### Configuration & Documentation
- **`config.py`** - Central configuration (model paths, thresholds, directories)
- **`docs/`** - Project documentation and guides
- **`requirements.txt`** - Python dependencies
- **Test files** - Various testing scripts for different components

## Architectural Patterns

### Modular Detection Pipeline
1. **Input Processing** - Frame capture and preprocessing
2. **Multi-modal Detection** - YOLO + MediaPipe parallel processing
3. **Seat Management** - Student tracking and assignment
4. **Result Fusion** - Combining detection results with confidence scoring
5. **Output Generation** - Annotated frames and structured data

### Real-time Web Architecture
- **Backend**: Flask + SocketIO for WebSocket communication
- **Frontend**: Vanilla JavaScript with real-time video streaming
- **Processing**: Asynchronous frame processing with immediate feedback

### Privacy-by-Design
- Temporary file storage with automatic cleanup
- Event-based retention (only suspicious frames saved)
- No persistent biometric data collection