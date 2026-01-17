"""
Face Recognition Module for Exam Cheat Detection System

The Primary 'Best' Implementation:
- Model: ArcFace (99.4% accuracy)
- Backend: DeepFace
- Hardware: GPU Accelerated (RTX 3070/4060/1660Ti)
- Strategy: Hybrid SID/Track mapping with session caching
"""

import os
import cv2
import numpy as np
import base64
import pickle
from pathlib import Path
from deepface import DeepFace

# --- GPU & Engine Optimization Setup ---
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_FORCE_GPU_ALLOW_GROWTH'] = 'true'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

try:
    import tensorflow as tf
    # Force GPU detection and memory growth
    gpus = tf.config.list_physical_devices('GPU')
    if gpus:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)

        # Performance boosting policies
        # from tensorflow.keras import mixed_precision
        # try:
        #     mixed_precision.set_global_policy('mixed_float16')
        #     print("🚀 Face AI: GPU acceleration ENABLED (FP16 Mixed Precision)")
        # except:
        #     print("✅ Face AI: GPU acceleration ENABLED")
        print("✅ Face AI: GPU acceleration ENABLED")
    else:
        # On Native Windows, TF 2.11+ is CPU only. This is normal.
        # We compensate with the ultra-light GhostFaceNet model.
        print("⚡ Face AI: Native Windows Optimized (CPU Mode)")
except Exception:
    pass


