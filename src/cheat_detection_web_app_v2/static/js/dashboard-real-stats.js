// Real Dashboard Statistics Integration
// Connects all dashboard elements with live backend data

let dashboardStatsChart = null;
let detectionPieChart = null;
let weeklyDetectionsChart = null;

// Fetch and update all dashboard statistics
async function loadDashboardStatistics() {
  try {
    const response = await fetch('/api/dashboard/statistics');
    const data = await response.json();

    if (data.success) {
      const stats = data.statistics;

      // Update stat cards
      updateStatCards(stats);

      // Update detection types pie chart
      updateDetectionTypesChart(stats.detection_types);

      // Update top subjects list
      updateTopSubjects(stats.top_subjects);

      // Update weekly detections chart
      updateWeeklyDetectionsChart(stats.weekly_data);

      console.log('Dashboard statistics loaded successfully');
    }
  } catch (error) {
    console.error('Failed to load dashboard statistics:', error);
  }
}

// Update stat cards (Confirmed %, Declined %, Total Alerts, Avg Review Time)
function updateStatCards(stats) {
  // Confirmed Percentage
  const confirmedPercentageEl = document.getElementById('confirmed-percentage');
  const confirmedFillEl = document.querySelector('.confirmed-fill');
  if (confirmedPercentageEl) {
    confirmedPercentageEl.textContent = stats.confirmed_percentage + ' %';
  }
  if (confirmedFillEl) {
    confirmedFillEl.style.width = stats.confirmed_percentage + '%';
  }

  // Declined Percentage
  const declinedPercentageEl = document.getElementById('declined-percentage');
  const declinedFillEl = document.querySelector('.declined-fill');
  if (declinedPercentageEl) {
    declinedPercentageEl.textContent = stats.declined_percentage + ' %';
  }
  if (declinedFillEl) {
    declinedFillEl.style.width = stats.declined_percentage + '%';
  }

  // Total Alerts
  const totalAlertsEl = document.getElementById('total-alerts');
  if (totalAlertsEl) {
    totalAlertsEl.textContent = stats.total_alerts;
  }

  // Average Review Time
  const avgReviewTimeEl = document.getElementById('avg-review-time');
  if (avgReviewTimeEl) {
    avgReviewTimeEl.textContent = stats.avg_review_time_minutes + 'm';
  }
}

