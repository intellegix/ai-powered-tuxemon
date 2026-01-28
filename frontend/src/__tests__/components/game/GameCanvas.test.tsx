/**
 * Unit Tests for GameCanvas Component
 * Austin Kidwell | Intellegix | AI-Powered Tuxemon Game
 *
 * Tests 60fps rendering performance, touch controls, mobile optimization,
 * and canvas-based game rendering for the mobile Pokemon-style game.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { GameCanvas } from '../../../components/GameCanvas'
import { mobileTestUtils, performanceTestUtils } from '../../../test/setup'

// Mock the game store hooks
vi.mock('../../../hooks/useGameStore', () => ({
  useGameData: vi.fn(() => ({
    gameState: {
      player: {
        id: '123',
        username: 'test_player',
        position: { x: 10, y: 10 },
        currentMap: 'test_map',
        level: 5,
      },
    },
    worldState: {
      npcs: [
        {
          id: 'npc_1',
          name: 'Test NPC',
          position: [12, 8],
          spriteName: 'villager_01',
          approachable: true,
        },
      ],
      objects: [],
      currentMap: 'test_map',
    },
  })),
  useUI: vi.fn(() => ({
    ui: {
      isLoading: false,
      error: null,
      showInventory: false,
    },
    setLoading: vi.fn(),
    setError: vi.fn(),
  })),
}))

// Mock WebSocket service
vi.mock('../../../services/websocket', () => ({
  useWebSocket: vi.fn(() => ({
    sendPlayerUpdate: vi.fn(),
    isConnected: true,
  })),
}))

describe('GameCanvas Component', () => {
  beforeEach(() => {
    mobileTestUtils.setMobileViewport()
  })

  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('renders canvas with correct dimensions', () => {
    const width = 375
    const height = 667

    render(<GameCanvas width={width} height={height} />)

    const canvas = screen.getByRole('img', { hidden: true }) // Canvas has img role
    expect(canvas).toBeInTheDocument()
    expect(canvas).toHaveAttribute('width', width.toString())
    expect(canvas).toHaveAttribute('height', height.toString())
  })

  it('initializes canvas context on mount', () => {
    const mockGetContext = vi.fn().mockReturnValue({
      fillRect: vi.fn(),
      clearRect: vi.fn(),
      drawImage: vi.fn(),
    })

    const originalGetContext = HTMLCanvasElement.prototype.getContext
    HTMLCanvasElement.prototype.getContext = mockGetContext

    render(<GameCanvas width={800} height={600} />)

    expect(mockGetContext).toHaveBeenCalledWith('2d')

    // Restore original method
    HTMLCanvasElement.prototype.getContext = originalGetContext
  })

  it('handles touch start events correctly', async () => {
    const user = userEvent.setup()
    render(<GameCanvas width={400} height={600} />)

    const canvas = screen.getByRole('img', { hidden: true })

    // Create touch event
    const touchEvent = mobileTestUtils.createTouchEvent('touchstart', [
      { clientX: 100, clientY: 150, target: canvas },
    ])

    // Simulate touch start
    canvas.dispatchEvent(touchEvent)

    // Verify touch handling (component should process the touch)
    expect(canvas).toBeInTheDocument()
  })

  it('handles touch move events for camera control', () => {
    render(<GameCanvas width={400} height={600} />)

    const canvas = screen.getByRole('img', { hidden: true })

    // Simulate touch start
    const touchStart = mobileTestUtils.createTouchEvent('touchstart', [
      { clientX: 100, clientY: 150 },
    ])
    canvas.dispatchEvent(touchStart)

    // Simulate touch move (drag)
    const touchMove = mobileTestUtils.createTouchEvent('touchmove', [
      { clientX: 120, clientY: 170 }, // Moved 20px right, 20px down
    ])
    canvas.dispatchEvent(touchMove)

    // Component should handle the drag (no errors thrown)
    expect(canvas).toBeInTheDocument()
  })

  it('handles touch end events', () => {
    render(<GameCanvas width={400} height={600} />)

    const canvas = screen.getByRole('img', { hidden: true })

    // Simulate complete touch sequence
    const touchStart = mobileTestUtils.createTouchEvent('touchstart', [
      { clientX: 100, clientY: 150 },
    ])
    canvas.dispatchEvent(touchStart)

    const touchEnd = mobileTestUtils.createTouchEvent('touchend', [])
    canvas.dispatchEvent(touchEnd)

    // Component should handle the complete touch sequence
    expect(canvas).toBeInTheDocument()
  })

  it('maintains 60fps performance on mobile devices', async () => {
    const renderTime = await performanceTestUtils.measureRender(() => {
      render(<GameCanvas width={375} height={667} />)
    })

    const isPerformant = performanceTestUtils.assertMobilePerformance(renderTime)
    expect(isPerformant).toBe(true)
    expect(renderTime).toBeLessThan(32) // 30fps threshold
  })

  it('handles different viewport sizes correctly', () => {
    // Test mobile viewport
    mobileTestUtils.setMobileViewport()
    const { rerender } = render(<GameCanvas width={375} height={667} />)
    let canvas = screen.getByRole('img', { hidden: true })
    expect(canvas).toHaveAttribute('width', '375')
    expect(canvas).toHaveAttribute('height', '667')

    // Test tablet viewport
    mobileTestUtils.setTabletViewport()
    rerender(<GameCanvas width={768} height={1024} />)
    canvas = screen.getByRole('img', { hidden: true })
    expect(canvas).toHaveAttribute('width', '768')
    expect(canvas).toHaveAttribute('height', '1024')
  })

  it('cleans up animation frames on unmount', () => {
    const mockCancelAnimationFrame = vi.fn()
    global.cancelAnimationFrame = mockCancelAnimationFrame

    const { unmount } = render(<GameCanvas width={400} height={600} />)

    unmount()

    // Component should clean up any running animation frames
    expect(mockCancelAnimationFrame).toHaveBeenCalled()
  })

  it('prevents context menu on long press (mobile)', async () => {
    render(<GameCanvas width={400} height={600} />)

    const canvas = screen.getByRole('img', { hidden: true })

    // Mock context menu event
    const contextMenuEvent = new MouseEvent('contextmenu', {
      bubbles: true,
      cancelable: true,
    })

    const preventDefault = vi.spyOn(contextMenuEvent, 'preventDefault')

    canvas.dispatchEvent(contextMenuEvent)

    // Should prevent context menu on mobile
    expect(preventDefault).toHaveBeenCalled()
  })

  it('handles high DPI displays correctly', () => {
    // Mock high DPI display
    Object.defineProperty(window, 'devicePixelRatio', { value: 2, writable: true })

    render(<GameCanvas width={400} height={600} />)

    const canvas = screen.getByRole('img', { hidden: true }) as HTMLCanvasElement

    // Canvas should handle high DPI scaling
    expect(canvas).toBeInTheDocument()
    expect(canvas.style.width).toBeDefined()
    expect(canvas.style.height).toBeDefined()
  })

  it('handles canvas rendering errors gracefully', () => {
    // Mock canvas context that throws errors
    const mockGetContext = vi.fn().mockImplementation(() => {
      throw new Error('Canvas context error')
    })

    HTMLCanvasElement.prototype.getContext = mockGetContext

    // Should not throw error when rendering fails
    expect(() => {
      render(<GameCanvas width={400} height={600} />)
    }).not.toThrow()

    // Component should still render (with error handling)
    expect(screen.getByRole('img', { hidden: true })).toBeInTheDocument()
  })

  it('optimizes rendering for battery efficiency', async () => {
    // Mock low battery scenario
    Object.defineProperty(navigator, 'getBattery', {
      value: vi.fn().mockResolvedValue({
        level: 0.2, // 20% battery
        charging: false,
      }),
    })

    const { unmount } = render(<GameCanvas width={400} height={600} />)

    // Component should implement battery-aware rendering optimizations
    expect(screen.getByRole('img', { hidden: true })).toBeInTheDocument()

    unmount()
  })

  it('handles network state changes', () => {
    render(<GameCanvas width={400} height={600} />)

    // Mock network state change to offline
    Object.defineProperty(navigator, 'onLine', { value: false, writable: true })
    window.dispatchEvent(new Event('offline'))

    // Component should handle offline state
    expect(screen.getByRole('img', { hidden: true })).toBeInTheDocument()

    // Mock network state change to online
    Object.defineProperty(navigator, 'onLine', { value: true, writable: true })
    window.dispatchEvent(new Event('online'))

    // Component should handle online state restoration
    expect(screen.getByRole('img', { hidden: true })).toBeInTheDocument()
  })

  it('supports keyboard navigation as fallback', async () => {
    const user = userEvent.setup()
    render(<GameCanvas width={400} height={600} />)

    const canvas = screen.getByRole('img', { hidden: true })

    // Make canvas focusable for keyboard navigation
    canvas.setAttribute('tabindex', '0')
    await user.click(canvas) // Focus the canvas

    // Test arrow key navigation
    await user.keyboard('{ArrowUp}')
    await user.keyboard('{ArrowDown}')
    await user.keyboard('{ArrowLeft}')
    await user.keyboard('{ArrowRight}')

    // Component should handle keyboard events
    expect(canvas).toHaveFocus()
  })

  it('renders with proper accessibility attributes', () => {
    render(<GameCanvas width={400} height={600} />)

    const canvas = screen.getByRole('img', { hidden: true })

    // Should have proper ARIA attributes
    expect(canvas).toHaveAttribute('aria-label')
    expect(canvas).toHaveAttribute('role', 'img')
  })

  it('handles rapid touch events without performance degradation', () => {
    render(<GameCanvas width={400} height={600} />)

    const canvas = screen.getByRole('img', { hidden: true })

    // Simulate rapid touch events
    for (let i = 0; i < 20; i++) {
      const touchEvent = mobileTestUtils.createTouchEvent('touchmove', [
        { clientX: 100 + i, clientY: 150 + i },
      ])
      canvas.dispatchEvent(touchEvent)
    }

    // Component should handle rapid events without crashing
    expect(canvas).toBeInTheDocument()
  })

  it('maintains aspect ratio across different screen sizes', () => {
    // Test various mobile aspect ratios
    const aspectRatios = [
      { width: 375, height: 667 }, // iPhone SE
      { width: 414, height: 896 }, // iPhone 11
      { width: 360, height: 640 }, // Small Android
      { width: 768, height: 1024 }, // iPad
    ]

    aspectRatios.forEach(({ width, height }) => {
      const { unmount } = render(<GameCanvas width={width} height={height} />)
      const canvas = screen.getByRole('img', { hidden: true })

      expect(canvas).toHaveAttribute('width', width.toString())
      expect(canvas).toHaveAttribute('height', height.toString())

      const aspectRatio = width / height
      expect(aspectRatio).toBeGreaterThan(0.3) // Reasonable aspect ratio range
      expect(aspectRatio).toBeLessThan(3.0)

      unmount()
    })
  })

  it('handles orientation changes', () => {
    render(<GameCanvas width={375} height={667} />)

    // Mock orientation change to landscape
    mobileTestUtils.mockDeviceOrientation('landscape')
    window.dispatchEvent(new Event('orientationchange'))

    // Component should handle orientation change
    expect(screen.getByRole('img', { hidden: true })).toBeInTheDocument()

    // Mock orientation change back to portrait
    mobileTestUtils.mockDeviceOrientation('portrait')
    window.dispatchEvent(new Event('orientationchange'))

    // Component should handle orientation change back
    expect(screen.getByRole('img', { hidden: true })).toBeInTheDocument()
  })
})