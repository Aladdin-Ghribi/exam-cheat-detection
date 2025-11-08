import os
import sys
import math
sys.path.append(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

import cv2
from ultralytics import YOLO
from config import YOLO_MODEL, CONFIDENCE_THRESHOLD, IMG_SIZE
from .object_tracker import ObjectTracker
from .exam_seat_manager import ExamSeatManager
from .pose_detector import PoseDetector
from .suspicion_scorer import SuspicionScorer




CHEATING_RELATED_CLASSES = {
  'cell_phone' : 67,
  'book' : 73,
  'laptop' : 63,
  'backpack' : 24,
  'handbag': 26,
#   'seat' : 56
  }

PERSON_CLASS_ID = 0
class YOLODetector:
    def __init__(self, model_path=YOLO_MODEL, enable_tracking=True, enable_seat_mapping=True, enable_pose=True, room_config=None):
        self.model = YOLO(model_path)
        self.target_class_ids= [PERSON_CLASS_ID] + list(CHEATING_RELATED_CLASSES.values())
        # now accessible via detector.CHEATING_RELATED_CLASSES
        self.CHEATING_RELATED_CLASSES = CHEATING_RELATED_CLASSES

        # Initialize tracker and seat manager if enabled
        self.enable_tracking = enable_tracking
        self.enable_seat_mapping = enable_seat_mapping
        self.enable_pose = enable_pose
        self.suspicion_scorer = None

        if self.enable_tracking:
            self.tracker = ObjectTracker()

        if self.enable_seat_mapping:
            self.seat_manager = ExamSeatManager()

        # Initialize pose detector if enabled
        if self.enable_pose:
            self.pose_detector = PoseDetector(
                model_complexity=0,  # Fastest model
                min_detection_confidence=0.4,  # Lower for better detection
                min_tracking_confidence=0.4,   # Lower for better tracking
                smoothing_factor=0.7,           # Reduced for more responsive detection
                history_length=10                # Increased for more stable tracking
            )
            self.suspicion_scorer = SuspicionScorer(
                history_length=10,  # Reduced for more responsive scoring
                smoothing_factor=0.5  # Reduced for more responsive scoring
            )

    def detect(self, source, save_image=False, save_path=None):
        results = self.model.predict(
            source=source,
            conf=CONFIDENCE_THRESHOLD,
            imgsz= IMG_SIZE,
            classes=self.target_class_ids,
            save=save_image,
            save_txt=False,#for custom results if needed
            stream=True,#stream result for video
            half= False,#half precision inference
            device='cuda',
            #half precision inference
        )

        for r in results:
            detections = []
            if r.boxes is not None:
                for box, cls_id_tensor, conf_tensor in zip(r.boxes.xyxy, r.boxes.cls, r.boxes.conf):
                   cls_id = int(cls_id_tensor)
                   conf = float(conf_tensor)
                   x1, y1, x2, y2 = box.tolist()
                   if cls_id in self.target_class_ids:
                        detections.append({
                            'class_id': cls_id,
                            'confidence': conf,
                            'bbox': [x1, y1, x2, y2]
                        })
            yield detections, r.orig_img


    # ✅ NEW: Method for single-frame detection (used by Flask)
    def detect_frame(self, frame):
        """
        Run detection on a single frame (NumPy array).
        Returns: dictionary with:
        - 'detections': list of detection dicts
        - 'seat_assignments': dict mapping seat_index -> track_id (if seat mapping enabled)
        """
        results = self.model.predict(
            source=frame,
            conf=CONFIDENCE_THRESHOLD,
            imgsz=IMG_SIZE,
            classes=self.target_class_ids,
            verbose=False
        )

        detections = []
        if results[0].boxes is not None:
            for box, cls_id_tensor, conf_tensor in zip(
                results[0].boxes.xyxy,
                results[0].boxes.cls,
                results[0].boxes.conf
            ):
                cls_id = int(cls_id_tensor)
                conf = float(conf_tensor)
                x1, y1, x2, y2 = box.tolist()
                if cls_id in self.target_class_ids:
                    detection = {
                        'class_id': cls_id,
                        'confidence': conf,
                        'bbox': [x1, y1, x2, y2]
                    }

                    # Add pose data if person detection and pose is enabled
                    if cls_id == PERSON_CLASS_ID and self.enable_pose:
                        # Crop person from frame
                        person_img = frame[int(y1):int(y2), int(x1):int(x2)]

                        # Skip if crop is invalid
                        if person_img.size > 0:
                            # Get track ID if available
                            track_id = None

                            # Detect pose for this person
                            pose_result = self.pose_detector.detect(person_img, track_id)

                            # Add pose data to detection
                            detection['pose'] = pose_result

                    detections.append(detection)

        # Apply tracking if enabled
        if self.enable_tracking:
            detections = self.tracker.update(detections)

        # Get seat assignments if enabled
        seat_assignments = None
        if self.enable_seat_mapping:
            seat_result = self.seat_manager.update(detections)
            seat_assignments = seat_result['zone_assignments']

        if self.enable_pose:
            self._annotate_behavior(detections)

        return {
            'detections': detections,
            'seat_assignments': seat_assignments
        }

    def _annotate_behavior(self, detections):
        object_detections = [det for det in detections if det['class_id'] != PERSON_CLASS_ID]
        active_keys = set()
        for detection in detections:
            if detection['class_id'] != PERSON_CLASS_ID:
                continue
            pose = detection.get('pose')
            behavior = {
                'head_orientation': None,
                'face_region': None,
                'hands': {
                    'left': {
                        'near_face': False,
                        'distance_to_face': None,
                        'near_object': False,
                        'distance_to_object': None,
                        'object_class': None,
                        'position': None,
                        'global_position': None,
                        'visible': False
                    },
                    'right': {
                        'near_face': False,
                        'distance_to_face': None,
                        'near_object': False,
                        'distance_to_object': None,
                        'object_class': None,
                        'position': None,
                        'global_position': None,
                        'visible': False
                    }
                }
            }
            if pose and pose.get('success'):
                behavior['head_orientation'] = pose.get('head_orientation')
                behavior['face_region'] = pose.get('face_region')
                behavior['hands']['left'] = self._build_behavior_hand_entry(detection, pose, object_detections, 'left')
                behavior['hands']['right'] = self._build_behavior_hand_entry(detection, pose, object_detections, 'right')
            detection['behavior'] = behavior
            if self.suspicion_scorer:
                suspicion = self.suspicion_scorer.score_detection(detection)
                key = suspicion.pop('key', None)
                behavior['suspicion'] = suspicion
                if key is not None:
                    active_keys.add(key)
        if self.suspicion_scorer:
            self.suspicion_scorer.prune(active_keys)

    def _build_behavior_hand_entry(self, detection, pose, object_detections, side):
        entry = {
            'near_face': False,
            'distance_to_face': None,
            'near_object': False,
            'distance_to_object': None,
            'object_class': None,
            'position': None,
            'global_position': None,
            'visible': False
        }
        hand_metrics = pose.get('hand_metrics')
        if not hand_metrics:
            return entry
        metrics = hand_metrics.get(side)
        if not metrics:
            return entry
        entry['distance_to_face'] = metrics.get('distance_to_face')
        entry['near_face'] = bool(metrics.get('near_face'))
        entry['position'] = metrics.get('position')
        entry['visible'] = bool(metrics.get('visible'))
        entry['face_threshold'] = metrics.get('face_threshold')
        if entry['position'] is None:
            return entry
        x1, y1, x2, y2 = detection['bbox']
        width = x2 - x1
        height = y2 - y1
        global_point = (
            float(x1 + entry['position'][0] * width),
            float(y1 + entry['position'][1] * height)
        )
        entry['global_position'] = global_point
        min_distance = None
        closest_class = None
        threshold = min(width, height) * 0.2
        if threshold <= 0:
            threshold = 30.0
        for obj in object_detections:
            distance = self._point_to_bbox_distance(global_point, obj['bbox'])
            if min_distance is None or distance < min_distance:
                min_distance = distance
                closest_class = self._class_label(obj['class_id'])
        if min_distance is not None and closest_class is not None:
            entry['distance_to_object'] = min_distance
            if min_distance <= threshold:
                entry['near_object'] = True
                entry['object_class'] = closest_class
        return entry

    def _point_to_bbox_distance(self, point, bbox):
        x, y = point
        x1, y1, x2, y2 = bbox
        if x < x1:
            dx = x1 - x
        elif x > x2:
            dx = x - x2
        else:
            dx = 0.0
        if y < y1:
            dy = y1 - y
        elif y > y2:
            dy = y - y2
        else:
            dy = 0.0
        if dx == 0.0 and dy == 0.0:
            return 0.0
        return math.hypot(dx, dy)

    def _class_label(self, class_id):
        names = self.model.names
        if isinstance(names, dict):
            return names.get(class_id, str(class_id))
        if isinstance(names, (list, tuple)) and class_id < len(names):
            return names[class_id]
        return str(class_id)

    def draw_detections(self, frame, detection_result):
        """
        Draw detections, tracking IDs, and seat assignments on the frame.

        Args:
            frame: Input frame
            detection_result: Dictionary returned by detect_frame

        Returns:
            Frame with annotations drawn
        """
        annotated_frame = frame.copy()
        detections = detection_result['detections']
        seat_assignments = detection_result.get('seat_assignments')

        # Draw seat map if available
        if self.enable_seat_mapping and seat_assignments is not None:
            annotated_frame = self.seat_manager.draw_zones(annotated_frame, seat_assignments)

        # Draw detections with tracking IDs
        for det in detections:
            x1, y1, x2, y2 = map(int, det['bbox'])
            label = f"{self.model.names[det['class_id']]} {det['confidence']:.2f}"

            # Add tracking ID if available
            if 'track_id' in det:
                label = f"[ID:{det['track_id']}] {label}"
                color = (0, 0, 255)  # Red for tracked persons

                # Draw stable position if available
                if 'stable_position' in det:
                    cx, cy = det['stable_position']
                    # Draw a larger, more visible point
                    cv2.circle(annotated_frame, (cx, cy), 8, (255, 255, 0), -1)  # Yellow circle
                    cv2.circle(annotated_frame, (cx, cy), 8, (0, 0, 0), 2)  # Black border
            else:
                color = (0, 255, 0)  # Green for untracked objects

            # Draw bounding box
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)

            # Draw pose skeleton if available and enabled
            if 'pose' in det and self.enable_pose and det['pose']['success']:
                # Draw pose skeleton on person in original frame
                pose_result = det['pose']

                # Draw pose landmarks
                if pose_result['head']:
                    for landmark in pose_result['head']:
                        x = int(x1 + landmark['x'] * (x2 - x1))
                        y = int(y1 + landmark['y'] * (y2 - y1))
                        cv2.circle(annotated_frame, (x, y), 5, (0, 0, 255), -1)  # Red for head

                if pose_result['shoulders']:
                    for landmark in pose_result['shoulders']:
                        x = int(x1 + landmark['x'] * (x2 - x1))
                        y = int(y1 + landmark['y'] * (y2 - y1))
                        cv2.circle(annotated_frame, (x, y), 5, (0, 255, 0), -1)  # Green for shoulders

                if pose_result['hands']:
                    for landmark in pose_result['hands']:
                        x = int(x1 + landmark['x'] * (x2 - x1))
                        y = int(y1 + landmark['y'] * (y2 - y1))
                        cv2.circle(annotated_frame, (x, y), 5, (255, 0, 0), -1)  # Blue for hands

                # Draw pose skeleton connections
                person_img = frame[int(y1):int(y2), int(x1):int(x2)]
                if person_img.size > 0:
                    # Draw connections on a temporary image
                    import numpy as np
                    temp_img = np.zeros_like(person_img)
                    skeleton_img = self.pose_detector.draw_landmarks(
                        temp_img,
                        pose_result['landmarks'],
                        connections=True
                    )

                    # Overlay skeleton on original frame
                    mask = skeleton_img > 0
                    annotated_frame[y1:y2, x1:x2][mask] = skeleton_img[mask]

            # Draw label
            (text_width, text_height), baseline = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
            cv2.rectangle(annotated_frame, (x1, y1 - text_height - baseline),
                          (x1 + text_width, y1), color, thickness=cv2.FILLED)
            cv2.putText(annotated_frame, label, (x1, y1 - baseline),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)

        return annotated_frame

    def get_room_map(self, seat_assignments=None):
        """
        Get a room map visualization.

        Args:
            seat_assignments: Dictionary mapping seat_index -> track_id

        Returns:
            Room map as an image
        """
        if not self.enable_seat_mapping:
            return None

        # Create a blank room map
        import numpy as np
        room_map = np.zeros((self.seat_manager.room_height, self.seat_manager.room_width, 3), dtype=np.uint8)

        # Draw zones
        return self.seat_manager.draw_zones(room_map, seat_assignments)
