// Game State Management for AI-Powered Tuxemon Frontend
// Austin Kidwell | Intellegix | Mobile-First Pokemon-Style Game

import { create } from 'zustand'
import { subscribeWithSelector, devtools } from 'zustand/middleware'
import { immer } from 'zustand/middleware/immer'
import type {
  Player,
  GameState,
  WorldState,
  CombatState,
  UIState,
  Screen,
  Notification,
  NPC,
  Monster,
  DialogueResponse,
} from '../types/game'

interface GameStore {
  // Authentication
  player: Player | null
  isAuthenticated: boolean
  authToken: string | null

  // Game state
  gameState: GameState | null
  worldState: WorldState | null
  combatState: CombatState | null

  // UI state
  ui: UIState

  // Connection state
  isConnected: boolean
  isLoading: boolean
  error: string | null

  // Actions
  setPlayer: (player: Player) => void
  setAuthToken: (token: string | null) => void
  setGameState: (state: GameState) => void
  setWorldState: (state: WorldState) => void
  setCombatState: (state: CombatState | null) => void
  updateNPCDialogue: (npcId: string, dialogue: DialogueResponse) => void
  updateMonsterHP: (monsterId: string, newHP: number) => void
  addNotification: (notification: Omit<Notification, 'id'>) => void
  removeNotification: (id: string) => void
  setScreen: (screen: Screen) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  setConnected: (connected: boolean) => void
  logout: () => void
  reset: () => void
}

const initialUIState: UIState = {
  activeScreen: Screen.MENU,
  dialogueOpen: false,
  menuOpen: false,
  combatMode: false,
  loading: false,
  error: null,
  notifications: [],
}

export const useGameStore = create<GameStore>()(
  devtools(
    subscribeWithSelector(
      immer((set, get) => ({
        // Initial state
        player: null,
        isAuthenticated: false,
        authToken: null,
        gameState: null,
        worldState: null,
        combatState: null,
        ui: initialUIState,
        isConnected: false,
        isLoading: false,
        error: null,

        // Actions
        setPlayer: (player) =>
          set((state) => {
            state.player = player
            state.isAuthenticated = true
          }),

        setAuthToken: (token) =>
          set((state) => {
            state.authToken = token
            state.isAuthenticated = !!token

            // Store token in localStorage for persistence
            if (token) {
              localStorage.setItem('authToken', token)
            } else {
              localStorage.removeItem('authToken')
            }
          }),

        setGameState: (gameState) =>
          set((state) => {
            state.gameState = gameState
          }),

        setWorldState: (worldState) =>
          set((state) => {
            state.worldState = worldState
          }),

        setCombatState: (combatState) =>
          set((state) => {
            state.combatState = combatState
            state.ui.combatMode = !!combatState
          }),

        updateNPCDialogue: (npcId, dialogue) =>
          set((state) => {
            if (state.worldState) {
              const npc = state.worldState.npcsNearby.find(n => n.id === npcId)
              if (npc) {
                // Update NPC relationship if dialogue changes it
                if (state.gameState && dialogue.relationshipChange !== 0) {
                  state.gameState.npcRelationships[npc.slug] =
                    (state.gameState.npcRelationships[npc.slug] || 0) + dialogue.relationshipChange
                }
              }
            }

            // Show dialogue UI
            state.ui.dialogueOpen = true
          }),

        updateMonsterHP: (monsterId, newHP) =>
          set((state) => {
            // Update in player's party
            if (state.gameState) {
              const monster = state.gameState.party.find(m => m.id === monsterId)
              if (monster) {
                monster.currentHp = Math.max(0, Math.min(newHP, monster.maxHp))
              }
            }

            // Update in combat state
            if (state.combatState) {
              state.combatState.participants.forEach(participant => {
                if (participant.activeMonster?.id === monsterId) {
                  participant.activeMonster.currentHp = Math.max(0, Math.min(newHP, participant.activeMonster.maxHp))
                }
                participant.party.forEach(monster => {
                  if (monster.id === monsterId) {
                    monster.currentHp = Math.max(0, Math.min(newHP, monster.maxHp))
                  }
                })
              })
            }
          }),

        addNotification: (notification) =>
          set((state) => {
            const id = Date.now().toString() + Math.random().toString(36)
            state.ui.notifications.push({ ...notification, id })

            // Auto-remove after duration if specified
            if (notification.duration) {
              setTimeout(() => {
                get().removeNotification(id)
              }, notification.duration)
            }
          }),

        removeNotification: (id) =>
          set((state) => {
            state.ui.notifications = state.ui.notifications.filter(n => n.id !== id)
          }),

        setScreen: (screen) =>
          set((state) => {
            state.ui.activeScreen = screen

            // Close menus when changing screens
            if (screen !== Screen.MENU) {
              state.ui.menuOpen = false
            }
          }),

        setLoading: (loading) =>
          set((state) => {
            state.ui.loading = loading
          }),

        setError: (error) =>
          set((state) => {
            state.ui.error = error
            if (error) {
              state.ui.loading = false
            }
          }),

        setConnected: (connected) =>
          set((state) => {
            state.isConnected = connected
            if (!connected) {
              state.combatState = null
              state.ui.combatMode = false
            }
          }),

        logout: () =>
          set((state) => {
            state.player = null
            state.isAuthenticated = false
            state.authToken = null
            state.gameState = null
            state.worldState = null
            state.combatState = null
            state.ui = { ...initialUIState }
            state.isConnected = false

            // Clear persisted data
            localStorage.removeItem('authToken')
          }),

        reset: () =>
          set((state) => {
            state.gameState = null
            state.worldState = null
            state.combatState = null
            state.ui = { ...initialUIState }
            state.error = null
          }),
      }))
    ),
    {
      name: 'tuxemon-game-store',
    }
  )
)

