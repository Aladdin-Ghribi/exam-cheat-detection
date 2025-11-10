# Development Guidelines

## Code Quality Standards

### Import Organization
- **System imports first**: `import os`, `import sys`
- **Path manipulation early**: `sys.path.append()` calls immediately after system imports
- **Third-party imports**: External libraries like `cv2`, `numpy`, `ultralytics`
- **Local imports**: Project modules using relative imports (`from .module import Class`)
- **Configuration imports**: `from config import CONSTANTS`

### Class Structure Patterns
- **Initialization with defaults**: All classes provide sensible default parameters
- **Configuration-driven**: Classes accept configuration parameters in `__init__`
- **Resource management**: Classes implement `close()` methods for cleanup
- **State management**: Use instance variables to track internal state

### Error Handling Standards
- **Graceful degradation**: Functions return None or default values on failure
- **Early returns**: Validate inputs early and return immediately on invalid data
- **Exception context**: Use try-catch blocks with specific error messages
- **State restoration**: Always restore original state in finally blocks or after errors

### Performance Optimization Patterns
- **Reduced complexity**: Use `model_complexity=0` for faster processing
- **Batch processing**: Process multiple items in single operations
- **Caching**: Initialize expensive resources once at startup
- **Threshold-based processing**: Skip processing when conditions aren't met

## Semantic Patterns

### Computer Vision Processing
```python
# Standard detection pipeline
results = self.model.predict(
    source=frame,
    conf=CONFIDENCE_THRESHOLD,
    imgsz=IMG_SIZE,
    classes=self.target_class_ids,
    verbose=False
)

# Consistent result extraction
for box, cls_id_tensor, conf_tensor in zip(results[0].boxes.xyxy, results[0].boxes.cls, results[0].boxes.conf):
    cls_id = int(cls_id_tensor)
    conf = float(conf_tensor)
    x1, y1, x2, y2 = box.tolist()
```

### Data Sanitization Pattern
```python
# Convert NumPy types to Python native types for JSON serialization
detections = []
for det in raw_detections:
    detections.append({
        'class_id': int(det['class_id']),
        'confidence': float(det['confidence']),
        'bbox': [float(x) for x in det['bbox']]
    })
```

### State Management with History
```python
# Use deque for fixed-size history tracking
from collections import deque
self.position_history = defaultdict(lambda: deque(maxlen=20))
self.landmark_history = {}  # track_id -> deque of landmarks
```

### Coordinate System Handling
```python
# Consistent bbox format: [x1, y1, x2, y2]
x1, y1, x2, y2 = map(int, det['bbox'])

# Normalized to pixel coordinate conversion
x = int(landmark['x'] * width)
y = int(landmark['y'] * height)

# Center point calculation
cx = int((x1 + x2) / 2.0)
cy = int(y1 + (y2 - y1) / 3)  # Lower chest for stability
```

### Real-time Processing Patterns
```python
# Frame rate control
const PROCESS_INTERVAL_MS = 50; // Target ~10 FPS
if (now - lastProcessedTime < PROCESS_INTERVAL_MS) {
    return;
}

# Asynchronous processing with state tracking
let isProcessing = false;
if (isProcessing) return;
isProcessing = true;
```

## API Design Patterns

### Method Return Structures
```python
# Consistent result dictionaries
return {
    'success': bool,
    'data': dict,
    'error': str or None
}

# Detection results format
return {
    'detections': list,
    'seat_assignments': dict,
    'additional_data': dict
}
```

### Configuration Management
```python
# Centralized configuration with defaults
CONFIDENCE_THRESHOLD = 0.5
IMG_SIZE = 1344
YOLO_MODEL = "yolo11m.pt"

# Class-level configuration
def __init__(self, model_path=YOLO_MODEL, enable_tracking=True):
    self.enable_tracking = enable_tracking
```

### WebSocket Communication
```javascript
// Structured data exchange
socket.emit('video_frame', { 
    image: frameDataUrl, 
    pose_enabled: poseEnabled 
});

socket.on('processed_frame', (data) => {
    // Handle: annotated_frame, detections, seat_assignments, metrics
});
```

## Naming Conventions

### Variables and Functions
- **Snake case**: `pose_enabled`, `seat_assignments`, `detection_result`
- **Descriptive names**: `annotated_frame` not `frame2`, `stable_position` not `pos`
- **Boolean prefixes**: `enable_pose`, `is_processing`, `has_detection`

### Constants and Configuration
- **ALL_CAPS**: `CONFIDENCE_THRESHOLD`, `PERSON_CLASS_ID`, `PROCESS_INTERVAL_MS`
- **Grouped by purpose**: `CHEATING_RELATED_CLASSES`, `IMG_SIZE`

### Class and Method Names
- **PascalCase classes**: `YOLODetector`, `PoseDetector`, `ExamSeatManager`
- **Descriptive methods**: `detect_frame()`, `draw_detections()`, `update_zone_assignments()`
- **Private methods**: `_smooth_landmarks()`, `_is_in_zone()`, `_build_behavior_hand_entry()`

## Documentation Standards

### Docstring Format
```python
def detect(self, image, track_id=None):
    """
    Process an image and detect pose landmarks with smoothing.

    Args:
        image: Input image (BGR format)
        track_id: Optional track ID for smoothing across frames

    Returns:
        Dictionary containing:
            - success: Boolean indicating if pose was detected
            - landmarks: List of landmarks (x, y, z, visibility)
    """
```

### Inline Comments
- **Explain complex logic**: Mathematical calculations, coordinate transformations
- **Mark optimizations**: `# Reduced complexity for speed`
- **Indicate state changes**: `# Store original pose state`
- **Flag important sections**: `# ✅ NEW: Method for single-frame detection`