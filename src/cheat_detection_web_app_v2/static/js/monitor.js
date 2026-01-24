// Monitor Page - Session Management and Alert Handling with WebSocket Integration

// ============================================
// SOCKET.IO CONNECTION
// ============================================

let socket = null;

function initSocket() {
  if (socket && socket.connected) return;

  socket = io();

  socket.on('connect', () => {
    console.log('Connected to server');
  });

  socket.on('disconnect', () => {
    console.log('Disconnected from server');
  });

  socket.on('session_started', (session) => {
    console.log('Session started:', session);
    activeSession = session;
  });

  socket.on('session_stopped', (session) => {
    console.log('Session stopped:', session);
  });

  socket.on('processed_frame', (data) => {
    // Cache detection data for client-side rendering
    if (data.detections) {
      lastDetections = data.detections;
    }

    // Update pipeline speed
    if (data.performance_stats) {
      const pipelineMs = data.performance_stats?.last_process_time_ms || 0;
      updatePipelineSpeed(Math.round(pipelineMs));
    }
  });

  socket.on('new_alert', (alert) => {
    console.log('New alert received:', alert);
    handleNewAlert(alert);
  });

  socket.on('review_result', (result) => {
    console.log('Review result:', result);
    if (result.success) {
      showNotification('Success', result.message);
    } else {
      showNotification('Error', result.error);
    }
  });

  socket.on('pending_alerts_list', (data) => {
    pendingAlerts = data.alerts || [];
    renderAlerts();
  });

  socket.on('alert_removed', (data) => {
    // Remove cleaned-up duplicate alert from UI
    console.log('Alert removed:', data.alert_id);
    pendingAlerts = pendingAlerts.filter(a => a.event_id !== data.alert_id && a.alert_id !== data.alert_id);
    renderAlerts();
  });

  // Listen for config updates (when settings change)
  socket.on('config_updated', (config) => {
    if (config.show_bbox !== undefined) {
      showDebugBoxes = config.show_bbox;
      console.log('[Monitor] Config updated - show_bbox:', showDebugBoxes);
    }
    if (config.show_pose !== undefined) {
      showPoseSkeleton = config.show_pose;
      console.log('[Monitor] Config updated - show_pose:', showPoseSkeleton);
    }
    if (config.show_confidence !== undefined) {
      showConfidenceScores = config.show_confidence;
      console.log('[Monitor] Config updated - show_confidence:', showConfidenceScores);
    }
    if (config.show_track_ids !== undefined) {
      showTrackIds = config.show_track_ids;
      console.log('[Monitor] Config updated - show_track_ids:', showTrackIds);
    }
  });
}

// ============================================
// WEBCAM HANDLING
// ============================================

let webcamStream = null;
let videoElement = null;
let canvasElement = null;
let canvasContext = null;
let overlayCanvas = null;
let overlayContext = null;
let pipelineInterval = null;
let displayInterval = null;
let isPipelineRunning = false;
let lastPipelineMs = 0;

// Cache for detection data to draw boxes on every frame
let lastDetections = [];
let showDebugBoxes = false;  // Default false, will be loaded from config
let showPoseSkeleton = false;  // Default false, will be loaded from config
let showConfidenceScores = false;  // Default false, will be loaded from config
let showTrackIds = false;  // Default false, will be loaded from config

// Load current display settings from config
fetch('/api/config')
  .then(r => r.json())
  .then(config => {
    if (config.show_bbox !== undefined) {
      showDebugBoxes = config.show_bbox;
      console.log('[Monitor] Loaded show_bbox from config:', showDebugBoxes);
    }
    if (config.show_pose !== undefined) {
      showPoseSkeleton = config.show_pose;
      console.log('[Monitor] Loaded show_pose from config:', showPoseSkeleton);
    }
    if (config.show_confidence !== undefined) {
      showConfidenceScores = config.show_confidence;
      console.log('[Monitor] Loaded show_confidence from config:', showConfidenceScores);
    }
    if (config.show_track_ids !== undefined) {
      showTrackIds = config.show_track_ids;
      console.log('[Monitor] Loaded show_track_ids from config:', showTrackIds);
    }
  });

function initWebcam() {
  // Create video element for webcam (will be shown directly for smooth preview)
  videoElement = document.createElement('video');
  videoElement.setAttribute('autoplay', '');
  videoElement.setAttribute('playsinline', '');
  videoElement.setAttribute('muted', '');
  videoElement.className = 'video-frame-native';
  videoElement.style.width = '100%';
  videoElement.style.height = '100%';
  videoElement.style.objectFit = 'contain';
  videoElement.style.display = 'none';

  // Create overlay canvas for smooth UI-side drawing
  overlayCanvas = document.createElement('canvas');
  overlayCanvas.className = 'video-canvas-overlay';
  overlayCanvas.style.position = 'absolute';
  overlayCanvas.style.top = '0';
  overlayCanvas.style.left = '0';
  overlayCanvas.style.width = '100%';
  overlayCanvas.style.height = '100%';
  overlayCanvas.style.pointerEvents = 'none';
  overlayCanvas.style.zIndex = '5';
  overlayContext = overlayCanvas.getContext('2d');

  // Create hidden canvas for frame capture (sends data to server)
  canvasElement = document.createElement('canvas');
  canvasElement.style.display = 'none';
  canvasContext = canvasElement.getContext('2d');

  // Auto-start webcam when page loads
  startWebcamPreview();
}

