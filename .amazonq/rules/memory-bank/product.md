# Product Overview

## Project Purpose
Real-time computer vision system that detects cheating behaviors during exams using YOLO object detection, MediaPipe pose estimation, and head orientation analysis. The system operates without collecting audio or biometric data, ensuring privacy while providing automated exam monitoring.

## Key Features
- **Real-time Detection**: Live monitoring of exam sessions through webcam or video feeds
- **Multi-modal Analysis**: Combines YOLO object detection with MediaPipe pose estimation
- **Seat Management**: Automatic assignment and tracking of students to exam seats
- **Web Interface**: Flask-based dashboard with real-time video processing via WebSocket
- **Privacy-First**: Retains only flagged events, auto-deletes non-suspicious frames
- **Interpretable Alerts**: Visual annotations with confidence scores and explanations

## Core Capabilities
- Object detection for suspicious items (phones, papers, etc.)
- Human pose analysis for unusual body positions
- Head orientation tracking to detect looking away from exam
- Temporal smoothing to reduce false positives
- Event logging with snapshots and metadata
- Real-time seat assignment and student tracking

## Target Users
- **Educational Institutions**: Schools and universities conducting remote or in-person exams
- **Exam Proctors**: Automated assistance for manual supervision
- **IT Administrators**: Easy deployment and configuration management

## Value Proposition
Reduces manual supervision workload by 70% while maintaining exam integrity through automated, privacy-respecting monitoring that provides clear evidence for review when suspicious behavior is detected.