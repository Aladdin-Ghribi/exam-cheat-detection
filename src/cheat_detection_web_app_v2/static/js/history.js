// History Page - Mock Data and Functionality

// Generate mock student events data
const generateMockEvents = () => {
  const firstNames = ['John', 'Sarah', 'Michael', 'Emma', 'James', 'Olivia', 'William', 'Sophia', 'David', 'Isabella', 'Robert', 'Mia', 'Daniel', 'Charlotte', 'Thomas', 'Amelia'];
  const lastNames = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez', 'Hernandez', 'Lopez'];

  const eventTypes = [
    { value: 'phone', label: 'Phone Detected', icon: 'bx-mobile' },
    { value: 'looking_away', label: 'Looking Away', icon: 'bx-show-alt' },
    { value: 'suspicious_object', label: 'Suspicious Object', icon: 'bx-error' }
  ];

  const severities = ['high', 'medium', 'low'];
  const exams = ['Mathematics Final', 'Physics Midterm', 'Chemistry Quiz', 'Biology Test', 'History Exam'];

  const events = [];

  for (let i = 0; i < 24; i++) {
    const firstName = firstNames[Math.floor(Math.random() * firstNames.length)];
    const lastName = lastNames[Math.floor(Math.random() * lastNames.length)];
    const studentName = `${firstName} ${lastName}`;
    const studentId = `STU${String(i + 12345).padStart(5, '0')}`;

    const eventCount = Math.floor(Math.random() * 5) + 1;
    const studentEvents = [];

    for (let j = 0; j < eventCount; j++) {
      const eventType = eventTypes[Math.floor(Math.random() * eventTypes.length)];
      const severity = severities[Math.floor(Math.random() * severities.length)];
      const hoursAgo = Math.floor(Math.random() * 48);
      const minutesAgo = Math.floor(Math.random() * 60);
      const timestamp = new Date();
      timestamp.setHours(timestamp.getHours() - hoursAgo);
      timestamp.setMinutes(timestamp.getMinutes() - minutesAgo);

      studentEvents.push({
        eventId: `E${i}_${j}`,
        type: eventType.value,
        typeLabel: eventType.label,
        typeIcon: eventType.icon,
        severity: severity,
        timestamp: timestamp,
        duration: (Math.random() * 10 + 2).toFixed(1),
        confidence: (Math.random() * 0.3 + 0.7).toFixed(2),
        description: `Student exhibited ${eventType.label.toLowerCase()} behavior during exam`,
        evidenceCount: Math.floor(Math.random() * 4) + 1
      });
    }

    // Sort events by timestamp (most recent first)
    studentEvents.sort((a, b) => b.timestamp - a.timestamp);

    events.push({
      id: `EVT${String(i + 1).padStart(3, '0')}`,
      studentId: studentId,
      studentName: studentName,
      studentPhoto: `https://ui-avatars.com/api/?name=${firstName}+${lastName}&background=random&size=200`,
      examName: exams[Math.floor(Math.random() * exams.length)],
      events: studentEvents,
      totalEvents: eventCount,
      highestSeverity: studentEvents.reduce((max, e) => {
        const severityOrder = { high: 3, medium: 2, low: 1 };
        return severityOrder[e.severity] > severityOrder[max] ? e.severity : max;
      }, 'low'),
      lastEventTime: studentEvents[0].timestamp,
      // Status: Pending (awaiting review), Confirmed (proctor confirmed), Declined (false positive)
      status: ['pending', 'confirmed', 'declined'][Math.floor(Math.random() * 3)],
      // Session ID - All events in this card are from the same exam session
      // When student starts a new session, a new event card will be created
      sessionId: `SESSION_${String(i + 1).padStart(4, '0')}`
    });
  }

  return events;
};

// Initialize
let allEvents = [];
let filteredEvents = [];

document.addEventListener('DOMContentLoaded', () => {
  // Fetch real data from backend
  fetchHistoryCards();

  // Setup event listeners
  setupFilterListeners();
  setupModalListeners();
});

async function fetchHistoryCards() {
  try {
    const response = await fetch('/api/history/cards');
    const data = await response.json();

    if (data.cards && data.cards.length > 0) {
      // Transform backend cards to frontend format
      allEvents = data.cards.map(card => transformCardToEvent(card));
      filteredEvents = [...allEvents];

      renderEventCards();
      updateResultsCount();
    } else {
      // No cards found
      allEvents = [];
      filteredEvents = [];
      renderEventCards();
      updateResultsCount();
    }
  } catch (error) {
    console.error('Error fetching history cards:', error);
    // Show empty state on error
    allEvents = [];
    filteredEvents = [];
    renderEventCards();
    updateResultsCount();
  }
}

function transformCardToEvent(card) {
  // Transform backend card format to frontend event format
  const events = card.events || [];
  const latestEvent = events[0] || {};

  // Determine highest severity from all events
  const severityOrder = { high: 3, medium: 2, low: 1 };
  const highestSeverity = events.reduce((max, e) => {
    const score = e.suspicion_score || 0;
    const severity = score >= 80 ? 'high' : (score >= 50 ? 'medium' : 'low');
    return severityOrder[severity] > severityOrder[max] ? severity : max;
  }, 'low');

  return {
    id: card.card_id,
    studentId: card.student_id,
    studentName: card.student_name,
    studentPhoto: `https://ui-avatars.com/api/?name=${encodeURIComponent(card.student_name)}&background=random&size=200`,
    examName: card.session_name || 'Unknown Session',
    events: events.map(e => {
      const reasons = e.reasons || [];
      const firstReason = reasons[0] || '';

      // Map backend reasons to frontend filter values
      let eventType = 'suspicious';
      if (firstReason.includes('Phone')) {
        eventType = 'phone';
      } else if (firstReason.includes('Looking away')) {
        eventType = 'looking_away';
      } else if (firstReason.includes('Suspicious object')) {
        eventType = 'suspicious_object';
      } else if (firstReason.includes('face')) {
        eventType = 'hand_face';
      }

      return {
        eventId: e.event_id,
        type: eventType,
        typeLabel: formatEventType(reasons),
        typeIcon: getEventIcon(reasons),
        severity: e.suspicion_score >= 80 ? 'high' : (e.suspicion_score >= 50 ? 'medium' : 'low'),
        timestamp: new Date(e.timestamp),
        suspicionScore: e.suspicion_score,
        confidence: e.confidence || (e.suspicion_score / 100.0),
        reasons: reasons,
        description: reasons.length > 0 ? reasons.join(', ') : 'Suspicious behavior detected',
        notes: e.notes || '',
        status: e.status || 'pending',
        evidenceCount: e.evidence_count || 2,
        evidencePath: `/api/evidence/${card.card_id}/${e.event_id}`,
        evidence: e.evidence || {}
      };
    }),
    totalEvents: events.length,
    highestSeverity: highestSeverity,
    lastEventTime: events.length > 0 ? new Date(latestEvent.timestamp) : new Date(),
    status: card.status || 'pending',
    sessionId: card.session_id
  };
}

function formatEventType(reasons) {
  if (!reasons || reasons.length === 0) return 'Suspicious Behavior';
  const reason = reasons[0];
  if (reason.includes('Phone')) return 'Phone Detected';
  if (reason.includes('Looking away')) return 'Looking Away';
  if (reason.includes('Suspicious object')) return 'Suspicious Object';
  if (reason.includes('face')) return 'Hand Near Face';
  return 'Suspicious Behavior';
}

function getEventIcon(reasons) {
  if (!reasons || reasons.length === 0) return 'bx-error';
  const reason = reasons[0];
  if (reason.includes('Phone')) return 'bx-mobile';
  if (reason.includes('Looking away')) return 'bx-show-alt';
  if (reason.includes('Suspicious object')) return 'bx-error';
  if (reason.includes('face')) return 'bx-face';
  return 'bx-error';
}

function getUniqueEventTypeBadges(events) {
  // Get unique event types from all events
  const uniqueTypes = new Map();

  events.forEach(event => {
    const typeKey = event.typeLabel;
    if (!uniqueTypes.has(typeKey)) {
      uniqueTypes.set(typeKey, {
        label: event.typeLabel,
        icon: event.typeIcon
      });
    }
  });

  // Generate badges HTML
  return Array.from(uniqueTypes.values()).map(type => `
    <span class="event-type-badge" style="font-size: 0.7rem; padding: 0.25rem 0.5rem; width: fit-content;">
      <i class='bx ${type.icon}' style="font-size: 0.75rem;"></i>
      ${type.label}
    </span>
  `).join('');
}

// Render student event cards
function renderEventCards() {
  const grid = document.getElementById('student-events-grid');
  const emptyState = document.getElementById('empty-state');

  if (filteredEvents.length === 0) {
    grid.innerHTML = '';
    emptyState.classList.remove('hidden');
    return;
  }

  emptyState.classList.add('hidden');

  grid.innerHTML = filteredEvents.map((event, index) => {
    const latestEvent = event.events[0];
    const timeAgo = getTimeAgo(latestEvent.timestamp);

    // Use first event's crop image as thumbnail
    const firstEvidence = latestEvent.evidence || {};
    const evidenceThumbnail = firstEvidence.crop
      ? `/api/evidence/${event.id}/${firstEvidence.crop}`
      : 'static/assets/studentTestPic.png';  // Fallback

    return `
            <div class="student-event-card" data-event-id="${event.id}">
                <!-- Large Thumbnail Header -->
                <div class="event-card-thumbnail">
                    <img src="${evidenceThumbnail}" alt="${event.studentName} Evidence" class="event-thumbnail-image">
                    <div class="event-thumbnail-overlay">
                        <h4 class="event-student-name-overlay">${event.studentName}</h4>
                        <p class="event-student-id-overlay">${event.studentId}</p>
                    </div>
                </div>

                <div class="event-card-body">
                    <div class="event-meta-row">
                        <div style="display: flex; flex-direction: column; gap: 0.25rem; flex: 1;">
                            ${getUniqueEventTypeBadges(event.events)}
                        </div>
                        <span class="severity-badge severity-${event.highestSeverity}">
                            ${event.highestSeverity}
                        </span>
                    </div>

                    <div class="event-timestamp">
                        <i class='bx bx-time-five'></i>
                        ${timeAgo}
                    </div>

                    <div class="event-stats">
                        <div class="event-stat">
                            <span class="event-stat-label">Events</span>
                            <span class="event-stat-value">${event.totalEvents}</span>
                        </div>
                        <div class="event-stat">
                            <span class="event-stat-label">Exam</span>
                            <span class="event-stat-value" style="font-size: 0.875rem;">${event.examName}</span>
                        </div>
                    </div>
                </div>

                <div class="event-card-footer">
                    <button class="btn-view-details" onclick="openEventDetailModal('${event.id}')">
                        View Details
                    </button>
                </div>
            </div>
        `;
  }).join('');
}

// Setup filter listeners
function setupFilterListeners() {
  // Search
  const searchInput = document.getElementById('student-search');
  let searchTimeout;
  searchInput.addEventListener('input', (e) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      applyFilters();
    }, 300);
  });

  // Date filters
  document.getElementById('date-from').addEventListener('change', applyFilters);
  document.getElementById('date-to').addEventListener('change', applyFilters);

  // Event type filters
  document.querySelectorAll('.event-type-filter').forEach(checkbox => {
    checkbox.addEventListener('change', (e) => {
      if (e.target.value === 'all') {
        // If "All Events" is checked, uncheck others
        if (e.target.checked) {
          document.querySelectorAll('.event-type-filter').forEach(cb => {
            if (cb !== e.target) cb.checked = false;
          });
        }
      } else {
        // If any specific event is checked, uncheck "All Events"
        if (e.target.checked) {
          document.querySelector('.event-type-filter[value="all"]').checked = false;
        }
      }
      applyFilters();
    });
  });

  // Severity filters
  document.querySelectorAll('.severity-filter').forEach(checkbox => {
    checkbox.addEventListener('change', applyFilters);
  });

  // Status filters
  document.querySelectorAll('.status-filter').forEach(checkbox => {
    checkbox.addEventListener('change', applyFilters);
  });

  // Clear filters
  document.getElementById('clear-filters').addEventListener('click', clearAllFilters);
}

// Apply all filters
function applyFilters() {
  const searchTerm = document.getElementById('student-search').value.toLowerCase();
  const dateFrom = document.getElementById('date-from').value;
  const dateTo = document.getElementById('date-to').value;

  const selectedEventTypes = Array.from(document.querySelectorAll('.event-type-filter:checked'))
    .map(cb => cb.value);
  const selectedSeverities = Array.from(document.querySelectorAll('.severity-filter:checked'))
    .map(cb => cb.value);
  const selectedStatuses = Array.from(document.querySelectorAll('.status-filter:checked'))
    .map(cb => cb.value);

  filteredEvents = allEvents.filter(event => {
    // Search filter
    if (searchTerm) {
      const matchesSearch = event.studentName.toLowerCase().includes(searchTerm) ||
        event.studentId.toLowerCase().includes(searchTerm);
      if (!matchesSearch) return false;
    }

    // Date filter
    if (dateFrom) {
      const fromDate = new Date(dateFrom);
      if (event.lastEventTime < fromDate) return false;
    }
    if (dateTo) {
      const toDate = new Date(dateTo);
      toDate.setHours(23, 59, 59);
      if (event.lastEventTime > toDate) return false;
    }

    // Event type filter
    if (!selectedEventTypes.includes('all')) {
      const hasMatchingEventType = event.events.some(e =>
        selectedEventTypes.includes(e.type)
      );
      if (!hasMatchingEventType) return false;
    }

    // Severity filter
    if (selectedSeverities.length > 0) {
      if (!selectedSeverities.includes(event.highestSeverity)) return false;
    }

    // Status filter
    if (selectedStatuses.length > 0) {
      if (!selectedStatuses.includes(event.status)) return false;
    }

    return true;
  });

  renderEventCards();
  updateResultsCount();
}