async function startWebcamPreview() {
  try {
    webcamStream = await navigator.mediaDevices.getUserMedia({
      video: {
        width: { ideal: 1920 },
        height: { ideal: 1080 },
        frameRate: { ideal: 30 }
      },
      audio: false
    });

    videoElement.srcObject = webcamStream;
    await videoElement.play();

    // Set canvas sizes to match video
    const vw = videoElement.videoWidth || 1280;
    const vh = videoElement.videoHeight || 720;
    canvasElement.width = vw;
    canvasElement.height = vh;
    overlayCanvas.width = vw;
    overlayCanvas.height = vh;

    console.log('Webcam started:', vw, 'x', vh);

    // Show native video directly for smooth preview
    showNativeVideoPreview();

    return true;
  } catch (error) {
    console.error('Error accessing webcam:', error);
    return false;
  }
}

// Show native video element for smooth preview (no pipeline)
function showNativeVideoPreview() {
  const videoFeed = document.getElementById('video-feed');
  if (!videoFeed || !videoElement) return;

  const placeholder = videoFeed.querySelector('.video-placeholder');
  if (placeholder) placeholder.style.display = 'none';

  // Hide any canvas-based image
  const imgElement = videoFeed.querySelector('.video-frame-img');
  if (imgElement) imgElement.style.display = 'none';

  // Show native video element
  videoElement.style.display = 'block';
  if (!videoFeed.contains(videoElement)) {
    videoFeed.appendChild(videoElement);
  }

  // Ensure overlay canvas is also present
  if (!videoFeed.contains(overlayCanvas)) {
    videoFeed.appendChild(overlayCanvas);
  }
  overlayCanvas.classList.remove('hidden');
}

// Switch to canvas mode for detection overlays
function switchToCanvasMode() {
  // In the new layered approach, we don't hide the video.
  // We just ensure the overlay canvas is visible.
  if (overlayCanvas) overlayCanvas.classList.remove('hidden');
}

function startLocalDisplayLoop(customIntervalMs) {
  // Use custom interval if provided, otherwise default to 60fps (16ms) for smooth overlays
  const intervalMs = customIntervalMs || 16;

  // Ensure layered view is active
  showNativeVideoPreview();

  // Draw overlays on the transparent overlay canvas
  displayInterval = setInterval(() => {
    if (overlayContext && overlayCanvas) {
      // Clear previous drawings
      overlayContext.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);

      // Draw bounding boxes if enabled and we have detections
      if (showDebugBoxes && lastDetections.length > 0) {
        drawBoundingBoxes(overlayContext, lastDetections, overlayCanvas.width, overlayCanvas.height);
      }

      // Draw pose skeleton if enabled and we have detections with pose data
      if (showPoseSkeleton && lastDetections.length > 0) {
        lastDetections.forEach(det => {
          if (det.pose_landmarks) {
            drawPoseSkeleton(overlayContext, det.pose_landmarks, overlayCanvas.width, overlayCanvas.height);
          }
        });
      }
    }
  }, intervalMs);
}

function displayLocalFrame(dataUrl) {
  // No-op in new layered approach
}

function stopWebcam() {
  if (displayInterval) {
    clearInterval(displayInterval);
    displayInterval = null;
  }
  if (pipelineInterval) {
    clearInterval(pipelineInterval);
    pipelineInterval = null;
  }
  if (webcamStream) {
    webcamStream.getTracks().forEach(track => track.stop());
    webcamStream = null;
  }
  isPipelineRunning = false;
}

function startPipelineProcessing() {
  isPipelineRunning = true;
  // Start the canvas display loop for detection overlays
  startLocalDisplayLoop();
  // Start sending frames to server
  pipelineInterval = setInterval(captureAndSendFrame, 33); // 30 FPS
}

function stopPipelineProcessing() {
  isPipelineRunning = false;
  if (pipelineInterval) {
    clearInterval(pipelineInterval);
    pipelineInterval = null;
  }
  // Stop the canvas display loop
  if (displayInterval) {
    clearInterval(displayInterval);
    displayInterval = null;
  }
  // Clear cached detections and speed display
  lastDetections = [];
  if (overlayContext && overlayCanvas) {
    overlayContext.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
  }
  updatePipelineSpeed(0);
}

function captureAndSendFrame() {
  if (!isPipelineRunning || !videoElement || !canvasContext) return;

  const startTime = performance.now();

  // Draw full 1080p frame to hidden canvas
  canvasContext.drawImage(videoElement, 0, 0);

  // Convert to base64 with speed-optimized quality (0.65)
  // This keeps object edges sharp for YOLO but makes packets 3x smaller.
  const frameData = canvasElement.toDataURL('image/jpeg', 0.65);

  // Bbox display controlled by settings page via config.json

  // Send to server
  if (socket && socket.connected) {
    socket.emit('video_frame', {
      image: frameData,
      debug_boxes: showDebugBoxes,
      send_time: startTime
    });
  }
}



function updatePipelineSpeed(ms) {
  const speedElement = document.getElementById('pipeline-speed');
  const speedText = document.getElementById('pipeline-speed-text');

  if (ms > 0) {
    const fps = Math.round(1000 / ms);
    const displayText = ms + 'ms (' + fps + ' FPS)';

    if (speedText) speedText.textContent = displayText;
    if (speedElement) speedElement.style.display = 'flex';
  } else {
    if (speedElement) speedElement.style.display = 'none';
  }
}

