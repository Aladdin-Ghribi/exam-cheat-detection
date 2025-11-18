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
const togglePoseBtn = document.getElementById('toggle-pose-btn');
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

togglePoseBtn.addEventListener('click', () => {
  poseEnabled = !poseEnabled;
  togglePoseBtn.textContent = poseEnabled ? 'Hide Pose' : 'Show Pose';
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
      html += `Pitch: ${ho.pitch.toFixed(1)}° | Yaw: ${ho.yaw.toFixed(1)}°</div>`;
      
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
    let score = 0;
    let reasons = [];
    
    if (det.behavior) {
      const behavior = det.behavior;
      
      if (behavior.head_orientation) {
        const ho = behavior.head_orientation;
        if (Math.abs(ho.yaw) > yawThreshold) {
          const yawScore = Math.min(30, Math.abs(ho.yaw) - yawThreshold);
          score += yawScore;
          reasons.push(`Head turned ${Math.abs(ho.yaw).toFixed(0)}° (yaw)`);
        }
        if (Math.abs(ho.pitch) > pitchThreshold) {
          const pitchScore = Math.min(20, Math.abs(ho.pitch) - pitchThreshold);
          score += pitchScore;
          reasons.push(`Head tilted ${Math.abs(ho.pitch).toFixed(0)}° (pitch)`);
        }
      }
      
      if (behavior.hands) {
        ['left', 'right'].forEach(side => {
          const hand = behavior.hands[side];
          if (hand && hand.visible) {
            if (hand.near_object && hand.object_class) {
              score += 40;
              reasons.push(`${side} hand near ${hand.object_class}`);
            } else if (hand.near_face) {
              score += 15;
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
      score += 30;
      reasons.push(`${className} detected nearby`);
    });
    
    score = Math.min(100, Math.round(score));
    
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
});

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
  showSaveStatus(`Auto-save ${autoSaveEnabled ? 'enabled' : 'disabled'}`);
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
