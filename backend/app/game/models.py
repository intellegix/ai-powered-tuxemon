# Game Models for AI-Powered Tuxemon
# Austin Kidwell | Intellegix | Mobile-First Pokemon-Style Game

from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator
from sqlmodel import SQLModel, Field as SQLField, Relationship


# Enums
class ElementType(str, Enum):
    NORMAL = "normal"
    FIRE = "fire"
    WATER = "water"
    GRASS = "grass"
    ELECTRIC = "electric"
    PSYCHIC = "psychic"
    ICE = "ice"
    DRAGON = "dragon"
    DARK = "dark"
    FIGHTING = "fighting"
    POISON = "poison"
    GROUND = "ground"
    FLYING = "flying"
    BUG = "bug"
    ROCK = "rock"
    GHOST = "ghost"
    STEEL = "steel"


class MonsterShape(str, Enum):
    AQUATIC = "aquatic"
    BLOB = "blob"
    BRUTE = "brute"
    DRAGON = "dragon"
    FLIER = "flier"
    GRUB = "grub"
    HUMANOID = "humanoid"
    HUNTER = "hunter"
    LANDRACE = "landrace"
    LEVIATHAN = "leviathan"
    POLLIWOG = "polliwog"
    SERPENT = "serpent"
    SPRITE = "sprite"
    VARMINT = "varmint"


class CombatPhase(str, Enum):
    WAITING = "waiting"
    ACTION_SELECTION = "action_selection"
    EXECUTING = "executing"
    VICTORY = "victory"
    DEFEAT = "defeat"


# Base Game Models
class MonsterStats(BaseModel):
    """Base stats for monsters."""
    hp: int = Field(ge=1, le=999)
    armour: int = Field(ge=1, le=100)
    dodge: int = Field(ge=1, le=100)
    melee: int = Field(ge=1, le=100)
    ranged: int = Field(ge=1, le=100)
    speed: int = Field(ge=1, le=100)


class MonsterBase(SQLModel, table=True):
    """Database model for monster species data."""
    __tablename__ = "monster_species"

    id: Optional[int] = SQLField(default=None, primary_key=True)
    slug: str = SQLField(unique=True, index=True)
    name: str
    description: str
    element_types: str  # JSON array of ElementType
    shape: MonsterShape
    base_stats: str  # JSON MonsterStats
    sprite_name: str
    capture_rate: float = Field(ge=0.0, le=1.0)
    growth_rate: str = "medium"

    # Evolution data
    evolves_from: Optional[str] = None
    evolves_to: str = "{}"  # JSON dict of evolution conditions

    created_at: datetime = SQLField(default_factory=datetime.utcnow)


class Monster(SQLModel, table=True):
    """Database model for individual monster instances."""
    __tablename__ = "monsters"

    id: Optional[UUID] = SQLField(default_factory=uuid4, primary_key=True)

    # Base data
    species_slug: str = SQLField(foreign_key="monster_species.slug")
    name: str
    level: int = Field(ge=1, le=999)

    # Stats and status
    current_hp: int = Field(ge=0)
    total_experience: int = Field(ge=0)
    status_effects: str = "{}"  # JSON list of status effects

    # Ownership
    player_id: Optional[UUID] = SQLField(foreign_key="players.id")
    npc_id: Optional[UUID] = SQLField(foreign_key="npcs.id")

    # Customization
    flairs: str = "{}"  # JSON list of visual customizations
    personality_traits: str = "{}"  # JSON dict for AI personality

    # Metadata
    obtained_at: datetime = SQLField(default_factory=datetime.utcnow)
    last_battle: Optional[datetime] = None
    times_battled: int = 0

    # Relationships
    player: Optional["Player"] = Relationship(back_populates="monsters")
    npc: Optional["NPC"] = Relationship(back_populates="monsters")


