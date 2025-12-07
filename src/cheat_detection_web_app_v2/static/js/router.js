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

      if (currentView && selectedView && currentView !== selectedView) {
        // Add fade-out to current view
        currentView.classList.add('fade-out');

        setTimeout(() => {
          // Hide all views
          document.querySelectorAll('.page-view').forEach(view => {
            view.classList.add('hidden');
            view.classList.remove('active', 'fade-out', 'fade-in');
          });

          // Show selected view with fade-in
          selectedView.classList.remove('hidden');
          selectedView.classList.add('active');

          // Trigger fade-in animation
          setTimeout(() => {
            selectedView.classList.add('fade-in');
          }, 10);
        }, 150); // Wait for fade-out to complete
      }
    });
  });
});
