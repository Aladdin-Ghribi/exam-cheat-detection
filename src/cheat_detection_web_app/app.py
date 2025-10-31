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
        # Get pose_enabled flag if present, default to True
        pose_enabled = data.get('pose_enabled', True)
        
        # Store original pose state
        original_pose_state = detector.enable_pose if hasattr(detector, 'enable_pose') else True
        
        # Temporarily set pose detection based on frontend flag
        if hasattr(detector, 'enable_pose'):
            detector.enable_pose = pose_enabled
        
        # Decode frame
        if isinstance(data, str):
            # Legacy format - just the image data
            header, encoded = data.split(',', 1)
        else:
            # New format - data is an object with image field
            header, encoded = data['image'].split(',', 1)
        
        nparr = np.frombuffer(base64.b64decode(encoded), np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            print("Error: Could not decode image frame from frontend.")
            # Restore original pose state before returning
            if hasattr(detector, 'enable_pose'):
                detector.enable_pose = original_pose_state
            return

        # Use detect_frame to get detections + seat assignments
        detection_result = detector.detect_frame(frame)
        
        # Sanitize detections (convert NumPy types to Python native types)
        raw_detections = detection_result['detections']
        detections = []
        for det in raw_detections:
            detections.append({
                'class_id': int(det['class_id']),
                'confidence': float(det['confidence']),
                'bbox': [float(x) for x in det['bbox']]
            })

        # Sanitize seat assignments
        raw_seat_assignments = detection_result.get('seat_assignments', {})
        seat_assignments = {
            int(k): int(v) for k, v in raw_seat_assignments.items()
        } if raw_seat_assignments else {}
        print("Seat Assignments:", seat_assignments)

        # Use built-in draw_detections for consistent styling
        annotated_frame = detector.draw_detections(frame, detection_result)

        # Encode and send back
        _, buffer = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
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
            'seat_assignments': seat_assignments,
            'metrics': class_counts
        })
        
        # Restore original pose state after processing
        if hasattr(detector, 'enable_pose'):
            detector.enable_pose = original_pose_state

    except Exception as e:
        print(f"Error in handle_video_frame: {e}")
        import traceback
        traceback.print_exc()
        # Restore original pose state in case of error
        if hasattr(detector, 'enable_pose'):
            detector.enable_pose = original_pose_state

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
        if data.get('file_type') == 'image':
            img = cv2.imread(file_path)
            if img is None:
                return jsonify({'error': 'Could not read image file'}), 400

            detection_result = detector.detect_frame(img)
            
            # Sanitize detections
            raw_detections = detection_result['detections']
            detections = []
            for det in raw_detections:
                detections.append({
                    'class_id': int(det['class_id']),
                    'confidence': float(det['confidence']),
                    'bbox': [float(x) for x in det['bbox']]
                })

            # Sanitize seat assignments
            raw_seat_assignments = detection_result.get('seat_assignments', {})
            seat_assignments = {
                int(k): int(v) for k, v in raw_seat_assignments.items()
            } if raw_seat_assignments else {}

            annotated_img = detector.draw_detections(img, detection_result)

            _, buffer = cv2.imencode('.jpg', annotated_img, [cv2.IMWRITE_JPEG_QUALITY, 85])
            annotated_img_encoded = base64.b64encode(buffer).decode('utf-8')

            class_counts = {}
            for det in detections:
                class_name = detector.model.names[det['class_id']]
                if class_name in detector.CHEATING_RELATED_CLASSES:
                    class_counts[class_name] = class_counts.get(class_name, 0) + 1

            return jsonify({
                'success': True,
                'annotated_frame': annotated_img_encoded,
                'detections': detections,
                'seat_assignments': seat_assignments,
                'metrics': class_counts
            })
        else:
            return jsonify({
                'success': True,
                'message': 'Video file received. Processing will continue via socket connection.'
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)