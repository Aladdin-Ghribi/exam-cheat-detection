import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { api } from '../services/api';

export const fetchCurrentData = createAsyncThunk(
  'app/fetchCurrentData',
  async () => await api.getCurrentData()
);

export const fetchEventLog = createAsyncThunk(
  'app/fetchEventLog', 
  async () => await api.getEventLog()
);

export const fetchSeatAssignments = createAsyncThunk(
  'app/fetchSeatAssignments',
  async () => await api.getSeatAssignments()
);

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

export const appSlice = createSlice({
  name: 'app',
  initialState,
  reducers: {
    setSocket: (state, action) => {
      state.socket = action.payload;
    },
    setConnected: (state, action) => {
      state.isConnected = action.payload;
    },
    updateDetectionData: (state, action) => {
      state.detectionData = { ...state.detectionData, ...action.payload };
    },
    setWebcamActive: (state, action) => {
      state.videoState.isWebcamActive = action.payload;
      if (action.payload) {
        state.videoState.currentVideoSource = 'webcam';
      }
    },
    setUploadedVideo: (state, action) => {
      state.videoState.uploadedVideo = action.payload;
      state.videoState.currentVideoSource = action.payload ? 'upload' : null;
    },
    updateSettings: (state, action) => {
      state.settings = { ...state.settings, ...action.payload };
    },
    toggleSettings: (state) => {
      state.showSettings = !state.showSettings;
    }
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchCurrentData.pending, (state) => {
        state.loading.currentData = true;
      })
      .addCase(fetchCurrentData.fulfilled, (state, action) => {
        state.loading.currentData = false;
        state.detectionData = { ...state.detectionData, ...action.payload };
      })
      .addCase(fetchEventLog.fulfilled, (state, action) => {
        state.loading.eventLog = false;
        state.detectionData.event_log = action.payload.events || [];
      })
      .addCase(fetchSeatAssignments.fulfilled, (state, action) => {
        state.loading.seatAssignments = false;
        state.detectionData.seat_assignments = action.payload.seat_assignments || {};
      })
  },
});

export const { 
  setSocket, 
  setConnected, 
  updateDetectionData, 
  setWebcamActive, 
  setUploadedVideo, 
  updateSettings, 
  toggleSettings 
} = appSlice.actions;

export default appSlice.reducer;