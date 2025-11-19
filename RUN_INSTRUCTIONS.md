# How to Run the Exam Cheat Detection System

## Quick Start

### 1. Activate Virtual Environment
```powershell
cd exam-cheat-detection
venv\Scripts\Activate.ps1
```

### 2. Install Dependencies (if not already installed)
```powershell
pip install -r requirements.txt
```

### 3. Run the Application
```powershell
python src/cheat_detection_web_app/app.py
```

### 4. Access the Dashboard
Open your web browser and navigate to:
```
http://localhost:5000
```

## Alternative Method

You can also use the start script:
```powershell
python start_app.py
```

## What to Expect

Once the application starts, you should see:
- "Initializing YOLODetector..." message
- "YOLODetector ready." confirmation
- Server running on `http://0.0.0.0:5000`

## Using the Dashboard

### Video Source Options
1. **Webcam**: Click "Use Webcam" button (default)
2. **Upload File**: Click "Upload File" to select a video or image

### Instructor View Features

#### Left Panel
- **Video Feed**: Real-time annotated video display
- **Runtime Controls** (collapsible):
  - Performance Settings (model size, frame skipping)
  - Detection Parameters (yaw, pitch, suspicion thresholds)
- **Save & Export** (collapsible):
  - Auto-save toggle
  - Manual save button
  - Export options (JSON, CSV, ZIP)

#### Right Panel
- **Seat Map**: Visual grid showing student positions with status indicators
  - 🔵 Blue: Active students
  - 🟡 Yellow: Suspicious activity
  - 🔴 Red: High alert
- **Event Log**: Filtered list of flagged events
  - Filter by severity (High/Medium/Low)
  - Filter by type (Head Turn/Hand Near Face/Object Nearby)
  - Refresh button to load recent events

## Troubleshooting

### Camera Access Denied
- Allow camera permissions in your browser
- Refresh the page after granting permissions

### Port Already in Use
If port 5000 is busy, edit `app.py` and change:
```python
socketio.run(app, debug=True, host='0.0.0.0', port=5001)
```

### Module Not Found Errors
Ensure you're in the virtual environment:
```powershell
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### YOLO Model Not Found
The application will automatically download the YOLO model on first run. Ensure you have internet connection.

## Performance Tips

1. **Use Nano Model** for faster processing on slower machines
2. **Enable Frame Skipping** to reduce CPU/GPU load
3. **Adjust Suspicion Threshold** to reduce false positives
4. **Close Other Applications** to free up system resources

## Stopping the Application

Press `Ctrl+C` in the terminal to stop the server.

## Testing

Run the test script to verify installation:
```powershell
python test_instructor_view.py
```

## System Requirements

- **Python**: 3.8 or higher
- **RAM**: 8GB minimum, 16GB recommended
- **GPU**: Optional but recommended for better performance
- **Camera**: Webcam or video file for testing
- **Browser**: Chrome, Firefox, or Edge (latest versions)
