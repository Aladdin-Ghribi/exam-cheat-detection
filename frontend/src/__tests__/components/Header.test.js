import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Header from '../../components/Header';

const HeaderWithRouter = ({ onSettingsClick }) => (
  <BrowserRouter>
    <Header onSettingsClick={onSettingsClick} />
  </BrowserRouter>
);

describe('Header Component', () => {
  test('renders app title', () => {
    render(<HeaderWithRouter onSettingsClick={jest.fn()} />);
    expect(screen.getByText('Exam Cheat Detection')).toBeInTheDocument();
  });

  test('calls onSettingsClick when settings button is clicked', () => {
    const mockSettingsClick = jest.fn();
    render(<HeaderWithRouter onSettingsClick={mockSettingsClick} />);
    
    fireEvent.click(screen.getByLabelText('Open settings modal'));
    expect(mockSettingsClick).toHaveBeenCalledTimes(1);
  });

  test('shows correct navigation text based on current route', () => {
    render(<HeaderWithRouter onSettingsClick={jest.fn()} />);
    expect(screen.getByText('Instructor View')).toBeInTheDocument();
  });

  test('has proper accessibility attributes', () => {
    render(<HeaderWithRouter onSettingsClick={jest.fn()} />);
    
    expect(screen.getByRole('banner')).toBeInTheDocument();
    expect(screen.getByRole('navigation')).toBeInTheDocument();
    expect(screen.getByLabelText('Main navigation')).toBeInTheDocument();
  });
});