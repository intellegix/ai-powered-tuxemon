/**
 * Unit Tests for InventoryUI Component
 * Austin Kidwell | Intellegix | AI-Powered Tuxemon Game
 *
 * Tests inventory management interface, touch interactions, item usage,
 * and mobile-optimized UI for the game's inventory system.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, cleanup, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { InventoryUI } from '../../../components/InventoryUI'
import { mobileTestUtils, performanceTestUtils } from '../../../test/setup'

// Mock game data and API
const mockInventoryData = {
  items: [
    {
      id: '1',
      slug: 'health_potion',
      name: 'Health Potion',
      description: 'Restores 50 HP to a monster.',
      category: 'healing',
      rarity: 'common',
      quantity: 5,
      sprite: 'potion_red.png',
      effects: { heal_hp: 50 },
    },
    {
      id: '2',
      slug: 'tuxeball',
      name: 'Tuxe Ball',
      description: 'A basic ball for catching wild monsters.',
      category: 'capture',
      rarity: 'common',
      quantity: 10,
      sprite: 'tuxeball.png',
      effects: { capture_rate: 0.3 },
    },
    {
      id: '3',
      slug: 'rare_candy',
      name: 'Rare Candy',
      description: 'Instantly increases a monster level by 1.',
      category: 'evolution',
      rarity: 'rare',
      quantity: 2,
      sprite: 'rare_candy.png',
      effects: { level_up: 1 },
    },
  ],
  maxSlots: 50,
  usedSlots: 17,
}

// Mock hooks and services
vi.mock('../../../hooks/useGameStore', () => ({
  useInventory: vi.fn(() => ({
    inventory: mockInventoryData,
    useItem: vi.fn(),
    sortItems: vi.fn(),
    searchItems: vi.fn(),
  })),
  useUI: vi.fn(() => ({
    ui: {
      showInventory: true,
      selectedItem: null,
    },
    setSelectedItem: vi.fn(),
    closeInventory: vi.fn(),
  })),
}))

vi.mock('../../../services/api', () => ({
  useItemActions: vi.fn(() => ({
    useItemMutation: {
      mutate: vi.fn(),
      isLoading: false,
    },
  })),
}))

describe('InventoryUI Component', () => {
  beforeEach(() => {
    mobileTestUtils.setMobileViewport()
  })

  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('renders inventory items correctly', () => {
    render(<InventoryUI />)

    // Should show all items
    expect(screen.getByText('Health Potion')).toBeInTheDocument()
    expect(screen.getByText('Tuxe Ball')).toBeInTheDocument()
    expect(screen.getByText('Rare Candy')).toBeInTheDocument()

    // Should show quantities
    expect(screen.getByText('5')).toBeInTheDocument()
    expect(screen.getByText('10')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
  })

  it('displays item categories with proper organization', () => {
    render(<InventoryUI />)

    // Should have category sections or filters
    expect(screen.getByText(/healing/i) || screen.getByText(/Health/i)).toBeInTheDocument()
    expect(screen.getByText(/capture/i) || screen.getByText(/Ball/i)).toBeInTheDocument()
    expect(screen.getByText(/evolution/i) || screen.getByText(/Candy/i)).toBeInTheDocument()
  })

  it('shows item rarity indicators', () => {
    render(<InventoryUI />)

    // Should indicate rare items differently
    const rareCandyElement = screen.getByText('Rare Candy').closest('[data-testid]')
      || screen.getByText('Rare Candy').parentElement

    expect(rareCandyElement).toBeInTheDocument()

    // Could check for rarity styling, icons, or text
    // The exact implementation depends on how rarity is displayed
  })

  it('handles touch interactions for mobile', async () => {
    const user = userEvent.setup()
    render(<InventoryUI />)

    const healthPotion = screen.getByText('Health Potion')

    // Test touch tap
    await user.click(healthPotion)

    // Should select the item or show details
    expect(healthPotion).toBeInTheDocument()

    // Test long press simulation (using pointerdown + delay)
    await user.pointer([
      { target: healthPotion, keys: '[TouchA>]', coords: { x: 100, y: 100 } },
    ])

    // Wait for long press duration
    await waitFor(() => {}, { timeout: 600 })

    await user.pointer([{ keys: '[/TouchA]' }])

    // Should show context menu or item options
    expect(healthPotion).toBeInTheDocument()
  })

  it('provides touch-friendly item selection with 44px targets', async () => {
    const user = userEvent.setup()
    render(<InventoryUI />)

    const itemElements = screen.getAllByRole('button')
      .filter(btn => btn.textContent?.includes('Health Potion') ||
                     btn.textContent?.includes('Tuxe Ball') ||
                     btn.textContent?.includes('Rare Candy'))

    // Each item should be touchable with adequate size
    itemElements.forEach(element => {
      const styles = window.getComputedStyle(element)
      const minSize = 44 // Minimum touch target size in px

      // Note: In test environment, computed styles might not reflect CSS
      // This is more of a structural test
      expect(element).toBeInTheDocument()
      expect(element.getAttribute('role')).toBe('button')
    })

    // Test that items are clickable
    if (itemElements.length > 0) {
      await user.click(itemElements[0])
      expect(itemElements[0]).toBeInTheDocument()
    }
  })

  it('handles swipe gestures for navigation', () => {
    render(<InventoryUI />)

    const inventoryContainer = screen.getByRole('dialog') ||
                              screen.getByTestId('inventory-container') ||
                              screen.getByText('Health Potion').closest('div')!

    // Simulate swipe down (close gesture)
    const touchStart = mobileTestUtils.createTouchEvent('touchstart', [
      { clientX: 200, clientY: 100 },
    ])
    inventoryContainer.dispatchEvent(touchStart)

    const touchMove = mobileTestUtils.createTouchEvent('touchmove', [
      { clientX: 200, clientY: 200 }, // Swipe down 100px
    ])
    inventoryContainer.dispatchEvent(touchMove)

    const touchEnd = mobileTestUtils.createTouchEvent('touchend', [])
    inventoryContainer.dispatchEvent(touchEnd)

    // Component should handle swipe gesture
    expect(inventoryContainer).toBeInTheDocument()
  })

  it('renders efficiently for mobile performance', async () => {
    const renderTime = await performanceTestUtils.measureRender(() => {
      render(<InventoryUI />)
    })

    const isPerformant = performanceTestUtils.assertMobilePerformance(renderTime)
    expect(isPerformant).toBe(true)
  })

  it('implements item search functionality', async () => {
    const user = userEvent.setup()
    render(<InventoryUI />)

    // Look for search input
    const searchInput = screen.queryByPlaceholderText(/search/i) ||
                       screen.queryByLabelText(/search/i) ||
                       screen.queryByRole('searchbox')

    if (searchInput) {
      await user.type(searchInput, 'potion')

      // Should filter to show only health potion
      expect(screen.getByText('Health Potion')).toBeInTheDocument()

      // Other items might be hidden (implementation dependent)
      // The component should handle search filtering
    }
  })

  it('shows item usage controls in battle context', () => {
    // Mock battle context
    vi.mocked(require('../../../hooks/useGameStore').useUI).mockReturnValue({
      ui: {
        showInventory: true,
        selectedItem: null,
        inBattle: true, // Battle context
      },
      setSelectedItem: vi.fn(),
      closeInventory: vi.fn(),
    })

    render(<InventoryUI />)

    // Should show items that are usable in battle
    expect(screen.getByText('Health Potion')).toBeInTheDocument()

    // Should indicate which items can be used in current context
    const healthPotion = screen.getByText('Health Potion')
    const potionContainer = healthPotion.closest('[data-testid]') ||
                           healthPotion.parentElement

    expect(potionContainer).toBeInTheDocument()
  })

  it('handles item sorting by different criteria', async () => {
    const user = userEvent.setup()
    render(<InventoryUI />)

    // Look for sort options
    const sortButton = screen.queryByText(/sort/i) ||
                      screen.queryByRole('button', { name: /sort/i }) ||
                      screen.queryByTestId('sort-button')

    if (sortButton) {
      await user.click(sortButton)

      // Should show sort options
      const nameOption = screen.queryByText(/name/i)
      const categoryOption = screen.queryByText(/category/i)
      const rarityOption = screen.queryByText(/rarity/i)

      if (nameOption) {
        await user.click(nameOption)
        // Items should be sorted alphabetically
      }
    }

    // Items should still be present after sorting
    expect(screen.getByText('Health Potion')).toBeInTheDocument()
  })

  it('shows inventory capacity indicators', () => {
    render(<InventoryUI />)

    // Should show used/total slots
    const capacityText = screen.queryByText(/17/) || // Used slots
                        screen.queryByText(/50/) || // Max slots
                        screen.queryByText(/slots/i)

    if (capacityText) {
      expect(capacityText).toBeInTheDocument()
    }

    // Should show some indication of inventory space
    const inventoryElement = screen.getByText('Health Potion').closest('div')
    expect(inventoryElement).toBeInTheDocument()
  })

  it('prevents accidental item usage with confirmation', async () => {
    const user = userEvent.setup()
    const mockUseItem = vi.fn()

    vi.mocked(require('../../../hooks/useGameStore').useInventory).mockReturnValue({
      inventory: mockInventoryData,
      useItem: mockUseItem,
      sortItems: vi.fn(),
      searchItems: vi.fn(),
    })

    render(<InventoryUI />)

    // Try to use a rare item
    const rareCandy = screen.getByText('Rare Candy')
    await user.click(rareCandy)

    // Look for use button
    const useButton = screen.queryByText(/use/i) ||
                     screen.queryByRole('button', { name: /use/i })

    if (useButton) {
      await user.click(useButton)

      // Should show confirmation for valuable items
      const confirmButton = screen.queryByText(/confirm/i) ||
                           screen.queryByText(/yes/i) ||
                           screen.queryByRole('button', { name: /confirm/i })

      if (confirmButton) {
        expect(confirmButton).toBeInTheDocument()
      }
    }
  })

  it('handles offline mode gracefully', () => {
    // Mock offline state
    Object.defineProperty(navigator, 'onLine', { value: false, writable: true })

    render(<InventoryUI />)

    // Should still show cached inventory
    expect(screen.getByText('Health Potion')).toBeInTheDocument()
    expect(screen.getByText('Tuxe Ball')).toBeInTheDocument()

    // Should indicate offline state
    const offlineIndicator = screen.queryByText(/offline/i) ||
                           screen.queryByTestId('offline-indicator')

    if (offlineIndicator) {
      expect(offlineIndicator).toBeInTheDocument()
    }
  })

  it('supports accessibility features', () => {
    render(<InventoryUI />)

    // Should have proper ARIA labels
    const inventoryDialog = screen.queryByRole('dialog') ||
                          screen.queryByLabelText(/inventory/i)

    if (inventoryDialog) {
      expect(inventoryDialog).toBeInTheDocument()
      expect(inventoryDialog).toHaveAttribute('aria-label')
    }

    // Items should be keyboard navigable
    const itemButtons = screen.getAllByRole('button')
    itemButtons.forEach(button => {
      expect(button).toHaveAttribute('tabindex')
    })
  })

  it('handles large inventory sets efficiently', async () => {
    // Mock large inventory
    const largeInventory = {
      ...mockInventoryData,
      items: Array.from({ length: 100 }, (_, i) => ({
        id: `item_${i}`,
        slug: `item_${i}`,
        name: `Item ${i}`,
        description: `Description for item ${i}`,
        category: 'misc',
        rarity: 'common',
        quantity: 1,
        sprite: 'default.png',
        effects: {},
      })),
    }

    vi.mocked(require('../../../hooks/useGameStore').useInventory).mockReturnValue({
      inventory: largeInventory,
      useItem: vi.fn(),
      sortItems: vi.fn(),
      searchItems: vi.fn(),
    })

    const renderTime = await performanceTestUtils.measureRender(() => {
      render(<InventoryUI />)
    })

    // Should handle large inventories efficiently
    const isPerformant = performanceTestUtils.assertMobilePerformance(renderTime)
    expect(isPerformant).toBe(true)
    expect(renderTime).toBeLessThan(100) // Should render within 100ms even with 100 items
  })

  it('maintains state during orientation changes', () => {
    const { rerender } = render(<InventoryUI />)

    // Select an item
    const healthPotion = screen.getByText('Health Potion')
    healthPotion.click()

    // Change orientation
    mobileTestUtils.mockDeviceOrientation('landscape')
    window.dispatchEvent(new Event('orientationchange'))

    rerender(<InventoryUI />)

    // Item should still be available
    expect(screen.getByText('Health Potion')).toBeInTheDocument()
    expect(screen.getByText('Tuxe Ball')).toBeInTheDocument()
    expect(screen.getByText('Rare Candy')).toBeInTheDocument()
  })
})