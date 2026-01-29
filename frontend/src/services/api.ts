// API Service for AI-Powered Tuxemon Frontend
// Austin Kidwell | Intellegix | Mobile-First Pokemon-Style Game

import axios, { AxiosInstance, AxiosResponse } from 'axios'
import type {
  Player,
  GameState,
  WorldState,
  CombatState,
  DialogueResponse,
  NPC,
  Monster,
  AuthTokens,
  LoginCredentials,
  RegisterData,
  APIResponse,
  CombatAction,
} from '../types/game'

class ApiService {
  private client: AxiosInstance
  private baseURL: string

  constructor() {
    this.baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

    this.client = axios.create({
      baseURL: this.baseURL,
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Request interceptor to add auth token
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('authToken')
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => {
        return Promise.reject(error)
      }
    )

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          // Token expired or invalid
          localStorage.removeItem('authToken')
          window.location.href = '/login'
        }
        return Promise.reject(error)
      }
    )
  }

  // Authentication endpoints
  async login(credentials: LoginCredentials): Promise<AuthTokens> {
    const response: AxiosResponse<AuthTokens> = await this.client.post('/auth/login', credentials)
    return response.data
  }

  async register(userData: RegisterData): Promise<AuthTokens> {
    const response: AxiosResponse<AuthTokens> = await this.client.post('/auth/register', userData)
    return response.data
  }

  async getProfile(): Promise<Player> {
    const response: AxiosResponse<Player> = await this.client.get('/auth/profile')
    return response.data
  }

  async refreshToken(): Promise<AuthTokens> {
    const response: AxiosResponse<AuthTokens> = await this.client.post('/auth/refresh')
    return response.data
  }

  async logout(): Promise<void> {
    await this.client.post('/auth/logout')
  }

  // Game state endpoints
  async getWorldState(): Promise<WorldState> {
    const response: AxiosResponse<WorldState> = await this.client.get('/game/world')
    return response.data
  }

  async getPlayerState(): Promise<GameState> {
    const response: AxiosResponse<GameState> = await this.client.get('/game/player')
    return response.data
  }

  async saveGameState(gameData: {
    currentMap: string
    positionX: number
    positionY: number
    storyProgress: Record<string, boolean>
    playTimeSeconds: number
  }): Promise<void> {
    await this.client.post('/game/save', gameData)
  }

  async movePlayer(movement: {
    newX: number
    newY: number
    newMap?: string
  }): Promise<{ message: string; newPosition: [number, number]; newMap: string }> {
    const response = await this.client.post('/game/move', movement)
    return response.data
  }

  async getMonsterSpecies(): Promise<{ species: any[] }> {
    const response = await this.client.get('/game/monsters/species')
    return response.data
  }

  async setMonsterNickname(monsterId: string, nickname: string): Promise<void> {
    await this.client.post(`/game/monsters/${monsterId}/nickname`, { nickname })
  }

  // NPC endpoints
  async getNearbyNPCs(params: {
    mapName: string
    playerX: number
    playerY: number
    radius?: number
  }): Promise<NPC[]> {
    const response: AxiosResponse<NPC[]> = await this.client.get('/npcs/nearby', { params })
    return response.data
  }

  async getNPCInfo(npcId: string): Promise<NPC> {
    const response: AxiosResponse<NPC> = await this.client.get(`/npcs/${npcId}`)
    return response.data
  }

  async interactWithNPC(npcId: string, interaction: {
    interactionType: string
    playerPartySummary: string
    recentAchievements?: string[]
  }): Promise<DialogueResponse> {
    const response: AxiosResponse<DialogueResponse> = await this.client.post(
      `/npcs/${npcId}/interact`,
      interaction
    )
    return response.data
  }

  async getNPCMemories(npcId: string): Promise<{
    memories: any[]
    totalInteractions: number
    relationshipLevel: number
    favoriteTopics: string[]
  }> {
    const response = await this.client.get(`/npcs/${npcId}/memories`)
    return response.data
  }

  // Combat endpoints
  async startBattle(battleData: {
    opponentNpcId: string
    playerMonsterIds: string[]
  }): Promise<CombatState> {
    const response: AxiosResponse<CombatState> = await this.client.post('/combat/start', battleData)
    return response.data
  }

  async submitCombatAction(action: {
    battleId: string
    actionType: string
    targetId?: string
    techniqueSlug?: string
    itemSlug?: string
    monsterSwitchTo?: string
  }): Promise<CombatState> {
    const response: AxiosResponse<CombatState> = await this.client.post('/combat/action', action)
    return response.data
  }

  async getCombatState(battleId: string): Promise<CombatState> {
    const response: AxiosResponse<CombatState> = await this.client.get(`/combat/${battleId}/state`)
    return response.data
  }

  async forfeitBattle(battleId: string): Promise<void> {
    await this.client.post(`/combat/${battleId}/forfeit`)
  }

  // Health check
  async healthCheck(): Promise<{
    status: string
    timestamp: number
    services: Record<string, string>
    version: string
  }> {
    const response = await this.client.get('/health')
    return response.data
  }

  // Utility methods
  setAuthToken(token: string): void {
    this.client.defaults.headers.common['Authorization'] = `Bearer ${token}`
  }

  clearAuthToken(): void {
    delete this.client.defaults.headers.common['Authorization']
  }

  getBaseURL(): string {
    return this.baseURL
  }

  // File upload for avatar/sprites (if needed later)
  async uploadFile(file: File, endpoint: string): Promise<{ url: string }> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await this.client.post(endpoint, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  }

  // Stream support for real-time features
  createEventSource(endpoint: string): EventSource {
    const token = localStorage.getItem('authToken')
    const url = `${this.baseURL}${endpoint}?token=${encodeURIComponent(token || '')}`
    return new EventSource(url)
  }
}

// Create singleton instance
export const apiService = new ApiService()

// React Query configuration
export const queryConfig = {
  queries: {
    retry: (failureCount: number, error: any) => {
      // Don't retry on auth errors
      if (error?.response?.status === 401 || error?.response?.status === 403) {
        return false
      }
      // Retry up to 3 times for other errors
      return failureCount < 3
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
    gcTime: 1000 * 60 * 30, // 30 minutes
  },
  mutations: {
    retry: false,
  },
}

// React Query hooks
export const useApiQuery = <T>(
  queryKey: string[],
  queryFn: () => Promise<T>,
  options?: any
) => {
  return {
    queryKey,
    queryFn,
    ...queryConfig.queries,
    ...options,
  }
}

export default apiService