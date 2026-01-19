
"""
Exam Cheat Detection Web Application v2
Flask-SocketIO backend with session management and event card logic
"""

import time
import threading
from src.utils.secure_eraser import SecureEraser
from datetime import datetime
import uuid
import base64
import json
import cv2
import numpy as np
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
from flask_socketio import SocketIO, emit
from src.detection.yolo_detector import YOLODetector
from src.detection.suspicion_scorer import SuspicionScorer
from src.detection.suspicion_config import SUSPICION_THRESHOLD
import os
import sys
import torch
from pathlib import Path

# Path setup - MUST BE FIRST
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Now import project modules


# ============================================
# APP CONFIGURATION
# ============================================

app = Flask(__name__,
            template_folder=str(Path(__file__).parent),
            static_folder=str(Path(__file__).parent / 'static'))
app.config['SECRET_KEY'] = 'exam-cheat-detection-v2-secret-key'

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='threading',
    ping_timeout=60,
    ping_interval=25,
    max_http_buffer_size=10000000,  # 10MB
    engineio_logger=False,
    logger=False
)

# Add cache-control headers to prevent back button access


@app.after_request
def add_security_headers(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


# Paths
DATA_DIR = PROJECT_ROOT / 'data'
OUTPUT_DIR = PROJECT_ROOT / 'output'
HISTORY_DIR = OUTPUT_DIR / 'history' / 'cards'
USERS_FILE = DATA_DIR / 'users.json'
CONFIG_FILE = DATA_DIR / 'config.json'

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_DIR.mkdir(parents=True, exist_ok=True)
(DATA_DIR / 'student_faces').mkdir(parents=True, exist_ok=True)

# ============================================
# DETECTION PIPELINE INITIALIZATION
# ============================================

print("=" * 50)
print("Initializing Exam Cheat Detection v2")
print("=" * 50)

print("Loading YOLODetector...")
detector = YOLODetector()
detector.auto_save_enabled = False  # We handle saving manually now
print("YOLODetector ready")

# Load configuration from config.json if it exists
if CONFIG_FILE.exists():
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)

        # Apply configuration settings to detector
        if 'model_size' in config and hasattr(detector, 'model_size'):
            if detector.model_size != config['model_size']:
                print(
                    f"Loading model size from config: {config['model_size']}")
                detector.switch_model(config['model_size'])

        if 'confidence_threshold' in config and hasattr(detector, 'confidence_threshold'):
            print(
                f"Loading confidence threshold from config: {config['confidence_threshold']}")
            detector.confidence_threshold = config['confidence_threshold']

        if 'img_processing_size' in config and hasattr(detector, 'img_size'):
            print(
                f"Loading image processing size from config: {config['img_processing_size']}")
            detector.img_size = config['img_processing_size']

        if 'model_complexity' in config and hasattr(detector, 'set_model_complexity'):
            print(
                f"Loading model complexity from config: {config['model_complexity']}")
            detector.set_model_complexity(config['model_complexity'])

        if 'yaw_threshold' in config and hasattr(detector, 'yaw_threshold'):
            print(
                f"Loading yaw threshold from config: {config['yaw_threshold']}")
            detector.yaw_threshold = config['yaw_threshold']

        if 'pitch_threshold' in config and hasattr(detector, 'pitch_threshold'):
            print(
                f"Loading pitch threshold from config: {config['pitch_threshold']}")
            detector.pitch_threshold = config['pitch_threshold']

        if 'roll_threshold' in config and hasattr(detector, 'roll_threshold'):
            print(
                f"Loading roll threshold from config: {config['roll_threshold']}")
            detector.roll_threshold = config['roll_threshold']

        if 'suspicion_threshold' in config and hasattr(detector, 'suspicion_threshold'):
            print(
                f"Loading suspicion threshold from config: {config['suspicion_threshold']}")
            detector.suspicion_threshold = config['suspicion_threshold']

        if 'hand_face_threshold' in config and hasattr(detector, 'suspicion_scorer'):
            print(
                f"Loading hand-face threshold from config: {config['hand_face_threshold']}")
            detector.suspicion_scorer.hand_face_threshold = config['hand_face_threshold']

        if 'hand_object_threshold' in config and hasattr(detector, 'suspicion_scorer'):
            print(
                f"Loading hand-object threshold from config: {config['hand_object_threshold']}")
            detector.suspicion_scorer.hand_object_threshold = config['hand_object_threshold']

        if 'enable_frame_skipping' in config and hasattr(detector, 'enable_frame_skipping'):
            print(
                f"Loading frame skipping from config: {config['enable_frame_skipping']}")
            detector.enable_frame_skipping = config['enable_frame_skipping']

        if 'frame_skip_threshold_ms' in config and hasattr(detector, 'frame_skip_threshold_ms'):
            print(
                f"Loading frame skip threshold from config: {config['frame_skip_threshold_ms']}")
            detector.frame_skip_threshold_ms = config['frame_skip_threshold_ms']

        if 'max_frame_skip' in config and hasattr(detector, 'max_frame_skip'):
            print(
                f"Loading max frame skip from config: {config['max_frame_skip']}")
            detector.max_frame_skip = config['max_frame_skip']

        if 'processing_interval_ms' in config and hasattr(detector, 'processing_interval_ms'):
            print(
                f"Loading processing interval from config: {config['processing_interval_ms']}")
            detector.processing_interval_ms = config['processing_interval_ms']

        if 'camera_source' in config and hasattr(detector, 'camera_source'):
            print(
                f"Loading camera source from config: {config['camera_source']}")
            detector.camera_source = config['camera_source']

        if 'camera_resolution' in config and hasattr(detector, 'camera_resolution'):
            print(
                f"Loading camera resolution from config: {config['camera_resolution']}")
            detector.camera_resolution = config['camera_resolution']

            # Update image size based on resolution
            if config['camera_resolution'] == "480p":
                detector.img_processing_size = (640, 480)
            elif config['camera_resolution'] == "720p":
                detector.img_processing_size = (1280, 720)
            elif config['camera_resolution'] == "1080p":
                detector.img_processing_size = (1920, 1080)

        if 'camera_fps' in config and hasattr(detector, 'camera_fps'):
            print(f"Loading camera FPS from config: {config['camera_fps']}")
            detector.camera_fps = config['camera_fps']

        if 'camera_label' in config and hasattr(detector, 'camera_label'):
            print(
                f"Loading camera label from config: {config['camera_label']}")
            detector.camera_label = config['camera_label']

        if 'auto_reconnect' in config and hasattr(detector, 'auto_reconnect'):
            print(
                f"Loading auto-reconnect from config: {config['auto_reconnect']}")
            detector.auto_reconnect = config['auto_reconnect']

        if 'auto_save' in config and hasattr(detector, 'auto_save_enabled'):
            print(f"Loading auto-save from config: {config['auto_save']}")
            detector.auto_save_enabled = config['auto_save']

        if 'suspicion_save_threshold' in config and hasattr(detector, 'suspicion_save_threshold'):
            print(
                f"Loading suspicion save threshold from config: {config['suspicion_save_threshold']}")
            detector.suspicion_save_threshold = config['suspicion_save_threshold']

        if 'retention_period' in config and hasattr(detector, 'retention_period'):
            print(
                f"Loading retention period from config: {config['retention_period']}")
            detector.retention_period = config['retention_period']

        if 'session_recording' in config and hasattr(detector, 'session_recording'):
            print(
                f"Loading session recording from config: {config['session_recording']}")
            detector.session_recording = config['session_recording']

        if 'show_bbox' in config and hasattr(detector, 'show_bbox'):
            print(
                f"Loading show bounding boxes from config: {config['show_bbox']}")
            detector.show_bbox = config['show_bbox']

        if 'show_pose' in config and hasattr(detector, 'show_pose'):
            print(
                f"Loading show pose skeleton from config: {config['show_pose']}")
            detector.show_pose = config['show_pose']

        if 'show_confidence' in config and hasattr(detector, 'show_confidence'):
            print(
                f"Loading show confidence scores from config: {config['show_confidence']}")
            detector.show_confidence = config['show_confidence']

        if 'device' in config and hasattr(detector, 'device'):
            torch_device = config['device']
            if config['device'] == 'gpu' and torch.cuda.is_available():
                torch_device = 'cuda'
            elif config['device'] == 'gpu':
                print("GPU selected in config but CUDA not available, using CPU")
                torch_device = 'cpu'
            print(f"Loading device from config: {torch_device}")
            detector.device = torch_device
            detector.model.to(torch_device)

        print("Configuration loaded from config.json")
    except Exception as e:
        print(f"Error loading configuration from config.json: {e}")

