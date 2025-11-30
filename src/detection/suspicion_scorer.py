from collections import deque
from .suspicion_config import (
    SUSPICION_THRESHOLD,
    HEAD_WEIGHT,
    HANDS_FACE_WEIGHT,
    HANDS_OBJECT_WEIGHT,
    SMOOTHING_FACTOR,
    HISTORY_LENGTH,
    HIGH_RISK_OBJECTS,
    MEDIUM_RISK_OBJECTS
)


class SuspicionScorer:
    def __init__(self):
        """
        Initialize the SuspicionScorer with centralized configuration.
        """
        self.history_length = HISTORY_LENGTH
        self.smoothing_factor = SMOOTHING_FACTOR
        self.history = {}
        self.orientation_baseline = {}
        self.baseline_ready_frames = 5

        # Risk objects from config
        self.high_risk_objects = HIGH_RISK_OBJECTS
        self.medium_risk_objects = MEDIUM_RISK_OBJECTS

        # Dynamic thresholds (can be updated from UI)
        self.yaw_threshold = 30
        self.pitch_threshold = 20
        self.suspicion_threshold = SUSPICION_THRESHOLD

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
        tracked = set(self.history.keys()) | set(
            self.orientation_baseline.keys())
        for key in tracked:
            if key not in active_keys:
                self.history.pop(key, None)
                self.orientation_baseline.pop(key, None)

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
        Args:
            key: Tracking key
            orientation: Head orientation dictionary
        Returns:
            Suspicion score for head orientation
        """
        if not orientation:
            return 0.0

        yaw = float(orientation.get('yaw', 0.0))
        pitch = float(orientation.get('pitch', 0.0))
        
        score = 0
        
        if abs(yaw) > self.yaw_threshold:
            score += min(30, abs(yaw) - self.yaw_threshold)
        if abs(pitch) > self.pitch_threshold:
            score += min(20, abs(pitch) - self.pitch_threshold)
        
        # Convert to 0-1 scale (max possible score is 50)
        return min(1.0, score / 100.0)

    def _scale_deviation(self, value, neutral, extreme):
        """
        Scale a deviation value to a suspicion score.
        Args:
            value: Deviation value
            neutral: Neutral threshold
            extreme: Extreme threshold
        Returns:
            Suspicion score
        """
        if value <= neutral:
            return 0.0
        return min(1.0, (value - neutral) / max(extreme - neutral, 1e-6))

    def _update_head_baseline(self, key, yaw, pitch, roll):
        """
        Update the head orientation baseline.
        Args:
            key: Tracking key
            yaw: Yaw angle
            pitch: Pitch angle
            roll: Roll angle (ignored)
        Returns:
            Updated baseline or None
        """
        if key is None:
            return None

        baseline = self.orientation_baseline.get(key)
        if baseline is None:
            self.orientation_baseline[key] = {
                'yaw': yaw,
                'pitch': pitch,
                'roll': 0.0,  # Set baseline roll to 0
                'frames': 1
            }
            return None

        # Only update baseline if current orientation is reasonably neutral
        if max(abs(yaw), abs(pitch)) > self.high_suspicious_gaze_threshold:
            return baseline

        frames = baseline.get('frames', 1)

        # Adaptive blending based on deviation
        def blend(axis, value):
            delta = abs(value - baseline[axis])
            if delta <= self.normal_gaze_threshold:
                alpha = 0.4  # Faster adaptation for small changes
            elif delta <= self.suspicious_gaze_threshold:
                alpha = 0.25
            else:
                alpha = 0.1  # Slow adaptation for large changes
            baseline[axis] = baseline[axis] * (1.0 - alpha) + value * alpha

        blend('yaw', yaw)
        blend('pitch', pitch)
        # Ignoring roll baseline updates
        # blend('roll', roll)
        baseline['frames'] = min(frames + 1, 1500)

        return baseline

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
                threshold = 0.15

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
