/**
 * Test Setup Configuration for AI-Powered Tuxemon Frontend
 * Austin Kidwell | Intellegix | Mobile-First Pokemon-Style Game
 *
 * Configures testing environment with mobile-specific utilities,
 * mocks, and performance validation for PWA testing.
 */

import '@testing-library/jest-dom'
import { vi, beforeEach, afterEach } from 'vitest'

// Mock global objects for browser environment
const mockNavigator = {
  userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)',
  onLine: true,
  connection: {
    effectiveType: '4g',
    downlink: 10,
    rtt: 100,
  },
  share: vi.fn(),
  standalone: false,
  serviceWorker: {
    register: vi.fn(),
    ready: Promise.resolve({
      showNotification: vi.fn(),
      sync: { register: vi.fn() },
    }),
  },
  permissions: {
    query: vi.fn().mockResolvedValue({ state: 'granted' }),
  },
}

const mockLocation = {
  hostname: 'localhost',
  origin: 'http://localhost:3000',
  pathname: '/',
  search: '',
  hash: '',
  reload: vi.fn(),
  assign: vi.fn(),
}

// Mock performance API for mobile testing
const mockPerformance = {
  now: vi.fn(() => Date.now()),
  mark: vi.fn(),
  measure: vi.fn(),
  getEntriesByType: vi.fn(() => []),
  observer: {
    observe: vi.fn(),
    disconnect: vi.fn(),
  },
}

// Mock Web APIs
Object.defineProperty(window, 'navigator', { value: mockNavigator, writable: true })
Object.defineProperty(window, 'location', { value: mockLocation, writable: true })
Object.defineProperty(window, 'performance', { value: mockPerformance, writable: true })

// Mock IndexedDB for offline storage testing
const mockIDB = {
  open: vi.fn().mockResolvedValue({
    transaction: vi.fn().mockReturnValue({
      objectStore: vi.fn().mockReturnValue({
        get: vi.fn().mockResolvedValue(undefined),
        put: vi.fn().mockResolvedValue(undefined),
        delete: vi.fn().mockResolvedValue(undefined),
        getAll: vi.fn().mockResolvedValue([]),
      }),
    }),
  }),
}

Object.defineProperty(window, 'indexedDB', { value: mockIDB, writable: true })

// Mock ResizeObserver for responsive components
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// Mock IntersectionObserver for lazy loading
global.IntersectionObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// Mock touch events for mobile testing
Object.defineProperty(window, 'TouchEvent', {
  value: class TouchEvent extends Event {
    touches: Touch[]
    targetTouches: Touch[]
    changedTouches: Touch[]

    constructor(type: string, init?: TouchEventInit) {
      super(type, init)
      this.touches = init?.touches || []
      this.targetTouches = init?.targetTouches || []
      this.changedTouches = init?.changedTouches || []
    }
  },
})

// Mock WebSocket for real-time features
global.WebSocket = vi.fn().mockImplementation(() => ({
  close: vi.fn(),
  send: vi.fn(),
  readyState: 1, // OPEN
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
}))

// Mock Canvas API for game rendering
const mockCanvas = {
  getContext: vi.fn().mockReturnValue({
    fillRect: vi.fn(),
    clearRect: vi.fn(),
    drawImage: vi.fn(),
    getImageData: vi.fn(),
    putImageData: vi.fn(),
    createImageData: vi.fn(),
    setTransform: vi.fn(),
    save: vi.fn(),
    restore: vi.fn(),
    beginPath: vi.fn(),
    moveTo: vi.fn(),
    lineTo: vi.fn(),
    stroke: vi.fn(),
    fill: vi.fn(),
    arc: vi.fn(),
    rect: vi.fn(),
    scale: vi.fn(),
    translate: vi.fn(),
    rotate: vi.fn(),
    measureText: vi.fn().mockReturnValue({ width: 100 }),
    createLinearGradient: vi.fn(),
    createRadialGradient: vi.fn(),
  }),
  toDataURL: vi.fn(),
  width: 800,
  height: 600,
}

Object.defineProperty(HTMLCanvasElement.prototype, 'getContext', {
  value: mockCanvas.getContext,
})

// Mock Audio API for sound effects
global.Audio = vi.fn().mockImplementation(() => ({
  play: vi.fn().mockResolvedValue(undefined),
  pause: vi.fn(),
  load: vi.fn(),
  currentTime: 0,
  duration: 100,
  volume: 1,
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
}))

// Mock vibration API for haptic feedback
Object.defineProperty(navigator, 'vibrate', {
  value: vi.fn(),
  writable: true,
})

// Mock device motion for mobile controls
window.DeviceMotionEvent = vi.fn() as any
window.DeviceOrientationEvent = vi.fn() as any

// Mock localStorage and sessionStorage
const createStorageMock = () => {
  let store: Record<string, string> = {}

  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => { store[key] = value }),
    removeItem: vi.fn((key: string) => { delete store[key] }),
    clear: vi.fn(() => { store = {} }),
    get length() { return Object.keys(store).length },
    key: vi.fn((index: number) => Object.keys(store)[index] || null),
  }
}