function drawBoundingBoxes(ctx, detections, canvasWidth, canvasHeight) {
  detections.forEach(det => {
    if (!det.bbox) return;

    const [x1, y1, x2, y2] = det.bbox;
    const score = det.unified_score || 0;

    // Color based on suspicion level (RGB format for canvas)
    let color, label;
    if (score >= 50) {
      color = 'rgb(255, 0, 0)'; // Red
      label = 'HIGH';
    } else if (score >= 20) {
      color = 'rgb(255, 165, 0)'; // Orange
      label = 'MED';
    } else {
      color = 'rgb(0, 140, 0)'; // Dark green
      label = 'OK';
    }

    // Draw bounding box with rounded corners and subtle glow
    ctx.save();
    ctx.shadowBlur = 6;
    ctx.shadowColor = color;
    ctx.strokeStyle = color;
    ctx.lineWidth = 2.5;

    // Function for rounded rect
    const roundedRect = (ctx, x, y, width, height, radius) => {
      ctx.beginPath();
      ctx.moveTo(x + radius, y);
      ctx.lineTo(x + width - radius, y);
      ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
      ctx.lineTo(x + width, y + height - radius);
      ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
      ctx.lineTo(x + radius, y + height);
      ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
      ctx.lineTo(x, y + radius);
      ctx.quadraticCurveTo(x, y, x + radius, y);
      ctx.closePath();
    };

    roundedRect(ctx, x1, y1, x2 - x1, y2 - y1, 8);
    ctx.stroke();

    // Build label text with identity support
    const trackId = det.track_id || '?';
    const studentName = det.student_name || '';
    const primaryId = det.primary_id || trackId;

    // Prioritize Student Name > Student ID > Track ID
    let identityText = studentName || (det.id_type === 'SID' ? primaryId : `#${trackId}`);

    const className = det.class_id === 0 ? identityText : `Class ${det.class_id}`;
    const labelText = `${className} ${Math.round(score)}% ${label}`;

    // Draw label background (glassmorphism style)
    ctx.font = 'bold 13px Manrope, sans-serif';
    const metrics = ctx.measureText(labelText);
    const textHeight = 18;

    ctx.shadowBlur = 0;
    ctx.fillStyle = color;
    ctx.globalAlpha = 0.85;

    // Draw label tab
    const tabHeight = textHeight + 6;
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x1 + metrics.width + 12, y1);
    ctx.lineTo(x1 + metrics.width + 12, y1 - tabHeight);
    ctx.lineTo(x1 + 4, y1 - tabHeight);
    ctx.quadraticCurveTo(x1, y1 - tabHeight, x1, y1 - tabHeight + 4);
    ctx.closePath();
    ctx.fill();

    // Draw label text
    ctx.globalAlpha = 1.0;
    ctx.fillStyle = 'white';
    ctx.fillText(labelText, x1 + 6, y1 - 8);
    ctx.restore();
  });
}

