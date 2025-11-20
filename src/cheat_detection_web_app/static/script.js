// script.js
const socket = io();
const displayCanvas = document.getElementById('displayCanvas');
const displayCtx = displayCanvas.getContext('2d');
const metricsContent = document.getElementById('metrics-content');
const seatAssignmentsDiv = document.getElementById('seat-assignments');
const behaviorContent = document.getElementById('behavior-content');
const scoringContent = document.getElementById('scoring-content');

const CONFIG_YAW_THRESHOLD = 30;
const CONFIG_PITCH_THRESHOLD = 20;
const CONFIG_SUSPICION_THRESHOLD = 20;

let yawThreshold = CONFIG_YAW_THRESHOLD;
let pitchThreshold = CONFIG_PITCH_THRESHOLD;
let suspicionThreshold = CONFIG_SUSPICION_THRESHOLD;

const webcamBtn = document.getElementById('webcam-btn');
const fileUploadInput = document.getElementById('file-upload');
const fileInfo = document.getElementById('file-info');
const fileName = document.getElementById('file-name');
const resetBtn = document.getElementById('reset-btn');
const togglePoseBtn = document.getElementById('toggle-pose-check');
const settingsToggleBtn = document.getElementById('settings-toggle-btn');
const settingsPanel = document.getElementById('settings-panel');
const filterSeverity = document.getElementById('filter-severity');
const filterStudent = document.getElementById('filter-student');
const modelSizeSelect = document.getElementById('model-size');
const frameSkipToggle = document.getElementById('frame-skip-toggle');
const processTimeSpan = document.getElementById('process-time');
const frameCountSpan = document.getElementById('frame-count');

let stream = null;
let videoElement = null;
let isProcessing = false;
let lastProcessedTime = 0;
const PROCESS_INTERVAL_MS = 50;
let sourceType = 'webcam';
let animationFrameId = null;
let poseEnabled = true;
let autoSaveEnabled = true;
let currentFrame = null;
let currentDetections = null;
let frameCount = 0;
let eventLogEntries = [];
let allEventLogEntries = [];
let activeStudents = new Set();

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

    videoElement = document.createElement('video');
    videoElement.srcObject = stream;

    videoElement.onloadedmetadata = () => {
      displayCanvas.width = 640;
      displayCanvas.height = 480;
      processFrame(videoElement);
    };

    videoElement.play();
  } catch (err) {
    console.error('Webcam access denied:', err);
    alert('Camera access required. Please allow and refresh.');
  }
}

async function processFile(file) {
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId);
  }

  if (stream) {
    stream.getTracks().forEach(track => track.stop());
    stream = null;
  }

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

    const fileType = file.type.split('/')[0];

    if (fileType === 'video') {
      videoElement = document.createElement('video');
      videoElement.src = URL.createObjectURL(file);
      videoElement.play();

      videoElement.onloadedmetadata = () => {
        displayCanvas.width = videoElement.videoWidth;
        displayCanvas.height = videoElement.videoHeight;
        processFrame(videoElement);
      };
    } else if (fileType === 'image') {
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

      const img = new Image();
      img.onload = () => {
        displayCanvas.width = img.width;
        displayCanvas.height = img.height;
        displayCtx.drawImage(img, 0, 0);
        updateMetrics(processResult.metrics);
        updateSeatAssignments(processResult.seat_assignments);
        updateBehaviorAnalysis(processResult.detections);
        updateSuspicionScores(processResult.detections);
      };
      img.src = `data:image/jpeg;base64,${processResult.annotated_frame}`;
    }

    fileName.textContent = file.name;
    fileInfo.style.display = 'flex';
    webcamBtn.classList.remove('active');

  } catch (error) {
    console.error('Error processing file:', error);
    alert(`Error: ${error.message}`);
    resetToWebcam();
  }
}

function resetToWebcam() {
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId);
  }

  if (videoElement && videoElement.pause) {
    videoElement.pause();
    videoElement.src = '';
  }

  fileInfo.style.display = 'none';
  webcamBtn.classList.add('active');
  fileUploadInput.value = '';

  displayCanvas.width = 640;
  displayCanvas.height = 480;

  displayCtx.clearRect(0, 0, displayCanvas.width, displayCanvas.height);

  startWebcam();
}

