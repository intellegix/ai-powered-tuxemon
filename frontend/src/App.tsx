// Main App Component for AI-Powered Tuxemon Frontend
// Austin Kidwell | Intellegix | Mobile-First Pokemon-Style Game

import React, { useEffect, useState } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'

// Hooks and services
import { useGameStore, useAuth, useUI, useConnection } from './hooks/useGameStore'
import { webSocketService } from './services/websocket'
import { apiService } from './services/api'

// Components
import GameCanvas from './components/GameCanvas'
import DialogSystem from './components/DialogSystem'
import LoadingScreen from './components/LoadingScreen'
import LoginScreen from './components/LoginScreen'
import GameHUD from './components/GameHUD'
import NotificationSystem from './components/NotificationSystem'
import InventoryUI from './components/InventoryUI'
import ShopUI from './components/ShopUI'

// Types
import type { NPC } from './types/game'

// Create React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error: any) => {
        if (error?.response?.status === 401 || error?.response?.status === 403) {
          return false
        }
        return failureCount < 3
      },
      staleTime: 1000 * 60 * 5, // 5 minutes
      gcTime: 1000 * 60 * 30, // 30 minutes
    },
    mutations: {
      retry: false,
    },
  },
})

const App: React.FC = () => {
  const { isAuthenticated, authToken, player } = useAuth()
  const { ui, setLoading, setError } = useUI()
  const { isConnected, setConnected } = useConnection()

  // Local state
  const [isInitialized, setIsInitialized] = useState(false)
  const [dialogNPC, setDialogNPC] = useState<NPC | null>(null)
  const [showDialog, setShowDialog] = useState(false)
  const [showInventory, setShowInventory] = useState(false)
  const [showShop, setShowShop] = useState(false)
  const [shopNPC, setShopNPC] = useState<NPC | null>(null)
  const [viewportSize, setViewportSize] = useState({
    width: window.innerWidth,
    height: window.innerHeight,
  })

  // Initialize app
  useEffect(() => {
    const initializeApp = async () => {
      try {
        setLoading(true)

        // Check for saved auth token
        const savedToken = localStorage.getItem('authToken')
        if (savedToken && !isAuthenticated) {
          try {
            // Validate token with server
            const profile = await apiService.getProfile()
            useGameStore.getState().setAuthToken(savedToken)
            useGameStore.getState().setPlayer(profile)
            console.log('✅ Restored user session')
          } catch (error) {
            console.log('❌ Saved token invalid, clearing')
            localStorage.removeItem('authToken')
          }
        }

        // Initialize WebSocket connection if authenticated
        if (isAuthenticated && authToken) {
          webSocketService.connect(authToken)
        }

        setIsInitialized(true)
      } catch (error) {
        console.error('App initialization failed:', error)
        setError('Failed to initialize app')
      } finally {
        setLoading(false)
      }
    }

    initializeApp()
  }, [])

  // Handle viewport resize for responsive design
  useEffect(() => {
    const handleResize = () => {
      setViewportSize({
        width: window.innerWidth,
        height: window.innerHeight,
      })
    }

    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  // Manage WebSocket connection based on auth state
  useEffect(() => {
    if (isAuthenticated && authToken && isInitialized) {
      webSocketService.connect(authToken)
    } else if (!isAuthenticated) {
      webSocketService.disconnect()
    }
  }, [isAuthenticated, authToken, isInitialized])

  // Handle authentication changes
  useEffect(() => {
    if (!isAuthenticated && isInitialized) {
      // Clear game state when logged out
      useGameStore.getState().reset()
      setDialogNPC(null)
      setShowDialog(false)
    }
  }, [isAuthenticated, isInitialized])

  // PWA install prompt
  useEffect(() => {
    let deferredPrompt: any

    const handleBeforeInstallPrompt = (e: Event) => {
      e.preventDefault()
      deferredPrompt = e

      // Show install notification
      useGameStore.getState().addNotification({
        type: 'info',
        title: 'Install App',
        message: 'Install Tuxemon for a better experience!',
        duration: 10000,
        actions: [
          {
            label: 'Install',
            action: () => {
              if (deferredPrompt) {
                deferredPrompt.prompt()
                deferredPrompt.userChoice.then((choiceResult: any) => {
                  if (choiceResult.outcome === 'accepted') {
                    console.log('PWA installed')
                  }
                  deferredPrompt = null
                })
              }
            },
            style: 'primary',
          },
        ],
      })
    }

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt)
    return () => window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt)
  }, [])

  // Handle NPC interactions
  const handleNPCInteraction = (npc: NPC) => {
    setDialogNPC(npc)
    setShowDialog(true)
  }

  const handleDialogClose = () => {
    setShowDialog(false)
    setDialogNPC(null)
  }

  const handleBattleStart = () => {
    setShowDialog(false)
    // TODO: Implement battle screen
    console.log('Starting battle...')
  }

  const handleShopOpen = (items: string[]) => {
    if (dialogNPC) {
      setShopNPC(dialogNPC)
      setShowShop(true)
    }
    setShowDialog(false)
  }

  const handleInventoryOpen = () => {
    setShowInventory(true)
  }

  const handleInventoryClose = () => {
    setShowInventory(false)
  }

  const handleUseItem = (itemSlug: string, targetMonsterId?: string) => {
    console.log('Used item:', itemSlug, 'on monster:', targetMonsterId)
    // TODO: Apply item effects to game state
  }

  const handleShopClose = () => {
    setShowShop(false)
    setShopNPC(null)
  }

  // Loading screen while initializing
  if (!isInitialized) {
    return <LoadingScreen message="Initializing Tuxemon..." />
  }

  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <div className="relative w-full h-screen overflow-hidden bg-gray-900">
          <AnimatePresence mode="wait">
            {/* Authentication Flow */}
            {!isAuthenticated ? (
              <motion.div
                key="auth"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="w-full h-full"
              >
                <Routes>
                  <Route path="/login" element={<LoginScreen />} />
                  <Route path="/register" element={<LoginScreen isRegister />} />
                  <Route path="*" element={<Navigate to="/login" replace />} />
                </Routes>
              </motion.div>
            ) : (
              /* Main Game Interface */
              <motion.div
                key="game"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="w-full h-full flex flex-col"
              >
                <Routes>
                  <Route
                    path="/game"
                    element={
                      <div className="flex-1 relative">
                        {/* Game Canvas */}
                        <GameCanvas
                          width={viewportSize.width}
                          height={viewportSize.height - 120} // Account for HUD
                        />

                        {/* Game HUD */}
                        <GameHUD
                          onMenuToggle={() => console.log('Menu toggle')}
                          onInventoryOpen={handleInventoryOpen}
                          onNPCInteraction={handleNPCInteraction}
                        />

                        {/* Dialog System */}
                        <DialogSystem
                          isOpen={showDialog}
                          npc={dialogNPC}
                          onClose={handleDialogClose}
                          onBattleStart={handleBattleStart}
                          onShopOpen={handleShopOpen}
                        />

                        {/* Inventory UI */}
                        <InventoryUI
                          isOpen={showInventory}
                          onClose={handleInventoryClose}
                          onUseItem={handleUseItem}
                        />

                        {/* Shop UI */}
                        <ShopUI
                          isOpen={showShop}
                          npcId={shopNPC?.id || ''}
                          npcName={shopNPC?.name || ''}
                          onClose={handleShopClose}
                        />

                        {/* Connection Status */}
                        <div className="absolute top-4 right-4 z-40">
                          <motion.div
                            animate={{
                              scale: isConnected ? 1 : [1, 1.2, 1],
                              backgroundColor: isConnected ? '#10b981' : '#ef4444',
                            }}
                            transition={{
                              scale: { duration: 1, repeat: isConnected ? 0 : Infinity },
                            }}
                            className="w-3 h-3 rounded-full shadow-lg"
                            title={isConnected ? 'Connected' : 'Disconnected'}
                          />
                        </div>

                        {/* Loading Overlay */}
                        {ui.loading && (
                          <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
                          >
                            <div className="bg-white rounded-lg p-6 flex items-center space-x-3">
                              <motion.div
                                animate={{ rotate: 360 }}
                                transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                                className="w-5 h-5 border-2 border-indigo-500 border-t-transparent rounded-full"
                              />
                              <span className="text-gray-700">Loading...</span>
                            </div>
                          </motion.div>
                        )}
                      </div>
                    }
                  />
                  <Route path="/profile" element={<div>Profile Screen</div>} />
                  <Route path="/settings" element={<div>Settings Screen</div>} />
                  <Route path="*" element={<Navigate to="/game" replace />} />
                </Routes>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Global UI Elements */}
          <NotificationSystem />

          {/* Debug Info (Development Only) */}
          {import.meta.env.DEV && (
            <div className="absolute bottom-4 left-4 bg-black bg-opacity-75 text-white text-xs p-2 rounded font-mono z-50">
              <div>Player: {player?.username || 'None'}</div>
              <div>Connected: {isConnected ? 'Yes' : 'No'}</div>
              <div>Viewport: {viewportSize.width}x{viewportSize.height}</div>
              <div>Version: {__APP_VERSION__ || 'Dev'}</div>
            </div>
          )}

          {/* Error Banner */}
          {ui.error && (
            <motion.div
              initial={{ y: -100 }}
              animate={{ y: 0 }}
              exit={{ y: -100 }}
              className="absolute top-0 left-0 right-0 bg-red-500 text-white p-3 text-center z-50"
            >
              <span>{ui.error}</span>
              <button
                onClick={() => useGameStore.getState().setError(null)}
                className="ml-3 text-white hover:text-gray-200"
              >
                ✕
              </button>
            </motion.div>
          )}
        </div>
      </Router>
    </QueryClientProvider>
  )
}

export default App