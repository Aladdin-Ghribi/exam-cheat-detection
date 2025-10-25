import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

import cv2
from ultralytics import YOLO
from config import YOLO_MODEL, CONFIDENCE_THRESHOLD, IMG_SIZE




CHEATING_RELATED_CLASSES = {
  'cell_phone' : 67,
  'book' : 73,
  'laptop' : 63,
  'backpack' : 24,
  'handbag': 26,
  }

PERSON_CLASS_ID = 0

class YOLODetector:
    def __init__(self, model_path=YOLO_MODEL):
        self.model = YOLO(model_path)
        self.target_class_ids= [PERSON_CLASS_ID] + list(CHEATING_RELATED_CLASSES.values())

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

if __name__ == "__main__":
    detector = YOLODetector()
    
    video_source = 0     
    '''
    use 0 for webcam as integer      ### use app called droidcam for using phone as webcam 
    use path to video file for video example 'data/sample/test4.mp4'
    use path to image file for image example 'data/sample/test1.jpg'
    
    '''

    for detections, img in detector.detect(source=video_source):
        print(f'Detections in current frame: {detections}')

    

        for det in detections:
            x1, y1, x2, y2 = map(int, det['bbox'])
            label = f"{detector.model.names[det['class_id']]} {det['confidence']:.2f}"
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(img, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        cv2.imshow('YOLO Detection', img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("User interrupted the video playback.")
            break
cv2.destroyAllWindows()
print("video playback finished or stopped.")