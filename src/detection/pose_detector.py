
import cv2
import mediapipe as mp
import numpy as np
from collections import deque


class PoseDetector:
    """
    Optimized MediaPipe Pose detector with smoothing for extracting 2D/3D coordinates.
    """

    def __init__(self, static_image_mode=False, model_complexity=0,
                 enable_segmentation=False, min_detection_confidence=0.3,
                 min_tracking_confidence=0.3, smoothing_factor=0.3, history_length=3):
        """
        Initialize MediaPipe Pose with optimization parameters.

        Args:
            static_image_mode: Whether to treat the input images as a batch of static
                and possibly unrelated images, or a video stream.
            model_complexity: Complexity of the pose landmark model (0, 1, or 2).
            enable_segmentation: Whether to enable segmentation.
            min_detection_confidence: Minimum confidence value ([0.0, 1.0]) for person detection.
            min_tracking_confidence: Minimum confidence value ([0.0, 1.0]) for tracking.
            smoothing_factor: Factor for smoothing landmarks (0.0-1.0, higher = more smoothing)
            history_length: Number of previous frames to use for smoothing
        """
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles

        self.pose = self.mp_pose.Pose(
            static_image_mode=static_image_mode,
            # 0=Lite (Fastest for real-time), 1=Full, 2=Heavy
            model_complexity=0,
            enable_segmentation=False,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )

        # High-speed smoothing
        self.smoothing_factor = smoothing_factor
        self.history_length = 5
        self.landmark_history = {}
        self.orientation_history = {}

        self.head_landmarks = [0]
        self.shoulder_landmarks = [11, 12]
        self.hand_landmarks = [19, 20, 21, 22]
        self.visibility_threshold = 0.5
        # Nose, left eye, right eye, mouth corners, shoulders
        self.head_pose_landmarks = [0, 2, 5, 9, 10, 11, 12]
        self.face_landmarks = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        self.left_hand_indices = [15, 17, 19, 21]
        self.right_hand_indices = [16, 18, 20, 22]
        # Optimized 3D head model for cheating detection
        self.head_pose_model_points = np.array([
            [0.0, 0.0, 0.0],
            [-40.0, -30.0, -10.0],
            [40.0, -30.0, -10.0],
            [-30.0, 40.0, -15.0],
            [30.0, 40.0, -15.0],
            [-70.0, 60.0, -50.0],
            [70.0, 60.0, -50.0]
        ], dtype=np.float32)

    def detect(self, image, track_id=None):
        """
        Process an image and detect pose landmarks with smoothing.

        Args:
            image: Input image (BGR format)
            track_id: Optional track ID for smoothing across frames

        Returns:
            Dictionary containing:
                - success: Boolean indicating if pose was detected
                - landmarks: List of landmarks (x, y, z, visibility)
                - head: Head landmarks
                - shoulders: Shoulder landmarks
                - hands: Hand landmarks
                - image: Processed image with pose drawn (if draw_landmarks=True)
        """
        # Convert the BGR image to RGB
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Process the image and find pose landmarks
        results = self.pose.process(rgb_image)

        # Initialize result dictionary
        result = {
            'success': False,
            'landmarks': None,
            'head': None,
            'shoulders': None,
            'hands': None,
            'head_orientation': None,
            'hand_metrics': None,
            'face_region': None
        }

        if results.pose_landmarks:
            result['success'] = True

            # Extract all landmarks
            landmarks = []
            for landmark in results.pose_landmarks.landmark:
                landmarks.append({
                    'x': landmark.x,
                    'y': landmark.y,
                    'z': landmark.z,
                    'visibility': landmark.visibility
                })

            # Apply smoothing if track_id is provided and we have history
            if track_id is not None and track_id in self.landmark_history:
                landmarks = self._smooth_landmarks(landmarks, track_id)

            # Store landmarks in history for smoothing
            if track_id is not None:
                if track_id not in self.landmark_history:
                    self.landmark_history[track_id] = deque(
                        maxlen=self.history_length)
                self.landmark_history[track_id].append(landmarks)

            result['landmarks'] = landmarks

            # Extract head landmarks
            head = []
            for idx in self.head_landmarks:
                landmark = landmarks[idx]
                head.append({
                    'x': landmark['x'],
                    'y': landmark['y'],
                    'z': landmark['z'],
                    'visibility': landmark['visibility']
                })
            result['head'] = head

            # Extract shoulder landmarks
            shoulders = []
            for idx in self.shoulder_landmarks:
                landmark = landmarks[idx]
                shoulders.append({
                    'x': landmark['x'],
                    'y': landmark['y'],
                    'z': landmark['z'],
                    'visibility': landmark['visibility']
                })
            result['shoulders'] = shoulders

            # Extract hand landmarks
            hands = []
            for idx in self.hand_landmarks:
                landmark = landmarks[idx]
                hands.append({
                    'x': landmark['x'],
                    'y': landmark['y'],
                    'z': landmark['z'],
                    'visibility': landmark['visibility']
                })
            result['hands'] = hands
            result['head_orientation'] = self._estimate_head_orientation(
                landmarks, image.shape, track_id)
            hand_metrics, face_region = self._compute_hand_metrics(landmarks)
            result['hand_metrics'] = hand_metrics
            result['face_region'] = face_region

        return result

    def _estimate_head_orientation(self, landmarks, image_shape, track_id=None):
        if landmarks is None or len(landmarks) <= max(self.head_pose_landmarks):
            return None
        height, width = image_shape[:2]

        # Validate landmarks
        valid_count = sum(1 for idx in self.head_pose_landmarks
                          if landmarks[idx]['visibility'] >= self.visibility_threshold)
        if valid_count < 5:
            return None

        image_points = []
        for idx in self.head_pose_landmarks:
            landmark = landmarks[idx]
            if landmark['visibility'] < self.visibility_threshold:
                return None
            image_points.append(
                [landmark['x'] * width, landmark['y'] * height])

        image_points = np.array(image_points, dtype=np.float32)
        focal_length = width * 1.2
        center = (width / 2.0, height / 2.0)
        camera_matrix = np.array([
            [focal_length, 0.0, center[0]],
            [0.0, focal_length, center[1]],
            [0.0, 0.0, 1.0]
        ], dtype=np.float32)
        dist_coeffs = np.zeros((4, 1), dtype=np.float32)

        success, rotation_vector, translation_vector = cv2.solvePnP(
            self.head_pose_model_points,
            image_points,
            camera_matrix,
            dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE
        )

        if not success:
            return None

        rotation_matrix, _ = cv2.Rodrigues(rotation_vector)
        angles = self._rotation_matrix_to_euler(rotation_matrix)
        pitch, yaw, roll = angles[0], angles[1], angles[2]

        if np.isnan(pitch) or np.isnan(yaw) or np.isnan(roll):
            return None

        orientation = {'pitch': pitch, 'yaw': yaw, 'roll': roll}
        if track_id is not None:
            orientation = self._smooth_orientation(orientation, track_id)

        return {
            'pitch': float(orientation['pitch']),
            'yaw': float(orientation['yaw']),
            'roll': float(orientation['roll']),
            'translation': translation_vector.flatten().astype(float).tolist()
        }

    def _compute_hand_metrics(self, landmarks):
        if landmarks is None or len(landmarks) <= max(self.right_hand_indices):
            return (None, None)
        face_points = []
        for idx in self.face_landmarks:
            landmark = landmarks[idx]
            if landmark['visibility'] >= self.visibility_threshold:
                face_points.append([landmark['x'], landmark['y']])
        if not face_points:
            return (None, None)
        face_points = np.array(face_points, dtype=np.float32)
        face_center = face_points.mean(axis=0)
        radius = np.mean(np.linalg.norm(face_points - face_center, axis=1))
        if radius <= 0:
            radius = 1e-6
        left_position = self._average_landmark_position(
            landmarks, self.left_hand_indices)
        right_position = self._average_landmark_position(
            landmarks, self.right_hand_indices)
        hand_metrics = {
            'left': self._build_hand_metric(left_position, face_center, radius),
            'right': self._build_hand_metric(right_position, face_center, radius)
        }
        face_region = {
            'center': (float(face_center[0]), float(face_center[1])),
            'radius': float(radius)
        }
        return (hand_metrics, face_region)

    def _average_landmark_position(self, landmarks, indices):
        points = []
        for idx in indices:
            if idx < len(landmarks):
                landmark = landmarks[idx]
                if landmark['visibility'] >= self.visibility_threshold:
                    points.append([landmark['x'], landmark['y']])
        if not points:
            return None
        return np.mean(np.array(points, dtype=np.float32), axis=0)

    def _build_hand_metric(self, position, face_center, radius):
        if position is None:
            return {
                'distance_to_face': None,
                'near_face': False,
                'position': None,
                'visible': False
            }
        distance = float(np.linalg.norm(position - face_center))
        # Use a more sensitive threshold for better detection
        threshold = radius * 1.4 if radius > 0 else 0.15
        # Add additional proximity levels for more nuanced scoring
        very_close_threshold = radius * 0.7 if radius > 0 else 0.075
        somewhat_close_threshold = radius * 2.0 if radius > 0 else 0.2

        return {
            'distance_to_face': distance,
            'near_face': distance <= threshold,
            'very_near_face': distance <= very_close_threshold,
            'somewhat_near_face': distance <= somewhat_close_threshold,
            'position': (float(position[0]), float(position[1])),
            'visible': True,
            'face_threshold': float(threshold),
            'very_close_threshold': float(very_close_threshold),
            'somewhat_close_threshold': float(somewhat_close_threshold)
        }

    def _rotation_matrix_to_euler(self, rotation_matrix):
        """
        Convert rotation matrix to Euler angles (pitch, yaw, roll) in degrees
        OpenCV coordinate system:
        X: right, Y: down, Z: forward (out of camera)

        Returns:
            [pitch, yaw, roll] in degrees where:
            pitch: rotation around X-axis (negative = up, positive = down)
            yaw: rotation around Y-axis (negative = left, positive = right)
            roll: rotation around Z-axis (negative = left tilt, positive = right tilt)
        """
        sy = np.sqrt(rotation_matrix[0, 0]**2 + rotation_matrix[1, 0]**2)
        singular = sy < 1e-6

        if not singular:
            pitch = np.arctan2(-rotation_matrix[2, 0], sy)
            yaw = np.arctan2(rotation_matrix[1, 0], rotation_matrix[0, 0])
            roll = np.arctan2(rotation_matrix[2, 1], rotation_matrix[2, 2])
        else:
            pitch = np.arctan2(-rotation_matrix[2, 0], sy)
            yaw = 0.0
            roll = np.arctan2(-rotation_matrix[1, 2], rotation_matrix[1, 1])

        pitch_deg = np.degrees(pitch)
        yaw_deg = np.degrees(yaw)
        roll_deg = np.degrees(roll)

        # Apply realistic head movement limits
        # Can't look completely up/down
        pitch_deg = np.clip(pitch_deg, -45, 45)
        # Can't turn head completely around
        yaw_deg = np.clip(yaw_deg, -90, 90)
        roll_deg = np.clip(roll_deg, -45, 45)     # Limited head tilt

        return np.array([pitch_deg, yaw_deg, roll_deg], dtype=np.float32)

    def _smooth_orientation(self, current_orientation, track_id):
        if track_id not in self.orientation_history:
            self.orientation_history[track_id] = deque(
                maxlen=self.history_length)
            self.orientation_history[track_id].append(current_orientation)
            return current_orientation

        prev_orientation = self.orientation_history[track_id][-1]
        alpha = 0.2

        smoothed = {
            'pitch': alpha * current_orientation['pitch'] + (1 - alpha) * prev_orientation['pitch'],
            'yaw': alpha * current_orientation['yaw'] + (1 - alpha) * prev_orientation['yaw'],
            'roll': alpha * current_orientation['roll'] + (1 - alpha) * prev_orientation['roll']
        }

        self.orientation_history[track_id].append(smoothed)
        return smoothed

    def _smooth_landmarks(self, current_landmarks, track_id):
        if track_id not in self.landmark_history or len(self.landmark_history[track_id]) < 1:
            return current_landmarks

        prev_landmarks = self.landmark_history[track_id][-1]
        alpha = self.smoothing_factor
        smoothed_landmarks = []

        for i, current in enumerate(current_landmarks):
            smoothed_landmarks.append({
                'x': alpha * current['x'] + (1 - alpha) * prev_landmarks[i]['x'],
                'y': alpha * current['y'] + (1 - alpha) * prev_landmarks[i]['y'],
                'z': alpha * current['z'] + (1 - alpha) * prev_landmarks[i]['z'],
                'visibility': current['visibility']
            })

        return smoothed_landmarks

    def draw_landmarks(self, image, landmarks, connections=True):
        """
        Draw pose landmarks on the image.

        Args:
            image: Input image
            landmarks: MediaPipe pose landmarks
            connections: Whether to draw connections between landmarks

        Returns:
            Image with landmarks drawn
        """
        annotated_image = image.copy()

        if landmarks:
            # Draw each landmark directly
            h, w, _ = image.shape
            for landmark in landmarks:
                # Convert normalized coordinates to pixel coordinates
                x = int(landmark['x'] * w)
                y = int(landmark['y'] * h)

                # Draw a circle for each landmark
                # Smaller circles for performance
                cv2.circle(annotated_image, (x, y), 3, (0, 255, 0), -1)

            # Draw connections if requested
            if connections:
                # Define connections between landmarks (simplified version)
                connections_list = [
                    (0, 1), (1, 2), (2, 3), (3, 7),  # Head connections
                    (0, 4), (4, 5), (5, 6), (6, 8),  # Head connections
                    (9, 10),  # Shoulders
                    (11, 12),  # Shoulders
                    (11, 13), (13, 15), (15, 17), (15,
                                                   # Left arm
                                                   19), (15, 21), (17, 19),
                    (12, 14), (14, 16), (16, 18), (16,
                                                   # Right arm
                                                   20), (16, 22), (18, 20),
                    (11, 23), (12, 24),  # Torso
                    (23, 24),  # Hips
                    (23, 25), (25, 27), (27, 29), (27, 31),  # Left leg
                    (24, 26), (26, 28), (28, 30), (28, 32),  # Right leg
                ]

                for start_idx, end_idx in connections_list:
                    if start_idx < len(landmarks) and end_idx < len(landmarks):
                        start = landmarks[start_idx]
                        end = landmarks[end_idx]

                        # Convert normalized coordinates to pixel coordinates
                        start_x = int(start['x'] * w)
                        start_y = int(start['y'] * h)
                        end_x = int(end['x'] * w)
                        end_y = int(end['y'] * h)

                        # Draw a line for the connection
                        # Thinner lines for performance
                        cv2.line(annotated_image, (start_x, start_y),
                                 (end_x, end_y), (0, 255, 0), 1)

        return annotated_image

    def get_posture_metrics(self, landmarks):
        """
        Calculate posture metrics from landmarks.

        Args:
            landmarks: List of landmarks

        Returns:
            Dictionary with posture metrics
        """
        if not landmarks:
            return None

        # Extract key points
        nose = landmarks[0]
        left_shoulder = landmarks[11]
        right_shoulder = landmarks[12]
        left_wrist = landmarks[19]
        right_wrist = landmarks[20]

        # Calculate shoulder tilt (angle between horizontal and line connecting shoulders)
        shoulder_vector = np.array([right_shoulder['x'] - left_shoulder['x'],
                                   right_shoulder['y'] - left_shoulder['y']])
        horizontal_vector = np.array([1, 0])
        shoulder_tilt = np.arccos(np.clip(np.dot(shoulder_vector, horizontal_vector) /
                                          (np.linalg.norm(shoulder_vector) * np.linalg.norm(horizontal_vector)), -1.0, 1.0))
        shoulder_tilt_degrees = np.degrees(shoulder_tilt)

        # Calculate head tilt (angle between vertical and line connecting nose to midpoint of shoulders)
        shoulder_midpoint = [(left_shoulder['x'] + right_shoulder['x']) / 2,
                             (left_shoulder['y'] + right_shoulder['y']) / 2]
        head_vector = np.array([nose['x'] - shoulder_midpoint[0],
                               nose['y'] - shoulder_midpoint[1]])
        vertical_vector = np.array([0, 1])
        head_tilt = np.arccos(np.clip(np.dot(head_vector, vertical_vector) /
                                      (np.linalg.norm(head_vector) * np.linalg.norm(vertical_vector)), -1.0, 1.0))
        head_tilt_degrees = np.degrees(head_tilt)

        # Calculate arm positions
        left_arm_raised = left_wrist['y'] < left_shoulder['y']
        right_arm_raised = right_wrist['y'] < right_shoulder['y']

        return {
            'shoulder_tilt': shoulder_tilt_degrees,
            'head_tilt': head_tilt_degrees,
            'left_arm_raised': left_arm_raised,
            'right_arm_raised': right_arm_raised
        }

    def close(self):
        """Close resources."""
        self.pose.close()