// Draw pose skeleton on canvas
function drawPoseSkeleton(ctx, landmarks, canvasWidth, canvasHeight) {
  if (!landmarks || landmarks.length === 0) return;

  // Convert normalized coordinates to canvas coordinates
  const points = landmarks.map(lm => ({
    x: lm.x * canvasWidth,
    y: lm.y * canvasHeight,
    visibility: lm.visibility
  }));

  // Define pose connections (MediaPipe pose landmarks 0-32)
  const connections = [
    // Torso & Shoulders
    { points: [11, 12], label: 'shoulders', color: '#00ffff' },
    { points: [23, 24], label: 'hips', color: '#00ffff' },
    { points: [11, 23], label: 'left_torso', color: '#ff3333' },
    { points: [12, 24], label: 'right_torso', color: '#3333ff' },

    // Left Arm
    { points: [11, 13], label: 'left_upper_arm', color: '#ff3333' },
    { points: [13, 15], label: 'left_lower_arm', color: '#ff3333' },
    { points: [15, 17], label: 'left_hand', color: '#ff3333' },
    { points: [15, 19], label: 'left_hand', color: '#ff3333' },
    { points: [15, 21], label: 'left_hand', color: '#ff3333' },

    // Right Arm
    { points: [12, 14], label: 'right_upper_arm', color: '#3333ff' },
    { points: [14, 16], label: 'right_lower_arm', color: '#3333ff' },
    { points: [16, 18], label: 'right_hand', color: '#3333ff' },
    { points: [16, 20], label: 'right_hand', color: '#3333ff' },
    { points: [16, 22], label: 'right_hand', color: '#3333ff' },

    // Left Leg
    { points: [23, 25], label: 'left_thigh', color: '#ff3333' },
    { points: [25, 27], label: 'left_calf', color: '#ff3333' },
    { points: [27, 29], label: 'left_foot', color: '#ff3333' },
    { points: [29, 31], label: 'left_foot', color: '#ff3333' },
    { points: [27, 31], label: 'left_foot', color: '#ff3333' },

    // Right Leg
    { points: [24, 26], label: 'right_thigh', color: '#3333ff' },
    { points: [26, 28], label: 'right_calf', color: '#3333ff' },
    { points: [28, 30], label: 'right_foot', color: '#3333ff' },
    { points: [30, 32], label: 'right_foot', color: '#3333ff' },
    { points: [28, 32], label: 'right_foot', color: '#3333ff' },

    // Face (Simplified for clarity)
    { points: [0, 1], label: 'face', color: '#ffffff' },
    { points: [0, 4], label: 'face', color: '#ffffff' },
    { points: [1, 2], label: 'face', color: '#ffffff' },
    { points: [2, 3], label: 'face', color: '#ffffff' },
    { points: [4, 5], label: 'face', color: '#ffffff' },
    { points: [5, 6], label: 'face', color: '#ffffff' },
    { points: [3, 7], label: 'face', color: '#ffffff' },
    { points: [6, 8], label: 'face', color: '#ffffff' },
    { points: [9, 10], label: 'face', color: '#ffffff' }
  ];

  // Connection Drawing with Glow effect
  ctx.save();
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';

  connections.forEach(conn => {
    const [startIdx, endIdx] = conn.points;
    if (startIdx >= points.length || endIdx >= points.length) return;

    const startPoint = points[startIdx];
    const endPoint = points[endIdx];

    if (startPoint.visibility > 0.5 && endPoint.visibility > 0.5) {
      // Glow/Neon effect
      ctx.shadowBlur = 4;
      ctx.shadowColor = conn.color;
      ctx.strokeStyle = conn.color;
      ctx.lineWidth = 3;

      ctx.beginPath();
      ctx.moveTo(startPoint.x, startPoint.y);
      ctx.lineTo(endPoint.x, endPoint.y);
      ctx.stroke();

      // Outer thin line for sharpness
      ctx.shadowBlur = 0;
      ctx.strokeStyle = 'white';
      ctx.lineWidth = 1;
      ctx.stroke();
    }
  });

  // Draw landmarks as glowing joints
  points.forEach((point, idx) => {
    if (point.visibility > 0.5) {
      // Different colors for specific joints
      let jointColor = '#00ff00'; // Default green
      if (idx <= 10) jointColor = '#ffffff'; // Face
      else if ([11, 13, 15, 23, 25, 27].includes(idx)) jointColor = '#ff3333'; // Left joints
      else if ([12, 14, 16, 24, 26, 28].includes(idx)) jointColor = '#3333ff'; // Right joints

      ctx.shadowBlur = 8;
      ctx.shadowColor = jointColor;
      ctx.fillStyle = jointColor;

      ctx.beginPath();
      ctx.arc(point.x, point.y, 4, 0, 2 * Math.PI);
      ctx.fill();

      // White core
      ctx.shadowBlur = 0;
      ctx.fillStyle = 'white';
      ctx.beginPath();
      ctx.arc(point.x, point.y, 1.5, 0, 2 * Math.PI);
      ctx.fill();
    }
  });
  ctx.restore();
}

// ============================================
// SESSION STATE
// ============================================

let activeSession = null;
let pendingAlerts = [];
let sessionStatistics = {
  totalAlerts: 0,
  confirmedAlerts: 0,
  declinedAlerts: 0
};
let sessionTimer = null;
let sessionStartTime = null;

// Sound notification state
let soundEnabled = false;

// Create audio objects for different severity levels
const alertSounds = {
  high: createBeepSound(800, 0.3, 200),
  medium: createBeepSound(600, 0.2, 150),
  low: createBeepSound(400, 0.15, 100)
};

// ============================================
// DEPARTMENT & SUBJECT TREE DATA
// ============================================

const monitorSubjectTree = {
  "Computer Science": {
    "General Subjects": [
      "Mathematics 1",
      "Mathematics 2",
      "English Language 1",
      "English Language 2",
      "Political Science Principles",
      "Statistics and Probabilities",
      "Islamic Culture",
      "Arabic Language",
      "Linear Algebra and Logic"
    ],
    "Specialized Subjects": [
      "Programming Basics",
      "Intro to Computer Science",
      "Electrical Engineering Principles",
      "Digital Systems Intro",
      "Computer Organization",
      "Assembly Language",
      "C Language",
      "Systems Analysis",
      "Database Management",
      "Software Engineering",
      "Operating Systems",
      "Visual Programming 1",
      "Visual Programming 2",
      "Data Structures 1",
      "Data Structures 2",
      "Network Programming",
      "Java Language",
      "Web Design",
      "Modeling and Simulation",
      "Artificial Intelligence",
      "Computer Graphics",
      "Image Processing",
      "Mobile Applications",
      "Computer Architecture",
      "Computer Networks",
      "System Programming",
      "Data and Information Security",
      "Network Building and Protection",
      "Discrete Mathematics",
      "Numerical Methods and Programming"
    ]
  }
};

if (typeof window !== 'undefined') {
  window.initSubjectDropdowns = initSubjectDropdowns;
}

function initSubjectDropdowns() {
  const deptSelect = document.getElementById('department-select');
  const subjSelect = document.getElementById('subject-select');
  const examNameHidden = document.getElementById('exam-name-input');

  console.log('Initializing Subject Dropdowns...');
  if (!deptSelect || !subjSelect) {
    console.error('Dropdown elements not found!');
    return;
  }

  // Clear existing department options (keep default)
  while (deptSelect.options.length > 1) {
    deptSelect.remove(1);
  }

  // Populate Departments
  Object.keys(monitorSubjectTree).forEach(dept => {
    const opt = document.createElement('option');
    opt.value = dept;
    opt.textContent = dept;
    deptSelect.appendChild(opt);
  });
  console.log('Departments populated:', Object.keys(monitorSubjectTree));

  // Handle Department Change
  deptSelect.addEventListener('change', () => {
    console.log('Department selected:', deptSelect.value);
    const dept = deptSelect.value;
    subjSelect.innerHTML = '<option value="" disabled selected>Select Subject</option>';
    subjSelect.disabled = false;

    const categories = monitorSubjectTree[dept];
    Object.keys(categories).forEach(catName => {
      const group = document.createElement('optgroup');
      group.label = catName;

      categories[catName].forEach(subject => {
        const opt = document.createElement('option');
        opt.value = subject;
        opt.textContent = subject;
        group.appendChild(opt);
      });
      subjSelect.appendChild(group);
    });
  });

  // Sync selection to hidden input for session naming compatibility
  subjSelect.addEventListener('change', () => {
    examNameHidden.value = subjSelect.value;
  });
}

