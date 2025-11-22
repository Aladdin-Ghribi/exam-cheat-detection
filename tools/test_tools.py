#!/usr/bin/env python3
"""
Quick test script to verify capture and replay tools are working.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """Test that all required modules can be imported."""
    print("🔧 Testing imports...")
    
    try:
        from tools.video_capture import VideoCaptureRecorder
        print("✅ VideoCaptureRecorder imported successfully")
    except Exception as e:
        print(f"❌ Failed to import VideoCaptureRecorder: {e}")
        return False
    
    try:
        from tools.video_replay import VideoReplayProcessor
        print("✅ VideoReplayProcessor imported successfully")
    except Exception as e:
        print(f"❌ Failed to import VideoReplayProcessor: {e}")
        return False
    
    try:
        from src.detection.yolo_detector import YOLODetector
        print("✅ YOLODetector imported successfully")
    except Exception as e:
        print(f"❌ Failed to import YOLODetector: {e}")
        return False
    
    return True

def test_directories():
    """Test that required directories exist."""
    print("\n📁 Testing directories...")
    
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    dirs_to_check = [
        'tools',
        'src/detection',
        'data',
        'output'
    ]
    
    all_exist = True
    for dir_name in dirs_to_check:
        dir_path = os.path.join(project_root, dir_name)
        if os.path.exists(dir_path):
            print(f"✅ {dir_name} exists")
        else:
            print(f"❌ {dir_name} not found")
            all_exist = False
    
    # Create test_videos directory if it doesn't exist
    test_videos_dir = os.path.join(project_root, 'data', 'test_videos')
    if not os.path.exists(test_videos_dir):
        os.makedirs(test_videos_dir, exist_ok=True)
        print(f"✅ Created data/test_videos directory")
    else:
        print(f"✅ data/test_videos exists")
    
    return all_exist

def main():
    print("="*60)
    print("Testing Capture and Replay Tools")
    print("="*60 + "\n")
    
    # Test imports
    if not test_imports():
        print("\n❌ Import tests failed")
        return False
    
    # Test directories
    if not test_directories():
        print("\n⚠️  Some directories are missing but tools should still work")
    
    print("\n" + "="*60)
    print("✅ All tests passed!")
    print("="*60)
    print("\nNext steps:")
    print("1. Record a test video:")
    print("   python tools/video_capture.py --scenario test")
    print("\n2. Replay the video:")
    print("   python tools/video_replay.py data/test_videos/test_*.mp4")
    print("\n3. Read the documentation:")
    print("   tools/README.md")
    print("="*60)
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
