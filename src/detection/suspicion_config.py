"""
Centralized configuration for suspicion scoring parameters.
This file ensures consistent thresholds and weights across all components.
"""

# Main suspicion threshold (0-100 scale)
SUSPICION_THRESHOLD = 20  # Default threshold for flagging suspicious behavior

# Head orientation thresholds (degrees)
NORMAL_GAZE_THRESHOLD = 25.0  # Normal forward gaze tolerance
SUSPICIOUS_GAZE_THRESHOLD = 45.0  # When to start scoring higher
HIGH_SUSPICION_GAZE_THRESHOLD = 60.0  # High suspicion
VERY_SUSPICION_GAZE_THRESHOLD = 80.0  # Very high suspicion

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

# UI scoring parameters (0-100 scale)
HEAD_YAW_MAX_SCORE = 30  # Maximum score for head yaw
HEAD_PITCH_MAX_SCORE = 20  # Maximum score for head pitch
HAND_OBJECT_SCORE = 40  # Score for hand near object
HAND_FACE_SCORE = 15  # Score for hand near face
NEARBY_OBJECT_SCORE = 30  # Score for objects near person

# UI thresholds
UI_YAW_THRESHOLD = 30  # UI threshold for yaw
UI_PITCH_THRESHOLD = 20  # UI threshold for pitch
