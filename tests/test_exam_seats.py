from src.detection.exam_seat_manager import ExamSeatManager
from src.detection.yolo_detector import YOLODetector
import os
import sys
import cv2
import time
import argparse
import numpy as np

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_exam_seats(source, save_output=False, output_path=None, config_path=None):
    """
    Test exam seat manager for assigning people to seats.

    Args:
        source: Video source (0 for webcam, path to video file)
        save_output: Whether to save output video
        output_path: Path to save output video
        config_path: Path to load/save seat configuration
    """
    print("Initializing exam seat manager...")

    # Initialize detector with tracking and seat mapping
    detector = YOLODetector(enable_tracking=True, enable_seat_mapping=True)

    # Initialize exam seat manager
    seat_manager = ExamSeatManager()

    # Load configuration if provided
    if config_path and os.path.exists(config_path):
        try:
            print(f"Loading seat configuration from {config_path}")
            if not seat_manager.load_config(config_path):
                print("Failed to load configuration, starting with empty configuration")
        except Exception as e:
            print(f"Error loading configuration: {e}")
            print("Starting with empty configuration")

    # Initialize video capture
    cap = cv2.VideoCapture(source)

    # Get video properties
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Update room dimensions in seat manager
    seat_manager.room_width = width
    seat_manager.room_height = height

    # Initialize video writer if saving output
    writer = None
    if save_output:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        if output_path is None:
            output_path = 'output_exam_seats.mp4'
        writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    # Process video frames
    frame_count = 0
    start_time = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Detect and track objects
        detection_result = detector.detect_frame(frame)
        detections = detection_result['detections']

        # Update seat manager with detections and frame for pose detection
        seat_result = seat_manager.update(detections, frame)

        # Draw zones and assignments with pose landmarks
        show_poses = True  # Set to True to show pose landmarks
        annotated_frame = seat_manager.draw_zones(
            frame, seat_result['zone_assignments'], show_poses)

        # Draw bounding boxes for people
        for detection in detections:
            if detection['class_id'] == 0:  # Person class
                bbox = detection['bbox']
                # Ensure bbox is in the correct format
                if isinstance(bbox, list) or isinstance(bbox, tuple):
                    if len(bbox) == 4:
                        x1, y1, x2, y2 = bbox
                    else:
                        continue
                else:
                    continue

                # Ensure coordinates are integers
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

                # Draw bounding box
                cv2.rectangle(annotated_frame, (x1, y1),
                              (x2, y2), (255, 0, 0), 2)

                # Draw track ID
                if 'track_id' in detection:
                    cv2.putText(annotated_frame, f"ID: {detection['track_id']}",
                                (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

                # Draw stable position
                if 'stable_position' in detection:
                    cx, cy = detection['stable_position']
                    # Draw stable point
                    cv2.circle(annotated_frame, (cx, cy), 8,
                               (0, 255, 255), -1)  # Yellow filled circle
                    cv2.circle(annotated_frame, (cx, cy), 8,
                               (0, 0, 0), 2)  # Black border

        # Print tracking info every 30 frames
        if frame_count % 30 == 0:
            print(f"Frame {frame_count}:")
            print(
                f"  Tracked persons: {len([d for d in detections if d['class_id'] == 0 and 'track_id' in d])}")
            print(
                f"  Zones: {len(seat_result['zones'])} (occupied: {sum(1 for z in seat_result['zones'].values() if z.get('occupied', False))})")

            # Print seat assignments
            if seat_result['zone_assignments']:
                print("  Seat assignments:")
                for track_id, zone_id in seat_result['zone_assignments'].items():
                    print(f"    Person {track_id} -> Zone {zone_id}")

        # Display frame
        cv2.imshow('Exam Seat Assignment', annotated_frame)

        # Save frame if requested
        if writer:
            writer.write(annotated_frame)

        # Check for exit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        frame_count += 1

    # Save configuration if provided
    if config_path:
        print(f"Saving seat configuration to {config_path}")
        seat_manager.save_config(config_path)

    # Calculate and print FPS
    end_time = time.time()
    elapsed_time = end_time - start_time
    fps_actual = frame_count / elapsed_time
    print(f"Processed {frame_count} frames in {elapsed_time:.2f} seconds")
    print(f"Average FPS: {fps_actual:.2f}")

    # Release resources
    cap.release()
    if writer:
        writer.release()
    cv2.destroyAllWindows()

    # Close seat manager resources
    seat_manager.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Test exam seat assignment for detected people')
    parser.add_argument('--source', type=str, default=0,
                        help='Video source (0 for webcam, path to video file)')
    parser.add_argument('--save', action='store_true',
                        help='Save output video')
    parser.add_argument('--output', type=str, help='Output video path')
    parser.add_argument('--config', type=str,
                        help='Path to load/save seat configuration')

    args = parser.parse_args()

    test_exam_seats(args.source, args.save, args.output, args.config)
