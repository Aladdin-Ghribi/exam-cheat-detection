"""
Testing tools for Exam Cheat Detection System.
Provides video capture and replay utilities for consistent testing.
"""

from .video_capture import VideoCaptureRecorder
from .video_replay import VideoReplayProcessor

__all__ = ['VideoCaptureRecorder', 'VideoReplayProcessor']
