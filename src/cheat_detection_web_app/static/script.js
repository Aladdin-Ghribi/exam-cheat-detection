const socket = io();
const canvas = document.getElementById('displayCanvas');
const ctx = canvas.getContext('2d');
const webcamBtn = document.getElementById('webcam-btn');
const fileUpload = document.getElementById('file-upload');
const fileNameSpan = document.getElementById('file-name');
const settingsBtn = document.getElementById('settings-btn');
const settingsModal = document.getElementById('settings-modal');
const closeModal = document.querySelector('.close');
const viewToggleBtn = document.getElementById('view-toggle-btn');
const mainElement = document.querySelector('main');

let stream = null;
let videoElement = null;
let isProcessing = false;
let poseEnabled = true;
let isInstructorView = false;

// View toggle - Start in monitoring view
mainElement.classList.add('monitoring-view');
viewToggleBtn.innerHTML = '👨🏫 Instructor View';

viewToggleBtn.onclick = () => {
  isInstructorView = !isInstructorView;
  if (isInstructorView) {
    mainElement.classList.remove('monitoring-view');
    viewToggleBtn.innerHTML = '📺 Monitoring View';
    viewToggleBtn.title = 'Switch to monitoring-only view';
  } else {
    mainElement.classList.add('monitoring-view');
    viewToggleBtn.innerHTML = '👨🏫 Instructor View';
    viewToggleBtn.title = 'Switch to instructor view with seat map and events';
  }
};

// Settings modal
settingsBtn.onclick = () => settingsModal.style.display = 'block';
closeModal.onclick = () => settingsModal.style.display = 'none';
window.onclick = (e) => { if (e.target == settingsModal) settingsModal.style.display = 'none'; };

// Webcam
webcamBtn.onclick = async () => {
  if (stream) return;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: true });
    videoElement = document.createElement('video');
    videoElement.srcObject = stream;
    videoElement.play();
    videoElement.onloadedmetadata = () => {
      canvas.width = 640;
      canvas.height = 480;
      processFrame();
    };
    webcamBtn.classList.add('active');
  } catch (err) {
    alert('Camera access denied');
  }
};

// File upload
fileUpload.onchange = async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  
  fileNameSpan.textContent = file.name;
  
  if (stream) {
    stream.getTracks().forEach(t => t.stop());
    stream = null;
  }
  
  const formData = new FormData();
  formData.append('file', file);
  
  const res = await fetch('/upload', { method: 'POST', body: formData });
  const data = await res.json();
  
  if (data.success && data.file_type === 'video') {
    videoElement = document.createElement('video');
    videoElement.src = URL.createObjectURL(file);
    videoElement.play();
    videoElement.onloadedmetadata = () => {
      canvas.width = videoElement.videoWidth;
      canvas.height = videoElement.videoHeight;
      processFrame();
    };
  }
};

function processFrame() {
  if (!videoElement || isProcessing) {
    requestAnimationFrame(processFrame);
    return;
  }
  
  if (videoElement.paused || videoElement.ended) {
    requestAnimationFrame(processFrame);
    return;
  }
  
  isProcessing = true;
  
  const tempCanvas = document.createElement('canvas');
  tempCanvas.width = videoElement.videoWidth || 640;
  tempCanvas.height = videoElement.videoHeight || 480;
  const tempCtx = tempCanvas.getContext('2d');
  tempCtx.drawImage(videoElement, 0, 0);
  
  const frameData = tempCanvas.toDataURL('image/jpeg', 0.85);
  socket.emit('video_frame', { image: frameData, pose_enabled: poseEnabled });
  
  requestAnimationFrame(processFrame);
}

socket.on('processed_frame', (data) => {
  const img = new Image();
  img.onload = () => {
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    updateSeatMap(data.seat_assignments, data.detections);
    updateEventLog(data.detections);
  };
  img.src = 'data:image/jpeg;base64,' + data.annotated_frame;
  isProcessing = false;
});

// Refresh seat map when threshold changes
setInterval(() => {
  if (Object.keys(currentSeats).length > 0) {
    updateSeatMap(currentSeats, currentDetections);
  }
}, 1000);

let currentSeats = {};
let currentDetections = [];

