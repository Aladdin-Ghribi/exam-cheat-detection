import React from 'react';
import { Link, useLocation } from 'react-router-dom';

const Header = React.memo(function Header({ onSettingsClick }) {
  const location = useLocation();
  const isInstructor = location.pathname === '/instructor';
  
  return (
    <header className="header" role="banner">
      <h1 id="app-title">Exam Cheat Detection</h1>
      <nav className="header-buttons" role="navigation" aria-label="Main navigation">
        <button 
          className="btn btn-settings" 
          onClick={onSettingsClick}
          aria-label="Open settings modal"
          type="button"
        >
          <span aria-hidden="true">⚙️</span> Settings
        </button>
        <Link 
          to={isInstructor ? '/' : '/instructor'}
          className="btn btn-instructor"
          aria-label={isInstructor ? 'Go to Dashboard' : 'Go to Instructor View'}
        >
          <span aria-hidden="true">{isInstructor ? '🏠' : '📊'}</span> 
          {isInstructor ? 'Dashboard' : 'Instructor View'}
        </Link>
      </nav>
    </header>
  );
}

});

export default Header;