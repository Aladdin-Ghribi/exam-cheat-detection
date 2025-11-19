import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { setWebcamActive, setUploadedVideo, updateDetectionData, fetchCurrentData } from '../store/appSlice';
import { api } from '../services/api';
import { throttle } from '../utils/performance';

function Dashboard() {
  const dispatch = useDispatch();
  const { socket, detectionData, videoState } = useSelector(state => state.app);
  const [sourceType, setSourceType] = useState('webcam');
  const [isProcessing, setIsProcessing] = useState(false);
  const [stream, setStream] = useState(null);
  const [fileName, setFileName] = useState('');
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const fileInputRef = useRef(null);

  const startWebcam = async () => {
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({ 
        video: { width: 640, height: 480 }, 
        audio: false 
      });
      setStream(mediaStream);
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
        videoRef.current.play();
        processFrames();
      }
    } catch (err) {
      console.error('Webcam access denied:', err);
      alert('Camera access required. Please allow and refresh.');
    }
  };

  const processFrames = useCallback(() => {
    if (!videoRef.current || !canvasRef.current || !socket) return;
    
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    
    const processFrame = () => {
      if (videoRef.current && !videoRef.current.paused) {
        canvas.width = videoRef.current.videoWidth || 640;
        canvas.height = videoRef.current.videoHeight || 480;
        ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
        
        const frameData = canvas.toDataURL('image/jpeg', 0.7);
        throttledEmit(frameData);
      }
      requestAnimationFrame(processFrame);
    };
    
    const throttledEmit = throttle((frameData) => {
      socket.emit('video_frame', { image: frameData, pose_enabled: true });
    }, 100);
    
    processFrame();
  }, [socket]);

  const handleFileUpload = useCallback(async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    try {
      const result = await api.uploadFile(file);
      
      if (result.success) {
        setFileName(file.name);
        setSourceType('file');
        dispatch(setUploadedVideo(file));
        
        if (result.file_type === 'image') {
          const processResult = await api.processFile(result.file_path, result.file_type);
          
          if (processResult.success) {
            dispatch(updateDetectionData({
              annotated_frame: processResult.annotated_frame,
              detections: processResult.detections,
              seat_assignments: processResult.seat_assignments,
              metrics: processResult.metrics
            }));
          }
        }
      }
    } catch (error) {
      console.error('Upload error:', error);
      alert('Upload failed');
    }
  }, [dispatch]);

  const resetToWebcam = () => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
    }
    setSourceType('webcam');
    setFileName('');
    dispatch(setUploadedVideo(null));
    dispatch(setWebcamActive(true));
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    startWebcam();
  };

  useEffect(() => {
    dispatch(fetchCurrentData());
    if (sourceType === 'webcam') {
      startWebcam();
    }
    return () => {
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
      }
    };
  }, [dispatch]);

  const { loading } = useSelector(state => state.app);

  return (
    <main className="animate-fadeIn" style={{ padding: '20px', minHeight: 'calc(100vh - 80px)' }} role="main">
      <section className="card animate-slideUp" style={{ marginBottom: '20px' }} aria-labelledby="source-heading">
        <h2 id="source-heading" style={{ margin: '0 0 1rem 0', color: '#2c3e50' }}>Select Source</h2>
        <div style={{ display: 'flex', gap: '10px', marginBottom: '10px' }} role="group" aria-labelledby="source-heading">
          <button 
            className={`btn ${sourceType === 'webcam' ? 'btn-instructor' : ''}`}
            onClick={resetToWebcam}
            aria-pressed={sourceType === 'webcam'}
            aria-describedby="webcam-desc"
          >
            Use Webcam
          </button>
          <label className="btn" style={{ background: '#f0f0f0', color: '#333' }} tabIndex="0" onKeyDown={(e) => e.key === 'Enter' && fileInputRef.current?.click()}>
            Upload File
            <input 
              ref={fileInputRef}
              type="file" 
              accept="video/mp4,image/jpeg,image/png" 
              onChange={handleFileUpload}
              style={{ display: 'none' }}
              aria-describedby="upload-desc"
            />
          </label>
        </div>
        <div id="webcam-desc" className="sr-only">Start live webcam feed for real-time detection</div>
        <div id="upload-desc" className="sr-only">Upload video or image file for analysis</div>
        {fileName && (
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px', background: '#f9f9f9', borderRadius: '4px' }}>
            <span style={{ fontWeight: 'bold' }}>{fileName}</span>
            <button className="btn" onClick={resetToWebcam} style={{ background: '#f44336', color: 'white' }}>
              Reset
            </button>
          </div>
        )}
      </div>

      <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap' }}>
        <section className="card animate-slideUp hover-lift" style={{ flex: 1, minWidth: '400px' }} aria-labelledby="video-heading">
          <h2 id="video-heading" style={{ margin: '0 0 1rem 0', color: '#2c3e50' }}>Video Feed</h2>
          <div style={{ position: 'relative', background: '#000', borderRadius: '8px', overflow: 'hidden' }} role="img" aria-label="Live video feed with detection annotations">
            {sourceType === 'webcam' && (
              <video 
                ref={videoRef} 
                style={{ width: '100%', height: 'auto' }}
                aria-label="Live webcam feed"
                muted
                playsInline
              />
            )}
            {detectionData.annotated_frame && (
              <img 
                src={`data:image/jpeg;base64,${detectionData.annotated_frame}`}
                alt="Processed frame showing detected objects and pose analysis with bounding boxes and annotations"
                style={{ width: '100%', height: 'auto' }}
              />
            )}
            <canvas ref={canvasRef} style={{ display: 'none' }} />
          </div>
        </div>

        <aside className="card animate-slideUp hover-lift" style={{ width: '300px', minWidth: '280px' }} aria-labelledby="metrics-heading">
          <h2 id="metrics-heading" style={{ margin: '0 0 1rem 0', color: '#2c3e50' }}>Detection Metrics</h2>
          {loading.currentData ? (
            <div className="loading" role="status" aria-live="polite">Loading metrics</div>
          ) : Object.keys(detectionData.metrics || {}).length === 0 ? (
            <p style={{ color: '#7f8c8d', fontStyle: 'italic' }} role="status">No objects detected</p>
          ) : (
            Object.entries(detectionData.metrics).map(([className, count]) => (
              <div key={className} className="metric-item" style={{ 
                margin: '8px 0', 
                padding: '12px', 
                background: 'linear-gradient(135deg, #f8f9fa, #e9ecef)', 
                borderLeft: '4px solid #27ae60',
                borderRadius: '8px',
                transition: 'all 0.3s ease'
              }} role="listitem" aria-label={`${className}: ${count} detected`}>
                <strong>{className}:</strong> <span aria-label={`${count} items`}>{count}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

export default Dashboard;