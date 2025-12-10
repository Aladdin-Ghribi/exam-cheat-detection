"""
Centralized configuration for suspicion scoring parameters.
This file ensures consistent thresholds and weights across all components.
"""

# Main suspicion threshold (0-100 scale)
SUSPICION_THRESHOLD = 15  # Lowered threshold for more sensitive detection


# Scoring weights
HEAD_WEIGHT = 0.75  # Weight for head orientation component
HANDS_FACE_WEIGHT = 0.15  # Weight for hand-face proximity
HANDS_OBJECT_WEIGHT = 0.10  # Weight for hand-object proximity

# Smoothing parameters
SMOOTHING_FACTOR = 0.5  # General smoothing factor
HISTORY_LENGTH = 10  # Number of frames to track for smoothing

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
RENDER_FPS = 30  # Client-side render loop FPS (smooth display)
PROCESS_FPS = 10  # Server-side processing FPS (AI inference)
