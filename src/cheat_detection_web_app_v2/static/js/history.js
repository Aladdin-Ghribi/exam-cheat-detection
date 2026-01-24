// History Page - Mock Data and Functionality

const subjectTree = {
  "Computer Science": {
    "General Subjects": [
      "Mathematics 1",
      "Mathematics 2",
      "English Language 1",
      "English Language 2",
      "Political Science Principles",
      "Statistics and Probabilities",
      "Islamic Culture",
      "Arabic Language",
      "Linear Algebra and Logic",

    ],
    "Specialized Subjects": [
      "Programming Basics",
      "Intro to Computer Science",
      "Electrical Engineering Principles",
      "Digital Systems Intro",
      "Computer Organization",
      "Assembly Language",
      "C Language",
      "Systems Analysis",
      "Database Management",
      "Software Engineering",
      "Operating Systems",
      "Visual Programming 1",
      "Visual Programming 2",
      "Data Structures 1",
      "Data Structures 2",
      "Network Programming",
      "Java Language",
      "Web Design",
      "Modeling and Simulation",
      "Artificial Intelligence",
      "Computer Graphics",
      "Image Processing",
      "Mobile Applications",
      "Computer Architecture",
      "Computer Networks",
      "System Programming",
      "Data and Information Security",
      "Network Building and Protection",
      "Discrete Mathematics",
      "Numerical Methods and Programming"
    ]
  }
};

// Generate mock student events data
const generateMockEvents = () => {
  const firstNames = ['John', 'Sarah', 'Michael', 'Emma', 'James', 'Olivia', 'William', 'Sophia', 'David', 'Isabella', 'Robert', 'Mia', 'Daniel', 'Charlotte', 'Thomas', 'Amelia'];
  const lastNames = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez', 'Hernandez', 'Lopez'];

  const eventTypes = [
    { value: 'phone', label: 'Phone Detected', icon: 'bx-mobile' },
    { value: 'looking_away', label: 'Looking Away', icon: 'bx-show-alt' },
    { value: 'suspicious_object', label: 'Suspicious Object', icon: 'bx-error' },
    { value: 'hand_face', label: 'Hand Near Face', icon: 'bx-face' }
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
  // Populate Department Dropdown
  const departmentSelect = document.getElementById('department-select-simple');
  if (departmentSelect && typeof subjectTree !== 'undefined') {
    departmentSelect.innerHTML = '<option value="">All Departments</option>';
    Object.keys(subjectTree).forEach(dept => {
      const option = document.createElement('option');
      option.value = dept;
      option.textContent = dept;
      departmentSelect.appendChild(option);
    });
  }

  // Fetch real data from backend
  fetchHistoryCards();

  // Setup event listeners
  setupFilterListeners();

  // Setup modal listeners after DOM is ready
  setTimeout(() => {
    setupModalListeners();
  }, 100);
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
    examName: (function () {
      let name = card.exam_name || card.session_name || 'Unknown Session';
      if (!card.exam_name && typeof name === 'string' && name.includes(' - ')) {
        return name.split(' - ')[1];
      }
      return name;
    })(),
    department: card.department || 'N/A',
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
        description: reasons.length > 0 ? reasons.join(', ') : '',
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
    notes: card.notes || '',
    sessionId: card.session_id,
    department: card.department || 'N/A',
    examFullName: card.exam_name || card.session_name || 'N/A',
    // GDPR retention data
    createdAt: card.created_at ? new Date(card.created_at) : new Date(),
    deletionDate: card.deletion_date ? new Date(card.deletion_date) : null,
    retentionPeriod: card.retention_period || 7
  };
}

