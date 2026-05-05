import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter as Router } from 'react-router-dom';
import Live from './Live';
import { useAuth } from '@/contexts/useAuth';
import { useRundown } from '@/contexts/useRundown';
import { useSocket } from '@/contexts/useSocket';
import { vi, describe, it, expect, beforeEach } from 'vitest';

// Mock the hooks
vi.mock('@/contexts/useAuth');
vi.mock('@/contexts/useRundown');
vi.mock('@/contexts/useSocket');

vi.mock('../components/live/TelemetryPanel', () => ({
  default: () => <div data-testid="telemetry-panel"></div>,
}));

import { getDocs } from 'firebase/firestore';

describe('Live page', () => {
  let eventListeners;

  beforeEach(() => {
    vi.clearAllMocks();
    eventListeners = {};
    const mockAddEventListener = vi.fn((event, handler) => {
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

    // Reset mocks before each test
    if (getDocs) {
      getDocs.mockClear();
    }
  });

  it('should display "Connection established" message when socket is opened', async () => {
    await act(async () => {
      render(
        <Router>
          <Live />
        </Router>
      );
    });

    await act(async () => {
      eventListeners.open();
    });

    expect(screen.getByText('Connection established')).toBeInTheDocument();
  });

  it('should display "Agent connection disconnected" message when socket is closed', async () => {
    await act(async () => {
      render(
        <Router>
          <Live />
        </Router>
      );
    });

    await act(async () => {
      eventListeners.close();
    });

    expect(screen.getByText('Agent connection disconnected')).toBeInTheDocument();
  });

  it('should load and display chat history', async () => {
    const mockHistory = [
      { id: '1', data: () => ({ type: 'USER_MESSAGE', text: 'Hello', timestamp: { toMillis: () => Date.now() } }) },
      { id: '2', data: () => ({ type: 'AGENT_MESSAGE', text: 'Hi there!', timestamp: { toMillis: () => Date.now() } }) },
    ];
    getDocs.mockResolvedValue({ docs: mockHistory });

    await act(async () => {
      render(
        <Router>
          <Live />
        </Router>
      );
    });

    await screen.findByText('Hello');
    expect(screen.getByText('Hi there!')).toBeInTheDocument();
  });

  it('should toggle microphone on and off and update agent replying status', async () => {
    const user = userEvent.setup();
    await act(async () => {
      render(
        <Router>
          <Live />
        </Router>
      );
    });

    // Initial state: Mic is off, no agent replying indicator
    const micButton = screen.getByRole('button', { name: /mic off/i });
    expect(micButton).toBeInTheDocument();
    expect(screen.queryByTestId('agent-replying-indicator')).not.toBeInTheDocument();

    // Turn mic on
    await act(async () => {
      await user.click(micButton);
    });

    // Mic is on, agent replying indicator should be visible
    const recordingButton = screen.getByRole('button', { name: /recording/i });
    expect(recordingButton).toBeInTheDocument();
    expect(screen.getByTestId('agent-replying-indicator')).toBeInTheDocument();

    // Turn mic off
    await act(async () => {
      await user.click(recordingButton);
    });

    // Mic is off, agent replying indicator should be gone
    const micOffButton = screen.getByRole('button', { name: /mic off/i });
    expect(micOffButton).toBeInTheDocument();
    expect(screen.queryByTestId('agent-replying-indicator')).not.toBeInTheDocument();
  });
});