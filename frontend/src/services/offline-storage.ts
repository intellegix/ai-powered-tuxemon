// IndexedDB Offline Storage for AI-Powered Tuxemon
// Austin Kidwell | Intellegix | Mobile-First Pokemon-Style Game

import type {
  Player,
  GameState,
  WorldState,
  Monster,
  NPC,
  DialogueResponse,
} from '../types/game'

interface OfflineAction {
  id: string
  type: 'move' | 'interact' | 'combat' | 'inventory' | 'dialogue'
  payload: any
  timestamp: number
  retryCount: number
  maxRetries: number
}

interface OfflineGameData {
  player: Player | null
  gameState: GameState | null
  worldState: WorldState | null
  lastSyncTimestamp: number
  cachedNPCs: Record<string, NPC>
  cachedDialogue: Record<string, DialogueResponse>
  pendingActions: OfflineAction[]
}

class OfflineStorageService {
  private dbName = 'TuxemonOfflineDB'
  private dbVersion = 1
  private db: IDBDatabase | null = null

  async initialize(): Promise<void> {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, this.dbVersion)

      request.onerror = () => {
        console.error('❌ Failed to open IndexedDB')
        reject(new Error('Failed to open IndexedDB'))
      }

      request.onsuccess = (event) => {
        this.db = (event.target as IDBOpenDBRequest).result
        console.log('✅ IndexedDB initialized for offline storage')
        resolve()
      }

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result

        // Game state store
        if (!db.objectStoreNames.contains('gameState')) {
          db.createObjectStore('gameState', { keyPath: 'id' })
        }

        // Cached NPCs store
        if (!db.objectStoreNames.contains('npcs')) {
          const npcStore = db.createObjectStore('npcs', { keyPath: 'id' })
          npcStore.createIndex('map_name', 'map_name', { unique: false })
        }

        // Cached dialogue store
        if (!db.objectStoreNames.contains('dialogue')) {
          const dialogueStore = db.createObjectStore('dialogue', { keyPath: 'npc_id' })
          dialogueStore.createIndex('timestamp', 'timestamp', { unique: false })
        }

        // Offline actions queue
        if (!db.objectStoreNames.contains('offlineActions')) {
          const actionsStore = db.createObjectStore('offlineActions', { keyPath: 'id' })
          actionsStore.createIndex('timestamp', 'timestamp', { unique: false })
          actionsStore.createIndex('type', 'type', { unique: false })
        }