function processFrame(videoElement) {
  if (!videoElement || isProcessing) {
    animationFrameId = requestAnimationFrame(() => processFrame(videoElement));
    return;
  }

  if (videoElement.tagName === 'VIDEO' && (videoElement.paused || videoElement.ended)) {
    if (videoElement.ended) {
      console.log('Video playback ended');
      return;
    }
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

  const captureCanvas = document.createElement('canvas');
  captureCanvas.width = videoElement.videoWidth || videoElement.width || 640;
  captureCanvas.height = videoElement.videoHeight || videoElement.height || 480;
  const captureCtx = captureCanvas.getContext('2d');
  captureCtx.drawImage(videoElement, 0, 0, captureCanvas.width, captureCanvas.height);

  const frameDataUrl = captureCanvas.toDataURL('image/jpeg', 0.85);
  socket.emit('video_frame', { image: frameDataUrl, pose_enabled: poseEnabled });

  animationFrameId = requestAnimationFrame(() => processFrame(videoElement));
}

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

settingsToggleBtn.addEventListener('click', () => {
  settingsPanel.style.display = settingsPanel.style.display === 'none' ? 'block' : 'none';
});

togglePoseBtn.addEventListener('change', (e) => {
  poseEnabled = e.target.checked;
});

filterSeverity.addEventListener('change', () => {
  applyEventFilters();
});

filterStudent.addEventListener('change', () => {
  applyEventFilters();
});

modelSizeSelect.addEventListener('change', (e) => {
  const modelSize = e.target.value;
  socket.emit('switch_model', { model_size: modelSize });
  console.log(`Switching to ${modelSize} model`);
});

frameSkipToggle.addEventListener('change', (e) => {
  socket.emit('toggle_frame_skipping', { enabled: e.target.checked });
  console.log(`Frame skipping ${e.target.checked ? 'enabled' : 'disabled'}`);
});

document.getElementById('yaw-threshold').addEventListener('input', (e) => {
  yawThreshold = parseInt(e.target.value);
  document.getElementById('yaw-value').textContent = yawThreshold;
});

document.getElementById('pitch-threshold').addEventListener('input', (e) => {
  pitchThreshold = parseInt(e.target.value);
  document.getElementById('pitch-value').textContent = pitchThreshold;
});

document.getElementById('suspicion-threshold').addEventListener('input', (e) => {
  suspicionThreshold = parseInt(e.target.value);
  document.getElementById('suspicion-value').textContent = suspicionThreshold;
  socket.emit('update_suspicion_threshold', { threshold: suspicionThreshold });
});

socket.on('processed_frame', (data) => {
  frameCount++;
  frameCountSpan.textContent = frameCount;
  
  if (data.performance_stats) {
    processTimeSpan.textContent = data.performance_stats.last_process_time_ms.toFixed(1);
  }

  const img = new Image();
  img.onload = () => {
    if (sourceType === 'webcam' && (displayCanvas.width !== 640 || displayCanvas.height !== 480)) {
      displayCanvas.width = 640;
      displayCanvas.height = 480;
    }

    displayCtx.drawImage(img, 0, 0, displayCanvas.width, displayCanvas.height);
    updateMetrics(data.metrics);
    updateSeatAssignments(data.seat_assignments);
    updateSeatMap(data.seat_map_data);
    updateEventLog(data.flagged_events);
    updateBehaviorAnalysis(data.detections);
    updateSuspicionScores(data.detections);
    
    currentFrame = data.annotated_frame;
    currentDetections = data.detections;
  };
  img.src = `data:image/jpeg;base64,${data.annotated_frame}`;
  isProcessing = false;
});

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

function updateSeatAssignments(seatAssignments) {
  if (!seatAssignmentsDiv) return;
  
  if (seatAssignments && Object.keys(seatAssignments).length > 0) {
    let seatHtml = '<ul style="list-style-type: none; padding-left: 0;">';
    for (const [trackId, seatIndex] of Object.entries(seatAssignments)) {
      seatHtml += `<li style="margin: 5px 0; padding: 5px; background: #e6f7ff; border-radius: 4px;">Person ID ${trackId} → Seat ${seatIndex}</li>`;
    }
    seatHtml += '</ul>';
    seatAssignmentsDiv.innerHTML = seatHtml;
  } else {
    seatAssignmentsDiv.innerHTML = 'No active seat assignments';
  }
}

function updateBehaviorAnalysis(detections) {
  if (!behaviorContent || !detections) return;
  
  const personDetections = detections.filter(d => d.class_id === 0 && d.behavior);
  
  if (personDetections.length === 0) {
    behaviorContent.innerHTML = 'No behavior data available';
    return;
  }
  
  let html = '';
  personDetections.forEach(det => {
    const behavior = det.behavior;
    const trackId = det.track_id || 'Unknown';
    
    html += `<div style="margin-bottom: 15px; padding: 8px; background: white; border-left: 3px solid #ffc107; border-radius: 4px;">`;
    html += `<strong>Person ID ${trackId}</strong><br>`;
    
    if (behavior.head_orientation) {
      const ho = behavior.head_orientation;
      html += `<div style="margin-top: 5px;"><strong>Head Angles:</strong><br>`;
      html += `Left/Right: ${ho.pitch.toFixed(1)}° | Body Roll: ${ho.yaw.toFixed(1)}°</div>`;
      
      if (Math.abs(ho.yaw) > 30 || Math.abs(ho.pitch) > 20) {
        html += `<div style="color: #d32f2f; font-weight: bold; margin-top: 3px;">⚠️ Looking away</div>`;
      }
    }
    
    if (behavior.hands) {
      html += `<div style="margin-top: 5px;"><strong>Hand Proximity:</strong><br>`;
      
      ['left', 'right'].forEach(side => {
        const hand = behavior.hands[side];
        if (hand && hand.visible) {
          const sideLabel = side.charAt(0).toUpperCase() + side.slice(1);
          html += `${sideLabel}: `;
          
          if (hand.near_face) {
            html += `<span style="color: #f57c00;">Near face (${hand.distance_to_face.toFixed(3)})</span>`;
          } else if (hand.near_object && hand.object_class) {
            html += `<span style="color: #d32f2f;">⚠️ Near ${hand.object_class}</span>`;
          } else {
            html += `<span style="color: #388e3c;">Normal</span>`;
          }
          html += `<br>`;
        }
      });
      html += `</div>`;
    }
    
    html += `</div>`;
  });
  
  behaviorContent.innerHTML = html;
}

function updateSuspicionScores(detections) {
  if (!scoringContent || !detections) return;
  
  const personDetections = detections.filter(d => d.class_id === 0);
  
  if (personDetections.length === 0) {
    scoringContent.innerHTML = 'No persons detected';
    return;
  }
  
  let html = '';
  personDetections.forEach(det => {
    const trackId = det.track_id || 'Unknown';
    const score = det.unified_score || 0;
    let reasons = [];
    
    if (det.behavior) {
      const behavior = det.behavior;
      
      if (behavior.head_orientation) {
        const ho = behavior.head_orientation;
        if (Math.abs(ho.yaw) > yawThreshold) {
          reasons.push(`Body rolled ${Math.abs(ho.yaw).toFixed(0)}°`);
        }
        if (Math.abs(ho.pitch) > pitchThreshold) {
          reasons.push(`Head left/right ${Math.abs(ho.pitch).toFixed(0)}°`);
        }
      }
      
      if (behavior.hands) {
        ['left', 'right'].forEach(side => {
          const hand = behavior.hands[side];
          if (hand && hand.visible) {
            if (hand.near_object && hand.object_class) {
              reasons.push(`${side} hand near ${hand.object_class}`);
            } else if (hand.near_face) {
              reasons.push(`${side} hand near face`);
            }
          }
        });
      }
    }
    
    const nearbyObjects = detections.filter(d => 
      d.class_id !== 0 && 
      isNearPerson(d.bbox, det.bbox)
    );
    
    nearbyObjects.forEach(obj => {
      const className = getClassName(obj.class_id);
      reasons.push(`${className} detected nearby`);
    });
    
    let alertLevel = 'low';
    let alertColor = '#4caf50';
    let alertBg = '#e8f5e9';
    
    if (score >= suspicionThreshold) {
      alertLevel = 'high';
      alertColor = '#d32f2f';
      alertBg = '#ffebee';
    } else if (score >= suspicionThreshold * 0.6) {
      alertLevel = 'medium';
      alertColor = '#f57c00';
      alertBg = '#fff3e0';
    }
    
    html += `<div style="margin-bottom: 12px; padding: 10px; background: ${alertBg}; border-left: 4px solid ${alertColor}; border-radius: 4px;">`;
    html += `<div style="display: flex; justify-content: space-between; align-items: center;">`;
    html += `<strong>Person ID ${trackId}</strong>`;
    html += `<span style="font-size: 20px; font-weight: bold; color: ${alertColor};">${score}/100</span>`;
    html += `</div>`;
    
    if (reasons.length > 0) {
      html += `<div style="margin-top: 8px; font-size: 13px;">`;
      html += `<strong>Reasons:</strong><ul style="margin: 5px 0; padding-left: 20px;">`;
      reasons.forEach(reason => {
        html += `<li>${reason}</li>`;
      });
      html += `</ul></div>`;
    } else {
      html += `<div style="margin-top: 5px; color: #666; font-size: 13px;">No suspicious behavior detected</div>`;
    }
    
    if (score >= suspicionThreshold) {
      html += `<div style="margin-top: 8px; padding: 5px; background: #d32f2f; color: white; border-radius: 3px; text-align: center; font-weight: bold;">⚠️ ALERT: High Suspicion</div>`;
    }
    
    html += `</div>`;
  });
  
  scoringContent.innerHTML = html;
}

function isNearPerson(objBbox, personBbox) {
  const [ox1, oy1, ox2, oy2] = objBbox;
  const [px1, py1, px2, py2] = personBbox;
  
  const horizontalOverlap = ox1 < px2 && ox2 > px1;
  const verticalOverlap = oy1 < py2 && oy2 > py1;
  
  return horizontalOverlap && verticalOverlap;
}

function getClassName(classId) {
  const classNames = {
    67: 'cell phone',
    73: 'book',
    63: 'laptop',
    24: 'backpack',
    26: 'handbag'
  };
  return classNames[classId] || `object ${classId}`;
}

socket.on('connect', () => {
  console.log('Connected to server');
  sourceType = 'webcam';
  startWebcam();
  loadHistoricalEvents();
  setInterval(loadHistoricalEvents, 5000); // Refresh every 5 seconds
});

function loadHistoricalEvents() {
  console.log('Loading historical events...');
  fetch('/api/historical_events')
    .then(response => {
      console.log('Response status:', response.status);
      return response.json();
    })
    .then(data => {
      console.log('Received data:', data);
      if (data.events && data.events.length > 0) {
        console.log('Found', data.events.length, 'events');
        allEventLogEntries = data.events;
        const uniqueStudents = new Set(data.events.map(e => e.track_id));
        activeStudents = uniqueStudents;
        updateStudentFilter();
        applyEventFilters();
      } else {
        console.log('No events found');
        allEventLogEntries = [];
        activeStudents = new Set();
        applyEventFilters();
      }
    })
    .catch(error => {
      console.error('Error loading historical events:', error);
    });
}

socket.on('disconnect', () => {
  console.log('Disconnected from server');
});

socket.on('error', (data) => {
  console.error('Backend error:', data.message);
});

const autoSaveToggle = document.getElementById('auto-save-toggle');
const manualSaveBtn = document.getElementById('manual-save-btn');
const exportJsonBtn = document.getElementById('export-json-btn');
const exportCsvBtn = document.getElementById('export-csv-btn');
const exportZipBtn = document.getElementById('export-zip-btn');
const saveStatus = document.getElementById('save-status');

autoSaveToggle.addEventListener('change', (e) => {
  autoSaveEnabled = e.target.checked;
  socket.emit('toggle_auto_save', { enabled: autoSaveEnabled });
});

manualSaveBtn.addEventListener('click', () => {
  if (!currentFrame || !currentDetections) {
    showSaveStatus('No frame available to save', 'error');
    return;
  }
  socket.emit('manual_save', { 
    frame: currentFrame, 
    detections: currentDetections 
  });
  showSaveStatus('Frame saved manually', 'success');
});

exportJsonBtn.addEventListener('click', () => {
  socket.emit('export_data', { format: 'json' });
});

exportCsvBtn.addEventListener('click', () => {
  socket.emit('export_data', { format: 'csv' });
});

exportZipBtn.addEventListener('click', () => {
  socket.emit('export_data', { format: 'zip' });
});

socket.on('export_ready', (data) => {
  const link = document.createElement('a');
  link.href = data.download_url;
  link.download = data.filename;
  link.click();
  showSaveStatus(`Exported: ${data.filename}`, 'success');
});

socket.on('save_notification', (data) => {
  showSaveStatus(data.message, data.type || 'info');
});

function showSaveStatus(message, type = 'info') {
  saveStatus.textContent = message;
  saveStatus.style.display = 'block';
  
  const colors = {
    success: '#e8f5e9',
    error: '#ffebee',
    info: '#e3f2fd'
  };
  saveStatus.style.background = colors[type] || colors.info;
  
  setTimeout(() => {
    saveStatus.style.display = 'none';
  }, 3000);
}

function updateSeatMap(seatMapData) {
  const seatMapGrid = document.getElementById('seat-map-grid');
  if (!seatMapGrid) return;
  
  if (!seatMapData || seatMapData.length === 0) {
    seatMapGrid.innerHTML = '<div style="text-align: center; color: #999; padding: 20px; grid-column: 1/-1;">No students detected</div>';
    return;
  }
  
  let html = '';
  seatMapData.forEach(student => {
    const det = currentDetections ? currentDetections.find(d => d.track_id === student.track_id) : null;
    const score = det ? (det.unified_score || 0) : 0;
    
    let bgColor = '#4CAF50';
    let textColor = '#fff';
    let icon = '✅';
    
    if (score >= suspicionThreshold) {
      bgColor = '#d32f2f';
      textColor = '#fff';
      icon = '🚨';
    } else if (score >= suspicionThreshold * 0.6) {
      bgColor = '#FFC107';
      textColor = '#000';
      icon = '⚠️';
    }
    
    const seatLabel = student.seat_id !== null && student.seat_id !== undefined ? `Seat ${student.seat_id}` : 'Unassigned';
    
    html += `
      <div style="
        background: ${bgColor};
        color: ${textColor};
        padding: 12px;
        border-radius: 8px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: transform 0.2s;
        cursor: pointer;
      " onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
        <div style="font-size: 24px; margin-bottom: 5px;">${icon}</div>
        <div style="font-weight: bold; font-size: 16px;">ID ${student.track_id}</div>
        <div style="font-size: 12px; margin-top: 3px; opacity: 0.9;">${seatLabel}</div>
        <div style="font-size: 11px; margin-top: 5px; padding: 3px; background: rgba(0,0,0,0.1); border-radius: 3px;">
          Score: ${score}/100
        </div>
      </div>
    `;
  });
  
  seatMapGrid.innerHTML = html;
}

function updateEventLog(flaggedEvents) {
  // Event log now loads only from output folder via loadHistoricalEvents()
  // This function is kept for compatibility but does nothing
}

function updateStudentFilter() {
  const currentValue = filterStudent.value;
  filterStudent.innerHTML = '<option value="all">All Students</option>';
  Array.from(activeStudents).sort((a, b) => a - b).forEach(id => {
    filterStudent.innerHTML += `<option value="${id}">Student ID ${id}</option>`;
  });
  filterStudent.value = currentValue;
}

function applyEventFilters() {
  const eventLog = document.getElementById('event-log');
  const severityFilter = filterSeverity.value;
  const studentFilter = filterStudent.value;
  
  let filtered = allEventLogEntries.filter(event => {
    if (studentFilter !== 'all' && event.track_id != studentFilter) return false;
    if (severityFilter === 'high' && event.score < 60) return false;
    if (severityFilter === 'medium' && (event.score < 40 || event.score >= 60)) return false;
    if (severityFilter === 'low' && (event.score < 20 || event.score >= 40)) return false;
    return true;
  });
  
  if (filtered.length === 0) {
    eventLog.innerHTML = '<div style="text-align: center; color: #999; padding: 20px;">No events match filters</div>';
    return;
  }
  
  let html = '';
  filtered.forEach((event, index) => {
    const bgColor = index % 2 === 0 ? '#fff' : '#f9f9f9';
    html += `
      <div style="
        padding: 15px;
        margin-bottom: 10px;
        background: ${bgColor};
        border-left: 4px solid #f44336;
        border-radius: 4px;
        line-height: 1.6;
      ">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
          <span style="font-weight: bold; color: #333; font-size: 14px;">Student ID ${event.track_id}</span>
          <span style="color: #666; font-size: 12px;">${event.timestamp}</span>
        </div>
        <div style="color: #555; font-size: 13px; margin-bottom: 5px;">${event.description}</div>
        <div style="display: inline-block; padding: 3px 8px; background: #ffebee; color: #d32f2f; border-radius: 3px; font-size: 11px; font-weight: bold;">
          Score: ${event.score}/100
        </div>
      </div>
    `;
  });
  
  eventLog.innerHTML = html;
}

settingsToggleBtn.addEventListener('mouseover', () => {
  settingsToggleBtn.style.background = '#3498db';
  settingsToggleBtn.style.color = 'white';
  settingsToggleBtn.style.transform = 'translateY(-2px)';
});

settingsToggleBtn.addEventListener('mouseout', () => {
  settingsToggleBtn.style.background = 'white';
  settingsToggleBtn.style.color = '#2c3e50';
  settingsToggleBtn.style.transform = 'translateY(0)';
});
