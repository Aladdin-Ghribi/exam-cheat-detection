import React, { useEffect } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { fetchEventLog, fetchSeatAssignments } from '../store/appSlice';

function InstructorView() {
  const dispatch = useDispatch();
  const { detectionData, loading } = useSelector(state => state.app);

  useEffect(() => {
    dispatch(fetchEventLog());
    dispatch(fetchSeatAssignments());
    
    const interval = setInterval(() => {
      dispatch(fetchEventLog());
      dispatch(fetchSeatAssignments());
    }, 5000);
    
    return () => clearInterval(interval);
  }, [dispatch]);
  const renderSeatMap = () => {
    if (loading.seatAssignments) {
      return <div className="loading" role="status" aria-live="polite">Loading seat assignments...</div>;
    }
    
    const seats = [];
    for (let i = 1; i <= 20; i++) {
      const assignedStudent = Object.entries(detectionData.seat_assignments || {})
        .find(([studentId, seatId]) => parseInt(seatId) === i);
      
      let status = 'empty';
      let studentId = null;
      let score = 0;
      
      if (assignedStudent) {
        studentId = assignedStudent[0];
        const detection = detectionData.detections?.find(d => d.track_id == studentId);
        if (detection?.behavior?.suspicion) {
          score = Math.round(detection.behavior.suspicion.smoothed * 100);
          status = score >= 20 ? 'flagged' : 'active';
        } else {
          status = 'active';
        }
      }
      
      seats.push(
        <div 
          key={i} 
          className={`seat ${status}`}
          role="gridcell"
          tabIndex="0"
          aria-label={`Seat ${i}: ${status === 'empty' ? 'Empty' : `Student ${studentId}, ${status === 'flagged' ? `flagged with score ${score}` : 'active'}`}`}
        >
          <div className="seat-id" aria-hidden="true">Seat {i}</div>
          <div className="seat-status" aria-hidden="true">
            {status === 'empty' ? 'Empty' : `Student ${studentId}`}
          </div>
          {status === 'flagged' && (
            <div className="suspicion-score" style={{ color: '#e74c3c' }} aria-label={`Suspicion score: ${score} out of 100`}>
              {score}/100
            </div>
          )}
        </div>
      );
    }
    return seats;
  };

  const renderAlerts = () => {
    const alerts = [];
    detectionData.detections?.forEach(detection => {
      if (detection.behavior?.suspicion) {
        const score = Math.round(detection.behavior.suspicion.smoothed * 100);
        if (score >= 20) {
          const reasons = [];
          
          if (detection.behavior.head_orientation) {
            const ho = detection.behavior.head_orientation;
            if (Math.abs(ho.yaw) > 30) {
              reasons.push(`Head turned ${Math.abs(ho.yaw).toFixed(0)}°`);
            }
            if (Math.abs(ho.pitch) > 20) {
              reasons.push(`Head tilted ${Math.abs(ho.pitch).toFixed(0)}°`);
            }
          }
          
          if (detection.behavior.hands) {
            ['left', 'right'].forEach(side => {
              const hand = detection.behavior.hands[side];
              if (hand?.visible) {
                if (hand.near_object && hand.object_class) {
                  reasons.push(`${side} hand near ${hand.object_class}`);
                } else if (hand.near_face) {
                  reasons.push(`${side} hand near face`);
                }
              }
            });
          }
          
          alerts.push({
            studentId: detection.track_id,
            score,
            reasons: reasons.length > 0 ? reasons : ['Suspicious behavior detected']
          });
        }
      }
    });
    
    return alerts;
  };

  const renderEventLog = () => {
    if (loading.eventLog) {
      return <p className="loading" role="status" aria-live="polite">Loading events...</p>;
    }
    
    if (!detectionData.event_log || detectionData.event_log.length === 0) {
      return <p className="no-events" role="status">No flagged incidents</p>;
    }
    
    return detectionData.event_log.slice().reverse().map((event, index) => (
      <div key={index} className={`event-item ${event.score >= 50 ? 'high-severity' : ''}`} role="listitem" aria-labelledby={`event-${index}`}>
        <div className="event-header">
          <span id={`event-${index}`} className="event-student">Student {event.student_id}</span>
          <div>
            <time className="event-timestamp" dateTime={event.timestamp}>{event.timestamp}</time>
            <span className="event-score" aria-label={`Severity score: ${event.score} out of 100`}>{event.score}/100</span>
          </div>
        </div>
        <div className="event-description" aria-label={`Incident details: ${event.description}`}>{event.description}</div>
      </div>
    ));
  };

  return (
    <main className="animate-fadeIn" style={{ padding: '20px', minHeight: 'calc(100vh - 80px)' }} role="main">
      <div style={{ display: 'flex', gap: '20px', height: 'calc(100vh - 120px)', flexWrap: 'wrap' }}>
        <section className="card animate-slideUp hover-lift" style={{ flex: 2, minWidth: '500px' }} aria-labelledby="seatmap-heading">
          <h2 id="seatmap-heading" style={{ margin: '0 0 1rem 0', color: '#2c3e50' }}>Seat Map</h2>
          <div className="seat-grid" role="grid" aria-label="Exam room seat assignments">
            {renderSeatMap()}
          </div>
        </div>
        
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {detectionData.annotated_frame && (
            <section className="card animate-slideUp hover-lift" style={{ maxHeight: '300px', marginBottom: '20px' }} aria-labelledby="livefeed-heading">
              <h3 id="livefeed-heading" style={{ margin: '0 0 1rem 0', color: '#2c3e50' }}>Live Feed</h3>
              <img 
                src={`data:image/jpeg;base64,${detectionData.annotated_frame}`}
                alt="Live video feed preview showing current detection results with annotations"
                style={{ width: '100%', height: 'auto', borderRadius: '4px' }}
              />
            </div>
          )}
          
          <section className="card animate-slideUp hover-lift" style={{ flex: 1, overflowY: 'auto', marginBottom: '20px' }} aria-labelledby="alerts-heading">
            <h2 id="alerts-heading" style={{ margin: '0 0 1rem 0', color: '#2c3e50' }}>Active Alerts</h2>
            <div className="alerts-list">
              {renderAlerts().length === 0 ? (
                <p className="no-alerts" role="status">No active alerts</p>
              ) : (
                renderAlerts().map((alert, index) => (
                  <div key={index} className="alert-item" role="alert" aria-labelledby={`alert-${index}`}>
                    <div className="alert-header">
                      <span id={`alert-${index}`} className="alert-student">Student {alert.studentId}</span>
                      <span className="alert-score" aria-label={`Suspicion score: ${alert.score} out of 100`}>{alert.score}/100</span>
                    </div>
                    <div className="alert-reason" aria-label={`Reasons: ${alert.reasons.join(', ')}`}>{alert.reasons.join(', ')}</div>
                  </div>
                ))
              )}
            </div>
          </div>
          
          <section className="card animate-slideUp hover-lift" style={{ flex: 1, overflowY: 'auto' }} aria-labelledby="eventlog-heading">
            <h2 id="eventlog-heading" style={{ margin: '0 0 1rem 0', color: '#2c3e50' }}>Event Log</h2>
            <div className="event-log">
              {renderEventLog()}
            </div>
          </div>
        </div>
      </div>
      
      <style jsx>{`
        .seat-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
          gap: 20px;
          padding: 20px 0;
        }
        
        .seat {
          background: linear-gradient(135deg, #ecf0f1, #d5dbdb);
          border: 2px solid #bdc3c7;
          border-radius: 12px;
          padding: 16px;
          text-align: center;
          transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
          box-shadow: 0 4px 12px rgba(0,0,0,0.1);
          position: relative;
          overflow: hidden;
        }
        
        .seat::before {
          content: '';
          position: absolute;
          top: 0;
          left: -100%;
          width: 100%;
          height: 100%;
          background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
          transition: left 0.6s;
        }
        
        .seat:hover::before {
          left: 100%;
        }
        
        .seat.active {
          background: linear-gradient(135deg, #d5f4e6, #a9dfbf);
          border-color: #27ae60;
          box-shadow: 0 6px 20px rgba(39, 174, 96, 0.2);
        }
        
        .seat.flagged {
          background: linear-gradient(135deg, #fadbd8, #f1948a);
          border-color: #e74c3c;
          animation: flaggedPulse 2s infinite;
          box-shadow: 0 6px 20px rgba(231, 76, 60, 0.3);
        }
        
        @keyframes flaggedPulse {
          0% { 
            box-shadow: 0 6px 20px rgba(231, 76, 60, 0.3), 0 0 0 0 rgba(231, 76, 60, 0.4); 
          }
          70% { 
            box-shadow: 0 6px 20px rgba(231, 76, 60, 0.3), 0 0 0 15px rgba(231, 76, 60, 0); 
          }
          100% { 
            box-shadow: 0 6px 20px rgba(231, 76, 60, 0.3), 0 0 0 0 rgba(231, 76, 60, 0); 
          }
        }
        
        .seat.empty {
          background: #f8f9fa;
          border-color: #dee2e6;
          opacity: 0.7;
        }
        
        @keyframes pulse {
          0% { box-shadow: 0 0 0 0 rgba(231, 76, 60, 0.4); }
          70% { box-shadow: 0 0 0 10px rgba(231, 76, 60, 0); }
          100% { box-shadow: 0 0 0 0 rgba(231, 76, 60, 0); }
        }
        
        .seat-id {
          font-weight: bold;
          font-size: 1.1rem;
          color: #2c3e50;
        }
        
        .seat-status {
          font-size: 0.8rem;
          margin-top: 5px;
          color: #7f8c8d;
        }
        
        .alert-item, .event-item {
          background: linear-gradient(135deg, #fff5f5, #ffeaea);
          border: 1px solid #fed7d7;
          border-left: 4px solid #e53e3e;
          border-radius: 12px;
          padding: 16px;
          margin-bottom: 12px;
          transition: all 0.3s ease;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .alert-item:hover, .event-item:hover {
          transform: translateX(4px);
          box-shadow: 0 4px 16px rgba(0,0,0,0.15);
        }
        
        .alert-header, .event-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 5px;
        }
        
        .alert-student, .event-student {
          font-weight: bold;
          color: #2d3748;
        }
        
        .alert-score, .event-score {
          background: #e53e3e;
          color: white;
          padding: 2px 8px;
          border-radius: 12px;
          font-size: 0.8rem;
        }
        
        .event-timestamp {
          color: #6c757d;
          font-size: 0.9rem;
          margin-right: 10px;
        }
        
        .alert-reason, .event-description {
          font-size: 0.9rem;
          color: #4a5568;
        }
        
        .no-alerts, .no-events {
          text-align: center;
          color: #a0aec0;
          font-style: italic;
          margin: 20px 0;
          padding: 2rem;
          background: linear-gradient(135deg, #f8f9fa, #e9ecef);
          border-radius: 12px;
          border: 2px dashed #dee2e6;
        }
        
        .loading {
          text-align: center;
          color: #6c757d;
          padding: 2rem;
          background: linear-gradient(135deg, #f8f9fa, #e9ecef);
          border-radius: 12px;
          margin: 20px 0;
        }
      `}</style>
    </div>
  );
}

export default InstructorView;