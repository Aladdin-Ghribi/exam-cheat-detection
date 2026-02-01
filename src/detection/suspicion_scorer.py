from collections import deque
from .suspicion_config import (
    SUSPICION_THRESHOLD,
    SMOOTHING_FACTOR,
    HISTORY_LENGTH,
    HIGH_RISK_OBJECTS,
    MEDIUM_RISK_OBJECTS,
    load_config
)


class SuspicionScorer:
    def __init__(self, config=None):
        """
        Initialize the SuspicionScorer with configuration from config.json.

        Args:
            config: Optional dictionary with configuration values. 
                    If not provided, loads from config.json automatically.
        """
        # Load config from file if not provided
        if config is None:
            config = load_config()

        # Store config for reference
        self._config = config

        # Smoothing parameters from config or defaults
        self.history_length = config.get('history_length', HISTORY_LENGTH)
        self.smoothing_factor = config.get(
            'smoothing_factor', SMOOTHING_FACTOR)
        self.history = {}

        # Risk object lists
        self.high_risk_objects = HIGH_RISK_OBJECTS
        self.medium_risk_objects = MEDIUM_RISK_OBJECTS

        # Dynamic thresholds from config.json
        self.yaw_threshold = config.get('yaw_threshold', 30)
        self.pitch_threshold = config.get('pitch_threshold', 20)
        self.suspicion_threshold = config.get(
            'suspicion_threshold', SUSPICION_THRESHOLD)
        self.hand_face_threshold = config.get('hand_face_threshold', 2.0)
        self.hand_object_threshold = config.get('hand_object_threshold', 55)

    def score_detection(self, detection):
        """
        Score a detection for suspicious behavior.
        Args:
            detection: Detection dictionary with behavior information
        Returns:
            Dictionary with suspicion scores
        """
        behavior = detection.get('behavior') or {}
        key = self._make_key(detection)
        components = self._compute_components(detection, behavior, key)

        # Simple scoring matching app.py logic
        score = 0

        # Head orientation (0-50 points)
        if 'head_orientation' in behavior:
            ho = behavior['head_orientation']
            if ho is not None:
                if abs(ho.get('yaw', 0)) > self.yaw_threshold:
                    score += min(30, abs(ho['yaw']) - self.yaw_threshold)
                if abs(ho.get('pitch', 0)) > self.pitch_threshold:
                    score += min(20, abs(ho['pitch']) - self.pitch_threshold)

        # Hand proximity (0-100 points per hand for high-risk objects)
        if 'hands' in behavior:
            for side in ['left', 'right']:
                hand = behavior['hands'].get(side, {})
                if hand.get('visible'):
                    if hand.get('near_object') and hand.get('object_class'):
                        obj_class = hand.get('object_class', '').lower()
                        if 'phone' in obj_class or 'book' in obj_class:
                            score = 100  # Instant flag for phone/book
                            break
                        else:
                            score += 40
                    elif hand.get('near_face'):
                        score += 15

        # Convert to 0-1 scale
        raw = min(1.0, score / 100.0)
        smoothed = self._smooth(key, raw)

        # Create result
        result = {
            'raw': raw,
            'smoothed': smoothed,
            'components': components,
            'key': key
        }

        # Store in history
        if key is not None:
            if key not in self.history:
                self.history[key] = deque(maxlen=self.history_length)
            if not self.history[key]:
                self.history[key].append(smoothed)
            elif self.history[key][-1] != smoothed:
                self.history[key].append(smoothed)

        return result

    def prune(self, active_keys):
        """
        Remove inactive keys from history.
        Args:
            active_keys: Set of currently active keys
        """
        for key in list(self.history.keys()):
            if key not in active_keys:
                self.history.pop(key, None)

    def _smooth(self, key, raw):
        """
        Apply smoothing to the raw score.
        Args:
            key: Tracking key
            raw: Raw score to smooth
        Returns:
            Smoothed score
        """
        if key is None:
            return raw

        window = self.history.get(key)
        if not window:
            return raw

        previous = window[-1]

        # Special handling for very high suspicion values
        if raw >= 0.85:
            # Minimal smoothing for very high suspicion
            return max(previous, raw * 0.95 + previous * 0.05)

        # Balanced smoothing approach
        if raw > previous:  # Increasing suspicion
            # Moderate smoothing for increases
            smoothed = previous * 0.7 + raw * 0.3
        else:  # Decreasing suspicion
            # More smoothing for decreases
            smoothed = previous * self.smoothing_factor + \
                raw * (1.0 - self.smoothing_factor)

        return max(0.0, min(1.0, smoothed))

    def _make_key(self, detection):
        """
        Create a tracking key for the detection.
        Args:
            detection: Detection dictionary
        Returns:
            Tracking key or None
        """
        track_id = detection.get('track_id')
        if track_id is not None:
            return ('track', track_id)
        bbox = detection.get('bbox')
        if bbox and len(bbox) == 4:
            cx = (bbox[0] + bbox[2]) * 0.5
            cy = (bbox[1] + bbox[3]) * 0.5
            return ('bbox', round(cx, 1), round(cy, 1))
        return None

    def _compute_components(self, detection, behavior, key):
        """
        Compute the individual suspicion components.
        Args:
            detection: Detection dictionary
            behavior: Behavior dictionary
            key: Tracking key
        Returns:
            Dictionary with component scores
        """
        head = self._head_component(key, behavior.get('head_orientation'))
        hands = behavior.get('hands') or {}
        face = self._hand_face_component(hands)
        obj = self._hand_object_component(detection.get('bbox'), hands)

        return {
            'head': head,
            'hands_face': face,
            'hands_object': obj
        }

    def _head_component(self, key, orientation):
        """
        Compute the head orientation suspicion component using simple thresholds.

        NOTE: Due to coordinate system mismatch between OpenCV and real-world movements,
        'pitch' actually measures LEFT/RIGHT head turning, and 'yaw' measures body roll.
        This is a known "fix" and works correctly.

        Args:
            key: Tracking key
            orientation: Head orientation dictionary
        Returns:
            Suspicion score for head orientation (0.0 to 1.0)
        """
        if not orientation:
            return 0.0

        # These are "swapped" from math convention to match reality
        yaw = float(orientation.get('yaw', 0.0))      # Actually: body roll
        # Actually: head turn left/right
        pitch = float(orientation.get('pitch', 0.0))

        score = 0.0

        # Yaw (body roll) component - reaches 100% at 90° roll
        if abs(yaw) > self.yaw_threshold:
            yaw_excess = abs(yaw) - self.yaw_threshold
            # Scale to 0-1: 60° beyond threshold = 100%
            score += min(1.0, yaw_excess / 60.0) * 0.6  # Max 60% contribution

        # Pitch (head turn) component - reaches 100% at ~67° turn
        if abs(pitch) > self.pitch_threshold:
            pitch_excess = abs(pitch) - self.pitch_threshold
            # Scale to 0-1: 45° beyond threshold = 100%
            score += min(1.0, pitch_excess / 45.0) * \
                0.4  # Max 40% contribution

        return min(1.0, score)  # Cap at 100%

    def _hand_face_component(self, hands):
        """
        Compute the hand-face proximity suspicion component.
        Args:
            hands: Hands dictionary
        Returns:
            Suspicion score for hand-face proximity
        """
        if not hands:
            return 0.0

        total = 0
        score_sum = 0.0

        for side in ('left', 'right'):
            entry = hands.get(side)
            if not entry or not entry.get('visible'):
                continue

            total += 1

            if entry.get('near_face'):
                score_sum += 0.85  # High score for hands near face
                continue

            distance = entry.get('distance_to_face')
            if distance is None:
                continue

            threshold = entry.get('face_threshold')
            if threshold is None or threshold <= 0.0:
                # Convert hand_face_threshold from UI (1.0-3.0) to internal scale (0.1-0.3)
                threshold = self.hand_face_threshold / 10.0

            # Graduated scoring based on proximity
            if distance < threshold * 0.5:  # Very close to face
                score_sum += 0.75
            elif distance < threshold:  # Near face
                score_sum += 0.6
            elif distance < threshold * 1.5:  # Somewhat near face
                score_sum += 0.3
            elif distance < threshold * 2.0:  # Extended proximity
                score_sum += 0.15

        if total == 0:
            return 0.0
        return min(1.0, score_sum / total)

    def _hand_object_component(self, bbox, hands):
        """
        Compute hand-object proximity suspicion component.
        Args:
            bbox: Bounding box
            hands: Hands dictionary
        Returns:
            Suspicion score for hand-object proximity
        """
        if not hands:
            return 0.0
        if not bbox or len(bbox) != 4:
            return 0.0

        width = max(bbox[2] - bbox[0], 1.0)
        height = max(bbox[3] - bbox[1], 1.0)
        # Use the user-configured threshold or fall back to a calculated one
        threshold = self.hand_object_threshold
        if threshold <= 0.0:
            threshold = min(width, height) * 0.25
            if threshold <= 0.0:
                threshold = 25.0

        expanded = threshold * 1.6
        max_score = 0.0

        for side in ('left', 'right'):
            entry = hands.get(side)
            if not entry or not entry.get('visible'):
                continue

            distance = entry.get('distance_to_object')

            label = entry.get('object_class')
            if label:
                label_norm = label.replace('_', ' ').lower()
            else:
                label_norm = None

            if label_norm and label_norm in self.high_risk_objects:
                # Ensure high-risk objects get a very high score that converts to 100/100
                return 0.99  # Slightly less than 1.0 to avoid rounding issues

            if distance is None:
                continue

            if label_norm and label_norm in self.medium_risk_objects:
                if entry.get('near_object'):
                    max_score = max(max_score, 0.75)
                else:
                    max_score = max(max_score, 0.45)
            else:
                if entry.get('near_object'):
                    max_score = max(max_score, 0.6)

            if distance < threshold * 0.5:
                max_score = max(max_score, 0.8)
            elif distance < threshold:
                max_score = max(max_score, 0.6)
            elif distance < threshold * 1.5:
                max_score = max(max_score, 0.35)

        return min(1.0, max_score)
