// Monitor Page - Session Management and Alert Handling

// Session state
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
let soundEnabled = false; // Muted by default

// Create audio objects for different severity levels (using Web Audio API fallback)
const alertSounds = {
  high: createBeepSound(800, 0.3, 200),    // High pitch, loud
  medium: createBeepSound(600, 0.2, 150),  // Medium pitch
  low: createBeepSound(400, 0.15, 100)     // Low pitch, quiet
};

// Initialize monitor page
document.addEventListener('DOMContentLoaded', () => {
  setupMonitorEventListeners();
  setupSoundToggle();
});

// Setup event listeners
function setupMonitorEventListeners() {
  // Start pipeline button
  const startBtn = document.getElementById('start-pipeline-btn');
  if (startBtn) {
    startBtn.addEventListener('click', startPipeline);
  }

  // Stop pipeline button
  const stopBtn = document.getElementById('stop-pipeline-btn');
  if (stopBtn) {
    stopBtn.addEventListener('click', stopPipeline);
  }

  // Modal close events
  const modalOverlay = document.getElementById('modal-overlay-alert');
  const modalCloseBtn = document.getElementById('modal-close-alert-btn');

  if (modalOverlay) {
    modalOverlay.addEventListener('click', closeAlertReviewModal);
  }

  if (modalCloseBtn) {
    modalCloseBtn.addEventListener('click', closeAlertReviewModal);
  }

  // ESC key to close modal
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      const modal = document.getElementById('alert-review-modal');
      if (modal && !modal.classList.contains('hidden')) {
        closeAlertReviewModal();
      }
    }
  });

  // Confirm and Decline buttons
  const confirmBtn = document.getElementById('btn-confirm-alert');
  const declineBtn = document.getElementById('btn-decline-alert');

  if (confirmBtn) {
    confirmBtn.addEventListener('click', () => reviewAlert('confirmed'));
  }

  if (declineBtn) {
    declineBtn.addEventListener('click', () => reviewAlert('declined'));
  }
}

// Start detection pipeline
function startPipeline() {
  const examNameInput = document.getElementById('exam-name-input');
  const examName = examNameInput.value.trim();

  if (!examName) {
    alert('Please enter an exam name before starting the pipeline.');
    examNameInput.focus();
    return;
  }

  // Create session
  activeSession = {
    session_id: `session_${Date.now()}`,
    exam_name: examName,
    start_time: new Date().toISOString(),
    camera_id: 'cam_001',
    status: 'active'
  };

  // Update UI
  const startBtn = document.getElementById('start-pipeline-btn');
  const stopBtn = document.getElementById('stop-pipeline-btn');
  const sessionStatus = document.getElementById('session-status');

  startBtn.classList.add('hidden');
  stopBtn.classList.remove('hidden');
  sessionStatus.textContent = `Active Session: ${examName}`;
  sessionStatus.classList.add('active');
  examNameInput.disabled = true;

  // Start session timer
  sessionStartTime = Date.now();
  startSessionTimer();

  // Simulate alerts for demo (remove when backend is connected)
  simulateRealTimeAlerts();

  console.log('Pipeline started:', activeSession);
}

