
import { render, screen, fireEvent, act } from '@testing-library/react';
import { BrowserRouter as Router } from 'react-router-dom';
import Layout from './Layout';
import { useAuth } from '@/contexts/useAuth';
import { useRundown } from '@/contexts/useRundown';
import { vi, describe, it, expect, beforeEach } from 'vitest';

// Mock the hooks
import { useSocket } from '@/contexts/useSocket';

vi.mock('@/contexts/useAuth');
vi.mock('@/contexts/useRundown');
vi.mock('@/contexts/useSocket');


describe('Layout', () => {
  let mockUpdateRundownSystem;

  beforeEach(() => {
    vi.clearAllMocks();
    mockUpdateRundownSystem = vi.fn();

    useAuth.mockReturnValue({
      currentUser: { uid: 'test-user', isAnonymous: false },
      signOut: vi.fn(),
      setIsUpgrading: vi.fn(),
    });

    useRundown.mockReturnValue({
      rundownSystem: 'cuez',
      updateRundownSystem: mockUpdateRundownSystem,
    });

    useSocket.mockReturnValue({
      connectionStatus: 'connected',
    });

  });

  it.only('toggles the rundown system', async () => {
    await act(async () => {
      render(
        <Router>
          <Layout />
        </Router>
      );
    });

    const switchElement = screen.getByTestId('rundown-system-toggle');
    fireEvent.click(switchElement);

    expect(mockUpdateRundownSystem).toHaveBeenCalledWith('sofie');
  });
});