class FaceRecognizer:
    def __init__(self, database_path="data/student_faces", model_name="GhostFaceNet"):
        """
        Initialize the system with high-efficiency models.
        GhostFaceNet is faster and more compliant with Keras 3.
        """
        self.database_path = Path(database_path)
        self.model_name = model_name
        self.student_database = {}  # SID -> embedding
        self.student_names = {}     # SID -> name
        self.student_photos = {}    # SID -> base64
        self.track_to_sid = {}      # Session Cache: track_id -> SID

        # Performance Settings
        # Balanced threshold for ArcFace (0.58 is great for varying distances)
        self.recognition_threshold = 0.58
        self.recognition_interval = 1     # Run every time it's called
        self.frame_counters = {}

        # Spatial cache: detects same person even if track ID changes
        # Stores: (center_x, center_y, student_id, student_name, timestamp)
        self.spatial_cache = []
        self.spatial_cache_ttl = 5.0  # 5 seconds (was 3)
        self.spatial_match_threshold = 150  # pixels (was 100)

        # Detector Backend
        # 'opencv' is fast and reliable for cropping faces to feed into ArcFace
        self.detector_backend = 'opencv'

        # Load existing database
        self._load_database()

        # Pre-build/verify model to ensure it's ready on GPU
        try:
            print(f"🚀 Initializing {self.model_name}...")
            DeepFace.build_model(self.model_name)
            print(f"✅ {self.model_name} ready")
        except Exception as e:
            print(f"❌ Failed to load {self.model_name}: {e}")

    def get_primary_id(self, track_id, frame, bbox):
        """
        Returns (id_type, primary_id, confidence)
        Checks session cache first, then spatial cache, then runs ArcFace.
        """
        import time

        # Calculate center of bbox for spatial matching
        cx = (bbox[0] + bbox[2]) / 2
        cy = (bbox[1] + bbox[3]) / 2
        current_time = time.time()

        # 1. Check Session Cache (Instant - by track ID)
        if track_id in self.track_to_sid:
            sid = self.track_to_sid[track_id]
            name = self.student_names.get(sid, '')
            return ('SID', sid, 1.0)

        # 2. Check Spatial Cache (handles unstable track IDs)
        # Clean expired entries
        self.spatial_cache = [
            entry for entry in self.spatial_cache
            if current_time - entry['time'] < self.spatial_cache_ttl
        ]

        # Find nearby match
        for entry in self.spatial_cache:
            dist = ((cx - entry['cx'])**2 + (cy - entry['cy'])**2)**0.5
            if dist < self.spatial_match_threshold:
                # Found a recent recognition at similar position
                # Cache for this track too
                self.track_to_sid[track_id] = entry['sid']
                return ('SID', entry['sid'], 0.95)

        # 3. Throttling
        self.frame_counters.setdefault(track_id, 0)
        self.frame_counters[track_id] += 1

        if self.frame_counters[track_id] % self.recognition_interval != 0:
            return ('TRACK', track_id, 0.0)

        # 4. Perform Deep Analysis
        result = self.recognize_face(frame, bbox)

        if result['recognized']:
            # Cache the result for this session (by track ID)
            self.track_to_sid[track_id] = result['student_id']

            # Also add to spatial cache
            self.spatial_cache.append({
                'cx': cx,
                'cy': cy,
                'sid': result['student_id'],
                'name': result['student_name'],
                'time': current_time
            })

            print(
                f"🎯 Face Recognized: {result['student_name']} ({result['student_id']})")
            return ('SID', result['student_id'], result['confidence'])

        return ('TRACK', track_id, 0.0)

    def recognize_face(self, frame, bbox):
        """
        Extracts face from bbox and compares embeddings against the database.
        """
        if not self.student_database:
            return {'student_id': None, 'student_name': None, 'confidence': 0.0, 'recognized': False}

        try:
            x1, y1, x2, y2 = map(int, bbox)
            # Add larger padding for better recognition context (ArcFace loves context)
            h, w = frame.shape[:2]
            p = 40
            face_crop = frame[max(0, y1-p):min(h, y2+p),
                              max(0, x1-p):min(w, x2+p)]

            if face_crop.size == 0:
                return {'recognized': False}

            # Generate Embedding using ArcFace
            objs = DeepFace.represent(
                img_path=face_crop,
                model_name=self.model_name,
                enforce_detection=False,
                detector_backend=self.detector_backend,
                align=True
            )

            if not objs:
                return {'recognized': False}

            current_embedding = np.array(objs[0]['embedding'])

            # Compare against DB (Cosine Similarity)
            best_sid = None
            best_score = 0
            second_best_score = 0

            for sid, db_embedding in self.student_database.items():
                sim = np.dot(current_embedding, db_embedding) / (
                    np.linalg.norm(current_embedding) *
                    np.linalg.norm(db_embedding)
                )

                if sim > best_score:
                    second_best_score = best_score
                    best_score = sim
                    best_sid = sid
                elif sim > second_best_score:
                    second_best_score = sim

            # STABILITY FILTERS:
            # 1. Must be above the threshold (0.65)
            # 2. Margin check (0.01) to prevent identity swaps (more permissive)
            margin = best_score - second_best_score
            is_strong_match = best_score >= self.recognition_threshold and \
                (len(self.student_database) == 1 or margin > 0.01)

            if is_strong_match:
                return {
                    'student_id': best_sid,
                    'student_name': self.student_names.get(best_sid, "Unknown"),
                    'confidence': float(best_score),
                    'recognized': True
                }

        except Exception as e:
            # print(f"DEBUG: Recognition error: {e}")
            pass

        return {'student_id': None, 'student_name': None, 'confidence': 0.0, 'recognized': False}

    def register_student(self, student_id, student_name, image_data):
        """
        Processes image (base64 or path), extracts ArcFace embedding, and saves to DB.
        """
        try:
            # Decode Image
            if isinstance(image_data, str) and image_data.startswith('data:image'):
                header, encoded = image_data.split(',', 1)
                img_bytes = base64.b64decode(encoded)
                nparr = np.frombuffer(img_bytes, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            elif isinstance(image_data, str):
                img = cv2.imread(image_data)
            else:
                img = image_data

            if img is None:
                raise ValueError("Invalid image")

            # Get Embedding
            objs = DeepFace.represent(
                img_path=img,
                model_name=self.model_name,
                enforce_detection=True,
                detector_backend=self.detector_backend
            )

            if not objs:
                raise ValueError("No face detected in registration image")

            embedding = np.array(objs[0]['embedding'])

            # Save
            self.student_database[student_id] = embedding
            self.student_names[student_id] = student_name

            # Generate Thumbnail
            thumb = cv2.resize(img, (150, 150))
            _, buffer = cv2.imencode('.jpg', thumb)
            self.student_photos[student_id] = base64.b64encode(
                buffer).decode('utf-8')

            self._save_database()
            return True

        except Exception as e:
            print(f"❌ Registration Error: {e}")
            return False

    def _load_database(self):
        db_path = self.database_path / "faces.pkl"
        if db_path.exists():
            with open(db_path, 'rb') as f:
                data = pickle.load(f)
                self.student_database = data.get('embeddings', {})
                self.student_names = data.get('names', {})
                self.student_photos = data.get('photos', {})
            print(f"📦 Database Loaded: {len(self.student_database)} students")

    def _save_database(self):
        self.database_path.mkdir(parents=True, exist_ok=True)
        db_path = self.database_path / "faces.pkl"
        with open(db_path, 'wb') as f:
            pickle.dump({
                'embeddings': self.student_database,
                'names': self.student_names,
                'photos': self.student_photos
            }, f)
        print("💾 Database Saved")

    def delete_student(self, student_id):
        if student_id in self.student_database:
            del self.student_database[student_id]
            self.student_names.pop(student_id, None)
            self.student_photos.pop(student_id, None)
            self._save_database()

            # Clear session caches that may reference this student
            # Remove from track_to_sid
            tracks_to_remove = [
                tid for tid, sid in self.track_to_sid.items() if sid == student_id]
            for tid in tracks_to_remove:
                del self.track_to_sid[tid]

            # Remove from spatial cache
            self.spatial_cache = [
                e for e in self.spatial_cache if e.get('sid') != student_id]

            print(f"🗑️ Student {student_id} deleted and caches cleared")
            return True
        return False

    def clear_session_cache(self):
        self.track_to_sid.clear()
        self.frame_counters.clear()

    def get_all_students(self):
        return [
            {'student_id': sid,
                'student_name': self.student_names[sid], 'photo': self.student_photos[sid]}
            for sid in self.student_database
        ]
