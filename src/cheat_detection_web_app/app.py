# src/cheat_detection_web_app/app.py
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from src.detection.yolo_detector import YOLODetector
from config import YOLO_MODEL, CONFIDENCE_THRESHOLD, IMG_SIZE_GPU, IMG_SIZE_CPU
import base64
import numpy as np
import cv2
from flask_socketio import SocketIO, emit
from flask import Flask, render_template, request, jsonify, send_file
import tempfile
import uuid
import json
import csv
import zipfile
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

UPLOAD_FOLDER = tempfile.mkdtemp()
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
socketio = SocketIO(app, cors_allowed_origins="*")

print("Initializing YOLODetector...")
detector = YOLODetector()
detector.auto_save_enabled = True
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
        pose_enabled = data.get('pose_enabled', True)
        original_pose_state = detector.enable_pose if hasattr(detector, 'enable_pose') else True
        
        if hasattr(detector, 'enable_pose'):
            detector.enable_pose = pose_enabled
        
        if isinstance(data, str):
            header, encoded = data.split(',', 1)
        else:
            header, encoded = data['image'].split(',', 1)
        
        nparr = np.frombuffer(base64.b64decode(encoded), np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            print("Error: Could not decode image frame from frontend.")
            if hasattr(detector, 'enable_pose'):
                detector.enable_pose = original_pose_state
            return

        detection_result = detector.detect_frame(frame)
        
        if hasattr(detector, 'auto_save_enabled') and detector.auto_save_enabled:
            if hasattr(detector, 'evidence_saver'):
                detector.evidence_saver.process_frame(frame, detection_result['detections'])
        
        raw_detections = detection_result['detections']
        detections = []
        for det in raw_detections:
            sanitized = {
                'class_id': int(det['class_id']),
                'confidence': float(det['confidence']),
                'bbox': [float(x) for x in det['bbox']]
            }
            if 'behavior' in det:
                sanitized['behavior'] = det['behavior']
                # Convert suspicion score to 0-100 scale
                if 'suspicion' in sanitized['behavior']:
                    suspicion = sanitized['behavior']['suspicion']
                    suspicion['suspicion_score_100'] = int(suspicion.get('smoothed', 0) * 100)
            if 'track_id' in det:
                sanitized['track_id'] = int(det['track_id'])
            detections.append(sanitized)

        raw_seat_assignments = detection_result.get('seat_assignments', {})
        seat_assignments = {
            int(k): int(v) for k, v in raw_seat_assignments.items()
        } if raw_seat_assignments else {}

        annotated_frame = detector.draw_detections(frame, detection_result)

        _, buffer = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        annotated_frame_encoded = base64.b64encode(buffer).decode('utf-8')

        class_counts = {}
        for det in detections:
            class_name = detector.model.names[det['class_id']]
            if class_name in detector.CHEATING_RELATED_CLASSES:
                class_counts[class_name] = class_counts.get(class_name, 0) + 1

        perf_stats = detector.get_performance_stats()

        # Store latest data globally and log flagged events
        global latest_data, event_log
        latest_data = {
            'detections': detections,
            'seat_assignments': seat_assignments,
            'annotated_frame': annotated_frame_encoded
        }
        
        # Log flagged incidents
        for det in detections:
            if det.get('behavior', {}).get('suspicion', {}).get('smoothed', 0) * 100 >= 20:
                event_log.append({
                    'timestamp': datetime.now().strftime('%H:%M:%S'),
                    'student_id': det.get('track_id', 'Unknown'),
                    'score': int(det['behavior']['suspicion']['smoothed'] * 100),
                    'description': get_incident_description(det)
                })
                if len(event_log) > 50:  # Keep only last 50 events
                    event_log.pop(0)
        
        emit('processed_frame', {
            'annotated_frame': annotated_frame_encoded,
            'detections': detections,
            'seat_assignments': seat_assignments,
            'metrics': class_counts,
            'performance_stats': perf_stats
        })
        
        if hasattr(detector, 'enable_pose'):
            detector.enable_pose = original_pose_state

    except Exception as e:
        print(f"Error in handle_video_frame: {e}")
        import traceback
        traceback.print_exc()
        if hasattr(detector, 'enable_pose'):
            detector.enable_pose = original_pose_state

@app.route('/')
def index():
    return render_template('index.html')

# Global variable to store latest detection data
latest_data = {'detections': [], 'seat_assignments': {}, 'annotated_frame': None}
event_log = []

def get_incident_description(detection):
    reasons = []
    behavior = detection.get('behavior', {})
    
    if behavior.get('head_orientation'):
        ho = behavior['head_orientation']
        if abs(ho['yaw']) > 30:
            reasons.append(f"Head turned {abs(ho['yaw']):.0f}°")
        if abs(ho['pitch']) > 20:
            reasons.append(f"Head tilted {abs(ho['pitch']):.0f}°")
    
    if behavior.get('hands'):
        for side in ['left', 'right']:
            hand = behavior['hands'].get(side, {})
            if hand.get('near_object') and hand.get('object_class'):
                reasons.append(f"{side.title()} hand near {hand['object_class']}")
            elif hand.get('near_face'):
                reasons.append(f"{side.title()} hand near face")
    
    return ', '.join(reasons) if reasons else 'Suspicious behavior detected'

@app.route('/api/current_data')
def get_current_data():
    global event_log
    data = latest_data.copy()
    data['event_log'] = event_log[-10:]  # Last 10 events
    data['has_active_session'] = bool(data.get('annotated_frame'))
    return jsonify(data)

@app.route('/api/event_log')
def get_event_log():
    global event_log
    return jsonify({
        'events': event_log,
        'total_count': len(event_log)
    })

@app.route('/api/seat_assignments')
def get_seat_assignments():
    global latest_data
    seat_assignments = latest_data.get('seat_assignments', {})
    return jsonify({
        'seat_assignments': seat_assignments,
        'active_seats': len([s for s in seat_assignments.values() if s])
    })

@app.route('/api/metrics')
def get_metrics():
    global latest_data
    detections = latest_data.get('detections', [])
    metrics = {}
    for det in detections:
        class_name = detector.model.names[det['class_id']]
        if class_name in detector.CHEATING_RELATED_CLASSES:
            metrics[class_name] = metrics.get(class_name, 0) + 1
    return jsonify({
        'metrics': metrics,
        'detection_count': len(detections)
    })

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    file_ext = os.path.splitext(str(file.filename))[1]
    unique_filename = str(uuid.uuid4()) + file_ext
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)

    file.save(file_path)

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
            
            raw_detections = detection_result['detections']
            detections = []
            for det in raw_detections:
                sanitized = {
                    'class_id': int(det['class_id']),
                    'confidence': float(det['confidence']),
                    'bbox': [float(x) for x in det['bbox']]
                }
                if 'behavior' in det:
                    sanitized['behavior'] = det['behavior']
                if 'track_id' in det:
                    sanitized['track_id'] = int(det['track_id'])
                detections.append(sanitized)

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

            # Store latest data globally for instructor view
            global latest_data
            latest_data = {
                'detections': detections,
                'seat_assignments': seat_assignments,
                'annotated_frame': annotated_img_encoded
            }
            
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

