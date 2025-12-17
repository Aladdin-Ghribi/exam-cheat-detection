document.addEventListener('DOMContentLoaded', () => {
  const settingsNavItems = document.querySelectorAll('.settings-nav-item');
  const settingsTitle = document.getElementById('settings-title');

  // Add event listener for track ID toggle
  const showTrackToggle = document.getElementById('show-track-toggle');
  if (showTrackToggle) {
    showTrackToggle.addEventListener('change', () => {
      // Save the setting
      saveConfig({
        show_track_ids: showTrackToggle.checked
      });
    });
  }

  settingsNavItems.forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();

      settingsNavItems.forEach(nav => nav.classList.remove('active'));
      item.classList.add('active');

      const setting = item.dataset.setting;
      let titleText;
      if (setting === 'detection') {
        titleText = 'Detection Model Settings';
      } else if (setting === 'privacy') {
        titleText = 'Evidence & Privacy Settings';
      } else if (setting === 'display') {
        titleText = 'UI & Display Settings';
      } else if (setting === 'advanced') {
        titleText = 'Advanced Detection Settings';
      } else if (setting === 'admin') {
        titleText = 'Add User';
      } else {
        titleText = setting.charAt(0).toUpperCase() + setting.slice(1) + ' Settings';
      }
      if (settingsTitle) settingsTitle.textContent = titleText;

      document.querySelectorAll('.setting-section').forEach(section => section.classList.add('hidden'));
      const contentSection = document.getElementById(`${setting}-content`);
      if (contentSection) contentSection.classList.remove('hidden');

      // Load accounts overview if profile section is selected
      if (setting === 'profile') {
        loadAccountsOverview();
      }

      // Load current config when detection section is selected
      if (setting === 'detection') {
        loadConfig();
      }
    });
  });

  const confidenceSlider = document.getElementById('confidence-slider');
  const confidenceValue = document.getElementById('confidence-value');
  if (confidenceSlider && confidenceValue) {
    confidenceSlider.addEventListener('input', (e) => {
      confidenceValue.textContent = parseFloat(e.target.value).toFixed(2);
    });
    confidenceSlider.addEventListener('change', (e) => {
      saveConfig({ confidence_threshold: parseFloat(e.target.value) });
    });
  }

  // Set up frame skipping toggle event listener
  const frameSkipToggle = document.getElementById('frame-skip-toggle');
  if (frameSkipToggle) {
    frameSkipToggle.addEventListener('change', (e) => {
      saveConfig({ enable_frame_skipping: e.target.checked });
    });
  }

  // Set up frame skip threshold input event listener
  const frameSkipThresholdInput = document.querySelector('input[type="number"][min="50"][max="200"]');
  if (frameSkipThresholdInput) {
    frameSkipThresholdInput.addEventListener('change', (e) => {
      const value = parseInt(e.target.value);
      // Validate range
      if (value >= 50 && value <= 200) {
        saveConfig({ frame_skip_threshold_ms: value });
      }
    });
  }

  // Set up max frame skip input event listener
  const maxFrameSkipInput = document.querySelector('input[type="number"][min="1"][max="5"]');
  if (maxFrameSkipInput) {
    maxFrameSkipInput.addEventListener('change', (e) => {
      const value = parseInt(e.target.value);
      // Validate range
      if (value >= 1 && value <= 5) {
        saveConfig({ max_frame_skip: value });
      }
    });
  }

  // Set up processing interval input event listener
  const processingIntervalInput = document.querySelector('input[type="number"][value="50"]');
  if (processingIntervalInput && !processingIntervalInput.hasAttribute('min') && !processingIntervalInput.hasAttribute('max')) {
    processingIntervalInput.addEventListener('change', (e) => {
      const value = parseInt(e.target.value);
      // Validate positive value
      if (value > 0) {
        saveConfig({ processing_interval_ms: value });
      }
    });
  }

  // Set up camera source dropdown event listener
  const cameraSourceSelect = document.querySelector('select.form-control');
  if (cameraSourceSelect) {
    cameraSourceSelect.addEventListener('change', (e) => {
      const value = e.target.value;
      saveConfig({ camera_source: value });
    });
  }

  // Set up camera resolution dropdown event listener
  const cameraResolutionSelects = document.querySelectorAll('select.form-control');
  if (cameraResolutionSelects.length > 1) {
    const cameraResolutionSelect = cameraResolutionSelects[1];
    cameraResolutionSelect.addEventListener('change', (e) => {
      const value = e.target.value;
      saveConfig({ camera_resolution: value });
    });
  }

  // Set up camera FPS radio button event listeners
  const cameraFPSRadios = document.querySelectorAll('input[name="camera-fps"]');
  cameraFPSRadios.forEach(radio => {
    radio.addEventListener('change', (e) => {
      if (e.target.checked) {
        const value = parseInt(e.target.value);
        saveConfig({ camera_fps: value });
      }
    });
  });

  // Set up camera label input event listener
  const cameraLabelInput = document.getElementById('camera-label');
  if (cameraLabelInput) {
    cameraLabelInput.addEventListener('change', (e) => {
      const value = e.target.value;
      saveConfig({ camera_label: value });

      // Update camera name in dashboard
      const cameraNameElement = document.getElementById('camera-name');
      if (cameraNameElement) {
        cameraNameElement.textContent = value || 'Camera 01';
      }

      // Update video camera label
      const videoCameraLabelElement = document.getElementById('video-camera-label');
      if (videoCameraLabelElement) {
        videoCameraLabelElement.textContent = value || 'Camera 01';
      }
    });
  }

  // Set up auto-reconnect toggle event listener
  const autoReconnectToggle = document.getElementById('auto-reconnect-toggle');
  if (autoReconnectToggle) {
    autoReconnectToggle.addEventListener('change', (e) => {
      const value = e.target.checked;
      saveConfig({ auto_reconnect: value });
    });
  }

  // Set up auto-save toggle event listener
  const autoSaveToggle = document.getElementById('auto-save-toggle');
  if (autoSaveToggle) {
    autoSaveToggle.addEventListener('change', (e) => {
      const value = e.target.checked;
      saveConfig({ auto_save: value });
    });
  }

  // Set up retention period input event listener
  const retentionPeriodInput = document.getElementById('retention-period-input');
  if (retentionPeriodInput) {
    retentionPeriodInput.addEventListener('change', (e) => {
      const value = parseInt(e.target.value);
      if (value >= 1 && value <= 30) {
        saveConfig({ retention_period: value });
      }
    });
  }

  // Set up session recording toggle event listener
  const sessionRecordingToggle = document.getElementById('session-recording-toggle');
  if (sessionRecordingToggle) {
    sessionRecordingToggle.addEventListener('change', (e) => {
      const value = e.target.checked;
      saveConfig({ session_recording: value });
    });
  }

  // Set up show bounding boxes toggle event listener
  const showBboxToggle = document.getElementById('show-bbox-toggle');
  if (showBboxToggle) {
    showBboxToggle.addEventListener('change', (e) => {
      const value = e.target.checked;
      saveConfig({ show_bbox: value });
    });
  }

  // Set up show pose skeleton toggle event listener
  const showPoseToggle = document.getElementById('show-pose-toggle');
  if (showPoseToggle) {
    showPoseToggle.addEventListener('change', (e) => {
      const value = e.target.checked;
      saveConfig({ show_pose: value });
    });
  }

  // Set up show confidence scores toggle event listener
  const showConfidenceToggle = document.getElementById('show-confidence-toggle');
  if (showConfidenceToggle) {
    showConfidenceToggle.addEventListener('change', (e) => {
      const value = e.target.checked;
      saveConfig({ show_confidence: value });
    });
  }

  // Set up FPS radio button event listeners
  const fpsRadios = document.querySelectorAll('input[name="fps"]');
  fpsRadios.forEach(radio => {
    radio.addEventListener('change', (e) => {
      if (e.target.checked) {
        saveConfig({ render_fps: parseInt(e.target.value) });
        // Update the display interval immediately
        updateDisplayFPS(parseInt(e.target.value));
      }
    });
  });

  const sliders = [
    { slider: 'yaw-slider', value: 'yaw-value', suffix: '°' },
    { slider: 'pitch-slider', value: 'pitch-value', suffix: '°' },
    { slider: 'roll-slider', value: 'roll-value', suffix: '°' },
    { slider: 'suspicion-slider', value: 'suspicion-value', suffix: '' },
    { slider: 'hand-face-slider', value: 'hand-face-value', suffix: '', decimals: 1 },
    { slider: 'hand-object-slider', value: 'hand-object-value', suffix: ' pixels' }
  ];

  sliders.forEach(({ slider, value, suffix, decimals }) => {
    const sliderEl = document.getElementById(slider);
    const valueEl = document.getElementById(value);
    if (sliderEl && valueEl) {
      sliderEl.addEventListener('input', (e) => {
        const val = decimals ? parseFloat(e.target.value).toFixed(decimals) : e.target.value;
        valueEl.textContent = val + suffix;
      });

      // Add change event listener to save the value
      if (slider === 'yaw-slider') {
        sliderEl.addEventListener('change', (e) => {
          saveConfig({ yaw_threshold: parseInt(e.target.value) });
        });
      }

      if (slider === 'pitch-slider') {
        sliderEl.addEventListener('change', (e) => {
          saveConfig({ pitch_threshold: parseInt(e.target.value) });
        });
      }

      if (slider === 'roll-slider') {
        sliderEl.addEventListener('change', (e) => {
          saveConfig({ roll_threshold: parseInt(e.target.value) });
        });
      }

      if (slider === 'suspicion-slider') {
        sliderEl.addEventListener('change', (e) => {
          saveConfig({ suspicion_threshold: parseInt(e.target.value) });
        });
      }

      if (slider === 'hand-face-slider') {
        sliderEl.addEventListener('change', (e) => {
          saveConfig({ hand_face_threshold: parseFloat(e.target.value) });
        });
      }

      if (slider === 'hand-object-slider') {
        sliderEl.addEventListener('change', (e) => {
          saveConfig({ hand_object_threshold: parseInt(e.target.value) });
        });
      }
    }
  });

  const suspicionSaveSlider = document.getElementById('suspicion-save-slider');
  const suspicionSaveValue = document.getElementById('suspicion-save-value');
  if (suspicionSaveSlider && suspicionSaveValue) {
    suspicionSaveSlider.addEventListener('input', (e) => {
      suspicionSaveValue.textContent = e.target.value;
    });

    suspicionSaveSlider.addEventListener('change', (e) => {
      const value = parseInt(e.target.value);
      saveConfig({ suspicion_save_threshold: value });
    });
  }

  const smoothingSlider = document.getElementById('smoothing-slider');
  const smoothingValue = document.getElementById('smoothing-value');
  if (smoothingSlider && smoothingValue) {
    smoothingSlider.addEventListener('input', (e) => {
      smoothingValue.textContent = parseFloat(e.target.value).toFixed(1);
    });

    smoothingSlider.addEventListener('change', (e) => {
      saveConfig({ smoothing_factor: parseFloat(e.target.value) });
    });
  }

  const visibilitySlider = document.getElementById('visibility-slider');
  const visibilityValue = document.getElementById('visibility-value');
  if (visibilitySlider && visibilityValue) {
    visibilitySlider.addEventListener('input', (e) => {
      visibilityValue.textContent = parseFloat(e.target.value).toFixed(1);
    });
  }

  const togglePassword = document.getElementById('toggle-password');
  const adminPassword = document.getElementById('admin-password');
  if (togglePassword && adminPassword) {
    togglePassword.addEventListener('click', () => {
      const type = adminPassword.type === 'password' ? 'text' : 'password';
      adminPassword.type = type;
      togglePassword.className = type === 'password' ? 'bx bx-show' : 'bx bx-hide';
    });
  }

  // YOLO Model Size dropdown
  const yoloModelSize = document.getElementById('yolo-model-size');
  if (yoloModelSize) {
    yoloModelSize.addEventListener('change', (e) => {
      saveConfig({ model_size: e.target.value });
    });
  }

  // Image Processing Size dropdown
  const imgProcessingSize = document.getElementById('img-processing-size');
  if (imgProcessingSize) {
    imgProcessingSize.addEventListener('change', (e) => {
      saveConfig({ img_processing_size: parseInt(e.target.value) });
    });
  }

  // Model Complexity dropdown
  const modelComplexity = document.getElementById('model-complexity');
  if (modelComplexity) {
    modelComplexity.addEventListener('change', (e) => {
      saveConfig({ model_complexity: parseInt(e.target.value) });
    });
  }

  // Device Selection radio buttons
  const deviceCpu = document.getElementById('device-cpu');
  const deviceGpu = document.getElementById('device-gpu');
  if (deviceCpu && deviceGpu) {
    deviceCpu.addEventListener('change', (e) => {
      if (e.target.checked) {
        saveConfig({ device: 'cpu' });
      }
    });

    deviceGpu.addEventListener('change', (e) => {
      if (e.target.checked) {
        saveConfig({ device: 'gpu' });
      }
    });
  }

  // History Length input
  const historyLengthInput = document.getElementById('history-length-input');
  if (historyLengthInput) {
    historyLengthInput.addEventListener('change', (e) => {
      const value = parseInt(e.target.value);
      if (value >= 3 && value <= 20) {
        saveConfig({ history_length: value });
      }
    });
  }

  // Add User button (Admin section)
  const addUserBtn = document.getElementById('add-user-btn');
  if (addUserBtn) {
    addUserBtn.addEventListener('click', () => {
      createUser();
    });
  }

  // Toggle password visibility for new user password
  const toggleNewPassword = document.getElementById('toggle-new-password');
  const newUserPassword = document.getElementById('new-user-password');
  if (toggleNewPassword && newUserPassword) {
    toggleNewPassword.addEventListener('click', () => {
      const type = newUserPassword.getAttribute('type') === 'password' ? 'text' : 'password';
      newUserPassword.setAttribute('type', type);
      toggleNewPassword.classList.toggle('bx-show');
      toggleNewPassword.classList.toggle('bx-hide');
    });
  }

  // Settings Alert Modal Listeners
  const alertCloseBtn = document.getElementById('settings-alert-close-btn');
  const alertOkBtn = document.getElementById('settings-alert-ok-btn');
  const alertOverlay = document.getElementById('settings-alert-modal');

  if (alertCloseBtn) {
    alertCloseBtn.addEventListener('click', hideSettingsAlert);
  }
  if (alertOkBtn) {
    alertOkBtn.addEventListener('click', hideSettingsAlert);
  }
  if (alertOverlay) {
    alertOverlay.addEventListener('click', (e) => {
      if (e.target === alertOverlay) hideSettingsAlert();
    });
  }
});

