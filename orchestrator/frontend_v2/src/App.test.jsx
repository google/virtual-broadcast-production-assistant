import { render, screen } from '@testing-library/react';
import { AuthProvider } from './contexts/AuthContext';
import { RundownProvider } from './contexts/RundownContext';
import { SocketProvider } from './contexts/SocketContext';
import App from './App';
import { vi, describe, it, beforeEach, expect } from 'vitest';

vi.mock('firebase/firestore', async (importOriginal) => {
    const actual = await importOriginal();
    return {
        ...actual,
        getFirestore: vi.fn(),
        doc: vi.fn(),
        getDoc: vi.fn(() => Promise.resolve({
            exists: () => true,
            data: () => ({ rundownSystem: 'cuez' })
        })),
        collection: vi.fn(),
        query: vi.fn(),
        onSnapshot: vi.fn(() => () => {}),
    }
});

vi.mock('firebaseui', () => ({
  auth: {
    AuthUI: {
      getInstance: vi.fn(() => ({
        start: vi.fn(),
      })),
      new: vi.fn(() => ({
        start: vi.fn()
      }))
    },
  },
}));

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
  }),
}));

describe('App', () => {
  beforeEach(() => {
    mockUseAuth.isAuthorised = true;
    mockUseAuth.currentUser = {
      uid: 'test-user',
      isAnonymous: false,
      getIdToken: () => Promise.resolve('test-token'),
      email: 'test@test.com',
    };
    mockUseAuth.loading = false;
  });

  it('renders without crashing', () => {
    render(
      <AuthProvider>
        <RundownProvider>
          <SocketProvider>
            <App />
          </SocketProvider>
        </RundownProvider>
      </AuthProvider>
    );
  });

  describe('when user is not authorized', () => {
    beforeEach(() => {
      mockUseAuth.isAuthorised = false;
    });

    it('renders the NotAuthorised page', () => {
      render(
        <AuthProvider>
          <RundownProvider>
            <SocketProvider>
              <App />
            </SocketProvider>
          </RundownProvider>
        </AuthProvider>
      );
      expect(screen.getByText('401 Not Authorised')).toBeInTheDocument();
    });

    it('renders the NotAuthorised page when user has no email', () => {
        mockUseAuth.currentUser.email = null;
        render(
            <AuthProvider>
                <RundownProvider>
                <SocketProvider>
                    <App />
                </SocketProvider>
                </RundownProvider>
            </AuthProvider>
        );
        expect(screen.getByText('401 Not Authorised')).toBeInTheDocument();
    });
  });
});
