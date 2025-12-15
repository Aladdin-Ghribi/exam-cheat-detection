document.addEventListener('DOMContentLoaded', () => {
  const userProfileBtn = document.getElementById('user-profile-btn');
  
  if (userProfileBtn) {
    userProfileBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      showProfileModal();
    });
  }
});

function showProfileModal() {
  const existingModal = document.getElementById('profile-modal');
  if (existingModal) {
    existingModal.remove();
  }

  const user = JSON.parse(localStorage.getItem('user') || '{}');
  const username = user.username || 'User';
  const email = user.email || 'N/A';
  const role = user.role || 'N/A';

  const modal = document.createElement('div');
  modal.id = 'profile-modal';
  modal.innerHTML = `
    <div class="profile-modal-overlay">
      <div class="profile-modal-content">
        <button class="profile-modal-close">&times;</button>
        <div class="profile-modal-header">
          <img src="https://ui-avatars.com/api/?name=${username}&background=random" alt="${username}" class="profile-modal-avatar">
          <h2>${username}</h2>
          <p>${role}</p>
        </div>
        <div class="profile-modal-body">
          <div class="profile-info-item">
            <i class='bx bx-user'></i>
            <div>
              <label>Username</label>
              <span>${username}</span>
            </div>
          </div>
          <div class="profile-info-item">
            <i class='bx bx-envelope'></i>
            <div>
              <label>Email</label>
              <span>${email}</span>
            </div>
          </div>
          <div class="profile-info-item">
            <i class='bx bx-shield'></i>
            <div>
              <label>Role</label>
              <span>${role}</span>
            </div>
          </div>
          <div class="profile-info-item">
            <i class='bx bx-time'></i>
            <div>
              <label>Last Login</label>
              <span>${new Date().toLocaleString()}</span>
            </div>
          </div>
        </div>
        <div class="profile-modal-footer">
          <button class="profile-btn edit-profile-btn">Edit Profile</button>
          <button class="profile-btn logout-btn">Logout</button>
        </div>
      </div>
    </div>
  `;

  document.body.appendChild(modal);

  const closeBtn = modal.querySelector('.profile-modal-close');
  const overlay = modal.querySelector('.profile-modal-overlay');
  const editBtn = modal.querySelector('.edit-profile-btn');

  closeBtn.addEventListener('click', () => modal.remove());
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) modal.remove();
  });
  
  editBtn.addEventListener('click', () => {
    modal.remove();
    showEditProfileModal(user);
  });

  const logoutBtn = modal.querySelector('.logout-btn');
  logoutBtn.addEventListener('click', () => {
    showLogoutConfirmation();
  });
}

function showEditProfileModal(user) {
  const existingModal = document.getElementById('edit-profile-modal');
  if (existingModal) {
    existingModal.remove();
  }

  const modal = document.createElement('div');
  modal.id = 'edit-profile-modal';
  modal.innerHTML = `
    <div class="profile-modal-overlay">
      <div class="profile-modal-content">
        <button class="profile-modal-close">&times;</button>
        <div class="profile-modal-header">
          <h2>Edit Profile</h2>
          <p>Update your profile information</p>
        </div>
        <div class="profile-modal-body">
          <div class="profile-edit-form">
            <div class="form-group">
              <label for="edit-username">Username</label>
              <input type="text" id="edit-username" value="${user.username || ''}" required>
            </div>
            <div class="form-group">
              <label for="edit-email">Email</label>
              <input type="email" id="edit-email" value="${user.email || ''}" required>
            </div>
            <div class="form-group">
              <label for="edit-password">New Password (leave empty to keep current)</label>
              <input type="password" id="edit-password" placeholder="Enter new password">
            </div>
            <div class="form-group">
              <label for="confirm-password">Confirm New Password</label>
              <input type="password" id="confirm-password" placeholder="Confirm new password">
            </div>
          </div>
        </div>
        <div class="profile-modal-footer">
          <button class="profile-btn save-profile-btn">Save Changes</button>
          <button class="profile-btn cancel-edit-btn">Cancel</button>
        </div>
      </div>
    </div>
  `;

  document.body.appendChild(modal);

  const closeBtn = modal.querySelector('.profile-modal-close');
  const overlay = modal.querySelector('.profile-modal-overlay');
  const saveBtn = modal.querySelector('.save-profile-btn');
  const cancelBtn = modal.querySelector('.cancel-edit-btn');

  closeBtn.addEventListener('click', () => modal.remove());
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) modal.remove();
  });

  cancelBtn.addEventListener('click', () => modal.remove());

  saveBtn.addEventListener('click', () => {
    const username = modal.querySelector('#edit-username').value.trim();
    const email = modal.querySelector('#edit-email').value.trim();
    const password = modal.querySelector('#edit-password').value;
    const confirmPassword = modal.querySelector('#confirm-password').value;

    if (!username || !email) {
      alert('Username and email are required.');
      return;
    }

    if (password && password !== confirmPassword) {
      alert('Passwords do not match.');
      return;
    }

    showSaveConfirmation(user.id, username, email, password);
  });
}

