// Battle Screen Component for AI-Powered Tuxemon Frontend
// Austin Kidwell | Intellegix | Mobile-First Pokemon-Style Game

import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useGameData, useUI } from '../hooks/useGameStore'
import { apiService } from '../services/api'
import type { Monster, CombatSession, CombatAction } from '../types/game'

interface BattleScreenProps {
  combatSession: CombatSession
  onBattleEnd: (winner: 'player' | 'npc') => void
  onEscape: () => void
}

interface BattleMonster extends Monster {
  currentHp: number
  maxHp: number
  techniques: Array<{
    slug: string
    name: string
    power: number
    element: string
    pp: number
    maxPp: number
  }>
}

interface BattleState {
  playerMonster: BattleMonster | null
  opponentMonster: BattleMonster | null
  phase: 'waiting' | 'action_selection' | 'executing' | 'victory' | 'defeat'
  turnQueue: CombatAction[]
  currentTurn: number
  battleLog: string[]
  weather: string | null
}

const BattleScreen: React.FC<BattleScreenProps> = ({
  combatSession,
  onBattleEnd,
  onEscape,
}) => {
  const { gameState } = useGameData()
  const { setLoading, setError } = useUI()

  const [battleState, setBattleState] = useState<BattleState>({
    playerMonster: null,
    opponentMonster: null,
    phase: 'waiting',
    turnQueue: [],
    currentTurn: 0,
    battleLog: ['Battle Started!'],
    weather: null,
  })

  const [selectedAction, setSelectedAction] = useState<string | null>(null)
  const [selectedTechnique, setSelectedTechnique] = useState<string | null>(null)
  const [showTechniques, setShowTechniques] = useState(false)
  const [showPartySelect, setShowPartySelect] = useState(false)
  const [animationPlaying, setAnimationPlaying] = useState(false)

  // Initialize battle state
  useEffect(() => {
    const initializeBattle = async () => {
      try {
        setLoading(true)

        // Get battle state from server
        const battleData = await apiService.getCombatState(combatSession.id)

        setBattleState(prev => ({
          ...prev,
          ...battleData,
          battleLog: ['Battle Started!'],
        }))

        console.log('Battle initialized:', battleData)
      } catch (error) {
        console.error('Failed to initialize battle:', error)
        setError('Failed to start battle')
      } finally {
        setLoading(false)
      }
    }

    initializeBattle()
  }, [combatSession.id, setLoading, setError])

  // Handle action selection
  const handleActionSelect = (action: string) => {
    setSelectedAction(action)
    setShowTechniques(action === 'attack')
    setShowPartySelect(action === 'switch')
  }

  // Submit combat action
  const submitAction = async (action: CombatAction) => {
    try {
      setAnimationPlaying(true)
      setLoading(true)

      const result = await apiService.submitCombatAction(combatSession.id, action)

      // Update battle state with result
      setBattleState(prev => ({
        ...prev,
        ...result.newState,
        battleLog: [...prev.battleLog, ...result.events],
      }))

      // Check for battle end
      if (result.winner) {
        setTimeout(() => {
          onBattleEnd(result.winner)
        }, 2000)
      }

      // Reset UI state
      setSelectedAction(null)
      setSelectedTechnique(null)
      setShowTechniques(false)
      setShowPartySelect(false)

    } catch (error) {
      console.error('Combat action failed:', error)
      setError('Action failed')
    } finally {
      setLoading(false)
      setAnimationPlaying(false)
    }
  }

  // Action handlers
  const handleAttack = (techniqueSlug: string) => {
    if (!battleState.playerMonster) return

    const action: CombatAction = {
      actorId: battleState.playerMonster.id,
      actionType: 'attack',
      techniqueSlug,
      targetId: battleState.opponentMonster?.id,
    }

    submitAction(action)
  }

  const handleSwitchMonster = (monsterId: string) => {
    if (!battleState.playerMonster) return

    const action: CombatAction = {
      actorId: battleState.playerMonster.id,
      actionType: 'switch',
      monsterSwitchTo: monsterId,
    }

    submitAction(action)
  }

  const handleRun = () => {
    onEscape()
  }

  // Calculate HP percentage for health bars
  const getHpPercentage = (current: number, max: number): number => {
    return Math.max(0, Math.min(100, (current / max) * 100))
  }

  // Get HP bar color based on percentage
  const getHpBarColor = (percentage: number): string => {
    if (percentage > 60) return 'bg-green-500'
    if (percentage > 25) return 'bg-yellow-500'
    return 'bg-red-500'
  }

  return (
    <div className="fixed inset-0 z-50 bg-gradient-to-b from-sky-400 via-blue-500 to-green-400">
      {/* Weather Effects */}
      {battleState.weather && (
        <div className="absolute inset-0 pointer-events-none">
          {/* Add weather particle effects here */}
        </div>
      )}

      {/* Battle Arena */}
      <div className="relative h-full flex flex-col">

        {/* Opponent Side */}
        <div className="flex-1 flex items-end justify-center p-4">
          <motion.div
            initial={{ x: 100, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            transition={{ delay: 0.3 }}
            className="relative"
          >
            {battleState.opponentMonster && (
              <>
                {/* Opponent Monster */}
                <motion.div
                  animate={{
                    y: animationPlaying ? [-5, 5, -5] : 0,
                  }}
                  transition={{
                    duration: 0.5,
                    repeat: animationPlaying ? 2 : 0,
                  }}
                  className="w-32 h-32 bg-gray-300 rounded-lg flex items-center justify-center text-4xl border-2 border-gray-400"
                >
                  🐉
                </motion.div>

                {/* Opponent Info Card */}
                <motion.div
                  initial={{ y: -20, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ delay: 0.5 }}
                  className="absolute -top-16 -left-8 bg-black/70 backdrop-blur-sm rounded-lg p-3 min-w-[200px]"
                >
                  <div className="text-white">
                    <p className="font-bold text-sm">{battleState.opponentMonster.name}</p>
                    <p className="text-xs text-gray-300">Lv. {battleState.opponentMonster.level}</p>

                    {/* HP Bar */}
                    <div className="mt-2">
                      <div className="flex justify-between text-xs text-gray-300 mb-1">
                        <span>HP</span>
                        <span>{battleState.opponentMonster.currentHp}/{battleState.opponentMonster.maxHp}</span>
                      </div>
                      <div className="w-full bg-gray-600 rounded-full h-2">
                        <motion.div
                          initial={{ width: '100%' }}
                          animate={{
                            width: `${getHpPercentage(
                              battleState.opponentMonster.currentHp,
                              battleState.opponentMonster.maxHp
                            )}%`
                          }}
                          transition={{ duration: 0.5 }}
                          className={`h-2 rounded-full ${getHpBarColor(
                            getHpPercentage(
                              battleState.opponentMonster.currentHp,
                              battleState.opponentMonster.maxHp
                            )
                          )}`}
                        />
                      </div>
                    </div>
                  </div>
                </motion.div>
              </>
            )}
          </motion.div>
        </div>

        {/* Player Side */}
        <div className="flex-1 flex items-start justify-start p-4">
          <motion.div
            initial={{ x: -100, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            transition={{ delay: 0.6 }}
            className="relative"
          >
            {battleState.playerMonster && (
              <>
                {/* Player Monster */}
                <motion.div
                  animate={{
                    y: animationPlaying ? [-5, 5, -5] : 0,
                  }}
                  transition={{
                    duration: 0.5,
                    repeat: animationPlaying ? 2 : 0,
                  }}
                  className="w-32 h-32 bg-gray-300 rounded-lg flex items-center justify-center text-4xl border-2 border-gray-400"
                >
                  🦎
                </motion.div>

                {/* Player Info Card */}
                <motion.div
                  initial={{ y: 20, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ delay: 0.8 }}
                  className="absolute -bottom-16 -right-8 bg-black/70 backdrop-blur-sm rounded-lg p-3 min-w-[200px]"
                >
                  <div className="text-white">
                    <p className="font-bold text-sm">{battleState.playerMonster.name}</p>
                    <p className="text-xs text-gray-300">Lv. {battleState.playerMonster.level}</p>

                    {/* HP Bar */}
                    <div className="mt-2">
                      <div className="flex justify-between text-xs text-gray-300 mb-1">
                        <span>HP</span>
                        <span>{battleState.playerMonster.currentHp}/{battleState.playerMonster.maxHp}</span>
                      </div>
                      <div className="w-full bg-gray-600 rounded-full h-2">
                        <motion.div
                          initial={{ width: '100%' }}
                          animate={{
                            width: `${getHpPercentage(
                              battleState.playerMonster.currentHp,
                              battleState.playerMonster.maxHp
                            )}%`
                          }}
                          transition={{ duration: 0.5 }}
                          className={`h-2 rounded-full ${getHpBarColor(
                            getHpPercentage(
                              battleState.playerMonster.currentHp,
                              battleState.playerMonster.maxHp
                            )
                          )}`}
                        />
                      </div>
                    </div>

                    {/* Experience Bar */}
                    <div className="mt-1">
                      <div className="w-full bg-gray-600 rounded-full h-1">
                        <div className="w-3/4 bg-blue-500 h-1 rounded-full" />
                      </div>
                    </div>
                  </div>
                </motion.div>
              </>
            )}
          </motion.div>
        </div>
      </div>

      {/* Battle Log */}
      <motion.div
        initial={{ y: 100, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 1 }}
        className="absolute bottom-40 left-4 right-4 bg-black/80 backdrop-blur-sm rounded-lg p-4 h-24 overflow-y-auto"
      >
        <div className="text-white text-sm space-y-1">
          {battleState.battleLog.slice(-3).map((log, index) => (
            <motion.p
              key={index}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.2 }}
            >
              {log}
            </motion.p>
          ))}
        </div>
      </motion.div>

      {/* Action Menu */}
      <AnimatePresence mode="wait">
        {battleState.phase === 'action_selection' && !animationPlaying && (
          <motion.div
            initial={{ y: 100, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 100, opacity: 0 }}
            className="absolute bottom-0 left-0 right-0 bg-black/90 backdrop-blur-lg p-4"
          >
            {!selectedAction && (
              <>
                <p className="text-white text-center mb-4">What will {battleState.playerMonster?.name} do?</p>
                <div className="grid grid-cols-2 gap-3">
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => handleActionSelect('attack')}
                    className="bg-red-600 hover:bg-red-700 text-white p-4 rounded-lg font-bold text-center transition-colors"
                  >
                    ⚔️ Attack
                  </motion.button>

                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => handleActionSelect('switch')}
                    className="bg-blue-600 hover:bg-blue-700 text-white p-4 rounded-lg font-bold text-center transition-colors"
                  >
                    🔄 Switch
                  </motion.button>

                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => handleActionSelect('item')}
                    className="bg-green-600 hover:bg-green-700 text-white p-4 rounded-lg font-bold text-center transition-colors"
                  >
                    🎒 Item
                  </motion.button>

                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={handleRun}
                    className="bg-gray-600 hover:bg-gray-700 text-white p-4 rounded-lg font-bold text-center transition-colors"
                  >
                    🏃 Run
                  </motion.button>
                </div>
              </>
            )}

            {/* Technique Selection */}
            {showTechniques && battleState.playerMonster?.techniques && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <div className="flex justify-between items-center mb-4">
                  <p className="text-white">Choose a technique:</p>
                  <button
                    onClick={() => setSelectedAction(null)}
                    className="text-white/70 hover:text-white"
                  >
                    ← Back
                  </button>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {battleState.playerMonster.techniques.map((technique) => (
                    <motion.button
                      key={technique.slug}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={() => handleAttack(technique.slug)}
                      disabled={technique.pp === 0}
                      className={`p-3 rounded-lg text-left transition-colors ${
                        technique.pp === 0
                          ? 'bg-gray-700 text-gray-500'
                          : 'bg-blue-600 hover:bg-blue-700 text-white'
                      }`}
                    >
                      <p className="font-bold text-sm">{technique.name}</p>
                      <p className="text-xs opacity-75">
                        {technique.element} • PP: {technique.pp}/{technique.maxPp}
                      </p>
                    </motion.button>
                  ))}
                </div>
              </motion.div>
            )}

            {/* Party Selection */}
            {showPartySelect && gameState?.party && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <div className="flex justify-between items-center mb-4">
                  <p className="text-white">Choose a monster:</p>
                  <button
                    onClick={() => setSelectedAction(null)}
                    className="text-white/70 hover:text-white"
                  >
                    ← Back
                  </button>
                </div>
                <div className="space-y-2">
                  {gameState.party.filter((monster: any) => monster.id !== battleState.playerMonster?.id).map((monster: any) => (
                    <motion.button
                      key={monster.id}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={() => handleSwitchMonster(monster.id)}
                      disabled={monster.currentHp === 0}
                      className={`w-full p-3 rounded-lg text-left transition-colors ${
                        monster.currentHp === 0
                          ? 'bg-gray-700 text-gray-500'
                          : 'bg-green-600 hover:bg-green-700 text-white'
                      }`}
                    >
                      <div className="flex justify-between items-center">
                        <div>
                          <p className="font-bold">{monster.name}</p>
                          <p className="text-sm opacity-75">Lv. {monster.level}</p>
                        </div>
                        <div className="text-right text-sm">
                          <p>HP: {monster.currentHp}/{monster.maxHp}</p>
                        </div>
                      </div>
                    </motion.button>
                  ))}
                </div>
              </motion.div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Loading/Animation State */}
      {animationPlaying && (
        <div className="absolute inset-0 bg-black/30 flex items-center justify-center z-10">
          <motion.div
            animate={{
              scale: [1, 1.2, 1],
              opacity: [1, 0.8, 1],
            }}
            transition={{
              duration: 0.5,
              repeat: 2,
            }}
            className="text-white text-4xl"
          >
            ⚡
          </motion.div>
        </div>
      )}

      {/* Battle End Screen */}
      {(battleState.phase === 'victory' || battleState.phase === 'defeat') && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="absolute inset-0 bg-black/80 flex items-center justify-center z-20"
        >
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="bg-white rounded-lg p-8 text-center max-w-sm mx-4"
          >
            <div className="text-6xl mb-4">
              {battleState.phase === 'victory' ? '🏆' : '😢'}
            </div>
            <h2 className="text-2xl font-bold mb-2">
              {battleState.phase === 'victory' ? 'Victory!' : 'Defeat'}
            </h2>
            <p className="text-gray-600 mb-6">
              {battleState.phase === 'victory'
                ? 'You won the battle!'
                : 'Your monster was defeated.'}
            </p>
            <button
              onClick={() => onBattleEnd(battleState.phase === 'victory' ? 'player' : 'npc')}
              className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-bold transition-colors"
            >
              Continue
            </button>
          </motion.div>
        </motion.div>
      )}
    </div>
  )
}

export default BattleScreen