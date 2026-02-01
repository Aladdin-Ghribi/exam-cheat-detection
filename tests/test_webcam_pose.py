
import cv2
import time
import numpy as np
from src.detection.suspicion_scorer import SuspicionScorer
from src.detection.pose_detector import PoseDetector
from src.detection.yolo_detector import YOLODetector
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Add project root to sys.path


def get_class_label(detector, class_id):
    """Get human-readable class label from class ID."""
    names = detector.model.names
    if isinstance(names, dict):
        return names.get(class_id, str(class_id))
    if isinstance(names, (list, tuple)) and class_id < len(names):
        return names[class_id]
    return str(class_id)


def make_empty_hand_entry():
    """Create an empty hand entry structure."""
    return {
        'near_face': False,
        'distance_to_face': None,
        'near_object': False,
        'distance_to_object': None,
        'object_class': None,
        'position': None,
        'global_position': None,
        'visible': False,
        'face_threshold': None
    }


def get_suspicion_color(level):
    """
    Get color based on suspicion level for smooth gradient.
    FIXED: Proper color gradient from green -> yellow -> orange -> red

    Args:
        level: Suspicion level (0.0 to 1.0)

    Returns:
        BGR color tuple
    """
    level = max(0.0, min(1.0, level))

    if level < 0.25:
        # Green to Yellow-Green (0.0 - 0.25)
        t = level / 0.25
        red = int(128 * t)
        green = 255
        blue = 0
    elif level < 0.5:
        # Yellow-Green to Yellow (0.25 - 0.5)
        t = (level - 0.25) / 0.25
        red = int(128 + 127 * t)
        green = 255
        blue = 0
    elif level < 0.75:
        # Yellow to Orange (0.5 - 0.75)
        t = (level - 0.5) / 0.25
        red = 255
        green = int(255 - 100 * t)
        blue = 0
    else:
        # Orange to Red (0.75 - 1.0)
        t = (level - 0.75) / 0.25
        red = 255
        green = int(155 - 155 * t)
        blue = 0

    return (blue, green, red)


