from .suspicion_scorer import SuspicionScorer
from .flagged_evidence_saver import FlaggedEvidenceSaver
from .pose_detector import PoseDetector
from .exam_seat_manager import ExamSeatManager
from .object_tracker import ObjectTracker
from .face_recognizer import FaceRecognizer
from .suspicion_config import load_config
from config import YOLO_MODEL, YOLO_MODEL_OPTIONS, CONFIDENCE_THRESHOLD, IMG_SIZE_GPU, IMG_SIZE_CPU, IMG_SIZE_NANO, ENABLE_FRAME_SKIPPING, FRAME_SKIP_THRESHOLD_MS, MAX_FRAME_SKIP
from ultralytics import YOLO
import cv2
import os
import sys
import math
import time
import torch
import numpy as np
import gc  # For explicit garbage collection
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
# Higher than general CONFIDENCE_THRESHOLD to reduce false positives.
CHEATING_OBJECT_MIN_CONFIDENCE = 0.8


class YOLODetector:
    def __init__(self, model_path=YOLO_MODEL, enable_tracking=True, enable_seat_mapping=False, enable_pose=True, room_config=None, model_size="medium"):
        # 🔧 Configure PyTorch BEFORE loading model
        if torch.cuda.is_available():
            # Use correct environment variable name
            os.environ['PYTORCH_ALLOC_CONF'] = 'max_split_size_mb:512,expandable_segments:True'
            torch.cuda.empty_cache()

        self.model = YOLO(model_path)
        self.model.overrides['verbose'] = False  # Disable all verbose output

        config = load_config()

        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'

        self.model_size = model_size
        self.img_size = self._get_img_size()
        self.cheating_object_min_confidence = float(
            config.get('cheating_object_min_confidence', CHEATING_OBJECT_MIN_CONFIDENCE)
        )
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
        self.face_id_cache = {}  # track_id -> {id_type, primary_id, confidence, ...}
        self.face_id_last_check = {}  # track_id -> frame_count when last checked

        # Cache behavior (configurable via data/config.json)
        config = load_config()
        # Run face recognition every 15 frames (~once per half second at 30fps)
        self.face_check_interval = config.get('face_check_interval', 15)

        # Track retry/cooldown settings
        self.face_track_max_attempts = config.get('face_track_max_attempts', 3)
        self.face_track_cooldown_sec = config.get(
            'face_track_cooldown_sec', 10)
        self.face_track_fail_counts = {}  # track_id -> failed attempts
        self.face_track_cooldown_until = {}  # track_id -> timestamp

        # Debug flag
        self.face_debug = bool(config.get('face_debug', False)) or (
            os.getenv('FACE_DEBUG', '0') == '1')

        # Warm up the pipeline to reduce first-frame latency
        self.warmup()

    def warmup(self):
        """Pre-initialize models by running a dummy frame through the pipeline."""
        print("\n🔥 Warming up AI Pipeline (pre-allocating GPU memory)...")
        start = time.time()

        # Create a dummy black frame (standard 1080p or consistent with config)
        dummy_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)

        try:
            # 1. Warm up YOLO
            _ = self.model.predict(
                source=dummy_frame,
                imgsz=self.img_size,
                device=self.device,
                verbose=False
            )
            print("✅ YOLO Engine Warm")

            # 2. Warm up Pose Detector
            if self.enable_pose:
                # Use a small crop for pose warmup
                dummy_crop = dummy_frame[0:200, 0:200]
                _ = self.pose_detector.detect(dummy_crop)
                print("✅ Pose Estimation Warm")

            # 3. Face recognizer is initialized in __init__

            # 4. Clear cache after warmup to start clean
            if self.device == 'cuda':
                torch.cuda.empty_cache()

            duration = time.time() - start
            print(f"✨ Pipeline Ready (Warmup took {duration:.2f}s)\n")

        except Exception as e:
            print(f"⚠️ Warmup warning: {e}")

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

    def detect_frame(self, frame, metrics=None):
        """Run detection on a single frame with frame skipping support."""
        start_time = time.time()
        t_total_start = time.perf_counter()
        self.frame_count += 1
        skipped = False

        # Check if we should skip this frame
        if self.enable_frame_skipping and self.skip_frames > 0:
            self.skip_frames -= 1
            skipped = True
            result = self.last_detections if self.last_detections else {
                'detections': [],
                'seat_assignments': None
            }
            if metrics is not None:
                detections = result.get('detections', []) if result else []
                persons = sum(1 for d in detections if d.get('class_id') == PERSON_CLASS_ID)
                objects = max(0, len(detections) - persons)
                metrics.append({
                    'frame_index': self.frame_count,
                    'skipped': True,
                    'num_detections': len(detections),
                    'num_persons': persons,
                    'num_objects': objects,
                    'infer_ms': 0.0,
                    'post_ms': 0.0,
                    'filter_ms': 0.0,
                    'tracking_ms': 0.0,
                    'pose_ms': 0.0,
                    'face_ms': 0.0,
                    'behavior_ms': 0.0,
                    'evidence_ms': 0.0,
                    'total_ms': (time.perf_counter() - t_total_start) * 1000.0
                })
            return result

        t_infer_start = time.perf_counter()
        results = self.model.predict(
            source=frame,
            conf=CONFIDENCE_THRESHOLD,
            imgsz=self.img_size,
            classes=self.target_class_ids,
            device=self.device,
            half=False,
            verbose=False
        )
        t_infer_end = time.perf_counter()

        detections = []
        pose_ms = 0.0
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
                    # to reduce false positives from weak class assignments.
                    if cls_id != PERSON_CLASS_ID and conf < self.cheating_object_min_confidence:
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
                            t_pose_start = time.perf_counter()
                            pose_result = self.pose_detector.detect(
                                person_img, track_id)
                            t_pose_end = time.perf_counter()
                            pose_ms += (t_pose_end - t_pose_start) * 1000.0
                            detection['pose'] = pose_result

                    detections.append(detection)

        t_post_end = time.perf_counter()

        # Filter out duplicate/overlapping person detections
        detections = self._filter_overlapping_persons(detections)
        t_filter_end = time.perf_counter()

        tracking_ms = 0.0
        face_ms = 0.0
        if self.enable_tracking:
            t_track_start = time.perf_counter()
            detections = self.tracker.update(detections)
            t_track_end = time.perf_counter()
            tracking_ms = (t_track_end - t_track_start) * 1000.0

            # Face recognition
            # After tracking is updated, attempt to identify each person
            # Process at most one face per frame to limit CPU load
            face_processed_this_frame = False

            t_face_start = time.perf_counter()

            for det in detections:
                if det.get('class_id') == PERSON_CLASS_ID:
                    track_id = det.get('track_id')
                    if track_id is not None and self.face_recognizer is not None:
                        last_check = self.face_id_last_check.get(track_id, 0)
                        now = time.time()
                        cached = self.face_id_cache.get(track_id)

                        # Cooldown only applies to TRACK results
                        cooldown_until = self.face_track_cooldown_until.get(
                            track_id, 0)
                        in_cooldown = bool(
                            cached and cached.get(
                                'id_type') == 'TRACK' and now < cooldown_until
                        )

                        # Only run recognition if we have not processed a face this frame
                        # and it is time to recheck or the track is new
                        can_check = not face_processed_this_frame and not in_cooldown and (
                            self.frame_count - last_check >= self.face_check_interval or
                            track_id not in self.face_id_cache
                        )

                        if can_check:
                            attempt = self.face_track_fail_counts.get(
                                track_id, 0) + 1
                            if self.face_debug:
                                print(
                                    f"🔎 FaceCheck track={track_id} attempt={attempt}/{self.face_track_max_attempts}")
                            id_type, primary_id, confidence = self.face_recognizer.get_primary_id(
                                track_id, frame, det['bbox']
                            )
                            # Update cache
                            self.face_id_cache[track_id] = {
                                'id_type': id_type,
                                'primary_id': primary_id,
                                'id_confidence': confidence
                            }
                            self.face_id_last_check[track_id] = self.frame_count
                            face_processed_this_frame = True  # One per frame

                            # Retry/cooldown logic
                            if id_type == 'SID':
                                if self.face_debug:
                                    name = self.face_recognizer.student_names.get(
                                        primary_id, '')
                                    print(
                                        f"✅ FaceRecognized track={track_id} sid={primary_id} name={name} conf={confidence:.2f}")
                                self.face_track_fail_counts.pop(track_id, None)
                                self.face_track_cooldown_until.pop(
                                    track_id, None)
                            else:
                                if self.face_debug:
                                    print(
                                        f"❌ FaceFailed track={track_id} status=TRACK conf={confidence:.2f}")
                                failures = self.face_track_fail_counts.get(
                                    track_id, 0) + 1
                                if failures >= self.face_track_max_attempts:
                                    self.face_track_cooldown_until[track_id] = (
                                        now + self.face_track_cooldown_sec
                                    )
                                    failures = 0  # reset after cooldown
                                self.face_track_fail_counts[track_id] = failures

                        # Retrieve identity from cache
                        if track_id in self.face_id_cache:
                            cached = self.face_id_cache[track_id]
                            det['id_type'] = cached['id_type']
                            det['primary_id'] = cached['primary_id']
                            det['id_confidence'] = cached['id_confidence']

                            if det['id_type'] == 'SID':
                                det['student_id'] = det['primary_id']
                                det['student_name'] = self.face_recognizer.student_names.get(
                                    det['student_id'], '')
                        else:
                            # Not identified yet, use track ID
                            det['id_type'] = 'TRACK'
                            det['primary_id'] = f'TRACK_{track_id}'
                            det['id_confidence'] = 1.0

            t_face_end = time.perf_counter()
            face_ms = (t_face_end - t_face_start) * 1000.0

        seat_assignments = None
        seat_ms = 0.0
        if self.enable_seat_mapping:
            t_seat_start = time.perf_counter()
            seat_result = self.seat_manager.update(detections)
            seat_assignments = seat_result['zone_assignments']
            t_seat_end = time.perf_counter()
            seat_ms = (t_seat_end - t_seat_start) * 1000.0

        behavior_ms = 0.0
        if self.enable_pose:
            t_behavior_start = time.perf_counter()
            self._annotate_behavior(detections, frame)
            t_behavior_end = time.perf_counter()
            behavior_ms = (t_behavior_end - t_behavior_start) * 1000.0

        evidence_ms = 0.0
        if self.auto_save_enabled:
            t_evidence_start = time.perf_counter()
            self.evidence_saver.process_frame(frame, detections)
            t_evidence_end = time.perf_counter()
            evidence_ms = (t_evidence_end - t_evidence_start) * 1000.0

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

        # Remove aggressive cleanup that causes the "stutter" every 30 frames
        # Only clear cache if we see an actual memory warning in app.py
        pass

        if metrics is not None:
            persons = sum(1 for d in detections if d.get('class_id') == PERSON_CLASS_ID)
            objects = max(0, len(detections) - persons)
            metrics.append({
                'frame_index': self.frame_count,
                'skipped': skipped,
                'num_detections': len(detections),
                'num_persons': persons,
                'num_objects': objects,
                'infer_ms': (t_infer_end - t_infer_start) * 1000.0,
                'post_ms': (t_post_end - t_infer_end) * 1000.0,
                'filter_ms': (t_filter_end - t_post_end) * 1000.0,
                'tracking_ms': tracking_ms,
                'pose_ms': pose_ms,
                'face_ms': face_ms,
                'behavior_ms': behavior_ms,
                'evidence_ms': evidence_ms,
                'seat_ms': seat_ms,
                'total_ms': (time.perf_counter() - t_total_start) * 1000.0
            })

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
            'object_confidence': None,
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
        closest_confidence = None
        threshold = min(width, height) * 0.2
        if threshold <= 0:
            threshold = 30.0
        for obj in object_detections:
            distance = self._point_to_bbox_distance(global_point, obj['bbox'])
            if min_distance is None or distance < min_distance:
                min_distance = distance
                closest_class = self._class_label(obj['class_id'])
                closest_confidence = float(obj.get('confidence', 0.0))
        if min_distance is not None and closest_class is not None:
            entry['distance_to_object'] = min_distance
            if min_distance <= threshold:
                entry['near_object'] = True
                entry['object_class'] = closest_class
                entry['object_confidence'] = closest_confidence
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

    def draw_detections(self, frame, detection_result):
        """
        Draw detections onto a frame. Compatible with tools/video_replay.py which
        passes the full detection result dict returned by `detect_frame`.
        """
        # Accept either the raw detections list or the result dict
        if detection_result is None:
            return frame
        if isinstance(detection_result, dict):
            detections = detection_result.get('detections', [])
        else:
            detections = detection_result

        for det in detections:
            bbox = det.get('bbox')
            if not bbox or len(bbox) != 4:
                continue
            x1, y1, x2, y2 = map(int, bbox)
            class_id = det.get('class_id')
            if class_id == PERSON_CLASS_ID:
                color = (0, 255, 0)
                behavior = det.get('behavior', {})
                suspicion = behavior.get('suspicion', {})
                score = suspicion.get('smoothed', 0.0)
                label = f"person {score * 100:.0f}%"
            else:
                color = (0, 165, 255)
                label = self._class_label(class_id)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, label, (x1, max(20, y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        return frame
