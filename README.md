# Real-Time Cheating Detection System for Exams

A real-time computer vision system that detects cheating behaviors during exams using **YOLO**, **MediaPipe**, and **head orientation analysis** — with **no audio or biometric data**.

## Objectives
- Detect cheating behaviors in real-time using only visual input
- Provide interpretable alerts with visual and textual explanations
- Reduce manual supervision during exams by automating monitoring
- Store flagged events with snapshots and metadata for instructor review
- Minimize false positives using temporal smoothing and multi-signal fusion
- Ensure privacy by retaining only flagged frames and deleting non-events

## Team
- **Dev A:** Aladdin Ghribi  
- **Dev B:** Malak Khalaf  

## Week 1 Status — ✅ Complete
- **Dev A:** Initialize repo, folder structure, config.py, YOLO smoke script  
- **Dev B:** Create GitHub Project board, README, Streamlit placeholder, verify environment setup  

## Project Board
(https://github.com/users/Aladdin-Ghribi/projects/1)

---

## Setup Instructions

### Prerequisites
- Python 3.8+
- Git
- Webcam or video file for testing

### Installation
```powershell
git clone https://github.com/Aladdin-Ghribi/exam-cheat-detection.git
cd exam-cheat-detection
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run Smoke Test
```powershell
python src/detection/yolo_smoke_test.py
```

## Run Dashboard
```powershell
streamlit run dashboard.py
```

## Expected Results(Week 13)
- Live prototype with bounding boxes, keypoints, and head angles
- Alerting system with visual and textual explanations
- Searchable event logs with snapshots and metadata
- Instructor dashboard with seat map and filtering
- Labeled test dataset and evaluation report
- Final delivery package with documentation and demo materials

## Resources
- Software: Python, PyTorch, Ultralytics YOLO, MediaPipe, OpenCV, Flask
- Hardware: Laptop with 16GB+ RAM,  GPU, webcam or CCTV feed
- Privacy: Save only flagged frames, auto-delete non-events, restrict access to evidence