@socketio.on('update_suspicion_threshold')
def update_suspicion_threshold(data):
    threshold = data.get('threshold', 20)
    detector.evidence_saver.suspicion_threshold = threshold
    print(f"Updated suspicion threshold to: {threshold}")
    emit('threshold_updated', {'threshold': threshold})

@socketio.on('toggle_auto_save')
def toggle_auto_save(data):
    enabled = data.get('enabled', True)
    detector.set_auto_save(enabled)
    print(f"Auto-save {'enabled' if enabled else 'disabled'}")
    emit('save_notification', {'message': f"Auto-save {'enabled' if enabled else 'disabled'}", 'type': 'info'})

@socketio.on('switch_model')
def switch_model(data):
    model_size = data.get('model_size', 'medium')
    if detector.switch_model(model_size):
        emit('save_notification', {'message': f'Switched to {model_size} model', 'type': 'success'})
    else:
        emit('save_notification', {'message': f'Failed to switch to {model_size} model', 'type': 'error'})

@socketio.on('toggle_frame_skipping')
def toggle_frame_skipping(data):
    enabled = data.get('enabled', True)
    detector.enable_frame_skipping = enabled
    print(f"Frame skipping {'enabled' if enabled else 'disabled'}")
    emit('save_notification', {'message': f"Frame skipping {'enabled' if enabled else 'disabled'}", 'type': 'info'})

@socketio.on('manual_save')
def manual_save(data):
    try:
        frame_b64 = data.get('frame')
        detections = data.get('detections', [])
        
        if not frame_b64:
            emit('save_notification', {'message': 'No frame data received', 'type': 'error'})
            return
        
        nparr = np.frombuffer(base64.b64decode(frame_b64), np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            emit('save_notification', {'message': 'Failed to decode frame', 'type': 'error'})
            return
        
        detector.evidence_saver.manual_save(frame, detections, reason="Manual save from UI")
        emit('save_notification', {'message': 'Frame saved successfully', 'type': 'success'})
    except Exception as e:
        print(f"Error in manual_save: {e}")
        emit('save_notification', {'message': f'Save failed: {str(e)}', 'type': 'error'})

@socketio.on('export_data')
def export_data(data):
    try:
        format_type = data.get('format', 'json')
        events = detector.evidence_saver.get_recent_events(limit=100)
        
        if not events:
            emit('save_notification', {'message': 'No events to export', 'type': 'error'})
            return
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if format_type == 'json':
            filename = f'flagged_events_{timestamp}.json'
            filepath = os.path.join(tempfile.gettempdir(), filename)
            with open(filepath, 'w') as f:
                json.dump(events, f, indent=2)
        
        elif format_type == 'csv':
            filename = f'flagged_events_{timestamp}.csv'
            filepath = os.path.join(tempfile.gettempdir(), filename)
            with open(filepath, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Event ID', 'Timestamp', 'Suspicion Score', 'Reasons'])
                for event in events:
                    writer.writerow([
                        event.get('event_id', ''),
                        event.get('timestamp', ''),
                        event.get('suspicion_score_100', 0),
                        '; '.join(event.get('reasons', []))
                    ])
        
        elif format_type == 'zip':
            filename = f'flagged_events_{timestamp}.zip'
            filepath = os.path.join(tempfile.gettempdir(), filename)
            with zipfile.ZipFile(filepath, 'w') as zipf:
                evidence_dir = detector.evidence_saver.output_dir
                for event in events:
                    event_id = event.get('event_id')
                    event_dir = os.path.join(evidence_dir, event_id)
                    if os.path.exists(event_dir):
                        for root, dirs, files in os.walk(event_dir):
                            for file in files:
                                file_path = os.path.join(root, file)
                                arcname = os.path.join(event_id, file)
                                zipf.write(file_path, arcname)
        
        emit('export_ready', {'download_url': f'/download/{filename}', 'filename': filename})
    except Exception as e:
        print(f"Error in export_data: {e}")
        emit('save_notification', {'message': f'Export failed: {str(e)}', 'type': 'error'})

@app.route('/download/<filename>')
def download_file(filename):
    filepath = os.path.join(tempfile.gettempdir(), filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True, download_name=filename)
    return jsonify({'error': 'File not found'}), 404

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
