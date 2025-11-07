import os
import sys
import unittest
import numpy as np
import cv2

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

from src.detection.pose_detector import PoseDetector
from src.detection.yolo_detector import YOLODetector


class PoseMetricsTest(unittest.TestCase):
    def setUp(self):
        self.detector = PoseDetector(static_image_mode=True)

    def tearDown(self):
        self.detector.pose.close()

    def test_head_pose_estimation_zero_rotation(self):
        height = 480
        width = 640
        camera_matrix = np.array([
            [float(width), 0.0, width / 2.0],
            [0.0, float(width), height / 2.0],
            [0.0, 0.0, 1.0]
        ], dtype=np.float32)
        dist_coeffs = np.zeros((4, 1), dtype=np.float32)
        rotation_vector = np.zeros((3, 1), dtype=np.float32)
        translation_vector = np.array([[0.0], [0.0], [1000.0]], dtype=np.float32)
        model_points = self.detector.head_pose_model_points
        image_points, _ = cv2.projectPoints(
            model_points,
            rotation_vector,
            translation_vector,
            camera_matrix,
            dist_coeffs
        )
        landmarks = [{'x': 0.0, 'y': 0.0, 'z': 0.0, 'visibility': 0.0} for _ in range(33)]
        for idx, point in zip(self.detector.head_pose_landmarks, image_points):
            landmarks[idx] = {
                'x': float(point[0][0] / width),
                'y': float(point[0][1] / height),
                'z': 0.0,
                'visibility': 1.0
            }
        orientation = self.detector._estimate_head_orientation(landmarks, (height, width, 3))
        self.assertIsNotNone(orientation)
        self.assertAlmostEqual(orientation['yaw'], 0.0, delta=1.0)
        self.assertAlmostEqual(orientation['pitch'], 0.0, delta=1.0)
        self.assertAlmostEqual(orientation['roll'], 0.0, delta=1.0)

    def test_hand_metrics_near_face(self):
        landmarks = [{'x': 0.0, 'y': 0.0, 'z': 0.0, 'visibility': 0.0} for _ in range(33)]
        face_positions = {
            0: (0.5, 0.4),
            1: (0.48, 0.38),
            2: (0.47, 0.38),
            3: (0.45, 0.38),
            4: (0.53, 0.38),
            5: (0.54, 0.38),
            6: (0.56, 0.38),
            7: (0.42, 0.4),
            8: (0.58, 0.4),
            9: (0.46, 0.45),
            10: (0.54, 0.45)
        }
        for idx, pos in face_positions.items():
            landmarks[idx] = {
                'x': pos[0],
                'y': pos[1],
                'z': 0.0,
                'visibility': 1.0
            }
        left_positions = {
            15: (0.5, 0.43),
            17: (0.49, 0.42),
            19: (0.5, 0.41),
            21: (0.49, 0.4)
        }
        for idx, pos in left_positions.items():
            landmarks[idx] = {
                'x': pos[0],
                'y': pos[1],
                'z': 0.0,
                'visibility': 1.0
            }
        right_positions = {
            16: (0.8, 0.8),
            18: (0.82, 0.82),
            20: (0.79, 0.79),
            22: (0.78, 0.78)
        }
        for idx, pos in right_positions.items():
            landmarks[idx] = {
                'x': pos[0],
                'y': pos[1],
                'z': 0.0,
                'visibility': 1.0
            }
        hand_metrics, face_region = self.detector._compute_hand_metrics(landmarks)
        self.assertIsNotNone(hand_metrics)
        self.assertIsNotNone(face_region)
        self.assertTrue(hand_metrics['left']['near_face'])
        self.assertFalse(hand_metrics['right']['near_face'])
        self.assertLess(hand_metrics['left']['distance_to_face'], hand_metrics['right']['distance_to_face'])

    def test_hand_near_object_detection(self):
        detector = YOLODetector.__new__(YOLODetector)
        class DummyModel:
            names = {0: 'person', 67: 'cell_phone'}
        detector.model = DummyModel()
        detection = {
            'class_id': 0,
            'bbox': [100.0, 120.0, 220.0, 340.0]
        }
        pose = {
            'hand_metrics': {
                'left': {
                    'distance_to_face': 0.05,
                    'near_face': True,
                    'position': (0.9, 0.6),
                    'visible': True
                }
            }
        }
        object_detections = [
            {
                'class_id': 67,
                'bbox': [180.0, 200.0, 260.0, 300.0]
            }
        ]
        entry = detector._build_behavior_hand_entry(detection, pose, object_detections, 'left')
        self.assertTrue(entry['near_object'])
        self.assertEqual(entry['object_class'], 'cell_phone')
        self.assertIsNotNone(entry['distance_to_object'])
        self.assertTrue(entry['visible'])


if __name__ == '__main__':
    unittest.main()