Object.defineProperty(window, 'localStorage', { value: createStorageMock() })
Object.defineProperty(window, 'sessionStorage', { value: createStorageMock() })

// Mock CSS Media Queries for responsive testing
Object.defineProperty(window, 'matchMedia', {
  value: vi.fn().mockImplementation((query: string) => ({
    matches: query.includes('max-width: 768px'), // Default to mobile
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock requestAnimationFrame for animations
let frameId = 0
Object.defineProperty(window, 'requestAnimationFrame', {
  value: vi.fn((callback: FrameRequestCallback) => {
    frameId++
    setTimeout(() => callback(performance.now()), 16) // 60fps
    return frameId
  }),
})

Object.defineProperty(window, 'cancelAnimationFrame', {
  value: vi.fn(),
})

// Mock URL constructor
global.URL = class URL {
  pathname: string
  search: string
  hash: string
  hostname: string
  origin: string

  constructor(url: string) {
    this.pathname = url.includes('/') ? url.split('/').slice(-1)[0] : url
    this.search = ''
    this.hash = ''
    this.hostname = 'localhost'
    this.origin = 'http://localhost:3000'
  }

  toString() {
    return `${this.origin}${this.pathname}${this.search}${this.hash}`
  }
} as any

// Mobile-specific test utilities
export const mobileTestUtils = {
  // Simulate touch events
  createTouchEvent: (type: string, touches: Partial<Touch>[] = []) => {
    const touchList = touches.map((touch, index) => ({
      identifier: touch.identifier ?? index,
      target: touch.target ?? document.body,
      clientX: touch.clientX ?? 0,
      clientY: touch.clientY ?? 0,
      pageX: touch.pageX ?? touch.clientX ?? 0,
      pageY: touch.pageY ?? touch.clientY ?? 0,
      screenX: touch.screenX ?? touch.clientX ?? 0,
      screenY: touch.screenY ?? touch.clientY ?? 0,
      radiusX: touch.radiusX ?? 1,
      radiusY: touch.radiusY ?? 1,
      rotationAngle: touch.rotationAngle ?? 0,
      force: touch.force ?? 1,
    })) as Touch[]

    return new TouchEvent(type, {
      touches: touchList,
      targetTouches: touchList,
      changedTouches: touchList,
    })
  },

  // Simulate device orientation
  mockDeviceOrientation: (orientation: 'portrait' | 'landscape') => {
    Object.defineProperty(screen, 'orientation', {
      value: {
        type: `${orientation}-primary`,
        angle: orientation === 'portrait' ? 0 : 90,
      },
      writable: true,
    })
  },

  // Simulate network conditions
  mockNetworkCondition: (effectiveType: '4g' | '3g' | '2g' | 'slow-2g', downlink = 10) => {
    Object.defineProperty(navigator, 'connection', {
      value: {
        effectiveType,
        downlink,
        rtt: effectiveType === '4g' ? 100 : effectiveType === '3g' ? 200 : 500,
      },
      writable: true,
    })
  },

  // Mock viewport dimensions
  mockViewport: (width: number, height: number) => {
    Object.defineProperty(window, 'innerWidth', { value: width, writable: true })
    Object.defineProperty(window, 'innerHeight', { value: height, writable: true })

    // Trigger resize event
    window.dispatchEvent(new Event('resize'))
  },

  // Common mobile breakpoints
  setMobileViewport: () => mobileTestUtils.mockViewport(375, 667), // iPhone SE
  setTabletViewport: () => mobileTestUtils.mockViewport(768, 1024), // iPad
  setDesktopViewport: () => mobileTestUtils.mockViewport(1920, 1080),
}

// Performance testing utilities
export const performanceTestUtils = {
  // Measure component render time
  measureRender: async (renderFunction: () => Promise<any> | any) => {
    const start = performance.now()
    await renderFunction()
    const end = performance.now()
    return end - start
  },

  // Assert performance thresholds for mobile
  assertMobilePerformance: (renderTime: number) => {
    // Mobile performance targets
    const MOBILE_RENDER_THRESHOLD = 16 // 16ms for 60fps
    const MOBILE_RENDER_WARNING = 32   // 32ms for 30fps

    if (renderTime > MOBILE_RENDER_THRESHOLD) {
      console.warn(`Render time ${renderTime.toFixed(2)}ms exceeds 60fps target (16ms)`)
    }

    return renderTime <= MOBILE_RENDER_WARNING
  },

  // Mock slow device
  mockSlowDevice: () => {
    vi.spyOn(performance, 'now').mockImplementation(() => Date.now() + Math.random() * 50)
  },

  // Reset performance mocks
  resetPerformanceMocks: () => {
    vi.restoreAllMocks()
  },
}

// Setup and teardown for each test
beforeEach(() => {
  // Reset all mocks
  vi.clearAllMocks()

  // Set default mobile viewport
  mobileTestUtils.setMobileViewport()

  // Reset navigator online status
  Object.defineProperty(navigator, 'onLine', { value: true, writable: true })

  // Clear storage
  localStorage.clear()
  sessionStorage.clear()
})

afterEach(() => {
  // Clean up any pending timers
  vi.clearAllTimers()

  // Reset performance mocks
  performanceTestUtils.resetPerformanceMocks()
})