function showSaveConfirmation(userId, username, email, password) {
  const confirmModal = document.createElement('div');
  confirmModal.id = 'save-confirm-modal';
  confirmModal.innerHTML = `
    <div class="profile-modal-overlay">
      <div class="logout-confirm-content">
        <h3>Are you sure you want to save changes?</h3>
        <div class="logout-confirm-buttons">
          <button class="confirm-btn yes-save-btn">Yes</button>
          <button class="confirm-btn cancel-save-btn">Cancel</button>
        </div>
      </div>
    </div>
  `;

  document.body.appendChild(confirmModal);

  const yesBtn = confirmModal.querySelector('.yes-save-btn');
  const cancelBtn = confirmModal.querySelector('.cancel-save-btn');
  const overlay = confirmModal.querySelector('.profile-modal-overlay');

  yesBtn.addEventListener('click', () => {
    confirmModal.remove();
    saveProfileChanges(userId, username, email, password);
  });

  cancelBtn.addEventListener('click', () => confirmModal.remove());
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) confirmModal.remove();
  });
}

function saveProfileChanges(userId, username, email, password) {
  const user = JSON.parse(localStorage.getItem('user') || '{}');
  fetch('/api/user/update', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      id: userId,
      username: username,
      email: email,
      password: password,
      current_user_role: user.role
    })
  })
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      // Update localStorage with new user data
      const updatedUser = {
        id: userId,
        username: username,
        email: email,
        role: JSON.parse(localStorage.getItem('user') || '{}').role
      };
      localStorage.setItem('user', JSON.stringify(updatedUser));

      // Close edit modal
      const editModal = document.getElementById('edit-profile-modal');
      if (editModal) editModal.remove();

      alert('Profile updated successfully!');
    } else {
      alert('Error updating profile: ' + data.error);
    }
  })
  .catch(error => {
    console.error('Error:', error);
    alert('An error occurred while updating your profile.');
  });
}

function showLogoutConfirmation() {
  const confirmModal = document.createElement('div');
  confirmModal.id = 'logout-confirm-modal';
  confirmModal.innerHTML = `
    <div class="profile-modal-overlay">
      <div class="logout-confirm-content">
        <h3>Are you sure you want to log out?</h3>
        <div class="logout-confirm-buttons">
          <button class="confirm-btn yes-btn">Yes</button>
          <button class="confirm-btn cancel-btn">Cancel</button>
        </div>
      </div>
    </div>
  `;

  document.body.appendChild(confirmModal);

  const yesBtn = confirmModal.querySelector('.yes-btn');
  const cancelBtn = confirmModal.querySelector('.cancel-btn');
  const overlay = confirmModal.querySelector('.profile-modal-overlay');

  yesBtn.addEventListener('click', () => {
    confirmModal.remove();
    localStorage.clear();
    window.location.replace('/');
  });

  cancelBtn.addEventListener('click', () => confirmModal.remove());
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) confirmModal.remove();
  });
}
