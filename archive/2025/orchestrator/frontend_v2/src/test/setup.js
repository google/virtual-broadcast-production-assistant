import { expect, afterEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';
import * as matchers from '@testing-library/jest-dom/matchers';

// extends Vitest's expect method with methods from react-testing-library
expect.extend(matchers);

// runs a cleanup after each test case (e.g. clearing jsdom)
afterEach(() => {
  cleanup();
});

// --- Global Mocks ---

// Mock AudioContext
global.AudioContext = vi.fn(() => ({
  audioWorklet: {
    addModule: vi.fn().mockResolvedValue(),
  },
  createMediaStreamSource: vi.fn(() => ({
    connect: vi.fn(),
  })),
  destination: {},
  close: vi.fn(),
}));

global.AudioWorkletNode = vi.fn(() => ({
  connect: vi.fn(),
  port: {
    onmessage: vi.fn(),
    postMessage: vi.fn(),
  },
}));

// Mock navigator.mediaDevices
global.navigator.mediaDevices = {
  ...global.navigator.mediaDevices,
  getUserMedia: vi.fn().mockResolvedValue({
    getTracks: vi.fn(() => [{ stop: vi.fn() }]),
  }),
};

// Mock Firebase SDK
vi.mock('firebase/app', () => ({
  initializeApp: vi.fn().mockReturnValue({}),
}));

vi.mock('firebase/auth', () => ({
  getAuth: vi.fn().mockReturnValue({}),
  onAuthStateChanged: vi.fn(() => {
    // Return a mock unsubscribe function
    return () => {};
  }),
  GoogleAuthProvider: vi.fn(),
  signInWithPopup: vi.fn().mockResolvedValue({ user: { uid: 'test-user' } }),
  signOut: vi.fn().mockResolvedValue(undefined),
}));

vi.mock('firebase/firestore', () => ({
  getFirestore: vi.fn().mockReturnValue({}),
  doc: vi.fn(() => ({})),
  getDoc: vi.fn(() => Promise.resolve({ exists: () => true, data: () => ({}) })),
  setDoc: vi.fn(() => Promise.resolve()),
  updateDoc: vi.fn(() => Promise.resolve()),
  collection: vi.fn(() => ({})),
  query: vi.fn(() => ({})),
  where: vi.fn(() => ({})),
  orderBy: vi.fn(() => ({})),
  limit: vi.fn(() => ({})),
  onSnapshot: vi.fn(() => () => {}), // Return an unsubscribe function
  getDocs: vi.fn(() => Promise.resolve({ docs: [] })),
  deleteDoc: vi.fn(() => Promise.resolve()),
}));

// Mock WebSocket API
vi.mock('@/api/webSocket', () => ({
  connectSocket: vi.fn(),
  disconnectSocket: vi.fn(),
  sendMessage: vi.fn(),
}));