import numpy as np
import cv2
from collections import defaultdict, deque


class ObjectTracker:
    def __init__(self, max_disappeared=90, max_distance=100):
        """
        Initialize the multi-object tracker with reappearance handling.

        Args:
            max_disappeared: Frames before deregistering object (90 = ~3 sec at 30fps)
            max_distance: Max distance for centroid association (increased for stability)
        """
        self.next_object_id = 0
        self.objects = {}
        self.disappeared = {}
        self.bboxes = {}
        self.tracks = defaultdict(lambda: deque(maxlen=60))  # Longer history
        self.reappearance_buffer = {}  # Store recently disappeared objects

        self.max_disappeared = max_disappeared
        self.max_distance = max_distance
        self.reappearance_threshold = max_disappeared  # Full window for reappearance

    def register(self, centroid, bbox):
        """Register a new object with the next available ID."""
        self.objects[self.next_object_id] = centroid
        self.bboxes[self.next_object_id] = bbox
        self.disappeared[self.next_object_id] = 0
        self.tracks[self.next_object_id].append(centroid)
        self.next_object_id += 1

    def deregister(self, object_id):
        """Deregister an object and move to reappearance buffer."""
        if object_id in self.objects:
            # Store in buffer for potential reappearance
            self.reappearance_buffer[object_id] = {
                'centroid': self.objects[object_id],
                'bbox': self.bboxes[object_id],
                'frames_since_disappeared': 0
            }
            del self.objects[object_id]
            del self.disappeared[object_id]
            del self.bboxes[object_id]

    def check_reappearance(self, centroid, bbox):
        """Check if centroid matches a recently disappeared object."""
        best_match_id = None
        min_distance = float('inf')

        for obj_id, buffer_data in list(self.reappearance_buffer.items()):
            buffer_data['frames_since_disappeared'] += 1

            # Remove if too old
            if buffer_data['frames_since_disappeared'] > self.reappearance_threshold:
                del self.reappearance_buffer[obj_id]
                continue

            # Check distance
            dist = np.sqrt((centroid[0] - buffer_data['centroid'][0])**2 +
                           (centroid[1] - buffer_data['centroid'][1])**2)

            if dist < min_distance and dist < self.max_distance * 1.5:
                min_distance = dist
                best_match_id = obj_id

        return best_match_id

    def update(self, detections):
        """Update tracker with new detections."""
        person_detections = [d for d in detections if d['class_id'] == 0]

        if len(person_detections) == 0:
            for object_id in list(self.disappeared.keys()):
                self.disappeared[object_id] += 1
                if self.disappeared[object_id] > self.max_disappeared:
                    self.deregister(object_id)
            return detections

        input_centroids = np.zeros((len(person_detections), 2), dtype="int")

        for (i, detection) in enumerate(person_detections):
            x1, y1, x2, y2 = detection['bbox']
            cx = int((x1 + x2) / 2.0)
            cy = int(y1 + (y2 - y1) / 3)
            input_centroids[i] = (cx, cy)
            detection['centroid'] = (cx, cy)

        if len(self.objects) == 0:
            for i in range(len(input_centroids)):
                # Check for reappearance first
                reappeared_id = self.check_reappearance(
                    input_centroids[i], person_detections[i]['bbox'])
                if reappeared_id is not None:
                    self.objects[reappeared_id] = input_centroids[i]
                    self.bboxes[reappeared_id] = person_detections[i]['bbox']
                    self.disappeared[reappeared_id] = 0
                    self.tracks[reappeared_id].append(input_centroids[i])
                    del self.reappearance_buffer[reappeared_id]
                else:
                    self.register(
                        input_centroids[i], person_detections[i]['bbox'])
        else:
            object_ids = list(self.objects.keys())
            object_centroids = list(self.objects.values())

            D = np.linalg.norm(np.array(object_centroids)[
                               :, np.newaxis] - input_centroids, axis=2)

            rows = D.min(axis=1).argsort()
            cols = D.argmin(axis=1)[rows]

            used_row_idxs = set()
            used_col_idxs = set()

            for (row, col) in zip(rows, cols):
                if row in used_row_idxs or col in used_col_idxs:
                    continue

                # Adaptive threshold: use larger of fixed max_distance or 50% of bbox size
                # This handles both close and far subjects
                bbox = person_detections[col]['bbox']
                bbox_diagonal = np.sqrt(
                    (bbox[2]-bbox[0])**2 + (bbox[3]-bbox[1])**2)
                adaptive_threshold = max(
                    self.max_distance, bbox_diagonal * 0.5)

                if D[row, col] > adaptive_threshold:
                    continue

                object_id = object_ids[row]
                self.objects[object_id] = input_centroids[col]
                self.bboxes[object_id] = person_detections[col]['bbox']
                self.tracks[object_id].append(input_centroids[col])
                self.disappeared[object_id] = 0

                used_row_idxs.add(row)
                used_col_idxs.add(col)

            unused_row_idxs = set(
                range(0, D.shape[0])).difference(used_row_idxs)
            unused_col_idxs = set(
                range(0, D.shape[1])).difference(used_col_idxs)

            if D.shape[0] >= D.shape[1]:
                for row in unused_row_idxs:
                    object_id = object_ids[row]
                    self.disappeared[object_id] += 1

                    if self.disappeared[object_id] > self.max_disappeared:
                        self.deregister(object_id)
            else:
                for col in unused_col_idxs:
                    reappeared_id = self.check_reappearance(
                        input_centroids[col], person_detections[col]['bbox'])
                    if reappeared_id is not None:
                        self.objects[reappeared_id] = input_centroids[col]
                        self.bboxes[reappeared_id] = person_detections[col]['bbox']
                        self.disappeared[reappeared_id] = 0
                        self.tracks[reappeared_id].append(input_centroids[col])
                        del self.reappearance_buffer[reappeared_id]
                    else:
                        self.register(
                            input_centroids[col], person_detections[col]['bbox'])

        updated_detections = []
        for detection in detections:
            if detection['class_id'] != 0:
                updated_detections.append(detection)
                continue

            cx, cy = detection['centroid']
            min_dist = float('inf')
            best_id = None

            for object_id, centroid in self.objects.items():
                dist = np.sqrt((cx - centroid[0])**2 + (cy - centroid[1])**2)
                if dist < min_dist:
                    min_dist = dist
                    best_id = object_id

            if best_id is not None and min_dist < self.max_distance:
                detection['track_id'] = best_id
            else:
                detection['track_id'] = self.next_object_id
                self.next_object_id += 1

            updated_detections.append(detection)

        return updated_detections

    def get_seat_assignments(self, seat_positions):
        """Seat mapping functionality has been removed."""
        return None