// Stop detection pipeline
function stopPipeline() {
  if (!activeSession) return;

  // Check if there are pending alerts
  if (pendingAlerts.length > 0) {
    const confirmStop = confirm(
      `You have ${pendingAlerts.length} pending alert(s) that haven't been reviewed.\n\n` +
      `You must review all alerts before stopping the session.\n\n` +
      `Please review all pending alerts first.`
    );

    if (!confirmStop) {
      return; // Don't stop the session
    }

    // User confirmed, but alerts remain for review
  }

  // Update session status
  activeSession.status = 'stopped';
  activeSession.end_time = new Date().toISOString();

  // Update UI
  const startBtn = document.getElementById('start-pipeline-btn');
  const stopBtn = document.getElementById('stop-pipeline-btn');
  const sessionStatus = document.getElementById('session-status');
  const examNameInput = document.getElementById('exam-name-input');

  startBtn.classList.remove('hidden');
  stopBtn.classList.add('hidden');
  sessionStatus.textContent = 'Session Stopped - Review Remaining Alerts';
  sessionStatus.classList.remove('active');
  examNameInput.disabled = false;
  examNameInput.value = '';

  // Stop timer - THIS IS THE FIX
  if (sessionTimer) {
    clearInterval(sessionTimer);
    sessionTimer = null;
  }

  // DO NOT clear pending alerts - keep them for review
  // pendingAlerts = []; // REMOVED - alerts stay until reviewed

  // Reset statistics immediately when stopping session
  sessionStatistics = {
    totalAlerts: 0,
    confirmedAlerts: 0,
    declinedAlerts: 0
  };
  updateStatistics();

  // Alerts remain for review but statistics are reset
  console.log('Pipeline stopped. Statistics reset. Pending alerts remain for review:', pendingAlerts.length);

  // Update session status message if alerts remain
  if (pendingAlerts.length > 0) {
    sessionStatus.textContent = `Session Stopped - ${pendingAlerts.length} Alert(s) Pending Review`;
    sessionStatus.style.color = '#FFB84D'; // Orange warning color
  }
}

// Start session timer
function startSessionTimer() {
  updateSessionTimer();
  sessionTimer = setInterval(updateSessionTimer, 1000);
}

// Update session timer display
function updateSessionTimer() {
  const elapsed = Math.floor((Date.now() - sessionStartTime) / 1000);
  const hours = Math.floor(elapsed / 3600);
  const minutes = Math.floor((elapsed % 3600) / 60);
  const seconds = elapsed % 60;

  const timeString = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;

  const timeElement = document.getElementById('video-time');
  if (timeElement) {
    timeElement.textContent = timeString;
  }
}

// Simulate real-time alerts (for demo - remove when backend connected)
function simulateRealTimeAlerts() {
  // Generate alerts at random intervals
  const alertInterval = setInterval(() => {
    if (!activeSession || activeSession.status !== 'active') {
      clearInterval(alertInterval);
      return;
    }

    // 30% chance of generating an alert every 5 seconds
    if (Math.random() < 0.3) {
      generateMockAlert();
    }
  }, 5000);
}

// Generate mock alert
function generateMockAlert() {
  const eventTypes = [
    { value: 'phone', label: 'Phone Detected', icon: 'bx-mobile' },
    { value: 'looking_away', label: 'Looking Away', icon: 'bx-show-alt' },
    { value: 'multiple_people', label: 'Multiple People', icon: 'bx-group' },
    { value: 'suspicious_object', label: 'Suspicious Object', icon: 'bx-error' }
  ];

  const severities = ['high', 'medium', 'low'];
  const eventType = eventTypes[Math.floor(Math.random() * eventTypes.length)];
  const severity = severities[Math.floor(Math.random() * severities.length)];

  const alert = {
    event_id: `event_${Date.now()}`,
    session_id: activeSession.session_id,
    timestamp: new Date().toISOString(),
    suspicion_score: Math.floor(Math.random() * 30 + 70), // 70-100
    reasons: [eventType.label],
    event_type: eventType.value,
    severity: severity,
    status: 'pending',
    // Mock image (replace with actual evidence when backend connected)
    evidence_thumbnail: 'static/assets/studentTestPic.png'
  };

  pendingAlerts.unshift(alert);
  sessionStatistics.totalAlerts++;

  // Play sound notification based on severity
  playAlertSound(severity);

  renderAlerts();
  updateStatistics();
}