// Selectors for common state combinations
export const useAuth = () => {
  const { player, isAuthenticated, authToken, setPlayer, setAuthToken, logout } = useGameStore(
    (state) => ({
      player: state.player,
      isAuthenticated: state.isAuthenticated,
      authToken: state.authToken,
      setPlayer: state.setPlayer,
      setAuthToken: state.setAuthToken,
      logout: state.logout,
    })
  )
  return { player, isAuthenticated, authToken, setPlayer, setAuthToken, logout }
}

export const useGameData = () => {
  const { gameState, worldState, setGameState, setWorldState } = useGameStore(
    (state) => ({
      gameState: state.gameState,
      worldState: state.worldState,
      setGameState: state.setGameState,
      setWorldState: state.setWorldState,
    })
  )
  return { gameState, worldState, setGameState, setWorldState }
}

export const useCombat = () => {
  const { combatState, setCombatState, updateMonsterHP } = useGameStore(
    (state) => ({
      combatState: state.combatState,
      setCombatState: state.setCombatState,
      updateMonsterHP: state.updateMonsterHP,
    })
  )
  return { combatState, setCombatState, updateMonsterHP }
}

export const useUI = () => {
  const { ui, setScreen, setLoading, setError, addNotification, removeNotification } = useGameStore(
    (state) => ({
      ui: state.ui,
      setScreen: state.setScreen,
      setLoading: state.setLoading,
      setError: state.setError,
      addNotification: state.addNotification,
      removeNotification: state.removeNotification,
    })
  )
  return { ui, setScreen, setLoading, setError, addNotification, removeNotification }
}

export const useConnection = () => {
  const { isConnected, setConnected, error, setError } = useGameStore(
    (state) => ({
      isConnected: state.isConnected,
      setConnected: state.setConnected,
      error: state.error,
      setError: state.setError,
    })
  )
  return { isConnected, setConnected, error, setError }
}

// Subscribe to auth changes for persistence
useGameStore.subscribe(
  (state) => state.authToken,
  (token) => {
    if (token) {
      localStorage.setItem('authToken', token)
    } else {
      localStorage.removeItem('authToken')
    }
  }
)

// Initialize auth token from localStorage
const savedToken = localStorage.getItem('authToken')
if (savedToken) {
  useGameStore.getState().setAuthToken(savedToken)
}