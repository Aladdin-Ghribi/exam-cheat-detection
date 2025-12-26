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
  // Create hidden video element for webcam
  videoElement = document.createElement('video');
  videoElement.setAttribute('autoplay', '');
  videoElement.setAttribute('playsinline', '');
  videoElement.style.display = 'none';
  document.body.appendChild(videoElement);

  // Create canvas for frame capture
  canvasElement = document.createElement('canvas');
  canvasElement.style.display = 'none';
  document.body.appendChild(canvasElement);
  canvasContext = canvasElement.getContext('2d');

  // Auto-start webcam when page loads
  startWebcamPreview();
}

async function startWebcamPreview() {
  try {
    webcamStream = await navigator.mediaDevices.getUserMedia({
      video: {
        width: { ideal: 1280 },
        height: { ideal: 720 },
        frameRate: { ideal: 30 }
      },
      audio: false
    });

    videoElement.srcObject = webcamStream;
    await videoElement.play();

    // Set canvas size to match video
    canvasElement.width = videoElement.videoWidth || 1280;
    canvasElement.height = videoElement.videoHeight || 720;

    console.log('Webcam started:', canvasElement.width, 'x', canvasElement.height);

    // Start local display loop (always running)
    startLocalDisplayLoop();

    return true;
  } catch (error) {
    console.error('Error accessing webcam:', error);
    return false;
  }
}

function startLocalDisplayLoop(customIntervalMs) {
  // Use custom interval if provided, otherwise default to 30fps (33ms)
  const intervalMs = customIntervalMs || 33;

  // Display webcam feed at specified fps continuously with detection boxes
  displayInterval = setInterval(() => {
    if (videoElement && canvasContext) {
      canvasContext.drawImage(videoElement, 0, 0);

      // Draw bounding boxes if enabled and we have detections
      if (showDebugBoxes && lastDetections.length > 0) {
        drawBoundingBoxes(canvasContext, lastDetections, canvasElement.width, canvasElement.height);
      }

      // Draw pose skeleton if enabled and we have detections with pose data
      if (showPoseSkeleton && lastDetections.length > 0) {
        lastDetections.forEach(det => {
          if (det.pose_landmarks) {
            drawPoseSkeleton(canvasContext, det.pose_landmarks, canvasElement.width, canvasElement.height);
          }
        });
      }

      // Display the frame
      const frameData = canvasElement.toDataURL('image/jpeg', 0.8);
      displayLocalFrame(frameData);
    }
  }, intervalMs); // Use the custom interval
}

function displayLocalFrame(dataUrl) {
  const videoFeed = document.getElementById('video-feed');
  if (!videoFeed) return;

  const placeholder = videoFeed.querySelector('.video-placeholder');
  if (placeholder) {
    placeholder.style.display = 'none';
  }

  let imgElement = videoFeed.querySelector('.video-frame-img');
  if (!imgElement) {
    imgElement = document.createElement('img');
    imgElement.className = 'video-frame-img';
    imgElement.style.width = '100%';
    imgElement.style.height = '100%';
    imgElement.style.objectFit = 'contain';
    videoFeed.appendChild(imgElement);
  }

  imgElement.src = dataUrl;
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
  pipelineInterval = setInterval(captureAndSendFrame, 100);
}

function stopPipelineProcessing() {
  isPipelineRunning = false;
  if (pipelineInterval) {
    clearInterval(pipelineInterval);
    pipelineInterval = null;
  }
  // Clear cached detections and speed display
  lastDetections = [];
  updatePipelineSpeed(0);
}

