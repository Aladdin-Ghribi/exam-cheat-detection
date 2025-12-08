document.addEventListener('DOMContentLoaded', () => {
  // Sidebar Toggle Logic
  const toggleBtn = document.getElementById('sidebar-toggle');
  const sidebar = document.getElementById('sidebar');
  const mainContent = document.querySelector('main');

  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener('click', () => {
      sidebar.classList.toggle('collapsed');

      // Adjust main content to expand/contract with sidebar
      if (mainContent) {
        mainContent.classList.toggle('sidebar-collapsed');
      }
    });
  }
});
