import { announceToScreenReader, trapFocus } from '../../utils/accessibility';

describe('Accessibility Utils', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
  });

  describe('announceToScreenReader', () => {
    test('creates announcement element with correct attributes', () => {
      announceToScreenReader('Test message');
      
      const announcement = document.querySelector('[aria-live]');
      expect(announcement).toBeInTheDocument();
      expect(announcement).toHaveAttribute('aria-live', 'polite');
      expect(announcement).toHaveAttribute('aria-atomic', 'true');
      expect(announcement).toHaveTextContent('Test message');
    });
  });

  describe('trapFocus', () => {
    test('focuses first focusable element', () => {
      document.body.innerHTML = `
        <div id="modal">
          <button id="first">First</button>
          <button id="second">Second</button>
        </div>
      `;
      
      const modal = document.getElementById('modal');
      const firstButton = document.getElementById('first');
      
      trapFocus(modal);
      
      expect(document.activeElement).toBe(firstButton);
    });
  });
});