function resetSubjectDropdowns() {
  const deptSelect = document.getElementById('department-select');
  const subjSelect = document.getElementById('subject-select');
  const examNameHidden = document.getElementById('exam-name-input');

  if (deptSelect) deptSelect.value = "";
  if (subjSelect) {
    subjSelect.innerHTML = '<option value="" disabled selected>Select Subject</option>';
    subjSelect.disabled = true;
    subjSelect.value = "";
  }
  if (examNameHidden) examNameHidden.value = "";
}

function updateDashboardStatus(isActive) {
  const container = document.getElementById('dashboard-status-container');
  const icon = document.getElementById('dashboard-status-icon');
  const label = document.getElementById('dashboard-status-label');
  const subtitle = document.getElementById('dashboard-status-subtitle');

  if (!container || !icon || !label || !subtitle) return;

  if (isActive) {
    container.classList.remove('status-idle');
    container.classList.add('status-active');
    icon.className = 'bx bx-check-circle';
    label.textContent = 'Active';
    subtitle.textContent = 'AI Engine Running';

    // Update session status bar
    const sessionStatus = document.getElementById('session-status');
    if (sessionStatus) {
      sessionStatus.textContent = 'Active';
      sessionStatus.className = 'session-status active';
    }
  } else {
    container.classList.remove('status-active');
    container.classList.add('status-idle');
    icon.className = 'bx bx-pause-circle';
    label.textContent = 'Not Active';
    subtitle.textContent = 'Engine Stopped';

    // Update session status bar
    const sessionStatus = document.getElementById('session-status');
    if (sessionStatus) {
      sessionStatus.textContent = 'Not Active';
      sessionStatus.className = 'session-status stopped';
    }
  }
}

// ============================================
// INITIALIZATION
// ============================================

console.log('Monitor.js loaded and executing...');

document.addEventListener('DOMContentLoaded', () => {
  console.log('Monitor.js DOMContentLoaded fired');
  initSocket();
  initWebcam();
  initSubjectDropdowns(); // Added dynamic dropdowns
  setupMonitorEventListeners();
  setupSoundToggle();

  // Set initial status to Idle
  updateDashboardStatus(false);
});

// ============================================
// EVENT LISTENERS
// ============================================

function setupMonitorEventListeners() {
  const toggleBtn = document.getElementById('pipeline-toggle-btn');
  if (toggleBtn) {
    toggleBtn.addEventListener('click', function () {
      if (isPipelineRunning) {
        stopPipeline();
      } else {
        startPipeline();
      }
    });
  }

  const modalOverlay = document.getElementById('modal-overlay-alert');
  const modalCloseBtn = document.getElementById('modal-close-alert-btn');

  if (modalOverlay) {
    modalOverlay.addEventListener('click', closeAlertReviewModal);
  }

  if (modalCloseBtn) {
    modalCloseBtn.addEventListener('click', closeAlertReviewModal);
  }

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      const modal = document.getElementById('alert-review-modal');
      if (modal && !modal.classList.contains('hidden')) {
        closeAlertReviewModal();
      }
      closeImageZoom();
    }
  });

  const confirmBtn = document.getElementById('btn-confirm-alert');
  const declineBtn = document.getElementById('btn-decline-alert');

  if (confirmBtn) {
    confirmBtn.addEventListener('click', () => reviewAlert('confirm'));
  }

  if (declineBtn) {
    declineBtn.addEventListener('click', () => reviewAlert('decline'));
  }

  // Stop confirmation modal buttons
  const stopModalClose = document.getElementById('stop-modal-close-btn');
  const stopModalOverlay = document.getElementById('stop-modal-overlay');
  const btnCancelStop = document.getElementById('btn-cancel-stop');
  const btnConfirmStop = document.getElementById('btn-confirm-stop');

  if (stopModalClose) {
    stopModalClose.addEventListener('click', cancelStopPipeline);
  }
  if (stopModalOverlay) {
    stopModalOverlay.addEventListener('click', cancelStopPipeline);
  }
  if (btnCancelStop) {
    btnCancelStop.addEventListener('click', cancelStopPipeline);
  }
  if (btnConfirmStop) {
    btnConfirmStop.addEventListener('click', confirmStopPipeline);
  }
}

// ============================================
// PIPELINE CONTROL
// ============================================