function captureAndSendFrame() {
  if (!isPipelineRunning || !videoElement || !canvasContext) return;

  const startTime = performance.now();

  // Draw current video frame to canvas
  canvasContext.drawImage(videoElement, 0, 0);

  // Convert to base64
  const frameData = canvasElement.toDataURL('image/jpeg', 0.8);

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

function displayFrame(base64Image, pipelineMs) {
  const videoFeed = document.getElementById('video-feed');
  if (!videoFeed) return;

  const placeholder = videoFeed.querySelector('.video-placeholder');
  if (placeholder) {
    placeholder.style.display = 'none';
  }

  let imgElement = videoFeed.querySelector('.video-frame-img');
  if (!imgElement) {
    imgElement = document.createElement('img');
    imgElement.className = 'video-frame-img';
    imgElement.style.width = '100%';
    imgElement.style.height = '100%';
    imgElement.style.objectFit = 'contain';
    videoFeed.appendChild(imgElement);
  }

  imgElement.src = 'data:image/jpeg;base64,' + base64Image;

  // Update pipeline speed display
  if (pipelineMs) {
    updatePipelineSpeed(pipelineMs);
  }
}

function updatePipelineSpeed(ms) {
  const speedElement = document.getElementById('pipeline-speed');
  const speedText = document.getElementById('pipeline-speed-text');

  if (speedElement && speedText) {
    if (ms > 0) {
      const fps = Math.round(1000 / ms);
      speedText.textContent = ms + 'ms (' + fps + ' FPS)';
      speedElement.style.display = 'flex';
    } else {
      speedElement.style.display = 'none';
    }
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

    // Draw bounding box
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

    // Build label text
    const trackId = det.track_id || '?';
    const className = det.class_id === 0 ? 'Person' : `Class ${det.class_id}`;

    // Build label text with or without track ID based on setting
    const trackText = showTrackIds ? `#${trackId} | ` : '';
    const labelText = `${className} ${trackText}${Math.round(score)}% ${label}`;

    // Draw label background
    ctx.font = '12px Arial';
    const metrics = ctx.measureText(labelText);
    const textHeight = 16;

    ctx.fillStyle = color;
    ctx.fillRect(x1, y1 - textHeight - 4, metrics.width + 8, textHeight + 4);

    // Draw label text
    ctx.fillStyle = 'white';
    ctx.fillText(labelText, x1 + 4, y1 - 6);

    // Draw confidence score if enabled
    if (showConfidenceScores && det.unified_score !== undefined) {
      // Draw confidence score above the bounding box

      ctx.fillStyle = 'rgba(255, 255, 255, 0.9)'; // Semi-transparent white background
      ctx.fillRect(x1, y2 - 25, 60, 20);

      ctx.fillStyle = 'black';
      ctx.font = '12px Arial';
      ctx.fillText(`${Math.round(det.unified_score)}%`, x1 + 5, y2 - 10);
    }
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

  // Define pose connections (MediaPipe pose landmarks)
  const connections = [
    [0, 1], [1, 2], [2, 3], [3, 7], // Face
    [0, 4], [4, 5], [5, 6], [6, 8], // Face
    [9, 10], [11, 12], [11, 13], [11, 23], [12, 24], [12, 25], // Arms
    [13, 15], [14, 16], [15, 17], [16, 18], [17, 19], [18, 20], // Arms
    [19, 21], [20, 22], // Arms
    [11, 23], [23, 24], [24, 25], // Torso
    [23, 25], [25, 26], [26, 27], [27, 28], [28, 29], [29, 30], [30, 31], // Legs
    [27, 29], [29, 31], [28, 30], [30, 32] // Legs
  ];

  // Draw connections
  ctx.strokeStyle = 'rgba(0, 255, 0, 0.7)'; // Green with transparency
  ctx.lineWidth = 2;

  connections.forEach(([startIdx, endIdx]) => {
    if (startIdx >= points.length || endIdx >= points.length) return;

    const startPoint = points[startIdx];
    const endPoint = points[endIdx];

    // Only draw if both points are visible enough
    if (startPoint.visibility > 0.3 && endPoint.visibility > 0.3) {
      ctx.beginPath();
      ctx.moveTo(startPoint.x, startPoint.y);
      ctx.lineTo(endPoint.x, endPoint.y);
      ctx.stroke();
    }
  });

  // Draw landmarks
  ctx.fillStyle = 'rgba(0, 255, 0, 0.9)'; // Bright green
  points.forEach(point => {
    if (point.visibility > 0.3) {
      ctx.beginPath();
      ctx.arc(point.x, point.y, 3, 0, 2 * Math.PI);
      ctx.fill();
    }
  });
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
// DASHBOARD STATUS UPDATE
// ============================================

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
  } else {
    container.classList.remove('status-active');
    container.classList.add('status-idle');
    icon.className = 'bx bx-pause-circle';
    label.textContent = 'Idle';
    subtitle.textContent = 'Engine Stopped';
  }
}

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', () => {
  initSocket();
  initWebcam();
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

  if (!examName) {
    alert('Please enter an exam name before starting the pipeline.');
    examNameInput.focus();
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
  examNameInput.disabled = false;
  examNameInput.value = '';

  // Stop timer
  if (sessionTimer) {
    clearInterval(sessionTimer);
    sessionTimer = null;
  }

  // Update status message
  if (pendingAlerts.length > 0) {
    sessionStatus.textContent = 'Session Stopped - ' + pendingAlerts.length + ' Alert(s) Pending Review';
    sessionStatus.style.color = '#FFB84D';
  } else {
    sessionStatus.textContent = 'No Active Session';
    sessionStatus.style.color = '';
  }
  sessionStatus.classList.remove('active');

  // Update dashboard status to Idle
  updateDashboardStatus(false);

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

    return '<div class="alert-card" data-alert-id="' + alert.event_id + '">' +
      '<div class="alert-card-header">' +
      '<img src="' + alert.evidence_thumbnail + '" alt="Alert Evidence" class="alert-thumbnail">' +
      '<div class="alert-card-info">' +
      '<span class="alert-severity-badge alert-severity-' + alert.severity + '">' + alert.severity + '</span>' +
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

  document.getElementById('student-id-input').value = '';
  document.getElementById('student-name-input').value = '';
  document.getElementById('review-notes-input').value = '';

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
