import streamlit as st

st.set_page_config(page_title="Cheating Detection Dashboard", layout="wide")

st.title("🔍 Real-Time Cheating Detection System")
st.subheader("Instructor Dashboard – Week 1 Placeholder")

st.success("✅ Environment verified | 📦 YOLO smoke test passed | 🎛️ Ready for development")

st.markdown("""
### Project Goals
- Detect suspicious behaviors (looking away, hand-to-face, unauthorized objects)
- Provide interpretable alerts with visual + textual explanations
- Store only flagged frames (privacy by design)
- Run in real-time on standard laptops

### Week 1 Status
- Dev A: Repo initialized, YOLO smoke test ✅  
- Dev B: Environment verified, README, Streamlit placeholder ✅

> Next: Person tracking, pose estimation, head orientation, and scoring logic.
""")

st.write("💡 This is a Week 1 placeholder. The live dashboard will be built incrementally through Week 13.")