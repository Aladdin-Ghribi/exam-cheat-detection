// script.js
const socket = io(); // Connect to Flask-SocketIO server
const displayCanvas = document.getElementById('displayCanvas');
const displayCtx = displayCanvas.getContext('2d');
const metricsContent = document.getElementById('metrics-content');

// UI elements
const webcamBtn = document.getElementById('webcam-btn');
const fileUploadInput = document.getElementById('file-upload');
const fileInfo = document.getElementById('file-info');
const fileName = document.getElementById('file-name');
const resetBtn = document.getElementById('reset-btn');

let stream = null;
let videoElement = null;
let isProcessing = false;
let lastProcessedTime = 0;
const PROCESS_INTERVAL_MS = 50; // Target ~10 FPS (adjust as needed)
let sourceType = 'webcam'; // 'webcam' or 'file'
let animationFrameId = null;

// --- Start Webcam ---
async function startWebcam() {
  try {
    const constraints = { 
      video: { 
        width: { ideal: 640 },
        height: { ideal: 480 }
      }, 
      audio: false 
    };
    stream = await navigator.mediaDevices.getUserMedia(constraints);

    // Create a hidden video element to capture frames
    videoElement = document.createElement('video');
    videoElement.srcObject = stream;

    // Wait for video to be ready
    videoElement.onloadedmetadata = () => {
      // Ensure canvas dimensions are set correctly
      displayCanvas.width = 640;
      displayCanvas.height = 480;

      // Start processing frames
      processFrame(videoElement);
    };

    videoElement.play();
  } catch (err) {
    console.error('Webcam access denied:', err);
    alert('Camera access required. Please allow and refresh.');
  }
}

// --- Process File (Video or Image) ---
async function processFile(file) {
  // Cancel any ongoing animation frame
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId);
  }

  // Stop webcam if it's running
  if (stream) {
    stream.getTracks().forEach(track => track.stop());
    stream = null;
  }

  // First upload the file to the server
  const formData = new FormData();
  formData.append('file', file);

  try {
    const uploadResponse = await fetch('/upload', {
      method: 'POST',
      body: formData
    });

    const uploadResult = await uploadResponse.json();

    if (!uploadResult.success) {
      throw new Error(uploadResult.error || 'File upload failed');
    }

    const fileType = file.type.split('/')[0]; // 'video' or 'image'

    // Create appropriate element
    if (fileType === 'video') {
      videoElement = document.createElement('video');
      videoElement.src = URL.createObjectURL(file);
      videoElement.play();

      videoElement.onloadedmetadata = () => {
        // Adjust canvas size to match video
        displayCanvas.width = videoElement.videoWidth;
        displayCanvas.height = videoElement.videoHeight;

        // Start processing frames
        processFrame(videoElement);
      };
    } else if (fileType === 'image') {
      // For images, we'll process them on the server
      const processResponse = await fetch('/process_file', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          file_path: uploadResult.file_path,
          file_type: uploadResult.file_type
        })
      });

      const processResult = await processResponse.json();

      if (!processResult.success) {
        throw new Error(processResult.error || 'Image processing failed');
      }

      // Display the processed image
      const img = new Image();
      img.onload = () => {
        // Adjust canvas size to match image
        displayCanvas.width = img.width;
        displayCanvas.height = img.height;

        // Draw processed image on canvas
        displayCtx.drawImage(img, 0, 0);

        // Update metrics
        updateMetrics(processResult.metrics);
      };
      img.src = `data:image/jpeg;base64,${processResult.annotated_frame}`;
    }

    // Update UI
    fileName.textContent = file.name;
    fileInfo.style.display = 'flex';
    webcamBtn.classList.remove('active');

  } catch (error) {
    console.error('Error processing file:', error);
    alert(`Error: ${error.message}`);
    // Reset to webcam on error
    resetToWebcam();
  }
}

