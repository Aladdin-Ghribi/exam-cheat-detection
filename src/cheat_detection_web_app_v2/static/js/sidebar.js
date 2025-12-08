document.addEventListener('DOMContentLoaded', () => {
  const toggleBtn = document.getElementById('sidebar-toggle');
  const sidebar = document.getElementById('sidebar');
  const appContainer = document.querySelector('.app-container');

  if (toggleBtn && sidebar && appContainer) {
    toggleBtn.addEventListener('click', () => {
      sidebar.classList.toggle('collapsed');
      appContainer.classList.toggle('sidebar-collapsed');
    });
  }
});
