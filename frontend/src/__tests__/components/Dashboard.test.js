import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import Dashboard from '../../components/Dashboard';
import appReducer from '../../store/appSlice';

const createMockStore = (initialState = {}) => {
  return configureStore({
    reducer: { app: appReducer },
    preloadedState: {
      app: {
        socket: null,
        detectionData: { metrics: {}, annotated_frame: null },
        videoState: { isWebcamActive: false, uploadedVideo: null },
        loading: { currentData: false },
        ...initialState
      }
    }
  });
};

const renderWithStore = (component, store) => {
  return render(
    <Provider store={store}>
      {component}
    </Provider>
  );
};

describe('Dashboard Component', () => {
  test('renders source selection section', () => {
    const store = createMockStore();
    renderWithStore(<Dashboard />, store);
    
    expect(screen.getByText('Select Source')).toBeInTheDocument();
    expect(screen.getByText('Use Webcam')).toBeInTheDocument();
    expect(screen.getByText('Upload File')).toBeInTheDocument();
  });

  test('shows loading state for metrics', () => {
    const store = createMockStore({ loading: { currentData: true } });
    renderWithStore(<Dashboard />, store);
    
    expect(screen.getByText('Loading metrics')).toBeInTheDocument();
  });

  test('displays detection metrics when available', () => {
    const store = createMockStore({
      detectionData: { metrics: { 'cell phone': 2, 'person': 1 } }
    });
    renderWithStore(<Dashboard />, store);
    
    expect(screen.getByText('cell phone:')).toBeInTheDocument();
    expect(screen.getByText('person:')).toBeInTheDocument();
  });

  test('shows no objects detected message when metrics are empty', () => {
    const store = createMockStore();
    renderWithStore(<Dashboard />, store);
    
    expect(screen.getByText('No objects detected')).toBeInTheDocument();
  });

  test('has proper accessibility structure', () => {
    const store = createMockStore();
    renderWithStore(<Dashboard />, store);
    
    expect(screen.getByRole('main')).toBeInTheDocument();
    expect(screen.getByLabelText('Select Source')).toBeInTheDocument();
    expect(screen.getByLabelText('Live video feed with detection annotations')).toBeInTheDocument();
  });
});