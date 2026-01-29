// Game HUD Component for AI-Powered Tuxemon Frontend
// Austin Kidwell | Intellegix | Mobile-First Pokemon-Style Game

import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useGameData, useAuth, useUI } from '../hooks/useGameStore'
import type { NPC } from '../types/game'

interface GameHUDProps {
  onMenuToggle: () => void
  onInventoryOpen: () => void
  onNPCInteraction: (npc: NPC) => void
}

const GameHUD: React.FC<GameHUDProps> = ({
  onMenuToggle,
  onInventoryOpen,
  onNPCInteraction,
}) => {
  const { gameState, worldState } = useGameData()
  const { player, logout } = useAuth()
  const { ui } = useUI()

  const [showMenu, setShowMenu] = useState(false)
  const [showPartyInfo, setShowPartyInfo] = useState(false)

  // Get nearby NPCs for interaction buttons
  const nearbyNPCs = worldState?.npcsNearby?.filter(npc => {
    if (!gameState?.position || !npc.approachable) return false
    const [playerX, playerY] = gameState.position
    const [npcX, npcY] = npc.position
    const distance = Math.abs(playerX - npcX) + Math.abs(playerY - npcY)
    return distance <= 1
  }) || []

  const handleLogout = () => {
    logout()
    setShowMenu(false)
  }

  const formatPlayTime = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    return hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`
  }

  return (
    <>
      {/* Top HUD Bar */}
      <div className="absolute top-0 left-0 right-0 z-30 bg-gradient-to-b from-black/50 to-transparent p-4">
        <div className="flex items-center justify-between">
          {/* Player Info */}
          <motion.div
            initial={{ x: -50, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            className="bg-black/40 backdrop-blur-sm rounded-lg px-4 py-2 border border-white/20"
          >
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-500 rounded-full flex items-center justify-center">
                <span className="text-white text-sm font-bold">
                  {player?.username?.charAt(0)?.toUpperCase() || 'P'}
                </span>
              </div>
              <div className="text-white text-sm">
                <p className="font-medium">{player?.username || 'Player'}</p>
                <p className="text-white/70 text-xs">
                  💰 {gameState?.money || 0} | ⏱ {formatPlayTime(gameState?.playTimeSeconds || 0)}
                </p>
              </div>
            </div>
          </motion.div>

          {/* Action Buttons */}
          <motion.div
            initial={{ x: 50, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            className="flex items-center space-x-2"
          >
            {/* Party Info Toggle */}
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setShowPartyInfo(!showPartyInfo)}
              className="bg-black/40 backdrop-blur-sm rounded-lg p-2 border border-white/20 text-white hover:bg-white/10 transition-colors"
            >
              <div className="w-6 h-6 flex items-center justify-center">
                🎯
              </div>
            </motion.button>

            {/* Menu Button */}
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setShowMenu(!showMenu)}
              className="bg-black/40 backdrop-blur-sm rounded-lg p-2 border border-white/20 text-white hover:bg-white/10 transition-colors"
            >
              <div className="w-6 h-6 flex items-center justify-center">
                ☰
              </div>
            </motion.button>
          </motion.div>
        </div>

        {/* Party Info Popup */}
        <AnimatePresence>
          {showPartyInfo && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="absolute top-16 left-4 bg-black/60 backdrop-blur-lg rounded-lg p-4 border border-white/20 text-white min-w-[200px]"
            >
              <h3 className="font-medium mb-2">Your Party</h3>
              {gameState?.party && gameState.party.length > 0 ? (
                <div className="space-y-2">
                  {gameState.party.slice(0, 6).map((monster: any, index: number) => (
                    <div key={index} className="flex items-center space-x-2 text-sm">
                      <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                      <span>{monster.name || `Monster ${index + 1}`}</span>
                      <span className="text-white/60 text-xs">Lv.{monster.level || 1}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-white/60 text-sm">No monsters in party</p>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Bottom HUD Bar */}
      <div className="absolute bottom-0 left-0 right-0 z-30 bg-gradient-to-t from-black/50 to-transparent p-4">
        <div className="flex items-center justify-between">
          {/* Position Info */}
          <motion.div
            initial={{ x: -50, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            className="bg-black/40 backdrop-blur-sm rounded-lg px-3 py-2 border border-white/20 text-white text-sm"
          >
            <div className="flex items-center space-x-2">
              <span>📍</span>
              <span>
                {gameState?.currentMap || 'Unknown'} ({gameState?.position?.[0] || 0}, {gameState?.position?.[1] || 0})
              </span>
            </div>
          </motion.div>

          {/* Action Buttons */}
          <motion.div
            initial={{ x: 50, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            className="flex items-center space-x-2"
          >
            {/* Inventory Button */}
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={onInventoryOpen}
              className="bg-black/40 backdrop-blur-sm rounded-lg px-4 py-2 border border-white/20 text-white hover:bg-white/10 transition-colors text-sm font-medium"
            >
              🎒 Bag
            </motion.button>

            {/* NPC Interaction Buttons */}
            <AnimatePresence>
              {nearbyNPCs.map((npc) => (
                <motion.button
                  key={npc.id}
                  initial={{ scale: 0, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  exit={{ scale: 0, opacity: 0 }}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => onNPCInteraction(npc)}
                  className="bg-gradient-to-r from-blue-500 to-purple-500 rounded-lg px-4 py-2 border border-white/20 text-white font-medium text-sm shadow-lg"
                >
                  💬 {npc.name}
                </motion.button>
              ))}
            </AnimatePresence>
          </motion.div>
        </div>
      </div>

      {/* Menu Overlay */}
      <AnimatePresence>
        {showMenu && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowMenu(false)}
              className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm"
            />

            {/* Menu Panel */}
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="fixed right-0 top-0 bottom-0 z-50 w-80 bg-black/80 backdrop-blur-xl border-l border-white/20 p-6"
            >
              <div className="flex flex-col h-full">
                {/* Header */}
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-white text-xl font-bold">Menu</h2>
                  <button
                    onClick={() => setShowMenu(false)}
                    className="text-white/60 hover:text-white text-2xl"
                  >
                    ✕
                  </button>
                </div>

                {/* Menu Items */}
                <div className="flex-1 space-y-2">
                  <motion.button
                    whileHover={{ x: 4 }}
                    onClick={onInventoryOpen}
                    className="w-full text-left p-3 text-white hover:bg-white/10 rounded-lg transition-colors flex items-center space-x-3"
                  >
                    <span>🎒</span>
                    <span>Inventory</span>
                  </motion.button>

                  <motion.button
                    whileHover={{ x: 4 }}
                    onClick={() => console.log('Monsters')}
                    className="w-full text-left p-3 text-white hover:bg-white/10 rounded-lg transition-colors flex items-center space-x-3"
                  >
                    <span>🐾</span>
                    <span>Monsters</span>
                  </motion.button>

                  <motion.button
                    whileHover={{ x: 4 }}
                    onClick={() => console.log('Map')}
                    className="w-full text-left p-3 text-white hover:bg-white/10 rounded-lg transition-colors flex items-center space-x-3"
                  >
                    <span>🗺️</span>
                    <span>Map</span>
                  </motion.button>

                  <motion.button
                    whileHover={{ x: 4 }}
                    onClick={() => console.log('Settings')}
                    className="w-full text-left p-3 text-white hover:bg-white/10 rounded-lg transition-colors flex items-center space-x-3"
                  >
                    <span>⚙️</span>
                    <span>Settings</span>
                  </motion.button>

                  <motion.button
                    whileHover={{ x: 4 }}
                    onClick={() => console.log('Help')}
                    className="w-full text-left p-3 text-white hover:bg-white/10 rounded-lg transition-colors flex items-center space-x-3"
                  >
                    <span>❓</span>
                    <span>Help</span>
                  </motion.button>
                </div>

                {/* Player Stats */}
                <div className="border-t border-white/20 pt-4 mb-4">
                  <h3 className="text-white font-medium mb-2">Statistics</h3>
                  <div className="text-white/70 text-sm space-y-1">
                    <p>Play Time: {formatPlayTime(gameState?.playTimeSeconds || 0)}</p>
                    <p>Money: ${gameState?.money || 0}</p>
                    <p>Monsters: {gameState?.party?.length || 0}/6</p>
                    <p>Current Map: {gameState?.currentMap || 'Unknown'}</p>
                  </div>
                </div>

                {/* Logout Button */}
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={handleLogout}
                  className="w-full p-3 bg-red-600/20 border border-red-500/30 rounded-lg text-red-400 hover:bg-red-600/30 transition-colors font-medium"
                >
                  🚪 Logout
                </motion.button>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Loading Indicator */}
      {ui.loading && (
        <div className="absolute top-4 right-4 z-40">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
            className="w-6 h-6 border-2 border-white border-t-transparent rounded-full"
          />
        </div>
      )}
    </>
  )
}

export default GameHUD