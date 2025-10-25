// script.js
const socket = io(); // Connect to the Socket.IO server

const videoElement = document.getElementById('videoElement');
const canvasElement = document.getElementById('canvasElement');
const metricsContent = document.getElementById('metrics-content');
const ctx = canvasElement.getContext('2d');

let stream = null;
let isProcessing = false; // Prevent overlapping processing calls

// Function to start the webcam
async function startWebcam() {
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    videoElement.srcObject = stream;
    console.log("Webcam access granted.");
  } catch (err) {
    console.error("Error accessing webcam: ", err);
    alert("Could not access the webcam. Please check permissions and try again.");
  }
}

/// script.js
// ... (existing code)

// ... (existing code in script.js)

let lastProcessedTime = 0;
// Adjust this value (milliseconds) to control the target processing rate
// e.g., 100ms = ~10 FPS, 66ms = ~15 FPS, 50ms = ~20 FPS
// Start with a conservative value and adjust based on your system's performance.
const PROCESS_INTERVAL_MS = 100;

// Function to capture frame, process, and send via WebSocket
function processFrame() {
  if (!stream || isProcessing) return;

  const now = Date.now();
  // Only proceed if enough time has passed since the last processed frame
  if (now - lastProcessedTime < PROCESS_INTERVAL_MS) {
    // Skip this frame, schedule the next check
    requestAnimationFrame(processFrame);
    return;
  }

  // Mark the time *before* starting processing
  lastProcessedTime = now;
  isProcessing = true; // Prevent overlapping processing calls

  // Set canvas dimensions to match video
  canvasElement.width = videoElement.videoWidth;
  canvasElement.height = videoElement.videoHeight;

  // Draw current video frame onto the hidden canvas
  ctx.drawImage(videoElement, 0, 0, canvasElement.width, canvasElement.height);

  // Convert canvas content to base64 JPEG data URL
  const frameDataUrl = canvasElement.toDataURL('image/jpeg', 0.8); // Adjust quality (0.8) as needed

  // Send the frame data to the backend via WebSocket
  socket.emit('video_frame', frameDataUrl);

  // Schedule the *next* attempt to process a frame
  // This happens *after* sending the current one.
  requestAnimationFrame(processFrame);
  // Note: The actual processing result comes back asynchronously via the 'processed_frame' event handler.
  // The isProcessing flag helps prevent sending new frames while waiting for the backend.
}

// Update the 'processed_frame' handler to reset the flag
socket.on('processed_frame', function (data) {
  // Update the video element with the annotated frame received from the backend
  videoElement.src = 'data:image/jpeg;base64,' + data.annotated_frame;

  // Update metrics display
  updateMetrics(data.metrics);

  // Crucially, reset the flag *after* handling the result
  // This allows the processFrame loop to send the next frame once this one is handled.
  // isProcessing = false; // This line might be better placed here if it refers to the *sending* part being done
  // Actually, resetting it here means the *next* frame capture can start immediately after this handler finishes,
  // potentially overlapping if the next processFrame call happens before the backend gets the *previous* frame.
  // The safest place is probably right before socket.emit, but let's keep it simple for now.
  // The 'isProcessing = true' happens at the start of processFrame, and 'isProcessing = false' happens here.
  // This ensures only one frame is sent at a time.
  isProcessing = false; // Mark that we have finished processing the *previous* frame's result/sending cycle
});

// ... (rest of existing code)

// Listen for connection events
socket.on('connect', function () {
  console.log('Connected to server via Socket.IO');
  startWebcam(); // Start webcam when connected
});

socket.on('disconnect', function () {
  console.log('Disconnected from server');
});

// Function to update metrics display
function updateMetrics(metrics) {
  metricsContent.innerHTML = ''; // Clear previous metrics

  if (Object.keys(metrics).length === 0) {
    metricsContent.innerHTML = '<p>No relevant objects detected.</p>';
    return;
  }

  for (const [className, count] of Object.entries(metrics)) {
    const p = document.createElement('p');
    p.textContent = `${className}: ${count}`;
    metricsContent.appendChild(p);
  }
}

// Optional: Listen for errors from the backend
socket.on('error', function (data) {
  console.error('Backend error:', data.message);
  // Display error message to user if needed
  // alert('An error occurred: ' + data.message);
});

// Start processing frames after the video element loads its metadata
videoElement.addEventListener('loadedmetadata', function () {
  // Adjust canvas size initially
  canvasElement.width = videoElement.videoWidth;
  canvasElement.height = videoElement.videoHeight;
  // Begin the processing loop
  processFrame();
});