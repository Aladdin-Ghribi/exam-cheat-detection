import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

import cv2
from ultralytics import YOLO
from config import YOLO_MODEL, CONFIDENCE_THRESHOLD, IMG_SIZE
from .object_tracker import ObjectTracker
from .exam_seat_manager import ExamSeatManager




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
    def __init__(self, model_path=YOLO_MODEL, enable_tracking=True, enable_seat_mapping=True, room_config=None):
        self.model = YOLO(model_path)
        self.target_class_ids= [PERSON_CLASS_ID] + list(CHEATING_RELATED_CLASSES.values())
        # now accessible via detector.CHEATING_RELATED_CLASSES
        self.CHEATING_RELATED_CLASSES = CHEATING_RELATED_CLASSES

        # Initialize tracker and seat manager if enabled
        self.enable_tracking = enable_tracking
        self.enable_seat_mapping = enable_seat_mapping

        if self.enable_tracking:
            self.tracker = ObjectTracker()

        if self.enable_seat_mapping:
            self.seat_manager = ExamSeatManager()

    def detect(self, source, save_image=False, save_path=None):
        results = self.model.predict(
            source=source,
            conf=CONFIDENCE_THRESHOLD,
            imgsz= IMG_SIZE,
            classes=self.target_class_ids,
            save=save_image,
            save_txt=False,#for custom results if needed 
            stream=True,#stream result for video
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
                    detections.append({
                        'class_id': cls_id,
                        'confidence': conf,
                        'bbox': [x1, y1, x2, y2]
                    })

        # Apply tracking if enabled
        if self.enable_tracking:
            detections = self.tracker.update(detections)

        # Get seat assignments if enabled
        seat_assignments = None
        if self.enable_seat_mapping:
            seat_result = self.seat_manager.update(detections)
            seat_assignments = seat_result['zone_assignments']

        return {
            'detections': detections,
            'seat_assignments': seat_assignments
        }

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

# if __name__ == "__main__":
#     detector = YOLODetector()
    
#     video_source = 0     
#     '''
#     use 0 for webcam as integer      ### use app called droidcam for using phone as webcam 
#     use path to video file for video example 'data/sample/test4.mp4'
#     use path to image file for image example 'data/sample/test1.jpg'
    
#     '''

#     for detections, img in detector.detect(source=video_source):
#         print(f'Detections in current frame: {detections}')

    

#         for det in detections:
#             x1, y1, x2, y2 = map(int, det['bbox'])
#             label = f"{detector.model.names[det['class_id']]} {det['confidence']:.2f}"
#             cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
#             cv2.putText(img, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

#         cv2.imshow('YOLO Detection', img)
#         if cv2.waitKey(1) & 0xFF == ord('q'):
#             print("User interrupted the video playback.")
#             break
# cv2.destroyAllWindows()
# print("video playback finished or stopped.")