# NOTE: Using detector.suspicion_scorer instead of creating a separate instance
# This ensures config changes propagate correctly
print("SuspicionScorer ready (via detector.suspicion_scorer)")

# Runtime threshold for alerts (can be updated via config)
runtime_suspicion_threshold = SUSPICION_THRESHOLD  # Start with default
if CONFIG_FILE.exists():
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            runtime_suspicion_threshold = config.get(
                'suspicion_threshold', SUSPICION_THRESHOLD)
            print(f"Alert threshold set to: {runtime_suspicion_threshold}%")
    except:
        pass

print("=" * 50)

# ============================================
# SECURE DELETION SCHEDULER
# ============================================


def run_retention_cleanup():
    """Context-aware background task to clean up expired evidence"""
    # Delay to let app startup finish
    time.sleep(8)
    print("\n" + "=" * 40)
    print("SECURITY GUARD: ACTIVE & MONITORING DATA")
    print("=" * 40)

    while True:
        try:
            # Get retention period from config
            retention_period = 7
            if CONFIG_FILE.exists():
                try:
                    with open(CONFIG_FILE, 'r') as f:
                        config = json.load(f)
                        retention_period = config.get('retention_period', 7)
                except:
                    pass

            print(
                f"🔍 Security Check: Scanning history (Retention: {retention_period} days)...")

            # check HISTORY_DIR (cards)
            print(f"  └─ Target: {HISTORY_DIR}")

            # check HISTORY_DIR (cards)
            if HISTORY_DIR.exists():
                count = 0
                for card_folder in HISTORY_DIR.iterdir():
                    if card_folder.is_dir():
                        is_expired = SecureEraser.is_expired(
                            card_folder.name, retention_period)
                        # print(f"DEBUG: Checking {card_folder.name} -> Expired? {is_expired}")

                        if is_expired:
                            print(
                                f"Time to securely delete expired card: {card_folder.name}")
                            SecureEraser.secure_delete_tree(card_folder)
                            count += 1
                if count > 0:
                    print(f"Securely deleted {count} expired cards")
                else:
                    print("DEBUG: No expired cards found.")

            # Also trigger detector's EvidenceSaver cleanup (which we'll update to use SecureEraser too)
            # if hasattr(detector, 'evidence_saver'):
            #    detector.evidence_saver._cleanup_old_evidence()

        except Exception as e:
            print(f"Error in retention cleanup loop: {e}")
            # Wait a bit before retrying to avoid tight loops on error
            time.sleep(60)

        # Sleep for 1 hour before next run
        time.sleep(3600)


# Start background thread (Only if not in reloader process)
if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    cleanup_thread = threading.Thread(
        target=run_retention_cleanup, daemon=True)
    cleanup_thread.start()
elif not app.debug:
    # If debug is off, start normally
    cleanup_thread = threading.Thread(
        target=run_retention_cleanup, daemon=True)
    cleanup_thread.start()

# ============================================
# SESSION MANAGEMENT
# ============================================

# Active session state (in-memory, one session at a time)
active_session = None
pending_alerts = {}
is_processing_frame = False  # The "Drop-if-Busy" Lock


def create_session(session_name, camera_id="cam_01", department=None, subject=None):
    """Create a new monitoring session"""
    session_id = "sess_" + datetime.now().strftime('%Y%m%d_%H%M%S')
    session = {
        "session_id": session_id,
        "session_name": session_name,
        "department": department,
        "subject": subject,
        "camera_id": camera_id,
        "started_at": datetime.now().isoformat(),
        "ended_at": None,
        "status": "active"
    }
    return session


def end_session():
    """End the current session"""
    global active_session
    if active_session:
        active_session["ended_at"] = datetime.now().isoformat()
        active_session["status"] = "ended"
    return active_session


# ============================================
# EVENT CARD MANAGEMENT
# ============================================

def get_card_path(session_id, student_id):
    """Get the path for a student's event card in a session"""
    card_folder = HISTORY_DIR / (session_id + "_" + student_id)
    return card_folder


def get_card(session_id, student_id):
    """Load an existing card if it exists"""
    card_folder = get_card_path(session_id, student_id)
    card_file = card_folder / "card.json"

    if card_file.exists():
        with open(card_file, 'r') as f:
            return json.load(f)
    return None


