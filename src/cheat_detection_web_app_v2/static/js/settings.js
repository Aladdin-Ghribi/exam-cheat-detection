document.addEventListener('DOMContentLoaded', () => {
  const settingsNavItems = document.querySelectorAll('.settings-nav-item');
  const settingsTitle = document.getElementById('settings-title');

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
    });
  });

  const confidenceSlider = document.getElementById('confidence-slider');
  const confidenceValue = document.getElementById('confidence-value');
  if (confidenceSlider && confidenceValue) {
    confidenceSlider.addEventListener('input', (e) => {
      confidenceValue.textContent = parseFloat(e.target.value).toFixed(2);
    });
  }

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
    }
  });

  const suspicionSaveSlider = document.getElementById('suspicion-save-slider');
  const suspicionSaveValue = document.getElementById('suspicion-save-value');
  if (suspicionSaveSlider && suspicionSaveValue) {
    suspicionSaveSlider.addEventListener('input', (e) => {
      suspicionSaveValue.textContent = e.target.value;
    });
  }

  const smoothingSlider = document.getElementById('smoothing-slider');
  const smoothingValue = document.getElementById('smoothing-value');
  if (smoothingSlider && smoothingValue) {
    smoothingSlider.addEventListener('input', (e) => {
      smoothingValue.textContent = parseFloat(e.target.value).toFixed(1);
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
});
