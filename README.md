<div align="center">
  <img width="883" height="300" alt="image" src="https://github.com/user-attachments/assets/6d46949a-bb22-4eb4-9686-65497d4d6272" />

</div>




![Project Status](https://img.shields.io/badge/Status-Week%2011%20Complete-success?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![YOLO](https://img.shields.io/badge/YOLO-Ultralytics-orange?style=for-the-badge)
![MediaPipe](https://img.shields.io/badge/MediaPipe-Google-green?style=for-the-badge)

> **A privacy-first, real-time computer vision system tailored for in-hall exam monitoring.**

This project uses **YOLOv11** and **MediaPipe** to detect suspicious behaviors (phones, multiple people, looking away) without recording audio or processing biometric templates.

---

##  Demo Preview

<!-- PLACEHOLDER: Replace this image with a GIF of your system in action! -->
<img width="508" height="243" alt="Screenshot 2025-12-14 192405" src="https://github.com/user-attachments/assets/0b822cbc-edf7-48ef-bedb-e2b9e01bbd53" />



---

##  Objectives
*   **👁️ Visual-Only Monitoring**: No audio scraping or invasive biometrics.
*   **⚡ Real-Time Alerts**: Instant feedback on suspicious activities.
*   **🛡️ Privacy First**: Only flagged frames are stored; everything else is discarded.
*   **📊 Instructor Dashboard**: Review timeline of events with evidence snapshots.

---

##  Tech Stack

| Component | Technology | Use Case |
| :--- | :--- | :--- |
| **Detection** | YOLOv11 | Object detection (Phones, People) |
| **Pose/Face** | MediaPipe | Head orientation, hand tracking |
| **Backend** | Flask/Python & OpenCV | Core processing pipeline |
| **Frontend** | JS/HTML/CSS | Proctor Dashboard & Analytics |
| **Log** | JSON | Metadata storage |

---

##  How It Works

```mermaid
graph TD
    A[Webcam Feed] --> B{Detection Engine}
    B -->|YOLO| C["Detect Objects<br>(Phone, Person)"]
    B -->|MediaPipe| D["Analyze Pose<br>(Head Angle, Hands)"]
    C --> E[Fusion Logic]
    D --> E
    E -->|Safe| F[Discard Frame]
    E -->|Suspicious| G[Trigger Alert]
    G --> H[Save Snapshot]
    G --> I[Notify Dashboard]
```

---

##  Setup & Installation

### Prerequisites
*   Python 3.8+
*   Git
*   Webcam

### Quick Start
```powershell
# 1. Clone the repository
git clone https://github.com/Aladdin-Ghribi/exam-cheat-detection.git
cd exam-cheat-detection

# 2. Create Virtual Environment
python -m venv venv
venv\Scripts\Activate.ps1

# 3. Install Dependencies
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements_stable.txt
```

**4. Launch Dashboard**
```
python .\start_app.py
```

---

##  Project Status (Week 11)

✅ **Current Milestone**: Week 1 - 11 Complete
🔜 **Next Up (Week 13)**: Full alert integration & final polish.

---

## 🔗 Project Board
[View Progress on GitHub Projects](https://github.com/users/Aladdin-Ghribi/projects/1)
