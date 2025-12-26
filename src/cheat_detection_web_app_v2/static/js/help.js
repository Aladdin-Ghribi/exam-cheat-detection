// Help Page JavaScript
// Handles tab switching and content display

(function () {
  'use strict';

  // Initialize help page when loaded
  function initHelpPage() {
    const helpTabs = document.querySelectorAll('.help-tab');
    const helpContents = document.querySelectorAll('.help-tab-content');

    console.log(`Found ${helpTabs.length} help tabs and ${helpContents.length} content sections`);

    if (helpTabs.length === 0) {
      console.warn('No help tabs found. Retrying in 1 second...');
      setTimeout(initHelpPage, 1000);
      return;
    }

    // Tab switching functionality
    helpTabs.forEach(tab => {
      tab.addEventListener('click', () => {
        const targetTab = tab.dataset.tab;
        console.log(`Switching to help tab: ${targetTab}`);

        // Remove active class from all tabs
        helpTabs.forEach(t => t.classList.remove('active'));
        // Add active class to clicked tab
        tab.classList.add('active');

        // Hide all content
        helpContents.forEach(content => content.classList.remove('active'));
        // Show targeted content
        const targetContent = document.getElementById(targetTab);
        if (targetContent) {
          targetContent.classList.add('active');
          console.log(`Shown content section: ${targetTab}`);

          // Scroll to top of content smoothly
          targetContent.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        } else {
          console.error(`Could not find content section with id: ${targetTab}`);
        }
      });
    });

    console.log('Help page initialized');
  }

  // Initialize when page loads
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initHelpPage);
  } else {
    initHelpPage();
  }
})();
