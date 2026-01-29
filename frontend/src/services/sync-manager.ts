// Background Sync Manager for AI-Powered Tuxemon
// Austin Kidwell | Intellegix | Mobile-First Pokemon-Style Game

import { offlineStorage, type OfflineAction } from './offline-storage'
import { apiService } from './api'
import type { GameState, WorldState, Player } from '../types/game'

interface SyncProgress {
  isSync: boolean
  totalActions: number
  completedActions: number
  currentAction: string | null
  errors: string[]
}

type SyncEventType = 'start' | 'progress' | 'complete' | 'error'

interface SyncEvent {
  type: SyncEventType
  data: SyncProgress | string
}

class SyncManager {
  private isOnline: boolean = navigator.onLine
  private isSyncing: boolean = false
  private syncInterval: number | null = null
  private retryTimeout: number | null = null
  private eventListeners: Set<(event: SyncEvent) => void> = new Set()

  // Configuration
  private readonly SYNC_INTERVAL = 30000 // 30 seconds
  private readonly RETRY_DELAY = 5000 // 5 seconds
  private readonly MAX_BATCH_SIZE = 10 // Process 10 actions per batch

  constructor() {
    this.setupOnlineDetection()
    this.startPeriodicSync()
  }

  private setupOnlineDetection(): void {
    // Listen for online/offline events
    window.addEventListener('online', () => {
      console.log('🌐 Connection restored')
      this.isOnline = true
      this.triggerSync('Connection restored')
    })

    window.addEventListener('offline', () => {
      console.log('📴 Connection lost - entering offline mode')
      this.isOnline = false
      this.stopSync()
    })

    // Initial connection state
    this.isOnline = navigator.onLine
  }

  private startPeriodicSync(): void {
    if (this.syncInterval) {
      clearInterval(this.syncInterval)
    }

    this.syncInterval = window.setInterval(() => {
      if (this.isOnline && !this.isSyncing) {
        this.syncPendingActions()
      }
    }, this.SYNC_INTERVAL)
  }

  private stopSync(): void {
    if (this.syncInterval) {
      clearInterval(this.syncInterval)
      this.syncInterval = null
    }

    if (this.retryTimeout) {
      clearTimeout(this.retryTimeout)
      this.retryTimeout = null
    }
  }

  // Event system
  public addEventListener(callback: (event: SyncEvent) => void): void {
    this.eventListeners.add(callback)
  }

  public removeEventListener(callback: (event: SyncEvent) => void): void {
    this.eventListeners.delete(callback)
  }

  private emitEvent(type: SyncEventType, data: any): void {
    const event: SyncEvent = { type, data }
    this.eventListeners.forEach(callback => {
      try {
        callback(event)
      } catch (error) {
        console.error('Sync event listener error:', error)
      }
    })
  }

  // Main sync functionality
  public async triggerSync(reason?: string): Promise<void> {
    if (!this.isOnline) {
      console.log('📴 Cannot sync - offline')
      return
    }

    if (this.isSyncing) {
      console.log('🔄 Sync already in progress')
      return
    }

    console.log(`🔄 Starting sync${reason ? ` - ${reason}` : ''}`)
    await this.syncPendingActions()
  }

  private async syncPendingActions(): Promise<void> {
    try {
      this.isSyncing = true

      const pendingActions = await offlineStorage.getPendingActions()

      if (pendingActions.length === 0) {
        console.log('✅ No actions to sync')
        this.isSyncing = false
        return
      }

      console.log(`🔄 Syncing ${pendingActions.length} pending actions`)

      const syncProgress: SyncProgress = {
        isSync: true,
        totalActions: pendingActions.length,
        completedActions: 0,
        currentAction: null,
        errors: []
      }

      this.emitEvent('start', syncProgress)

      // Process actions in batches to avoid overwhelming the server
      const batches = this.chunkArray(pendingActions, this.MAX_BATCH_SIZE)

      for (const batch of batches) {
        await this.processBatch(batch, syncProgress)

        // Add small delay between batches to be server-friendly
        if (batches.length > 1) {
          await this.delay(1000)
        }
      }

      if (syncProgress.errors.length > 0) {
        console.warn(`⚠️ Sync completed with ${syncProgress.errors.length} errors`)
        this.emitEvent('error', syncProgress)
      } else {
        console.log('✅ All actions synced successfully')
        this.emitEvent('complete', syncProgress)
      }

    } catch (error) {
      console.error('❌ Sync failed:', error)
      this.emitEvent('error', `Sync failed: ${error}`)

      // Retry after delay
      this.scheduleRetry()
    } finally {
      this.isSyncing = false
    }
  }

  private async processBatch(batch: OfflineAction[], progress: SyncProgress): Promise<void> {
    for (const action of batch) {
      try {
        progress.currentAction = `${action.type}: ${action.id.slice(-8)}`
        this.emitEvent('progress', progress)

        await this.syncAction(action)
        await offlineStorage.removeOfflineAction(action.id)

        progress.completedActions++
        console.log(`✅ Synced action: ${action.type} (${action.id})`)

      } catch (error) {
        console.error(`❌ Failed to sync action ${action.id}:`, error)

        // Update retry count
        const newRetryCount = action.retryCount + 1

        if (newRetryCount >= action.maxRetries) {
          // Remove failed action after max retries
          await offlineStorage.removeOfflineAction(action.id)
          progress.errors.push(`Max retries exceeded for ${action.type} action`)
          console.warn(`🗑️ Removed failed action after ${action.maxRetries} retries: ${action.id}`)
        } else {
          // Update retry count for next attempt
          await offlineStorage.updateActionRetryCount(action.id, newRetryCount)
          progress.errors.push(`Retry ${newRetryCount}/${action.maxRetries} for ${action.type} action`)
        }

        progress.completedActions++
      }
    }
  }

