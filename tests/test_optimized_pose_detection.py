from src.detection.yolo_detector import YOLODetector
from src.detection.pose_detector import PoseDetector
import os
import sys
import cv2
import time
import argparse
import numpy as np

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_optimized_pose_detection(source, save_output=False, output_path=None):
    """
    Test optimized pose detection for multiple people in a frame.

    Args:
        source: Video source (0 for webcam, path to video file)
        save_output: Whether to save output video
        output_path: Path to save output video
    """
    print("Initializing optimized detectors...")

    # Initialize pose detector with optimized settings
    pose_detector = PoseDetector(
        model_complexity=0,  # Fastest model
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
        smoothing_factor=0.7,  # Smoothing to reduce jitter
        history_length=5  # Number of frames to use for smoothing
    )

    # Initialize YOLO detector for person detection
    yolo_detector = YOLODetector(
        enable_tracking=False, enable_seat_mapping=False)

    # Initialize video capture
    cap = cv2.VideoCapture(source)

    # Check if camera opened successfully
    if not cap.isOpened():
        print(f"Error: Could not open video source {source}")
        return

    # For webcam, set resolution
    if source == 0:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)

    # Get video properties
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Initialize video writer if saving output
    writer = None
    if save_output:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        if output_path is None:
            output_path = 'output_optimized_pose_detection.mp4'
        writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    # Process video frames
    frame_count = 0
    start_time = time.time()
    show_connections = True
    track_id_counter = 0

    # Simple person tracking based on position
    prev_positions = {}

    # Give camera time to initialize
    print("Initializing camera...")
    time.sleep(2.0)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Reduce frame size for faster processing (optional)
        small_frame = cv2.resize(frame, (0, 0), fx=0.8, fy=0.8)

        # Detect people first using YOLO
        yolo_result = yolo_detector.detect_frame(small_frame)
        person_detections = [d for d in yolo_result['detections']
                             if d['class_id'] == 0]  # Filter for person class

        # Start with original frame
        annotated_frame = frame.copy()

        # Process each detected person
        for i, person in enumerate(person_detections):
            # Get person bounding box
            x1, y1, x2, y2 = map(int, person['bbox'])

            # Scale back to original frame size
            x1, y1, x2, y2 = int(x1/0.8), int(y1/0.8), int(x2/0.8), int(y2/0.8)

            # Draw bounding box
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # Crop person from frame
            person_img = frame[y1:y2, x1:x2]

            # Skip if crop is invalid
            if person_img.size == 0:
                continue

            # Assign track ID based on position
            center_x, center_y = (x1 + x2) // 2, (y1 + y2) // 2
            track_id = None

            # Find closest previous position
            min_dist = float('inf')
            if prev_positions:  # Check if prev_positions is not empty
                for prev_id, (prev_x, prev_y) in prev_positions.items():
                    dist = np.sqrt((center_x - prev_x)**2 +
                                   (center_y - prev_y)**2)
                    if dist < min_dist and dist < 100:  # Threshold for matching
                        min_dist = dist
                        track_id = prev_id

            # If no match found, assign new ID
            if track_id is None:
                track_id = track_id_counter
                track_id_counter += 1

            # Update position
            prev_positions[track_id] = (center_x, center_y)

            # Detect pose for this person with track ID for smoothing
            pose_result = pose_detector.detect(person_img, track_id)

            # Draw pose landmarks if detected
            if pose_result['success']:
                # Get posture metrics
                posture_metrics = pose_detector.get_posture_metrics(
                    pose_result['landmarks'])

                # Draw pose landmarks on person in original frame
                if pose_result['head']:
                    for landmark in pose_result['head']:
                        x = int(x1 + landmark['x'] * (x2 - x1))
                        y = int(y1 + landmark['y'] * (y2 - y1))
                        cv2.circle(annotated_frame, (x, y), 5,
                                   (0, 0, 255), -1)  # Red for head

                if pose_result['shoulders']:
                    for landmark in pose_result['shoulders']:
                        x = int(x1 + landmark['x'] * (x2 - x1))
                        y = int(y1 + landmark['y'] * (y2 - y1))
                        cv2.circle(annotated_frame, (x, y), 5,
                                   (0, 255, 0), -1)  # Green for shoulders

                if pose_result['hands']:
                    for landmark in pose_result['hands']:
                        x = int(x1 + landmark['x'] * (x2 - x1))
                        y = int(y1 + landmark['y'] * (y2 - y1))
                        cv2.circle(annotated_frame, (x, y), 5,
                                   (255, 0, 0), -1)  # Blue for hands

                # Draw posture metrics
                if posture_metrics:
                    metrics_text = [
                        f"Person {track_id}",
                        f"Shoulder: {posture_metrics['shoulder_tilt']:.1f}°",
                        f"Head: {posture_metrics['head_tilt']:.1f}°"
                    ]

                    if posture_metrics['left_arm_raised']:
                        metrics_text.append("L: Raised")
                    if posture_metrics['right_arm_raised']:
                        metrics_text.append("R: Raised")

                    # Draw text
                    for j, text in enumerate(metrics_text):
                        cv2.putText(annotated_frame, text, (x1, y1 - 10 - j*20),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

                # Draw pose skeleton if connections are enabled
                if show_connections:
                    # Draw connections on a buffer image
                    temp_img = np.zeros_like(person_img)
                    skeleton_img = pose_detector.draw_landmarks(
                        temp_img,
                        pose_result['landmarks'],
                        connections=True
                    )

                    # Overlay skeleton on original frame
                    mask = (skeleton_img > 0).any(axis=2)
                    annotated_frame[y1:y2, x1:x2][mask] = skeleton_img[mask]

        # If no people detected, show a message
        if len(person_detections) == 0:
            cv2.putText(annotated_frame, "No people detected", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        # Print pose info every 30 frames
        if frame_count % 30 == 0:
            print(f"Frame {frame_count}:")
            print(f"  People detected: {len(person_detections)}")
            print(f"  Processing time: {time.time() - start_time:.2f}s")

        # Display instructions
        instructions = [
            "Press 'c' to toggle connections",
            "Press 'q' to quit"
        ]
        for i, text in enumerate(instructions):
            cv2.putText(annotated_frame, text, (width - 250, 30 + i*30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # Display frame
        cv2.imshow('Optimized Pose Detection', annotated_frame)

        # Save frame if requested
        if writer:
            writer.write(annotated_frame)

        # Check for key presses
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('c'):
            show_connections = not show_connections
            print(f"Connections {'shown' if show_connections else 'hidden'}")

        frame_count += 1

    # Calculate and print FPS
    end_time = time.time()
    elapsed_time = end_time - start_time
    if elapsed_time > 0:
        fps_actual = frame_count / elapsed_time
        print(f"Processed {frame_count} frames in {elapsed_time:.2f} seconds")
        print(f"Average FPS: {fps_actual:.2f}")
    else:
        print(f"Processed {frame_count} frames in less than a second")

    # Release resources
    cap.release()
    if writer:
        writer.release()
    cv2.destroyAllWindows()

    # Close detector
    pose_detector.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Test optimized multi-person pose detection')
    parser.add_argument('--source', type=str, default=0,
                        help='Video source (0 for webcam, path to video file)')
    parser.add_argument('--save', action='store_true',
                        help='Save output video')
    parser.add_argument('--output', type=str, help='Output video path')

    args = parser.parse_args()

    result = test_optimized_pose_detection(args.source, args.save, args.output)

    # Keep window open until user closes it
    if result is not None and args.source == 0:
        cv2.waitKey(0)