// Render alerts in the panel
function renderAlerts() {
  const alertsList = document.getElementById('alerts-list');
  const noAlertsState = document.getElementById('no-alerts-state');
  const alertsCount = document.getElementById('alerts-count');

  if (pendingAlerts.length === 0) {
    // Remove all alert cards but keep no-alerts-state
    const alertCards = alertsList.querySelectorAll('.alert-card');
    alertCards.forEach(card => card.remove());

    // Show empty state
    if (noAlertsState) noAlertsState.style.display = 'flex';
    if (alertsCount) alertsCount.textContent = '0 Pending';
    return;
  }

  // Hide empty state when there are alerts
  if (noAlertsState) noAlertsState.style.display = 'none';
  if (alertsCount) alertsCount.textContent = `${pendingAlerts.length} Pending`;

  // Generate alert cards HTML
  const alertCardsHTML = pendingAlerts.map(alert => {
    const timeAgo = getTimeAgo(new Date(alert.timestamp));

    return `
      <div class="alert-card" data-alert-id="${alert.event_id}">
        <div class="alert-card-header">
          <img src="${alert.evidence_thumbnail}" alt="Alert Evidence" class="alert-thumbnail">
          <div class="alert-card-info">
            <span class="alert-severity-badge alert-severity-${alert.severity}">${alert.severity}</span>
            <span class="alert-reason">${alert.reasons.join(', ')}</span>
          </div>
        </div>
        <div class="alert-card-footer">
          <span class="alert-time">
            <i class='bx bx-time'></i>
            ${timeAgo}
          </span>
          <button class="btn-review-alert" onclick="openAlertReviewModal('${alert.event_id}')">
            Review
          </button>
        </div>
      </div>
    `;
  }).join('');

  // Remove existing alert cards
  const existingCards = alertsList.querySelectorAll('.alert-card');
  existingCards.forEach(card => card.remove());

  // Insert new alert cards before no-alerts-state (or at the beginning)
  if (noAlertsState) {
    noAlertsState.insertAdjacentHTML('beforebegin', alertCardsHTML);
  } else {
    alertsList.innerHTML = alertCardsHTML;
  }
}

// Open alert review modal
function openAlertReviewModal(eventId) {
  const alert = pendingAlerts.find(a => a.event_id === eventId);
  if (!alert) return;

  const modal = document.getElementById('alert-review-modal');

  // Populate alert details
  document.getElementById('alert-evidence-image').src = alert.evidence_thumbnail;
  document.getElementById('alert-suspicion-score').textContent = `${alert.suspicion_score}%`;
  document.getElementById('alert-timestamp').textContent = formatTimestamp(new Date(alert.timestamp));
  document.getElementById('alert-reasons').textContent = alert.reasons.join(', ');

  // Clear form
  document.getElementById('student-id-input').value = '';
  document.getElementById('student-name-input').value = '';
  document.getElementById('review-notes-input').value = '';

  // Store current alert ID for review
  modal.dataset.alertId = eventId;

  // Show modal
  modal.classList.remove('hidden');
  document.body.style.overflow = 'hidden';
}

// Close alert review modal
function closeAlertReviewModal() {
  const modal = document.getElementById('alert-review-modal');
  modal.classList.add('hidden');
  document.body.style.overflow = '';
  delete modal.dataset.alertId;
}

// Review alert (confirm or decline)
function reviewAlert(decision) {
  const modal = document.getElementById('alert-review-modal');
  const eventId = modal.dataset.alertId;

  if (!eventId) return;

  // Get form values
  const studentId = document.getElementById('student-id-input').value.trim();
  const studentName = document.getElementById('student-name-input').value.trim();
  const notes = document.getElementById('review-notes-input').value.trim();

  // Validate required fields based on decision
  if (decision === 'confirmed') {
    // For confirmation, require at least ID or name (preferably both)
    if (!studentId && !studentName) {
      alert('For confirmed cheating, please enter at least Student ID or Student Name.');
      return;
    }
  }
  // For decline, student info is optional (no validation needed)

  // Find the alert
  const alertIndex = pendingAlerts.findIndex(a => a.event_id === eventId);
  if (alertIndex === -1) return;

  const alert = pendingAlerts[alertIndex];

  // Update alert with student info and decision
  alert.status = decision;

  // Only add student info if provided
  if (studentId || studentName) {
    alert.student_info = {
      student_id: studentId || 'N/A',
      student_name: studentName || 'N/A'
    };
  }

  alert.proctor_review = {
    decision: decision,
    notes: notes,
    reviewed_at: new Date().toISOString()
  };

  // Update statistics
  if (decision === 'confirmed') {
    sessionStatistics.confirmedAlerts++;
  } else if (decision === 'declined') {
    sessionStatistics.declinedAlerts++;
  }

  // Remove from pending alerts
  pendingAlerts.splice(alertIndex, 1);

  // TODO: Send to backend when integrated
  console.log('Alert reviewed:', alert);

  // Update UI
  renderAlerts();
  updateStatistics();
  closeAlertReviewModal();

  // Show notification
  const action = decision === 'confirmed' ? 'Confirmed' : 'Declined';
  const studentInfo = (studentName || studentId)
    ? `Student: ${studentName || 'Unknown'} (${studentId || 'No ID'})`
    : 'No student info provided';
  showNotification(`Alert ${action}`, studentInfo);

  // If all alerts are reviewed and session was stopped, fully reset
  if (pendingAlerts.length === 0 && (!activeSession || activeSession.status === 'stopped')) {
    setTimeout(() => {
      // Reset session completely
      const sessionStatus = document.getElementById('session-status');
      if (sessionStatus) {
        sessionStatus.textContent = 'No Active Session';
        sessionStatus.style.color = ''; // Reset color
      }

      // Reset statistics
      sessionStatistics = {
        totalAlerts: 0,
        confirmedAlerts: 0,
        declinedAlerts: 0
      };
      updateStatistics();

      activeSession = null;
      console.log('All alerts reviewed. Session fully reset.');
    }, 500);
  }
}