  private async syncAction(action: OfflineAction): Promise<void> {
    switch (action.type) {
      case 'move':
        await this.syncMoveAction(action)
        break

      case 'interact':
        await this.syncInteractAction(action)
        break

      case 'combat':
        await this.syncCombatAction(action)
        break

      case 'inventory':
        await this.syncInventoryAction(action)
        break

      case 'dialogue':
        await this.syncDialogueAction(action)
        break

      default:
        throw new Error(`Unknown action type: ${action.type}`)
    }
  }

  private async syncMoveAction(action: OfflineAction): Promise<void> {
    const { x, y, mapName } = action.payload

    // Validate move is still valid (basic check)
    if (typeof x !== 'number' || typeof y !== 'number' || !mapName) {
      throw new Error('Invalid move action payload')
    }

    // Send move to server (assuming API endpoint exists)
    await apiService.post('/game/move', {
      position_x: x,
      position_y: y,
      map_name: mapName,
      timestamp: action.timestamp
    })
  }

  private async syncInteractAction(action: OfflineAction): Promise<void> {
    const { npcId, interactionType } = action.payload

    // Send interaction to server
    await apiService.post(`/npcs/${npcId}/interact`, {
      interaction_type: interactionType,
      timestamp: action.timestamp
    })
  }

  private async syncCombatAction(action: OfflineAction): Promise<void> {
    const { battleId, combatAction } = action.payload

    // Send combat action to server
    await apiService.post('/combat/action', {
      battle_id: battleId,
      action: combatAction,
      timestamp: action.timestamp
    })
  }

  private async syncInventoryAction(action: OfflineAction): Promise<void> {
    const { actionType, itemSlug, quantity, targetId } = action.payload

    switch (actionType) {
      case 'use':
        await apiService.post('/inventory/use', {
          item_slug: itemSlug,
          quantity: quantity || 1,
          target_monster_id: targetId,
          timestamp: action.timestamp
        })
        break

      default:
        throw new Error(`Unknown inventory action: ${actionType}`)
    }
  }

  private async syncDialogueAction(action: OfflineAction): Promise<void> {
    const { npcId, message, context } = action.payload

    // Send dialogue response to server for AI learning
    await apiService.post(`/npcs/${npcId}/dialogue/feedback`, {
      message,
      context,
      timestamp: action.timestamp
    })
  }

  // Background sync with service worker (when supported)
  public async registerBackgroundSync(): Promise<void> {
    if ('serviceWorker' in navigator && 'sync' in window.ServiceWorkerRegistration.prototype) {
      try {
        const registration = await navigator.serviceWorker.ready
        await registration.sync.register('game-sync')
        console.log('✅ Background sync registered')
      } catch (error) {
        console.warn('⚠️ Background sync registration failed:', error)
      }
    }
  }

  // Force sync all data (for manual refresh)
  public async forceFullSync(): Promise<void> {
    if (!this.isOnline) {
      throw new Error('Cannot sync while offline')
    }

    console.log('🔄 Starting full sync...')

    try {
      // Sync pending actions
      await this.syncPendingActions()

      // Sync game state
      const gameState = await offlineStorage.loadGameState()
      if (gameState?.player) {
        await apiService.post('/game/sync', {
          player_state: gameState.player,
          game_state: gameState.gameState,
          last_sync: gameState.lastSyncTimestamp
        })
      }

      console.log('✅ Full sync completed')

    } catch (error) {
      console.error('❌ Full sync failed:', error)
      throw error
    }
  }

  // Utility methods
  private chunkArray<T>(array: T[], size: number): T[][] {
    const chunks: T[][] = []
    for (let i = 0; i < array.length; i += size) {
      chunks.push(array.slice(i, i + size))
    }
    return chunks
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms))
  }

  private scheduleRetry(): void {
    if (this.retryTimeout) {
      clearTimeout(this.retryTimeout)
    }

    this.retryTimeout = window.setTimeout(() => {
      if (this.isOnline && !this.isSyncing) {
        console.log('🔄 Retrying sync...')
        this.syncPendingActions()
      }
    }, this.RETRY_DELAY)
  }

  // Public getters
  public get online(): boolean {
    return this.isOnline
  }

  public get syncing(): boolean {
    return this.isSyncing
  }

  public async getSyncStats(): Promise<{
    isOnline: boolean
    isSyncing: boolean
    pendingActions: number
    lastSyncAttempt: number | null
  }> {
    const pendingActions = await offlineStorage.getPendingActions()

    return {
      isOnline: this.isOnline,
      isSyncing: this.isSyncing,
      pendingActions: pendingActions.length,
      lastSyncAttempt: null // Could be stored in localStorage
    }
  }

  // Cleanup
  public destroy(): void {
    this.stopSync()
    this.eventListeners.clear()

    window.removeEventListener('online', this.triggerSync)
    window.removeEventListener('offline', this.stopSync)
  }
}

// Create singleton instance
export const syncManager = new SyncManager()

// Export types
export type { SyncProgress, SyncEvent, SyncEventType }