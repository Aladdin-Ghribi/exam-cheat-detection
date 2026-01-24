// SPA Router with Animations
document.addEventListener('DOMContentLoaded', () => {
  const navItems = document.querySelectorAll('.nav-item');
  const pageTitle = document.getElementById('page-title');

  navItems.forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();

      // Remove active class from all nav items
      navItems.forEach(nav => nav.classList.remove('active'));
      // Add active class to clicked item
      item.classList.add('active');

      // Get page name
      const pageId = item.dataset.page;
      const viewId = `view-${pageId}`;

      // Update Title
      pageTitle.textContent = item.querySelector('span').textContent;

      // Get current and new views
      const currentView = document.querySelector('.page-view.active');
      const selectedView = document.getElementById(viewId);

      console.log(`Navigation: ${pageId} -> ${viewId}`);
      console.log('Current view:', currentView);
      console.log('Selected view:', selectedView);

      if (currentView && selectedView && currentView !== selectedView) {
        // Add fade-out to current view
        currentView.classList.add('fade-out');

        setTimeout(() => {
          console.log('=== INSIDE TIMEOUT ===');
          console.log('About to process views...');

          // Hide all views
          document.querySelectorAll('.page-view').forEach(view => {
            console.log('Processing view:', view.id, 'Classes before:', view.className);
            view.classList.add('hidden');
            view.classList.remove('active', 'fade-out', 'fade-in');
            console.log('Classes after:', view.className);
          });

          console.log('All views processed. About to show selected view...');
          console.log('Selected view before show:', selectedView);

          // Show selected view with fade-in
          selectedView.classList.remove('hidden');
          selectedView.classList.add('active');

          console.log('Selected view after show:', selectedView.className);

          // Trigger fade-in animation
          setTimeout(() => {
            selectedView.classList.add('fade-in');
            console.log('Fade-in animation added');
          }, 10);

          // ===== PAGE-SPECIFIC REFRESH CALLBACKS =====
          // Refresh History page data when navigating to it
          if (pageId === 'history' && typeof fetchHistoryCards === 'function') {
            fetchHistoryCards();
          }

          // Refresh Settings page data when navigating to it
          if (pageId === 'settings') {
            // Load accounts if profile section is visible
            if (typeof loadAccountsOverview === 'function') {
              loadAccountsOverview();
            }
            // Load config for detection settings
            if (typeof loadConfig === 'function') {
              loadConfig();
            }
          }

          // Initialize Monitor page dropdowns when navigating to it
          if (pageId === 'monitor') {
            console.log('Navigated to Monitor - Initializing dropdowns...');
            if (typeof initSubjectDropdowns === 'function') {
              initSubjectDropdowns();
            } else {
              console.error('initSubjectDropdowns function is not defined');
            }
            if (typeof startWebcamPreview === 'function') {
              // Ensure webcam is active
              startWebcamPreview();
            }
          }

        }, 150); // Wait for fade-out to complete
      }
    });
  });

  console.log('Router initialized.');
});