function updateSeatMap(seats, detections) {
  currentSeats = seats;
  currentDetections = detections;
  
  const grid = document.getElementById('seat-map-grid');
  grid.innerHTML = '';
  
  if (!seats || Object.keys(seats).length === 0) {
    grid.innerHTML = '<p style="grid-column: 1/-1; text-align:center; color:#94a3b8;">No students detected</p>';
    return;
  }
  
  Object.entries(seats).forEach(([trackId, seatId]) => {
    const det = detections.find(d => d.track_id == trackId);
    
    // Get score from multiple possible locations
    let score = 0;
    if (det?.behavior?.suspicion) {
      score = det.behavior.suspicion.suspicion_score_100 || 
              Math.round((det.behavior.suspicion.smoothed || 0) * 100);
    }
    
    console.log(`Seat ${seatId}, Track ${trackId}, Score: ${score}`);
    
    const div = document.createElement('div');
    div.className = 'seat-item';
    
    // Alert if score >= 70, Suspicious if >= 40, Active otherwise
    if (score >= 70) {
      div.classList.add('alert');
    } else if (score >= 40) {
      div.classList.add('suspicious');
    } else {
      div.classList.add('active');
    }
    
    const statusText = score >= 70 ? 'ALERT' : score >= 40 ? 'FLAGGED' : 'ACTIVE';
    div.innerHTML = `
      <div style="font-size: 1rem; font-weight: 600;">Seat ${seatId}</div>
      <div style="font-size: 0.75rem; opacity: 0.9;">ID: ${trackId}</div>
      <div style="font-size: 0.8rem; font-weight: 600; margin-top: 0.25rem;">${score}%</div>
      <div style="font-size: 0.7rem; opacity: 0.8;">${statusText}</div>
    `;
    div.title = `Student ${trackId} - ${statusText} - Suspicion: ${score}%`;
    grid.appendChild(div);
  });
}

let allEvents = [];
let studentIds = new Set();

function updateEventLog(detections) {
  const suspicionThreshold = parseInt(document.getElementById('suspicion-threshold').value);
  
  detections.forEach(det => {
    // Skip non-person detections
    if (det.class_id !== 0) return;
    
    const score = det.behavior?.suspicion?.suspicion_score_100 || 0;
    
    // Only log if score meets threshold
    if (score < suspicionThreshold) return;
    
    const studentId = det.track_id || 'Unknown';
    studentIds.add(studentId);
    
    const severity = score >= 70 ? 'high' : score >= 40 ? 'medium' : 'low';
    const event = {
      time: new Date().toLocaleTimeString(),
      studentId,
      score,
      severity,
      description: getEventDescription(det)
    };
    
    // Avoid duplicate events (check if same student with similar score in last second)
    const isDuplicate = allEvents.some(e => 
      e.studentId === studentId && 
      Math.abs(e.score - score) < 5 &&
      (new Date() - new Date('1970-01-01 ' + e.time)) < 1000
    );
    
    if (!isDuplicate) {
      allEvents.unshift(event);
      if (allEvents.length > 100) allEvents.pop();
    }
  });
  
  updateStudentFilter();
  renderEvents();
  updateStats();
}

function getEventDescription(det) {
  const behavior = det.behavior || {};
  const reasons = [];
  
  if (behavior.head_orientation) {
    const yaw = Math.abs(behavior.head_orientation.yaw);
    const pitch = Math.abs(behavior.head_orientation.pitch);
    if (yaw > 30) reasons.push(`Head turned ${yaw.toFixed(0)}°`);
    if (pitch > 20) reasons.push(`Head tilted ${pitch.toFixed(0)}°`);
  }
  
  if (behavior.hands) {
    ['left', 'right'].forEach(side => {
      const hand = behavior.hands[side];
      if (hand?.near_object) reasons.push(`${side} hand near object`);
      if (hand?.near_face) reasons.push(`${side} hand near face`);
    });
  }
  
  return reasons.length > 0 ? reasons.join(', ') : 'Suspicious behavior';
}

function renderEvents() {
  const log = document.getElementById('event-log-list');
  const severityFilter = document.getElementById('severity-filter').value;
  const studentFilter = document.getElementById('student-filter').value;
  const suspicionThreshold = parseInt(document.getElementById('suspicion-threshold').value);
  
  const filtered = allEvents.filter(e => {
    const matchSeverity = severityFilter === 'all' || e.severity === severityFilter;
    const matchStudent = studentFilter === 'all' || e.studentId == studentFilter;
    const matchThreshold = e.score >= suspicionThreshold;
    return matchSeverity && matchStudent && matchThreshold;
  });
  
  log.innerHTML = '';
  
  if (filtered.length === 0) {
    log.innerHTML = '<p style="text-align:center; color:#94a3b8; padding:2rem;">No events match filters</p>';
    return;
  }
  
  filtered.slice(0, 20).forEach(event => {
    const div = document.createElement('div');
    div.className = `event-item ${event.severity}`;
    div.innerHTML = `
      <div class="event-time">${event.time}</div>
      <div class="event-student">Student ID: ${event.studentId} • Score: ${event.score}%</div>
      <div class="event-desc">${event.description}</div>
    `;
    log.appendChild(div);
  });
  
  updateStats();
}