function formatEventType(reasons) {
  if (!reasons || reasons.length === 0) return 'Unknown';
  const reason = reasons[0];
  if (reason.includes('Phone')) return 'Phone Detected';
  if (reason.includes('Looking away')) return 'Looking Away';
  if (reason.includes('Suspicious object')) return 'Suspicious Object';
  if (reason.includes('face')) return 'Hand Near Face';
  return 'Unknown';
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
    <span class="event-type-badge">
      <i class='bx ${type.icon}'></i>
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

    // Get retention countdown and icon
    const retentionCountdown = getRetentionCountdown(event.deletionDate);
    const retentionIconData = getRetentionIcon(event.deletionDate);

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
                        <div style="display: flex; flex-direction: row; flex-wrap: wrap; gap: 0.4rem; flex: 1; align-items: center;">
                            ${getUniqueEventTypeBadges(event.events)}
                        </div>
                        <span class="severity-badge severity-${event.highestSeverity}">
                            ${event.highestSeverity}
                        </span>
                    </div>

                    <div class="event-timestamp ${retentionIconData.class}">
                        <i class='bx ${retentionIconData.icon}'></i>
                        ${retentionCountdown}
                    </div>

                    <div class="event-stats">
                        <div class="event-stat">
                            <span class="event-stat-label">Department</span>
                            <span class="event-stat-value" style="font-size: 0.8rem; color: #70E1FF;">${event.department}</span>
                        </div>
                        <div class="event-stat">
                            <span class="event-stat-label">Exam Name</span>
                            <span class="event-stat-value" style="font-size: 0.875rem;">${event.examName}</span>
                        </div>
                    </div>

                    ${event.notes ? `
                    <div class="event-notes-preview">
                        <span class="notes-label"><i class='bx bx-note'></i> Proctor Note</span>
                        <p>${event.notes}</p>
                    </div>
                    ` : ''}
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

// Setup filter listeners for sidebar filter panel
function setupFilterListeners() {
  // Filter toggle button
  const filterToggleBtn = document.getElementById('filter-toggle-btn');
  const filterPanel = document.querySelector('.history-filter-panel');
  const filterContent = document.getElementById('filter-bar-content');

  if (filterToggleBtn && filterPanel && filterContent) {
    filterToggleBtn.addEventListener('click', () => {
      filterPanel.classList.toggle('collapsed');
      filterContent.classList.toggle('collapsed');

      // Toggle icon direction
      const icon = filterToggleBtn.querySelector('i');
      if (icon) {
        if (filterPanel.classList.contains('collapsed')) {
          icon.classList.remove('bx-chevron-left');
          icon.classList.add('bx-chevron-right');
        } else {
          icon.classList.remove('bx-chevron-right');
          icon.classList.add('bx-chevron-left');
        }
      }
    });
  }

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

  // Simple Academic Dropdowns
  const departmentSelect = document.getElementById('department-select-simple');
  const subjectSelect = document.getElementById('subject-select-simple');

  // Department dropdown functionality
  if (departmentSelect) {
    departmentSelect.addEventListener('change', (e) => {
      const selectedDept = e.target.value;
      // Update subject dropdown based on selected department
      updateSimpleSubjectDropdown(selectedDept);
      // Apply filters
      applyFilters();
    });
  }

  // Subject dropdown functionality
  if (subjectSelect) {
    subjectSelect.addEventListener('change', (e) => {
      // Apply filters
      applyFilters();
    });
  }

  // Event type filters - modern chip style
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

  // Status filters (without pending)
  document.querySelectorAll('.status-filter').forEach(checkbox => {
    checkbox.addEventListener('change', applyFilters);
  });

  // Clear filters
  document.getElementById('clear-filters').addEventListener('click', clearAllFilters);
}

// Update simple subject dropdown based on selected department
function updateSimpleSubjectDropdown(department) {
  const subjectSelect = document.getElementById('subject-select-simple');
  if (!subjectSelect) return;

  // Clear existing options
  subjectSelect.innerHTML = '<option value="">All Subjects</option>';

  if (department && subjectTree && subjectTree[department]) {
    const allSubjects = [];

    // Collect all subjects from all categories
    Object.values(subjectTree[department]).forEach(categorySubjects => {
      allSubjects.push(...categorySubjects);
    });

    // Add subjects to dropdown
    allSubjects.sort().forEach(subject => {
      const option = document.createElement('option');
      option.value = subject;
      option.textContent = subject;
      subjectSelect.appendChild(option);
    });

    // Enable subject dropdown
    subjectSelect.disabled = false;
  } else {
    // Disable subject dropdown if no department selected
    subjectSelect.disabled = true;
  }
}

// Apply all filters
function applyFilters() {
  const searchTerm = document.getElementById('student-search').value.toLowerCase();
  const dateFrom = document.getElementById('date-from').value;
  const dateTo = document.getElementById('date-to').value;

  const selectedDepartment = document.getElementById('department-select-simple')?.value || '';
  const selectedSubject = document.getElementById('subject-select-simple')?.value || '';
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

    // Department filter
    if (selectedDepartment && selectedDepartment !== "") {
      if (event.department !== selectedDepartment) return false;
    }

    // Subject filter
    if (selectedSubject && selectedSubject !== "") {
      if (event.examName !== selectedSubject) return false;
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

  // Reset department dropdown
  const departmentSelect = document.getElementById('department-select-simple');
  if (departmentSelect) {
    departmentSelect.value = '';
  }

  // Reset subject dropdown
  const subjectSelect = document.getElementById('subject-select-simple');
  if (subjectSelect) {
    subjectSelect.value = '';
    subjectSelect.disabled = true;
    subjectSelect.innerHTML = '<option value="">All Subjects</option>';
  }

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

// Retention countdown helper
function getRetentionCountdown(deletionDate) {
  if (!deletionDate) return 'No deletion date';

  const now = new Date();
  const timeRemaining = deletionDate - now; // milliseconds

  // If already expired
  if (timeRemaining <= 0) {
    return 'Expired - pending deletion';
  }

  const seconds = Math.floor(timeRemaining / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  // Format based on time remaining
  if (days >= 2) {
    return `${days} days left`;
  } else if (days === 1) {
    return `1 day left`;
  } else if (hours >= 1) {
    return `${hours} hours left`;
  } else if (minutes >= 1) {
    return `${minutes} minutes left`;
  } else {
    return '< 1 minute left';
  }
}

// Get retention icon based on urgency
function getRetentionIcon(deletionDate) {
  if (!deletionDate) return { icon: 'bx-time-five', class: 'retention-safe' };

  const now = new Date();
  const timeRemaining = deletionDate - now;
  const daysRemaining = timeRemaining / (1000 * 60 * 60 * 24);

  if (daysRemaining < 0) {
    return { icon: 'bx-alarm-exclamation', class: 'retention-expired' };
  } else if (daysRemaining < 1) {
    return { icon: 'bx-alarm', class: 'retention-urgent' };
  } else if (daysRemaining < 3) {
    return { icon: 'bx-stopwatch', class: 'retention-warning' };
  } else {
    return { icon: 'bx-time-five', class: 'retention-safe' };
  }
}

// Time ago helper (kept for modal/other uses)
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
  console.log('Setting up modal listeners...');

  const modal = document.getElementById('event-detail-modal');
  const overlay = document.getElementById('modal-overlay');
  const closeBtn = document.getElementById('modal-close-btn');

  console.log('Modal elements:', { modal: !!modal, overlay: !!overlay, closeBtn: !!closeBtn });

  // Setup overlay click
  if (overlay) {
    overlay.removeEventListener('click', closeEventDetailModal);
    overlay.addEventListener('click', closeEventDetailModal);
    console.log('Overlay listener added');
  }

  // Setup close button click - multiple approaches
  if (closeBtn) {
    // Remove any existing listeners
    closeBtn.removeEventListener('click', closeEventDetailModal);

    // Add new listener with proper event handling
    closeBtn.addEventListener('click', function (e) {
      console.log('Close button clicked');
      e.preventDefault();
      e.stopPropagation();
      closeEventDetailModal();
    });

    // Also add listener to the icon inside
    const icon = closeBtn.querySelector('.bx-x');
    if (icon) {
      icon.removeEventListener('click', closeEventDetailModal);
      icon.addEventListener('click', function (e) {
        console.log('X icon clicked');
        e.preventDefault();
        e.stopPropagation();
        closeEventDetailModal();
      });
    }

    console.log('Close button listeners added');
  }

  // Global fallback for any bx-x in modal
  document.removeEventListener('click', handleModalCloseClick);
  document.addEventListener('click', handleModalCloseClick);

  console.log('Global fallback listener added');

  // Setup other modal buttons
  setupModalActionButtons();

  // Close on ESC key
  document.removeEventListener('keydown', handleModalEscKey);
  document.addEventListener('keydown', handleModalEscKey);

  console.log('Modal listeners setup complete');
}

// Helper function for global click handling
function handleModalCloseClick(e) {
  // Check if click is on bx-x icon or close button within the modal
  if (e.target.classList.contains('bx-x') || e.target.classList.contains('modal-close-btn')) {
    const modal = e.target.closest('#event-detail-modal');
    if (modal) {
      console.log('Global close handler triggered');
      e.preventDefault();
      e.stopPropagation();
      closeEventDetailModal();
    }
  }
}

// Helper function for ESC key handling
function handleModalEscKey(e) {
  const modal = document.getElementById('event-detail-modal');
  if (e.key === 'Escape' && modal && !modal.classList.contains('hidden')) {
    console.log('ESC key pressed to close modal');
    e.preventDefault();
    closeEventDetailModal();
  }
}

// Setup modal action buttons
function setupModalActionButtons() {
  const saveNotesBtn = document.getElementById('save-notes-btn');
  if (saveNotesBtn) {
    saveNotesBtn.addEventListener('click', () => {
      const modal = document.getElementById('event-detail-modal');
      const cardId = modal.dataset.currentCardId;
      const notes = document.getElementById('modal-notes').value;
      updateCardOnBackend(cardId, null, notes);
    });
  }

  const exportBtn = document.getElementById('export-evidence-btn');
  if (exportBtn) {
    exportBtn.addEventListener('click', () => {
      const modal = document.getElementById('event-detail-modal');
      const cardId = modal.dataset.currentCardId;
      exportEventToPDF(cardId);
    });
  }
}

function openEventDetailModal(eventId) {
  const event = allEvents.find(e => e.id === eventId);
  if (!event) return;

  const modal = document.getElementById('event-detail-modal');

  // Store card ID for evidence gallery
  modal.dataset.currentCardId = event.id;

  // Store card ID for evidence gallery
  modal.dataset.currentCardId = event.id;

  // Populate modal header
  document.getElementById('modal-student-photo').src = event.studentPhoto;
  document.getElementById('modal-student-name').textContent = event.studentName;
  document.getElementById('modal-student-id').textContent = `ID: ${event.studentId}`;
  document.getElementById('modal-exam-name').textContent = event.examName;

  // Populate event summary
  document.getElementById('modal-total-events').textContent = event.totalEvents;
  document.getElementById('modal-highest-severity').innerHTML = `<span class="severity-badge severity-${event.highestSeverity}">${event.highestSeverity}</span>`;

  const deptEl = document.getElementById('modal-department');
  const examFullEl = document.getElementById('modal-exam-full-name');
  if (deptEl) deptEl.textContent = event.department || 'N/A';
  if (examFullEl) examFullEl.textContent = event.examFullName || 'N/A';

  document.getElementById('modal-last-event').textContent = formatTimestamp(event.lastEventTime);

  // Status with color coding
  const statusEl = document.getElementById('modal-status');
  const statusColors = {
    'pending': 'color: #FFA500;',      // Orange
    'confirmed': 'color: #FF4444;',    // Red
    'declined': 'color: #4CAF50;'      // Green
  };
  statusEl.innerHTML = `<span style="${statusColors[event.status] || ''}">${event.status.toUpperCase()}</span>`;

  // Populate notes
  document.getElementById('modal-notes').value = event.notes || '';

  // Show status action buttons
  const actionsRow = document.getElementById('modal-status-actions');
  actionsRow.innerHTML = `
    <button class="btn-confirm-event ${event.status === 'confirmed' ? 'active' : ''}" onclick="confirmEvent('${event.id}')">
      <i class='bx bx-check-circle'></i>
      ${event.status === 'confirmed' ? 'Confirmed Cheating' : 'Confirm Cheating'}
    </button>
    <button class="btn-decline-event ${event.status === 'declined' ? 'active' : ''}" onclick="declineEvent('${event.id}')">
      <i class='bx bx-x-circle'></i>
      ${event.status === 'declined' ? 'Declined (False Positive)' : 'Decline Event'}
    </button>
  `;
  actionsRow.style.display = 'flex';

  // Populate event timeline
  renderEventTimeline(event.events);

  // Populate evidence gallery
  renderEvidenceGallery(event.events);

  // Show modal
  modal.classList.remove('hidden');
  document.body.style.overflow = 'hidden';
}

function closeEventDetailModal() {
  console.log('closeEventDetailModal called');
  const modal = document.getElementById('event-detail-modal');

  if (modal) {
    console.log('Modal found, current classes:', modal.className);
    modal.classList.add('hidden');
    document.body.style.overflow = '';
    console.log('Modal closed, new classes:', modal.className);

    // Verify it's actually hidden
    setTimeout(() => {
      if (modal.classList.contains('hidden')) {
        console.log('Modal successfully hidden');
      } else {
        console.error('Modal failed to hide');
      }
    }, 50);
  } else {
    console.error('Modal element not found in DOM');
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
                ${event.notes ? `<p class="timeline-notes"><strong>Note:</strong> ${event.notes}</p>` : ''}
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
async function confirmEvent(cardId) {
  const event = allEvents.find(e => e.id === cardId);
  if (event) {
    const success = await updateCardOnBackend(cardId, 'confirmed', null);
    if (success) {
      event.status = 'confirmed';
      // Refresh the modal to update status
      openEventDetailModal(cardId);
    }
  }
}

// Decline event function
async function declineEvent(cardId) {
  const event = allEvents.find(e => e.id === cardId);
  if (event) {
    const success = await updateCardOnBackend(cardId, 'declined', null);
    if (success) {
      event.status = 'declined';
      // Refresh the modal to update status
      openEventDetailModal(cardId);
    }
  }
}

async function updateCardOnBackend(cardId, status, notes) {
  try {
    const payload = { card_id: cardId };
    if (status) payload.status = status;
    if (notes !== null) payload.notes = notes;

    const response = await fetch('/api/history/update_card', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });

    const data = await response.json();
    if (data.success) {
      // Update local data
      const event = allEvents.find(e => e.id === cardId);
      if (event) {
        if (status) event.status = status;
        if (notes !== null) event.notes = notes;
      }

      // Re-render cards to show updated status/notes
      renderEventCards();

      // Show success notification (if available)
      console.log('Card updated successfully');
      return true;
    } else {
      alert('Error updating card: ' + data.error);
      return false;
    }
  } catch (error) {
    console.error('Error updating card:', error);
    alert('Failed to connect to server');
    return false;
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

// ============================================
// PDF EXPORT FUNCTIONALITY
// ============================================

// Helper function to load image as base64
async function loadImageAsBase64(url) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = 'Anonymous';

    img.onload = function () {
      const canvas = document.createElement('canvas');
      canvas.width = img.width;
      canvas.height = img.height;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(img, 0, 0);
      const dataURL = canvas.toDataURL('image/jpeg', 0.8);
      resolve(dataURL);
    };

    img.onerror = function () {
      console.warn(`Failed to load image: ${url}`);
      resolve(null);
    };

    img.src = url;
  });
}

async function exportEventToPDF(cardId) {
  const event = allEvents.find(e => e.id === cardId);
  if (!event) {
    alert('Event data not found');
    return;
  }

  try {
    // Show loading indicator
    const exportBtn = document.getElementById('export-evidence-btn');
    const originalText = exportBtn.innerHTML;
    exportBtn.innerHTML = '<i class="bx bx-loader-alt bx-spin"></i> Generating PDF...';
    exportBtn.disabled = true;

    // Initialize jsPDF
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF('p', 'mm', 'a4');

    const pageWidth = doc.internal.pageSize.getWidth();
    const pageHeight = doc.internal.pageSize.getHeight();
    const margin = 15;
    let yPos = margin;

    // Color palette
    const colors = {
      primary: [13, 110, 253],
      secondary: [108, 117, 125],
      success: [76, 175, 80],
      warning: [255, 165, 0],
      danger: [255, 68, 68],
      light: [248, 249, 250],
      dark: [33, 37, 41],
      border: [222, 226, 230]
    };

    // Helper function to add new page if needed
    const checkPageBreak = (requiredSpace) => {
      if (yPos + requiredSpace > pageHeight - margin - 15) {
        addPageFooter();
        doc.addPage();
        yPos = margin;
        return true;
      }
      return false;
    };

    // Add page footer
    const addPageFooter = () => {
      const pageNum = doc.internal.getCurrentPageInfo().pageNumber;
      doc.setFontSize(8);
      doc.setTextColor(...colors.secondary);
      doc.text(
        `Page ${pageNum}`,
        pageWidth / 2,
        pageHeight - 8,
        { align: 'center' }
      );
      doc.text(
        'Smart Invigilator - Exam Cheat Detection System',
        margin,
        pageHeight - 8
      );
      doc.text(
        new Date().toLocaleDateString(),
        pageWidth - margin,
        pageHeight - 8,
        { align: 'right' }
      );
    };

    // Professional Header with gradient effect
    doc.setFillColor(...colors.primary);
    doc.rect(0, 0, pageWidth, 50, 'F');

    // Add subtle pattern overlay
    doc.setFillColor(255, 255, 255);
    doc.setGState(new doc.GState({ opacity: 0.1 }));
    for (let i = 0; i < pageWidth; i += 10) {
      doc.circle(i, 10, 3, 'F');
      doc.circle(i + 5, 30, 2, 'F');
    }
    doc.setGState(new doc.GState({ opacity: 1 }));

    // Header text
    doc.setTextColor(255, 255, 255);
    doc.setFontSize(28);
    doc.setFont('helvetica', 'bold');
    doc.text('EXAM MONITORING REPORT', pageWidth / 2, 22, { align: 'center' });

    doc.setFontSize(11);
    doc.setFont('helvetica', 'normal');
    doc.text('Automated Cheat Detection Analysis', pageWidth / 2, 32, { align: 'center' });

    doc.setFontSize(9);
    doc.text(`Report Generated: ${new Date().toLocaleString()}`, pageWidth / 2, 42, { align: 'center' });

    yPos = 60;

    // === STUDENT INFORMATION SECTION ===
    doc.setFillColor(...colors.light);
    doc.rect(margin, yPos - 5, pageWidth - 2 * margin, 40, 'F');

    doc.setTextColor(...colors.dark);
    doc.setFontSize(14);
    doc.setFont('helvetica', 'bold');
    doc.text('STUDENT INFORMATION', margin + 5, yPos + 2);

    // Divider line
    doc.setDrawColor(...colors.primary);
    doc.setLineWidth(0.5);
    doc.line(margin + 5, yPos + 5, pageWidth - margin - 5, yPos + 5);

    yPos += 12;

    // Student details in two columns
    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');
    const col1X = margin + 8;
    const col2X = pageWidth / 2 + 5;

    doc.setFont('helvetica', 'bold');
    doc.text('Full Name:', col1X, yPos);
    doc.setFont('helvetica', 'normal');
    doc.text(event.studentName, col1X + 25, yPos);

    doc.setFont('helvetica', 'bold');
    doc.text('Student ID:', col2X, yPos);
    doc.setFont('helvetica', 'normal');
    doc.text(event.studentId, col2X + 25, yPos);
    yPos += 7;

    doc.setFont('helvetica', 'bold');
    doc.text('Exam Name:', col1X, yPos);
    doc.setFont('helvetica', 'normal');
    doc.text(event.examName, col1X + 25, yPos);

    doc.setFont('helvetica', 'bold');
    doc.text('Session ID:', col2X, yPos);
    doc.setFont('helvetica', 'normal');
    doc.text(event.sessionId || 'N/A', col2X + 25, yPos);
    yPos += 7;

    doc.setFont('helvetica', 'bold');
    doc.text('Report Date:', col1X, yPos);
    doc.setFont('helvetica', 'normal');
    doc.text(formatTimestamp(event.lastEventTime), col1X + 25, yPos);

    doc.setFont('helvetica', 'bold');
    doc.text('Status:', col2X, yPos);
    doc.setFont('helvetica', 'normal');
    const statusColor = event.status === 'confirmed' ? colors.danger :
      event.status === 'declined' ? colors.success : colors.warning;
    doc.setTextColor(...statusColor);
    doc.text(event.status.toUpperCase(), col2X + 25, yPos);
    doc.setTextColor(...colors.dark);

    yPos += 18;

    // === SUMMARY STATISTICS TABLE ===
    checkPageBreak(50);

    doc.setTextColor(...colors.dark);
    doc.setFontSize(14);
    doc.setFont('helvetica', 'bold');
    doc.text('DETECTION SUMMARY', margin, yPos);
    yPos += 8;

    // Create statistics boxes
    const boxWidth = (pageWidth - 2 * margin - 10) / 3;
    const boxHeight = 25;
    const boxY = yPos;

    // Box 1: Total Events
    doc.setFillColor(...colors.primary);
    doc.roundedRect(margin, boxY, boxWidth, boxHeight, 2, 2, 'F');
    doc.setTextColor(255, 255, 255);
    doc.setFontSize(24);
    doc.setFont('helvetica', 'bold');
    doc.text(event.totalEvents.toString(), margin + boxWidth / 2, boxY + 12, { align: 'center' });
    doc.setFontSize(9);
    doc.setFont('helvetica', 'normal');
    doc.text('Total Events', margin + boxWidth / 2, boxY + 20, { align: 'center' });

    // Box 2: Highest Severity
    const severityColor = event.highestSeverity === 'high' ? colors.danger :
      event.highestSeverity === 'medium' ? colors.warning : colors.success;
    doc.setFillColor(...severityColor);
    doc.roundedRect(margin + boxWidth + 5, boxY, boxWidth, boxHeight, 2, 2, 'F');
    doc.setFontSize(12);
    doc.setFont('helvetica', 'bold');
    doc.text(event.highestSeverity.toUpperCase(), margin + boxWidth + 5 + boxWidth / 2, boxY + 12, { align: 'center' });
    doc.setFontSize(9);
    doc.setFont('helvetica', 'normal');
    doc.text('Severity Level', margin + boxWidth + 5 + boxWidth / 2, boxY + 20, { align: 'center' });

    // Box 3: Review Status
    const statusBoxColor = event.status === 'confirmed' ? colors.danger :
      event.status === 'declined' ? colors.success : colors.warning;
    doc.setFillColor(...statusBoxColor);
    doc.roundedRect(margin + 2 * boxWidth + 10, boxY, boxWidth, boxHeight, 2, 2, 'F');
    doc.setFontSize(12);
    doc.setFont('helvetica', 'bold');
    doc.text(event.status.toUpperCase(), margin + 2 * boxWidth + 10 + boxWidth / 2, boxY + 12, { align: 'center' });
    doc.setFontSize(9);
    doc.setFont('helvetica', 'normal');
    doc.text('Review Status', margin + 2 * boxWidth + 10 + boxWidth / 2, boxY + 20, { align: 'center' });

    yPos += boxHeight + 15;

    // === PROCTOR NOTES SECTION ===
    if (event.notes && event.notes.trim()) {
      checkPageBreak(40);

      doc.setFillColor(255, 252, 230);
      const notesHeight = 5 + Math.ceil(event.notes.length / 80) * 5;
      doc.roundedRect(margin, yPos - 3, pageWidth - 2 * margin, notesHeight + 15, 2, 2, 'F');

      doc.setTextColor(...colors.dark);
      doc.setFontSize(12);
      doc.setFont('helvetica', 'bold');
      doc.text('📝 Proctor Notes', margin + 5, yPos + 3);

      yPos += 10;
      doc.setFontSize(9);
      doc.setFont('helvetica', 'normal');
      const notesLines = doc.splitTextToSize(event.notes, pageWidth - 2 * margin - 10);
      notesLines.forEach(line => {
        doc.text(line, margin + 5, yPos);
        yPos += 5;
      });
      yPos += 10;
    }

    // === EVENT TIMELINE SECTION ===
    checkPageBreak(40);

    doc.setTextColor(...colors.dark);
    doc.setFontSize(14);
    doc.setFont('helvetica', 'bold');
    doc.text('DETAILED EVENT TIMELINE', margin, yPos);
    yPos += 10;

    // Sort events by timestamp
    const sortedEvents = [...event.events].sort((a, b) => a.timestamp - b.timestamp);

    for (let i = 0; i < sortedEvents.length; i++) {
      const evt = sortedEvents[i];
      checkPageBreak(60);

      // Event card background
      const cardHeight = 45;
      doc.setFillColor(250, 250, 250);
      doc.roundedRect(margin, yPos - 3, pageWidth - 2 * margin, cardHeight, 2, 2, 'F');

      // Event number badge
      const badgeColor = evt.severity === 'high' ? colors.danger :
        evt.severity === 'medium' ? colors.warning : colors.success;
      doc.setFillColor(...badgeColor);
      doc.circle(margin + 8, yPos + 3, 5, 'F');
      doc.setTextColor(255, 255, 255);
      doc.setFontSize(10);
      doc.setFont('helvetica', 'bold');
      doc.text((i + 1).toString(), margin + 8, yPos + 4.5, { align: 'center' });

      // Event header
      doc.setTextColor(...colors.dark);
      doc.setFontSize(11);
      doc.setFont('helvetica', 'bold');
      doc.text(evt.typeLabel, margin + 18, yPos + 4);

      // Timestamp
      doc.setFontSize(8);
      doc.setFont('helvetica', 'normal');
      doc.setTextColor(...colors.secondary);
      doc.text(formatTimestamp(evt.timestamp), pageWidth - margin - 5, yPos + 4, { align: 'right' });

      yPos += 10;

      // Event details
      doc.setFontSize(9);
      doc.setTextColor(...colors.dark);

      doc.setFont('helvetica', 'bold');
      doc.text('Confidence:', margin + 18, yPos);
      doc.setFont('helvetica', 'normal');
      doc.text(`${(evt.confidence * 100).toFixed(0)}%`, margin + 40, yPos);

      doc.setFont('helvetica', 'bold');
      doc.text('Severity:', margin + 70, yPos);
      doc.setFont('helvetica', 'normal');
      doc.setTextColor(...badgeColor);
      doc.text(evt.severity.toUpperCase(), margin + 90, yPos);
      doc.setTextColor(...colors.dark);

      if (evt.suspicionScore !== undefined) {
        doc.setFont('helvetica', 'bold');
        doc.text('Score:', margin + 120, yPos);
        doc.setFont('helvetica', 'normal');
        doc.text(evt.suspicionScore.toString(), margin + 135, yPos);
      }

      yPos += 6;

      // Reasons
      if (evt.reasons && evt.reasons.length > 0) {
        doc.setFont('helvetica', 'bold');
        doc.text('Detection Reasons:', margin + 18, yPos);
        yPos += 5;
        doc.setFont('helvetica', 'italic');
        doc.setFontSize(8);
        const reasonsText = evt.reasons.join(', ');
        const reasonsLines = doc.splitTextToSize(reasonsText, pageWidth - 2 * margin - 25);
        reasonsLines.forEach(line => {
          doc.text(line, margin + 18, yPos);
          yPos += 4;
        });
        yPos += 2;
      }

      yPos += cardHeight - 25;
    }

    yPos += 5;

    // === EVIDENCE GALLERY SECTION ===
    checkPageBreak(40);

    doc.setTextColor(...colors.dark);
    doc.setFontSize(14);
    doc.setFont('helvetica', 'bold');
    doc.text('EVIDENCE GALLERY', margin, yPos);
    yPos += 10;

    // Load and add actual images
    const modal = document.getElementById('event-detail-modal');
    const currentEventCardId = modal.dataset.currentCardId;

    let imagesAdded = 0;
    const imagesPerRow = 2;
    const imageWidth = (pageWidth - 2 * margin - 10) / 2;
    const imageHeight = imageWidth * 0.75;
    let currentRow = 0;

    for (let i = 0; i < sortedEvents.length && imagesAdded < 8; i++) {
      const evt = sortedEvents[i];
      const evidence = evt.evidence || {};

      if (evidence.crop) {
        checkPageBreak(imageHeight + 25);

        const col = imagesAdded % imagesPerRow;
        const xPos = margin + col * (imageWidth + 10);

        if (col === 0 && imagesAdded > 0) {
          yPos += 10;
        }

        try {
          const imgUrl = `/api/evidence/${currentEventCardId}/${evidence.crop}`;
          const base64Image = await loadImageAsBase64(imgUrl);

          if (base64Image) {
            // Add border
            doc.setDrawColor(...colors.border);
            doc.setLineWidth(0.3);
            doc.roundedRect(xPos, yPos, imageWidth, imageHeight, 2, 2, 'S');

            // Add image
            doc.addImage(base64Image, 'JPEG', xPos + 1, yPos + 1, imageWidth - 2, imageHeight - 2);

            // Add caption
            doc.setFontSize(8);
            doc.setFont('helvetica', 'italic');
            doc.setTextColor(...colors.secondary);
            const caption = `Event ${i + 1}: ${evt.typeLabel}`;
            doc.text(caption, xPos + imageWidth / 2, yPos + imageHeight + 5, { align: 'center' });

            imagesAdded++;

            if (col === imagesPerRow - 1) {
              yPos += imageHeight + 15;
            }
          }
        } catch (err) {
          console.warn('Could not load evidence image:', err);
        }
      }
    }

    // If odd number of images, advance position
    if (imagesAdded % imagesPerRow !== 0) {
      yPos += imageHeight + 15;
    }

    // Add footer to last page
    addPageFooter();

    // === FINAL PAGE NUMBERING ===
    const totalPages = doc.internal.getNumberOfPages();
    for (let i = 1; i <= totalPages; i++) {
      doc.setPage(i);
      doc.setFontSize(8);
      doc.setTextColor(...colors.secondary);
      const pageText = doc.getTextDimensions(`Page ${i}`);
      doc.text(
        ` of ${totalPages}`,
        pageWidth / 2 + pageText.w / 2,
        pageHeight - 8
      );
    }

    // Save the PDF with proper extension
    const fileName = `Exam_Report_${event.studentId}_${event.id}_${new Date().toISOString().split('T')[0]}.pdf`;

    // Use blob method for better browser compatibility
    const pdfBlob = doc.output('blob');
    const url = URL.createObjectURL(pdfBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = fileName;
    link.style.display = 'none';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    // Restore button
    exportBtn.innerHTML = originalText;
    exportBtn.disabled = false;

    console.log('PDF exported successfully:', fileName);
  } catch (error) {
    console.error('Error generating PDF:', error);
    alert('Error generating PDF report. Please try again.');

    // Restore button
    const exportBtn = document.getElementById('export-evidence-btn');
    exportBtn.innerHTML = '<i class="bx bx-download"></i> Export Evidence';
    exportBtn.disabled = false;
  }
}
