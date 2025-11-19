import appReducer, { 
  setSocket, 
  setConnected, 
  updateDetectionData, 
  setWebcamActive, 
  updateSettings 
} from '../../store/appSlice';

describe('appSlice', () => {
  const initialState = {
    socket: null,
    isConnected: false,
    detectionData: {
      detections: [],
      seat_assignments: {},
      annotated_frame: null,
      metrics: {},
      event_log: []
    },
    videoState: {
      isWebcamActive: false,
      uploadedVideo: null,
      currentVideoSource: null
    },
    settings: {
      poseEnabled: true,
      confidenceThreshold: 0.5,
      suspicionThreshold: 0.7,
      performanceMode: 'balanced'
    },
    showSettings: false,
    loading: {
      currentData: false,
      eventLog: false,
      seatAssignments: false
    }
  };

  test('should return initial state', () => {
    expect(appReducer(undefined, { type: 'unknown' })).toEqual(initialState);
  });

  test('should handle setConnected', () => {
    const actual = appReducer(initialState, setConnected(true));
    expect(actual.isConnected).toBe(true);
  });

  test('should handle updateDetectionData', () => {
    const newData = {
      detections: [{ id: 1, class: 'person' }],
      metrics: { person: 1 }
    };
    
    const actual = appReducer(initialState, updateDetectionData(newData));
    expect(actual.detectionData.detections).toEqual(newData.detections);
    expect(actual.detectionData.metrics).toEqual(newData.metrics);
  });

  test('should handle setWebcamActive', () => {
    const actual = appReducer(initialState, setWebcamActive(true));
    expect(actual.videoState.isWebcamActive).toBe(true);
    expect(actual.videoState.currentVideoSource).toBe('webcam');
  });

  test('should handle updateSettings', () => {
    const newSettings = { poseEnabled: false, confidenceThreshold: 0.8 };
    const actual = appReducer(initialState, updateSettings(newSettings));
    
    expect(actual.settings.poseEnabled).toBe(false);
    expect(actual.settings.confidenceThreshold).toBe(0.8);
    expect(actual.settings.suspicionThreshold).toBe(0.7); // unchanged
  });
});