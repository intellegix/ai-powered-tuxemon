// Dialog System Component for AI-Powered Tuxemon Frontend
// Austin Kidwell | Intellegix | Mobile-First Pokemon-Style Game

import React, { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useGameStore, useUI } from '../hooks/useGameStore'
import { apiService } from '../services/api'
import type { DialogueResponse, NPC, Emotion } from '../types/game'

interface DialogSystemProps {
  isOpen: boolean
  npc: NPC | null
  onClose: () => void
  onBattleStart?: () => void
  onShopOpen?: (items: string[]) => void
}

interface TypewriterTextProps {
  text: string
  speed?: number
  onComplete?: () => void
}

const TypewriterText: React.FC<TypewriterTextProps> = ({
  text,
  speed = 30,
  onComplete
}) => {
  const [displayedText, setDisplayedText] = useState('')
  const [currentIndex, setCurrentIndex] = useState(0)

  useEffect(() => {
    if (currentIndex < text.length) {
      const timer = setTimeout(() => {
        setDisplayedText(prev => prev + text[currentIndex])
        setCurrentIndex(prev => prev + 1)
      }, speed)

      return () => clearTimeout(timer)
    } else if (currentIndex === text.length && onComplete) {
      onComplete()
    }
  }, [currentIndex, text, speed, onComplete])

  useEffect(() => {
    setDisplayedText('')
    setCurrentIndex(0)
  }, [text])

  return <span>{displayedText}</span>
}

const emotionEmojis: Record<Emotion, string> = {
  [Emotion.NEUTRAL]: '😐',
  [Emotion.HAPPY]: '😊',
  [Emotion.EXCITED]: '🤩',
  [Emotion.SAD]: '😢',
  [Emotion.ANGRY]: '😠',
  [Emotion.CONFUSED]: '😕',
  [Emotion.SHY]: '😳',
  [Emotion.PROUD]: '😤',
}

