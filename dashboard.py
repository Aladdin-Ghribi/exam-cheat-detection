# streamlit_dashboard_simple.py
import streamlit as st
from streamlit_webrtc import VideoTransformerBase, webrtc_streamer
import av
import tempfile
import os
import sys
import cv2 # Need cv2 for drawing and resizing

# Adjust path if necessary to import your YoloDetector
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.detection.yolo_detector import YOLODetector

# --- Configuration for Display Size ---
# Define a standard size for display (width, height)
# If the original image is larger than this, it will be resized down, maintaining aspect ratio
# If smaller, it might be displayed as-is or potentially upscaled (OpenCV handles this based on interpolation)
STANDARD_DISPLAY_WIDTH = 640  # Adjust as needed
STANDARD_DISPLAY_HEIGHT = 480 # Adjust as needed

def resize_image_maintain_aspect(image, target_width, target_height):
    """Resizes an image to fit within target dimensions, maintaining aspect ratio."""
    h, w = image.shape[:2]
    scale = min(target_width / w, target_height / h)
    if scale < 1.0: # Only resize down if the image is larger than target
        new_w = int(w * scale)
        new_h = int(h * scale)
        # Use INTER_AREA for shrinking (good quality)
        resized_img = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        return resized_img
    else:
        # If image is smaller than target, return as is or resize up (INTER_CUBIC or INTER_LINEAR for upscaling)
        # Returning as is for now to avoid upscaling potentially low-res images unnecessarily.
        # If upscaling small images is desired, uncomment the next lines:
        # new_w = int(w * scale)
        # new_h = int(h * scale)
        # resized_img = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        # return resized_img
        return image # Return original if no downscaling is needed

# --- Video Transformer Class for Detection ---
class YOLOVideoProcessor(VideoTransformerBase):
    def __init__(self):
        # Initialize your detector here
        self.detector = YOLODetector() # Uses model, IMG_SIZE, CONFIDENCE_THRESHOLD from config.py

    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        # This method is called for each frame received from the input source
        # (e.g., file, webcam - configured in the webrtc_streamer call)

        # Get the numpy array (image) from the av.VideoFrame
        img_rgb = frame.to_ndarray(format="rgb24")

        # --- Run your detection logic on the single frame 'img_rgb' ---
        results = self.detector.model(img_rgb, verbose=False) # Run inference (expects RGB/BGR, handles internally)

        # Process the results for this frame
        detections = []
        if results[0].boxes is not None:
             for box, cls_id_tensor, conf_tensor in zip(results[0].boxes.xyxy, results[0].boxes.cls, results[0].boxes.conf):
                cls_id = int(cls_id_tensor)
                conf = float(conf_tensor)
                x1, y1, x2, y2 = box.tolist()
                # Filter based on target class IDs
                if cls_id in self.detector.target_class_ids:
                    detections.append({
                        'class_id': cls_id,
                        'confidence': conf,
                        'bbox': [x1, y1, x2, y2]
                    })

        # --- Draw detections on the image (converted to BGR for cv2) ---
        img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
        for det in detections:
            # The bbox coordinates are in absolute pixel values (x1, y1, x2, y2)
            x1, y1, x2, y2 = map(int, det['bbox'])
            label = f"{self.detector.model.names[det['class_id']]} {det['confidence']:.2f}"
            color = (0, 255, 0) # BGR Green
            cv2.rectangle(img_bgr, (x1, y1), (x2, y2), color, 2)
            # Calculate text size for background
            (text_width, text_height), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
            cv2.rectangle(img_bgr, (x1, y1 - text_height - baseline), (x1 + text_width, y1), color, thickness=cv2.FILLED)
            cv2.putText(img_bgr, label, (x1, y1 - baseline), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2) # Black text in BGR

        # Convert back to RGB for the output frame
        img_with_boxes_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

        # --- Resize the processed image for standard display size ---
        img_with_boxes_resized = resize_image_maintain_aspect(img_with_boxes_rgb, STANDARD_DISPLAY_WIDTH, STANDARD_DISPLAY_HEIGHT)

        # The processed and resized image 'img_with_boxes_resized' is returned as an av.VideoFrame
        processed_frame = av.VideoFrame.from_ndarray(img_with_boxes_resized, format="rgb24") # Specify output format
        return processed_frame

