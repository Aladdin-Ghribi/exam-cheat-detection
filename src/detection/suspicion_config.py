"""
Centralized configuration for suspicion scoring parameters.
Defaults can be overridden by config.json.
"""
import json
from pathlib import Path


def load_config():
    """
    Load configuration from config.json if it exists.
    Returns a dictionary with config values, or empty dict if file doesn't exist.
    """
    config_path = Path(__file__).parent.parent.parent / 'data' / 'config.json'
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


# Main suspicion threshold (0-100 scale)
SUSPICION_THRESHOLD = 20  # Can be overridden by config.json


# Scoring weights
HEAD_WEIGHT = 0.75  # Weight for head orientation component
HANDS_FACE_WEIGHT = 0.05  # Weight for hand-face proximity
HANDS_OBJECT_WEIGHT = 0.07  # Weight for hand-object proximity

# Smoothing parameters
SMOOTHING_FACTOR = 0.75  # General smoothing factor
HISTORY_LENGTH = 20  # Number of frames to track for smoothing

# Risk objects classification
HIGH_RISK_OBJECTS = frozenset({
    'cell phone',
    'cellphone',
    'mobile phone',
    'mobile',
    'phone',
    'smartphone',
    'smart phone',
    'iphone',
    'android phone',
    'book',
    'textbook',
    'notebook',
    'study guide'
})

MEDIUM_RISK_OBJECTS = frozenset({
    'laptop',
    'handbag',
    'backpack'
})


# Performance settings (FPS)
RENDER_FPS = 30  # Client-side render loop FPS
PROCESS_FPS = 10  # Server-side processing FPS (model inference)
