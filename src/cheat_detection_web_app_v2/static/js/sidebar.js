document.addEventListener('DOMContentLoaded', () => {
  const toggleBtn = document.getElementById('sidebar-toggle');
  const sidebar = document.getElementById('sidebar');
  const mainContent = document.querySelector('main');
  const appContainer = document.querySelector('.app-container');
  const userProfileBtn = document.getElementById('user-profile-btn');

  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener('click', () => {
      sidebar.classList.toggle('collapsed');

      // Adjust main content to expand/contract with sidebar (from feature/History branch)
      if (mainContent) {
        mainContent.classList.toggle('sidebar-collapsed');
      }

      // Adjust app container (from main branch) 
      if (appContainer) {
        appContainer.classList.toggle('sidebar-collapsed');
      }
    });
  }


});
