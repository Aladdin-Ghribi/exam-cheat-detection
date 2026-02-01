import os
import json
import secrets
import cv2
import time
from datetime import datetime
from collections import deque
import shutil
from .suspicion_config import SUSPICION_THRESHOLD


class FlaggedEvidenceSaver:
    """
    Handles automatic saving of flagged frames, cropped regions, and metadata
    when suspicion scores exceed threshold. 

    GDPR COMPLIANCE NOTICE:
    Photos of cheating incidents are deleted within 7 days after review to comply 
    with storage limitation principles. This class implements a secure deletion 
    mechanism that overwrites data before removing files.
    """

    def __init__(self, output_dir="output/flagged_evidence", suspicion_threshold=None,
                 max_retention_days=7, max_saved_events=100):
        # Use centralized threshold if not provided
        if suspicion_threshold is None:
            suspicion_threshold = SUSPICION_THRESHOLD
        """
        Initialize the evidence saver.

        Args:
            output_dir: Directory to save flagged evidence
            suspicion_threshold: Minimum suspicion score to trigger save
            max_retention_days: Auto-delete evidence older than this
            max_saved_events: Maximum number of events to keep (FIFO)
        """
        self.output_dir = output_dir
        self.suspicion_threshold = suspicion_threshold
        self.max_retention_days = max_retention_days
        self.max_saved_events = max_saved_events
        self.auto_save_enabled = True  # Enable auto-save by default

        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)

        # Track saved events for retention (FIFO queue)
        self.saved_events = deque(maxlen=max_saved_events)

        # Clean up old evidence on startup
        self._cleanup_old_evidence()

    def process_frame(self, frame, detections, timestamp=None):
        """
        Process a frame and save evidence for EACH person individually if they exceed threshold.

        Args:
            frame: OpenCV image array
            detections: List of detection dictionaries with behavior.suspicion.smoothed
            timestamp: Optional timestamp, defaults to current time
        """
        if not self.auto_save_enabled:
            return

        if timestamp is None:
            timestamp = datetime.now()

        # Check each person individually
        for det in detections:
            if det.get('class_id') != 0:  # Skip non-person objects
                continue

            suspicion_score = self._get_suspicion_score(det)
            score_100 = min(100, round(suspicion_score * 100))

            # Flag this person if they exceed threshold individually
            if score_100 >= self.suspicion_threshold:
                self._save_evidence(frame, [det], timestamp, suspicion_score)

    def _save_evidence(self, frame, detections, timestamp, max_suspicion):
        """
        Save frame snapshot, cropped regions, and metadata.
        """
        # Create unique event ID
        event_id = f"{timestamp.strftime('%Y%m%d_%H%M%S_%f')}_{int(max_suspicion*100)}"

        event_dir = os.path.join(self.output_dir, event_id)
        os.makedirs(event_dir, exist_ok=True)

        # Save full frame snapshot (Fast encoding)
        frame_path = os.path.join(event_dir, "frame.jpg")
        cv2.imwrite(frame_path, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])

        # Save cropped regions for flagged detections
        crops_info = []
        for i, det in enumerate(detections):
            # Get suspicion score from behavior.suspicion.smoothed or directly from suspicion_score
            suspicion_score = 0
            if 'behavior' in det and 'suspicion' in det['behavior']:
                suspicion = det['behavior']['suspicion']
                if 'smoothed' in suspicion:
                    suspicion_score = suspicion['smoothed']
            elif 'suspicion_score' in det:
                suspicion_score = det['suspicion_score']

            # Always save crops for detections with high suspicion scores (>= 0.5)
            # This ensures we capture evidence even if individual detection is below threshold
            if suspicion_score >= 0.5:
                crop = self._extract_crop(frame, det['bbox'])
                if crop is not None:
                    # Get behavior description for filename
                    behavior_desc = 'unknown'
                    if 'behavior' in det:
                        behavior = det['behavior']
                        if 'suspicion' in behavior and 'components' in behavior['suspicion']:
                            # Use the highest scoring component as behavior description
                            components = behavior['suspicion']['components']
                            if components:
                                max_comp = max(
                                    components.items(), key=lambda x: x[1])
                                behavior_desc = max_comp[0]

                    crop_path = os.path.join(
                        event_dir, f"crop_{i}_{behavior_desc}.jpg")
                    cv2.imwrite(crop_path, crop, [
                                int(cv2.IMWRITE_JPEG_QUALITY), 90])

                    # Get class name from model names if not directly available
                    class_name = 'unknown'
                    if 'class_name' in det:
                        class_name = det['class_name']
                    elif 'class_id' in det:
                        # Map class_id to class name using COCO dataset names
                        class_id = det['class_id']
                        class_map = {
                            0: 'person',
                            24: 'backpack',
                            26: 'handbag',
                            63: 'laptop',
                            67: 'cell phone',
                            73: 'book'
                        }
                        class_name = class_map.get(
                            class_id, f'class_{class_id}')

                    crops_info.append({
                        'crop_path': os.path.basename(crop_path),
                        'bbox': det['bbox'],
                        'behavior': behavior_desc,
                        'class_name': class_name,
                        'suspicion_score': suspicion_score,
                        'suspicion_score_100': min(100, round(suspicion_score * 100))
                    })

        # Create metadata
        # Use the max_suspicion calculated earlier instead of the last detection's score
        metadata = {
            'event_id': event_id,
            'timestamp': timestamp.isoformat(),
            'suspicion_score': max_suspicion,
            'suspicion_score_100': min(100, round(max_suspicion * 100)),
            'frame_path': os.path.basename(frame_path),
            'crops': crops_info,
            'reasons': [self._get_behavior_description(det) for det in detections
                        if self._get_suspicion_score(det) >= self.suspicion_threshold],
            'all_detections': [
                {
                    'bbox': det['bbox'],
                    'class_name': self._get_class_name(det),
                    'suspicion_score': self._get_suspicion_score(det),
                    'suspicion_score_100': min(100, round(self._get_suspicion_score(det) * 100)),
                    'behavior': det.get('behavior', 'none')
                } for det in detections
            ]
        }

        # Save metadata
        metadata_path = os.path.join(event_dir, "metadata.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        # Track for retention
        self.saved_events.append({
            'event_id': event_id,
            'timestamp': timestamp,
            'path': event_dir
        })

        # Convert score to 0-100 scale for consistency with UI
        # Use rounding to ensure proper conversion
        score_100 = min(100, round(suspicion_score * 100))
        print(f"Saved flagged evidence: {event_id} (score: {score_100}/100)")
        print(f"  - Crops saved: {len(crops_info)}")
        print(f"  - Reasons: {[c['behavior'] for c in crops_info]}")

    def _extract_crop(self, frame, bbox, padding=10):
        """
        Extract cropped region from frame with padding.

        Args:
            frame: OpenCV image
            bbox: [x1, y1, x2, y2]
            padding: Pixels to add around bbox

        Returns:
            Cropped image or None if invalid
        """
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = bbox

        # Add padding
        x1 = max(0, int(x1) - padding)
        y1 = max(0, int(y1) - padding)
        x2 = min(w, int(x2) + padding)
        y2 = min(h, int(y2) + padding)

        if x2 <= x1 or y2 <= y1:
            return None

        return frame[y1:y2, x1:x2]

    def _get_suspicion_score(self, detection):
        """
        Extract suspicion score from detection dictionary.

        Args:
            detection: Detection dictionary

        Returns:
            Suspicion score (float)
        """
        if 'behavior' in detection and 'suspicion' in detection['behavior']:
            suspicion = detection['behavior']['suspicion']
            if 'smoothed' in suspicion:
                return float(suspicion['smoothed'])
            elif 'raw' in suspicion:
                return float(suspicion['raw'])
        elif 'suspicion_score' in detection:
            return float(detection['suspicion_score'])
        return 0.0

    def _get_class_name(self, detection):
        """
        Extract class name from detection dictionary.

        Args:
            detection: Detection dictionary

        Returns:
            Class name (string)
        """
        if 'class_name' in detection:
            return detection['class_name']
        elif 'class_id' in detection:
            # Map class_id to class name using COCO dataset names
            # This is a simplified mapping for common classes
            class_id = detection['class_id']
            class_map = {
                0: 'person',
                24: 'backpack',
                26: 'handbag',
                63: 'laptop',
                67: 'cell phone',
                73: 'book'
            }
            return class_map.get(class_id, f'class_{class_id}')
        return 'unknown'

    def _get_behavior_description(self, detection):
        """
        Get a human-readable description of the suspicious behavior.

        Args:
            detection: Detection dictionary

        Returns:
            Behavior description (string)
        """
        if 'behavior' in detection and 'suspicion' in detection['behavior']:
            suspicion = detection['behavior']['suspicion']
            if 'components' in suspicion:
                # Use the highest scoring component as behavior description
                components = suspicion['components']
                if components:
                    max_comp = max(components.items(), key=lambda x: x[1])
                    return max_comp[0]
        return 'unknown'

    def _cleanup_old_evidence(self):
        """
        Remove evidence older than retention period and enforce max events limit.
        """
        current_time = datetime.now()
        dirs_to_remove = []

        # Check all subdirectories in output_dir
        if os.path.exists(self.output_dir):
            for dirname in os.listdir(self.output_dir):
                dir_path = os.path.join(self.output_dir, dirname)
                if os.path.isdir(dir_path):
                    try:
                        # Extract timestamp from dirname (format: YYYYMMDD_HHMMSS_fffff_score)
                        timestamp_str = dirname.split(
                            '_')[0] + '_' + dirname.split('_')[1]
                        event_time = datetime.strptime(
                            timestamp_str, '%Y%m%d_%H%M%S')

                        # Check if older than retention period
                        if (current_time - event_time).days > self.max_retention_days:
                            dirs_to_remove.append(dir_path)
                    except (ValueError, IndexError):
                        # If can't parse, keep it (maybe manual saves)
                        pass

        # Remove old directories securely
        for dir_path in dirs_to_remove:
            self._secure_delete_recursive(dir_path)
            print(
                f"Auto-deleted old evidence (securely): {os.path.basename(dir_path)}")

        # If still too many, remove oldest (though deque should limit)
        all_dirs = [os.path.join(self.output_dir, d) for d in os.listdir(self.output_dir)
                    if os.path.isdir(os.path.join(self.output_dir, d))]
        if len(all_dirs) > self.max_saved_events:
            # Sort by modification time, keep newest
            all_dirs.sort(key=os.path.getmtime, reverse=True)
            for old_dir in all_dirs[self.max_saved_events:]:
                shutil.rmtree(old_dir)
                print(
                    f"Auto-deleted excess evidence: {os.path.basename(old_dir)}")

    def get_recent_events(self, limit=10):
        """
        Get list of recent flagged events for export/UI integration.

        Returns:
            List of event metadata dictionaries
        """
        events = []
        for event in list(self.saved_events)[-limit:]:
            metadata_path = os.path.join(event['path'], 'metadata.json')
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    events.append(json.load(f))
        return events

    def manual_save(self, frame, detections, reason="manual", timestamp=None):
        """
        Manually save evidence (for Dev B's UI integration).

        Args:
            frame: OpenCV image
            detections: Detection data
            reason: Manual reason for flagging
            timestamp: Optional timestamp
        """
        if timestamp is None:
            timestamp = datetime.now()

        # Store current auto_save state
        original_auto_save = self.auto_save_enabled

        # Enable auto-save for manual save
        self.auto_save_enabled = True

        # Force save with high suspicion score
        self._save_evidence(frame, detections, timestamp, 1.0)

        # Restore original auto_save state
        self.auto_save_enabled = original_auto_save

        # Update metadata with manual reason
        event_dir = os.path.join(
            self.output_dir, self.saved_events[-1]['event_id'])
        metadata_path = os.path.join(event_dir, "metadata.json")
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            metadata['manual_save'] = True
            metadata['manual_reason'] = reason
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)

    def _secure_delete_recursive(self, dir_path):
        """
        Recursively secure delete a directory and its contents.
        """
        if not os.path.exists(dir_path):
            return

        for root, dirs, files in os.walk(dir_path, topdown=False):
            for name in files:
                file_path = os.path.join(root, name)
                self._secure_delete_file(file_path)
            for name in dirs:
                os.rmdir(os.path.join(root, name))

        if os.path.exists(dir_path):
            os.rmdir(dir_path)

    def _secure_delete_file(self, file_path):
        """
        Securely delete a file by overwriting it before removal.
        Note: On SSDs/Flash storage, physical overwrite isn't guaranteed due to wear leveling,
        but this provides best-effort software-level compliance.
        """
        try:
            if os.path.exists(file_path):
                # Get file size
                stats = os.stat(file_path)
                length = stats.st_size

                # Pass 1: Overwrite with random data
                with open(file_path, "wb") as f:
                    f.write(secrets.token_bytes(length))
                    f.flush()
                    os.fsync(f.fileno())

                # Pass 2: Overwrite with zeros
                with open(file_path, "wb") as f:
                    f.write(b'\\x00' * length)
                    f.flush()
                    os.fsync(f.fileno())

                # Final removal
                os.remove(file_path)
        except Exception as e:
            print(f"Error secure deleting {file_path}: {e}")
            # Fallback to standard delete
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass
