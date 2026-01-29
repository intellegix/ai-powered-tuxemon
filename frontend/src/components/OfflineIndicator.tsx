// Offline Indicator Component for AI-Powered Tuxemon
// Austin Kidwell | Intellegix | Mobile-First Pokemon-Style Game

import React, { useState, useEffect } from 'react'
import { syncManager, type SyncProgress, type SyncEvent } from '../services/sync-manager'

interface OfflineIndicatorProps {
  className?: string
  showDetailedStatus?: boolean
}

type ConnectionStatus = 'online' | 'offline' | 'syncing' | 'sync-error'

export const OfflineIndicator: React.FC<OfflineIndicatorProps> = ({
  className = '',
  showDetailedStatus = false
}) => {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>(
    navigator.onLine ? 'online' : 'offline'
  )
  const [syncProgress, setSyncProgress] = useState<SyncProgress | null>(null)
  const [pendingActionsCount, setPendingActionsCount] = useState(0)
  const [showDetails, setShowDetails] = useState(false)

  useEffect(() => {
    // Update connection status
    const updateConnectionStatus = () => {
      setConnectionStatus(navigator.onLine ? 'online' : 'offline')
    }

    // Listen for browser online/offline events
    window.addEventListener('online', updateConnectionStatus)
    window.addEventListener('offline', updateConnectionStatus)

    // Listen for sync events from sync manager
    const handleSyncEvent = (event: SyncEvent) => {
      switch (event.type) {
        case 'start':
          setConnectionStatus('syncing')
          setSyncProgress(event.data as SyncProgress)
          break

        case 'progress':
          setSyncProgress(event.data as SyncProgress)
          break

        case 'complete':
          setConnectionStatus('online')
          setSyncProgress(null)
          // Brief success indication
          setTimeout(() => {
            setPendingActionsCount(0)
          }, 1000)
          break

        case 'error':
          setConnectionStatus('sync-error')
          setSyncProgress(null)
          // Auto-retry logic handled by sync manager
          setTimeout(() => {
            setConnectionStatus(navigator.onLine ? 'online' : 'offline')
          }, 3000)
          break
      }
    }

    // Register sync event listener
    syncManager.addEventListener(handleSyncEvent)

    // Periodically check pending actions count
    const updatePendingCount = async () => {
      try {
        const stats = await syncManager.getSyncStats()
        setPendingActionsCount(stats.pendingActions)
      } catch (error) {
        console.warn('Failed to get sync stats:', error)
      }
    }

    // Update immediately and then every 30 seconds
    updatePendingCount()
    const statsInterval = setInterval(updatePendingCount, 30000)

    // Cleanup
    return () => {
      window.removeEventListener('online', updateConnectionStatus)
      window.removeEventListener('offline', updateConnectionStatus)
      syncManager.removeEventListener(handleSyncEvent)
      clearInterval(statsInterval)
    }
  }, [])

  // Get status display info
  const getStatusInfo = () => {
    switch (connectionStatus) {
      case 'online':
        return {
          icon: '🌐',
          text: 'Online',
          color: 'text-green-600',
          bgColor: 'bg-green-100',
          description: 'Connected and synced'
        }
      case 'offline':
        return {
          icon: '📴',
          text: 'Offline',
          color: 'text-gray-600',
          bgColor: 'bg-gray-100',
          description: 'Playing offline - actions will sync when online'
        }
      case 'syncing':
        return {
          icon: '🔄',
          text: 'Syncing',
          color: 'text-blue-600',
          bgColor: 'bg-blue-100',
          description: 'Synchronizing your progress...'
        }
      case 'sync-error':
        return {
          icon: '⚠️',
          text: 'Sync Error',
          color: 'text-red-600',
          bgColor: 'bg-red-100',
          description: 'Failed to sync - will retry automatically'
        }
    }
  }

  const statusInfo = getStatusInfo()

  // Compact indicator for minimal UI space
  if (!showDetailedStatus) {
    return (
      <button
        onClick={() => setShowDetails(!showDetails)}
        className={`
          flex items-center gap-2 px-3 py-2 rounded-lg transition-all duration-200
          ${statusInfo.bgColor} ${statusInfo.color}
          hover:shadow-md active:scale-95
          ${className}
        `}
        aria-label={`Connection status: ${statusInfo.text}`}
      >
        <span className="text-lg" role="img" aria-label={statusInfo.text}>
          {statusInfo.icon}
        </span>

        {/* Show pending actions count if any */}
        {pendingActionsCount > 0 && (
          <span className="bg-orange-500 text-white text-xs px-2 py-1 rounded-full min-w-[20px] text-center">
            {pendingActionsCount}
          </span>
        )}

        {/* Sync progress indicator */}
        {connectionStatus === 'syncing' && syncProgress && (
          <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
        )}
      </button>
    )
  }

  // Detailed status panel
  return (
    <div className={`bg-white rounded-lg shadow-lg border p-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-2xl" role="img" aria-label={statusInfo.text}>
            {statusInfo.icon}
          </span>
          <div>
            <h3 className={`font-semibold ${statusInfo.color}`}>
              {statusInfo.text}
            </h3>
            <p className="text-sm text-gray-600">
              {statusInfo.description}
            </p>
          </div>
        </div>

        {/* Minimize button */}
        <button
          onClick={() => setShowDetails(false)}
          className="text-gray-400 hover:text-gray-600 p-1"
          aria-label="Minimize status"
        >
          ✕
        </button>
      </div>

      {/* Sync progress bar */}
      {syncProgress && (
        <div className="mb-3">
          <div className="flex justify-between text-sm text-gray-600 mb-1">
            <span>
              {syncProgress.currentAction || 'Preparing to sync...'}
            </span>
            <span>
              {syncProgress.completedActions} / {syncProgress.totalActions}
            </span>
          </div>

          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{
                width: `${Math.round(
                  (syncProgress.completedActions / syncProgress.totalActions) * 100
                )}%`
              }}
            />
          </div>

          {/* Sync errors */}
          {syncProgress.errors.length > 0 && (
            <div className="mt-2 p-2 bg-red-50 rounded-md">
              <p className="text-sm text-red-700 font-medium">
                Sync Issues ({syncProgress.errors.length}):
              </p>
              <ul className="text-xs text-red-600 mt-1 space-y-1">
                {syncProgress.errors.slice(-3).map((error, index) => (
                  <li key={index} className="truncate">
                    • {error}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Pending actions info */}
      {pendingActionsCount > 0 && (
        <div className="bg-orange-50 rounded-md p-3">
          <div className="flex items-center gap-2">
            <span className="text-orange-600 font-medium">
              📤 {pendingActionsCount} actions queued
            </span>
          </div>
          <p className="text-sm text-orange-700 mt-1">
            {connectionStatus === 'offline'
              ? 'Will sync when you go back online'
              : 'Syncing now...'}
          </p>
        </div>
      )}

      {/* Connection tips */}
      {connectionStatus === 'offline' && (
        <div className="bg-blue-50 rounded-md p-3 mt-3">
          <h4 className="text-sm font-medium text-blue-800 mb-1">
            💡 Offline Mode Active
          </h4>
          <ul className="text-xs text-blue-700 space-y-1">
            <li>• You can still play the game normally</li>
            <li>• Your progress is saved locally</li>
            <li>• NPCs use cached dialogue</li>
            <li>• Everything will sync when you're back online</li>
          </ul>
        </div>
      )}

      {/* Manual sync button */}
      {connectionStatus === 'online' && pendingActionsCount === 0 && (
        <button
          onClick={() => syncManager.triggerSync('Manual refresh')}
          className="w-full mt-3 py-2 px-4 bg-blue-100 text-blue-700 rounded-md text-sm font-medium hover:bg-blue-200 transition-colors"
        >
          🔄 Refresh Game Data
        </button>
      )}

      {/* Force sync button for errors */}
      {connectionStatus === 'sync-error' && (
        <button
          onClick={() => syncManager.triggerSync('Retry after error')}
          className="w-full mt-3 py-2 px-4 bg-red-100 text-red-700 rounded-md text-sm font-medium hover:bg-red-200 transition-colors"
        >
          🔄 Retry Sync
        </button>
      )}
    </div>
  )
}

// Hook for using offline status in other components
export const useOfflineStatus = () => {
  const [isOnline, setIsOnline] = useState(navigator.onLine)
  const [isSyncing, setIsSyncing] = useState(false)
  const [pendingActions, setPendingActions] = useState(0)

  useEffect(() => {
    const handleOnline = () => setIsOnline(true)
    const handleOffline = () => setIsOnline(false)

    const handleSyncEvent = (event: SyncEvent) => {
      setIsSyncing(event.type === 'start' || event.type === 'progress')
    }

    const updatePendingCount = async () => {
      try {
        const stats = await syncManager.getSyncStats()
        setPendingActions(stats.pendingActions)
      } catch (error) {
        console.warn('Failed to get sync stats:', error)
      }
    }

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)
    syncManager.addEventListener(handleSyncEvent)

    // Update pending count periodically
    updatePendingCount()
    const interval = setInterval(updatePendingCount, 30000)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
      syncManager.removeEventListener(handleSyncEvent)
      clearInterval(interval)
    }
  }, [])

  return { isOnline, isSyncing, pendingActions }
}

export default OfflineIndicator