/**
 * Custom Alert Modal for Settings
 * @param {string} type - 'success', 'error', or 'warning'
 * @param {string} title - Modal title
 * @param {string} message - Modal message
 */
function showSettingsAlert(type, title, message) {
  const modal = document.getElementById('settings-alert-modal');
  const iconContainer = document.getElementById('settings-alert-icon-container');
  const icon = document.getElementById('settings-alert-icon');
  const titleEl = document.getElementById('settings-alert-title');
  const messageEl = document.getElementById('settings-alert-message');

  if (!modal) return;

  // Set colors and icon based on type
  iconContainer.className = 'alert-icon-wrapper ' + type;
  if (type === 'success') {
    icon.className = 'bx bx-check-circle';
  } else if (type === 'error') {
    icon.className = 'bx bx-x-circle';
  } else {
    icon.className = 'bx bx-info-circle';
  }

  titleEl.textContent = title;
  messageEl.textContent = message;

  modal.classList.remove('hidden');
  document.body.style.overflow = 'hidden';
}

function hideSettingsAlert() {
  const modal = document.getElementById('settings-alert-modal');
  if (modal) {
    modal.classList.add('hidden');
    document.body.style.overflow = '';
  }
}

function loadAccountsOverview() {
  const user = JSON.parse(localStorage.getItem('user') || '{}');
  const profileContent = document.getElementById('profile-content');

  if (!profileContent) return;

  // Check if user is admin
  if (user.role !== 'administrator') {
    profileContent.innerHTML = `
      <h3 class="section-title">Accounts Overview</h3>
      <p>You do not have permission to view user accounts.</p>
    `;
    return;
  }

  // Fetch users from API
  fetch(`/api/users?current_user_role=${user.role}`)
    .then(response => response.json())
    .then(data => {
      const users = data.users || [];

      // Build the accounts table
      const tableHTML = `
        <h3 class="section-title">Accounts Overview</h3>
        <table class="accounts-table">
          <thead>
            <tr>
              <th>Username</th>
              <th>Email</th>
              <th>Password</th>
              <th>Role</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            ${users.map(user => `
              <tr>
                <td>${user.username || 'N/A'}</td>
                <td>${user.email || 'N/A'}</td>
                <td>${user.password || 'N/A'}</td>
                <td>${user.role || 'N/A'}</td>
                <td><button class="edit-btn" data-user-id="${user.id}" title="Edit User"><svg width="20" height="20" viewBox="0 0 110 117" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path fill-rule="evenodd" clip-rule="evenodd" d="M93.0553 4.41701L104.308 13.3777C105.395 14.4005 106.008 15.829 105.999 17.3214C105.991 18.8136 105.363 20.2354 104.265 21.2462L95.714 31.4788L66.6187 66.1792C66.1092 66.762 65.4316 67.1716 64.6785 67.3505L49.5883 70.7709C47.6086 70.8701 45.8847 69.4308 45.6289 67.4655V51.9585C45.6799 51.2104 45.981 50.5019 46.484 49.9465L75.0404 17.6605L84.8419 5.95477C86.7806 3.413 90.3275 2.74896 93.0553 4.41701Z" stroke="white" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M68.9502 109.352L68.9541 111.049V113.13H35.7139V111.075L35.7188 109.352H68.9502ZM5.38184 87.7942L7.51562 87.7981C9.0333 98.8036 17.7162 107.527 28.7139 109.097V111.233L28.709 112.908C15.6217 111.289 5.26735 100.888 3.70605 87.7942H5.38184ZM100.963 87.7942C99.4015 100.889 89.046 111.29 75.958 112.908L75.9541 110.842V109.097C86.9519 107.527 95.6334 98.8036 97.1514 87.7981L99.2871 87.7942H100.963ZM75.666 89.1448V92.9241H29.0098V89.1448H75.666ZM101.169 60.8469V80.7893L99.0557 80.7942H97.3896V60.8469H101.169ZM7.27832 47.3743V80.7942H5.6123L3.5 80.7893V47.3772L4.94824 47.3743H7.27832ZM28.7139 16.9348V19.0706C17.7164 20.6408 9.03358 29.3634 7.51562 40.3684L4.93262 40.3743H3.70508C5.26581 27.2793 15.6212 16.8774 28.709 15.2581L28.7139 16.9348ZM78.3799 20.0676C79.541 22.0107 81.1192 24.1134 83.0654 25.8752L83.3662 26.1418C85.7498 28.2157 88.5635 29.6895 91.7852 29.8889L92.626 33.6926C87.9296 33.7231 83.9623 31.6696 80.8857 28.9924L80.5352 28.6819C78.1113 26.4893 76.2053 23.8829 74.8525 21.5237L78.3799 20.0676ZM48.834 15.0374V18.8157H35.7188L35.7139 16.7258V15.0374H48.834Z" fill="black" stroke="white" stroke-width="7"/>
                  </svg></button></td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      `;

      profileContent.innerHTML = tableHTML;

      // Add event listeners to edit buttons
      document.querySelectorAll('.edit-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
          const userId = e.currentTarget.dataset.userId;
          const userData = users.find(u => u.id == userId);
          if (userData) {
            showAdminEditModal(userData);
          }
        });
      });
    })
    .catch(error => {
      console.error('Error loading users:', error);
      profileContent.innerHTML = `
        <h3 class="section-title">Accounts Overview</h3>
        <p>Error loading user accounts. Please try again later.</p>
      `;
    });
}

function showAdminEditModal(user) {
  const existingModal = document.getElementById('admin-edit-modal');
  if (existingModal) {
    existingModal.remove();
  }

  const modal = document.createElement('div');
  modal.id = 'admin-edit-modal';
  modal.innerHTML = `
    <div class="profile-modal-overlay">
      <div class="profile-modal-content">
        <button class="profile-modal-close">&times;</button>
        <div class="profile-modal-header">
          <h2>Edit User Account</h2>
          <p>Modify user information</p>
        </div>
        <div class="profile-modal-body">
          <div class="profile-edit-form">
            <div class="form-group">
              <label for="admin-edit-username">Username</label>
              <input type="text" id="admin-edit-username" value="${user.username || ''}" required>
            </div>
            <div class="form-group">
              <label for="admin-edit-password">Password</label>
              <input type="text" id="admin-edit-password" value="${user.password || ''}" required>
            </div>
            <div class="form-group">
              <label for="admin-edit-role">Role</label>
              <select id="admin-edit-role" required>
                <option value="proctor" ${user.role === 'proctor' ? 'selected' : ''}>Proctor</option>
                <option value="administrator" ${user.role === 'administrator' ? 'selected' : ''}>Administrator</option>
              </select>
            </div>
          </div>
        </div>
        <div class="profile-modal-footer">
          <button class="profile-btn save-admin-edit-btn">Save Edits</button>
          <button class="profile-btn delete-admin-user-btn">Delete User</button>
          <button class="profile-btn cancel-admin-edit-btn">Cancel</button>
        </div>
      </div>
      <div class="confirmation-dialog" id="save-confirmation-dialog" style="display: none;">
        <div class="confirmation-content">
          <h3>Confirm Changes</h3>
          <p>Are you sure you want to save changes to this user account?</p>
          <div class="confirmation-buttons">
            <button class="profile-btn confirm-save-btn">Yes, Save</button>
            <button class="profile-btn cancel-save-btn">Cancel</button>
          </div>
        </div>
      </div>
      <div class="confirmation-dialog" id="delete-confirmation-dialog" style="display: none;">
        <div class="confirmation-content">
          <h3>Confirm Deletion</h3>
          <p>Are you sure you want to delete this user? This action cannot be undone.</p>
          <div class="confirmation-buttons">
            <button class="profile-btn confirm-delete-btn">Yes, Delete</button>
            <button class="profile-btn cancel-delete-btn">Cancel</button>
          </div>
        </div>
      </div>
    </div>
  `;

  document.body.appendChild(modal);

  const closeBtn = modal.querySelector('.profile-modal-close');
  const overlay = modal.querySelector('.profile-modal-overlay');
  const saveBtn = modal.querySelector('.save-admin-edit-btn');
  const deleteBtn = modal.querySelector('.delete-admin-user-btn');
  const cancelBtn = modal.querySelector('.cancel-admin-edit-btn');
  const saveConfirmationDialog = modal.querySelector('#save-confirmation-dialog');
  const deleteConfirmationDialog = modal.querySelector('#delete-confirmation-dialog');
  const confirmSaveBtn = modal.querySelector('.confirm-save-btn');
  const cancelSaveBtn = modal.querySelector('.cancel-save-btn');
  const confirmDeleteBtn = modal.querySelector('.confirm-delete-btn');
  const cancelDeleteBtn = modal.querySelector('.cancel-delete-btn');

  closeBtn.addEventListener('click', () => modal.remove());
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) modal.remove();
  });

  cancelBtn.addEventListener('click', () => modal.remove());

  saveBtn.addEventListener('click', () => {
    const username = modal.querySelector('#admin-edit-username').value.trim();
    const password = modal.querySelector('#admin-edit-password').value.trim();
    const role = modal.querySelector('#admin-edit-role').value;

    if (!username || !password || !role) {
      showSettingsAlert('error', 'Incomplete Data', 'Username, password, and role are required.');
      return;
    }

    // Show confirmation dialog
    saveConfirmationDialog.style.display = 'flex';
  });

  deleteBtn.addEventListener('click', () => {
    deleteConfirmationDialog.style.display = 'flex';
  });

  confirmSaveBtn.addEventListener('click', () => {
    const username = modal.querySelector('#admin-edit-username').value.trim();
    const password = modal.querySelector('#admin-edit-password').value.trim();
    const role = modal.querySelector('#admin-edit-role').value;
    saveAdminUserChanges(user.id, username, password, role);
  });

  cancelSaveBtn.addEventListener('click', () => {
    saveConfirmationDialog.style.display = 'none';
  });

  confirmDeleteBtn.addEventListener('click', () => {
    deleteAdminUser(user.id);
  });

  cancelDeleteBtn.addEventListener('click', () => {
    deleteConfirmationDialog.style.display = 'none';
  });
}

function saveAdminUserChanges(userId, username, password, role) {
  const user = JSON.parse(localStorage.getItem('user') || '{}');
  fetch('/api/user/update', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      id: userId,
      username: username,
      password: password,
      role: role,
      current_user_role: user.role
    })
  })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        // Close modal
        const modal = document.getElementById('admin-edit-modal');
        if (modal) modal.remove();

        showSettingsAlert('success', 'Update Successful', 'User account updated successfully!');
        // Reload the accounts overview
        loadAccountsOverview();
      } else {
        showSettingsAlert('error', 'Update Failed', 'Error updating user account: ' + data.error);
      }
    })
    .catch(error => {
      console.error('Error:', error);
      alert('An error occurred while updating the user account.');
    });
}

function deleteAdminUser(userId) {
  const user = JSON.parse(localStorage.getItem('user') || '{}');
  fetch('/api/user/delete', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      id: userId,
      current_user_role: user.role
    })
  })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        // Close modal
        const modal = document.getElementById('admin-edit-modal');
        if (modal) modal.remove();

        showSettingsAlert('success', 'User Deleted', 'User deleted successfully!');
        // Reload the accounts overview
        loadAccountsOverview();
      } else {
        showSettingsAlert('error', 'Deletion Failed', 'Error deleting user: ' + data.error);
      }
    })
    .catch(error => {
      console.error('Error:', error);
      alert('An error occurred while deleting the user.');
    });
}

// Create a new user (admin only)
function createUser() {
  const user = JSON.parse(localStorage.getItem('user') || '{}');

  // Get form values
  const username = document.getElementById('new-user-username')?.value?.trim();
  const email = document.getElementById('new-user-email')?.value?.trim();
  const password = document.getElementById('new-user-password')?.value?.trim();
  const role = document.getElementById('new-user-role')?.value;

  // Validate client-side
  if (!username) {
    showSettingsAlert('error', 'Missing Username', 'Please enter a username');
    return;
  }
  if (!email) {
    showSettingsAlert('error', 'Missing Email', 'Please enter an email address');
    return;
  }
  if (!password) {
    showSettingsAlert('error', 'Missing Password', 'Please enter a password');
    return;
  }

  fetch('/api/user/create', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      username: username,
      email: email,
      password: password,
      role: role,
      current_user_role: user.role
    })
  })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        showSettingsAlert('success', 'User Created', `User "${username}" created successfully!`);

        // Clear the form
        document.getElementById('new-user-username').value = '';
        document.getElementById('new-user-email').value = '';
        document.getElementById('new-user-password').value = '';
        document.getElementById('new-user-role').value = 'proctor';

        // Reload the accounts overview to show the new user
        loadAccountsOverview();
      } else {
        showSettingsAlert('error', 'Creation Failed', 'Error creating user: ' + data.error);
      }
    })
    .catch(error => {
      console.error('Error:', error);
      alert('An error occurred while creating the user.');
    });
}

// Function to update display FPS - global scope for loadConfig to access
function updateDisplayFPS(fps) {
  // Clear existing interval if any
  if (typeof displayInterval !== 'undefined') {
    clearInterval(displayInterval);
  }

  // Calculate new interval in milliseconds
  const intervalMs = Math.round(1000 / fps);

  // Restart display loop with new FPS
  if (typeof startLocalDisplayLoop === 'function') {
    startLocalDisplayLoop(intervalMs);
  }
}

function loadConfig() {
  fetch('/api/config')
    .then(response => response.json())
    .then(config => {
      // Set YOLO model size dropdown
      const yoloModelSize = document.getElementById('yolo-model-size');
      if (yoloModelSize && config.model_size) {
        yoloModelSize.value = config.model_size;
      }

      // Set confidence threshold slider
      const confidenceSlider = document.getElementById('confidence-slider');
      const confidenceValue = document.getElementById('confidence-value');
      if (confidenceSlider && confidenceValue && config.confidence_threshold !== undefined) {
        confidenceSlider.value = config.confidence_threshold;
        confidenceValue.textContent = parseFloat(config.confidence_threshold).toFixed(2);
      }

      // Set image processing size dropdown
      const imgProcessingSize = document.getElementById('img-processing-size');
      if (imgProcessingSize && config.img_processing_size !== undefined) {
        imgProcessingSize.value = config.img_processing_size;
      }

      // Set device selection radio buttons
      const deviceCpu = document.getElementById('device-cpu');
      const deviceGpu = document.getElementById('device-gpu');
      if (deviceCpu && deviceGpu && config.device !== undefined) {
        if (config.device === 'gpu') {
          deviceGpu.checked = true;
        } else {
          deviceCpu.checked = true;
        }
      }

      // Set Model Complexity dropdown
      const modelComplexity = document.getElementById('model-complexity');
      if (modelComplexity && config.model_complexity !== undefined) {
        modelComplexity.value = config.model_complexity;
      }

      // Set Yaw Threshold slider
      const yawSlider = document.getElementById('yaw-slider');
      const yawValue = document.getElementById('yaw-value');
      if (yawSlider && yawValue && config.yaw_threshold !== undefined) {
        yawSlider.value = config.yaw_threshold;
        yawValue.textContent = config.yaw_threshold + '°';
      }

      // Set Pitch Threshold slider
      const pitchSlider = document.getElementById('pitch-slider');
      const pitchValue = document.getElementById('pitch-value');
      if (pitchSlider && pitchValue && config.pitch_threshold !== undefined) {
        pitchSlider.value = config.pitch_threshold;
        pitchValue.textContent = config.pitch_threshold + '°';
      }

      // Set Roll Threshold slider
      const rollSlider = document.getElementById('roll-slider');
      const rollValue = document.getElementById('roll-value');
      if (rollSlider && rollValue && config.roll_threshold !== undefined) {
        rollSlider.value = config.roll_threshold;
        rollValue.textContent = config.roll_threshold + '°';
      }

      // Set Suspicion Score Threshold slider
      const suspicionSlider = document.getElementById('suspicion-slider');
      const suspicionValue = document.getElementById('suspicion-value');
      if (suspicionSlider && suspicionValue && config.suspicion_threshold !== undefined) {
        suspicionSlider.value = config.suspicion_threshold;
        suspicionValue.textContent = config.suspicion_threshold;
      }

      // Set Hand-Face Distance Threshold slider
      const handFaceSlider = document.getElementById('hand-face-slider');
      const handFaceValue = document.getElementById('hand-face-value');
      if (handFaceSlider && handFaceValue && config.hand_face_threshold !== undefined) {
        handFaceSlider.value = config.hand_face_threshold;
        handFaceValue.textContent = config.hand_face_threshold;
      }

      // Set Hand-Object Distance Threshold slider
      const handObjectSlider = document.getElementById('hand-object-slider');
      const handObjectValue = document.getElementById('hand-object-value');
      if (handObjectSlider && handObjectValue && config.hand_object_threshold !== undefined) {
        handObjectSlider.value = config.hand_object_threshold;
        handObjectValue.textContent = config.hand_object_threshold + ' pixels';
      }

      // Set Render FPS radio buttons
      if (config.render_fps !== undefined) {
        const fpsRadios = document.querySelectorAll('input[name="fps"]');
        fpsRadios.forEach(radio => {
          if (parseInt(radio.value) === config.render_fps) {
            radio.checked = true;
          }
        });

        // Update display FPS with loaded value
        updateDisplayFPS(config.render_fps);
      }

      // Set Frame Skipping toggle
      if (config.enable_frame_skipping !== undefined) {
        const frameSkipToggle = document.getElementById('frame-skip-toggle');
        if (frameSkipToggle) {
          frameSkipToggle.checked = config.enable_frame_skipping;
        }
      }

      // Set Frame Skip Threshold input
      if (config.frame_skip_threshold_ms !== undefined) {
        const frameSkipThresholdInput = document.querySelector('input[type="number"][min="50"][max="200"]');
        if (frameSkipThresholdInput) {
          frameSkipThresholdInput.value = config.frame_skip_threshold_ms;
        }
      }

      // Set Max Frame Skip input
      if (config.max_frame_skip !== undefined) {
        const maxFrameSkipInput = document.querySelector('input[type="number"][min="1"][max="5"]');
        if (maxFrameSkipInput) {
          maxFrameSkipInput.value = config.max_frame_skip;
        }
      }

      // Set Processing Interval input
      if (config.processing_interval_ms !== undefined) {
        const processingIntervalInput = document.querySelector('input[type="number"][value="50"]');
        if (processingIntervalInput && !processingIntervalInput.hasAttribute('min') && !processingIntervalInput.hasAttribute('max')) {
          processingIntervalInput.value = config.processing_interval_ms;
        }
      }

      // Set Camera Source dropdown
      if (config.camera_source !== undefined) {
        const cameraSourceSelect = document.querySelector('select.form-control');
        if (cameraSourceSelect) {
          // Find and select the option with matching text
          const options = cameraSourceSelect.options;
          for (let i = 0; i < options.length; i++) {
            if (options[i].text === config.camera_source) {
              cameraSourceSelect.selectedIndex = i;
              break;
            }
          }
        }
      }

      // Set Camera Resolution dropdown
      if (config.camera_resolution !== undefined) {
        const cameraResolutionSelects = document.querySelectorAll('select.form-control');
        if (cameraResolutionSelects.length > 1) {
          const cameraResolutionSelect = cameraResolutionSelects[1];
          // Find and select the option with matching text
          const options = cameraResolutionSelect.options;
          for (let i = 0; i < options.length; i++) {
            if (options[i].text === config.camera_resolution) {
              cameraResolutionSelect.selectedIndex = i;
              break;
            }
          }
        }
      }

      // Set Camera FPS radio buttons
      if (config.camera_fps !== undefined) {
        const cameraFPSRadios = document.querySelectorAll('input[name="camera-fps"]');
        cameraFPSRadios.forEach(radio => {
          if (parseInt(radio.value) === config.camera_fps) {
            radio.checked = true;
          }
        });
      }

      // Set Camera label input
      if (config.camera_label !== undefined) {
        const cameraLabelInput = document.getElementById('camera-label');
        if (cameraLabelInput) {
          cameraLabelInput.value = config.camera_label;
        }

        // Update camera name in dashboard
        const cameraNameElement = document.getElementById('camera-name');
        if (cameraNameElement) {
          cameraNameElement.textContent = config.camera_label || 'Camera 01';
        }

        // Update video camera label
        const videoCameraLabelElement = document.getElementById('video-camera-label');
        if (videoCameraLabelElement) {
          videoCameraLabelElement.textContent = config.camera_label || 'Camera 01';
        }
      }

      // Set auto-reconnect toggle
      if (config.auto_reconnect !== undefined) {
        const autoReconnectToggle = document.getElementById('auto-reconnect-toggle');
        if (autoReconnectToggle) {
          autoReconnectToggle.checked = config.auto_reconnect;
        }
      }

      // Set auto-save toggle
      if (config.auto_save !== undefined) {
        const autoSaveToggle = document.getElementById('auto-save-toggle');
        if (autoSaveToggle) {
          autoSaveToggle.checked = config.auto_save;
        }
      }

      // Set suspicion save threshold
      if (config.suspicion_save_threshold !== undefined) {
        const suspicionSaveSlider = document.getElementById('suspicion-save-slider');
        const suspicionSaveValue = document.getElementById('suspicion-save-value');
        if (suspicionSaveSlider && suspicionSaveValue) {
          suspicionSaveSlider.value = config.suspicion_save_threshold;
          suspicionSaveValue.textContent = config.suspicion_save_threshold;
        }
      }

      // Set retention period
      if (config.retention_period !== undefined) {
        const retentionPeriodInput = document.getElementById('retention-period-input');
        if (retentionPeriodInput) {
          retentionPeriodInput.value = config.retention_period;
        }
      }

      // Set session recording toggle
      if (config.session_recording !== undefined) {
        const sessionRecordingToggle = document.getElementById('session-recording-toggle');
        if (sessionRecordingToggle) {
          sessionRecordingToggle.checked = config.session_recording;
        }
      }

      // Set show bounding boxes toggle
      if (config.show_bbox !== undefined) {
        const showBboxToggle = document.getElementById('show-bbox-toggle');
        if (showBboxToggle) {
          showBboxToggle.checked = config.show_bbox;
        }
      }

      // Set show track IDs toggle
      if (config.show_track_ids !== undefined) {
        const showTrackToggle = document.getElementById('show-track-toggle');
        if (showTrackToggle) {
          showTrackToggle.checked = config.show_track_ids;
        }
      }

      // Set other config values as needed
      // Add more config loading here if required
    })
    .catch(error => {
      console.error('Error loading config:', error);
    });
}

function saveConfig(updates) {
  fetch('/api/config', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(updates)
  })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        console.log('Config updated successfully');
      } else {
        console.error('Error updating config:', data.error);
      }
    })
    .catch(error => {
      console.error('Error saving config:', error);
    });
}
