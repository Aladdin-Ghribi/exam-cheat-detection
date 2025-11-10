// script.js
const socket = io(); // Connect to Flask-SocketIO server
const displayCanvas = document.getElementById('displayCanvas');
const displayCtx = displayCanvas.getContext('2d');
const metricsContent = document.getElementById('metrics-content');
const seatAssignmentsDiv = document.getElementById('seat-assignments');
const behaviorContent = document.getElementById('behavior-content');
const scoringContent = document.getElementById('scoring-content');

// Scoring thresholds
let yawThreshold = 30;
let pitchThreshold = 20;
let suspicionThreshold = 50;

// UI elements
const webcamBtn = document.getElementById('webcam-btn');
const fileUploadInput = document.getElementById('file-upload');
const fileInfo = document.getElementById('file-info');
const fileName = document.getElementById('file-name');
const resetBtn = document.getElementById('reset-btn');
const togglePoseBtn = document.getElementById('toggle-pose-btn');

let stream = null;
let videoElement = null;
let isProcessing = false;
let lastProcessedTime = 0;
const PROCESS_INTERVAL_MS = 50; // Target ~10 FPS (adjust as needed)
let sourceType = 'webcam'; // 'webcam' or 'file'
let animationFrameId = null;
let poseEnabled = true; // Track pose visibility state

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

        // Update metrics and seat assignments
        updateMetrics(processResult.metrics);
        updateSeatAssignments(processResult.seat_assignments);
        updateBehaviorAnalysis(processResult.detections);
        updateSuspicionScores(processResult.detections);
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
  socket.emit('video_frame', { image: frameDataUrl, pose_enabled: poseEnabled });

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

togglePoseBtn.addEventListener('click', () => {
  poseEnabled = !poseEnabled;
  togglePoseBtn.textContent = poseEnabled ? 'Hide Pose' : 'Show Pose';
});

// Threshold controls
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
    updateSeatAssignments(data.seat_assignments);
    updateBehaviorAnalysis(data.detections);
    updateSuspicionScores(data.detections);
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

// --- Update Seat Assignments Panel ---
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

// --- Update Behavior Analysis Panel ---
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
    
    // Head orientation
    if (behavior.head_orientation) {
      const ho = behavior.head_orientation;
      html += `<div style="margin-top: 5px;"><strong>Head Angles:</strong><br>`;
      html += `Pitch: ${ho.pitch.toFixed(1)}° | Yaw: ${ho.yaw.toFixed(1)}° | Roll: ${ho.roll.toFixed(1)}°</div>`;
      
      // Alert for extreme angles
      if (Math.abs(ho.yaw) > 30 || Math.abs(ho.pitch) > 20) {
        html += `<div style="color: #d32f2f; font-weight: bold; margin-top: 3px;">⚠️ Looking away</div>`;
      }
    }
    
    // Hand proximity
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

// --- Calculate and Display Suspicion Scores ---
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
    
    // Check behavior data
    if (det.behavior) {
      const behavior = det.behavior;
      
      // Head orientation scoring
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
      
      // Hand proximity scoring
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
    
    // Check for suspicious objects nearby
    const nearbyObjects = detections.filter(d => 
      d.class_id !== 0 && 
      isNearPerson(d.bbox, det.bbox)
    );
    
    nearbyObjects.forEach(obj => {
      const className = getClassName(obj.class_id);
      score += 30;
      reasons.push(`${className} detected nearby`);
    });
    
    // Cap score at 100
    score = Math.min(100, Math.round(score));
    
    // Determine alert level
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

// Helper function to check if object is near person
function isNearPerson(objBbox, personBbox) {
  const [ox1, oy1, ox2, oy2] = objBbox;
  const [px1, py1, px2, py2] = personBbox;
  
  // Check if bounding boxes overlap or are close
  const horizontalOverlap = ox1 < px2 && ox2 > px1;
  const verticalOverlap = oy1 < py2 && oy2 > py1;
  
  return horizontalOverlap && verticalOverlap;
}

// Helper function to get class name
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
