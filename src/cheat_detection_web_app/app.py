# src/cheat_detection_web_app/app.py
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from src.detection.yolo_detector import YOLODetector
from config import YOLO_MODEL, CONFIDENCE_THRESHOLD, IMG_SIZE
import base64
import numpy as np
import cv2
from flask_socketio import SocketIO, emit
from flask import Flask, render_template, request, jsonify
import tempfile
import uuid


# Add project root to sys.path so we can import config and src modules
PROJECT_ROOT = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

# Create a temporary directory for uploaded files
UPLOAD_FOLDER = tempfile.mkdtemp()
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize detector ONCE at startup (not per request!)
print("Initializing YOLODetector...")
detector = YOLODetector()
print("YOLODetector ready.")


@socketio.on('connect')
def handle_connect():
    print('Client connected')


@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')


@socketio.on('video_frame')
def handle_video_frame(data):
    try:
        # Decode frame
        header, encoded = data.split(',', 1)
        nparr = np.frombuffer(base64.b64decode(encoded), np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            print("Error: Could not decode image frame from frontend.")
            return

        # Use your existing YoloDetector to process the SINGLE frame
        # Note: detector.detect() is a generator for streams, but we can adapt it
        # For a single frame, we call model.predict directly via the detector instance

        detections = detector.detect_frame(frame)

        # Draw detections
        annotated_frame = frame.copy()
        for det in detections:
            x1, y1, x2, y2 = map(int, det['bbox'])
            label = f"{detector.model.names[det['class_id']]} {det['confidence']:.2f}"
            color = (0, 255, 0)
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
            (text_width, text_height), baseline = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
            cv2.rectangle(annotated_frame, (x1, y1 - text_height - baseline),
                          (x1 + text_width, y1), color, thickness=cv2.FILLED)
            cv2.putText(annotated_frame, label, (x1, y1 - baseline),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)

        # Encode and send back
        _, buffer = cv2.imencode('.jpg', annotated_frame, [
                                 cv2.IMWRITE_JPEG_QUALITY, 85])
        annotated_frame_encoded = base64.b64encode(buffer).decode('utf-8')

        # Metrics
        class_counts = {}
        for det in detections:
            class_name = detector.model.names[det['class_id']]
            if class_name in detector.CHEATING_RELATED_CLASSES:
                class_counts[class_name] = class_counts.get(class_name, 0) + 1

        emit('processed_frame', {
            'annotated_frame': annotated_frame_encoded,
            'detections': detections,
            'metrics': class_counts
        })

    except Exception as e:
        print(f"Error in handle_video_frame: {e}")
        import traceback
        traceback.print_exc()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # Generate a unique filename to avoid conflicts
    file_ext = os.path.splitext(str(file.filename))[1]
    unique_filename = str(uuid.uuid4()) + file_ext
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)

    # Save the file
    file.save(file_path)

    # Return the file path for processing
    return jsonify({
        'success': True,
        'file_path': file_path,
        'file_type': 'video' if file_ext.lower() in ['.mp4', '.avi', '.mov'] else 'image'
    })


@app.route('/process_file', methods=['POST'])
def process_file():
    data = request.get_json()
    file_path = data.get('file_path')

    if not file_path or not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404

    try:
        # Process the file with the detector
        detections = []

        if data.get('file_type') == 'image':
            # Process a single image
            img = cv2.imread(file_path)
            if img is None:
                return jsonify({'error': 'Could not read image file'}), 400

            detections = detector.detect_frame(img)

            # Draw detections
            annotated_img = img.copy()
            for det in detections:
                x1, y1, x2, y2 = map(int, det['bbox'])
                label = f"{detector.model.names[det['class_id']]} {det['confidence']:.2f}"
                color = (0, 255, 0)
                cv2.rectangle(annotated_img, (x1, y1), (x2, y2), color, 2)
                (text_width, text_height), baseline = cv2.getTextSize(
                    label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                cv2.rectangle(annotated_img, (x1, y1 - text_height - baseline),
                            (x1 + text_width, y1), color, thickness=cv2.FILLED)
                cv2.putText(annotated_img, label, (x1, y1 - baseline),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)

            # Encode and send back
            _, buffer = cv2.imencode('.jpg', annotated_img, [
                                    cv2.IMWRITE_JPEG_QUALITY, 85])
            annotated_img_encoded = base64.b64encode(buffer).decode('utf-8')

            # Metrics
            class_counts = {}
            for det in detections:
                class_name = detector.model.names[det['class_id']]
                if class_name in detector.CHEATING_RELATED_CLASSES:
                    class_counts[class_name] = class_counts.get(class_name, 0) + 1

            return jsonify({
                'success': True,
                'annotated_frame': annotated_img_encoded,
                'detections': detections,
                'metrics': class_counts
            })
        else:
            # For video files, we'll handle them frame by frame via the existing socket connection
            return jsonify({
                'success': True,
                'message': 'Video file received. Processing will continue via socket connection.'
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
