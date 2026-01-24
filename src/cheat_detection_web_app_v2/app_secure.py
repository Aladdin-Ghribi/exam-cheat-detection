# src/cheat_detection_web_app_v2/app_secure.py
"""
Exam Cheat Detection Web Application v2 - SECURE VERSION
Flask-SocketIO backend with comprehensive security features
"""

import os
import sys
import secrets
import logging
import re
from pathlib import Path
from datetime import datetime, timedelta
from functools import wraps

# Path setup - MUST BE FIRST
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / '.env')

# Security imports
import bcrypt
import jwt
from flask import Flask, request, jsonify, send_file, send_from_directory, session
from flask_socketio import SocketIO, emit, disconnect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import safe_join
import numpy as np
import cv2
import json
import base64

# Project imports
from src.detection.suspicion_config import SUSPICION_THRESHOLD
from src.detection.suspicion_scorer import SuspicionScorer
from src.detection.yolo_detector import YOLODetector

# ============================================
# SECURITY CONFIGURATION
# ============================================

SECRET_KEY = os.getenv('SECRET_KEY', secrets.token_hex(32))
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', secrets.token_hex(32))
DEBUG_MODE = os.getenv('DEBUG_MODE', 'False').lower() == 'true'
ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', 'http://localhost:5000').split(',')
MAX_EVIDENCE_SIZE_MB = int(os.getenv('MAX_EVIDENCE_SIZE_MB', '5'))
SESSION_TIMEOUT_MINUTES = int(os.getenv('SESSION_TIMEOUT_MINUTES', '120'))

# ============================================
# LOGGING CONFIGURATION
# ============================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(PROJECT_ROOT / 'logs' / 'app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================
# APP CONFIGURATION
# ============================================

app = Flask(__name__,
            template_folder=str(Path(__file__).parent),
            static_folder=str(Path(__file__).parent / 'static'))

app.config['SECRET_KEY'] = SECRET_KEY
app.config['SESSION_COOKIE_SECURE'] = not DEBUG_MODE
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=SESSION_TIMEOUT_MINUTES)
app.config['MAX_CONTENT_LENGTH'] = MAX_EVIDENCE_SIZE_MB * 1024 * 1024

socketio = SocketIO(app, cors_allowed_origins=ALLOWED_ORIGINS, async_mode='threading')

# Rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Paths
DATA_DIR = PROJECT_ROOT / 'data'
OUTPUT_DIR = PROJECT_ROOT / 'output'
HISTORY_DIR = OUTPUT_DIR / 'history' / 'cards'
USERS_FILE = DATA_DIR / 'users.json'
CONFIG_FILE = DATA_DIR / 'config.json'
LOGS_DIR = PROJECT_ROOT / 'logs'

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ============================================
# SECURITY HEADERS
# ============================================

@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https:;"
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# ============================================
# INPUT VALIDATION
# ============================================

def sanitize_string(text, max_length=255):
    """Sanitize user input"""
    if not text:
        return ""
    text = str(text).strip()[:max_length]
    # Remove potentially dangerous characters
    text = re.sub(r'[<>\"\'&]', '', text)
    return text

def validate_student_id(student_id):
    """Validate student ID format"""
    if not student_id:
        return False
    return bool(re.match(r'^[A-Za-z0-9_-]{1,50}$', student_id))

def validate_session_name(name):
    """Validate session name"""
    if not name or len(name) > 100:
        return False
    return bool(re.match(r'^[A-Za-z0-9\s_-]+$', name))

# ============================================
# AUTHENTICATION & AUTHORIZATION
# ============================================

active_sessions = {}  # user_id -> {token, expires_at, user_data}

def generate_token(user_data):
    """Generate JWT token"""
    payload = {
        'user_id': user_data['id'],
        'username': user_data['username'],
        'role': user_data['role'],
        'exp': datetime.utcnow() + timedelta(minutes=SESSION_TIMEOUT_MINUTES),
        'iat': datetime.utcnow()
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm='HS256')
    return token

def verify_token(token):
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        return None
    except jwt.InvalidTokenError:
        logger.warning("Invalid token")
        return None

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Unauthorized'}), 401
        
        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        request.user = payload
        return f(*args, **kwargs)
    return decorated_function

# ============================================
# PASSWORD HASHING
# ============================================

def hash_password(password):
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, hashed):
    """Verify password against hash"""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except:
        return False

# ============================================
# AUDIT LOGGING
# ============================================

