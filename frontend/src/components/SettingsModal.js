import React, { useState, useEffect, useRef } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { updateSettings } from '../store/appSlice';
import { trapFocus, announceToScreenReader } from '../utils/accessibility';

function SettingsModal({ onClose }) {
  const dispatch = useDispatch();
  const { socket, settings } = useSelector(state => state.app);
  const modalRef = useRef(null);
  const [poseEnabled, setPoseEnabled] = useState(settings.poseEnabled || true);
  const [yawThreshold, setYawThreshold] = useState(30);
  const [pitchThreshold, setPitchThreshold] = useState(20);
  const [suspicionThreshold, setSuspicionThreshold] = useState(settings.suspicionThreshold * 100 || 20);
  const [modelSize, setModelSize] = useState(settings.performanceMode || 'medium');
  const [frameSkipping, setFrameSkipping] = useState(true);

  useEffect(() => {
    announceToScreenReader('Settings modal opened');
    const cleanup = trapFocus(modalRef.current);
    
    const handleEscape = (e) => {
      if (e.key === 'Escape') onClose();
    };
    
    document.addEventListener('keydown', handleEscape);
    
    return () => {
      cleanup();
      document.removeEventListener('keydown', handleEscape);
      announceToScreenReader('Settings modal closed');
    };
  }, [onClose]);

  const handleSuspicionChange = (value) => {
    setSuspicionThreshold(value);
    dispatch(updateSettings({ suspicionThreshold: value / 100 }));
    if (socket) {
      socket.emit('update_suspicion_threshold', { threshold: value });
    }
  };

  const handleModelChange = (size) => {
    setModelSize(size);
    dispatch(updateSettings({ performanceMode: size }));
    if (socket) {
      socket.emit('switch_model', { model_size: size });
    }
  };

  const handleFrameSkipToggle = (enabled) => {
    setFrameSkipping(enabled);
    if (socket) {
      socket.emit('toggle_frame_skipping', { enabled });
    }
  };

  return (
    <div 
      className="modal-overlay" 
      onClick={onClose} 
      role="dialog"
      aria-modal="true"
      aria-labelledby="settings-title"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(0, 0, 0, 0.6)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        backdropFilter: 'blur(5px)',
        animation: 'fadeIn 0.3s ease'
      }}>
      <div ref={modalRef} className="modal-content" onClick={e => e.stopPropagation()} style={{
        background: 'linear-gradient(135deg, #ffffff, #f8f9fa)',
        borderRadius: '20px',
        maxWidth: '600px',
        width: '90%',
        maxHeight: '80vh',
        overflowY: 'auto',
        boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
        border: '1px solid rgba(255, 255, 255, 0.2)',
        animation: 'slideIn 0.3s ease'
      }}>
        <div className="modal-header" style={{
          padding: '1.5rem 2rem',
          borderBottom: '1px solid #e9ecef',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: 'linear-gradient(135deg, #2c3e50, #34495e)',
          color: 'white',
          borderRadius: '20px 20px 0 0'
        }}>
          <h2 id="settings-title" style={{ margin: 0, fontSize: '1.5rem', fontWeight: '600' }}>Settings</h2>
          <button 
            onClick={onClose}
            aria-label="Close settings modal"
            style={{
              background: 'none',
              border: 'none',
              color: 'white',
              fontSize: '1.5rem',
              cursor: 'pointer',
              padding: '0.5rem',
              borderRadius: '50%',
              transition: 'all 0.3s ease'
            }}
            onMouseOver={e => e.target.style.background = 'rgba(255,255,255,0.2)'}
            onMouseOut={e => e.target.style.background = 'none'}
          >
            <span aria-hidden="true">×</span>
          </button>
        </div>
        
        <div style={{ padding: '2rem' }}>
          <fieldset className="settings-section" style={{ marginBottom: '2rem', border: 'none', padding: 0 }}>
            <legend style={{ color: '#2c3e50', marginBottom: '1rem', fontSize: '1.2rem', fontWeight: '600' }}>Pose Controls</legend>
            <button 
              className="btn"
              onClick={() => {
                const newValue = !poseEnabled;
                setPoseEnabled(newValue);
                dispatch(updateSettings({ poseEnabled: newValue }));
              }}
              aria-pressed={poseEnabled}
              aria-describedby="pose-desc"
              style={{ 
                background: poseEnabled ? '#4CAF50' : '#f44336',
                color: 'white'
              }}
            >
              {poseEnabled ? 'Hide Pose' : 'Show Pose'}
            </button>
            <div id="pose-desc" className="sr-only">Toggle pose detection overlay on video feed</div>
          </div>
          
          <fieldset className="settings-section" style={{ marginBottom: '2rem', border: 'none', padding: 0 }}>
            <legend style={{ color: '#2c3e50', marginBottom: '1rem', fontSize: '1.2rem', fontWeight: '600' }}>Scoring Thresholds</legend>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
              <div>
                <label htmlFor="yaw-threshold">Head Yaw Threshold: {yawThreshold}°</label>
                <input 
                  id="yaw-threshold"
                  type="range" 
                  min="15" 
                  max="60" 
                  step="5"
                  value={yawThreshold}
                  onChange={(e) => setYawThreshold(e.target.value)}
                  aria-describedby="yaw-desc"
                  style={{ 
                    width: '100%',
                    height: '6px',
                    borderRadius: '3px',
                    background: 'linear-gradient(to right, #3498db, #2980b9)',
                    outline: 'none',
                    cursor: 'pointer'
                  }}
                />
                <div id="yaw-desc" className="sr-only">Angle threshold for detecting head turning left or right</div>
              </div>
              <div>
                <label htmlFor="pitch-threshold">Head Pitch Threshold: {pitchThreshold}°</label>
                <input 
                  id="pitch-threshold"
                  type="range" 
                  min="10" 
                  max="40" 
                  step="5"
                  value={pitchThreshold}
                  onChange={(e) => setPitchThreshold(e.target.value)}
                  aria-describedby="pitch-desc"
                  style={{ width: '100%' }}
                />
                <div id="pitch-desc" className="sr-only">Angle threshold for detecting head tilting up or down</div>
              </div>
              <div style={{ gridColumn: 'span 2' }}>
                <label htmlFor="suspicion-threshold">Suspicion Threshold: {suspicionThreshold}</label>
                <input 
                  id="suspicion-threshold"
                  type="range" 
                  min="20" 
                  max="100" 
                  step="10"
                  value={suspicionThreshold}
                  onChange={(e) => handleSuspicionChange(e.target.value)}
                  aria-describedby="suspicion-desc"
                  style={{ width: '100%' }}
                />
                <div id="suspicion-desc" className="sr-only">Minimum score required to flag suspicious behavior</div>
              </div>
            </div>
          </div>
          
          <div className="settings-section" style={{ marginBottom: '2rem' }}>
            <h3 style={{ color: '#2c3e50', marginBottom: '1rem', fontSize: '1.2rem' }}>Performance Settings</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
              <div>
                <label>Model Size:</label>
                <select 
                  value={modelSize}
                  onChange={(e) => handleModelChange(e.target.value)}
                  style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
                >
                  <option value="nano">Nano (Fastest)</option>
                  <option value="small">Small (Fast)</option>
                  <option value="medium">Medium (Balanced)</option>
                </select>
              </div>
              <div>
                <label>
                  <input 
                    type="checkbox" 
                    checked={frameSkipping}
                    onChange={(e) => handleFrameSkipToggle(e.target.checked)}
                    style={{ marginRight: '5px' }}
                  />
                  Enable Frame Skipping
                </label>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default SettingsModal;