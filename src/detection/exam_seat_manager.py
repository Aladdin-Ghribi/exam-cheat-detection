import numpy as np
import cv2
from collections import defaultdict, deque
import json
import os

class ExamSeatManager:
    def __init__(self, room_width=1280, room_height=720, zone_size=(120, 150)):
        """
        Initialize exam seat manager with zone-based seating.

        Args:
            room_width: Width of exam room in pixels
            room_height: Height of exam room in pixels
            zone_size: (width, height) of each seating zone in pixels
        """
        self.room_width = room_width
        self.room_height = room_height
        self.zone_width = zone_size[0]
        self.zone_height = zone_size[1]

        # Dictionary to store person data
        self.person_zones = {}  # track_id -> zone data
        self.position_history = defaultdict(lambda: deque(maxlen=20))  # track_id -> positions history
        self.position_stability = {}  # track_id -> stability score
        self.empty_zones = {}  # zone_id -> last occupied time
        self.zone_assignments = {}  # track_id -> zone_id

        # Zone management
        self.next_zone_id = 0
        self.zones = {}  # zone_id -> zone data

    def update(self, detections):
        """
        Update seat assignments based on current detections.

        Args:
            detections: List of person detections with track IDs

        Returns:
            Dictionary with updated assignments and zones
        """
        # Update position history for each tracked person
        for detection in detections:
            if 'track_id' not in detection:
                continue

            track_id = detection['track_id']
            bbox = detection['bbox']

            # Ensure bbox is in correct format
            if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
                continue

            x1, y1, x2, y2 = bbox

            # Ensure coordinates are integers
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

            # Calculate lower chest position (more stable than center)
            cx = int((x1 + x2) / 2.0)
            cy = int(y1 + (y2 - y1) / 3)

            # Add to position history
            self.position_history[track_id].append((cx, cy))

            # Calculate stable position (weighted average of recent positions)
            if len(self.position_history[track_id]) >= 5:
                recent_positions = list(self.position_history[track_id])[-10:]  # Use more positions

                # Calculate position stability (lower variance = more stable)
                positions_array = np.array(recent_positions)
                variance = np.var(positions_array, axis=0)
                stability_score = 1.0 / (1.0 + np.mean(variance))  # Higher score = more stable
                self.position_stability[track_id] = stability_score

                # Weight recent positions more heavily
                weights = np.exp(np.linspace(-1, 0, len(recent_positions)))  # Exponential weights
                weights /= weights.sum()  # Normalize

                # Calculate weighted average
                weighted_positions = positions_array * weights[:, np.newaxis]
                stable_position = np.sum(weighted_positions, axis=0).astype(int)
                detection['stable_position'] = tuple(stable_position)

        # Update zone assignments
        self._update_zone_assignments(detections)

        return {
            'zone_assignments': self.zone_assignments,
            'zones': self.zones
        }

    def _update_zone_assignments(self, detections):
        """
        Update zone assignments based on current detections.

        Args:
            detections: List of person detections
        """
        # Reset current assignments
        current_assignments = {}

        # First, try to assign people to their existing zones
        for detection in detections:
            if 'track_id' not in detection or 'stable_position' not in detection:
                continue

            track_id = detection['track_id']
            stable_pos = detection['stable_position']

            # Check if this person already has a zone
            if track_id in self.zone_assignments:
                zone_id = self.zone_assignments[track_id]
                zone = self.zones.get(zone_id)

                # Check if person is still in their zone
                if zone and self._is_in_zone(stable_pos, zone):
                    current_assignments[track_id] = zone_id
                    zone['occupied'] = True
                    zone['last_seen'] = 0
                    zone['stability'] = self.position_stability.get(track_id, 0.5)
                    continue
                else:
                    # Check if person is near their zone (allowing for more movement)
                    # Use a dynamic threshold based on stability (more stable = smaller threshold)
                    stability = self.position_stability.get(track_id, 0.5)
                    threshold = 350 - stability * 100  # Range: 250-350 pixels

                    if zone and self._is_near_zone(stable_pos, zone, threshold=threshold):
                        current_assignments[track_id] = zone_id
                        zone['occupied'] = True
                        zone['last_seen'] = 0
                        zone['stability'] = stability

                        # Update zone center slightly based on new position (adaptive zone)
                        # This helps zone "follow" person slightly
                        current_center = zone['center']
                        weight = 0.1  # How much to move the zone center (10% towards new position)
                        new_center_x = int(current_center[0] * (1 - weight) + stable_pos[0] * weight)
                        new_center_y = int(current_center[1] * (1 - weight) + stable_pos[1] * weight)
                        zone['center'] = (new_center_x, new_center_y)

                        # Update zone boundaries
                        width = zone.get('width', self.zone_width)
                        height = zone.get('height', self.zone_height)
                        zone['top_left'] = (new_center_x - width // 2, new_center_y - height // 2)
                        zone['bottom_right'] = (new_center_x + width // 2, new_center_y + height // 2)

                        continue
            else:
                # Person moved out of their zone, try to find the nearest zone
                best_zone_id = None
                min_distance = float('inf')

                for z_id, z in self.zones.items():
                    if not z.get('occupied', False):
                        distance = np.linalg.norm(np.array(stable_pos) - np.array(z['center']))
                        if distance < min_distance and distance < 300:  # Even larger threshold for movement
                            min_distance = distance
                            best_zone_id = z_id

                if best_zone_id is not None:
                    current_assignments[track_id] = best_zone_id
                    self.zones[best_zone_id]['occupied'] = True
                    self.zones[best_zone_id]['last_seen'] = 0
                    self.zones[best_zone_id]['track_id'] = track_id
                else:
                    # Create a new zone for this person
                    new_zone_id = self._create_zone(stable_pos, track_id)
                    if new_zone_id is not None:  # Only assign if zone was created
                        current_assignments[track_id] = new_zone_id
                continue

            # If not, try to find an empty zone nearby
            best_zone_id = None
            min_distance = float('inf')

            for zone_id, zone in self.zones.items():
                if not zone.get('occupied', False):
                    distance = np.linalg.norm(np.array(stable_pos) - np.array(zone['center']))
                    if distance < min_distance and distance < 250:  # Increased threshold for better assignment
                        min_distance = distance
                        best_zone_id = zone_id

            # If found a suitable empty zone, assign it
            if best_zone_id is not None:
                current_assignments[track_id] = best_zone_id
                self.zones[best_zone_id]['occupied'] = True
                self.zones[best_zone_id]['last_seen'] = 0
                self.zones[best_zone_id]['track_id'] = track_id
            else:
                # Create a new zone for this person
                new_zone_id = self._create_zone(stable_pos, track_id)
                if new_zone_id is not None:  # Only assign if zone was created
                    current_assignments[track_id] = new_zone_id

        # Update zone assignments
        self.zone_assignments = current_assignments

        # Mark zones as empty if no one was assigned for a few frames
        for zone_id, zone in self.zones.items():
            if zone.get('occupied', False) and zone_id not in current_assignments.values():
                zone['last_seen'] = zone.get('last_seen', 0) + 1
                if zone['last_seen'] > 60:  # Further increased to 60 frames for more stability
                    zone['occupied'] = False
                    zone['track_id'] = None

        # Clean up zones that have been empty for too long
        zones_to_remove = []
        for zone_id, zone in self.zones.items():
            if not zone.get('occupied', False) and zone['last_seen'] > 120:  # Remove zones empty for 2 seconds
                zones_to_remove.append(zone_id)

        for zone_id in zones_to_remove:
            del self.zones[zone_id]

    def _is_in_zone(self, position, zone):
        """
        Check if a position is within a zone.

        Args:
            position: (x, y) tuple
            zone: Zone dictionary

        Returns:
            True if position is in zone, False otherwise
        """
        x, y = position
        cx, cy = zone['center']

        # Use adjusted dimensions if available, otherwise use defaults
        if 'width' in zone and 'height' in zone:
            half_width = zone['width'] // 2
            half_height = zone['height'] // 2
        else:
            half_width = self.zone_width // 2
            half_height = self.zone_height // 2

        return (cx - half_width <= x <= cx + half_width and
                cy - half_height <= y <= cy + half_height)

    def _create_zone(self, position, track_id):
        """
        Create a new zone at the specified position.

        Args:
            position: (x, y) tuple for zone center
            track_id: ID of the person this zone is for

        Returns:
            ID of the created zone
        """
        # Always create a zone for new people - the main goal is every person has a zone
        # We can have more zones than people temporarily
        zone_id = self.next_zone_id
        self.next_zone_id += 1

        # Get stability score if available
        stability = self.position_stability.get(track_id, 0.5)

        # Adjust zone size based on stability (more stable = smaller zone)
        width_factor = 1.2 - stability * 0.4  # Range: 0.8 to 1.2
        height_factor = 1.2 - stability * 0.4  # Range: 0.8 to 1.2

        adjusted_width = int(self.zone_width * width_factor)
        adjusted_height = int(self.zone_height * height_factor)

        self.zones[zone_id] = {
            'center': position,
            'occupied': True,
            'last_seen': 0,
            'track_id': track_id,
            'stability': stability,
            'top_left': (position[0] - adjusted_width // 2, position[1] - adjusted_height // 2),
            'bottom_right': (position[0] + adjusted_width // 2, position[1] + adjusted_height // 2),
            'width': adjusted_width,
            'height': adjusted_height
        }

        return zone_id

    def _is_near_zone(self, position, zone, threshold=250):
        """
        Check if a position is near a zone within a threshold distance.

        Args:
            position: (x, y) tuple
            zone: Zone dictionary
            threshold: Maximum distance to be considered "near"

        Returns:
            True if position is near the zone, False otherwise
        """
        x, y = position
        cx, cy = zone['center']

        # Calculate Euclidean distance
        distance = np.sqrt((x - cx)**2 + (y - cy)**2)

        return distance <= threshold

    def draw_zones(self, frame, zone_assignments):
        """
        Draw zones on the frame.

        Args:
            frame: Image to draw on
            zone_assignments: Dictionary of track_id -> zone_id assignments

        Returns:
            Frame with zones drawn
        """
        result_frame = frame.copy()

        for zone_id, zone in self.zones.items():
            # Skip empty zones
            if not zone.get('occupied', False):
                continue

            center = zone['center']
            top_left = zone['top_left']
            bottom_right = zone['bottom_right']

            # Red for occupied
            color = (0, 0, 255)

            # Find the track ID for this zone
            track_id = None
            for t_id, z_id in zone_assignments.items():
                if z_id == zone_id:
                    track_id = t_id
                    break

            stability = zone.get('stability', 0.5)
            label = f"ID: {track_id} (S:{stability:.2f})" if track_id else "Occupied"

            # Draw zone
            cv2.rectangle(result_frame, top_left, bottom_right, color, 2)

            # Draw center point with size based on stability
            radius = int(5 + stability * 10)  # Radius between 5-15 based on stability
            cv2.circle(result_frame, center, radius, color, -1)

            cv2.putText(result_frame, label, (center[0] - 40, center[1] - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 2)

        return result_frame

    def save_config(self, config_path):
        """Save seat configuration to a JSON file."""
        # Convert zones to a serializable format
        zones_data = []
        for zone_id, zone in self.zones.items():
            zones_data.append({
                'id': int(zone_id),
                'center': [int(coord) for coord in zone['center']],
                'occupied': bool(zone['occupied']),
                'stability': zone.get('stability', 0.5),
                'width': zone.get('width', self.zone_width),
                'height': zone.get('height', self.zone_height)
            })

        config = {
            'room_width': self.room_width,
            'room_height': self.room_height,
            'zone_width': self.zone_width,
            'zone_height': self.zone_height,
            'zones': zones_data
        }

        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

    def load_config(self, config_path):
        """Load seat configuration from a JSON file."""
        if not os.path.exists(config_path):
            return False

        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except json.JSONDecodeError:
            return False

        self.room_width = config.get('room_width', 1280)
        self.room_height = config.get('room_height', 720)
        self.zone_width = config.get('zone_width', 80)
        self.zone_height = config.get('zone_height', 100)

        # Load zones
        self.zones = {}
        for zone_data in config.get('zones', []):
            zone_id = int(zone_data['id'])
            center = tuple(int(coord) for coord in zone_data['center'])

            self.zones[zone_id] = {
                'center': center,
                'occupied': bool(zone_data.get('occupied', False)),
                'last_seen': 0,
                'track_id': None,
                'stability': zone_data.get('stability', 0.5),
                'width': zone_data.get('width', self.zone_width),
                'height': zone_data.get('height', self.zone_height),
                'top_left': (center[0] - zone_data.get('width', self.zone_width) // 2, center[1] - zone_data.get('height', self.zone_height) // 2),
                'bottom_right': (center[0] + zone_data.get('width', self.zone_width) // 2, center[1] + zone_data.get('height', self.zone_height) // 2)
            }

        # Update next zone        if self.zones:
            self.next_zone_id = max(self.zones.keys()) + 1

        return True