// --- Reset to Webcam ---
function resetToWebcam() {
  // Cancel any ongoing animation frame
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId);
  }

  // Stop video if it's playing
  if (videoElement && videoElement.pause) {
    videoElement.pause();
    videoElement.src = '';
  }

  // Reset UI
  fileInfo.style.display = 'none';
  webcamBtn.classList.add('active');
  fileUploadInput.value = '';

  // Reset canvas to default dimensions
  displayCanvas.width = 640;
  displayCanvas.height = 480;

  // Clear the canvas
  displayCtx.clearRect(0, 0, displayCanvas.width, displayCanvas.height);

  // Start webcam
  startWebcam();
}

// --- Capture & Send Frame ---
function processFrame(videoElement) {
  // Check if we have a valid video element
  if (!videoElement || isProcessing) {
    animationFrameId = requestAnimationFrame(() => processFrame(videoElement));
    return;
  }

  // For video elements, check if they're still playing
  if (videoElement.tagName === 'VIDEO' && (videoElement.paused || videoElement.ended)) {
    // If video ended, stop processing
    if (videoElement.ended) {
      console.log('Video playback ended');
      return;
    }
    // If video is paused for some reason, continue checking
    animationFrameId = requestAnimationFrame(() => processFrame(videoElement));
    return;
  }

  const now = Date.now();
  if (now - lastProcessedTime < PROCESS_INTERVAL_MS) {
    animationFrameId = requestAnimationFrame(() => processFrame(videoElement));
    return;
  }

  lastProcessedTime = now;
  isProcessing = true;

  // Create capture canvas
  const captureCanvas = document.createElement('canvas');
  captureCanvas.width = videoElement.videoWidth || videoElement.width || 640;
  captureCanvas.height = videoElement.videoHeight || videoElement.height || 480;
  const captureCtx = captureCanvas.getContext('2d');
  captureCtx.drawImage(videoElement, 0, 0, captureCanvas.width, captureCanvas.height);

  // Convert to base64 and send
  const frameDataUrl = captureCanvas.toDataURL('image/jpeg', 0.85);
  socket.emit('video_frame', frameDataUrl);

  // Schedule next frame
  animationFrameId = requestAnimationFrame(() => processFrame(videoElement));
}

// --- Event Listeners ---
webcamBtn.addEventListener('click', () => {
  if (sourceType !== 'webcam') {
    resetToWebcam();
    sourceType = 'webcam';
  }
});

fileUploadInput.addEventListener('change', (e) => {
  const file = e.target.files[0];
  if (file) {
    processFile(file);
    sourceType = 'file';
  }
});

resetBtn.addEventListener('click', () => {
  resetToWebcam();
  sourceType = 'webcam';
});

// --- Handle Processed Frame from Backend ---
socket.on('processed_frame', (data) => {
  const img = new Image();
  img.onload = () => {
    // Ensure canvas dimensions are correct before drawing
    if (sourceType === 'webcam' && (displayCanvas.width !== 640 || displayCanvas.height !== 480)) {
      displayCanvas.width = 640;
      displayCanvas.height = 480;
    }

    // Draw directly onto display canvas — NO FLICKER
    displayCtx.drawImage(img, 0, 0, displayCanvas.width, displayCanvas.height);
    updateMetrics(data.metrics);
  };
  img.src = `data:image/jpeg;base64,${data.annotated_frame}`;
  isProcessing = false;
});

// --- Update Metrics Panel ---
function updateMetrics(metrics) {
  metricsContent.innerHTML = '';
  if (Object.keys(metrics).length === 0) {
    metricsContent.innerHTML = '<p>No relevant objects detected.</p>';
    return;
  }
  Object.entries(metrics).forEach(([className, count]) => {
    const p = document.createElement('p');
    p.textContent = `${className}: ${count}`;
    metricsContent.appendChild(p);
  });
}

// --- Handle Connection Events ---
socket.on('connect', () => {
  console.log('Connected to server');
  // Start with webcam by default
  sourceType = 'webcam';
  startWebcam();
});

socket.on('disconnect', () => {
  console.log('Disconnected from server');
});

// --- Error Handling ---
socket.on('error', (data) => {
  console.error('Backend error:', data.message);
});