export const DialogSystem: React.FC<DialogSystemProps> = ({
  isOpen,
  npc,
  onClose,
  onBattleStart,
  onShopOpen,
}) => {
  const [currentDialogue, setCurrentDialogue] = useState<DialogueResponse | null>(null)
  const [isTyping, setIsTyping] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [interactionHistory, setInteractionHistory] = useState<DialogueResponse[]>([])
  const [showActions, setShowActions] = useState(false)

  const { gameState } = useGameStore()
  const { addNotification } = useUI()
  const dialogRef = useRef<HTMLDivElement>(null)

  // Auto-interact with NPC when dialog opens
  useEffect(() => {
    if (isOpen && npc && gameState) {
      initiateDialogue()
    }
  }, [isOpen, npc?.id, gameState?.playerId])

  // Scroll to bottom when new dialogue appears
  useEffect(() => {
    if (dialogRef.current) {
      dialogRef.current.scrollTop = dialogRef.current.scrollHeight
    }
  }, [interactionHistory])

  const initiateDialogue = async () => {
    if (!npc || !gameState) return

    setIsLoading(true)
    setError(null)
    setShowActions(false)

    try {
      // Prepare interaction context
      const partyNames = gameState.party.map(m => `${m.name} (Lv.${m.level})`).join(', ')
      const partySummary = gameState.party.length > 0
        ? `Party: ${partyNames}`
        : 'No monsters in party'

      // Get recent achievements (simplified)
      const achievements = Object.entries(gameState.storyProgress)
        .filter(([_, completed]) => completed)
        .map(([achievement, _]) => achievement)
        .slice(-3)

      const dialogue = await apiService.interactWithNPC(npc.id, {
        interactionType: 'dialogue',
        playerPartySummary: partySummary,
        recentAchievements: achievements,
      })

      setCurrentDialogue(dialogue)
      setInteractionHistory(prev => [...prev, dialogue])
      setIsTyping(true)

      // Handle special dialogue actions
      if (dialogue.triggersBattle && onBattleStart) {
        // Delay battle start until dialogue is complete
        setTimeout(() => {
          onBattleStart()
        }, 3000)
      }

      if (dialogue.shopItems && dialogue.shopItems.length > 0 && onShopOpen) {
        onShopOpen(dialogue.shopItems)
      }

    } catch (error) {
      console.error('Failed to get NPC dialogue:', error)
      setError('Failed to talk to NPC. They seem distracted.')

      // Fallback dialogue
      setCurrentDialogue({
        text: "Hello there! I'm not sure what to say right now.",
        emotion: Emotion.CONFUSED,
        actions: [],
        relationshipChange: 0,
        triggersBattle: false,
      })
      setIsTyping(true)
    } finally {
      setIsLoading(false)
    }
  }

  const handleTypingComplete = () => {
    setIsTyping(false)
    setShowActions(true)
  }

  const handleContinue = () => {
    if (currentDialogue?.triggersBattle) {
      onBattleStart?.()
      return
    }

    if (currentDialogue?.actions && currentDialogue.actions.length > 0) {
      // Show action selection UI
      return
    }

    // Continue conversation
    setShowActions(false)
    initiateDialogue()
  }

  const handleSkip = () => {
    setIsTyping(false)
    setShowActions(true)
  }

  const getEmotionEmoji = (emotion: Emotion): string => {
    return emotionEmojis[emotion] || emotionEmojis[Emotion.NEUTRAL]
  }

  const getRelationshipColor = (level: number): string => {
    if (level >= 0.8) return 'text-pink-500'
    if (level >= 0.6) return 'text-yellow-500'
    if (level >= 0.4) return 'text-blue-500'
    if (level >= 0.2) return 'text-green-500'
    return 'text-gray-500'
  }

  if (!isOpen || !npc) return null

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black bg-opacity-60 flex items-end z-50"
        onClick={onClose}
      >
        <motion.div
          initial={{ y: 300 }}
          animate={{ y: 0 }}
          exit={{ y: 300 }}
          transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          className="w-full bg-white rounded-t-2xl shadow-2xl max-h-80 flex flex-col"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-gray-200">
            <div className="flex items-center space-x-3">
              {/* NPC Avatar */}
              <div className="w-12 h-12 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-full flex items-center justify-center text-white font-bold">
                {npc.name.charAt(0).toUpperCase()}
              </div>

              {/* NPC Info */}
              <div>
                <h3 className="font-bold text-gray-800">{npc.name}</h3>
                <div className="flex items-center space-x-2">
                  <div className={`text-sm ${getRelationshipColor(npc.relationshipLevel)}`}>
                    {'♥'.repeat(Math.ceil(npc.relationshipLevel * 5))}
                  </div>
                  {npc.isTrainer && (
                    <span className="text-xs bg-orange-100 text-orange-800 px-2 py-1 rounded-full">
                      Trainer
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Close Button */}
            <button
              onClick={onClose}
              className="w-8 h-8 flex items-center justify-center rounded-full bg-gray-100 hover:bg-gray-200 transition-colors"
            >
              ✕
            </button>
          </div>

          {/* Dialog Content */}
          <div
            ref={dialogRef}
            className="flex-1 overflow-y-auto p-4 space-y-4"
          >
            {/* Loading State */}
            {isLoading && (
              <div className="flex items-center justify-center py-8">
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                  className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full"
                />
                <span className="ml-2 text-gray-600">AI is thinking...</span>
              </div>
            )}

            {/* Error State */}
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                <p className="text-red-700 text-sm">{error}</p>
              </div>
            )}

            {/* Current Dialogue */}
            {currentDialogue && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-gray-50 rounded-lg p-4"
              >
                <div className="flex items-start space-x-3">
                  <div className="text-2xl">
                    {getEmotionEmoji(currentDialogue.emotion)}
                  </div>
                  <div className="flex-1">
                    <div className="bg-white rounded-lg p-3 shadow-sm">
                      <p className="text-gray-800 leading-relaxed">
                        {isTyping ? (
                          <TypewriterText
                            text={currentDialogue.text}
                            speed={20}
                            onComplete={handleTypingComplete}
                          />
                        ) : (
                          currentDialogue.text
                        )}
                      </p>
                    </div>

                    {/* Special Actions */}
                    {currentDialogue.triggersBattle && showActions && (
                      <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg"
                      >
                        <p className="text-red-700 text-sm font-medium">
                          🔥 {npc.name} wants to battle!
                        </p>
                      </motion.div>
                    )}

                    {currentDialogue.shopItems && currentDialogue.shopItems.length > 0 && showActions && (
                      <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="mt-3 p-3 bg-green-50 border border-green-200 rounded-lg"
                      >
                        <p className="text-green-700 text-sm font-medium">
                          🛍️ Shop items available!
                        </p>
                      </motion.div>
                    )}
                  </div>
                </div>
              </motion.div>
            )}

            {/* Interaction History */}
            {interactionHistory.length > 1 && (
              <details className="text-sm">
                <summary className="cursor-pointer text-gray-600 hover:text-gray-800">
                  Previous messages ({interactionHistory.length - 1})
                </summary>
                <div className="mt-2 space-y-2">
                  {interactionHistory.slice(0, -1).map((dialogue, index) => (
                    <div key={index} className="bg-gray-100 rounded p-2 text-gray-700">
                      <span className="mr-2">{getEmotionEmoji(dialogue.emotion)}</span>
                      {dialogue.text}
                    </div>
                  ))}
                </div>
              </details>
            )}
          </div>

          {/* Action Bar */}
          {showActions && currentDialogue && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="border-t border-gray-200 p-4"
            >
              <div className="flex space-x-3">
                {/* Skip typing button */}
                {isTyping && (
                  <button
                    onClick={handleSkip}
                    className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-gray-700 text-sm transition-colors"
                  >
                    Skip
                  </button>
                )}

                {/* Continue/Action buttons */}
                {!isTyping && (
                  <>
                    <button
                      onClick={handleContinue}
                      className="flex-1 px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg font-medium transition-colors"
                    >
                      {currentDialogue.triggersBattle ? 'Battle!' : 'Continue'}
                    </button>

                    <button
                      onClick={onClose}
                      className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-gray-700 transition-colors"
                    >
                      End
                    </button>
                  </>
                )}
              </div>
            </motion.div>
          )}

          {/* Touch indicator for mobile */}
          {isTyping && (
            <div className="absolute bottom-20 right-4">
              <motion.div
                animate={{ scale: [1, 1.1, 1] }}
                transition={{ duration: 1, repeat: Infinity }}
                className="w-8 h-8 bg-indigo-500 rounded-full flex items-center justify-center text-white text-xs"
              >
                👆
              </motion.div>
            </div>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}

export default DialogSystem