import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import App from '../../App';

// Mock socket.io-client
jest.mock('socket.io-client', () => {
  return jest.fn(() => ({
    on: jest.fn(),
    emit: jest.fn(),
    close: jest.fn()
  }));
});

describe('App Integration Tests', () => {
  test('renders app with header and main content', () => {
    render(<App />);
    
    expect(screen.getByText('Exam Cheat Detection')).toBeInTheDocument();
    expect(screen.getByRole('main')).toBeInTheDocument();
  });

  test('navigation between dashboard and instructor view works', () => {
    render(<App />);
    
    // Should start on dashboard
    expect(screen.getByText('Select Source')).toBeInTheDocument();
    
    // Navigate to instructor view
    fireEvent.click(screen.getByText('Instructor View'));
    expect(screen.getByText('Seat Map')).toBeInTheDocument();
    
    // Navigate back to dashboard
    fireEvent.click(screen.getByText('Dashboard'));
    expect(screen.getByText('Select Source')).toBeInTheDocument();
  });

  test('settings modal opens and closes', () => {
    render(<App />);
    
    // Open settings
    fireEvent.click(screen.getByLabelText('Open settings modal'));
    expect(screen.getByText('Pose Controls')).toBeInTheDocument();
    
    // Close settings
    fireEvent.click(screen.getByLabelText('Close settings modal'));
    expect(screen.queryByText('Pose Controls')).not.toBeInTheDocument();
  });

  test('skip link is present for accessibility', () => {
    render(<App />);
    expect(screen.getByText('Skip to main content')).toBeInTheDocument();
  });
});