// Clear all filters
function clearAllFilters() {
  document.getElementById('student-search').value = '';
  document.getElementById('date-from').value = '';
  document.getElementById('date-to').value = '';

  document.querySelectorAll('.event-type-filter').forEach(cb => {
    cb.checked = cb.value === 'all';
  });

  document.querySelectorAll('.severity-filter').forEach(cb => {
    cb.checked = true;
  });

  document.querySelectorAll('.status-filter').forEach(cb => {
    cb.checked = true;
  });

  applyFilters();
}

// Update results count
function updateResultsCount() {
  const count = document.getElementById('results-count');
  count.textContent = `${filteredEvents.length} event${filteredEvents.length !== 1 ? 's' : ''} found`;
}

// Time ago helper
function getTimeAgo(date) {
  const seconds = Math.floor((new Date() - date) / 1000);

  if (seconds < 60) return 'Just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)} minutes ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} hours ago`;
  if (seconds < 604800) return `${Math.floor(seconds / 86400)} days ago`;

  return date.toLocaleDateString();
}

// Format timestamp
function formatTimestamp(date) {
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}

// ============================================
// MODAL FUNCTIONALITY
// ============================================

function setupModalListeners() {
  const modal = document.getElementById('event-detail-modal');
  const overlay = document.getElementById('modal-overlay');
  const closeBtn = document.getElementById('modal-close-btn');

  // Close on overlay click
  overlay.addEventListener('click', closeEventDetailModal);

  // Close on button click
  closeBtn.addEventListener('click', closeEventDetailModal);

  // Close on ESC key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !modal.classList.contains('hidden')) {
      closeEventDetailModal();
    }
  });
}

function openEventDetailModal(eventId) {
  const event = allEvents.find(e => e.id === eventId);
  if (!event) return;

  const modal = document.getElementById('event-detail-modal');

  // Store card ID for evidence gallery
  modal.dataset.currentCardId = event.id;

  // Blur the top header when modal opens
  const topHeader = document.querySelector('.top-header');
  if (topHeader) {
    topHeader.classList.add('blur-background');
  }

  // Populate modal header
  document.getElementById('modal-student-photo').src = event.studentPhoto;
  document.getElementById('modal-student-name').textContent = event.studentName;
  document.getElementById('modal-student-id').textContent = `ID: ${event.studentId}`;
  document.getElementById('modal-exam-name').textContent = event.examName;

  // Populate event summary
  document.getElementById('modal-total-events').textContent = event.totalEvents;
  document.getElementById('modal-highest-severity').innerHTML = `<span class="severity-badge severity-${event.highestSeverity}">${event.highestSeverity}</span>`;
  document.getElementById('modal-last-event').textContent = formatTimestamp(event.lastEventTime);

  // Status with color coding
  const statusEl = document.getElementById('modal-status');
  const statusColors = {
    'pending': 'color: #FFA500;',      // Orange
    'confirmed': 'color: #FF4444;',    // Red
    'declined': 'color: #4CAF50;'      // Green
  };
  statusEl.innerHTML = `<span style="${statusColors[event.status] || ''}">${event.status.toUpperCase()}</span>`;

  // Show action buttons only for pending events
  const actionsRow = document.getElementById('modal-status-actions');
  if (event.status === 'pending') {
    actionsRow.innerHTML = `
      <button class="btn-confirm-event" onclick="confirmEvent('${event.id}')">
        <i class='bx bx-check-circle'></i>
        Confirm Event
      </button>
      <button class="btn-decline-event" onclick="declineEvent('${event.id}')">
        <i class='bx bx-x-circle'></i>
        Decline Event
      </button>
    `;
    actionsRow.style.display = 'flex';
  } else {
    actionsRow.style.display = 'none';
  }

  // Populate event timeline
  renderEventTimeline(event.events);

  // Populate evidence gallery
  renderEvidenceGallery(event.events);

  // Show modal
  modal.classList.remove('hidden');
  document.body.style.overflow = 'hidden';
}

