from src.detection.yolo_detector import YOLODetector
from src.detection.pose_detector import PoseDetector
import os
import sys
import cv2
import time
import numpy as np

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_class_label(detector, class_id):
    names = detector.model.names
    if isinstance(names, dict):
        return names.get(class_id, str(class_id))
    if isinstance(names, (list, tuple)) and class_id < len(names):
        return names[class_id]
    return str(class_id)


def test_webcam_pose():
    """
    Test optimized pose detection for webcam.
    """
    print("Initializing optimized detectors...")

    # Initialize pose detector with optimized settings
    pose_detector = PoseDetector(
        model_complexity=0,  # Reduced complexity for speed
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
        smoothing_factor=0.85,  # Smoothing to reduce jitter
        history_length=8  # Number of frames to use for smoothing
    )

    # Initialize YOLO detector for person detection
    yolo_detector = YOLODetector(
        enable_tracking=False, enable_seat_mapping=False)

    # Initialize video capture for webcam
    cap = cv2.VideoCapture(0)

    # Check if camera opened successfully
    if not cap.isOpened():
        print("Error: Could not open webcam")
        return

    # Set webcam resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1440)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1440)
    cap.set(cv2.CAP_PROP_FPS, 30)

    # Give camera time to initialize
    print("Initializing webcam...")
    time.sleep(2.0)

    # Process video frames
    frame_count = 0
    start_time = time.time()
    show_connections = True
    track_id_counter = 0

    # Simple person tracking based on position
    prev_positions = {}
    scale_factor = 0.85
    scale_inverse = 1.0 / scale_factor

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Reduce frame size for faster processing
        small_frame = cv2.resize(
            frame, (0, 0), fx=scale_factor, fy=scale_factor)

        yolo_result = yolo_detector.detect_frame(small_frame)
        detections = yolo_result['detections']
        person_detections = [d for d in detections if d['class_id'] == 0]
        object_detections = [d for d in detections if d['class_id'] != 0]

        annotated_frame = frame.copy()
        frame_height, frame_width = annotated_frame.shape[:2]

        for obj in object_detections:
            ox1, oy1, ox2, oy2 = obj['bbox']
            ox1 = int(ox1 * scale_inverse)
            oy1 = int(oy1 * scale_inverse)
            ox2 = int(ox2 * scale_inverse)
            oy2 = int(oy2 * scale_inverse)
            color = (0, 165, 255)
            cv2.rectangle(annotated_frame, (ox1, oy1), (ox2, oy2), color, 2)
            label = f"{get_class_label(yolo_detector, obj['class_id'])} {obj['confidence']:.2f}"
            cv2.putText(annotated_frame, label, (ox1, max(oy1 - 10, 20)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # Process each detected person
        for i, person in enumerate(person_detections):
            px1, py1, px2, py2 = person['bbox']
            x1 = int(px1 * scale_inverse)
            y1 = int(py1 * scale_inverse)
            x2 = int(px2 * scale_inverse)
            y2 = int(py2 * scale_inverse)

            # Draw bounding box
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            bbox_width = max(x2 - x1, 1)
            bbox_height = max(y2 - y1, 1)

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
            person['pose'] = pose_result
            yolo_detector._annotate_behavior(detections)
            behavior = person.get('behavior')
            behavior_hands = behavior.get('hands') if behavior else None

            # Draw pose landmarks if detected
            if pose_result['success']:
                # Get posture metrics
                posture_metrics = pose_detector.get_posture_metrics(
                    pose_result['landmarks'])
                orientation = pose_result.get('head_orientation')
                hand_metrics = pose_result.get('hand_metrics')
                face_region = pose_result.get('face_region')

                # Draw pose landmarks on person in original frame
                if pose_result['head']:
                    for landmark in pose_result['head']:
                        x = int(x1 + landmark['x'] * bbox_width)
                        y = int(y1 + landmark['y'] * bbox_height)
                        cv2.circle(annotated_frame, (x, y), 5,
                                   (0, 0, 255), -1)  # Red for head

                if pose_result['shoulders']:
                    for landmark in pose_result['shoulders']:
                        x = int(x1 + landmark['x'] * bbox_width)
                        y = int(y1 + landmark['y'] * bbox_height)
                        cv2.circle(annotated_frame, (x, y), 5,
                                   (0, 255, 0), -1)  # Green for shoulders

                if pose_result['hands']:
                    for landmark in pose_result['hands']:
                        x = int(x1 + landmark['x'] * bbox_width)
                        y = int(y1 + landmark['y'] * bbox_height)
                        cv2.circle(annotated_frame, (x, y), 5,
                                   (255, 0, 0), -1)  # Blue for hands

                if face_region:
                    cx = int(x1 + face_region['center'][0] * bbox_width)
                    cy = int(y1 + face_region['center'][1] * bbox_height)
                    radius_px = int(
                        face_region['radius'] * min(bbox_width, bbox_height))
                    if radius_px < 1:
                        radius_px = 1
                    cv2.circle(annotated_frame, (cx, cy),
                               radius_px, (255, 255, 0), 2)

                if hand_metrics:
                    for side, base_color in (('left', (0, 255, 255)), ('right', (255, 0, 255))):
                        entry = hand_metrics.get(side)
                        if not entry:
                            continue
                        position = entry.get('position')
                        if not position or not entry.get('visible'):
                            continue
                        hand_behavior = behavior_hands.get(
                            side) if behavior_hands else None
                        near_object = hand_behavior.get(
                            'near_object') if hand_behavior else False
                        color = base_color
                        if near_object:
                            color = (0, 0, 255)
                        hx = int(x1 + position[0] * bbox_width)
                        hy = int(y1 + position[1] * bbox_height)
                        size = 12 if near_object else (
                            10 if entry.get('near_face') else 8)
                        thickness = - \
                            1 if entry.get('near_face') or near_object else 2
                        cv2.circle(annotated_frame, (hx, hy),
                                   size, color, thickness)
                        if hand_behavior and hand_behavior.get('global_position'):
                            gx, gy = hand_behavior['global_position']
                            gx = int(gx * scale_inverse)
                            gy = int(gy * scale_inverse)
                            cv2.circle(annotated_frame, (gx, gy),
                                       6, (0, 0, 255), -1)

                # Draw posture metrics if available
                metrics_text = [f"Person {track_id}"]

                if orientation:
                    metrics_text.append(f"Yaw: {orientation['yaw']:.1f}°")
                    metrics_text.append(f"Pitch: {orientation['pitch']:.1f}°")
                    metrics_text.append(f"Roll: {orientation['roll']:.1f}°")

                if posture_metrics:
                    metrics_text.append(
                        f"Shoulder: {posture_metrics['shoulder_tilt']:.1f}°")
                    metrics_text.append(
                        f"Head: {posture_metrics['head_tilt']:.1f}°")
                    if posture_metrics['left_arm_raised']:
                        metrics_text.append("L: Raised")
                    if posture_metrics['right_arm_raised']:
                        metrics_text.append("R: Raised")

                if hand_metrics:
                    left_metrics = hand_metrics.get('left')
                    right_metrics = hand_metrics.get('right')
                    if left_metrics and left_metrics.get('distance_to_face') is not None:
                        metrics_text.append(
                            f"L Face: {left_metrics['distance_to_face']:.2f} ({'near' if left_metrics.get('near_face') else 'far'})")
                    if right_metrics and right_metrics.get('distance_to_face') is not None:
                        metrics_text.append(
                            f"R Face: {right_metrics['distance_to_face']:.2f} ({'near' if right_metrics.get('near_face') else 'far'})")
                    if behavior_hands:
                        for label, key in (('L', 'left'), ('R', 'right')):
                            hand_entry = behavior_hands.get(key)
                            if not hand_entry:
                                continue
                            distance = hand_entry.get('distance_to_object')
                            if distance is None:
                                continue
                            status = 'near' if hand_entry.get(
                                'near_object') else 'far'
                            obj_label = hand_entry.get(
                                'object_class') or 'object'
                            metrics_text.append(
                                f"{label} Obj: {obj_label} {distance:.1f} ({status})")

                text_x = max(10, min(x2 + 10, frame_width - 200))
                text_y = max(y1, 20)
                for j, text in enumerate(metrics_text):
                    (text_w, text_h), baseline = cv2.getTextSize(
                        text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                    y = text_y + j * (text_h + 12)
                    cv2.rectangle(annotated_frame, (text_x - 4, y - text_h - 4),
                                  (text_x + text_w + 4, y + baseline + 4), (0, 0, 0), cv2.FILLED)
                    cv2.putText(annotated_frame, text, (text_x, y + baseline),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

                # Draw pose skeleton if connections are enabled
                if show_connections:
                    # Draw connections on a temporary image
                    temp_img = np.zeros_like(person_img)
                    skeleton_img = pose_detector.draw_landmarks(
                        temp_img,
                        pose_result['landmarks'],
                        connections=True
                    )

                    # Overlay skeleton on original frame
                    mask = skeleton_img > 0
                    annotated_frame[y1:y2, x1:x2][mask] = skeleton_img[mask]

        # If no people detected, show a message
        if len(person_detections) == 0:
            cv2.putText(annotated_frame, "No people detected", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        # Print pose info every 30 frames
        if frame_count % 30 == 0:
            print(f"Frame {frame_count}:")
            print(f"  People detected: {len(person_detections)}")
            elapsed = time.time() - start_time
            if elapsed > 0:
                fps = frame_count / elapsed
                print(f"  FPS: {fps:.2f}")

        # Display instructions
        instructions = [
            "Press 'c' to toggle connections",
            "Press 'q' to quit"
        ]
        for i, text in enumerate(instructions):
            cv2.putText(annotated_frame, text, (10, 30 + i*30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # Display frame
        cv2.imshow('Webcam Pose Detection', annotated_frame)

        # Check for key presses
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('c'):
            show_connections = not show_connections
            print(f"Connections {'shown' if show_connections else 'hidden'}")

        frame_count += 1

    # Release resources
    cap.release()
    cv2.destroyAllWindows()

    # Close detector
    pose_detector.close()


if __name__ == "__main__":
    test_webcam_pose()
