# Emotional State System for AI-Powered Tuxemon NPCs
# Austin Kidwell | Intellegix | Mobile-First Pokemon-Style Game

import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, update
from loguru import logger

from app.game.models import NPC


class EmotionalState(str, Enum):
    """Core emotional states for NPCs."""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    EXCITED = "excited"
    CONTENT = "content"
    SAD = "sad"
    ANGRY = "angry"
    FRUSTRATED = "frustrated"
    CONFUSED = "confused"
    WORRIED = "worried"
    GRATEFUL = "grateful"
    PROUD = "proud"


class StimulusType(str, Enum):
    """Types of stimuli that can trigger emotional responses."""
    BATTLE_WON = "battle_won"
    BATTLE_LOST = "battle_lost"
    GIFT_RECEIVED = "gift_received"
    COMPLIMENT_RECEIVED = "compliment_received"
    INSULT_RECEIVED = "insult_received"
    ACHIEVEMENT_WITNESSED = "achievement_witnessed"
    FRIENDSHIP_INCREASED = "friendship_increased"
    FRIENDSHIP_DECREASED = "friendship_decreased"
    SURPRISE_ENCOUNTER = "surprise_encounter"
    QUEST_COMPLETED = "quest_completed"
    QUEST_FAILED = "quest_failed"
    MONSTER_EVOLVED = "monster_evolved"
    RARE_ITEM_FOUND = "rare_item_found"
    WEATHER_CHANGED = "weather_changed"
    TIME_PASSED = "time_passed"


class EmotionalStimulus(BaseModel):
    """A stimulus that can affect NPC emotional state."""
    stimulus_type: StimulusType
    intensity: float = Field(ge=0.0, le=1.0, description="Intensity of the stimulus")
    source_player_id: Optional[UUID] = None
    source_description: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    context: Dict = Field(default_factory=dict)


class EmotionalEffect(BaseModel):
    """Effect of a stimulus on emotional state."""
    target_emotion: EmotionalState
    magnitude: float = Field(ge=-1.0, le=1.0, description="Change in emotion intensity")
    duration_hours: float = Field(ge=0.0, le=168.0, default=2.0)  # Max 1 week


class NPCEmotionalState(BaseModel):
    """Current emotional state of an NPC."""
    npc_id: UUID
    primary_emotion: EmotionalState = EmotionalState.NEUTRAL
    emotion_intensity: float = Field(ge=0.0, le=1.0, default=0.5)
    secondary_emotion: Optional[EmotionalState] = None
    secondary_intensity: float = Field(ge=0.0, le=1.0, default=0.0)

    # Emotional history
    recent_stimuli: List[EmotionalStimulus] = Field(default_factory=list, max_items=10)
    last_update: datetime = Field(default_factory=datetime.utcnow)

    # Personality modifiers
    emotional_volatility: float = Field(ge=0.0, le=1.0, default=0.5)  # How quickly emotions change
    emotional_recovery: float = Field(ge=0.0, le=1.0, default=0.3)   # How quickly emotions return to baseline
    baseline_mood: EmotionalState = EmotionalState.NEUTRAL


