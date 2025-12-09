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

  const modal = document.createElement('div');
  modal.id = 'profile-modal';
  modal.innerHTML = `
    <div class="profile-modal-overlay">
      <div class="profile-modal-content">
        <button class="profile-modal-close">&times;</button>
        <div class="profile-modal-header">
          <img src="https://ui-avatars.com/api/?name=Admin&background=random" alt="Admin" class="profile-modal-avatar">
          <h2>Admin User</h2>
          <p>Proctor Access</p>
        </div>
        <div class="profile-modal-body">
          <div class="profile-info-item">
            <i class='bx bx-user'></i>
            <div>
              <label>Username</label>
              <span>admin_user</span>
            </div>
          </div>
          <div class="profile-info-item">
            <i class='bx bx-envelope'></i>
            <div>
              <label>Email</label>
              <span>admin@proctor.com</span>
            </div>
          </div>
          <div class="profile-info-item">
            <i class='bx bx-shield'></i>
            <div>
              <label>Role</label>
              <span>Administrator</span>
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
    document.querySelector('.nav-item[data-page="settings"]').click();
    setTimeout(() => {
      document.querySelector('.settings-nav-item[data-setting="profile"]').click();
    }, 200);
  });

  const logoutBtn = modal.querySelector('.logout-btn');
  logoutBtn.addEventListener('click', () => {
    showLogoutConfirmation();
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
    window.location.href = '/logout';
  });

  cancelBtn.addEventListener('click', () => confirmModal.remove());
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) confirmModal.remove();
  });
}
