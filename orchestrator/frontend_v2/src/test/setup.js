import { expect, afterEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';
import * as matchers from '@testing-library/jest-dom/matchers';

// extends Vitest's expect method with methods from react-testing-library
expect.extend(matchers);

// runs a cleanup after each test case (e.g. clearing jsdom)
afterEach(() => {
  cleanup();
});

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
    getTracks: vi.fn(() => [{
      stop: vi.fn()
    }]),
  }),
};