class Player(SQLModel, table=True):
    """Database model for players."""
    __tablename__ = "players"

    id: Optional[UUID] = SQLField(default_factory=uuid4, primary_key=True)
    username: str = SQLField(unique=True, index=True)
    email: str = SQLField(unique=True, index=True)
    hashed_password: str

    # Game state
    current_map: str = "starting_town"
    position_x: int = 0
    position_y: int = 0
    money: int = 0

    # Progress
    story_progress: str = "{}"  # JSON dict of story flags
    play_time_seconds: int = 0

    # Relationships
    npc_relationships: str = "{}"  # JSON dict of NPC favorability scores

    # Metadata
    created_at: datetime = SQLField(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    is_active: bool = True

    # Relationships
    monsters: List[Monster] = Relationship(back_populates="player")


class NPC(SQLModel, table=True):
    """Database model for NPCs with AI capabilities."""
    __tablename__ = "npcs"

    id: Optional[UUID] = SQLField(default_factory=uuid4, primary_key=True)

    # Basic info
    slug: str = SQLField(unique=True, index=True)
    name: str
    sprite_name: str

    # Position and state
    map_name: str
    position_x: int
    position_y: int
    facing_direction: str = "down"

    # AI Configuration
    ai_enabled: bool = True
    personality_traits: str = "{}"  # JSON PersonalityTraits
    dialogue_mode: str = "hybrid"  # ai, scripted, hybrid
    memory_retention: float = Field(ge=0.0, le=1.0, default=0.8)

    # Game mechanics
    is_trainer: bool = False
    can_battle: bool = False
    shop_items: str = "{}"  # JSON list of shop items

    # Schedule and behavior
    schedule: str = "{}"  # JSON daily schedule
    approachable: bool = True

    # Metadata
    created_at: datetime = SQLField(default_factory=datetime.utcnow)
    last_interaction: Optional[datetime] = None
    total_interactions: int = 0

    # Relationships
    monsters: List[Monster] = Relationship(back_populates="npc")


class CombatSession(SQLModel, table=True):
    """Database model for combat sessions."""
    __tablename__ = "combat_sessions"

    id: Optional[UUID] = SQLField(default_factory=uuid4, primary_key=True)

    # Participants
    player_id: UUID = SQLField(foreign_key="players.id")
    opponent_npc_id: Optional[UUID] = SQLField(foreign_key="npcs.id")

    # Combat state
    phase: CombatPhase = CombatPhase.WAITING
    current_turn: int = 0
    turn_queue: str = "[]"  # JSON list of pending actions

    # Environment
    weather: Optional[str] = None
    field_effects: str = "[]"  # JSON list of active field effects

    # Metadata
    started_at: datetime = SQLField(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    winner: Optional[str] = None  # "player" or "npc"


# Pydantic Models for API
class PersonalityTraits(BaseModel):
    """AI personality traits for NPCs."""
    curiosity: float = Field(ge=0.0, le=1.0, default=0.5)
    patience: float = Field(ge=0.0, le=1.0, default=0.5)
    verbosity: float = Field(ge=0.0, le=1.0, default=0.5)
    humor: float = Field(ge=0.0, le=1.0, default=0.5)
    trust_threshold: float = Field(ge=0.0, le=1.0, default=0.3)
    friendliness: float = Field(ge=0.0, le=1.0, default=0.5)
    competitiveness: float = Field(ge=0.0, le=1.0, default=0.5)
    knowledge_sharing: float = Field(ge=0.0, le=1.0, default=0.5)


class AIConfig(BaseModel):
    """AI configuration for NPCs."""
    enabled: bool = True
    personality_traits: PersonalityTraits
    dialogue_mode: str = "hybrid"  # "ai", "scripted", "hybrid"
    memory_retention: float = Field(ge=0.0, le=1.0, default=0.8)
    max_memory_items: int = 100
    response_delay_ms: int = Field(ge=0, le=5000, default=1000)


class GameState(BaseModel):
    """Current game state for a player."""
    player_id: UUID
    current_map: str
    position: Tuple[int, int]
    party: List[Dict[str, Any]]
    inventory: List[Dict[str, Any]]
    money: int
    story_progress: Dict[str, bool]
    npc_relationships: Dict[str, float]
    play_time_seconds: int


class NPCInteractionContext(BaseModel):
    """Context for NPC interactions."""
    player_id: UUID
    npc_id: UUID
    interaction_type: str  # "dialogue", "battle", "shop"
    player_position: Tuple[int, int]
    player_party_summary: str
    recent_achievements: List[str]
    relationship_level: float
    time_of_day: str


class DialogueResponse(BaseModel):
    """AI-generated dialogue response."""
    text: str
    emotion: str = "neutral"
    actions: List[str] = []
    relationship_change: float = 0.0
    triggers_battle: bool = False
    shop_items: Optional[List[str]] = None


class CombatAction(BaseModel):
    """Combat action from player or AI."""
    actor_id: UUID
    action_type: str  # "attack", "switch", "item", "flee"
    target_id: Optional[UUID] = None
    technique_slug: Optional[str] = None
    item_slug: Optional[str] = None
    monster_switch_to: Optional[UUID] = None


class MemoryItem(BaseModel):
    """Single memory item for NPCs."""
    id: UUID = Field(default_factory=uuid4)
    npc_id: UUID
    player_id: UUID
    content: str
    importance: float = Field(ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tags: List[str] = []
    emotional_context: str = "neutral"


class WorldState(BaseModel):
    """Current world state for mobile client."""
    map_name: str
    npcs_nearby: List[Dict[str, Any]]
    interactive_objects: List[Dict[str, Any]]
    weather: Optional[str] = None
    time_of_day: str
    player_can_move: bool = True


# Import inventory and shop models
from app.game.items import ItemBase, PlayerInventorySlot
from app.game.economy import ShopTransaction, ShopInventorySlot