// Update statistics display
function updateStatistics() {
  document.getElementById('total-alerts-stat').textContent = sessionStatistics.totalAlerts;
  document.getElementById('confirmed-alerts-stat').textContent = sessionStatistics.confirmedAlerts;
  document.getElementById('declined-alerts-stat').textContent = sessionStatistics.declinedAlerts;
}

// Helper: Get time ago string
function getTimeAgo(date) {
  const seconds = Math.floor((new Date() - date) / 1000);

  if (seconds < 60) return 'Just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

// Helper: Format timestamp
function formatTimestamp(date) {
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}

// Helper: Show notification
function showNotification(title, message) {
  // Simple console notification for now
  console.log(`[${title}] ${message}`);

  // TODO: Implement proper notification UI when ready
}

// ============================================
// IMAGE ZOOM FUNCTIONALITY
// ============================================

function openImageZoom(imageSrc) {
  const lightbox = document.getElementById('image-zoom-lightbox');
  const zoomedImage = document.getElementById('zoomed-image');
  const topHeader = document.querySelector('.top-header');

  zoomedImage.src = imageSrc;
  lightbox.classList.remove('hidden');
  document.body.style.overflow = 'hidden';

  // Blur top header
  if (topHeader) {
    topHeader.classList.add('blur-background');
  }
}

function closeImageZoom() {
  const lightbox = document.getElementById('image-zoom-lightbox');
  const topHeader = document.querySelector('.top-header');

  lightbox.classList.add('hidden');
  document.body.style.overflow = '';

  // Remove blur from top header
  if (topHeader) {
    topHeader.classList.remove('blur-background');
  }
}

// ============================================
// SOUND NOTIFICATION SYSTEM
// ============================================

// Create beep sound using Web Audio API
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

// Setup sound toggle button
function setupSoundToggle() {
  const soundToggleBtn = document.getElementById('sound-toggle-btn');
  const soundIcon = document.getElementById('sound-icon');

  if (!soundToggleBtn) return;

  soundToggleBtn.addEventListener('click', () => {
    soundEnabled = !soundEnabled;

    if (soundEnabled) {
      // Sound ON
      soundToggleBtn.classList.add('active');
      soundToggleBtn.title = 'Alert Sounds: ON';
      soundIcon.classList.remove('bx-volume-mute');
      soundIcon.classList.add('bx-volume-full');

      // Play test sound
      alertSounds.medium();
    } else {
      // Sound OFF
      soundToggleBtn.classList.remove('active');
      soundToggleBtn.title = 'Alert Sounds: OFF';
      soundIcon.classList.remove('bx-volume-full');
      soundIcon.classList.add('bx-volume-mute');
    }
  });
}

// Play alert sound based on severity
function playAlertSound(severity) {
  if (!soundEnabled) return;

  const soundFunction = alertSounds[severity] || alertSounds.medium;
  soundFunction();
}
