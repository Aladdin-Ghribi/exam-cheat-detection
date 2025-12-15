import os
import sys
import math
import time
import torch
sys.path.append(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

import cv2
from ultralytics import YOLO
from config import YOLO_MODEL, YOLO_MODEL_OPTIONS, CONFIDENCE_THRESHOLD, IMG_SIZE_GPU, IMG_SIZE_CPU, IMG_SIZE_NANO, ENABLE_FRAME_SKIPPING, FRAME_SKIP_THRESHOLD_MS, MAX_FRAME_SKIP
from .object_tracker import ObjectTracker
from .exam_seat_manager import ExamSeatManager
from .pose_detector import PoseDetector
from .flagged_evidence_saver import FlaggedEvidenceSaver
from .suspicion_scorer import SuspicionScorer

CHEATING_RELATED_CLASSES = {
  'cell_phone' : 67,
  'book' : 73,
  'laptop' : 63,
  'backpack' : 24,
  'handbag': 26,
}

PERSON_CLASS_ID = 0

class YOLODetector:
    def __init__(self, model_path=YOLO_MODEL, enable_tracking=True, enable_seat_mapping=True, enable_pose=True, room_config=None, model_size="medium"):
        self.model = YOLO(model_path)
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model_size = model_size
        self.img_size = self._get_img_size()
        self.target_class_ids = [PERSON_CLASS_ID] + list(CHEATING_RELATED_CLASSES.values())
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
            self.pose_detector = PoseDetector(
                model_complexity=0,
                min_detection_confidence=0.4,
                min_tracking_confidence=0.4,
                smoothing_factor=0.7,
                history_length=10
            )
            self.suspicion_scorer = SuspicionScorer()

        self.evidence_saver = FlaggedEvidenceSaver()
        self.auto_save_enabled = True
        self.show_pose = True  # Default to showing pose skeleton
        self.show_confidence = True  # Default to showing confidence scores

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
            print(f"Invalid model size. Options: {list(YOLO_MODEL_OPTIONS.keys())}")
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
                    detection = {
                        'class_id': cls_id,
                        'confidence': conf,
                        'bbox': [x1, y1, x2, y2]
                    }

                    if cls_id == PERSON_CLASS_ID and self.enable_pose:
                        person_img = frame[int(y1):int(y2), int(x1):int(x2)]
                        if person_img.size > 0:
                            track_id = None
                            pose_result = self.pose_detector.detect(person_img, track_id)
                            detection['pose'] = pose_result

                    detections.append(detection)

        if self.enable_tracking:
            detections = self.tracker.update(detections)

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
            self.skip_frames = min(self.max_frame_skip, int(process_time / self.frame_skip_threshold))

        return result

    def _annotate_behavior(self, detections, frame):
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
                
                # Transform landmarks from cropped person image to full frame coordinates
                landmarks = pose.get('landmarks')
                if landmarks:
                    x1, y1, x2, y2 = detection['bbox']
                    width = x2 - x1
                    height = y2 - y1
                    transformed_landmarks = []
                    for lm in landmarks:
                        transformed_landmarks.append({
                            'x': (x1 + lm['x'] * width) / frame.shape[1],  # Normalize to full frame width
                            'y': (y1 + lm['y'] * height) / frame.shape[0],  # Normalize to full frame height
                            'z': lm['z'],
                            'visibility': lm['visibility']
                        })
                    behavior['pose_landmarks'] = transformed_landmarks
                
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
