// script.js
const socket = io(); // Connect to Flask-SocketIO server
const displayCanvas = document.getElementById('displayCanvas');
const displayCtx = displayCanvas.getContext('2d');
const metricsContent = document.getElementById('metrics-content');

let stream = null;
let isProcessing = false;
let lastProcessedTime = 0;
const PROCESS_INTERVAL_MS = 50; // Target ~10 FPS (adjust as needed)

// --- Start Webcam ---
async function startWebcam() {
  try {
    const constraints = { video: true, audio: false };
    stream = await navigator.mediaDevices.getUserMedia(constraints);

    // Create a hidden video element to capture frames
    const hiddenVideo = document.createElement('video');
    hiddenVideo.srcObject = stream;
    hiddenVideo.play();

    // Start processing frames
    processFrame(hiddenVideo);
  } catch (err) {
    console.error('Webcam access denied:', err);
    alert('Camera access required. Please allow and refresh.');
  }
}

// --- Capture & Send Frame ---
function processFrame(videoElement) {
  if (!stream || isProcessing) {
    requestAnimationFrame(() => processFrame(videoElement));
    return;
  }

  const now = Date.now();
  if (now - lastProcessedTime < PROCESS_INTERVAL_MS) {
    requestAnimationFrame(() => processFrame(videoElement));
    return;
  }

  lastProcessedTime = now;
  isProcessing = true;

  // Create capture canvas
  const captureCanvas = document.createElement('canvas');
  captureCanvas.width = videoElement.videoWidth || 640;
  captureCanvas.height = videoElement.videoHeight || 480;
  const captureCtx = captureCanvas.getContext('2d');
  captureCtx.drawImage(videoElement, 0, 0, captureCanvas.width, captureCanvas.height);

  // Convert to base64 and send
  const frameDataUrl = captureCanvas.toDataURL('image/jpeg', 0.85);
  socket.emit('video_frame', frameDataUrl);

  // Schedule next frame
  requestAnimationFrame(() => processFrame(videoElement));
}

// --- Handle Processed Frame from Backend ---
socket.on('processed_frame', (data) => {
  const img = new Image();
  img.onload = () => {
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
  startWebcam();
});

socket.on('disconnect', () => {
  console.log('Disconnected from server');
});

// --- Error Handling ---
socket.on('error', (data) => {
  console.error('Backend error:', data.message);
});