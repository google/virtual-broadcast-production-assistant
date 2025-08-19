
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter as Router } from 'react-router-dom';
import Layout from './Layout';
import { useAuth } from '@/contexts/AuthContext';
import { useRundown } from '@/contexts/RundownContext';
import { vi, describe, it, expect, beforeEach } from 'vitest';

// Mock the hooks
vi.mock('@/contexts/AuthContext');
vi.mock('@/contexts/RundownContext');

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
  });

  it('toggles the rundown system', () => {
    render(
      <Router>
        <Layout />
      </Router>
    );

    const switchElement = screen.getByRole('switch');
    fireEvent.click(switchElement);

    expect(mockUpdateRundownSystem).toHaveBeenCalledWith('sofie');
  });
});