async function startPipeline() {
  console.log('[DEBUG] startPipeline called');
  const examNameInput = document.getElementById('exam-name-input');
  const examName = examNameInput.value.trim();

  const deptSelect = document.getElementById('department-select');
  const subjSelect = document.getElementById('subject-select');

  if (!deptSelect.value || !subjSelect.value) {
    alert('Please select both a Department and a Subject before starting.');
    if (!deptSelect.value) deptSelect.focus();
    else subjSelect.focus();
    return;
  }

  // Check if webcam is available
  if (!webcamStream) {
    alert('Webcam not available. Please allow camera access and refresh the page.');
    return;
  }

  // Start session on server
  if (socket && socket.connected) {
    socket.emit('start_session', {
      session_name: examName,
      department: document.getElementById('department-select').value,
      subject: document.getElementById('subject-select').value,
      camera_id: 'cam_01'
    });
  }

  // Update local state
  activeSession = {
    session_id: 'pending',
    session_name: examName,
    status: 'active'
  };

  // Update UI
  const toggleBtn = document.getElementById('pipeline-toggle-btn');
  const toggleBtnIcon = document.getElementById('pipeline-btn-icon');
  const toggleBtnText = document.getElementById('pipeline-btn-text');
  const sessionStatus = document.getElementById('session-status');

  if (toggleBtn) {
    toggleBtn.classList.remove('btn-start-pipeline');
    toggleBtn.classList.add('btn-stop-pipeline');
    if (toggleBtnIcon) toggleBtnIcon.className = 'bx bx-stop-circle';
    if (toggleBtnText) toggleBtnText.textContent = 'Stop Pipeline';
  }
  sessionStatus.textContent = 'Active Session: ' + examName;
  sessionStatus.classList.add('active');
  examNameInput.disabled = true;

  // Start session timer
  sessionStartTime = Date.now();
  startSessionTimer();

  // Update dashboard status
  updateDashboardStatus(true);

  // Start pipeline processing (sends frames to server)
  startPipelineProcessing();

  console.log('Pipeline started');
}

function stopPipeline() {
  if (!activeSession) return;

  // Check pending alerts
  if (pendingAlerts.length > 0) {
    showStopConfirmationModal();
    return;
  }

  // No pending alerts, stop immediately
  confirmStopPipeline();
}

// ============================================
// STOP CONFIRMATION MODAL HELPERS
// ============================================

function showStopConfirmationModal() {
  const modal = document.getElementById('stop-modal-overlay');
  const pendingCount = document.getElementById('pending-count');

  if (pendingCount) {
    pendingCount.textContent = pendingAlerts.length;
  }

  if (modal) {
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
  }
}

function hideStopConfirmationModal() {
  const modal = document.getElementById('stop-modal-overlay');
  if (modal) {
    modal.classList.add('hidden');
    document.body.style.overflow = '';
  }
}

function cancelStopPipeline() {
  hideStopConfirmationModal();
}

function confirmStopPipeline() {
  hideStopConfirmationModal();

  // Stop pipeline processing (but keep camera feed running)
  stopPipelineProcessing();

  // Stop session on server
  if (socket && socket.connected) {
    socket.emit('stop_session');
  }

  // Update session status
  activeSession.status = 'stopped';

  // Update UI
  const toggleBtn = document.getElementById('pipeline-toggle-btn');
  const toggleBtnIcon = document.getElementById('pipeline-btn-icon');
  const toggleBtnText = document.getElementById('pipeline-btn-text');
  const sessionStatus = document.getElementById('session-status');
  const examNameInput = document.getElementById('exam-name-input');

  if (toggleBtn) {
    toggleBtn.classList.remove('btn-stop-pipeline');
    toggleBtn.classList.add('btn-start-pipeline');
    if (toggleBtnIcon) toggleBtnIcon.className = 'bx bx-play-circle';
    if (toggleBtnText) toggleBtnText.textContent = 'Start Pipeline';
  }
  const deptSelect = document.getElementById('department-select');
  const subjSelect = document.getElementById('subject-select');
  if (deptSelect) {
    deptSelect.disabled = false;
    deptSelect.value = ""; // Explicitly reset to "Select Department"
  }
  if (subjSelect) {
    subjSelect.disabled = true;
    subjSelect.innerHTML = '<option value="" disabled selected>Select Subject</option>';
    subjSelect.value = "";
  }

  if (examNameInput) {
    examNameInput.disabled = false;
    examNameInput.value = '';
  }

  // Stop timer
  if (sessionTimer) {
    clearInterval(sessionTimer);
    sessionTimer = null;
  }

  // Update status message
  if (sessionStatus) {
    if (pendingAlerts.length > 0) {
      sessionStatus.textContent = 'Session Stopped - ' + pendingAlerts.length + ' Alert(s) Pending Review';
      sessionStatus.className = 'session-status stopped';
    } else {
      sessionStatus.textContent = 'Not Active';
      sessionStatus.className = 'session-status stopped';
    }
    sessionStatus.style.color = '';
  }
  sessionStatus.classList.remove('active');

  // Clear stats
  const totalStat = document.getElementById('total-alerts-stat');
  const confirmedStat = document.getElementById('confirmed-alerts-stat');
  const declinedStat = document.getElementById('declined-alerts-stat');

  if (totalStat) totalStat.textContent = '0';
  if (confirmedStat) confirmedStat.textContent = '0';
  if (declinedStat) declinedStat.textContent = '0';

  // Clear session state
  activeSession = null;

  console.log('Pipeline stopped');
}

// ============================================
// SESSION TIMER
// ============================================

function startSessionTimer() {
  updateSessionTimer();
  sessionTimer = setInterval(updateSessionTimer, 1000);
}

