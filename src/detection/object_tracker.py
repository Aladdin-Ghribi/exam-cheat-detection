import numpy as np
import cv2
from collections import defaultdict, deque

class ObjectTracker:
    def __init__(self, max_disappeared=30, max_distance=50):
        """
        Initialize the multi-object tracker.

        Args:
            max_disappeared: Maximum number of consecutive frames a tracked
                           object can be marked as "disappeared" before we
                           deregister the object from tracking
            max_distance: Maximum distance between centroids for association
        """
        self.next_object_id = 0
        self.objects = {}  # Stores object_id -> centroid
        self.disappeared = {}  # Stores object_id -> count of consecutive frames disappeared
        self.bboxes = {}  # Stores object_id -> bounding box
        self.tracks = defaultdict(lambda: deque(maxlen=30))  # Stores object_id -> history of positions

        self.max_disappeared = max_disappeared
        self.max_distance = max_distance

    def register(self, centroid, bbox):
        """Register a new object with the next available ID."""
        self.objects[self.next_object_id] = centroid
        self.bboxes[self.next_object_id] = bbox
        self.disappeared[self.next_object_id] = 0
        self.tracks[self.next_object_id].append(centroid)
        self.next_object_id += 1

    def deregister(self, object_id):
        """Deregister an object with the given ID."""
        del self.objects[object_id]
        del self.disappeared[object_id]
        del self.bboxes[object_id]
        # Note: We keep the tracks history for potential analysis

    def update(self, detections):
        """
        Update the tracker with new detections.

        Args:
            detections: List of dictionaries, each containing:
                       - 'bbox': [x1, y1, x2, y2]
                       - 'class_id': int
                       - 'confidence': float

        Returns:
            Updated list of detections with added 'track_id' for each person
        """
        # Filter only person detections for tracking
        person_detections = [d for d in detections if d['class_id'] == 0]  # Assuming class_id 0 is 'person'

        if len(person_detections) == 0:
            # Mark all existing objects as disappeared
            for object_id in list(self.disappeared.keys()):
                self.disappeared[object_id] += 1

                # If an object has been disappeared for too long, deregister it
                if self.disappeared[object_id] > self.max_disappeared:
                    self.deregister(object_id)

            # Return original detections with no track IDs
            return detections

        # Initialize an array of input centroids for the current frame
        input_centroids = np.zeros((len(person_detections), 2), dtype="int")

        # Calculate centroids from bounding boxes (using lower chest position)
        for (i, detection) in enumerate(person_detections):
            x1, y1, x2, y2 = detection['bbox']
            cx = int((x1 + x2) / 2.0)
            # Use lower chest position (approximately 1/3 down from the top of the bounding box)
            cy = int(y1 + (y2 - y1) / 3)
            input_centroids[i] = (cx, cy)
            detection['centroid'] = (cx, cy)

        # If we are currently not tracking any objects, register all
        if len(self.objects) == 0:
            for i in range(len(input_centroids)):
                self.register(input_centroids[i], person_detections[i]['bbox'])
        else:
            # Get the set of object IDs and corresponding centroids
            object_ids = list(self.objects.keys())
            object_centroids = list(self.objects.values())

            # Compute the distance between each pair of object centroids and input centroids
            D = np.linalg.norm(np.array(object_centroids)[:, np.newaxis] - input_centroids, axis=2)

            # Find the smallest value in each row and sort the row indexes based on minimum values
            rows = D.min(axis=1).argsort()

            # Find the smallest value in each column and sort based on the previously computed row index
            cols = D.argmin(axis=1)[rows]

            # Keep track of which row and column indexes we have already examined
            used_row_idxs = set()
            used_col_idxs = set()

            # Loop over the combination of (row, column) index tuples
            for (row, col) in zip(rows, cols):
                # If we have already examined either the row or column, ignore it
                if row in used_row_idxs or col in used_col_idxs:
                    continue

                # If the distance between centroids is greater than the maximum distance,
                # do not associate the two centroids
                if D[row, col] > self.max_distance:
                    continue

                # Grab the object ID for the current row and set its new centroid
                object_id = object_ids[row]
                self.objects[object_id] = input_centroids[col]
                self.bboxes[object_id] = person_detections[col]['bbox']
                self.tracks[object_id].append(input_centroids[col])
                self.disappeared[object_id] = 0

                # Indicate that we have examined each of the row and column indexes
                used_row_idxs.add(row)
                used_col_idxs.add(col)

            # Compute both the row and column index we have NOT yet examined
            unused_row_idxs = set(range(0, D.shape[0])).difference(used_row_idxs)
            unused_col_idxs = set(range(0, D.shape[1])).difference(used_col_idxs)

            # If the number of object centroids is equal to or greater than the number of input centroids
            # we need to check and see if some of these objects have potentially disappeared
            if D.shape[0] >= D.shape[1]:
                # Loop over the unused row indexes
                for row in unused_row_idxs:
                    object_id = object_ids[row]
                    self.disappeared[object_id] += 1

                    # If the object has been marked as disappeared for a maximum number of consecutive frames,
                    # deregister it
                    if self.disappeared[object_id] > self.max_disappeared:
                        self.deregister(object_id)

            # Otherwise, register each new input centroid as a trackable object
            else:
                for col in unused_col_idxs:
                    self.register(input_centroids[col], person_detections[col]['bbox'])

        # Update the original detections with track IDs
        updated_detections = []
        for detection in detections:
            if detection['class_id'] != 0:  # Not a person, no tracking
                updated_detections.append(detection)
                continue

            # Find the closest track for this person
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
                # This shouldn't happen if our tracking is working correctly
                # But as a fallback, assign a new ID
                detection['track_id'] = self.next_object_id
                self.next_object_id += 1

            updated_detections.append(detection)

        return updated_detections

    def get_seat_assignments(self, seat_positions):
        """
        Seat mapping functionality has been removed.

        Returns:
            None
        """
        return None
