import streamlit as st
import os

st.set_page_config(page_title="Cheating Detection Dashboard", layout="wide")
st.title("🔍 Real-Time Cheating Detection System")
st.subheader("Week 2 – Raw Detections")

# Display raw detection if available
detection_path = "output/raw_detections/raw_detection.jpg"
if os.path.exists(detection_path):
    st.image(detection_path, caption="Raw YOLO Detections", use_column_width=True)
else:
    st.info("📁 Raw detections will appear here once saved to: output/raw_detections/raw_detection.jpg")

# Show folder structure (fulfills "organize saved frames folder")
st.markdown("### 📁 Output Folder (Week 2)")
st.code("""
output/
└── raw_detections/   # ← Organized for temporary detection frames
""")