function updateSessionTimer() {
  const elapsed = Math.floor((Date.now() - sessionStartTime) / 1000);
  const hours = Math.floor(elapsed / 3600);
  const minutes = Math.floor((elapsed % 3600) / 60);
  const seconds = elapsed % 60;

  const timeString = String(hours).padStart(2, '0') + ':' +
    String(minutes).padStart(2, '0') + ':' +
    String(seconds).padStart(2, '0');

  const timeElement = document.getElementById('video-time');
  if (timeElement) {
    timeElement.textContent = timeString;
  }
}

// ============================================
// ALERT HANDLING
// ============================================

function handleNewAlert(alert) {
  // Add to pending alerts
  pendingAlerts.unshift({
    event_id: alert.alert_id,
    alert_id: alert.alert_id,
    track_id: alert.track_id,
    primary_id: alert.primary_id,
    id_type: alert.id_type,
    student_id: alert.student_id,
    student_name: alert.student_name,
    timestamp: alert.timestamp,
    suspicion_score: alert.suspicion_score,
    reasons: alert.reasons,
    type: alert.type,
    severity: alert.suspicion_score >= 80 ? 'high' : (alert.suspicion_score >= 50 ? 'medium' : 'low'),
    status: 'pending',
    evidence_thumbnail: alert.crop_base64 ? ('data:image/jpeg;base64,' + alert.crop_base64) : 'static/assets/studentTestPic.png',
    crop_base64: alert.crop_base64
  });

  sessionStatistics.totalAlerts++;

  // Play sound
  const severity = alert.suspicion_score >= 80 ? 'high' : (alert.suspicion_score >= 50 ? 'medium' : 'low');
  playAlertSound(severity);

  renderAlerts();
  updateStatistics();
}

function renderAlerts() {
  const alertsList = document.getElementById('alerts-list');
  const noAlertsState = document.getElementById('no-alerts-state');
  const alertsCount = document.getElementById('alerts-count');

  if (pendingAlerts.length === 0) {
    const alertCards = alertsList.querySelectorAll('.alert-card');
    alertCards.forEach(card => card.remove());

    if (noAlertsState) noAlertsState.style.display = 'flex';
    if (alertsCount) alertsCount.textContent = '0 Pending';
    return;
  }

  if (noAlertsState) noAlertsState.style.display = 'none';
  if (alertsCount) alertsCount.textContent = pendingAlerts.length + ' Pending';

  const alertCardsHTML = pendingAlerts.map(alert => {
    const timeAgo = getTimeAgo(new Date(alert.timestamp));
    const identityText = alert.id_type === 'SID' ? `Student: ${alert.student_id}` : `ID: ${alert.primary_id}`;
    const identityClass = alert.id_type === 'SID' ? 'identity-recognized' : 'identity-unknown';

    return '<div class="alert-card" data-alert-id="' + alert.event_id + '">' +
      '<div class="alert-card-header">' +
      '<img src="' + alert.evidence_thumbnail + '" alt="Alert Evidence" class="alert-thumbnail">' +
      '<div class="alert-card-info">' +
      '<div class="alert-top-info">' +
      '<span class="alert-severity-badge alert-severity-' + alert.severity + '">' + alert.severity + '</span>' +
      '<span class="' + identityClass + '">' + identityText + '</span>' +
      '</div>' +
      '<span class="alert-reason">' + alert.reasons.join(', ') + '</span>' +
      '</div>' +
      '</div>' +
      '<div class="alert-card-footer">' +
      '<span class="alert-time">' +
      '<i class="bx bx-time"></i> ' + timeAgo +
      '</span>' +
      '<button class="btn-review-alert" onclick="openAlertReviewModal(\'' + alert.event_id + '\')">' +
      'Review' +
      '</button>' +
      '</div>' +
      '</div>';
  }).join('');

  const existingCards = alertsList.querySelectorAll('.alert-card');
  existingCards.forEach(card => card.remove());

  if (noAlertsState) {
    noAlertsState.insertAdjacentHTML('beforebegin', alertCardsHTML);
  } else {
    alertsList.innerHTML = alertCardsHTML;
  }
}

// ============================================
// ALERT REVIEW MODAL
// ============================================

function openAlertReviewModal(eventId) {
  const alert = pendingAlerts.find(a => a.event_id === eventId || a.alert_id === eventId);
  if (!alert) return;

  const modal = document.getElementById('alert-review-modal');

  document.getElementById('alert-evidence-image').src = alert.evidence_thumbnail;
  document.getElementById('alert-suspicion-score').textContent = alert.suspicion_score + '%';
  document.getElementById('alert-timestamp').textContent = formatTimestamp(new Date(alert.timestamp));
  document.getElementById('alert-reasons').textContent = alert.reasons.join(', ');

  // Auto-fill student data if identified
  const sidInput = document.getElementById('student-id-input');
  const nameInput = document.getElementById('student-name-input');
  const noteInput = document.getElementById('review-notes-input');

  if (alert.id_type === 'SID') {
    sidInput.value = alert.student_id || '';
    nameInput.value = alert.student_name || '';
    sidInput.classList.add('auto-filled');
    nameInput.classList.add('auto-filled');
  } else {
    sidInput.value = '';
    nameInput.value = '';
    sidInput.classList.remove('auto-filled');
    nameInput.classList.remove('auto-filled');
  }

  noteInput.value = '';
  modal.dataset.alertId = alert.alert_id || alert.event_id;

  modal.classList.remove('hidden');
  document.body.style.overflow = 'hidden';
}