# --- Streamlit App ---
def main():
    st.set_page_config(page_title="Simple Media Dashboard", layout="wide")
    st.title("🖼️ Simple Media Display Dashboard")
    st.subheader("Select and View Media with YOLO Detections (Standard Size)")

    # --- Source Selection ---
    source_type = st.radio("Choose Source Type:", ("Image File", "Video File")) # Removed "Webcam" for simplicity with st.image/st.video

    source = None
    if source_type == "Image File":
        uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])
        if uploaded_file is not None:
            # Save uploaded file temporarily
            tfile = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1])
            tfile.write(uploaded_file.read())
            source = tfile.name
            tfile.close()
    elif source_type == "Video File":
        uploaded_file = st.file_uploader("Choose a video...", type=["mp4", "mov", "avi", "mkv"])
        if uploaded_file is not None:
            # Save uploaded file temporarily
            tfile = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1])
            tfile.write(uploaded_file.read())
            source = tfile.name
            tfile.close()

    # --- Display Media ---
    if source:
        st.subheader(f"Displaying: {source_type}")
        if source_type == "Image File":
            # For images, we can show original and processed separately
            # Read the image
            img_orig_bgr = cv2.imread(source)
            if img_orig_bgr is not None:
                # Convert BGR to RGB for Streamlit
                img_orig_rgb = cv2.cvtColor(img_orig_bgr, cv2.COLOR_BGR2RGB)

                # --- Resize Original Image ---
                img_orig_resized = resize_image_maintain_aspect(img_orig_rgb, STANDARD_DISPLAY_WIDTH, STANDARD_DISPLAY_HEIGHT)

                # Process the *resized* original image (or the original if smaller, depending on your choice in resize_image_maintain_aspect)
                # It's often better to run detection on the original resolution and then resize the annotated output,
                # but for display consistency, resizing input is also an option.
                # Let's run detection on the *original* image and then resize the annotated version.
                detector = YOLODetector()
                # Run model inference on the single original image array (RGB)
                results = detector.model(img_orig_rgb, verbose=False) # Input is RGB

                # Process results
                detections = []
                if results[0].boxes is not None:
                     for box, cls_id_tensor, conf_tensor in zip(results[0].boxes.xyxy, results[0].boxes.cls, results[0].boxes.conf):
                        cls_id = int(cls_id_tensor)
                        conf = float(conf_tensor)
                        x1, y1, x2, y2 = box.tolist()
                        if cls_id in detector.target_class_ids:
                            detections.append({
                                'class_id': cls_id,
                                'confidence': conf,
                                'bbox': [x1, y1, x2, y2]
                            })

                # Draw detections on the *original* BGR image (before resizing annotations)
                img_annotated_bgr = img_orig_bgr.copy() # Work on BGR copy for cv2
                for det in detections:
                    x1, y1, x2, y2 = map(int, det['bbox'])
                    label = f"{detector.model.names[det['class_id']]} {det['confidence']:.2f}"
                    color = (0, 255, 0) # BGR Green
                    cv2.rectangle(img_annotated_bgr, (x1, y1), (x2, y2), color, 2)
                    # Calculate text size for background
                    (text_width, text_height), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                    cv2.rectangle(img_annotated_bgr, (x1, y1 - text_height - baseline), (x1 + text_width, y1), color, thickness=cv2.FILLED)
                    cv2.putText(img_annotated_bgr, label, (x1, y1 - baseline), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2) # Black text

                # Convert annotated image back to RGB for Streamlit
                img_annotated_rgb = cv2.cvtColor(img_annotated_bgr, cv2.COLOR_BGR2RGB)

                # --- Resize Annotated Image ---
                img_annotated_resized = resize_image_maintain_aspect(img_annotated_rgb, STANDARD_DISPLAY_WIDTH, STANDARD_DISPLAY_HEIGHT)

                # Display side-by-side
                col1, col2 = st.columns(2)
                with col1:
                    st.image(img_orig_resized, caption="Original Image (Resized)", use_column_width=True) # use_column_width helps fit the container
                with col2:
                    st.image(img_annotated_resized, caption="YOLO Detections (Resized)", use_column_width=True) # use_column_width helps fit the container


        elif source_type == "Video File":
            # For videos, use streamlit-webrtc to process and display frames live
            # The YOLOVideoProcessor now handles resizing *after* detection/drawing.
            st.write("Playing video with YOLO detections (processed & resized stream):")
            webrtc_ctx = webrtc_streamer(
                key=f"video_with_detection_resized_{source}", # Unique key for the streamer instance
                video_processor_factory=YOLOVideoProcessor,
                media_stream_constraints={"video": True, "audio": False}, # Enable video, disable audio
                async_processing=True, # Recommended for performance
            )

            if webrtc_ctx.state.playing:
                 st.info("Processing and displaying video stream with YOLO detections (resized).")
            else:
                 st.warning("WebRTC stream is not active. The video file might require offline processing for detection display.")


        # Optional: Clean up the temporary file after displaying (or let it persist until script rerun)
        # os.unlink(source) # Uncomment if you want to delete immediately after display attempt

    else:
        st.info("Please select a source type and upload a file.")

if __name__ == "__main__":
    main()