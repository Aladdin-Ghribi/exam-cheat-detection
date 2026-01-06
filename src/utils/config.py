"""
Environment configuration loader
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_path)


class Config:
    """Application configuration from environment variables"""
    
    # Flask
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', os.urandom(32).hex())
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    ENV = os.getenv('FLASK_ENV', 'production')
    
    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', os.urandom(32).hex())
    JWT_EXPIRATION_HOURS = int(os.getenv('JWT_EXPIRATION_HOURS', '24'))
    
    # Security
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'True').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = os.getenv('SESSION_COOKIE_HTTPONLY', 'True').lower() == 'true'
    SESSION_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
    MAX_LOGIN_ATTEMPTS = int(os.getenv('MAX_LOGIN_ATTEMPTS', '5'))
    LOCKOUT_MINUTES = int(os.getenv('LOCKOUT_MINUTES', '15'))
    
    # Rate Limiting
    RATE_LIMIT_ENABLED = os.getenv('RATE_LIMIT_ENABLED', 'True').lower() == 'true'
    
    # File Upload
    MAX_UPLOAD_SIZE_MB = int(os.getenv('MAX_UPLOAD_SIZE_MB', '10'))
    MAX_CONTENT_LENGTH = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    ALLOWED_EXTENSIONS = set(os.getenv('ALLOWED_EXTENSIONS', 'jpg,jpeg,png').split(','))
    
    # Retention
    DEFAULT_RETENTION_DAYS = int(os.getenv('DEFAULT_RETENTION_DAYS', '7'))
    MAX_RETENTION_DAYS = int(os.getenv('MAX_RETENTION_DAYS', '30'))
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/app.log')
    
    @staticmethod
    def validate():
        """Validate critical configuration"""
        if Config.SECRET_KEY == 'your-secret-key-here-change-this':
            raise ValueError("⚠️  SECURITY WARNING: Change FLASK_SECRET_KEY in .env!")
        
        if Config.JWT_SECRET_KEY == 'your-jwt-secret-here-change-this':
            raise ValueError("⚠️  SECURITY WARNING: Change JWT_SECRET_KEY in .env!")
        
        if Config.ENV == 'production' and Config.DEBUG:
            raise ValueError("⚠️  SECURITY WARNING: DEBUG must be False in production!")