def create_or_update_card(session_id, session_name, student_id,
                          student_name, event_data, status,
                          department=None, subject=None):
    """
    Create a new card or add event to existing card.

    Logic:
    - If card exists for (session_id + student_id) -> add event to timeline
    - If card doesn't exist -> create new card with this event
    """
    card_folder = get_card_path(session_id, student_id)
    card_folder.mkdir(parents=True, exist_ok=True)

    card_file = card_folder / "card.json"
    evidence_folder = card_folder / "evidence"
    evidence_folder.mkdir(exist_ok=True)

    # Generate event ID
    event_id = "evt_" + datetime.now().strftime('%H%M%S_%f')

    # Prepare event entry
    event_entry = {
        "event_id": event_id,
        "timestamp": event_data.get("timestamp", datetime.now().isoformat()),
        "type": event_data.get("type", "unknown"),
        "suspicion_score": event_data.get("suspicion_score", 0),
        # Convert to 0-1 scale
        "confidence": event_data.get("suspicion_score", 0) / 100.0,
        "reasons": event_data.get("reasons", []),
        "status": status,
        "notes": event_data.get("notes", ""),
        "evidence_count": 2,  # Always have frame + crop
        "evidence": {
            "frame": f"{event_id}/frame.jpg",
            "crop": f"{event_id}/crop.jpg"
        }
    }

    # Save evidence for this event
    event_evidence_folder = evidence_folder / event_id
    event_evidence_folder.mkdir(exist_ok=True)

    if "frame_base64" in event_data and event_data["frame_base64"]:
        save_evidence_image(
            event_data["frame_base64"], event_evidence_folder / "frame.jpg")

    if "crop_base64" in event_data and event_data["crop_base64"]:
        save_evidence_image(
            event_data["crop_base64"], event_evidence_folder / "crop.jpg")

    # Check if card exists
    existing_card = get_card(session_id, student_id)

    if existing_card:
        # Add event to existing card
        existing_card["events"].append(event_entry)
        existing_card["updated_at"] = datetime.now().isoformat()
        if status == "confirmed":
            existing_card["status"] = "confirmed"
        card = existing_card
    else:
        # Create new card
        card = {
            "card_id": session_id + "_" + student_id,
            "session_id": session_id,
            "session_name": session_name,
            "department": department,
            "exam_name": subject,
            "student_id": student_id,
            "student_name": student_name,
            "status": status,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "events": [event_entry]
        }

    # Save card
    with open(card_file, 'w') as f:
        json.dump(card, f, indent=2)

    return card


def save_evidence_image(base64_data, filepath):
    """Save a base64 encoded image to file"""
    try:
        if ',' in base64_data:
            base64_data = base64_data.split(',', 1)[1]

        img_data = base64.b64decode(base64_data)
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is not None:
            cv2.imwrite(str(filepath), img)
    except Exception as e:
        print("Error saving evidence image: " + str(e))


def get_all_cards():
    """Get all event cards from history"""
    cards = []

    if not HISTORY_DIR.exists():
        return cards

    # Get retention period from config
    retention_period = 7  # Default
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                retention_period = config.get('retention_period', 7)
        except Exception as e:
            print("Error loading retention period from config: " + str(e))

    for card_folder in HISTORY_DIR.iterdir():
        if card_folder.is_dir():
            card_file = card_folder / "card.json"
            if card_file.exists():
                try:
                    with open(card_file, 'r') as f:
                        card = json.load(f)

                        # Add deletion_date calculation
                        if 'created_at' in card:
                            try:
                                created_at = datetime.fromisoformat(
                                    card['created_at'])
                                from datetime import timedelta
                                deletion_date = created_at + \
                                    timedelta(days=retention_period)
                                card['deletion_date'] = deletion_date.isoformat()
                                card['retention_period'] = retention_period
                            except Exception as e:
                                print(
                                    f"Error calculating deletion date for card {card.get('card_id', 'unknown')}: {e}")

                        cards.append(card)
                except Exception as e:
                    print("Error loading card: " + str(e))

    cards.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return cards


# ============================================
# FRAME ANNOTATION
# ============================================


# ============================================
# ALERT GENERATION
# ============================================

def get_alert_metadata(detection):
    """
    Check if detection warrants an alert and determine metadata (reasons, type).
    Returns (reasons, type) if suspicion >= threshold, else (None, None).
    """
    if detection.get('class_id') != 0:
        return None, None

    behavior = detection.get('behavior', {})
    suspicion = behavior.get('suspicion', {})
    suspicion_score = suspicion.get('smoothed', 0) * 100

    threshold = runtime_suspicion_threshold

    if suspicion_score < threshold:
        return None, None

    reasons = []
    components = suspicion.get('components', {})

    # Head orientation check
    if components.get('head', 0) > 0.1:
        head_orientation = behavior.get('head_orientation', {})
        if head_orientation:
            yaw = head_orientation.get('yaw', 0)
            pitch = head_orientation.get('pitch', 0)
            if abs(yaw) > 25 or abs(pitch) > 20:
                reasons.append("Looking away")

    # Hand near face (threshold 0.1 = 10%)
    if components.get('hands_face', 0) > 0.1:
        reasons.append("Hand near face")

    # Object detection check
    if components.get('hands_object', 0) > 0.1:
        hands = behavior.get('hands', {})
        phone_detected = False
        other_object_detected = False

        for side in ['left', 'right']:
            hand = hands.get(side, {})
            if hand.get('near_object') and hand.get('object_class'):
                obj_class = hand.get('object_class', '').lower()

                if 'phone' in obj_class or 'cell' in obj_class or 'mobile' in obj_class:
                    phone_detected = True
                else:
                    other_object_detected = True

        if phone_detected:
            reasons.append("Phone usage detected")
        if other_object_detected:
            reasons.append("Suspicious object detected")

    if not reasons:
        reasons = ["Suspicious behavior detected"]

    alert_type = reasons[0].split()[0].lower() if reasons else "unknown"
    return reasons, alert_type


