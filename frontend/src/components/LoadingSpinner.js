import React from 'react';

function LoadingSpinner({ size = 'medium', text = 'Loading...' }) {
  const sizeMap = {
    small: '20px',
    medium: '40px',
    large: '60px'
  };

  return (
    <div className="loading-container" style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '2rem',
      gap: '1rem'
    }}>
      <div 
        className="spinner"
        style={{
          width: sizeMap[size],
          height: sizeMap[size],
          border: '3px solid #ecf0f1',
          borderTop: '3px solid #3498db',
          borderRadius: '50%',
          animation: 'spin 1s linear infinite'
        }}
      />
      <span style={{ color: '#7f8c8d', fontSize: '0.9rem' }}>{text}</span>
    </div>
  );
}

export default LoadingSpinner;