import { render, screen, act } from '@testing-library/react';
import { BrowserRouter as Router } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { RundownProvider } from './contexts/RundownContext';
import { SocketProvider } from './contexts/SocketContext';
import App from './App';
import { vi, describe, it, beforeEach, expect } from 'vitest';

const mockUseAuth = {
  currentUser: {
    uid: 'test-user',
    isAnonymous: false,
    getIdToken: () => Promise.resolve('test-token'),
    email: 'test@test.com',
  },
  loading: false,
  isAuthorised: true,
  signOut: vi.fn(),
};

vi.mock('@/contexts/useAuth', () => ({
  useAuth: () => mockUseAuth,
}));

vi.mock('@/contexts/useRundown', () => ({
  useRundown: () => ({
    rundownSystem: 'cuez',
  }),
}));

vi.mock('@/contexts/useSocket', () => ({
  useSocket: () => ({
    connectionStatus: 'connected',
    addEventListener: () => () => {},
  }),
}));

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.isAuthorised = true;
    mockUseAuth.currentUser = {
      uid: 'test-user',
      isAnonymous: false,
      getIdToken: () => Promise.resolve('test-token'),
      email: 'test@test.com',
    };
    mockUseAuth.loading = false;
  });

  it('renders without crashing', async () => {
    await act(async () => {
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

  describe('when user is not authorized', () => {
    beforeEach(() => {
      mockUseAuth.isAuthorised = false;
    });

    it('renders the NotAuthorised page', async () => {
      await act(async () => {
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
      expect(screen.getByText('401 Not Authorised')).toBeInTheDocument();
    });

    it('renders the NotAuthorised page when user has no email', async () => {
        mockUseAuth.currentUser.email = null;
        await act(async () => {
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
        expect(screen.getByText('401 Not Authorised')).toBeInTheDocument();
    });
  });
});