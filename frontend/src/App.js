import React, { useEffect, Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route, useLocation } from 'react-router-dom';
import { Provider, useDispatch, useSelector } from 'react-redux';
import io from 'socket.io-client';
import { store } from './store/store';
import { setSocket, setConnected, updateDetectionData, toggleSettings } from './store/appSlice';
import Header from './components/Header';
import LoadingSpinner from './components/LoadingSpinner';
import './App.css';
import './styles/animations.css';

// Lazy load components for code splitting
const Dashboard = lazy(() => import('./components/Dashboard'));
const InstructorView = lazy(() => import('./components/InstructorView'));
const SettingsModal = lazy(() => import('./components/SettingsModal'));

function AppContent() {
  const dispatch = useDispatch();
  const location = useLocation();
  const { showSettings } = useSelector(state => state.app);

  // Update document title based on route
  useEffect(() => {
    const titles = {
      '/': 'Dashboard - Exam Monitoring System',
      '/instructor': 'Instructor View - Exam Monitoring System'
    };
    document.title = titles[location.pathname] || 'Exam Monitoring System';
  }, [location.pathname]);

  useEffect(() => {
    const socketUrl = process.env.REACT_APP_SOCKET_URL || window.location.origin;
    const newSocket = io(socketUrl);
    dispatch(setSocket(newSocket));

    newSocket.on('connect', () => {
      dispatch(setConnected(true));
    });

    newSocket.on('disconnect', () => {
      dispatch(setConnected(false));
    });

    newSocket.on('processed_frame', (data) => {
      dispatch(updateDetectionData({
        detections: data.detections,
        seat_assignments: data.seat_assignments,
        annotated_frame: data.annotated_frame,
        metrics: data.metrics
      }));
    });

    fetch('/api/current_data')
      .then(res => res.json())
      .then(data => {
        dispatch(updateDetectionData(data));
      })
      .catch(() => {});

    return () => newSocket.close();
  }, [dispatch]);

  return (
    <Router>
      <div className="app">
        <a href="#main-content" className="skip-link">Skip to main content</a>
        <Header 
          onSettingsClick={() => dispatch(toggleSettings())}
        />
        
        <div id="main-content">
          <Suspense fallback={<LoadingSpinner size="large" text="Loading..." />}>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/instructor" element={<InstructorView />} />
            </Routes>
          </Suspense>
        </div>
        
        {showSettings && (
          <Suspense fallback={<LoadingSpinner text="Loading settings..." />}>
            <SettingsModal 
              onClose={() => dispatch(toggleSettings())}
            />
          </Suspense>
        )}
      </div>
    </Router>
  );
}

function App() {
  return (
    <Provider store={store}>
      <AppContent />
    </Provider>
  );
}

export default App;