def audit_log(event_type, user_id=None, details=None):
    """Log security-relevant events"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'event_type': event_type,
        'user_id': user_id,
        'ip_address': request.remote_addr if request else None,
        'details': details
    }
    logger.info(f"AUDIT: {json.dumps(log_entry)}")

# ============================================
# DETECTION PIPELINE INITIALIZATION
# ============================================

logger.info("=" * 50)
logger.info("Initializing Exam Cheat Detection v2 - SECURE")
logger.info("=" * 50)

logger.info("Loading YOLODetector...")
detector = YOLODetector()
detector.auto_save_enabled = False
logger.info("YOLODetector ready")

logger.info("Loading SuspicionScorer...")
suspicion_scorer = SuspicionScorer()
logger.info("SuspicionScorer ready")

logger.info("=" * 50)

# ============================================
# SESSION MANAGEMENT
# ============================================

active_exam_session = None
pending_alerts = {}

def create_exam_session(session_name, camera_id="cam_01"):
    """Create a new monitoring session"""
    session_id = "sess_" + datetime.now().strftime('%Y%m%d_%H%M%S')
    return {
        "session_id": session_id,
        "session_name": sanitize_string(session_name, 100),
        "camera_id": sanitize_string(camera_id, 50),
        "started_at": datetime.now().isoformat(),
        "ended_at": None,
        "status": "active"
    }

# ============================================
# HTTP ROUTES
# ============================================

@app.route('/')
def index():
    """Serve login page"""
    return send_from_directory(Path(__file__).parent, 'login.html')

@app.route('/dashboard')
def dashboard():
    """Serve dashboard - requires authentication check on frontend"""
    return send_from_directory(Path(__file__).parent, 'dashboard.html')

@app.route('/logout')
def logout():
    """Logout and clear session"""
    session.clear()
    return send_from_directory(Path(__file__).parent, 'login.html')

@app.route('/api/login', methods=['POST'])
@limiter.limit(os.getenv('LOGIN_RATE_LIMIT', '5 per minute'))
def api_login():
    """Authenticate user with bcrypt password verification"""
    try:
        data = request.get_json()
        username = sanitize_string(data.get('username', ''), 50)
        password = data.get('password', '')
        
        if not username or not password:
            audit_log('login_failed', details='Missing credentials')
            return jsonify({'success': False, 'error': 'Username and password required'}), 400
        
        if not USERS_FILE.exists():
            audit_log('login_failed', details='User database not found')
            return jsonify({'success': False, 'error': 'Authentication system unavailable'}), 500
        
        with open(USERS_FILE, 'r') as f:
            users = json.load(f)
        
        for user in users:
            if user.get('username') == username:
                # Check if password is hashed (starts with $2b$)
                stored_password = user.get('password', '')
                if stored_password.startswith('$2b$'):
                    password_valid = verify_password(password, stored_password)
                else:
                    # Fallback for plain text (should be migrated)
                    password_valid = (password == stored_password)
                    logger.warning(f"Plain text password detected for user: {username}")
                
                if password_valid:
                    user_data = {
                        'id': user.get('id'),
                        'username': user.get('username'),
                        'email': user.get('email'),
                        'role': user.get('role')
                    }
                    token = generate_token(user_data)
                    
                    audit_log('login_success', user_id=user.get('id'), details=f"User {username} logged in")
                    
                    return jsonify({
                        'success': True,
                        'token': token,
                        'user': user_data
                    })
                else:
                    audit_log('login_failed', details=f"Invalid password for user: {username}")
                    return jsonify({'success': False, 'error': 'Invalid username or password'}), 401
        
        audit_log('login_failed', details=f"User not found: {username}")
        return jsonify({'success': False, 'error': 'Invalid username or password'}), 401
    
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'success': False, 'error': 'Authentication error'}), 500

@app.route('/api/verify-token', methods=['POST'])
def verify_token_route():
    """Verify if token is still valid"""
    try:
        data = request.get_json()
        token = data.get('token', '')
        
        if not token:
            return jsonify({'valid': False}), 401
        
        payload = verify_token(token)
        if payload:
            return jsonify({'valid': True, 'user': {
                'id': payload['user_id'],
                'username': payload['username'],
                'role': payload['role']
            }})
        else:
            return jsonify({'valid': False}), 401
    except:
        return jsonify({'valid': False}), 401

@app.route('/api/users', methods=['GET'])
@require_auth
def get_users():
    """Get users list (admin only)"""
    if request.user.get('role') != 'admin':
        return jsonify({'error': 'Forbidden'}), 403
    
    if USERS_FILE.exists():
        with open(USERS_FILE, 'r') as f:
            users = json.load(f)
        return jsonify({'users': [{k: v for k, v in u.items() if k != 'password'} for u in users]})
    return jsonify({'users': []})

@app.route('/api/dashboard-stats', methods=['GET'])
@require_auth
def get_dashboard_stats():
    """Get dashboard statistics for cheating detection events"""
    try:
        stats = {
            'phone_detected': 0,
            'looking_away': 0,
            'suspicious_objects': 0,
            'hand_face': 0,
            'total_alerts': 0
        }
        
        # Count events from history directory
        if HISTORY_DIR.exists():
            for json_file in HISTORY_DIR.glob('*.json'):
                try:
                    with open(json_file, 'r') as f:
                        event = json.load(f)
                        event_type = event.get('event_type', '')
                        
                        if event_type == 'phone':
                            stats['phone_detected'] += 1
                        elif event_type == 'looking_away':
                            stats['looking_away'] += 1
                        elif event_type == 'suspicious_object':
                            stats['suspicious_objects'] += 1
                        elif event_type == 'hand_face':
                            stats['hand_face'] += 1
                        
                        stats['total_alerts'] += 1
                except:
                    continue
        
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        logger.error(f"Dashboard stats error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to fetch statistics'}), 500


@app.route('/api/weekly-trends', methods=['GET'])
@require_auth
def get_weekly_trends():
    """Get cheating detection trends for the last 7 days"""
    try:
        from datetime import datetime, timedelta
        
        # Initialize data structure for last 7 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=6)  # Last 7 days including today
        
        # Create date labels (e.g., "Mon 13", "Tue 14", etc.)
        date_labels = []
        current = start_date
        for i in range(7):
            date_labels.append(current.strftime('%a %d'))
            current += timedelta(days=1)
        
        # Initialize counts for each day and type
        daily_data = {
            'phone': [0] * 7,
            'looking_away': [0] * 7,
            'suspicious_object': [0] * 7
        }
        
        # Count events from history directory
        if HISTORY_DIR.exists():
            for json_file in HISTORY_DIR.glob('*.json'):
                try:
                    with open(json_file, 'r') as f:
                        event = json.load(f)
                    
                    # Parse event timestamp
                    timestamp_str = event.get('timestamp', '')
                    if timestamp_str:
                        # Handle ISO format timestamps
                        event_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        
                        # Check if event is within last 7 days
                        if start_date.date() <= event_time.date() <= end_date.date():
                            # Calculate day index (0-6)
                            day_diff = (event_time.date() - start_date.date()).days
                            if 0 <= day_diff < 7:
                                event_type = event.get('event_type', '')
                                
                                if event_type == 'phone':
                                    daily_data['phone'][day_diff] += 1
                                elif event_type == 'looking_away':
                                    daily_data['looking_away'][day_diff] += 1
                                elif event_type == 'suspicious_object':
                                    daily_data['suspicious_object'][day_diff] += 1
                except Exception as e:
                    logger.debug(f"Error processing event file {json_file}: {str(e)}")
                    continue
        
        return jsonify({
            'success': True,
            'data': {
                'labels': date_labels,
                'datasets': [
                    {
                        'label': 'Phone Detected',
                        'data': daily_data['phone'],
                        'backgroundColor': 'rgba(244, 67, 54, 0.7)',
                        'borderColor': '#F44336',
                        'borderWidth': 2
                    },
                    {
                        'label': 'Looking Away',
                        'data': daily_data['looking_away'],
                        'backgroundColor': 'rgba(255, 187, 51, 0.7)',
                        'borderColor': '#FFBB33',
                        'borderWidth': 2
                    },
                    {
                        'label': 'Suspicious Objects',
                        'data': daily_data['suspicious_object'],
                        'backgroundColor': 'rgba(0, 229, 255, 0.7)',
                        'borderColor': '#00E5FF',
                        'borderWidth': 2
                    }
                ]
            }
        })
    except Exception as e:
        logger.error(f"Weekly trends error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to fetch weekly trends'}), 500


# ============================================
# INITIALIZATION
# ============================================

def init_data_files():
    """Initialize default data files"""
    if not USERS_FILE.exists():
        default_users = [
            {
                "id": "1",
                "username": "admin",
                "password": hash_password("admin123"),
                "email": "admin@proctor.com",
                "role": "admin"
            },
            {
                "id": "2",
                "username": "user",
                "password": hash_password("user123"),
                "email": "user_proctor@email.com",
                "role": "proctor"
            }
        ]
        with open(USERS_FILE, 'w') as f:
            json.dump(default_users, f, indent=2)
        logger.info("Created default users with hashed passwords")

init_data_files()

# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    logger.info("")
    logger.info("=" * 50)
    logger.info("Starting Exam Cheat Detection v2 - SECURE MODE")
    logger.info(f"Debug Mode: {DEBUG_MODE}")
    logger.info(f"Allowed Origins: {ALLOWED_ORIGINS}")
    logger.info("Open browser: http://localhost:5000")
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 50)
    logger.info("")
    
    socketio.run(app, debug=DEBUG_MODE, host='127.0.0.1' if not DEBUG_MODE else '0.0.0.0', port=5000)