def generate_alert_from_detection(detection, frame, reasons=None, alert_type=None):
    """
    Generate full alert data with images.
    If reasons/type are not provided, they will be calculated.
    """
    if reasons is None or alert_type is None:
        reasons, alert_type = get_alert_metadata(detection)

    if not reasons:
        return None

    behavior = detection.get('behavior', {})
    suspicion = behavior.get('suspicion', {})
    suspicion_score = suspicion.get('smoothed', 0) * 100

    # Get detection crop
    bbox = detection.get('bbox', [0, 0, 0, 0])
    x1, y1, x2, y2 = [int(v) for v in bbox]

    h, w = frame.shape[:2]
    pad = 20
    x1 = max(0, x1 - pad)
    y1 = max(0, y1 - pad)
    x2 = min(w, x2 + pad)
    y2 = min(h, y2 + pad)

    crop = frame[y1:y2, x1:x2]

    # Encode images with balanced quality (Speed + Detail)
    _, frame_buffer = cv2.imencode(
        '.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
    frame_b64 = base64.b64encode(frame_buffer).decode('utf-8')

    _, crop_buffer = cv2.imencode(
        '.jpg', crop, [cv2.IMWRITE_JPEG_QUALITY, 65])
    crop_b64 = base64.b64encode(crop_buffer).decode('utf-8')

    # Create alert
    alert_id = "alert_" + datetime.now().strftime('%Y%m%d_%H%M%S_%f')

    alert = {
        "alert_id": alert_id,
        "track_id": detection.get('track_id'),
        "id_type": detection.get('id_type', 'TRACK'),
        "primary_id": detection.get('primary_id', detection.get('track_id', '?')),
        "student_id": detection.get('student_id', ''),
        "student_name": detection.get('student_name', ''),
        "timestamp": datetime.now().isoformat(),
        "suspicion_score": int(suspicion_score),
        "reasons": reasons,
        "type": alert_type,
        "frame_base64": frame_b64,
        "crop_base64": crop_b64,
        "bbox": bbox
    }

    return alert


# ============================================
# SOCKET EVENTS
# ============================================

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('connection_status', {'status': 'connected'})


@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')


@socketio.on('start_session')
def handle_start_session(data):
    """Start a new monitoring session"""
    global active_session, pending_alerts

    session_name = data.get('session_name', 'Unnamed Exam')
    camera_id = data.get('camera_id', 'cam_01')
    department = data.get('department')
    subject = data.get('subject')

    if active_session and active_session['status'] == 'active':
        end_session()

    pending_alerts = {}
    active_session = create_session(
        session_name, camera_id, department, subject)

    print(
        f"Session started: {active_session['session_id']} - {session_name} ({department}/{subject})")
    emit('session_started', active_session)


@socketio.on('stop_session')
def handle_stop_session(data=None):
    """Stop the current session"""
    global active_session

    if active_session:
        session_id = active_session.get('session_id', 'unknown')
        ended_session = end_session()
        active_session = None  # CRITICAL: Clear global session state
        print(f"Session ended: {session_id}")
        emit('session_stopped', ended_session)
    else:
        emit('session_stopped', {'error': 'No active session'})


@socketio.on('video_frame')
def handle_video_frame(data):
    """Process a video frame from the frontend"""
    global pending_alerts, active_session, is_processing_frame

    # 🛑 STABILITY LOCK: If server is busy, DROP the frame to keep MS low
    if is_processing_frame:
        return

    try:
        is_processing_frame = True
        if isinstance(data, str):
            header, encoded = data.split(',', 1)
            debug_boxes = True
        else:
            image_data = data.get('image', data.get('frame', ''))
            debug_boxes = data.get('debug_boxes', True)
            if ',' in image_data:
                header, encoded = image_data.split(',', 1)
            else:
                encoded = image_data

        nparr = np.frombuffer(base64.b64decode(encoded), np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            return

        # 🔧 Check GPU memory before processing
        if detector.device == 'cuda':
            try:
                mem_allocated = torch.cuda.memory_allocated() / 1024**3  # GB
                mem_reserved = torch.cuda.memory_reserved() / 1024**3     # GB

                # If memory usage is too high, force cleanup
                if mem_reserved > 7.0:  # More than 7GB on 8GB card
                    print(
                        f"⚠️ High GPU memory usage: {mem_reserved:.2f}GB - forcing cleanup")
                    torch.cuda.empty_cache()
                    import gc
                    gc.collect()
            except Exception as mem_err:
                print(f"Memory check error: {mem_err}")

        detection_result = detector.detect_frame(frame)

        if detection_result is None:
            print("⚠️ Detection returned None - skipping frame")
            return

        detections = detection_result.get('detections', [])

        processed_detections = []
        new_alerts = []

        for det in detections:
            # Prepare sanitized data for frontend
            sanitized = {
                'class_id': det['class_id'],
                'confidence': det['confidence'],
                'bbox': det['bbox'],
                'track_id': det.get('track_id'),
                'id_type': det.get('id_type'),
                'primary_id': det.get('primary_id'),
                'student_id': det.get('student_id'),
                'student_name': det.get('student_name'),
                'behavior': {}
            }

            if 'behavior' in det:
                behavior = det['behavior']
                if detector.show_pose and 'pose_landmarks' in behavior:
                    sanitized['pose_landmarks'] = behavior['pose_landmarks']
                if 'head_orientation' in behavior:
                    sanitized['behavior']['head_orientation'] = behavior['head_orientation']
                if 'hands' in behavior:
                    sanitized['behavior']['hands'] = behavior['hands']
                if 'suspicion' in behavior:
                    sanitized['behavior']['suspicion'] = behavior['suspicion']

                # Use existing suspicion result from detection
                suspicion_result = behavior.get('suspicion', {})
                unified_score = round(
                    suspicion_result.get('smoothed', 0) * 100)
                sanitized['unified_score'] = unified_score

                # Logic for generating alerts
                if active_session and active_session['status'] == 'active' and unified_score >= runtime_suspicion_threshold:
                    # 1. Get lightweight metadata first for dedup check
                    reasons, event_type = get_alert_metadata(det)

                    if reasons:
                        dedup_id = det.get('student_id') or det.get(
                            'primary_id') or det.get('track_id')

                        # 2. Precise dedup check: only skip if THIS person already has THIS type of alert
                        should_alert = True
                        for existing in pending_alerts.values():
                            existing_dedup_id = existing.get('student_id') or existing.get(
                                'primary_id', existing.get('track_id'))
                            if existing_dedup_id == dedup_id and existing.get('type') == event_type:
                                should_alert = False
                                break

                        if should_alert:
                            # 3. Only now do the heavy encoding/image processing
                            alert = generate_alert_from_detection(
                                det, frame, reasons, event_type)
                            if alert:
                                pending_alerts[alert['alert_id']] = alert
                                new_alerts.append(alert)

            processed_detections.append(sanitized)

        perf_stats = detector.get_performance_stats()

        emit('processed_frame', {
            'detections': processed_detections,
            'performance_stats': perf_stats
        }, broadcast=False)

        for alert in new_alerts:
            alert_notification = {
                'alert_id': alert['alert_id'],
                'track_id': alert['track_id'],
                'id_type': alert.get('id_type', 'TRACK'),
                'primary_id': alert.get('primary_id', alert['track_id']),
                'student_id': alert.get('student_id', ''),
                'student_name': alert.get('student_name', ''),
                'timestamp': alert['timestamp'],
                'suspicion_score': alert['suspicion_score'],
                'reasons': alert['reasons'],
                'type': alert['type'],
                'crop_base64': alert['crop_base64']
            }
            emit('new_alert', alert_notification)

    except Exception as e:
        print("Error processing frame: " + str(e))
        import traceback
        traceback.print_exc()
    finally:
        is_processing_frame = False  # Release lock so next frame can enter


@socketio.on('review_alert')
def handle_review_alert(data):
    """Handle proctor's review of an alert (confirm/decline)"""
    global pending_alerts, active_session

    alert_id = data.get('alert_id')
    decision = data.get('decision')
    student_id = data.get('student_id', '').strip()
    student_name = data.get('student_name', '').strip()
    notes = data.get('notes', '')

    if not alert_id or alert_id not in pending_alerts:
        emit('review_result', {'success': False, 'error': 'Alert not found'})
        return

    alert = pending_alerts[alert_id]

    if decision == 'confirm' and not student_id:
        emit('review_result', {'success': False,
             'error': 'Student ID required for confirmation'})
        return

    if decision == 'decline' and not student_id:
        track_id = alert.get('track_id', '?')
        del pending_alerts[alert_id]
        print(f"❌ Alert declined and removed from pending (Track #{track_id})")
        emit('review_result', {
            'success': True,
            'action': 'discarded',
            'message': 'Alert discarded (no student ID)'
        })
        return

    # Check if we have a session (can be active or stopped - we still save events after stopping)
    if not active_session:
        emit('review_result', {'success': False, 'error': 'No session found'})
        return

    session_id = active_session['session_id']
    session_name = active_session['session_name']

    print(
        f"Saving event - Session: {session_id}, Student: {student_id}, Decision: {decision}")

    event_data = {
        'timestamp': alert['timestamp'],
        'type': alert['type'],
        'suspicion_score': alert['suspicion_score'],
        'reasons': alert['reasons'],
        'notes': notes,
        'frame_base64': alert.get('frame_base64'),
        'crop_base64': alert.get('crop_base64')
    }

    status = 'confirmed' if decision == 'confirm' else 'declined'

    try:
        card = create_or_update_card(
            session_id=session_id,
            session_name=session_name,
            student_id=student_id,
            # Fallback if name was cleared
            student_name=student_name or ("Student " + student_id),
            event_data=event_data,
            status=status,
            department=active_session.get('department'),
            subject=active_session.get('subject')
        )

        print(f"Card created/updated: {card['card_id']}")

        emit('review_result', {
            'success': True,
            'action': status,
            'card_id': card['card_id'],
            'is_new_card': len(card['events']) == 1,
            'message': 'Event ' + status + ' and saved'
        })
    except Exception as e:
        print(f"Error saving card: {e}")
        import traceback
        traceback.print_exc()
        emit('review_result', {'success': False,
             'error': 'Error saving card: ' + str(e)})
    finally:
        # CRITICAL: Always remove from pending, otherwise new alerts for this person will be blocked
        if alert_id in pending_alerts:
            track_id = pending_alerts[alert_id].get('track_id', '?')
            del pending_alerts[alert_id]
            print(
                f"✅ Alert processed and removed from pending (Track #{track_id})")


@socketio.on('get_pending_alerts')
def handle_get_pending_alerts():
    """Get list of pending alerts"""
    alerts = []
    for alert in pending_alerts.values():
        alerts.append({
            'alert_id': alert['alert_id'],
            'track_id': alert['track_id'],
            'timestamp': alert['timestamp'],
            'suspicion_score': alert['suspicion_score'],
            'reasons': alert['reasons'],
            'type': alert['type'],
            'crop_base64': alert['crop_base64']
        })
    emit('pending_alerts_list', {'alerts': alerts})


# ============================================
# HTTP ROUTES
# ============================================

@app.route('/')
def index():
    """Serve the login page as entry point"""
    return send_from_directory(Path(__file__).parent, 'login.html')


@app.route('/dashboard')
def dashboard():
    """Serve the main dashboard"""
    return send_from_directory(Path(__file__).parent, 'dashboard.html')


@app.route('/logout')
def logout():
    """Logout user and redirect to login page"""
    return send_from_directory(Path(__file__).parent, 'login.html')


@app.route('/api/session/active')
def get_active_session():
    """Get the currently active session"""
    if active_session and active_session['status'] == 'active':
        return jsonify(active_session)
    return jsonify({'session': None})


@app.route('/api/history/cards')
def get_history_cards():
    """Get all event cards for history page"""
    cards = get_all_cards()
    return jsonify({'cards': cards})


@app.route('/api/history/card/<card_id>')
def get_card_detail(card_id):
    """Get detailed card data including evidence paths"""
    card_folder = HISTORY_DIR / card_id
    if not card_folder.exists():
        return jsonify({'error': 'Card not found'}), 404

    card_file = card_folder / "card.json"
    if not card_file.exists():
        return jsonify({'error': 'Card data not found'}), 404

    with open(card_file, 'r') as f:
        card = json.load(f)

    evidence_folder = card_folder / "evidence"
    for event in card.get('events', []):
        event_id = event['event_id']
        event_evidence = evidence_folder / event_id
        if event_evidence.exists():
            event['evidence'] = {
                'frame': '/api/evidence/' + card_id + '/' + event_id + '/frame.jpg',
                'crop': '/api/evidence/' + card_id + '/' + event_id + '/crop.jpg'
            }

    return jsonify(card)


@app.route('/api/evidence/<card_id>/<event_id>/<filename>')
def get_evidence_file(card_id, event_id, filename):
    """Serve evidence images"""
    filepath = HISTORY_DIR / card_id / "evidence" / event_id / filename
    if filepath.exists():
        return send_file(filepath)
    return jsonify({'error': 'File not found'}), 404


@app.route('/api/login', methods=['POST'])
def api_login():
    """Authenticate user credentials"""
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({'success': False, 'error': 'Username and password required'}), 400

    if not USERS_FILE.exists():
        return jsonify({'success': False, 'error': 'User database not found'}), 500

    with open(USERS_FILE, 'r') as f:
        users = json.load(f)

    for user in users:
        if user.get('username') == username and user.get('password') == password:
            return jsonify({
                'success': True,
                'user': {
                    'id': user.get('id'),
                    'username': user.get('username'),
                    'email': user.get('email'),
                    'role': user.get('role')
                }
            })

    return jsonify({'success': False, 'error': 'Invalid username or password'}), 401


@app.route('/api/users', methods=['GET'])
def get_users():
    """Get list of users (for settings/admin)"""
    if USERS_FILE.exists():
        with open(USERS_FILE, 'r') as f:
            users = json.load(f)
        # Include passwords for admin users (check current user role from localStorage)
        current_user_role = request.args.get('current_user_role', '')
        if current_user_role == 'administrator':
            return jsonify({'users': users})
        else:
            return jsonify({'users': [{k: v for k, v in u.items() if k != 'password'} for u in users]})
    return jsonify({'users': []})


@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            return jsonify(json.load(f))
    return jsonify({
        'suspicion_threshold': SUSPICION_THRESHOLD,
        'model_size': 'medium',
        'confidence_threshold': 0.4
    })


@app.route('/api/config', methods=['POST'])
def update_config():
    """Update configuration"""
    config = request.get_json()

    # Check if model_size changed and switch model if needed
    if 'model_size' in config:
        new_model_size = config['model_size']
        if detector.model_size != new_model_size:
            print(
                f"Switching model from {detector.model_size} to {new_model_size}")
            if detector.switch_model(new_model_size):
                print(f"Model switched successfully to {new_model_size}")
            else:
                print(f"Failed to switch model to {new_model_size}")
                return jsonify({'success': False, 'error': f'Failed to switch to model size {new_model_size}'})

    # Update image processing size if changed
    if 'img_processing_size' in config:
        new_img_size = config['img_processing_size']
        if hasattr(detector, 'img_size') and detector.img_size != new_img_size:
            print(
                f"Updating image processing size from {detector.img_size} to {new_img_size}")
            detector.img_size = new_img_size

    # Update confidence threshold if changed
    if 'confidence_threshold' in config:
        new_conf_threshold = config['confidence_threshold']
        if hasattr(detector, 'confidence_threshold') and detector.confidence_threshold != new_conf_threshold:
            print(
                f"Updating confidence threshold from {detector.confidence_threshold} to {new_conf_threshold}")
            detector.confidence_threshold = new_conf_threshold

    # Update device if changed
    if 'device' in config:
        new_device = config['device']
        if hasattr(detector, 'device') and detector.device != new_device:
            print(f"Updating device from {detector.device} to {new_device}")
            # Convert string values to torch device format
            torch_device = new_device
            if new_device == 'gpu' and torch.cuda.is_available():
                torch_device = 'cuda'
            elif new_device == 'gpu':
                print("GPU selected but CUDA not available, using CPU")
                torch_device = 'cpu'

            # Update detector device
            detector.device = torch_device
            detector.model.to(torch_device)

    # Update model complexity if changed
    if 'model_complexity' in config:
        new_complexity = int(config['model_complexity'])
        if hasattr(detector, 'set_model_complexity'):
            detector.set_model_complexity(new_complexity)

    # Update yaw threshold if changed
    if 'yaw_threshold' in config:
        new_yaw_threshold = config['yaw_threshold']
        if hasattr(detector, 'yaw_threshold') and detector.yaw_threshold != new_yaw_threshold:
            print(
                f"Updating yaw threshold from {detector.yaw_threshold} to {new_yaw_threshold}")
            detector.yaw_threshold = new_yaw_threshold
        # Also sync to suspicion_scorer for consistent scoring
        if hasattr(detector, 'suspicion_scorer'):
            detector.suspicion_scorer.yaw_threshold = new_yaw_threshold

    # Update pitch threshold if changed
    if 'pitch_threshold' in config:
        new_pitch_threshold = config['pitch_threshold']
        if hasattr(detector, 'pitch_threshold') and detector.pitch_threshold != new_pitch_threshold:
            print(
                f"Updating pitch threshold from {detector.pitch_threshold} to {new_pitch_threshold}")
            detector.pitch_threshold = new_pitch_threshold
        # Also sync to suspicion_scorer for consistent scoring
        if hasattr(detector, 'suspicion_scorer'):
            detector.suspicion_scorer.pitch_threshold = new_pitch_threshold

    # Update roll threshold if changed
    if 'roll_threshold' in config:
        new_roll_threshold = config['roll_threshold']
        if hasattr(detector, 'roll_threshold') and detector.roll_threshold != new_roll_threshold:
            print(
                f"Updating roll threshold from {detector.roll_threshold} to {new_roll_threshold}")
            detector.roll_threshold = new_roll_threshold

    # Update suspicion threshold if changed
    if 'suspicion_threshold' in config:
        new_suspicion_threshold = config['suspicion_threshold']
        if hasattr(detector, 'suspicion_threshold') and detector.suspicion_threshold != new_suspicion_threshold:
            print(
                f"Updating suspicion threshold from {detector.suspicion_threshold} to {new_suspicion_threshold}")
            detector.suspicion_threshold = new_suspicion_threshold

        # Also sync to suspicion_scorer
        if hasattr(detector, 'suspicion_scorer'):
            detector.suspicion_scorer.suspicion_threshold = new_suspicion_threshold

        # Update runtime threshold for alert generation
        global runtime_suspicion_threshold
        runtime_suspicion_threshold = new_suspicion_threshold
        print(f"Alert threshold updated to: {runtime_suspicion_threshold}%")

    # Update hand-face threshold if changed
    if 'hand_face_threshold' in config:
        new_hand_face_threshold = config['hand_face_threshold']
        if hasattr(detector, 'suspicion_scorer'):
            if detector.suspicion_scorer.hand_face_threshold != new_hand_face_threshold:
                print(
                    f"Updating hand-face threshold from {detector.suspicion_scorer.hand_face_threshold} to {new_hand_face_threshold}")
                detector.suspicion_scorer.hand_face_threshold = new_hand_face_threshold

    # Update hand-object threshold if changed
    if 'hand_object_threshold' in config:
        new_hand_object_threshold = config['hand_object_threshold']
        if hasattr(detector, 'suspicion_scorer'):
            if detector.suspicion_scorer.hand_object_threshold != new_hand_object_threshold:
                print(
                    f"Updating hand-object threshold from {detector.suspicion_scorer.hand_object_threshold} to {new_hand_object_threshold}")
                detector.suspicion_scorer.hand_object_threshold = new_hand_object_threshold

    # Update smoothing factor if changed (Advanced settings)
    if 'smoothing_factor' in config:
        new_smoothing = config['smoothing_factor']
        if hasattr(detector, 'suspicion_scorer'):
            if detector.suspicion_scorer.smoothing_factor != new_smoothing:
                print(f"Updating smoothing factor to {new_smoothing}")
                detector.suspicion_scorer.smoothing_factor = new_smoothing

    # Update history length if changed (Advanced settings)
    if 'history_length' in config:
        new_history_length = config['history_length']
        if hasattr(detector, 'suspicion_scorer'):
            if detector.suspicion_scorer.history_length != new_history_length:
                print(f"Updating history length to {new_history_length}")
                detector.suspicion_scorer.history_length = new_history_length

    # Update frame skipping if changed
    if 'enable_frame_skipping' in config:
        new_enable_frame_skipping = config['enable_frame_skipping']
        if hasattr(detector, 'enable_frame_skipping') and detector.enable_frame_skipping != new_enable_frame_skipping:
            print(
                f"Updating frame skipping from {detector.enable_frame_skipping} to {new_enable_frame_skipping}")
            detector.enable_frame_skipping = new_enable_frame_skipping

    # Update frame skip threshold if changed
    if 'frame_skip_threshold_ms' in config:
        new_frame_skip_threshold_ms = config['frame_skip_threshold_ms']
        if hasattr(detector, 'frame_skip_threshold_ms') and detector.frame_skip_threshold_ms != new_frame_skip_threshold_ms:
            print(
                f"Updating frame skip threshold from {detector.frame_skip_threshold_ms} to {new_frame_skip_threshold_ms}")
            detector.frame_skip_threshold_ms = new_frame_skip_threshold_ms

    # Update max frame skip if changed
    if 'max_frame_skip' in config:
        new_max_frame_skip = config['max_frame_skip']
        if hasattr(detector, 'max_frame_skip') and detector.max_frame_skip != new_max_frame_skip:
            print(
                f"Updating max frame skip from {detector.max_frame_skip} to {new_max_frame_skip}")
            detector.max_frame_skip = new_max_frame_skip

    # Update processing interval if changed
    if 'processing_interval_ms' in config:
        new_processing_interval_ms = config['processing_interval_ms']
        if hasattr(detector, 'processing_interval_ms') and detector.processing_interval_ms != new_processing_interval_ms:
            print(
                f"Updating processing interval from {detector.processing_interval_ms} to {new_processing_interval_ms}")
            detector.processing_interval_ms = new_processing_interval_ms

    # Update camera source if changed
    if 'camera_source' in config:
        new_camera_source = config['camera_source']
        if hasattr(detector, 'camera_source') and detector.camera_source != new_camera_source:
            print(
                f"Updating camera source from {detector.camera_source} to {new_camera_source}")
            detector.camera_source = new_camera_source

    # Update camera resolution if changed
    if 'camera_resolution' in config:
        new_camera_resolution = config['camera_resolution']
        if hasattr(detector, 'camera_resolution') and detector.camera_resolution != new_camera_resolution:
            print(
                f"Updating camera resolution from {detector.camera_resolution} to {new_camera_resolution}")
            detector.camera_resolution = new_camera_resolution

            # Update image size based on resolution
            if new_camera_resolution == "480p":
                detector.img_processing_size = (640, 480)
            elif new_camera_resolution == "720p":
                detector.img_processing_size = (1280, 720)
            elif new_camera_resolution == "1080p":
                detector.img_processing_size = (1920, 1080)

    # Update camera FPS if changed
    if 'camera_fps' in config:
        new_camera_fps = config['camera_fps']
        if hasattr(detector, 'camera_fps') and detector.camera_fps != new_camera_fps:
            print(
                f"Updating camera FPS from {detector.camera_fps} to {new_camera_fps}")
            detector.camera_fps = new_camera_fps

    # Update camera label if changed
    if 'camera_label' in config:
        new_camera_label = config['camera_label']
        if hasattr(detector, 'camera_label') and detector.camera_label != new_camera_label:
            print(
                f"Updating camera label from {detector.camera_label} to {new_camera_label}")
            detector.camera_label = new_camera_label

    # Update auto-reconnect if changed
    if 'auto_reconnect' in config:
        new_auto_reconnect = config['auto_reconnect']
        if hasattr(detector, 'auto_reconnect') and detector.auto_reconnect != new_auto_reconnect:
            print(
                f"Updating auto-reconnect from {detector.auto_reconnect} to {new_auto_reconnect}")
            detector.auto_reconnect = new_auto_reconnect

    # Update auto-save if changed
    if 'auto_save' in config:
        new_auto_save = config['auto_save']
        if hasattr(detector, 'auto_save_enabled') and detector.auto_save_enabled != new_auto_save:
            print(
                f"Updating auto-save from {detector.auto_save_enabled} to {new_auto_save}")
            detector.auto_save_enabled = new_auto_save

    # Update suspicion save threshold if changed
    if 'suspicion_save_threshold' in config:
        new_suspicion_save_threshold = config['suspicion_save_threshold']
        if hasattr(detector, 'suspicion_save_threshold') and detector.suspicion_save_threshold != new_suspicion_save_threshold:
            print(
                f"Updating suspicion save threshold from {detector.suspicion_save_threshold} to {new_suspicion_save_threshold}")
            detector.suspicion_save_threshold = new_suspicion_save_threshold

    # Update retention period if changed
    if 'retention_period' in config:
        new_retention_period = config['retention_period']
        if hasattr(detector, 'retention_period') and detector.retention_period != new_retention_period:
            print(
                f"Updating retention period from {detector.retention_period} to {new_retention_period}")
            detector.retention_period = new_retention_period

    # Update session recording if changed
    if 'session_recording' in config:
        new_session_recording = config['session_recording']
        if hasattr(detector, 'session_recording') and detector.session_recording != new_session_recording:
            print(
                f"Updating session recording from {detector.session_recording} to {new_session_recording}")
            detector.session_recording = new_session_recording

    # Update show bounding boxes if changed
    if 'show_bbox' in config:
        new_show_bbox = config['show_bbox']
        if hasattr(detector, 'show_bbox') and detector.show_bbox != new_show_bbox:
            print(
                f"Updating show bounding boxes from {detector.show_bbox} to {new_show_bbox}")
            detector.show_bbox = new_show_bbox

    # Update show pose skeleton if changed
    if 'show_pose' in config:
        new_show_pose = config['show_pose']
        if hasattr(detector, 'show_pose') and detector.show_pose != new_show_pose:
            print(
                f"Updating show pose skeleton from {detector.show_pose} to {new_show_pose}")
            detector.show_pose = new_show_pose

    # Update show confidence scores if changed
    if 'show_confidence' in config:
        new_show_confidence = config['show_confidence']
        if hasattr(detector, 'show_confidence') and detector.show_confidence != new_show_confidence:
            print(
                f"Updating show confidence scores from {detector.show_confidence} to {new_show_confidence}")
            detector.show_confidence = new_show_confidence

    # ===== CRITICAL FIX: Merge with existing config instead of overwriting =====
    # Load existing config
    existing_config = {}
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                existing_config = json.load(f)
        except Exception as e:
            print(f"Error loading existing config: {e}")

    # Merge updates into existing config
    existing_config.update(config)

    # Save merged config
    with open(CONFIG_FILE, 'w') as f:
        json.dump(existing_config, f, indent=2)

    print(
        f"Configuration updated successfully. Changed keys: {list(config.keys())}")

    # Broadcast config update to all connected clients
    socketio.emit('config_updated', existing_config)

    return jsonify({'success': True})


@app.route('/api/user/update', methods=['POST'])
def update_user():
    """Update user profile information"""
    data = request.get_json()
    user_id = data.get('id')
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    role = data.get('role', '').strip()

    if not user_id or not username:
        return jsonify({'success': False, 'error': 'User ID and username are required'}), 400

    if not USERS_FILE.exists():
        return jsonify({'success': False, 'error': 'User database not found'}), 500

    with open(USERS_FILE, 'r') as f:
        users = json.load(f)

    # Check if current user is admin (from localStorage, passed in request)
    current_user_role = data.get('current_user_role', '')
    is_admin = current_user_role == 'administrator'

    user_found = False
    for user in users:
        if user.get('id') == user_id:
            # Update allowed fields
            user['username'] = username
            if password:  # Only update password if provided
                user['password'] = password
            # Only allow role update if current user is admin
            if is_admin and role:
                user['role'] = role
            user_found = True
            break

    if not user_found:
        return jsonify({'success': False, 'error': 'User not found'}), 404

    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

    return jsonify({'success': True, 'message': 'Profile updated successfully'})


# --- STUDENT REGISTRATION API ---

@app.route('/api/students/list', methods=['GET'])
def get_students():
    """Get list of all registered students with face data."""
    students = detector.face_recognizer.get_all_students()
    return jsonify({'success': True, 'students': students})


@app.route('/api/students/register', methods=['POST'])
def register_student():
    """Register a new student with face photo."""
    data = request.get_json()
    student_id = data.get('student_id')
    student_name = data.get('student_name')
    image_data = data.get('image')  # base64 string

    if not all([student_id, student_name, image_data]):
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400

    success = detector.face_recognizer.register_student(
        student_id, student_name, image_data
    )

    if success:
        return jsonify({'success': True, 'message': f'Student {student_name} registered successfully'})
    else:
        return jsonify({'success': False, 'error': 'Face registration failed. Ensure face is clearly visible.'}), 500


@app.route('/api/students/delete', methods=['POST'])
def delete_student():
    """Delete a student from the face database."""
    data = request.get_json()
    student_id = data.get('student_id')

    if not student_id:
        return jsonify({'success': False, 'error': 'Student ID required'}), 400

    success = detector.face_recognizer.delete_student(student_id)
    if success:
        return jsonify({'success': True, 'message': 'Student record deleted'})
    else:
        return jsonify({'success': False, 'error': 'Failed to delete student record'}), 404


@app.route('/api/user/delete', methods=['POST'])
def delete_user():
    """Delete a user account"""
    data = request.get_json()
    user_id = data.get('id')

    if not user_id:
        return jsonify({'success': False, 'error': 'User ID is required'}), 400

    if not USERS_FILE.exists():
        return jsonify({'success': False, 'error': 'User database not found'}), 500

    with open(USERS_FILE, 'r') as f:
        users = json.load(f)

    # Check if current user is admin (from localStorage, passed in request)
    current_user_role = data.get('current_user_role', '')
    if current_user_role != 'administrator':
        return jsonify({'success': False, 'error': 'Only administrators can delete users'}), 403

    user_found = False
    for i, user in enumerate(users):
        if user.get('id') == user_id:
            # Prevent admin from deleting themselves
            if user.get('role') == 'administrator' and len([u for u in users if u.get('role') == 'administrator']) <= 1:
                return jsonify({'success': False, 'error': 'Cannot delete the last administrator account'}), 400
            users.pop(i)
            user_found = True
            break

    if not user_found:
        return jsonify({'success': False, 'error': 'User not found'}), 404

    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

    return jsonify({'success': True, 'message': 'User deleted successfully'})


@app.route('/api/user/create', methods=['POST'])
def create_user():
    """Create a new user account (admin only)"""
    data = request.get_json()

    # Check if current user is admin
    current_user_role = data.get('current_user_role', '')
    if current_user_role != 'administrator':
        return jsonify({'success': False, 'error': 'Only administrators can create users'}), 403

    # Get form data
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    role = data.get('role', 'proctor').strip()

    # Validate required fields
    if not username:
        return jsonify({'success': False, 'error': 'Username is required'}), 400
    if not email:
        return jsonify({'success': False, 'error': 'Email is required'}), 400
    if not password:
        return jsonify({'success': False, 'error': 'Password is required'}), 400
    if role not in ['proctor', 'administrator']:
        return jsonify({'success': False, 'error': 'Invalid role'}), 400

    # Load existing users
    users = []
    if USERS_FILE.exists():
        with open(USERS_FILE, 'r') as f:
            users = json.load(f)

    # Check for duplicate username or email
    for user in users:
        if user.get('username', '').lower() == username.lower():
            return jsonify({'success': False, 'error': 'Username already exists'}), 400
        if user.get('email', '').lower() == email.lower():
            return jsonify({'success': False, 'error': 'Email already exists'}), 400

    # Generate new user ID
    max_id = 0
    for user in users:
        try:
            user_id = int(user.get('id', 0))
            if user_id > max_id:
                max_id = user_id
        except ValueError:
            pass
    new_id = str(max_id + 1)

    # Create new user
    new_user = {
        'id': new_id,
        'username': username,
        'email': email,
        'password': password,
        'role': role
    }

    users.append(new_user)

    # Save to file
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

    print(f"New user created: {username} ({role})")
    return jsonify({'success': True, 'message': f'User {username} created successfully', 'user': {'id': new_id, 'username': username, 'email': email, 'role': role}})


@app.route('/api/history/update_card', methods=['POST'])
def update_history_card():
    """Update a history card status and notes"""
    data = request.get_json()
    card_id = data.get('card_id')
    new_status = data.get('status')
    new_notes = data.get('notes')

    if not card_id:
        return jsonify({'success': False, 'error': 'Card ID is required'}), 400

    card_folder = HISTORY_DIR / card_id
    card_file = card_folder / "card.json"

    if not card_file.exists():
        return jsonify({'success': False, 'error': f'Card {card_id} not found'}), 404

    try:
        with open(card_file, 'r') as f:
            card = json.load(f)

        if new_status:
            card['status'] = new_status
            # Also update all events in the card for consistency
            for event in card.get('events', []):
                event['status'] = new_status

        if new_notes is not None:
            card['notes'] = new_notes

        card['updated_at'] = datetime.now().isoformat()

        with open(card_file, 'w') as f:
            json.dump(card, f, indent=2)

        return jsonify({'success': True, 'message': 'Card updated successfully'})
    except Exception as e:
        print(f"Error updating card {card_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# INITIALIZATION
# ============================================

def init_data_files():
    """Initialize default data files if they don't exist"""
    if not USERS_FILE.exists():
        default_users = [
            {
                "id": "1",
                "username": "admin",
                "password": "admin123",
                "email": "admin@proctor.com",
                "role": "administrator"
            }
        ]
        with open(USERS_FILE, 'w') as f:
            json.dump(default_users, f, indent=2)

    if not CONFIG_FILE.exists():
        # Import config values from config.py for consolidation
        from config import (
            YOLO_MODEL, CONFIDENCE_THRESHOLD, IMG_SIZE_GPU, IMG_SIZE_CPU, IMG_SIZE_NANO,
            ENABLE_FRAME_SKIPPING, FRAME_SKIP_THRESHOLD_MS, MAX_FRAME_SKIP
        )
        from src.detection.suspicion_config import (
            SUSPICION_THRESHOLD, HEAD_WEIGHT, HANDS_FACE_WEIGHT, HANDS_OBJECT_WEIGHT,
            SMOOTHING_FACTOR, HISTORY_LENGTH
        )

        default_config = {
            # Detection thresholds
            "suspicion_threshold": SUSPICION_THRESHOLD,
            "confidence_threshold": CONFIDENCE_THRESHOLD,
            "yaw_threshold": 30,
            "pitch_threshold": 20,
            "roll_threshold": 45,
            "hand_face_threshold": 2.0,
            "hand_object_threshold": 55,
            "render_fps": 30,

            # Device setting
            "device": "gpu" if torch.cuda.is_available() else "cpu",

            # Model settings
            "model_size": "medium",
            "yolo_model": YOLO_MODEL,
            "img_size_gpu": IMG_SIZE_GPU,
            "img_size_cpu": IMG_SIZE_CPU,
            "img_size_nano": IMG_SIZE_NANO,
            "img_processing_size": IMG_SIZE_GPU if torch.cuda.is_available() else IMG_SIZE_CPU,

            # Performance
            "enable_frame_skipping": ENABLE_FRAME_SKIPPING,
            "frame_skip_threshold_ms": FRAME_SKIP_THRESHOLD_MS,
            "max_frame_skip": MAX_FRAME_SKIP,
            "render_fps": 30,
            "process_fps": 10,
            "processing_interval_ms": 50,

            # Camera
            "camera_source": "Webcam",
            "camera_resolution": "720p",
            "camera_fps": 30,
            "camera_label": "Main Camera",
            "auto_reconnect": True,
            "auto_save": True,
            "suspicion_save_threshold": 70,
            "retention_period": 7,
            "show_bbox": False,
            "show_pose": False,
            "show_confidence": False,
            "show_track_ids": False,

            # Suspicion scoring weights
            "head_weight": HEAD_WEIGHT,
            "hands_face_weight": HANDS_FACE_WEIGHT,
            "hands_object_weight": HANDS_OBJECT_WEIGHT,
            "smoothing_factor": SMOOTHING_FACTOR,
            "history_length": HISTORY_LENGTH
        }
        with open(CONFIG_FILE, 'w') as f:
            json.dump(default_config, f, indent=2)


init_data_files()

# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    print("")
    print("=" * 50)
    print("Starting Exam Cheat Detection v2")
    print("Open browser: http://localhost:5000")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    print("")

    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
