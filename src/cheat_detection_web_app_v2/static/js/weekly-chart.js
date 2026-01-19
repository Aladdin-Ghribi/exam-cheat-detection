// Weekly Trends Chart Implementation
let weeklyChart = null;

async function loadWeeklyTrends() {
    try {
        const token = localStorage.getItem('token');
        const response = await fetch('/api/weekly-trends', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        const result = await response.json();
        if (result.success) {
            renderWeeklyChart(result.data);
        }
    } catch (error) {
        console.error('Failed to load weekly trends:', error);
    }
}

function renderWeeklyChart(data) {
    const ctx = document.getElementById('weekly-trends-chart');
    if (!ctx) return;

    // Destroy existing chart if it exists
    if (weeklyChart) {
        weeklyChart.destroy();
    }

    weeklyChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels,
            datasets: data.datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 2.5,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        color: '#E0E0E0',
                        font: {
                            size: 12,
                            family: 'Manrope, sans-serif'
                        },
                        padding: 15,
                        usePointStyle: true
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(30, 30, 30, 0.95)',
                    titleColor: '#FFFFFF',
                    bodyColor: '#E0E0E0',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1,
                    padding: 12,
                    displayColors: true,
                    callbacks: {
                        label: function (context) {
                            return context.dataset.label + ': ' + context.parsed.y + ' incidents';
                        }
                    }
                }
            },
            scales: {
                x: {
                    stacked: false,
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: '#888888',
                        font: {
                            size: 11,
                            family: 'Manrope, sans-serif'
                        }
                    }
                },
                y: {
                    stacked: false,
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#888888',
                        font: {
                            size: 11,
                            family: 'Manrope, sans-serif'
                        },
                        stepSize: 1,
                        precision: 0
                    }
                }
            }
        }
    });
}

// Initialize chart on dashboard page load
if (document.getElementById('view-dashboard')) {
    loadWeeklyTrends();
    // Refresh chart every 5 minutes
    setInterval(loadWeeklyTrends, 300000);
}
