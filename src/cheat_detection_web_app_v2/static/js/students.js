/**
 * Student Registration and Database Management
 * Handles face capture, registration, and student listing.
 */

document.addEventListener('DOMContentLoaded', () => {
  // UI Elements
  const studentsGrid = document.getElementById('students-grid');
  const btnAddStudent = document.getElementById('btn-add-student');
  const registrationModal = document.getElementById('registration-modal');
  const closeRegistrationModal = document.getElementById('close-registration-modal');
  const btnCancelRegistration = document.getElementById('btn-cancel-registration');
  const btnSubmitRegistration = document.getElementById('btn-submit-registration');

  const regVideo = document.getElementById('registration-video');
  const regCanvas = document.getElementById('registration-canvas');
  const regPhotoPreview = document.getElementById('registration-photo-preview');
  const btnCapturePhoto = document.getElementById('btn-capture-photo');
  const btnRetakePhoto = document.getElementById('btn-retake-photo');

  const inputSid = document.getElementById('reg-student-id');
  const inputName = document.getElementById('reg-student-name');

  let stream = null;
  let capturedImageBase64 = null;

  // --- Tab Management Integration ---
  // Ensure we load students when this page becomes active
  const navItems = document.querySelectorAll('.nav-item');
  navItems.forEach(item => {
    item.addEventListener('click', () => {
      if (item.getAttribute('data-page') === 'students') {
        loadStudents();
      }
    });
  });

  // --- API Calls ---

  async function loadStudents() {
    if (!studentsGrid) return;

    try {
      const response = await fetch('/api/students/list');
      const data = await response.json();

      if (data.success) {
        renderStudents(data.students);
      }
    } catch (error) {
      console.error('Failed to load students:', error);
    }
  }

  function renderStudents(students) {
    if (students.length === 0) {
      studentsGrid.innerHTML = `
                <div class="empty-state-full">
                    <i class='bx bx-user-x'></i>
                    <h3>No Students Registered</h3>
                    <p>Register students to enable automatic face identification during exams.</p>
                </div>`;
      return;
    }

    studentsGrid.innerHTML = students.map(student => `
            <div class="student-card" data-sid="${student.student_id}">
                <div class="student-photo-wrapper">
                    <img src="data:image/jpeg;base64,${student.photo}" class="student-photo" alt="${student.student_name}">
                </div>
                <div class="student-card-info">
                    <div class="student-card-name">${student.student_name}</div>
                    <div class="student-card-id">${student.student_id}</div>
                </div>
                <button class="btn-delete-student" onclick="deleteStudent('${student.student_id}')" title="Delete record">
                    <i class='bx bx-trash'></i>
                </button>
            </div>
        `).join('');
  }

  // Delete confirmation modal elements
  const deleteModal = document.getElementById('delete-confirm-modal');
  const deleteOverlay = document.getElementById('delete-confirm-overlay');
  const deleteMessage = document.getElementById('delete-confirm-message');
  const btnCancelDelete = document.getElementById('btn-cancel-delete');
  const btnConfirmDelete = document.getElementById('btn-confirm-delete');
  let pendingDeleteSid = null;

  // Show custom delete confirmation modal
  window.deleteStudent = (sid) => {
    pendingDeleteSid = sid;
    deleteMessage.textContent = `Are you sure you want to delete registration for student "${sid}"? This action cannot be undone.`;
    deleteModal.classList.remove('hidden');
  };

  // Cancel delete
  const closeDeleteModal = () => {
    deleteModal.classList.add('hidden');
    pendingDeleteSid = null;
  };

  btnCancelDelete.addEventListener('click', closeDeleteModal);
  deleteOverlay.addEventListener('click', closeDeleteModal);

  // Confirm delete
  btnConfirmDelete.addEventListener('click', async () => {
    if (!pendingDeleteSid) return;
    const sid = pendingDeleteSid;
    closeDeleteModal();

    try {
      const response = await fetch('/api/students/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ student_id: sid })
      });

      const data = await response.json();
      if (data.success) {
        loadStudents();
      } else {
        // Could add error modal here too
        console.error('Error deleting student:', data.error);
      }
    } catch (error) {
      console.error('Delete request failed:', error);
    }
  });

  // --- Modal & Camera Management ---

  btnAddStudent.addEventListener('click', async () => {
    registrationModal.classList.remove('hidden');
    resetRegistrationForm();
    await startCamera();
  });

  const closeRegistration = () => {
    registrationModal.classList.add('hidden');
    stopCamera();
  };

  closeRegistrationModal.addEventListener('click', closeRegistration);
  btnCancelRegistration.addEventListener('click', closeRegistration);

  async function startCamera() {
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480, facingMode: "user" }
      });
      regVideo.srcObject = stream;
    } catch (error) {
      console.error('Camera access denied:', error);
      alert('Could not access camera. Please check permissions.');
    }
  }

  function stopCamera() {
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      stream = null;
    }
  }

  btnCapturePhoto.addEventListener('click', () => {
    const context = regCanvas.getContext('2d');
    regCanvas.width = regVideo.videoWidth;
    regCanvas.height = regVideo.videoHeight;
    context.drawImage(regVideo, 0, 0, regCanvas.width, regCanvas.height);

    capturedImageBase64 = regCanvas.toDataURL('image/jpeg', 0.9);
    regPhotoPreview.src = capturedImageBase64;

    // UI Shuffle
    regVideo.classList.add('hidden');
    regPhotoPreview.classList.remove('hidden');
    btnCapturePhoto.classList.add('hidden');
    btnRetakePhoto.classList.remove('hidden');

    validateForm();
  });

  btnRetakePhoto.addEventListener('click', () => {
    capturedImageBase64 = null;
    regVideo.classList.remove('hidden');
    regPhotoPreview.classList.add('hidden');
    btnCapturePhoto.classList.remove('hidden');
    btnRetakePhoto.classList.add('hidden');

    validateForm();
  });

  // Form Validation with error prompts
  const validateForm = (showErrors = false) => {
    const sidValue = inputSid.value.trim();
    const nameValue = inputName.value.trim();

    let isValid = true;

    // Validate Student ID
    if (sidValue.length < 3) {
      if (showErrors || (sidValue.length > 0)) {
        inputSid.classList.add('error');
        inputSid.parentElement.classList.add('has-error');
      }
      isValid = false;
    } else {
      inputSid.classList.remove('error');
      inputSid.parentElement.classList.remove('has-error');
    }

    // Validate Name
    if (nameValue.length < 3) {
      if (showErrors || (nameValue.length > 0)) {
        inputName.classList.add('error');
        inputName.parentElement.classList.add('has-error');
      }
      isValid = false;
    } else {
      inputName.classList.remove('error');
      inputName.parentElement.classList.remove('has-error');
    }

    // Check photo
    const hasPhoto = capturedImageBase64 !== null;
    if (!hasPhoto && showErrors) {
      showGenericAlert('Photo Required', 'Please capture a face photo before registering.', 'warning');
    }

    const formComplete = isValid && hasPhoto;
    // We don't disable the button anymore to allow "prompt handling"
    btnSubmitRegistration.classList.toggle('btn-disabled', !formComplete);

    return formComplete;
  };

  inputSid.addEventListener('input', validateForm);
  inputName.addEventListener('input', validateForm);

  // Show error on blur if empty
  inputSid.addEventListener('blur', () => {
    if (inputSid.value.trim().length === 0 && document.activeElement !== inputSid) {
      inputSid.classList.add('error');
      inputSid.parentElement.classList.add('has-error');
    }
  });

  inputName.addEventListener('blur', () => {
    if (inputName.value.trim().length === 0 && document.activeElement !== inputName) {
      inputName.classList.add('error');
      inputName.parentElement.classList.add('has-error');
    }
  });

  function resetRegistrationForm() {
    inputSid.value = '';
    inputName.value = '';
    capturedImageBase64 = null;
    regVideo.classList.remove('hidden');
    regPhotoPreview.classList.add('hidden');
    btnCapturePhoto.classList.remove('hidden');
    btnRetakePhoto.classList.add('hidden');

    // Ensure button is NOT disabled so click prompt works
    btnSubmitRegistration.disabled = false;

    // Reset visual state
    btnSubmitRegistration.classList.add('btn-disabled');
    btnSubmitRegistration.innerHTML = `<i class='bx bx-check-double'></i> Complete Registration`;

    // Clear errors
    inputSid.classList.remove('error');
    inputName.classList.remove('error');
    inputSid.parentElement.classList.remove('has-error');
    inputName.parentElement.classList.remove('has-error');
  }

  // Success Modal
  const successModal = document.getElementById('success-modal');
  const successOverlay = document.getElementById('success-modal-overlay');
  const successMessage = document.getElementById('success-modal-message');
  const btnSuccessOk = document.getElementById('btn-success-ok');

  const showSuccessModal = (studentName) => {
    successMessage.textContent = `"${studentName}" has been successfully registered.`;
    successModal.classList.remove('hidden');
  };

  const closeSuccessModal = () => {
    successModal.classList.add('hidden');
  };

  if (btnSuccessOk) btnSuccessOk.addEventListener('click', closeSuccessModal);
  if (successOverlay) successOverlay.addEventListener('click', closeSuccessModal);

  console.log('Register script initialized. Submit btn:', btnSubmitRegistration);

  btnSubmitRegistration.addEventListener('click', async (e) => {
    console.log('Submit registration clicked');
    e.preventDefault();

    // Re-validate and show ALL errors on click
    const isFormValid = validateForm(true);
    console.log('Form validation result:', isFormValid);

    if (!isFormValid) {
      console.log('Validation failed, stopping.');
      return;
    }

    const payload = {
      student_id: inputSid.value.trim(),
      student_name: inputName.value.trim(),
      image: capturedImageBase64
    };

    console.log('Sending payload for SID:', payload.student_id);

    btnSubmitRegistration.disabled = true;
    btnSubmitRegistration.innerHTML = `<i class='bx bx-loader-alt bx-spin'></i> Processing...`;

    try {
      const response = await fetch('/api/students/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await response.json();
      console.log('Response received:', data);

      if (data.success) {
        const studentName = payload.student_name;
        closeRegistration();
        loadStudents();
        // Show success modal
        showSuccessModal(studentName);
      } else {
        console.error('Registration failed:', data.error);
        showGenericAlert('Registration Error', data.error || 'Unknown error occurred.', 'error');
        btnSubmitRegistration.disabled = false;
        btnSubmitRegistration.innerHTML = `<i class='bx bx-check-double'></i> Complete Registration`;
      }
    } catch (error) {
      console.error('Registration request failed:', error);
      showGenericAlert('Connection Error', 'Failed to connect to the server. Please check your network.', 'error');
      btnSubmitRegistration.disabled = false;
      btnSubmitRegistration.innerHTML = `<i class='bx bx-check-double'></i> Complete Registration`;
    }
  });

  // --- Generic Alert Modal Helper ---
  const genericAlertOverlay = document.getElementById('generic-alert-overlay');
  const genericAlertTitle = document.getElementById('generic-alert-title');
  const genericAlertMessage = document.getElementById('generic-alert-message');
  const genericAlertIcon = document.getElementById('generic-alert-icon');
  const genericAlertIconWrapper = document.getElementById('generic-alert-icon-wrapper');
  const btnOkGenericAlert = document.getElementById('btn-ok-generic-alert');
  const btnCloseGenericAlert = document.getElementById('btn-close-generic-alert');

  const showGenericAlert = (title, message, type = 'warning') => {
    if (!genericAlertOverlay) return;
    genericAlertTitle.textContent = title;
    genericAlertMessage.textContent = message;

    // Set icon based on type
    genericAlertIconWrapper.className = `alert-icon-wrapper ${type}`;
    if (type === 'success') genericAlertIcon.className = 'bx bx-check-circle';
    else if (type === 'error') genericAlertIcon.className = 'bx bx-x-circle';
    else genericAlertIcon.className = 'bx bx-error-circle';

    genericAlertOverlay.classList.remove('hidden');
  };

  const closeGenericAlert = () => {
    if (genericAlertOverlay) genericAlertOverlay.classList.add('hidden');
  };

  if (btnOkGenericAlert) btnOkGenericAlert.addEventListener('click', closeGenericAlert);
  if (btnCloseGenericAlert) btnCloseGenericAlert.addEventListener('click', closeGenericAlert);
});