// Update Detection Types Pie Chart
function updateDetectionTypesChart(detectionTypes) {
  const pieCtx = document.getElementById('detection-type-pie-chart');
  if (!pieCtx) return;

  const phonePercent = detectionTypes.phone || 0;
  const lookingAwayPercent = detectionTypes.looking_away || 0;
  const suspiciousObjectPercent = detectionTypes.suspicious_object || 0;
  const handFacePercent = detectionTypes.hand_face || 0;

  // Update legend values
  const phoneCountEl = document.getElementById('phone-count');
  const lookingAwayCountEl = document.getElementById('looking-away-count');
  const suspiciousObjectCountEl = document.getElementById('suspicious-object-count');
  const handFaceCountEl = document.getElementById('hand-face-count');

  if (phoneCountEl) phoneCountEl.textContent = phonePercent + '%';
  if (lookingAwayCountEl) lookingAwayCountEl.textContent = lookingAwayPercent + '%';
  if (suspiciousObjectCountEl) suspiciousObjectCountEl.textContent = suspiciousObjectPercent + '%';
  if (handFaceCountEl) handFaceCountEl.textContent = handFacePercent + '%';

  // Destroy existing chart if it exists
  if (detectionPieChart) {
    detectionPieChart.destroy();
  }

  // Create new chart with real data
  detectionPieChart = new Chart(pieCtx, {
    type: 'doughnut',
    data: {
      labels: ['Phone', 'Looking Away', 'Suspicious Object', 'Hand Near Face'],
      datasets: [{
        data: [phonePercent, lookingAwayPercent, suspiciousObjectPercent, handFacePercent],
        backgroundColor: [
          '#FFB84D',
          '#0071FF',
          '#00C851',
          '#FF6B6B'
        ],
        borderWidth: 0,
        hoverOffset: 8
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '70%',
      plugins: {
        legend: {
          display: false
        },
        tooltip: {
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          titleColor: '#fff',
          bodyColor: '#fff',
          borderColor: 'rgba(255, 255, 255, 0.1)',
          borderWidth: 1,
          padding: 12,
          displayColors: true,
          callbacks: {
            label: function (context) {
              return context.label + ': ' + context.parsed + '%';
            }
          }
        }
      }
    }
  });
}

// Update Top Subjects List
function updateTopSubjects(subjects) {
  const subjectsListEl = document.querySelector('.top-subjects-list');
  if (!subjectsListEl || !subjects || subjects.length === 0) return;

  // Clear existing content
  subjectsListEl.innerHTML = '';

  // Ensure we have exactly 6 subjects (add defaults if needed)
  const defaultSubjects = [
    { name: 'Mathematics', count: 0, percentage: 0 },
    { name: 'Physics', count: 0, percentage: 0 },
    { name: 'Chemistry', count: 0, percentage: 0 },
    { name: 'Biology', count: 0, percentage: 0 },
    { name: 'Computer Science', count: 0, percentage: 0 },
    { name: 'English', count: 0, percentage: 0 }
  ];

  const displaySubjects = subjects.length > 0 ? subjects : defaultSubjects;
  const maxCount = displaySubjects.length > 0 ? Math.max(...displaySubjects.map(s => s.count)) : 1;

  displaySubjects.slice(0, 6).forEach((subject, index) => {
    const barWidth = maxCount > 0 ? (subject.count / maxCount * 100) : 0;

    const subjectItem = document.createElement('div');
    subjectItem.className = 'subject-item';
    subjectItem.innerHTML = `
      <div class="subject-rank">${index + 1}</div>
      <div class="subject-info">
        <div class="subject-name">${subject.name}</div>
        <div class="subject-bar-container">
          <div class="subject-bar-fill" style="width: ${barWidth}%;"></div>
        </div>
      </div>
      <div class="subject-count">${subject.count}</div>
    `;

    subjectsListEl.appendChild(subjectItem);
  });
}

// Store full weekly data globally for filtering
let fullWeeklyData = null;

// Update Weekly Detections Chart
function updateWeeklyDetectionsChart(weeklyData) {
  const weeklyCtx = document.getElementById('weekly-detections-chart');
  if (!weeklyCtx || !weeklyData) return;

  // Store full data for filtering
  fullWeeklyData = weeklyData;

  // Get selected time range (default to 12 months)
  const filterSelect = document.getElementById('monthly-trend-filter');
  const monthsToShow = filterSelect ? parseInt(filterSelect.value) : 12;

  // Filter data based on selected range
  const filteredData = filterWeeklyData(weeklyData, monthsToShow);

  // Destroy existing chart if it exists
  if (weeklyDetectionsChart) {
    weeklyDetectionsChart.destroy();
  }

  // Create new chart with filtered data
  weeklyDetectionsChart = new Chart(weeklyCtx, {
    type: 'line',
    data: {
      labels: filteredData.labels,
      datasets: [{
        label: 'High Priority',
        data: filteredData.high,
        fill: true,
        backgroundColor: function (context) {
          const ctx = context.chart.ctx;
          const gradient = ctx.createLinearGradient(0, 0, 0, 280);
          gradient.addColorStop(0, 'rgba(255, 184, 77, 0.4)');
          gradient.addColorStop(1, 'rgba(255, 184, 77, 0)');
          return gradient;
        },
        borderColor: '#FFB84D',
        borderWidth: 3,
        tension: 0.4,
        pointRadius: 0,
        pointHoverRadius: 6,
        pointHoverBackgroundColor: '#FFB84D',
        pointHoverBorderColor: '#fff',
        pointHoverBorderWidth: 2
      }, {
        label: 'Medium Priority',
        data: weeklyData.medium,
        fill: true,
        backgroundColor: function (context) {
          const ctx = context.chart.ctx;
          const gradient = ctx.createLinearGradient(0, 0, 0, 280);
          gradient.addColorStop(0, 'rgba(0, 113, 255, 0.3)');
          gradient.addColorStop(1, 'rgba(0, 113, 255, 0)');
          return gradient;
        },
        borderColor: '#0071FF',
        borderWidth: 3,
        tension: 0.4,
        pointRadius: 0,
        pointHoverRadius: 6,
        pointHoverBackgroundColor: '#0071FF',
        pointHoverBorderColor: '#fff',
        pointHoverBorderWidth: 2
      }, {
        label: 'Low Priority',
        data: weeklyData.low,
        fill: true,
        backgroundColor: function (context) {
          const ctx = context.chart.ctx;
          const gradient = ctx.createLinearGradient(0, 0, 0, 280);
          gradient.addColorStop(0, 'rgba(0, 200, 81, 0.2)');
          gradient.addColorStop(1, 'rgba(0, 200, 81, 0)');
          return gradient;
        },
        borderColor: '#00C851',
        borderWidth: 3,
        tension: 0.4,
        pointRadius: 0,
        pointHoverRadius: 6,
        pointHoverBackgroundColor: '#00C851',
        pointHoverBorderColor: '#fff',
        pointHoverBorderWidth: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false
        },
        tooltip: {
          mode: 'index',
          intersect: false,
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          titleColor: '#fff',
          bodyColor: '#fff',
          borderColor: 'rgba(255, 255, 255, 0.1)',
          borderWidth: 1,
          padding: 12,
          displayColors: true,
          boxWidth: 8,
          boxHeight: 8
        }
      },
      scales: {
        x: {
          grid: {
            display: false
          },
          ticks: {
            color: '#9CA3AF',
            font: {
              size: 11
            }
          }
        },
        y: {
          grid: {
            color: 'rgba(255, 255, 255, 0.05)'
          },
          ticks: {
            color: '#9CA3AF',
            font: {
              size: 11
            },
            callback: function (value) {
              return value >= 1000 ? (value / 1000) + 'k' : value;
            }
          }
        }
      },
      interaction: {
        mode: 'nearest',
        axis: 'x',
        intersect: false
      }
    }
  });
}

// Filter weekly data based on selected month range
function filterWeeklyData(data, monthsToShow) {
  if (!data || !data.labels) return data;

  // Get the last N months (ensuring current month is always included)
  const totalMonths = data.labels.length;
  const startIndex = Math.max(0, totalMonths - monthsToShow);

  console.log(`Filtering ${monthsToShow} months:`);
  console.log(`Total months: ${totalMonths}, Start index: ${startIndex}`);
  console.log(`Original labels: ${data.labels}`);
  console.log(`Filtered labels: ${data.labels.slice(startIndex)}`);
  console.log(`Original high data: ${data.high}`);
  console.log(`Filtered high data: ${data.high.slice(startIndex)}`);

  return {
    labels: data.labels.slice(startIndex),
    high: data.high.slice(startIndex),
    medium: data.medium.slice(startIndex),
    low: data.low.slice(startIndex)
  };
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function () {
  if (document.getElementById('view-dashboard')) {
    // Wait for Chart.js to be ready
    setTimeout(() => {
      loadDashboardStatistics();
      // Refresh every 30 seconds
      setInterval(loadDashboardStatistics, 30000);
    }, 500);

    // Add event listener for time filter dropdown
    const filterSelect = document.getElementById('monthly-trend-filter');
    if (filterSelect) {
      filterSelect.addEventListener('change', function () {
        if (fullWeeklyData) {
          updateWeeklyDetectionsChart(fullWeeklyData);
        }
      });
    }
  }
});

// Also reload when switching to dashboard page
document.addEventListener('pageChanged', function (e) {
  if (e.detail.page === 'dashboard') {
    setTimeout(loadDashboardStatistics, 300);
  }
});