function updateStudentFilter() {
  const filter = document.getElementById('student-filter');
  const currentValue = filter.value;
  
  filter.innerHTML = '<option value="all">All Students</option>';
  Array.from(studentIds).sort((a, b) => a - b).forEach(id => {
    const opt = document.createElement('option');
    opt.value = id;
    opt.textContent = `Student ${id}`;
    filter.appendChild(opt);
  });
  
  filter.value = currentValue;
}

function updateStats() {
  document.getElementById('student-count').textContent = studentIds.size;
  document.getElementById('flagged-count').textContent = allEvents.filter(e => e.severity === 'high').length;
  document.getElementById('event-count').textContent = allEvents.length;
}

// Settings controls with real-time feedback
function showFeedback(elementId, message, duration = 2000) {
  const feedback = document.getElementById(elementId);
  feedback.textContent = message;
  feedback.classList.add('show');
  setTimeout(() => feedback.classList.remove('show'), duration);
}

document.getElementById('toggle-pose-btn').onchange = (e) => {
  poseEnabled = e.target.checked;
  showFeedback('param-feedback', `Pose detection ${e.target.checked ? 'enabled' : 'disabled'}`);
  renderEvents();
};

document.getElementById('yaw-threshold').oninput = (e) => {
  document.getElementById('yaw-value').textContent = e.target.value + '°';
  showFeedback('param-feedback', `Yaw threshold updated to ${e.target.value}°`);
  renderEvents();
};

document.getElementById('pitch-threshold').oninput = (e) => {
  document.getElementById('pitch-value').textContent = e.target.value + '°';
  showFeedback('param-feedback', `Pitch threshold updated to ${e.target.value}°`);
  renderEvents();
};

document.getElementById('suspicion-threshold').oninput = (e) => {
  document.getElementById('suspicion-value').textContent = e.target.value;
  socket.emit('update_suspicion_threshold', { threshold: parseInt(e.target.value) });
  showFeedback('param-feedback', `Suspicion threshold updated to ${e.target.value}`);
  renderEvents();
  updateSeatMap({}, []);
};

document.getElementById('model-size').onchange = (e) => {
  socket.emit('switch_model', { model_size: e.target.value });
  showFeedback('perf-feedback', `Switching to ${e.target.value} model...`);
};

document.getElementById('frame-skip-toggle').onchange = (e) => {
  socket.emit('toggle_frame_skipping', { enabled: e.target.checked });
  showFeedback('perf-feedback', `Frame skipping ${e.target.checked ? 'enabled' : 'disabled'}`);
};

document.getElementById('auto-save-toggle').onchange = (e) => {
  socket.emit('toggle_auto_save', { enabled: e.target.checked });
  showFeedback('export-feedback', `Auto-save ${e.target.checked ? 'enabled' : 'disabled'}`);
};

document.getElementById('export-json-btn').onclick = () => {
  socket.emit('export_data', { format: 'json' });
  showFeedback('export-feedback', 'Exporting JSON...');
};

document.getElementById('export-csv-btn').onclick = () => {
  socket.emit('export_data', { format: 'csv' });
  showFeedback('export-feedback', 'Exporting CSV...');
};

document.getElementById('export-zip-btn').onclick = () => {
  socket.emit('export_data', { format: 'zip' });
  showFeedback('export-feedback', 'Exporting ZIP...');
};

socket.on('export_ready', (data) => {
  const a = document.createElement('a');
  a.href = data.download_url;
  a.download = data.filename;
  a.click();
  showFeedback('export-feedback', `Downloaded: ${data.filename}`);
});

socket.on('save_notification', (data) => {
  const status = document.getElementById('save-status');
  status.textContent = data.message;
  status.style.display = 'block';
  status.style.background = data.type === 'success' ? '#d1fae5' : data.type === 'error' ? '#fee2e2' : '#dbeafe';
  setTimeout(() => status.style.display = 'none', 3000);
  
  if (data.type === 'success') {
    showFeedback('perf-feedback', data.message);
  }
});

// Filters
document.getElementById('severity-filter').onchange = renderEvents;
document.getElementById('student-filter').onchange = renderEvents;

document.getElementById('clear-log-btn').onclick = () => {
  if (confirm('Clear all events?')) {
    allEvents = [];
    renderEvents();
    updateStats();
  }
};

// Auto-start webcam
socket.on('connect', () => {
  console.log('Connected to server');
  setTimeout(() => webcamBtn.click(), 500);
});

// Initialize
renderEvents();
updateStats();