def test_webcam_pose():
    """
    Test pose detection and suspicion scoring using webcam.
    """
    print("Initializing detectors...")

    # Initialize pose detector with optimized settings
    pose_detector = PoseDetector(
        model_complexity=0,              # Fastest model
        min_detection_confidence=0.4,    # Balanced for detection
        min_tracking_confidence=0.4,     # Balanced for tracking
        smoothing_factor=0.7,            # Good smoothing
        history_length=10                # Good history
    )

    # Initialize YOLO detector for person and object detection
    yolo_detector = YOLODetector(
        enable_tracking=True,
        enable_seat_mapping=False,
        enable_pose=False  # We'll handle pose separately
    )

    # Initialize suspicion scorer
    suspicion_scorer = SuspicionScorer(
        history_length=10,
        smoothing_factor=0.6
    )

    # Initialize video capture with DirectShow backend (more stable on Windows)
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    if not cap.isOpened():
        print("Error: Could not open webcam with DirectShow, trying default...")
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Error: Could not open webcam")
            return

    # Set webcam resolution and FPS
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    print("Initializing webcam...")
    # Read and discard first few frames
    for _ in range(5):
        cap.read()
    time.sleep(0.5)

    # Processing variables
    frame_count = 0
    start_time = time.time()
    show_connections = True
    show_metrics = True
    manual_track_id_counter = 0
    manual_prev_positions = {}
    scale_factor = 1.0  # No scaling needed with 640x480

    print("\nControls:")
    print("  'c' - Toggle skeleton connections")
    print("  'm' - Toggle detailed metrics")
    print("  'q' - Quit")
    print("\nStarting detection...\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to read frame")
            break

        # Resize frame for faster processing
        small_frame = cv2.resize(
            frame, (0, 0), fx=scale_factor, fy=scale_factor)

        # Run YOLO detection
        yolo_result = yolo_detector.detect_frame(small_frame)
        detections = yolo_result['detections']

        # Separate person and object detections
        person_detections = [d for d in detections if d['class_id'] == 0]
        object_detections = [d for d in detections if d['class_id'] != 0]

        frame_active_keys = set()
        manual_active_ids = set()
        annotated_frame = frame.copy()
        frame_height, frame_width = annotated_frame.shape[:2]

        # Draw detected objects first
        for obj in object_detections:
            ox1, oy1, ox2, oy2 = obj['bbox']
            ox1 = int(ox1 / scale_factor)
            oy1 = int(oy1 / scale_factor)
            ox2 = int(ox2 / scale_factor)
            oy2 = int(oy2 / scale_factor)

            color = (0, 165, 255)  # Orange for objects
            cv2.rectangle(annotated_frame, (ox1, oy1), (ox2, oy2), color, 2)

            label = f"{get_class_label(yolo_detector, obj['class_id'])} {obj['confidence']:.2f}"
            cv2.putText(annotated_frame, label, (ox1, max(oy1 - 10, 20)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # Process each detected person
        for person in person_detections:
            px1, py1, px2, py2 = person['bbox']
            x1 = int(px1 / scale_factor)
            y1 = int(py1 / scale_factor)
            x2 = int(px2 / scale_factor)
            y2 = int(py2 / scale_factor)

            bbox_width = max(x2 - x1, 1)
            bbox_height = max(y2 - y1, 1)

            # Crop person region
            person_img = frame[y1:y2, x1:x2]
            if person_img.size == 0:
                continue

            # Handle tracking ID
            center_x, center_y = (x1 + x2) // 2, (y1 + y2) // 2
            track_id = person.get('track_id')

            if track_id is None:
                # Manual tracking fallback
                min_dist = float('inf')
                for prev_id, (prev_x, prev_y) in manual_prev_positions.items():
                    dist = np.sqrt((center_x - prev_x) ** 2 +
                                   (center_y - prev_y) ** 2)
                    if dist < min_dist and dist < 100:
                        min_dist = dist
                        track_id = prev_id

                if track_id is None:
                    track_id = f"manual_{manual_track_id_counter}"
                    manual_track_id_counter += 1

                manual_prev_positions[track_id] = (center_x, center_y)
                manual_active_ids.add(track_id)
            elif isinstance(track_id, str) and track_id.startswith('manual_'):
                manual_prev_positions[track_id] = (center_x, center_y)
                manual_active_ids.add(track_id)

            # Detect pose
            pose_result = pose_detector.detect(person_img, track_id)
            person['pose'] = pose_result
            person['track_id'] = track_id

            # Build behavior data
            behavior = {
                'head_orientation': None,
                'face_region': None,
                'hands': {
                    'left': make_empty_hand_entry(),
                    'right': make_empty_hand_entry()
                }
            }

            if pose_result.get('success'):
                behavior['head_orientation'] = pose_result.get(
                    'head_orientation')
                behavior['face_region'] = pose_result.get('face_region')
                behavior['hands']['left'] = yolo_detector._build_behavior_hand_entry(
                    person, pose_result, object_detections, 'left')
                behavior['hands']['right'] = yolo_detector._build_behavior_hand_entry(
                    person, pose_result, object_detections, 'right')

            person['behavior'] = behavior

            # Calculate suspicion score
            suspicion_info = suspicion_scorer.score_detection(person)
            key = suspicion_info.pop('key', None)
            behavior['suspicion'] = suspicion_info

            if key is not None:
                frame_active_keys.add(key)

            # Get bbox color based on suspicion level
            level = suspicion_info.get('smoothed', 0.0)
            bbox_color = get_suspicion_color(level)

            # Draw bounding box with suspicion-based color
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), bbox_color, 3)

            # Draw pose landmarks if successful
            if pose_result.get('success'):
                face_region = pose_result.get('face_region')
                hand_metrics = pose_result.get('hand_metrics')

                # Draw face region
                if face_region:
                    cx = int(x1 + face_region['center'][0] * bbox_width)
                    cy = int(y1 + face_region['center'][1] * bbox_height)
                    radius_px = int(
                        face_region['radius'] * min(bbox_width, bbox_height))
                    radius_px = max(radius_px, 1)
                    cv2.circle(annotated_frame, (cx, cy),
                               radius_px, (255, 255, 0), 2)

                # Draw hand positions
                if hand_metrics:
                    behavior_hands = behavior['hands']

                    for side, base_color in [('left', (0, 255, 255)), ('right', (255, 0, 255))]:
                        entry = hand_metrics.get(side)
                        if not entry or not entry.get('visible'):
                            continue

                        position = entry.get('position')
                        if not position:
                            continue

                        hand_behavior = behavior_hands.get(side)
                        near_object = hand_behavior.get(
                            'near_object') if hand_behavior else False

                        # Choose color based on proximity
                        color = (0, 0, 255) if near_object else base_color

                        hx = int(x1 + position[0] * bbox_width)
                        hy = int(y1 + position[1] * bbox_height)

                        size = 12 if near_object else (
                            10 if entry.get('near_face') else 8)
                        thickness = -1 if (entry.get('near_face')
                                           or near_object) else 2

                        cv2.circle(annotated_frame, (hx, hy),
                                   size, color, thickness)

                # Draw skeleton if enabled
                if show_connections:
                    temp_img = np.zeros_like(person_img)
                    skeleton_img = pose_detector.draw_landmarks(
                        temp_img,
                        pose_result['landmarks'],
                        connections=True
                    )
                    mask = skeleton_img > 0
                    annotated_frame[y1:y2, x1:x2][mask] = skeleton_img[mask]

            # Draw metrics if enabled
            if show_metrics:
                metrics_text = [f"ID: {track_id}"]

                orientation = behavior.get('head_orientation')
                if orientation:
                    yaw = orientation['yaw']
                    pitch = orientation['pitch']
                    roll = orientation['roll']

                    # Display actual orientation values
                    metrics_text.append(f"Yaw: {yaw:.1f}°")
                    metrics_text.append(f"Pitch: {pitch:.1f}°")
                    metrics_text.append(f"Roll: {roll:.1f}°")

                # Suspicion info with visual indicator
                if suspicion_info:
                    raw_score = suspicion_info['raw']
                    smooth_score = suspicion_info['smoothed']

                    metrics_text.append(f"Raw: {raw_score:.2f}")
                    metrics_text.append(f"Smooth: {smooth_score:.2f}")

                    # Risk level indicator
                    if smooth_score < 0.2:
                        risk_level = "LOW"
                        risk_color = (0, 255, 0)
                    elif smooth_score < 0.5:
                        risk_level = "MEDIUM"
                        risk_color = (0, 255, 255)
                    elif smooth_score < 0.75:
                        risk_level = "HIGH"
                        risk_color = (0, 165, 255)
                    else:
                        risk_level = "CRITICAL"
                        risk_color = (0, 0, 255)

                    metrics_text.append(f"Risk: {risk_level}")

                    # Component breakdown
                    components = suspicion_info.get('components', {})
                    h = components.get('head', 0.0)
                    f = components.get('hands_face', 0.0)
                    o = components.get('hands_object', 0.0)
                    metrics_text.append(f"H:{h:.2f} F:{f:.2f} O:{o:.2f}")

                # Draw metrics panel
                text_x = max(10, min(x2 + 10, frame_width - 250))
                text_y = max(y1, 30)

                for j, text in enumerate(metrics_text):
                    (text_w, text_h), baseline = cv2.getTextSize(
                        text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                    y = text_y + j * (text_h + 12)

                    # Draw background
                    cv2.rectangle(annotated_frame,
                                  (text_x - 4, y - text_h - 4),
                                  (text_x + text_w + 4, y + baseline + 4),
                                  (0, 0, 0), cv2.FILLED)

                    # Use risk color for risk level text
                    text_color = risk_color if "Risk:" in text else (
                        255, 255, 255)

                    # Draw text
                    cv2.putText(annotated_frame, text, (text_x, y + baseline),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 1)

        # Prune inactive tracks
        if suspicion_scorer:
            suspicion_scorer.prune(frame_active_keys)

        if manual_active_ids:
            manual_prev_positions = {k: v for k, v in manual_prev_positions.items()
                                     if k in manual_active_ids}
        else:
            manual_prev_positions.clear()

        # Display status message if no people detected
        if len(person_detections) == 0:
            cv2.putText(annotated_frame, "No people detected", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        # Display FPS and instructions
        if frame_count % 30 == 0:
            elapsed = time.time() - start_time
            if elapsed > 0:
                fps = frame_count / elapsed
                print(
                    f"Frame {frame_count} | People: {len(person_detections)} | FPS: {fps:.1f}")

        # Draw instructions
        instructions = [
            "Press 'c' to toggle connections",
            "Press 'm' to toggle metrics",
            "Press 'q' to quit"
        ]
        for i, text in enumerate(instructions):
            cv2.putText(annotated_frame, text, (10, frame_height - 90 + i*30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # Display frame
        cv2.imshow('Exam Cheat Detection - Webcam Test', annotated_frame)

        # Handle key presses
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('c'):
            show_connections = not show_connections
            print(f"Connections: {'ON' if show_connections else 'OFF'}")
        elif key == ord('m'):
            show_metrics = not show_metrics
            print(f"Metrics: {'ON' if show_metrics else 'OFF'}")

        frame_count += 1

    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    pose_detector.close()

    # Print summary
    elapsed = time.time() - start_time
    avg_fps = frame_count / elapsed if elapsed > 0 else 0
    print(f"\nProcessing complete!")
    print(f"Total frames: {frame_count}")
    print(f"Total time: {elapsed:.1f}s")
    print(f"Average FPS: {avg_fps:.1f}")


if __name__ == "__main__":
    test_webcam_pose()