function closeAlertReviewModal() {
  const modal = document.getElementById('alert-review-modal');
  modal.classList.add('hidden');
  document.body.style.overflow = '';
  delete modal.dataset.alertId;
}

function reviewAlert(decision) {
  const modal = document.getElementById('alert-review-modal');
  const alertId = modal.dataset.alertId;

  if (!alertId) return;

  const studentId = document.getElementById('student-id-input').value.trim();
  const studentName = document.getElementById('student-name-input').value.trim();
  const notes = document.getElementById('review-notes-input').value.trim();

  // Validation: confirm requires student ID
  if (decision === 'confirm' && !studentId) {
    alert('Student ID is required to confirm cheating.');
    document.getElementById('student-id-input').focus();
    return;
  }

  // Send review to server
  if (socket && socket.connected) {
    socket.emit('review_alert', {
      alert_id: alertId,
      decision: decision,
      student_id: studentId,
      student_name: studentName,
      notes: notes
    });
  }

  // Update statistics
  if (decision === 'confirm') {
    sessionStatistics.confirmedAlerts++;
  } else if (decision === 'decline') {
    sessionStatistics.declinedAlerts++;
  }

  // Remove from pending alerts locally
  const alertIndex = pendingAlerts.findIndex(a => a.alert_id === alertId || a.event_id === alertId);
  if (alertIndex !== -1) {
    pendingAlerts.splice(alertIndex, 1);
  }

  renderAlerts();
  updateStatistics();
  closeAlertReviewModal();

  const action = decision === 'confirm' ? 'Confirmed' : 'Declined';
  showNotification('Alert ' + action, studentId ? ('Student: ' + studentId) : 'No student ID');

  // Check if session ended and all alerts reviewed
  if (pendingAlerts.length === 0 && activeSession && activeSession.status === 'stopped') {
    setTimeout(() => {
      const sessionStatus = document.getElementById('session-status');
      if (sessionStatus) {
        sessionStatus.textContent = 'No Active Session';
        sessionStatus.style.color = '';
      }
      activeSession = null;
      sessionStatistics = { totalAlerts: 0, confirmedAlerts: 0, declinedAlerts: 0 };
      updateStatistics();
    }, 500);
  }
}

// ============================================
// STATISTICS
// ============================================

function updateStatistics() {
  const totalEl = document.getElementById('total-alerts-stat');
  const confirmedEl = document.getElementById('confirmed-alerts-stat');
  const declinedEl = document.getElementById('declined-alerts-stat');

  if (totalEl) totalEl.textContent = sessionStatistics.totalAlerts;
  if (confirmedEl) confirmedEl.textContent = sessionStatistics.confirmedAlerts;
  if (declinedEl) declinedEl.textContent = sessionStatistics.declinedAlerts;
}

// ============================================
// HELPER FUNCTIONS
// ============================================

function getTimeAgo(date) {
  const seconds = Math.floor((new Date() - date) / 1000);

  if (seconds < 60) return 'Just now';
  if (seconds < 3600) return Math.floor(seconds / 60) + 'm ago';
  if (seconds < 86400) return Math.floor(seconds / 3600) + 'h ago';
  return Math.floor(seconds / 86400) + 'd ago';
}

function formatTimestamp(date) {
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}

function showNotification(title, message) {
  console.log('[' + title + '] ' + message);
  // TODO: Implement toast notification
}

// ============================================
// IMAGE ZOOM FUNCTIONALITY
// ============================================

function openImageZoom(imageSrc) {
  const lightbox = document.getElementById('image-zoom-lightbox');
  const zoomedImage = document.getElementById('zoomed-image');
  zoomedImage.src = imageSrc;
  lightbox.classList.remove('hidden');
  document.body.style.overflow = 'hidden';
}

function closeImageZoom() {
  const lightbox = document.getElementById('image-zoom-lightbox');
  if (!lightbox) return;

  lightbox.classList.add('hidden');
  document.body.style.overflow = '';
}

// ============================================
// SOUND NOTIFICATION SYSTEM
// ============================================

function createBeepSound(frequency, volume, duration) {
  return function () {
    try {
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();

      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);

      oscillator.frequency.value = frequency;
      oscillator.type = 'sine';

      gainNode.gain.setValueAtTime(volume, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + duration / 1000);

      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + duration / 1000);
    } catch (error) {
      console.log('Web Audio API not supported:', error);
    }
  };
}

function setupSoundToggle() {
  const soundToggleBtn = document.getElementById('sound-toggle-btn');
  const soundIcon = document.getElementById('sound-icon');

  if (!soundToggleBtn) return;

  soundToggleBtn.addEventListener('click', () => {
    soundEnabled = !soundEnabled;

    if (soundEnabled) {
      soundToggleBtn.classList.add('active');
      soundToggleBtn.title = 'Alert Sounds: ON';
      soundIcon.classList.remove('bx-volume-mute');
      soundIcon.classList.add('bx-volume-full');
      alertSounds.medium();
    } else {
      soundToggleBtn.classList.remove('active');
      soundToggleBtn.title = 'Alert Sounds: OFF';
      soundIcon.classList.remove('bx-volume-full');
      soundIcon.classList.add('bx-volume-mute');
    }
  });
}

function playAlertSound(severity) {
  if (!soundEnabled) return;

  const soundFunction = alertSounds[severity] || alertSounds.medium;
  soundFunction();
}
