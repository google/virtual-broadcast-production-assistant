import React from 'react';
import { render, screen, act } from '@testing-library/react';
import { BrowserRouter as Router } from 'react-router-dom';
import Live from './Live';
import { useAuth } from '@/contexts/AuthContext';
import { useRundown } from '@/contexts/RundownContext';
import { useSocket } from '@/contexts/SocketContext';
import { vi, describe, it, expect, beforeEach } from 'vitest';

vi.mock('firebase/app', () => ({
  initializeApp: vi.fn(() => ({})),
}));

vi.mock('firebase/auth', () => ({
  getAuth: vi.fn(),
}));

vi.mock('firebase/firestore', () => ({
    getFirestore: vi.fn(),
}));

// Mock the hooks
vi.mock('@/contexts/AuthContext');
vi.mock('@/contexts/RundownContext');
vi.mock('@/contexts/SocketContext');

describe('Live page', () => {
  let mockAddEventListener;
  let eventListeners;

  beforeEach(() => {
    vi.clearAllMocks();
    eventListeners = {};
    mockAddEventListener = vi.fn((event, handler) => {
      eventListeners[event] = handler;
      return () => {
        delete eventListeners[event];
      };
    });

    useAuth.mockReturnValue({
      currentUser: { uid: 'test-user', isAnonymous: false },
    });

    useRundown.mockReturnValue({
      rundownSystem: 'cuez',
    });

    useSocket.mockReturnValue({
      addEventListener: mockAddEventListener,
    });
  });

  it('should display "Connection established" message when socket is opened', () => {
    render(
      <Router>
        <Live />
      </Router>
    );

    act(() => {
      eventListeners.open();
    });

    expect(screen.getByText('Connection established')).toBeInTheDocument();
  });

  it('should display "Agent connection disconnected" message when socket is closed', () => {
    render(
      <Router>
        <Live />
      </Router>
    );

    act(() => {
      eventListeners.close();
    });

    expect(screen.getByText('Agent connection disconnected')).toBeInTheDocument();
  });
});
