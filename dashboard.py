import streamlit as st
import os

st.set_page_config(page_title="Cheating Detection Dashboard", layout="wide")

st.title("🔍 Real-Time Cheating Detection System")
st.subheader("Instructor Dashboard – Week 2: Raw Detections")

# Sidebar control
with st.sidebar:
    st.header("Controls")
    show_detections = st.checkbox("Show Raw Detections", value=True)

# Main layout
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📹 Input Feed")
    st.image("https://placehold.co/640x480?text=Raw+Camera+Feed", use_column_width=True)

with col2:
    st.markdown("### 📦 Raw Detections (Week 2)")
    if show_detections:
        detection_path = "output/smoke_test_result.jpg"
        if os.path.exists(detection_path):
            st.image(detection_path, caption="YOLO Detections (Persons, Objects)", use_column_width=True)
        else:
            st.warning("⚠️ Run `python src/detection/yolo_smoke_test.py` to generate a detection preview.")
    else:
        st.info("Toggle 'Show Raw Detections' to view bounding boxes.")

# Show output folder structure
st.divider()
st.markdown("### 📁 Output Folder Structure (Week 2)")
st.code("""
output/
├── smoke_test_result.jpg       # ← From Week 1 smoke test
└── raw_detections/             # ← For Week 2+ temporary frames
""")

# Status
st.success("✅ Week 2 – Dev B: UI ready to display raw detections. Folder structure organized.")