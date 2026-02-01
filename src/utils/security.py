"""
Rate limiting and CSRF protection
"""
import time
import secrets
from collections import defaultdict
from functools import wraps
from flask import request, jsonify, session


# Rate limiting storage (in-memory, use Redis in production)
_rate_limit_storage = defaultdict(list)
_failed_login_attempts = defaultdict(list)


def rate_limit(max_requests: int, window_seconds: int):
    """
    Rate limiting decorator

    Args:
        max_requests: Maximum requests allowed
        window_seconds: Time window in seconds
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            # Get client identifier (IP address)
            client_id = request.remote_addr
            current_time = time.time()

            # Clean old requests outside the window
            _rate_limit_storage[client_id] = [
                req_time for req_time in _rate_limit_storage[client_id]
                if current_time - req_time < window_seconds
            ]

            # Check if limit exceeded
            if len(_rate_limit_storage[client_id]) >= max_requests:
                return jsonify({
                    'error': 'Rate limit exceeded. Please try again later.',
                    'retry_after': window_seconds
                }), 429

            # Add current request
            _rate_limit_storage[client_id].append(current_time)

            return f(*args, **kwargs)

        return wrapped
    return decorator


def check_failed_login_attempts(username: str, max_attempts: int = 5, lockout_minutes: int = 15) -> bool:
    """
    Check if account should be locked due to failed login attempts

    Returns:
        True if account is locked, False otherwise
    """
    current_time = time.time()
    lockout_seconds = lockout_minutes * 60

    # Remove old attempts
    _failed_login_attempts[username] = [
        attempt_time for attempt_time in _failed_login_attempts[username]
        if current_time - attempt_time < lockout_seconds
    ]

    # Check if locked
    return len(_failed_login_attempts[username]) >= max_attempts


def record_failed_login(username: str):
    """Record a failed login attempt"""
    _failed_login_attempts[username].append(time.time())


def clear_failed_login_attempts(username: str):
    """Clear failed login attempts after successful login"""
    _failed_login_attempts[username] = []


def generate_csrf_token() -> str:
    """Generate CSRF token for session"""
    token = secrets.token_hex(32)
    session['csrf_token'] = token
    return token


def validate_csrf_token(token: str) -> bool:
    """Validate CSRF token"""
    return token and session.get('csrf_token') == token


def csrf_protect(f):
    """Decorator to protect routes with CSRF token validation"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method in ['POST', 'PUT', 'DELETE']:
            token = request.headers.get(
                'X-CSRF-Token') or request.form.get('csrf_token')

            if not validate_csrf_token(token):
                return jsonify({'error': 'Invalid CSRF token'}), 403

        return f(*args, **kwargs)

    return decorated
