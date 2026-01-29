// Game Types for AI-Powered Tuxemon Frontend
// Austin Kidwell | Intellegix | Mobile-First Pokemon-Style Game

export interface Player {
  id: string
  username: string
  email: string
  currentMap: string
  money: number
  playTimeSeconds: number
  createdAt: string
  lastLogin: string | null
}

export interface Monster {
  id: string
  speciesSlug: string
  name: string
  level: number
  currentHp: number
  maxHp: number
  elementTypes: ElementType[]
  spriteUrl: string
  totalExperience: number
  statusEffects: StatusEffect[]
  flairs: string[]
}

export interface NPC {
  id: string
  slug: string
  name: string
  spriteName: string
  position: [number, number]
  facingDirection: Direction
  isTrainer: boolean
  canBattle: boolean
  approachable: boolean
  relationshipLevel: number
}

export interface DialogueResponse {
  text: string
  emotion: Emotion
  actions: string[]
  relationshipChange: number
  triggersBattle: boolean
  shopItems?: string[]
}

export interface GameState {
  playerId: string
  currentMap: string
  position: [number, number]
  party: Monster[]
  inventory: InventoryItem[]
  money: number
  storyProgress: Record<string, boolean>
  npcRelationships: Record<string, number>
  playTimeSeconds: number
}

export interface WorldState {
  mapName: string
  npcsNearby: NPC[]
  interactiveObjects: InteractiveObject[]
  weather: Weather | null
  timeOfDay: TimeOfDay
  playerCanMove: boolean
}

export interface CombatState {
  battleId: string
  phase: CombatPhase
  participants: CombatParticipant[]
  currentTurn: number
  turnQueue: CombatAction[]
  weather: Weather | null
  fieldEffects: string[]
  battleLog: string[]
  canAct: boolean
  validActions: string[]
}

export interface CombatParticipant {
  id: string
  name: string
  isPlayer: boolean
  activeMonster: Monster | null
  party: Monster[]
  defeated: boolean
}

export interface CombatAction {
  actorId: string
  actionType: 'attack' | 'switch' | 'item' | 'flee'
  targetId?: string
  techniqueSlug?: string
  itemSlug?: string
  monsterSwitchTo?: string
}

export interface InventoryItem {
  slug: string
  name: string
  quantity: number
  description: string
  icon: string
}

export interface InteractiveObject {
  id: string
  type: 'chest' | 'sign' | 'door' | 'item'
  position: [number, number]
  interactable: boolean
  sprite: string
}

// Enums
export enum ElementType {
  NORMAL = 'normal',
  FIRE = 'fire',
  WATER = 'water',
  GRASS = 'grass',
  ELECTRIC = 'electric',
  PSYCHIC = 'psychic',
  ICE = 'ice',
  DRAGON = 'dragon',
  DARK = 'dark',
  FIGHTING = 'fighting',
  POISON = 'poison',
  GROUND = 'ground',
  FLYING = 'flying',
  BUG = 'bug',
  ROCK = 'rock',
  GHOST = 'ghost',
  STEEL = 'steel',
}

export enum Direction {
  UP = 'up',
  DOWN = 'down',
  LEFT = 'left',
  RIGHT = 'right',
}

export enum Emotion {
  NEUTRAL = 'neutral',
  HAPPY = 'happy',
  EXCITED = 'excited',
  SAD = 'sad',
  ANGRY = 'angry',
  CONFUSED = 'confused',
  SHY = 'shy',
  PROUD = 'proud',
}

export enum CombatPhase {
  WAITING = 'waiting',
  ACTION_SELECTION = 'action_selection',
  EXECUTING = 'executing',
  VICTORY = 'victory',
  DEFEAT = 'defeat',
}

export enum Weather {
  SUNNY = 'sunny',
  RAINY = 'rainy',
  STORMY = 'stormy',
  SNOWY = 'snowy',
  FOGGY = 'foggy',
}

export enum TimeOfDay {
  MORNING = 'morning',
  AFTERNOON = 'afternoon',
  EVENING = 'evening',
  NIGHT = 'night',
}

export interface StatusEffect {
  slug: string
  name: string
  description: string
  turnsRemaining: number
  severity: 'minor' | 'major' | 'critical'
}

// Touch and UI Types
export interface TouchPosition {
  x: number
  y: number
  timestamp: number
}

export interface GestureEvent {
  type: 'tap' | 'longpress' | 'swipe' | 'pinch'
  position: TouchPosition
  direction?: Direction
  distance?: number
  scale?: number
}

export interface UIState {
  activeScreen: Screen
  dialogueOpen: boolean
  menuOpen: boolean
  combatMode: boolean
  loading: boolean
  error: string | null
  notifications: Notification[]
}

export enum Screen {
  MENU = 'menu',
  GAME = 'game',
  COMBAT = 'combat',
  INVENTORY = 'inventory',
  SETTINGS = 'settings',
  PROFILE = 'profile',
}

export interface Notification {
  id: string
  type: 'info' | 'success' | 'warning' | 'error'
  title: string
  message: string
  duration?: number
  actions?: NotificationAction[]
}

export interface NotificationAction {
  label: string
  action: () => void
  style?: 'primary' | 'secondary' | 'danger'
}

// WebSocket Events
export type WebSocketEvent =
  | { type: 'world_update'; data: WorldState }
  | { type: 'npc_dialogue'; data: { npcId: string; dialogue: DialogueResponse } }
  | { type: 'combat_update'; data: CombatState }
  | { type: 'player_moved'; data: { playerId: string; position: [number, number]; map: string } }
  | { type: 'notification'; data: Notification }
  | { type: 'error'; data: { message: string; code?: string } }

// API Response Types
export interface APIResponse<T> {
  data: T
  message?: string
  error?: string
  timestamp: number
}

export interface AuthTokens {
  accessToken: string
  tokenType: string
  expiresIn: number
}

export interface LoginCredentials {
  username: string
  password: string
}

export interface RegisterData {
  username: string
  email: string
  password: string
}

// Performance and Analytics
export interface PerformanceMetrics {
  fps: number
  renderTime: number
  networkLatency: number
  memoryUsage: number
  batteryLevel?: number
}

export interface AnalyticsEvent {
  event: string
  properties: Record<string, any>
  timestamp: number
  sessionId: string
  playerId?: string
}