function closeEventDetailModal() {
  const modal = document.getElementById('event-detail-modal');
  modal.classList.add('hidden');
  document.body.style.overflow = '';

  // Remove blur from the top header when modal closes
  const topHeader = document.querySelector('.top-header');
  if (topHeader) {
    topHeader.classList.remove('blur-background');
  }
}

function renderEventTimeline(events) {
  const timeline = document.getElementById('event-timeline');

  timeline.innerHTML = events.map(event => `
        <div class="timeline-item">
            <div class="timeline-icon severity-${event.severity}">
                <i class='bx ${event.typeIcon}'></i>
            </div>
            <div class="timeline-content">
                <div class="timeline-header">
                    <span class="timeline-event-type">${event.typeLabel}</span>
                    <span class="timeline-time">${formatTimestamp(event.timestamp)}</span>
                </div>
                <p class="timeline-description">${event.description}</p>
                <div class="timeline-metadata">
                    <span class="timeline-meta-item">
                        <i class='bx bx-bar-chart-alt-2'></i>
                        Confidence: ${(event.confidence * 100).toFixed(0)}%
                    </span>
                    <span class="timeline-meta-item">
                        <i class='bx bx-image-alt'></i>
                        Evidence: ${event.evidenceCount} images
                    </span>
                    <span class="timeline-meta-item">
                        <i class='bx ${event.status === 'confirmed' ? 'bx-check-circle' : (event.status === 'declined' ? 'bx-x-circle' : 'bx-time')}'></i>
                        Status: <strong style="color: ${event.status === 'confirmed' ? '#FF4444' : (event.status === 'declined' ? '#4CAF50' : '#FFA500')}">${event.status.toUpperCase()}</strong>
                    </span>
                </div>
            </div>
        </div>
    `).join('');
}

function renderEvidenceGallery(events) {
  const gallery = document.getElementById('evidence-gallery');

  // Get the current event card ID from modal
  const modal = document.getElementById('event-detail-modal');
  const currentEventCardId = modal.dataset.currentCardId;

  // Generate evidence images from events
  const evidenceImages = [];
  events.forEach((event) => {
    const evidence = event.evidence || {};

    // Add crop image if exists
    if (evidence.crop) {
      evidenceImages.push({
        url: `/api/evidence/${currentEventCardId}/${evidence.crop}`,
        timestamp: event.timestamp,
        eventType: event.typeLabel
      });
    }

    // Add frame image if exists
    if (evidence.frame) {
      evidenceImages.push({
        url: `/api/evidence/${currentEventCardId}/${evidence.frame}`,
        timestamp: event.timestamp,
        eventType: event.typeLabel
      });
    }
  });

  gallery.innerHTML = evidenceImages.slice(0, 12).map((img, index) => `
        <div class="evidence-item" onclick="openEvidenceLightbox('${img.url}', '${formatTimestamp(img.timestamp)}', '${img.eventType}')">
            <img src="${img.url}" alt="Evidence">
            <div class="evidence-item-overlay">
                <span class="evidence-timestamp">${formatTimestamp(img.timestamp)}</span>
            </div>
        </div>
    `).join('');
}

// Confirm event function
function confirmEvent(eventId) {
  const event = allEvents.find(e => e.id === eventId);
  if (event) {
    event.status = 'confirmed';
    // Refresh the modal to update status
    closeEventDetailModal();
    setTimeout(() => openEventDetailModal(eventId), 100);

    // TODO: Send to backend API when connected
    console.log(`Event ${eventId} confirmed`);
  }
}

// Decline event function
function declineEvent(eventId) {
  const event = allEvents.find(e => e.id === eventId);
  if (event) {
    event.status = 'declined';
    // Refresh the modal to update status
    closeEventDetailModal();
    setTimeout(() => openEventDetailModal(eventId), 100);

    // TODO: Send to backend API when connected
    console.log(`Event ${eventId} declined`);
  }
}

// Evidence lightbox for enlarged view
function openEvidenceLightbox(imageUrl, timestamp, eventType) {
  const lightbox = document.getElementById('evidence-lightbox');
  const lightboxImg = document.getElementById('lightbox-image');
  const lightboxCaption = document.getElementById('lightbox-caption');

  lightboxImg.src = imageUrl;
  lightboxCaption.innerHTML = `
    <strong>${eventType}</strong><br>
    ${timestamp}
  `;

  lightbox.classList.remove('hidden');
  document.body.style.overflow = 'hidden';
}

function closeEvidenceLightbox() {
  const lightbox = document.getElementById('evidence-lightbox');
  lightbox.classList.add('hidden');
  document.body.style.overflow = '';
}
