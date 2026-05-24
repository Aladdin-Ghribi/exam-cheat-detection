#!/usr/bin/env python3
"""
Video Replay Script for Exam Cheat Detection Testing
Processes recorded videos through the detection pipeline and generates reports.
"""

import cv2
import json
import os
import sys
import time
from datetime import datetime
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.detection.yolo_detector import YOLODetector
from config import YOLO_MODEL
from src.detection.suspicion_config import load_config


class VideoReplayProcessor:
    def __init__(self, enable_pose=True, enable_tracking=True, enable_seat_mapping=True):
        """
        Initialize video replay processor.
        
        Args:
            enable_pose: Enable pose detection
            enable_tracking: Enable object tracking
            enable_seat_mapping: Enable seat mapping
        """
        print("🔧 Initializing detection pipeline...")
        config = load_config()
        self.detector = YOLODetector(
            enable_pose=enable_pose,
            enable_tracking=enable_tracking,
            enable_seat_mapping=enable_seat_mapping
        )
        self.alert_threshold_percent = float(config.get('suspicion_threshold', 20))
        print("✅ Detection pipeline ready")
        
        self.results = []
        
    def process_video(self, video_path, metadata_path=None, save_output=True, show_preview=False):
        """
        Process a video file through the detection pipeline.
        
        Args:
            video_path: Path to video file
            metadata_path: Path to metadata JSON (optional)
            save_output: Save annotated video output
            show_preview: Show live preview during processing
            
        Returns:
            Dictionary with processing results
        """
        if not os.path.exists(video_path):
            print(f"❌ Video file not found: {video_path}")
            return None
        
        # Load metadata if available
        metadata = None
        if metadata_path and os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
        
        print(f"\n📹 Processing video: {os.path.basename(video_path)}")
        if metadata:
            print(f"   Scenario: {metadata.get('scenario_name', 'Unknown')}")
            print(f"   Description: {metadata.get('description', 'None')}")
            print(f"   Expected behaviors: {', '.join(metadata.get('expected_behaviors', []))}")
        
        # Open video
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"❌ Could not open video: {video_path}")
            return None
        
        # Get video properties
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        print(f"   Resolution: {width}x{height}")
        print(f"   FPS: {fps}")
        print(f"   Total frames: {frame_count}")
        
        # Setup output video if needed
        output_writer = None
        if save_output:
            output_path = video_path.replace('.mp4', '_annotated.mp4')
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            output_writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            print(f"   Output: {output_path}")
        
        # Processing statistics
        frame_idx = 0
        processing_times = []
        detections_per_frame = []
        suspicion_scores = []
        frame_scores = []
        flagged_frames = []
        
        start_time = time.time()
        
        print("\n⏳ Processing frames...")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_start = time.time()
            
            # Process frame through detection pipeline
            detection_result = self.detector.detect_frame(frame)
            
            # Extract statistics
            detections = detection_result['detections']
            detections_per_frame.append(len(detections))
            
            # Get max suspicion score
            max_raw_suspicion = 0
            max_smoothed_suspicion = 0
            for det in detections:
                if 'behavior' in det and 'suspicion' in det['behavior']:
                    suspicion = det['behavior']['suspicion']
                    raw_score = suspicion.get('raw', 0)
                    smoothed_score = suspicion.get('smoothed', 0)
                    max_raw_suspicion = max(max_raw_suspicion, raw_score)
                    max_smoothed_suspicion = max(max_smoothed_suspicion, smoothed_score)

            suspicion_scores.append(max_smoothed_suspicion)
            frame_scores.append({
                'frame': frame_idx,
                'timestamp': frame_idx / fps,
                'raw_suspicion_score': max_raw_suspicion * 100,
                'smoothed_suspicion_score': max_smoothed_suspicion * 100,
                'detections': len(detections)
            })
            
            # Check if frame should be flagged
            if max_smoothed_suspicion * 100 >= self.alert_threshold_percent:  # Threshold from config
                flagged_frames.append({
                    'frame': frame_idx,
                    'timestamp': frame_idx / fps,
                    'suspicion_score': max_smoothed_suspicion * 100,
                    'detections': len(detections)
                })
            
            # Annotate frame
            # Use smoothed suspicion as the displayed max suspicion
            max_suspicion = max_smoothed_suspicion
            annotated_frame = self.detector.draw_detections(frame, detection_result)
            
            # Add frame info
            cv2.putText(annotated_frame, f"Frame: {frame_idx}/{frame_count}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(annotated_frame, f"Max Suspicion: {max_suspicion*100:.1f}", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Save to output video
            if output_writer:
                output_writer.write(annotated_frame)
            
            # Show preview
            if show_preview:
                cv2.imshow('Video Replay - Press Q to stop', annotated_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            
            # Track processing time
            processing_times.append(time.time() - frame_start)
            frame_idx += 1
            
            # Progress indicator
            if frame_idx % 30 == 0:
                progress = (frame_idx / frame_count) * 100
                avg_time = sum(processing_times[-30:]) / min(30, len(processing_times))
                print(f"   Progress: {progress:.1f}% | Avg time: {avg_time*1000:.1f}ms/frame")
        
        # Cleanup
        cap.release()
        if output_writer:
            output_writer.release()
        if show_preview:
            cv2.destroyAllWindows()
        
        total_time = time.time() - start_time
        
        # Compile results
        result = {
            'video_path': video_path,
            'metadata': metadata,
            'processing_stats': {
                'total_frames': frame_idx,
                'total_time_seconds': total_time,
                'avg_fps': frame_idx / total_time if total_time > 0 else 0,
                'avg_processing_time_ms': (sum(processing_times) / len(processing_times)) * 1000 if processing_times else 0,
                'min_processing_time_ms': min(processing_times) * 1000 if processing_times else 0,
                'max_processing_time_ms': max(processing_times) * 1000 if processing_times else 0
            },
            'detection_stats': {
                'total_detections': sum(detections_per_frame),
                'avg_detections_per_frame': sum(detections_per_frame) / len(detections_per_frame) if detections_per_frame else 0,
                'max_detections_per_frame': max(detections_per_frame) if detections_per_frame else 0
            },
            'suspicion_stats': {
                'avg_suspicion_score': (sum(suspicion_scores) / len(suspicion_scores)) * 100 if suspicion_scores else 0,
                'max_suspicion_score': max(suspicion_scores) * 100 if suspicion_scores else 0,
                'flagged_frames_count': len(flagged_frames),
                'flagged_frames': flagged_frames
            },
            'frame_scores': frame_scores,
            'evaluation': {
                'threshold_percent': self.alert_threshold_percent,
                'score_mode': 'smoothed'
            }
        }
        
        print(f"\n✅ Processing complete!")
        print(f"   Total time: {total_time:.2f}s")
        print(f"   Average FPS: {result['processing_stats']['avg_fps']:.2f}")
        print(f"   Average processing time: {result['processing_stats']['avg_processing_time_ms']:.2f}ms/frame")
        print(f"   Flagged frames: {len(flagged_frames)}")
        
        return result
    
    def process_batch(self, video_dir, output_report_path=None):
        """
        Process all videos in a directory.
        
        Args:
            video_dir: Directory containing videos
            output_report_path: Path to save batch report
            
        Returns:
            List of processing results
        """
        video_files = list(Path(video_dir).glob('*.mp4'))
        # Exclude annotated videos
        video_files = [v for v in video_files if '_annotated' not in str(v)]
        
        if not video_files:
            print(f"❌ No video files found in {video_dir}")
            return []
        
        print(f"\n📦 Batch processing {len(video_files)} videos...")
        
        results = []
        for video_path in video_files:
            metadata_path = str(video_path).replace('.mp4', '_metadata.json')
            result = self.process_video(
                str(video_path),
                metadata_path if os.path.exists(metadata_path) else None,
                save_output=True,
                show_preview=False
            )
            if result:
                results.append(result)
        
        # Generate batch report
        if output_report_path and results:
            report = {
                'timestamp': datetime.now().isoformat(),
                'total_videos': len(results),
                'summary': {
                    'avg_fps': sum(r['processing_stats']['avg_fps'] for r in results) / len(results),
                    'avg_processing_time_ms': sum(r['processing_stats']['avg_processing_time_ms'] for r in results) / len(results),
                    'total_flagged_frames': sum(r['suspicion_stats']['flagged_frames_count'] for r in results)
                },
                'videos': results
            }
            
            with open(output_report_path, 'w') as f:
                json.dump(report, f, indent=2)
            
            print(f"\n📊 Batch report saved: {output_report_path}")
            print(f"   Average FPS: {report['summary']['avg_fps']:.2f}")
            print(f"   Average processing time: {report['summary']['avg_processing_time_ms']:.2f}ms")
            print(f"   Total flagged frames: {report['summary']['total_flagged_frames']}")
        
        return results


def main():
    parser = argparse.ArgumentParser(description='Replay test videos through detection pipeline')
    parser.add_argument('input', type=str,
                       help='Video file or directory to process')
    parser.add_argument('--batch', action='store_true',
                       help='Process all videos in directory')
    parser.add_argument('--no-pose', action='store_true',
                       help='Disable pose detection')
    parser.add_argument('--no-tracking', action='store_true',
                       help='Disable object tracking')
    parser.add_argument('--no-seat-mapping', action='store_true',
                       help='Disable seat mapping')
    parser.add_argument('--no-output', action='store_true',
                       help='Do not save annotated video')
    parser.add_argument('--preview', action='store_true',
                       help='Show live preview during processing')
    parser.add_argument('--report', type=str,
                       help='Path to save batch report (JSON)')
    
    args = parser.parse_args()
    
    # Initialize processor
    processor = VideoReplayProcessor(
        enable_pose=not args.no_pose,
        enable_tracking=not args.no_tracking,
        enable_seat_mapping=not args.no_seat_mapping
    )
    
    if args.batch:
        # Batch processing
        report_path = args.report or os.path.join(args.input, 'batch_report.json')
        processor.process_batch(args.input, report_path)
    else:
        # Single video processing
        metadata_path = args.input.replace('.mp4', '_metadata.json')
        result = processor.process_video(
            args.input,
            metadata_path if os.path.exists(metadata_path) else None,
            save_output=not args.no_output,
            show_preview=args.preview
        )
        
        # Save individual report
        if result and args.report:
            # Ensure destination directory exists
            report_path = Path(args.report)
            if not report_path.parent.exists():
                report_path.parent.mkdir(parents=True, exist_ok=True)
            with open(report_path, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"\n📊 Report saved: {args.report}")


if __name__ == "__main__":
    main()
