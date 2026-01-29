// WebSocket Service for AI-Powered Tuxemon Frontend
// Austin Kidwell | Intellegix | Mobile-First Pokemon-Style Game

import { io, Socket } from 'socket.io-client'
import { useGameStore } from '../hooks/useGameStore'
import type { WebSocketEvent } from '../types/game'

class WebSocketService {
  private socket: Socket | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  private isConnecting = false

  constructor() {
    this.setupEventListeners()
  }

  connect(authToken?: string): void {
    if (this.socket?.connected || this.isConnecting) {
      return
    }

    this.isConnecting = true
    const wsURL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'

    this.socket = io(wsURL, {
      auth: {
        token: authToken || localStorage.getItem('authToken'),
      },
      transports: ['websocket', 'polling'],
      timeout: 10000,
      forceNew: true,
    })

    this.setupSocketListeners()
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
    }
    this.isConnecting = false
    this.reconnectAttempts = 0
    useGameStore.getState().setConnected(false)
  }

  private setupSocketListeners(): void {
    if (!this.socket) return

    this.socket.on('connect', () => {
      console.log('✅ WebSocket connected')
      this.isConnecting = false
      this.reconnectAttempts = 0
      useGameStore.getState().setConnected(true)
      useGameStore.getState().setError(null)

      // Send initial player position for proximity tracking
      this.sendPlayerUpdate()
    })

    this.socket.on('disconnect', (reason) => {
      console.log('❌ WebSocket disconnected:', reason)
      useGameStore.getState().setConnected(false)

      // Auto-reconnect unless disconnected intentionally
      if (reason !== 'io client disconnect' && this.reconnectAttempts < this.maxReconnectAttempts) {
        this.scheduleReconnect()
      }
    })

    this.socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error)
      this.isConnecting = false
      useGameStore.getState().setConnected(false)
      useGameStore.getState().setError('Connection failed')

      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.scheduleReconnect()
      }
    })

    // Game event listeners
    this.socket.on('world_update', (data) => {
      useGameStore.getState().setWorldState(data)
    })

    this.socket.on('npc_dialogue', (data) => {
      const { npcId, dialogue } = data
      useGameStore.getState().updateNPCDialogue(npcId, dialogue)

      // Show notification for AI responses
      useGameStore.getState().addNotification({
        type: 'info',
        title: 'NPC Response',
        message: dialogue.text.substring(0, 50) + '...',
        duration: 3000,
      })
    })

    this.socket.on('combat_update', (data) => {
      useGameStore.getState().setCombatState(data)
    })

    this.socket.on('player_moved', (data) => {
      // Handle other players moving (for future multiplayer features)
      console.log('Player moved:', data)
    })

    this.socket.on('notification', (data) => {
      useGameStore.getState().addNotification(data)
    })

    this.socket.on('error', (data) => {
      console.error('WebSocket error:', data)
      useGameStore.getState().setError(data.message)
    })

    // AI-specific events
    this.socket.on('ai_dialogue_stream', (data) => {
      // Handle streaming AI dialogue responses
      const { npcId, chunk, isComplete } = data
      // TODO: Implement streaming dialogue updates
    })

    this.socket.on('ai_processing', (data) => {
      // Show loading indicator for AI processing
      const { npcId, processing } = data
      if (processing) {
        useGameStore.getState().addNotification({
          type: 'info',
          title: 'AI Thinking...',
          message: 'NPC is generating a response',
          duration: undefined, // Will be removed when processing completes
        })
      }
    })
  }

  private setupEventListeners(): void {
    // Listen for auth changes to reconnect with new token
    useGameStore.subscribe(
      (state) => state.authToken,
      (token) => {
        if (token && !this.socket?.connected) {
          this.connect(token)
        } else if (!token && this.socket?.connected) {
          this.disconnect()
        }
      }
    )

    // Listen for player position changes to send updates
    useGameStore.subscribe(
      (state) => state.gameState?.position,
      () => {
        this.sendPlayerUpdate()
      }
    )
  }

  private scheduleReconnect(): void {
    this.reconnectAttempts++
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1)

    console.log(`🔄 Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`)

    setTimeout(() => {
      if (this.reconnectAttempts <= this.maxReconnectAttempts) {
        const token = localStorage.getItem('authToken')
        if (token) {
          this.connect(token)
        }
      }
    }, delay)
  }

  // Public methods for sending events
  sendPlayerUpdate(): void {
    if (!this.socket?.connected) return

    const gameState = useGameStore.getState().gameState
    if (!gameState) return

    this.socket.emit('player_update', {
      position: gameState.position,
      map: gameState.currentMap,
      timestamp: Date.now(),
    })
  }

  sendChatMessage(message: string, npcId?: string): void {
    if (!this.socket?.connected) return

    this.socket.emit('chat_message', {
      message,
      npcId,
      timestamp: Date.now(),
    })
  }

  sendCombatAction(action: any): void {
    if (!this.socket?.connected) return

    this.socket.emit('combat_action', action)
  }

  sendNPCInteraction(npcId: string, interactionType: string): void {
    if (!this.socket?.connected) return

    this.socket.emit('npc_interaction', {
      npcId,
      interactionType,
      timestamp: Date.now(),
    })
  }

  // Utility methods
  isConnected(): boolean {
    return this.socket?.connected || false
  }

  getConnectionState(): 'connected' | 'connecting' | 'disconnected' | 'error' {
    if (this.socket?.connected) return 'connected'
    if (this.isConnecting) return 'connecting'
    if (this.reconnectAttempts > 0 && this.reconnectAttempts < this.maxReconnectAttempts) return 'connecting'
    return 'disconnected'
  }

  // Performance monitoring
  measureLatency(): Promise<number> {
    return new Promise((resolve) => {
      if (!this.socket?.connected) {
        resolve(-1)
        return
      }

      const start = Date.now()
      this.socket.emit('ping', start, (response: number) => {
        const latency = Date.now() - response
        resolve(latency)
      })

      // Timeout after 5 seconds
      setTimeout(() => resolve(-1), 5000)
    })
  }

  // Debugging helpers
  enableDebugMode(): void {
    if (this.socket) {
      this.socket.onAny((eventName, ...args) => {
        console.log(`📡 WebSocket event: ${eventName}`, args)
      })
    }
  }

  getSocketInfo(): any {
    if (!this.socket) return null

    return {
      id: this.socket.id,
      connected: this.socket.connected,
      transport: this.socket.io.engine.transport.name,
      reconnectAttempts: this.reconnectAttempts,
    }
  }
}

// Create singleton instance
export const webSocketService = new WebSocketService()

// React hook for WebSocket status
export const useWebSocket = () => {
  const { isConnected, setConnected } = useGameStore((state) => ({
    isConnected: state.isConnected,
    setConnected: state.setConnected,
  }))

  return {
    isConnected,
    connectionState: webSocketService.getConnectionState(),
    connect: webSocketService.connect.bind(webSocketService),
    disconnect: webSocketService.disconnect.bind(webSocketService),
    sendPlayerUpdate: webSocketService.sendPlayerUpdate.bind(webSocketService),
    sendChatMessage: webSocketService.sendChatMessage.bind(webSocketService),
    sendCombatAction: webSocketService.sendCombatAction.bind(webSocketService),
    sendNPCInteraction: webSocketService.sendNPCInteraction.bind(webSocketService),
    measureLatency: webSocketService.measureLatency.bind(webSocketService),
  }
}

export default webSocketService