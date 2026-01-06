"""
Input validation and sanitization utilities
"""
import re
from typing import Any, Optional


class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass


def validate_username(username: str) -> str:
    """Validate username format"""
    if not username or not isinstance(username, str):
        raise ValidationError("Username is required")
    
    username = username.strip()
    
    if len(username) < 3 or len(username) > 50:
        raise ValidationError("Username must be 3-50 characters")
    
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        raise ValidationError("Username can only contain letters, numbers, hyphens, and underscores")
    
    return username


def validate_password(password: str) -> str:
    """Validate password strength"""
    if not password or not isinstance(password, str):
        raise ValidationError("Password is required")
    
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters")
    
    if len(password) > 128:
        raise ValidationError("Password too long (max 128 characters)")
    
    # Check for at least one letter and one number
    if not re.search(r'[a-zA-Z]', password) or not re.search(r'\d', password):
        raise ValidationError("Password must contain letters and numbers")
    
    return password


def validate_email(email: str) -> str:
    """Validate email format"""
    if not email or not isinstance(email, str):
        raise ValidationError("Email is required")
    
    email = email.strip().lower()
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        raise ValidationError("Invalid email format")
    
    return email


def validate_student_id(student_id: str) -> str:
    """Validate student ID format"""
    if not student_id or not isinstance(student_id, str):
        raise ValidationError("Student ID is required")
    
    student_id = student_id.strip()
    
    if len(student_id) < 3 or len(student_id) > 20:
        raise ValidationError("Student ID must be 3-20 characters")
    
    if not re.match(r'^[a-zA-Z0-9_-]+$', student_id):
        raise ValidationError("Student ID can only contain letters, numbers, hyphens, and underscores")
    
    return student_id


def validate_session_name(name: str) -> str:
    """Validate session name"""
    if not name or not isinstance(name, str):
        raise ValidationError("Session name is required")
    
    name = name.strip()
    
    if len(name) < 3 or len(name) > 100:
        raise ValidationError("Session name must be 3-100 characters")
    
    # Allow more characters for session names
    if not re.match(r'^[a-zA-Z0-9 _-]+$', name):
        raise ValidationError("Session name contains invalid characters")
    
    return name


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal"""
    if not filename:
        return ""
    
    # Remove path separators and dangerous characters
    filename = re.sub(r'[/\\:*?"<>|]', '', filename)
    filename = filename.replace('..', '')
    
    return filename.strip()


def validate_numeric_range(value: Any, min_val: float, max_val: float, name: str) -> float:
    """Validate numeric value is within range"""
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{name} must be a number")
    
    if value < min_val or value > max_val:
        raise ValidationError(f"{name} must be between {min_val} and {max_val}")
    
    return value
