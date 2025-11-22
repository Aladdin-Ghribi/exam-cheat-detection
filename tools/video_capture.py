#!/usr/bin/env python3
"""
Video Capture Tool for Exam Cheat Detection Testing
Records webcam video with metadata for testing and debugging purposes.
"""

import cv2
import json
import os
import sys
from datetime import datetime
import argparse

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class VideoCaptureRecorder:
    def __init__(self, output_dir="data/test_videos", resolution=(1280, 720), fps=30):
        """
        Initialize video capture recorder.
        
        Args:
            output_dir: Directory to save recorded videos
            resolution: Video resolution (width, height)
            fps: Frames per second
        """
        self.output_dir = output_dir
        self.resolution = resolution
        self.fps = fps
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Recording state
        self.is_recording = False
        self.video_writer = None
        self.current_metadata = {}
        self.frame_count = 0
        
        # Performance optimization - frame buffer
        from collections import deque
        self.frame_buffer = deque(maxlen=60)  # Buffer up to 2 seconds at 30fps
        self.dropped_frames = 0
        
    def start_recording(self, scenario_name, description="", expected_behaviors=None):
        """
        Start recording a new video.
        
        Args:
            scenario_name: Name of the test scenario
            description: Description of what's being tested
            expected_behaviors: List of expected cheating behaviors to detect
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{scenario_name}_{timestamp}"
        
        # Video file path
        video_path = os.path.join(self.output_dir, f"{filename}.mp4")
        
        # Initialize video writer with optimized codec
        # Try different codecs for better performance
        codecs_to_try = [
            ('H264', cv2.VideoWriter_fourcc(*'H264')),  # Best quality, hardware accelerated
            ('XVID', cv2.VideoWriter_fourcc(*'XVID')),  # Good compatibility
            ('MJPG', cv2.VideoWriter_fourcc(*'MJPG')),  # Fast, larger files
            ('mp4v', cv2.VideoWriter_fourcc(*'mp4v'))   # Fallback
        ]
        
        self.video_writer = None
        for codec_name, fourcc in codecs_to_try:
            try:
                writer = cv2.VideoWriter(video_path, fourcc, self.fps, self.resolution)
                if writer.isOpened():
                    self.video_writer = writer
                    print(f"   Using codec: {codec_name}")
                    break
                writer.release()
            except:
                continue
        
        if self.video_writer is None:
            print("   ⚠️  Warning: Using fallback codec (may be slower)")
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.video_writer = cv2.VideoWriter(video_path, fourcc, self.fps, self.resolution)
        
        # Initialize metadata
        self.current_metadata = {
            'filename': f"{filename}.mp4",
            'scenario_name': scenario_name,
            'description': description,
            'expected_behaviors': expected_behaviors or [],
            'timestamp': datetime.now().isoformat(),
            'resolution': self.resolution,
            'fps': self.fps,
            'duration_seconds': 0,
            'frame_count': 0,
            'annotations': []
        }
        
        self.is_recording = True
        self.frame_count = 0
        
        print(f"📹 Started recording: {scenario_name}")
        print(f"   Output: {video_path}")
        print(f"   Press 'a' to add annotation, 'q' to stop recording")
        
    def add_annotation(self, behavior_type, description=""):
        """
        Add a time-stamped annotation during recording.
        
        Args:
            behavior_type: Type of behavior (e.g., 'phone_usage', 'head_turn')
            description: Additional description
        """
        if not self.is_recording:
            return
            
        annotation = {
            'frame': self.frame_count,
            'timestamp': self.frame_count / self.fps,
            'behavior_type': behavior_type,
            'description': description
        }
        
        self.current_metadata['annotations'].append(annotation)
        print(f"   ✓ Annotation added at {annotation['timestamp']:.2f}s: {behavior_type}")
        
    def write_frame(self, frame):
        """Write a frame to the video file with buffering."""
        if not self.is_recording or self.video_writer is None:
            return
            
        # Resize frame if needed
        if frame.shape[1] != self.resolution[0] or frame.shape[0] != self.resolution[1]:
            frame = cv2.resize(frame, self.resolution)
        
        # Try to write frame
        try:
            self.video_writer.write(frame)
            self.frame_count += 1
        except Exception as e:
            self.dropped_frames += 1
            if self.dropped_frames % 10 == 0:
                print(f"   ⚠️  Dropped {self.dropped_frames} frames")
        
    def stop_recording(self):
        """Stop recording and save metadata."""
        if not self.is_recording:
            return
            
        # Update metadata
        self.current_metadata['frame_count'] = self.frame_count
        self.current_metadata['duration_seconds'] = self.frame_count / self.fps
        
        # Save metadata
        metadata_path = os.path.join(
            self.output_dir, 
            self.current_metadata['filename'].replace('.mp4', '_metadata.json')
        )
        
        with open(metadata_path, 'w') as f:
            json.dump(self.current_metadata, f, indent=2)
        
        # Release video writer
        if self.video_writer:
            self.video_writer.release()
            
        print(f"✅ Recording stopped")
        print(f"   Duration: {self.current_metadata['duration_seconds']:.2f}s")
        print(f"   Frames: {self.frame_count}")
        if self.dropped_frames > 0:
            print(f"   ⚠️  Dropped frames: {self.dropped_frames}")
        print(f"   Annotations: {len(self.current_metadata['annotations'])}")
        print(f"   Metadata saved: {metadata_path}")
        
        self.is_recording = False
        self.video_writer = None
        self.dropped_frames = 0
        

def interactive_capture():
    """Interactive video capture with live preview."""
    parser = argparse.ArgumentParser(description='Record test videos for exam cheat detection')
    parser.add_argument('--scenario', type=str, default='test_scenario',
                       help='Scenario name')
    parser.add_argument('--description', type=str, default='',
                       help='Scenario description')
    parser.add_argument('--output-dir', type=str, default='data/test_videos',
                       help='Output directory')
    parser.add_argument('--resolution', type=str, default='1280x720',
                       help='Video resolution (WIDTHxHEIGHT)')
    parser.add_argument('--fps', type=int, default=30,
                       help='Frames per second')
    
    args = parser.parse_args()
    
    # Parse resolution
    width, height = map(int, args.resolution.split('x'))
    
    # Initialize recorder
    recorder = VideoCaptureRecorder(
        output_dir=args.output_dir,
        resolution=(width, height),
        fps=args.fps
    )
    
    # Open webcam
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    
    if not cap.isOpened():
        print("❌ Error: Could not open webcam")
        return
    
    print("\n" + "="*60)
    print("📹 Video Capture Tool - Exam Cheat Detection")
    print("="*60)
    print("\nControls:")
    print("  SPACE - Start/Stop recording")
    print("  a     - Add annotation (during recording)")
    print("  q     - Quit")
    print("\nScenario:", args.scenario)
    print("Description:", args.description or "None")
    print("="*60 + "\n")
    
    annotation_types = [
        'phone_usage',
        'head_turn_left',
        'head_turn_right',
        'hand_to_face',
        'looking_down',
        'looking_up',
        'suspicious_object',
        'normal_behavior'
    ]
    
    current_annotation_idx = 0
    
    import time
    last_frame_time = time.time()
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Calculate actual FPS for monitoring
        current_time = time.time()
        actual_fps = 1.0 / (current_time - last_frame_time) if (current_time - last_frame_time) > 0 else 0
        last_frame_time = current_time
        
        # Write frame if recording
        if recorder.is_recording:
            recorder.write_frame(frame)
            
            # Add recording indicator
            cv2.circle(frame, (30, 30), 10, (0, 0, 255), -1)
            cv2.putText(frame, "REC", (50, 40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Show frame count and time
            time_text = f"Time: {recorder.frame_count / recorder.fps:.2f}s"
            cv2.putText(frame, time_text, (50, 70),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Show current annotation type
        annotation_text = f"Next annotation: {annotation_types[current_annotation_idx]}"
        cv2.putText(frame, annotation_text, (10, frame.shape[0] - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # Display frame
        cv2.imshow('Video Capture - Press SPACE to start/stop', frame)
        
        # Handle keyboard input
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q'):
            if recorder.is_recording:
                recorder.stop_recording()
            break
        elif key == ord(' '):  # Space bar
            if recorder.is_recording:
                recorder.stop_recording()
            else:
                recorder.start_recording(
                    scenario_name=args.scenario,
                    description=args.description,
                    expected_behaviors=[]
                )
        elif key == ord('a') and recorder.is_recording:
            # Add annotation
            behavior = annotation_types[current_annotation_idx]
            recorder.add_annotation(behavior)
        elif key == ord('n'):
            # Next annotation type
            current_annotation_idx = (current_annotation_idx + 1) % len(annotation_types)
            print(f"   Next annotation: {annotation_types[current_annotation_idx]}")
        elif key == ord('p'):
            # Previous annotation type
            current_annotation_idx = (current_annotation_idx - 1) % len(annotation_types)
            print(f"   Next annotation: {annotation_types[current_annotation_idx]}")
    
    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    print("\n✅ Capture tool closed")


if __name__ == "__main__":
    interactive_capture()
