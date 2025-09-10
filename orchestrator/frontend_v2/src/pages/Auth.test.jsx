import { render, screen, fireEvent } from '@testing-library/react';
import { vi, describe, it, expect } from 'vitest';
import Auth from './Auth';

// Mock firebase/app
vi.mock('firebase/app', () => ({
  initializeApp: vi.fn().mockReturnValue({}),
}));

// Mock firebase/auth to provide all necessary exports
vi.mock('firebase/auth', async () => {
  const actual = await vi.importActual('firebase/auth');
  return {
    ...actual,
    getAuth: vi.fn().mockReturnValue({}),
    GoogleAuthProvider: vi.fn(),
    signInWithPopup: vi.fn(),
  };
});

// Import signInWithPopup after the mock is defined
import { signInWithPopup } from 'firebase/auth';

describe('Auth Page', () => {
  it('renders a sign-in button', () => {
    render(<Auth />);
    const button = screen.getByRole('button', { name: /sign in with google/i });
    expect(button).toBeInTheDocument();
  });

  it('calls signInWithPopup when the button is clicked', () => {
    render(<Auth />);
    const button = screen.getByRole('button', { name: /sign in with google/i });
    fireEvent.click(button);
    expect(signInWithPopup).toHaveBeenCalled();
  });
});