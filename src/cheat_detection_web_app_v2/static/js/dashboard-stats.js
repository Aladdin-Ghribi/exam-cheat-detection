// Fetch and update dashboard statistics
async function updateDashboardStats() {
    try {
        const token = localStorage.getItem('token');
        const response = await fetch('/api/dashboard-stats', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        const data = await response.json();
        if (data.success) {
            document.getElementById('phone-detected-count').textContent = data.stats.phone_detected;
            document.getElementById('looking-away-count').textContent = data.stats.looking_away;
            document.getElementById('suspicious-objects-count').textContent = data.stats.suspicious_objects;

            // Also update total alerts if it exists
            const totalAlertsEl = document.querySelector('.stats-grid .stat-value');
            if (totalAlertsEl) {
                totalAlertsEl.textContent = data.stats.total_alerts;
            }
        }
    } catch (error) {
        console.error('Failed to fetch dashboard stats:', error);
    }
}

// Update stats on page load and every 30 seconds
if (document.getElementById('view-dashboard')) {
    updateDashboardStats();
    setInterval(updateDashboardStats, 30000);
}
