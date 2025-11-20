# src/cheat_detection_web_app/app.py
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from src.detection.yolo_detector import YOLODetector
from src.detection.suspicion_scorer import SuspicionScorer
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

print("Initializing SuspicionScorer...")
suspicion_scorer = SuspicionScorer()
print("SuspicionScorer ready.")

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
                # Add unified suspicion score calculation
                suspicion_result = suspicion_scorer.score_detection(det)
                sanitized['unified_score'] = round(suspicion_result['smoothed'] * 100)
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

        # Build seat map data with status
        seat_map_data = []
        for det in detections:
            if det['class_id'] == 0 and 'track_id' in det:
                track_id = det['track_id']
                seat_id = seat_assignments.get(track_id)
                suspicion_score = 0
                if 'behavior' in det and 'suspicion' in det['behavior']:
                    suspicion_score = det['behavior']['suspicion'].get('smoothed', 0) * 100
                
                status = 'flagged' if suspicion_score >= 20 else 'active'
                seat_map_data.append({
                    'track_id': track_id,
                    'seat_id': seat_id,
                    'status': status,
                    'suspicion_score': suspicion_score
                })

        # Check for flagged events
        flagged_events = []
        for det in detections:
            if det['class_id'] == 0 and 'behavior' in det and 'suspicion' in det['behavior']:
                suspicion_score = det['behavior']['suspicion'].get('smoothed', 0) * 100
                if suspicion_score >= 20:
                    reasons = []
                    if 'head_orientation' in det['behavior']:
                        ho = det['behavior']['head_orientation']
                        if ho and abs(ho.get('yaw', 0)) > 30:
                            reasons.append(f"Head turned {abs(ho['yaw']):.0f}°")
                    if 'hands' in det['behavior']:
                        for side in ['left', 'right']:
                            hand = det['behavior']['hands'].get(side, {})
                            if hand.get('near_object') and hand.get('object_class'):
                                reasons.append(f"{side.capitalize()} hand near {hand['object_class']}")
                    
                    if reasons:
                        flagged_events.append({
                            'track_id': det.get('track_id'),
                            'timestamp': datetime.now().strftime('%H:%M:%S'),
                            'score': int(suspicion_score),
                            'description': ', '.join(reasons[:2])
                        })

        emit('processed_frame', {
            'annotated_frame': annotated_frame_encoded,
            'detections': detections,
            'seat_assignments': seat_assignments,
            'seat_map_data': seat_map_data,
            'flagged_events': flagged_events,
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
                    # Add unified suspicion score calculation
                    suspicion_result = suspicion_scorer.score_detection(det)
                    sanitized['unified_score'] = round(suspicion_result['smoothed'] * 100)
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
    detector.auto_save_enabled = enabled
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

@app.route('/api/historical_events', methods=['GET'])
def get_historical_events():
    try:
        evidence_dir = os.path.join(PROJECT_ROOT, 'output', 'flagged_evidence')
        if not os.path.exists(evidence_dir):
            return jsonify({'events': []})
        
        events = []
        for event_folder in os.listdir(evidence_dir):
            metadata_path = os.path.join(evidence_dir, event_folder, 'metadata.json')
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                    timestamp_str = metadata.get('timestamp', '')
                    if timestamp_str:
                        dt = datetime.fromisoformat(timestamp_str)
                        time_str = dt.strftime('%H:%M:%S')
                    else:
                        time_str = 'Unknown'
                    
                    track_id = event_folder.split('_')[-1]
                    suspicion_score = metadata.get('suspicion_score_100', 0)
                    reasons = metadata.get('reasons', [])
                    
                    if not reasons and 'all_detections' in metadata and len(metadata['all_detections']) > 0:
                        det = metadata['all_detections'][0]
                        if 'behavior' in det:
                            behavior = det['behavior']
                            if 'head_orientation' in behavior:
                                ho = behavior['head_orientation']
                                if abs(ho.get('yaw', 0)) > 30:
                                    reasons.append(f"Body rolled {abs(ho['yaw']):.0f}°")
                                if abs(ho.get('pitch', 0)) > 20:
                                    reasons.append(f"Head left/right {abs(ho['pitch']):.0f}°")
                            if 'hands' in behavior:
                                for side in ['left', 'right']:
                                    hand = behavior['hands'].get(side, {})
                                    if hand.get('near_object') and hand.get('object_class'):
                                        reasons.append(f"{side.capitalize()} hand near {hand['object_class']}")
                    
                    events.append({
                        'track_id': int(track_id),
                        'timestamp': time_str,
                        'score': suspicion_score,
                        'description': ', '.join(reasons[:2]) if reasons else 'Suspicious behavior detected'
                    })
        
        events.sort(key=lambda x: x['timestamp'], reverse=True)
        return jsonify({'events': events[:100]})
    except Exception as e:
        print(f"Error loading historical events: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'events': []})

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
