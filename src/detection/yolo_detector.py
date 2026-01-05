from .suspicion_scorer import SuspicionScorer
from .flagged_evidence_saver import FlaggedEvidenceSaver
from .pose_detector import PoseDetector
from .exam_seat_manager import ExamSeatManager
from .object_tracker import ObjectTracker
from .face_recognizer import FaceRecognizer
from config import YOLO_MODEL, YOLO_MODEL_OPTIONS, CONFIDENCE_THRESHOLD, IMG_SIZE_GPU, IMG_SIZE_CPU, IMG_SIZE_NANO, ENABLE_FRAME_SKIPPING, FRAME_SKIP_THRESHOLD_MS, MAX_FRAME_SKIP
from ultralytics import YOLO
import cv2
import os
import sys
import math
import time
import torch
sys.path.append(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))


CHEATING_RELATED_CLASSES = {
    'cell_phone': 67,
    'book': 73,
    'laptop': 63,
    'backpack': 24,
    'handbag': 26,
}

PERSON_CLASS_ID = 0

# Minimum confidence specifically for cheating objects (phones, books, etc.)
# Higher than general CONFIDENCE_THRESHOLD to reduce false positives
CHEATING_OBJECT_MIN_CONFIDENCE = 0.5


class YOLODetector:
    def __init__(self, model_path=YOLO_MODEL, enable_tracking=True, enable_seat_mapping=True, enable_pose=True, room_config=None, model_size="medium"):
        self.model = YOLO(model_path)
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model_size = model_size
        self.img_size = self._get_img_size()
        self.target_class_ids = [PERSON_CLASS_ID] + \
            list(CHEATING_RELATED_CLASSES.values())
        self.CHEATING_RELATED_CLASSES = CHEATING_RELATED_CLASSES

        # Frame skipping for performance
        self.frame_count = 0
        self.skip_frames = 0
        self.last_process_time = 0
        self.enable_frame_skipping = ENABLE_FRAME_SKIPPING
        self.frame_skip_threshold = FRAME_SKIP_THRESHOLD_MS
        self.max_frame_skip = MAX_FRAME_SKIP
        self.last_detections = None

        # Initialize tracker and seat manager if enabled
        self.enable_tracking = enable_tracking
        self.enable_seat_mapping = enable_seat_mapping
        self.enable_pose = enable_pose
        self.suspicion_scorer = None

        if self.enable_tracking:
            self.tracker = ObjectTracker()

        if self.enable_seat_mapping:
            self.seat_manager = ExamSeatManager()

        if self.enable_pose:
            # Model complexity for pose detection (0=lite, 1=full, 2=heavy)
            self.model_complexity = 0  # Default, can be updated via config
            self.pose_detector = PoseDetector(
                model_complexity=self.model_complexity,
                min_detection_confidence=0.4,
                min_tracking_confidence=0.4,
                smoothing_factor=0.7,
                history_length=10
            )
            self.suspicion_scorer = SuspicionScorer()

        self.evidence_saver = FlaggedEvidenceSaver()
        self.auto_save_enabled = True
        # Default to showing bounding boxes (can be overridden by config)
        self.show_bbox = True
        self.show_pose = True  # Default to showing pose skeleton
        self.show_confidence = True  # Default to showing confidence scores

        # Initialize Face Recognizer
        self.face_recognizer = FaceRecognizer()

    def _get_img_size(self):
        """Get appropriate image size based on model size and device."""
        if self.model_size == "nano":
            return IMG_SIZE_NANO
        elif self.model_size == "small":
            return IMG_SIZE_CPU
        else:  # medium
            return IMG_SIZE_GPU if self.device == 'cuda' else IMG_SIZE_CPU

    def switch_model(self, model_size):
        """Switch to a different YOLO model size."""
        if model_size not in YOLO_MODEL_OPTIONS:
            print(
                f"Invalid model size. Options: {list(YOLO_MODEL_OPTIONS.keys())}")
            return False

        model_path = YOLO_MODEL_OPTIONS[model_size]
        if not os.path.exists(model_path):
            print(f"Model file not found: {model_path}")
            return False

        self.model = YOLO(model_path)
        self.model_size = model_size
        self.img_size = self._get_img_size()
        print(f"Switched to {model_size} model ({model_path})")
        return True

    def detect_frame(self, frame):
        """Run detection on a single frame with frame skipping support."""
        start_time = time.time()
        self.frame_count += 1

        # Check if we should skip this frame
        if self.enable_frame_skipping and self.skip_frames > 0:
            self.skip_frames -= 1
            return self.last_detections if self.last_detections else {'detections': [], 'seat_assignments': None}

        results = self.model.predict(
            source=frame,
            conf=CONFIDENCE_THRESHOLD,
            imgsz=self.img_size,
            classes=self.target_class_ids,
            device=self.device,
            half=False,
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
                    # Skip low-confidence cheating objects (phones, books, etc.)
                    # to reduce false positives
                    if cls_id != PERSON_CLASS_ID and conf < CHEATING_OBJECT_MIN_CONFIDENCE:
                        continue

                    detection = {
                        'class_id': cls_id,
                        'confidence': conf,
                        'bbox': [x1, y1, x2, y2]
                    }

                    if cls_id == PERSON_CLASS_ID and self.enable_pose:
                        person_img = frame[int(y1):int(y2), int(x1):int(x2)]
                        if person_img.size > 0:
                            track_id = None
                            pose_result = self.pose_detector.detect(
                                person_img, track_id)
                            detection['pose'] = pose_result

                    detections.append(detection)

        # Filter out duplicate/overlapping person detections (e.g., extended arms detected as persons)
        detections = self._filter_overlapping_persons(detections)

        if self.enable_tracking:
            detections = self.tracker.update(detections)

            # 🎯 FACE RECOGNITION INTEGRATION
            # After tracking is updated, attempt to identify each person
            for det in detections:
                if det.get('class_id') == PERSON_CLASS_ID:
                    track_id = det.get('track_id')
                    if track_id is not None:
                        # Get identity (SID or falling back to track_id)
                        id_type, primary_id, confidence = self.face_recognizer.get_primary_id(
                            track_id, frame, det['bbox']
                        )

                        det['id_type'] = id_type          # 'SID' or 'TRACK'
                        # e.g., 'S12345' or 'TRACK_7'
                        det['primary_id'] = primary_id
                        det['id_confidence'] = confidence

                        # If recognized as a student, add student info
                        if id_type == 'SID':
                            det['student_id'] = primary_id
                            det['student_name'] = self.face_recognizer.student_names.get(
                                primary_id, '')

        seat_assignments = None
        if self.enable_seat_mapping:
            seat_result = self.seat_manager.update(detections)
            seat_assignments = seat_result['zone_assignments']

        if self.enable_pose:
            self._annotate_behavior(detections, frame)

        if self.auto_save_enabled:
            self.evidence_saver.process_frame(frame, detections)

        result = {
            'detections': detections,
            'seat_assignments': seat_assignments
        }

        self.last_detections = result

        # Check processing time and enable frame skipping if needed
        process_time = (time.time() - start_time) * 1000
        self.last_process_time = process_time

        if self.enable_frame_skipping and process_time > self.frame_skip_threshold:
            self.skip_frames = min(self.max_frame_skip, int(
                process_time / self.frame_skip_threshold))

        return result

    def _annotate_behavior(self, detections, frame):
        object_detections = [
            det for det in detections if det['class_id'] != PERSON_CLASS_ID]
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

                # Transform landmarks from cropped person image to full frame coordinates
                landmarks = pose.get('landmarks')
                if landmarks:
                    x1, y1, x2, y2 = detection['bbox']
                    width = x2 - x1
                    height = y2 - y1
                    transformed_landmarks = []
                    for lm in landmarks:
                        transformed_landmarks.append({
                            # Normalize to full frame width
                            'x': (x1 + lm['x'] * width) / frame.shape[1],
                            # Normalize to full frame height
                            'y': (y1 + lm['y'] * height) / frame.shape[0],
                            'z': lm['z'],
                            'visibility': lm['visibility']
                        })
                    behavior['pose_landmarks'] = transformed_landmarks

                behavior['hands']['left'] = self._build_behavior_hand_entry(
                    detection, pose, object_detections, 'left')
                behavior['hands']['right'] = self._build_behavior_hand_entry(
                    detection, pose, object_detections, 'right')
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

    def _filter_overlapping_persons(self, detections, iou_threshold=0.5):
        """
        Filter out overlapping person detections to prevent duplicates
        (e.g., extended arms being detected as separate persons).
        Keeps the detection with higher confidence when two overlap.
        """
        person_detections = [
            d for d in detections if d['class_id'] == PERSON_CLASS_ID]
        other_detections = [
            d for d in detections if d['class_id'] != PERSON_CLASS_ID]

        if len(person_detections) <= 1:
            return detections

        # Sort by confidence (highest first)
        person_detections.sort(key=lambda x: x.get(
            'confidence', 0), reverse=True)

        keep = []
        suppressed = set()

        for i, det_a in enumerate(person_detections):
            if i in suppressed:
                continue
            keep.append(det_a)

            box_a = det_a['bbox']
            area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])

            for j in range(i + 1, len(person_detections)):
                if j in suppressed:
                    continue

                box_b = person_detections[j]['bbox']
                area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])

                # Compute IoU
                x1 = max(box_a[0], box_b[0])
                y1 = max(box_a[1], box_b[1])
                x2 = min(box_a[2], box_b[2])
                y2 = min(box_a[3], box_b[3])

                if x2 > x1 and y2 > y1:
                    intersection = (x2 - x1) * (y2 - y1)
                    union = area_a + area_b - intersection
                    iou = intersection / union if union > 0 else 0

                    # Also check if one box is mostly inside the other
                    min_area = min(area_a, area_b)
                    overlap_ratio = intersection / min_area if min_area > 0 else 0

                    # Check if the smaller box is significantly smaller (likely a false detection like an arm)
                    # If both boxes are similar in size, they're likely two different people
                    max_area = max(area_a, area_b)
                    size_ratio = min_area / max_area if max_area > 0 else 1

                    # Only suppress if:
                    # 1. High IoU/overlap AND smaller box is much smaller than larger (size_ratio < 0.5)
                    # 2. This prevents filtering out two overlapping people of similar size
                    if (iou > iou_threshold or overlap_ratio > 0.7) and size_ratio < 0.5:
                        suppressed.add(j)

        return keep + other_detections

    def _class_label(self, class_id):
        names = self.model.names
        if isinstance(names, dict):
            return names.get(class_id, str(class_id))
        if isinstance(names, (list, tuple)) and class_id < len(names):
            return names[class_id]
        return str(class_id)

    def set_auto_save(self, enabled):
        self.auto_save_enabled = enabled
        if hasattr(self, 'evidence_saver'):
            self.evidence_saver.auto_save_enabled = enabled

    def get_performance_stats(self):
        """Get current performance statistics."""
        return {
            'model_size': self.model_size,
            'device': self.device,
            'last_process_time_ms': self.last_process_time,
            'frame_count': self.frame_count,
            'skip_frames_active': self.skip_frames
        }

    def set_model_complexity(self, complexity):
        """
        Set pose detection model complexity and reinitialize pose_detector.

        Args:
            complexity: 0 (lite), 1 (full), or 2 (heavy)
        """
        if not self.enable_pose:
            return False

        if complexity not in [0, 1, 2]:
            print(
                f"Invalid model complexity: {complexity}. Must be 0, 1, or 2.")
            return False

        if self.model_complexity == complexity:
            return True  # Already set

        print(
            f"Updating pose model complexity from {self.model_complexity} to {complexity}")
        self.model_complexity = complexity

        # Reinitialize pose detector with new complexity
        self.pose_detector = PoseDetector(
            model_complexity=complexity,
            min_detection_confidence=0.4,
            min_tracking_confidence=0.4,
            smoothing_factor=0.7,
            history_length=10
        )
        print(f"Pose detector reinitialized with complexity {complexity}")
        return True