class EmotionalStateManager:
    """Manages NPC emotional states and responses to stimuli."""

    def __init__(self):
        self.emotion_decay_rate = 0.1  # Emotions decay by 10% per hour by default
        self.stimulus_rules = self._initialize_stimulus_rules()

    def _initialize_stimulus_rules(self) -> Dict[StimulusType, List[EmotionalEffect]]:
        """Initialize rules for how stimuli affect emotions."""
        return {
            StimulusType.BATTLE_WON: [
                EmotionalEffect(target_emotion=EmotionalState.HAPPY, magnitude=0.6, duration_hours=3.0),
                EmotionalEffect(target_emotion=EmotionalState.PROUD, magnitude=0.4, duration_hours=2.0),
            ],
            StimulusType.BATTLE_LOST: [
                EmotionalEffect(target_emotion=EmotionalState.SAD, magnitude=0.5, duration_hours=2.0),
                EmotionalEffect(target_emotion=EmotionalState.FRUSTRATED, magnitude=0.3, duration_hours=1.0),
            ],
            StimulusType.GIFT_RECEIVED: [
                EmotionalEffect(target_emotion=EmotionalState.GRATEFUL, magnitude=0.7, duration_hours=4.0),
                EmotionalEffect(target_emotion=EmotionalState.HAPPY, magnitude=0.5, duration_hours=2.0),
            ],
            StimulusType.COMPLIMENT_RECEIVED: [
                EmotionalEffect(target_emotion=EmotionalState.HAPPY, magnitude=0.4, duration_hours=1.5),
                EmotionalEffect(target_emotion=EmotionalState.PROUD, magnitude=0.3, duration_hours=1.0),
            ],
            StimulusType.INSULT_RECEIVED: [
                EmotionalEffect(target_emotion=EmotionalState.ANGRY, magnitude=0.6, duration_hours=2.0),
                EmotionalEffect(target_emotion=EmotionalState.SAD, magnitude=0.3, duration_hours=1.0),
            ],
            StimulusType.ACHIEVEMENT_WITNESSED: [
                EmotionalEffect(target_emotion=EmotionalState.EXCITED, magnitude=0.4, duration_hours=1.0),
                EmotionalEffect(target_emotion=EmotionalState.PROUD, magnitude=0.2, duration_hours=0.5),
            ],
            StimulusType.FRIENDSHIP_INCREASED: [
                EmotionalEffect(target_emotion=EmotionalState.HAPPY, magnitude=0.5, duration_hours=3.0),
                EmotionalEffect(target_emotion=EmotionalState.CONTENT, magnitude=0.3, duration_hours=2.0),
            ],
            StimulusType.FRIENDSHIP_DECREASED: [
                EmotionalEffect(target_emotion=EmotionalState.SAD, magnitude=0.4, duration_hours=2.0),
                EmotionalEffect(target_emotion=EmotionalState.WORRIED, magnitude=0.3, duration_hours=1.5),
            ],
            StimulusType.SURPRISE_ENCOUNTER: [
                EmotionalEffect(target_emotion=EmotionalState.EXCITED, magnitude=0.6, duration_hours=1.0),
                EmotionalEffect(target_emotion=EmotionalState.CONFUSED, magnitude=0.2, duration_hours=0.5),
            ],
            StimulusType.QUEST_COMPLETED: [
                EmotionalEffect(target_emotion=EmotionalState.PROUD, magnitude=0.8, duration_hours=4.0),
                EmotionalEffect(target_emotion=EmotionalState.CONTENT, magnitude=0.5, duration_hours=2.0),
            ],
            StimulusType.QUEST_FAILED: [
                EmotionalEffect(target_emotion=EmotionalState.FRUSTRATED, magnitude=0.7, duration_hours=3.0),
                EmotionalEffect(target_emotion=EmotionalState.SAD, magnitude=0.4, duration_hours=2.0),
            ],
            StimulusType.MONSTER_EVOLVED: [
                EmotionalEffect(target_emotion=EmotionalState.EXCITED, magnitude=0.9, duration_hours=5.0),
                EmotionalEffect(target_emotion=EmotionalState.PROUD, magnitude=0.6, duration_hours=3.0),
            ],
            StimulusType.RARE_ITEM_FOUND: [
                EmotionalEffect(target_emotion=EmotionalState.EXCITED, magnitude=0.7, duration_hours=2.0),
                EmotionalEffect(target_emotion=EmotionalState.HAPPY, magnitude=0.5, duration_hours=1.0),
            ],
        }

    async def get_npc_emotional_state(
        self,
        db: AsyncSession,
        npc_id: UUID,
    ) -> NPCEmotionalState:
        """Get current emotional state of an NPC."""
        try:
            # Get NPC from database
            result = await db.execute(select(NPC).where(NPC.id == npc_id))
            npc = result.scalar_one_or_none()

            if not npc:
                raise ValueError(f"NPC {npc_id} not found")

            # Parse personality traits to get emotional modifiers
            personality_data = json.loads(npc.personality_traits or "{}")
            emotional_volatility = personality_data.get("curiosity", 0.5)  # Curious NPCs are more emotionally volatile
            emotional_recovery = personality_data.get("patience", 0.3)     # Patient NPCs recover emotions faster

            # Try to load existing emotional state from metadata or create default
            emotional_state_data = {}
            if hasattr(npc, 'emotional_state_json'):
                emotional_state_data = json.loads(getattr(npc, 'emotional_state_json', '{}'))

            emotional_state = NPCEmotionalState(
                npc_id=npc_id,
                primary_emotion=EmotionalState(emotional_state_data.get('primary_emotion', EmotionalState.NEUTRAL)),
                emotion_intensity=emotional_state_data.get('emotion_intensity', 0.5),
                secondary_emotion=EmotionalState(emotional_state_data.get('secondary_emotion')) if emotional_state_data.get('secondary_emotion') else None,
                secondary_intensity=emotional_state_data.get('secondary_intensity', 0.0),
                recent_stimuli=[EmotionalStimulus(**s) for s in emotional_state_data.get('recent_stimuli', [])],
                last_update=datetime.fromisoformat(emotional_state_data.get('last_update', datetime.utcnow().isoformat())),
                emotional_volatility=emotional_volatility,
                emotional_recovery=emotional_recovery,
                baseline_mood=EmotionalState(emotional_state_data.get('baseline_mood', EmotionalState.NEUTRAL)),
            )

            # Apply time-based decay
            await self._apply_emotional_decay(emotional_state)

            return emotional_state

        except Exception as e:
            logger.error(f"Error getting emotional state for NPC {npc_id}: {e}")
            # Return default neutral state
            return NPCEmotionalState(npc_id=npc_id)

    async def apply_stimulus(
        self,
        db: AsyncSession,
        npc_id: UUID,
        stimulus: EmotionalStimulus,
    ) -> NPCEmotionalState:
        """Apply an emotional stimulus to an NPC and update their state."""
        try:
            # Get current emotional state
            emotional_state = await self.get_npc_emotional_state(db, npc_id)

            # Get the effects of this stimulus
            effects = self.stimulus_rules.get(stimulus.stimulus_type, [])

            logger.info(f"Applying stimulus {stimulus.stimulus_type} to NPC {npc_id}")

            for effect in effects:
                # Modify effect based on stimulus intensity
                adjusted_magnitude = effect.magnitude * stimulus.intensity

                # Apply personality modifiers
                if emotional_state.emotional_volatility > 0.7:
                    adjusted_magnitude *= 1.3  # More volatile NPCs react stronger
                elif emotional_state.emotional_volatility < 0.3:
                    adjusted_magnitude *= 0.7  # Less volatile NPCs react weaker

                # Apply the emotional change
                if effect.target_emotion == emotional_state.primary_emotion:
                    # Intensify existing emotion
                    emotional_state.emotion_intensity = min(1.0, emotional_state.emotion_intensity + adjusted_magnitude)
                else:
                    # Switch or add secondary emotion
                    if emotional_state.emotion_intensity < 0.3 or adjusted_magnitude > 0.5:
                        # Replace primary emotion if current is weak or new stimulus is strong
                        emotional_state.secondary_emotion = emotional_state.primary_emotion
                        emotional_state.secondary_intensity = emotional_state.emotion_intensity * 0.5

                        emotional_state.primary_emotion = effect.target_emotion
                        emotional_state.emotion_intensity = min(1.0, adjusted_magnitude + 0.2)
                    else:
                        # Add as secondary emotion
                        emotional_state.secondary_emotion = effect.target_emotion
                        emotional_state.secondary_intensity = min(1.0, adjusted_magnitude)

            # Add stimulus to recent history
            emotional_state.recent_stimuli.append(stimulus)
            if len(emotional_state.recent_stimuli) > 10:
                emotional_state.recent_stimuli.pop(0)  # Keep only last 10

            emotional_state.last_update = datetime.utcnow()

            # Save to database
            await self._save_emotional_state(db, emotional_state)

            logger.info(f"NPC {npc_id} emotion updated: {emotional_state.primary_emotion} ({emotional_state.emotion_intensity:.2f})")

            return emotional_state

        except Exception as e:
            logger.error(f"Error applying stimulus to NPC {npc_id}: {e}")
            return await self.get_npc_emotional_state(db, npc_id)

    async def _apply_emotional_decay(self, emotional_state: NPCEmotionalState):
        """Apply time-based decay to emotional intensity."""
        time_since_update = datetime.utcnow() - emotional_state.last_update
        hours_passed = time_since_update.total_seconds() / 3600.0

        if hours_passed > 0:
            # Calculate decay rate (influenced by emotional recovery)
            decay_rate = self.emotion_decay_rate * (1 + emotional_state.emotional_recovery)
            decay_factor = max(0.0, 1.0 - (decay_rate * hours_passed))

            # Apply decay to primary emotion
            emotional_state.emotion_intensity *= decay_factor

            # Apply decay to secondary emotion
            if emotional_state.secondary_emotion:
                emotional_state.secondary_intensity *= decay_factor

                # Remove secondary emotion if it becomes too weak
                if emotional_state.secondary_intensity < 0.1:
                    emotional_state.secondary_emotion = None
                    emotional_state.secondary_intensity = 0.0

            # Return to baseline if emotions become very weak
            if emotional_state.emotion_intensity < 0.2:
                emotional_state.primary_emotion = emotional_state.baseline_mood
                emotional_state.emotion_intensity = 0.3

    async def _save_emotional_state(
        self,
        db: AsyncSession,
        emotional_state: NPCEmotionalState,
    ):
        """Save emotional state to the database."""
        try:
            # Serialize emotional state
            state_data = {
                "primary_emotion": emotional_state.primary_emotion,
                "emotion_intensity": emotional_state.emotion_intensity,
                "secondary_emotion": emotional_state.secondary_emotion,
                "secondary_intensity": emotional_state.secondary_intensity,
                "recent_stimuli": [s.model_dump() for s in emotional_state.recent_stimuli[-5:]],  # Keep only last 5
                "last_update": emotional_state.last_update.isoformat(),
                "emotional_volatility": emotional_state.emotional_volatility,
                "emotional_recovery": emotional_state.emotional_recovery,
                "baseline_mood": emotional_state.baseline_mood,
            }

            # For now, we'll store this in the NPC's personality_traits as a workaround
            # In a full implementation, we'd add an emotional_state_json field to the NPC table
            result = await db.execute(select(NPC).where(NPC.id == emotional_state.npc_id))
            npc = result.scalar_one_or_none()

            if npc:
                # Parse existing personality traits
                personality_data = json.loads(npc.personality_traits or "{}")
                # Add emotional state
                personality_data["_emotional_state"] = state_data
                # Save back
                npc.personality_traits = json.dumps(personality_data)
                await db.commit()

        except Exception as e:
            logger.error(f"Error saving emotional state: {e}")

    def get_emotion_influence_on_dialogue(
        self,
        emotional_state: NPCEmotionalState,
    ) -> Dict[str, any]:
        """Get how current emotional state should influence dialogue generation."""
        influence = {
            "primary_emotion": emotional_state.primary_emotion,
            "emotion_intensity": emotional_state.emotion_intensity,
            "dialogue_modifiers": {},
            "suggested_emotion_tag": emotional_state.primary_emotion,
        }

        # Map emotions to dialogue characteristics
        emotion_modifiers = {
            EmotionalState.HAPPY: {
                "tone": "cheerful and upbeat",
                "verbosity_modifier": 1.2,  # Happy NPCs talk more
                "relationship_bonus": 0.1,
            },
            EmotionalState.EXCITED: {
                "tone": "enthusiastic and energetic",
                "verbosity_modifier": 1.4,  # Excited NPCs talk a lot
                "relationship_bonus": 0.05,
            },
            EmotionalState.SAD: {
                "tone": "melancholy and subdued",
                "verbosity_modifier": 0.7,  # Sad NPCs talk less
                "relationship_bonus": -0.05,
            },
            EmotionalState.ANGRY: {
                "tone": "irritated and short",
                "verbosity_modifier": 0.8,  # Angry NPCs are more curt
                "relationship_bonus": -0.1,
            },
            EmotionalState.GRATEFUL: {
                "tone": "thankful and warm",
                "verbosity_modifier": 1.1,
                "relationship_bonus": 0.15,  # Grateful NPCs build relationships faster
            },
            EmotionalState.PROUD: {
                "tone": "confident and accomplished",
                "verbosity_modifier": 1.3,
                "relationship_bonus": 0.05,
            },
            EmotionalState.CONFUSED: {
                "tone": "uncertain and questioning",
                "verbosity_modifier": 0.9,
                "relationship_bonus": 0.0,
            },
            EmotionalState.WORRIED: {
                "tone": "anxious and concerned",
                "verbosity_modifier": 1.1,  # Worried NPCs might talk more to seek reassurance
                "relationship_bonus": 0.0,
            },
        }

        base_modifiers = emotion_modifiers.get(emotional_state.primary_emotion, {})

        # Scale modifiers by emotion intensity
        for key, value in base_modifiers.items():
            if isinstance(value, (int, float)):
                # Scale numerical modifiers by intensity
                intensity_factor = 0.5 + (emotional_state.emotion_intensity * 0.5)  # 0.5 to 1.0 range
                influence["dialogue_modifiers"][key] = value * intensity_factor
            else:
                influence["dialogue_modifiers"][key] = value

        return influence

    async def trigger_battle_outcome(
        self,
        db: AsyncSession,
        npc_id: UUID,
        player_id: UUID,
        npc_won: bool,
    ):
        """Trigger emotional response to battle outcome."""
        stimulus_type = StimulusType.BATTLE_WON if npc_won else StimulusType.BATTLE_LOST
        stimulus = EmotionalStimulus(
            stimulus_type=stimulus_type,
            intensity=0.8,  # Battles are significant events
            source_player_id=player_id,
            source_description=f"Battle with player {'won' if npc_won else 'lost'}",
            context={"outcome": "victory" if npc_won else "defeat"}
        )

        return await self.apply_stimulus(db, npc_id, stimulus)

    async def trigger_gift_received(
        self,
        db: AsyncSession,
        npc_id: UUID,
        player_id: UUID,
        gift_name: str,
        gift_value: float = 0.5,
    ):
        """Trigger emotional response to receiving a gift."""
        stimulus = EmotionalStimulus(
            stimulus_type=StimulusType.GIFT_RECEIVED,
            intensity=min(1.0, gift_value),  # Intensity based on gift value
            source_player_id=player_id,
            source_description=f"Received gift: {gift_name}",
            context={"gift_name": gift_name, "gift_value": gift_value}
        )

        return await self.apply_stimulus(db, npc_id, stimulus)

    async def trigger_relationship_change(
        self,
        db: AsyncSession,
        npc_id: UUID,
        player_id: UUID,
        old_level: float,
        new_level: float,
    ):
        """Trigger emotional response to relationship level change."""
        if new_level > old_level:
            stimulus_type = StimulusType.FRIENDSHIP_INCREASED
            intensity = min(1.0, (new_level - old_level) * 2.0)  # Scale by relationship change
        else:
            stimulus_type = StimulusType.FRIENDSHIP_DECREASED
            intensity = min(1.0, (old_level - new_level) * 2.0)

        stimulus = EmotionalStimulus(
            stimulus_type=stimulus_type,
            intensity=intensity,
            source_player_id=player_id,
            source_description=f"Relationship changed from {old_level:.2f} to {new_level:.2f}",
            context={"old_level": old_level, "new_level": new_level}
        )

        return await self.apply_stimulus(db, npc_id, stimulus)


# Global emotional state manager instance
emotion_manager = EmotionalStateManager()