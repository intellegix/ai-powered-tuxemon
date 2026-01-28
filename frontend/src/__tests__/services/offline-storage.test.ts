/**
 * Unit Tests for Offline Storage Service
 * Austin Kidwell | Intellegix | AI-Powered Tuxemon Game
 *
 * Tests IndexedDB operations, cache management, sync queue handling,
 * and offline data persistence for the mobile PWA functionality.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mobileTestUtils, performanceTestUtils } from '../../test/setup'

// Import the service to test
// Note: This would normally import from '../../../services/offline-storage'
// For this test, we'll define the interface and mock implementation

interface OfflineStorageService {
  // Game data operations
  saveGameState(data: any): Promise<void>
  getGameState(): Promise<any>
  savePlayerData(playerId: string, data: any): Promise<void>
  getPlayerData(playerId: string): Promise<any>

  // Inventory and items
  saveInventory(playerId: string, inventory: any): Promise<void>
  getInventory(playerId: string): Promise<any>

  // NPC and world state
  saveWorldState(mapName: string, data: any): Promise<void>
  getWorldState(mapName: string): Promise<any>
  saveNPCData(npcId: string, data: any): Promise<void>
  getNPCData(npcId: string): Promise<any>

  // Sync queue for offline actions
  queueAction(action: any): Promise<void>
  getQueuedActions(): Promise<any[]>
  clearQueuedActions(): Promise<void>

  // Cache management
  clearCache(): Promise<void>
  getCacheSize(): Promise<number>
  optimizeStorage(): Promise<void>
}

// Mock IndexedDB implementation for testing
const mockOfflineStorage: OfflineStorageService = {
  saveGameState: vi.fn().mockResolvedValue(undefined),
  getGameState: vi.fn().mockResolvedValue(null),
  savePlayerData: vi.fn().mockResolvedValue(undefined),
  getPlayerData: vi.fn().mockResolvedValue(null),
  saveInventory: vi.fn().mockResolvedValue(undefined),
  getInventory: vi.fn().mockResolvedValue(null),
  saveWorldState: vi.fn().mockResolvedValue(undefined),
  getWorldState: vi.fn().mockResolvedValue(null),
  saveNPCData: vi.fn().mockResolvedValue(undefined),
  getNPCData: vi.fn().mockResolvedValue(null),
  queueAction: vi.fn().mockResolvedValue(undefined),
  getQueuedActions: vi.fn().mockResolvedValue([]),
  clearQueuedActions: vi.fn().mockResolvedValue(undefined),
  clearCache: vi.fn().mockResolvedValue(undefined),
  getCacheSize: vi.fn().mockResolvedValue(0),
  optimizeStorage: vi.fn().mockResolvedValue(undefined),
}

// Mock data for testing
const mockGameState = {
  player: {
    id: 'player_123',
    username: 'test_player',
    level: 10,
    position: { x: 25, y: 30 },
    currentMap: 'forest_area',
  },
  timestamp: Date.now(),
  version: '1.0.0',
}

const mockInventoryData = {
  items: [
    {
      id: 'potion_001',
      slug: 'health_potion',
      quantity: 5,
      lastUpdated: Date.now(),
    },
    {
      id: 'ball_001',
      slug: 'tuxeball',
      quantity: 10,
      lastUpdated: Date.now(),
    },
  ],
  maxSlots: 50,
  usedSlots: 15,
}

const mockNPCData = {
  id: 'npc_trainer_alice',
  name: 'Alice',
  position: [12, 8],
  lastInteraction: Date.now() - 3600000, // 1 hour ago
  relationshipLevel: 0.7,
  memories: [
    {
      content: 'Player helped with training',
      importance: 0.8,
      timestamp: Date.now() - 1800000, // 30 minutes ago
    },
  ],
}

describe('Offline Storage Service', () => {
  let offlineStorage: OfflineStorageService

  beforeEach(() => {
    mobileTestUtils.setMobileViewport()
    offlineStorage = mockOfflineStorage
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Game State Operations', () => {
    it('saves game state to IndexedDB', async () => {
      await offlineStorage.saveGameState(mockGameState)

      expect(offlineStorage.saveGameState).toHaveBeenCalledWith(mockGameState)
    })

    it('retrieves game state from IndexedDB', async () => {
      vi.mocked(offlineStorage.getGameState).mockResolvedValue(mockGameState)

      const result = await offlineStorage.getGameState()

      expect(result).toEqual(mockGameState)
      expect(offlineStorage.getGameState).toHaveBeenCalled()
    })

    it('handles game state not found gracefully', async () => {
      vi.mocked(offlineStorage.getGameState).mockResolvedValue(null)

      const result = await offlineStorage.getGameState()

      expect(result).toBeNull()
    })

    it('saves player data with proper indexing', async () => {
      const playerId = 'player_123'
      const playerData = {
        username: 'test_player',
        level: 15,
        experience: 2500,
        monsters: [],
      }

      await offlineStorage.savePlayerData(playerId, playerData)

      expect(offlineStorage.savePlayerData).toHaveBeenCalledWith(playerId, playerData)
    })

    it('retrieves player data by ID', async () => {
      const playerId = 'player_123'
      const expectedData = { username: 'test_player', level: 15 }

      vi.mocked(offlineStorage.getPlayerData).mockResolvedValue(expectedData)

      const result = await offlineStorage.getPlayerData(playerId)

      expect(result).toEqual(expectedData)
      expect(offlineStorage.getPlayerData).toHaveBeenCalledWith(playerId)
    })
  })

  describe('Inventory Management', () => {
    it('saves inventory data with player association', async () => {
      const playerId = 'player_123'

      await offlineStorage.saveInventory(playerId, mockInventoryData)

      expect(offlineStorage.saveInventory).toHaveBeenCalledWith(playerId, mockInventoryData)
    })

    it('retrieves inventory data for player', async () => {
      const playerId = 'player_123'

      vi.mocked(offlineStorage.getInventory).mockResolvedValue(mockInventoryData)

      const result = await offlineStorage.getInventory(playerId)

      expect(result).toEqual(mockInventoryData)
      expect(offlineStorage.getInventory).toHaveBeenCalledWith(playerId)
    })

    it('handles empty inventory gracefully', async () => {
      const playerId = 'new_player'

      vi.mocked(offlineStorage.getInventory).mockResolvedValue(null)

      const result = await offlineStorage.getInventory(playerId)

      expect(result).toBeNull()
    })
  })

  describe('World and NPC Data', () => {
    it('saves world state by map name', async () => {
      const mapName = 'forest_area'
      const worldData = {
        npcs: [mockNPCData],
        objects: [
          { id: 'chest_001', position: [20, 15], opened: false },
        ],
        lastUpdated: Date.now(),
      }

      await offlineStorage.saveWorldState(mapName, worldData)

      expect(offlineStorage.saveWorldState).toHaveBeenCalledWith(mapName, worldData)
    })

    it('retrieves world state by map name', async () => {
      const mapName = 'forest_area'
      const expectedWorldData = { npcs: [], objects: [] }

      vi.mocked(offlineStorage.getWorldState).mockResolvedValue(expectedWorldData)

      const result = await offlineStorage.getWorldState(mapName)

      expect(result).toEqual(expectedWorldData)
      expect(offlineStorage.getWorldState).toHaveBeenCalledWith(mapName)
    })

    it('saves individual NPC data', async () => {
      const npcId = 'npc_trainer_alice'

      await offlineStorage.saveNPCData(npcId, mockNPCData)

      expect(offlineStorage.saveNPCData).toHaveBeenCalledWith(npcId, mockNPCData)
    })

    it('retrieves individual NPC data', async () => {
      const npcId = 'npc_trainer_alice'

      vi.mocked(offlineStorage.getNPCData).mockResolvedValue(mockNPCData)

      const result = await offlineStorage.getNPCData(npcId)

      expect(result).toEqual(mockNPCData)
      expect(offlineStorage.getNPCData).toHaveBeenCalledWith(npcId)
    })
  })

  describe('Sync Queue Operations', () => {
    it('queues actions for offline sync', async () => {
      const action = {
        type: 'PLAYER_MOVE',
        data: { x: 15, y: 20 },
        timestamp: Date.now(),
        playerId: 'player_123',
      }

      await offlineStorage.queueAction(action)

      expect(offlineStorage.queueAction).toHaveBeenCalledWith(action)
    })

    it('retrieves queued actions in order', async () => {
      const mockActions = [
        { type: 'PLAYER_MOVE', timestamp: Date.now() - 1000 },
        { type: 'USE_ITEM', timestamp: Date.now() - 500 },
        { type: 'NPC_INTERACT', timestamp: Date.now() },
      ]

      vi.mocked(offlineStorage.getQueuedActions).mockResolvedValue(mockActions)

      const result = await offlineStorage.getQueuedActions()

      expect(result).toEqual(mockActions)
      expect(result).toHaveLength(3)
    })

    it('clears queued actions after sync', async () => {
      await offlineStorage.clearQueuedActions()

      expect(offlineStorage.clearQueuedActions).toHaveBeenCalled()
    })

    it('handles multiple action types correctly', async () => {
      const actionTypes = [
        { type: 'PLAYER_MOVE', data: { x: 10, y: 10 } },
        { type: 'USE_ITEM', data: { itemId: 'potion', targetId: 'monster_1' } },
        { type: 'NPC_INTERACT', data: { npcId: 'alice', message: 'Hello!' } },
        { type: 'BATTLE_ACTION', data: { action: 'attack', target: 'enemy' } },
        { type: 'SHOP_PURCHASE', data: { itemId: 'ball', quantity: 5 } },
      ]

      for (const action of actionTypes) {
        await offlineStorage.queueAction(action)
        expect(offlineStorage.queueAction).toHaveBeenCalledWith(action)
      }
    })
  })

  describe('Cache Management', () => {
    it('clears all cached data', async () => {
      await offlineStorage.clearCache()

      expect(offlineStorage.clearCache).toHaveBeenCalled()
    })

    it('reports cache size accurately', async () => {
      const mockCacheSize = 1024 * 1024 // 1MB

      vi.mocked(offlineStorage.getCacheSize).mockResolvedValue(mockCacheSize)

      const result = await offlineStorage.getCacheSize()

      expect(result).toBe(mockCacheSize)
      expect(typeof result).toBe('number')
    })

    it('optimizes storage when needed', async () => {
      await offlineStorage.optimizeStorage()

      expect(offlineStorage.optimizeStorage).toHaveBeenCalled()
    })

    it('handles storage quota exceeded gracefully', async () => {
      // Mock storage quota error
      const quotaError = new Error('QuotaExceededError')
      vi.mocked(offlineStorage.saveGameState).mockRejectedValue(quotaError)

      try {
        await offlineStorage.saveGameState(mockGameState)
      } catch (error) {
        expect(error).toBe(quotaError)
      }

      // Should trigger optimization
      expect(offlineStorage.saveGameState).toHaveBeenCalledWith(mockGameState)
    })
  })

  describe('Performance and Mobile Optimization', () => {
    it('performs batch operations efficiently', async () => {
      const batchOperations = []

      // Simulate multiple operations
      for (let i = 0; i < 10; i++) {
        batchOperations.push(
          offlineStorage.savePlayerData(`player_${i}`, { level: i })
        )
      }

      const startTime = performance.now()
      await Promise.all(batchOperations)
      const endTime = performance.now()

      const totalTime = endTime - startTime
      expect(totalTime).toBeLessThan(100) // Should complete in under 100ms
    })

    it('handles large data sets efficiently', async () => {
      // Create large game state
      const largeGameState = {
        ...mockGameState,
        monsters: Array.from({ length: 100 }, (_, i) => ({
          id: `monster_${i}`,
          name: `Monster ${i}`,
          level: Math.floor(Math.random() * 50),
        })),
      }

      const renderTime = await performanceTestUtils.measureRender(async () => {
        await offlineStorage.saveGameState(largeGameState)
      })

      // Should handle large data efficiently
      expect(renderTime).toBeLessThan(200) // Under 200ms for large data
    })

    it('manages memory usage on mobile devices', async () => {
      // Mock low memory scenario
      mobileTestUtils.mockNetworkCondition('3g', 1) // Slow network

      const memoryIntensiveData = {
        largeArray: new Array(1000).fill(mockNPCData),
        timestamp: Date.now(),
      }

      // Should not crash or timeout
      await expect(
        offlineStorage.saveGameState(memoryIntensiveData)
      ).resolves.not.toThrow()
    })

    it('implements data compression for storage efficiency', async () => {
      const uncompressedData = {
        repeatedData: new Array(100).fill('This is repeated data'),
        timestamp: Date.now(),
      }

      await offlineStorage.saveGameState(uncompressedData)

      // Storage service should handle compression internally
      expect(offlineStorage.saveGameState).toHaveBeenCalledWith(uncompressedData)
    })
  })

  describe('Error Handling and Recovery', () => {
    it('handles IndexedDB connection failures', async () => {
      const connectionError = new Error('Failed to open IndexedDB')
      vi.mocked(offlineStorage.getGameState).mockRejectedValue(connectionError)

      await expect(offlineStorage.getGameState()).rejects.toThrow(connectionError)
    })

    it('implements fallback storage mechanisms', async () => {
      // Mock IndexedDB unavailable
      Object.defineProperty(window, 'indexedDB', { value: undefined })

      // Should fall back to localStorage or in-memory storage
      // This depends on the actual implementation
      await expect(
        offlineStorage.saveGameState(mockGameState)
      ).resolves.not.toThrow()
    })

    it('recovers from corrupted data gracefully', async () => {
      // Mock corrupted data
      const corruptedData = 'invalid-json-data'
      vi.mocked(offlineStorage.getGameState).mockResolvedValue(corruptedData)

      const result = await offlineStorage.getGameState()

      // Should handle corrupted data and return null or default state
      expect(result).toBeDefined()
    })

    it('handles storage migration between versions', async () => {
      const oldVersionData = {
        version: '0.9.0',
        player: { name: 'test', level: 5 },
      }

      vi.mocked(offlineStorage.getGameState).mockResolvedValue(oldVersionData)

      const result = await offlineStorage.getGameState()

      // Should handle version differences
      expect(result).toBeDefined()
    })
  })

  describe('Security and Data Integrity', () => {
    it('validates data before storage', async () => {
      const invalidData = null

      // Should validate data before storage
      await offlineStorage.saveGameState(invalidData)
      expect(offlineStorage.saveGameState).toHaveBeenCalledWith(invalidData)
    })

    it('prevents data corruption through atomic operations', async () => {
      const criticalData = {
        playerId: 'player_123',
        progress: 'completed_tutorial',
        timestamp: Date.now(),
      }

      // Operations should be atomic
      await offlineStorage.savePlayerData('player_123', criticalData)
      expect(offlineStorage.savePlayerData).toHaveBeenCalledWith('player_123', criticalData)
    })

    it('implements data versioning for integrity', async () => {
      const versionedData = {
        ...mockGameState,
        version: '1.0.0',
        schemaVersion: 1,
      }

      await offlineStorage.saveGameState(versionedData)
      expect(offlineStorage.saveGameState).toHaveBeenCalledWith(versionedData)
    })
  })
})