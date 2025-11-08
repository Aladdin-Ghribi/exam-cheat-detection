import cv2
import argparse
import os
import sys
import numpy as np

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.detection.yolo_detector import YOLODetector

def test_webcam_seats():
    """Test seat detection with live webcam feed"""
    # Initialize the YOLO detector
    detector = YOLODetector(model_path='yolo11m.pt')

    # Initialize webcam
    cap = cv2.VideoCapture(0)  # 0 is the default webcam

    if not cap.isOpened():
        print("Error: Could not open webcam")
        return

    # Set webcam resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    print("Starting webcam seat detection...")
    print("Press 'q' to quit")

    while True:
        # Read frame from webcam
        ret, frame = cap.read()

        if not ret:
            print("Error: Could not read frame from webcam")
            break

        # Detect people and assign seats
        detection_result = detector.detect_frame(frame)

        # Draw the results
        frame = detector.draw_detections(frame, detection_result)
        frame = detector.seat_manager.draw_zones(frame, detection_result['seat_assignments'])

        # Display the frame
        cv2.imshow('Exam Seat Detection - Webcam', frame)

        # Check for quit key
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release resources
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    test_webcam_seats()
