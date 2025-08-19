import { render } from '@testing-library/react';
import { BrowserRouter as Router } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { RundownProvider } from './contexts/RundownContext';
import { SocketProvider } from './contexts/SocketContext';
import App from './App';
import { vi, describe, it } from 'vitest';

vi.mock('@/contexts/useAuth', () => ({
  useAuth: () => ({
    currentUser: { uid: 'test-user', isAnonymous: false },
    loading: false,
  }),
}));

vi.mock('@/contexts/useRundown', () => ({
  useRundown: () => ({
    rundownSystem: 'cuez',
  }),
}));

vi.mock('@/contexts/useSocket', () => ({
  useSocket: () => ({
    connectionStatus: 'connected',
  }),
}));

describe('App', () => {
  it('renders without crashing', () => {
    render(
      <Router>
        <AuthProvider>
          <RundownProvider>
            <SocketProvider>
              <App />
            </SocketProvider>
          </RundownProvider>
        </AuthProvider>
      </Router>
    );
  });
});
