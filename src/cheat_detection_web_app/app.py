# app.py
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import cv2
import numpy as np
from ultralytics import YOLO
import base64
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
# Allow connections from any origin for local dev
socketio = SocketIO(app, cors_allowed_origins="*")

# --- Configuration ---
MODEL_PATH = "yolo11m.pt"  # Or "yolo11m.pt" etc.
CONFIDENCE_THRESHOLD = 0.5
IMG_SIZE = 640  # Or 832 if you prefer

# Define classes relevant to cheating (example IDs for COCO dataset)
CHEATING_RELATED_CLASSES = {
    'cell_phone': 67,
    'book': 73,
    'laptop': 63,
    'backpack': 24,
    'handbag': 26,
    'person':0
}

# --- Initialize Model ---
print(f"Loading model: {MODEL_PATH}")
model = YOLO(MODEL_PATH)
print("Model loaded successfully.")

# --- WebSocket Event Handlers ---


@socketio.on('connect')
def handle_connect():
    print('Client connected')


@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')


@socketio.on('video_frame')
def handle_video_frame(data):
    """Receives a video frame from the frontend, processes it, and sends back results."""
    try:
        # Decode the base64 image data received from the frontend
        # The frontend sends 'data:image/jpeg;base64,...'
        header, encoded = data.split(',', 1)
        nparr = np.frombuffer(base64.b64decode(encoded), np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            print("Error: Could not decode image frame from frontend.")
            return  # Exit if frame is invalid

        # --- Run YOLO Detection ---
        results = model(frame, verbose=False,
                        conf=CONFIDENCE_THRESHOLD, imgsz=IMG_SIZE)

        # --- Process Results ---
        detections = []
        for r in results:
            if r.boxes is not None:
                for box, cls_id_tensor, conf_tensor in zip(r.boxes.xyxy, r.boxes.cls, r.boxes.conf):
                    cls_id = int(cls_id_tensor)
                    conf = float(conf_tensor)
                    x1, y1, x2, y2 = box.tolist()

                    # Filter based on target class IDs if needed, or just filter by confidence
                    # For metrics, let the frontend filter later if needed.
                    detections.append({
                        'class_id': cls_id,
                        'confidence': conf,
                        'bbox': [x1, y1, x2, y2]
                    })

        # --- Draw Detections on the frame (Optional for sending back) ---
        # For performance, you might choose to draw boxes on the frontend.
        # Or, draw them here and send the annotated frame back.
        # Let's draw them here for consistency with the OpenCV example.
        annotated_frame = frame.copy()
        for det in detections:
            x1, y1, x2, y2 = map(int, det['bbox'])
            label = f"{model.names[det['class_id']]} {det['confidence']:.2f}"
            color = (0, 255, 0)  # BGR Green
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
            # Calculate text size for background
            (text_width, text_height), baseline = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
            cv2.rectangle(annotated_frame, (x1, y1 - text_height - baseline),
                          (x1 + text_width, y1), color, thickness=cv2.FILLED)
            cv2.putText(annotated_frame, label, (x1, y1 - baseline),
                        # Black text
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)

        # --- Prepare Data to Send Back ---
        # Encode the annotated frame back to base64 for sending to frontend
        _, buffer = cv2.imencode('.jpg', annotated_frame, [
                                 cv2.IMWRITE_JPEG_QUALITY, 85])  # Adjust quality as needed
        annotated_frame_encoded = base64.b64encode(buffer).decode('utf-8')

        # Prepare metrics data
        class_counts = {}
        for det in detections:
            class_name = model.names[det['class_id']]
            if class_name in CHEATING_RELATED_CLASSES:
                class_counts[class_name] = class_counts.get(class_name, 0) + 1

        # Emit the processed frame and metrics back to the frontend
        emit('processed_frame', {
            'annotated_frame': annotated_frame_encoded,
            'detections': detections,
            'metrics': class_counts
        })

    except Exception as e:
        print(f"Error processing frame: {e}")
        # Optionally emit an error message to the frontend
        # emit('error', {'message': str(e)})


@app.route('/')
def index():
    """Serve the main HTML page."""
    return render_template('index.html')


if __name__ == '__main__':
    # Host on 0.0.0.0 to access from other devices on network if needed
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
