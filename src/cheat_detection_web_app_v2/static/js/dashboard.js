// Update time, date, and uptime
document.addEventListener('DOMContentLoaded', () => {
  const timeElement = document.getElementById('current-time');
  const dateElement = document.getElementById('current-date');
  const uptimeElement = document.getElementById('system-uptime');

  // Start time for uptime calculation
  const startTime = Date.now();

  function updateClock() {
    const now = new Date();

    // Update time (HH:MM format)
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    if (timeElement) {
      timeElement.textContent = `${hours}:${minutes}`;
    }

    // Update date (YYYY-MM-DD format)
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    if (dateElement) {
      const dateSpan = dateElement.querySelector('span');
      if (dateSpan) {
        dateSpan.textContent = `${year}-${month}-${day}`;
      }
    }
  }

  function updateUptime() {
    const elapsed = Date.now() - startTime;
    const seconds = Math.floor(elapsed / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    const remainingMinutes = minutes % 60;

    if (uptimeElement) {
      if (days > 0) {
        uptimeElement.textContent = `${days}d ${remainingMinutes}m`;
      } else if (hours > 0) {
        uptimeElement.textContent = `${hours}h ${remainingMinutes}m`;
      } else {
        uptimeElement.textContent = `${remainingMinutes}m`;
      }
    }
  }

  // Initial update
  updateClock();
  updateUptime();

  // Update every second
  setInterval(updateClock, 1000);
  setInterval(updateUptime, 60000); // Update uptime every minute
});
