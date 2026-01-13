"""
Secure logging with audit trail
"""
import logging
import json
from datetime import datetime
from pathlib import Path
from functools import wraps
from flask import request


class AuditLogger:
    """Audit logger for security-sensitive operations"""
    
    def __init__(self, log_dir='logs'):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Setup audit log
        self.audit_file = self.log_dir / 'audit.log'
        self.logger = logging.getLogger('audit')
        self.logger.setLevel(logging.INFO)
        
        handler = logging.FileHandler(self.audit_file)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s'
        ))
        self.logger.addHandler(handler)
    
    def log_event(self, event_type: str, user_id: str = None, details: dict = None):
        """Log security event"""
        event = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'user_id': user_id,
            'ip_address': request.remote_addr if request else None,
            'user_agent': request.headers.get('User-Agent') if request else None,
            'details': details or {}
        }
        self.logger.info(json.dumps(event))
    
    def log_login_success(self, user_id: str, username: str):
        """Log successful login"""
        self.log_event('LOGIN_SUCCESS', user_id, {'username': username})
    
    def log_login_failure(self, username: str, reason: str):
        """Log failed login attempt"""
        self.log_event('LOGIN_FAILURE', None, {'username': username, 'reason': reason})
    
    def log_logout(self, user_id: str, username: str):
        """Log logout"""
        self.log_event('LOGOUT', user_id, {'username': username})
    
    def log_password_change(self, user_id: str):
        """Log password change"""
        self.log_event('PASSWORD_CHANGE', user_id)
    
    def log_user_created(self, admin_id: str, new_user_id: str, username: str):
        """Log user creation"""
        self.log_event('USER_CREATED', admin_id, {
            'new_user_id': new_user_id,
            'username': username
        })
    
    def log_user_deleted(self, admin_id: str, deleted_user_id: str):
        """Log user deletion"""
        self.log_event('USER_DELETED', admin_id, {'deleted_user_id': deleted_user_id})
    
    def log_config_change(self, user_id: str, changes: dict):
        """Log configuration changes"""
        self.log_event('CONFIG_CHANGE', user_id, {'changes': list(changes.keys())})
    
    def log_session_start(self, user_id: str, session_id: str):
        """Log exam session start"""
        self.log_event('SESSION_START', user_id, {'session_id': session_id})
    
    def log_session_end(self, user_id: str, session_id: str):
        """Log exam session end"""
        self.log_event('SESSION_END', user_id, {'session_id': session_id})
    
    def log_alert_confirmed(self, user_id: str, alert_id: str, student_id: str):
        """Log alert confirmation"""
        self.log_event('ALERT_CONFIRMED', user_id, {
            'alert_id': alert_id,
            'student_id': student_id
        })
    
    def log_evidence_deleted(self, user_id: str, card_id: str):
        """Log evidence deletion"""
        self.log_event('EVIDENCE_DELETED', user_id, {'card_id': card_id})


# Global audit logger instance
audit_logger = AuditLogger()


def audit_log(event_type: str):
    """Decorator to automatically log function calls"""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            user_id = getattr(request, 'user', {}).get('user_id')
            result = f(*args, **kwargs)
            audit_logger.log_event(event_type, user_id)
            return result
        return wrapped
    return decorator
