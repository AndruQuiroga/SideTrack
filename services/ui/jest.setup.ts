import '@testing-library/jest-dom';

// Mock ResizeObserver for Recharts
class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

// @ts-ignore
window.ResizeObserver = ResizeObserver;
