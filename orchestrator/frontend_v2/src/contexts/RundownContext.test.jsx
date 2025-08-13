import React from 'react';
import { render, act } from '@testing-library/react';
import { RundownProvider, useRundown } from './RundownContext';
import { SocketProvider } from './SocketContext';
import { AuthProvider } from './AuthContext';

// Mock dependencies
jest.mock('./SocketContext', () => ({
  ...jest.requireActual('./SocketContext'),
  useSocket: jest.fn(),
}));
jest.mock('./AuthContext');
jest.mock('@/lib/firebase', () => ({
  db: {},
}));
jest.mock('firebase/firestore', () => ({
  doc: jest.fn(),
  getDoc: jest.fn(),
  setDoc: jest.fn(),
}));

const mockReconnect = jest.fn();
const mockUseSocket = require('./SocketContext').useSocket;

// A test component to consume the context
const TestConsumer = () => {
  const { rundownSystem, updateRundownSystem } = useRundown();
  return (
    <div>
      <span>{rundownSystem}</span>
      <button onClick={() => updateRundownSystem('sofie')}>Update</button>
    </div>
  );
};

describe('RundownProvider', () => {
  beforeEach(() => {
    // Reset mocks before each test
    jest.clearAllMocks();
    mockUseSocket.mockReturnValue({ reconnect: mockReconnect });
    require('./AuthContext').useAuth.mockReturnValue({ currentUser: { uid: 'test-user' } });
  });

  it('calls reconnect when the rundown system is updated', async () => {
    const { getByText } = render(
      <AuthProvider>
        <SocketProvider>
          <RundownProvider>
            <TestConsumer />
          </RundownProvider>
        </SocketProvider>
      </AuthProvider>
    );

    // Initial state
    expect(getByText('cuez')).toBeInTheDocument();
    expect(mockReconnect).not.toHaveBeenCalled();

    // Click the update button
    await act(async () => {
      getByText('Update').click();
    });

    // Check that the state updated and reconnect was called
    expect(getByText('sofie')).toBeInTheDocument();
    expect(mockReconnect).toHaveBeenCalledTimes(1);
  });
});
