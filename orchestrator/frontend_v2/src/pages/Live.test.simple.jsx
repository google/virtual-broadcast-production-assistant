import { render, screen } from '@testing-library/react';
import { BrowserRouter as Router } from 'react-router-dom';
import Live from './Live';
import { useSocket } from '@/contexts/useSocket';
import { vi, describe, it, expect } from 'vitest';

vi.mock('@/contexts/useAuth', () => ({
  useAuth: () => ({
    currentUser: { uid: 'test-user', isAnonymous: false },
  }),
}));

vi.mock('@/contexts/useRundown', () => ({
  useRundown: () => ({
    rundownSystem: 'cuez',
  }),
}));

vi.mock('@/contexts/useSocket');

describe('Live page', () => {
  it('should display "Connection established" message when socket is opened', () => {
    useSocket.mockReturnValue({
      addEventListener: () => () => {},
      connectionStatus: 'connected',
    });

    render(
      <Router>
        <Live />
      </Router>
    );

    expect(screen.getByText('Connection established')).toBeInTheDocument();
  });
});