        // Player assets (sprites, audio) cache
        if (!db.objectStoreNames.contains('assets')) {
          db.createObjectStore('assets', { keyPath: 'url' })
        }
      }
    })
  }

  // Game State Persistence
  async saveGameState(gameData: OfflineGameData): Promise<void> {
    if (!this.db) throw new Error('Database not initialized')

    const transaction = this.db.transaction(['gameState'], 'readwrite')
    const store = transaction.objectStore('gameState')

    await new Promise<void>((resolve, reject) => {
      const request = store.put({
        id: 'current',
        ...gameData,
        savedAt: Date.now()
      })

      request.onsuccess = () => resolve()
      request.onerror = () => reject(new Error('Failed to save game state'))
    })
  }

  async loadGameState(): Promise<OfflineGameData | null> {
    if (!this.db) throw new Error('Database not initialized')

    const transaction = this.db.transaction(['gameState'], 'readonly')
    const store = transaction.objectStore('gameState')

    return new Promise((resolve, reject) => {
      const request = store.get('current')

      request.onsuccess = () => {
        const result = request.result
        if (result) {
          const { id, savedAt, ...gameData } = result
          resolve(gameData as OfflineGameData)
        } else {
          resolve(null)
        }
      }

      request.onerror = () => reject(new Error('Failed to load game state'))
    })
  }

  // NPC Caching
  async cacheNPC(npc: NPC): Promise<void> {
    if (!this.db) throw new Error('Database not initialized')

    const transaction = this.db.transaction(['npcs'], 'readwrite')
    const store = transaction.objectStore('npcs')

    await new Promise<void>((resolve, reject) => {
      const request = store.put({
        ...npc,
        cachedAt: Date.now()
      })

      request.onsuccess = () => resolve()
      request.onerror = () => reject(new Error('Failed to cache NPC'))
    })
  }

  async getCachedNPCs(mapName?: string): Promise<NPC[]> {
    if (!this.db) throw new Error('Database not initialized')

    const transaction = this.db.transaction(['npcs'], 'readonly')
    const store = transaction.objectStore('npcs')

    return new Promise((resolve, reject) => {
      let request: IDBRequest

      if (mapName) {
        const index = store.index('map_name')
        request = index.getAll(mapName)
      } else {
        request = store.getAll()
      }

      request.onsuccess = () => {
        const npcs = request.result.map((item: any) => {
          const { cachedAt, ...npc } = item
          return npc as NPC
        })
        resolve(npcs)
      }

      request.onerror = () => reject(new Error('Failed to get cached NPCs'))
    })
  }

  // Dialogue Caching
  async cacheDialogue(npcId: string, dialogue: DialogueResponse): Promise<void> {
    if (!this.db) throw new Error('Database not initialized')

    const transaction = this.db.transaction(['dialogue'], 'readwrite')
    const store = transaction.objectStore('dialogue')

    await new Promise<void>((resolve, reject) => {
      const request = store.put({
        npc_id: npcId,
        dialogue,
        cachedAt: Date.now()
      })

      request.onsuccess = () => resolve()
      request.onerror = () => reject(new Error('Failed to cache dialogue'))
    })
  }

  async getCachedDialogue(npcId: string): Promise<DialogueResponse | null> {
    if (!this.db) throw new Error('Database not initialized')

    const transaction = this.db.transaction(['dialogue'], 'readonly')
    const store = transaction.objectStore('dialogue')

    return new Promise((resolve, reject) => {
      const request = store.get(npcId)

      request.onsuccess = () => {
        const result = request.result
        if (result) {
          // Check if dialogue is not too old (max 1 hour)
          const maxAge = 60 * 60 * 1000 // 1 hour
          if (Date.now() - result.cachedAt < maxAge) {
            resolve(result.dialogue)
          } else {
            resolve(null)
          }
        } else {
          resolve(null)
        }
      }

      request.onerror = () => reject(new Error('Failed to get cached dialogue'))
    })
  }

  // Offline Actions Queue
  async queueOfflineAction(action: Omit<OfflineAction, 'id' | 'timestamp'>): Promise<string> {
    if (!this.db) throw new Error('Database not initialized')

    const actionId = `action_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    const fullAction: OfflineAction = {
      id: actionId,
      timestamp: Date.now(),
      ...action
    }

    const transaction = this.db.transaction(['offlineActions'], 'readwrite')
    const store = transaction.objectStore('offlineActions')

    await new Promise<void>((resolve, reject) => {
      const request = store.put(fullAction)
      request.onsuccess = () => resolve()
      request.onerror = () => reject(new Error('Failed to queue offline action'))
    })

    console.log(`📤 Queued offline action: ${action.type}`, fullAction)
    return actionId
  }

  async getPendingActions(): Promise<OfflineAction[]> {
    if (!this.db) throw new Error('Database not initialized')

    const transaction = this.db.transaction(['offlineActions'], 'readonly')
    const store = transaction.objectStore('offlineActions')

    return new Promise((resolve, reject) => {
      const request = store.getAll()

      request.onsuccess = () => {
        const actions = request.result.sort((a, b) => a.timestamp - b.timestamp)
        resolve(actions)
      }

      request.onerror = () => reject(new Error('Failed to get pending actions'))
    })
  }

  async removeOfflineAction(actionId: string): Promise<void> {
    if (!this.db) throw new Error('Database not initialized')

    const transaction = this.db.transaction(['offlineActions'], 'readwrite')
    const store = transaction.objectStore('offlineActions')

    await new Promise<void>((resolve, reject) => {
      const request = store.delete(actionId)
      request.onsuccess = () => resolve()
      request.onerror = () => reject(new Error('Failed to remove offline action'))
    })
  }

  async updateActionRetryCount(actionId: string, retryCount: number): Promise<void> {
    if (!this.db) throw new Error('Database not initialized')

    const transaction = this.db.transaction(['offlineActions'], 'readwrite')
    const store = transaction.objectStore('offlineActions')

    const getRequest = store.get(actionId)
    getRequest.onsuccess = () => {
      const action = getRequest.result
      if (action) {
        action.retryCount = retryCount
        store.put(action)
      }
    }
  }

  // Asset Caching
  async cacheAsset(url: string, blob: Blob): Promise<void> {
    if (!this.db) throw new Error('Database not initialized')

    const transaction = this.db.transaction(['assets'], 'readwrite')
    const store = transaction.objectStore('assets')

    await new Promise<void>((resolve, reject) => {
      const request = store.put({
        url,
        blob,
        cachedAt: Date.now()
      })

      request.onsuccess = () => resolve()
      request.onerror = () => reject(new Error('Failed to cache asset'))
    })
  }

  async getCachedAsset(url: string): Promise<Blob | null> {
    if (!this.db) throw new Error('Database not initialized')

    const transaction = this.db.transaction(['assets'], 'readonly')
    const store = transaction.objectStore('assets')

    return new Promise((resolve, reject) => {
      const request = store.get(url)

      request.onsuccess = () => {
        const result = request.result
        if (result) {
          resolve(result.blob)
        } else {
          resolve(null)
        }
      }

      request.onerror = () => reject(new Error('Failed to get cached asset'))
    })
  }

  // Storage Management
  async clearExpiredData(): Promise<void> {
    if (!this.db) throw new Error('Database not initialized')

    const oneDayAgo = Date.now() - 24 * 60 * 60 * 1000

    // Clear old dialogue cache
    const dialogueTransaction = this.db.transaction(['dialogue'], 'readwrite')
    const dialogueStore = dialogueTransaction.objectStore('dialogue')
    const dialogueIndex = dialogueStore.index('timestamp')

    const dialogueRange = IDBKeyRange.upperBound(oneDayAgo)
    dialogueIndex.openCursor(dialogueRange).onsuccess = (event) => {
      const cursor = (event.target as IDBRequest).result
      if (cursor) {
        cursor.delete()
        cursor.continue()
      }
    }

    // Clear failed actions (over max retries)
    const actionsTransaction = this.db.transaction(['offlineActions'], 'readwrite')
    const actionsStore = actionsTransaction.objectStore('offlineActions')

    actionsStore.openCursor().onsuccess = (event) => {
      const cursor = (event.target as IDBRequest).result
      if (cursor) {
        const action = cursor.value
        if (action.retryCount >= action.maxRetries) {
          cursor.delete()
        }
        cursor.continue()
      }
    }

    console.log('🧹 Cleared expired offline data')
  }

  async getStorageStats(): Promise<{
    gameStateSize: number
    npcCount: number
    dialogueCount: number
    pendingActionsCount: number
    assetCount: number
  }> {
    if (!this.db) throw new Error('Database not initialized')

    const [gameState, npcs, dialogue, actions, assets] = await Promise.all([
      this.countRecords('gameState'),
      this.countRecords('npcs'),
      this.countRecords('dialogue'),
      this.countRecords('offlineActions'),
      this.countRecords('assets'),
    ])

    return {
      gameStateSize: gameState,
      npcCount: npcs,
      dialogueCount: dialogue,
      pendingActionsCount: actions,
      assetCount: assets,
    }
  }

  private async countRecords(storeName: string): Promise<number> {
    if (!this.db) return 0

    const transaction = this.db.transaction([storeName], 'readonly')
    const store = transaction.objectStore(storeName)

    return new Promise((resolve, reject) => {
      const request = store.count()
      request.onsuccess = () => resolve(request.result)
      request.onerror = () => reject(new Error(`Failed to count ${storeName}`))
    })
  }
}

// Create singleton instance
export const offlineStorage = new OfflineStorageService()

// Export types
export type { OfflineAction, OfflineGameData }