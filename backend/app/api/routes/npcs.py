# NPC API Routes for AI-Powered Tuxemon
# Austin Kidwell | Intellegix | Mobile-First Pokemon-Style Game

from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.database import get_db
from app.game.models import (
    NPC,
    Player,
    NPCInteractionContext,
    DialogueResponse,
    PersonalityTraits,
    MemoryItem,
)
from app.api.routes.auth import get_current_player
from app.ai.ai_manager import ai_manager
from app.game.npc_schedule import npc_schedule_manager

router = APIRouter()


# Response models
class NPCInfo(BaseModel):
    """NPC information for mobile client."""
    id: UUID
    slug: str
    name: str
    sprite_name: str
    position: tuple[int, int]
    facing_direction: str
    is_trainer: bool
    can_battle: bool
    approachable: bool
    relationship_level: float


class NPCInteractionRequest(BaseModel):
    """Request for NPC interaction."""
    interaction_type: str  # "dialogue", "battle", "shop"
    player_party_summary: str
    recent_achievements: List[str] = []


class NPCMemoryResponse(BaseModel):
    """NPC memory information."""
    memories: List[Dict[str, Any]]
    total_interactions: int
    relationship_level: float
    favorite_topics: List[str]


@router.get("/nearby", response_model=List[NPCInfo])
async def get_nearby_npcs(
    map_name: str,
    player_x: int,
    player_y: int,
    radius: int = 10,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    """Get NPCs near the player's current position with schedule-based positioning."""
    import json

    # First, update NPC positions based on current time
    await npc_schedule_manager.update_npc_positions(db)

    # Get NPCs using the schedule manager (more accurate with current schedules)
    npcs_data = await npc_schedule_manager.get_npcs_in_area(
        db=db,
        map_name=map_name,
        center_x=player_x,
        center_y=player_y,
        radius=radius
    )

    # Get relationship levels
    relationships = json.loads(current_player.npc_relationships or "{}")

    npc_infos = []
    for npc_data in npcs_data:
        relationship_level = relationships.get(npc_data["slug"], 0.0)

        npc_info = NPCInfo(
            id=UUID(npc_data["id"]),
            slug=npc_data["slug"],
            name=npc_data["name"],
            sprite_name=npc_data["spriteName"],
            position=tuple(npc_data["position"]),
            facing_direction=npc_data["facingDirection"],
            is_trainer=npc_data["isTrainer"],
            can_battle=npc_data["canBattle"],
            approachable=npc_data["approachable"],
            relationship_level=relationship_level,
        )
        npc_infos.append(npc_info)

    logger.info(f"Found {len(npc_infos)} NPCs near player at ({player_x}, {player_y}) on {map_name}")
    return npc_infos


@router.get("/{npc_id}", response_model=NPCInfo)
async def get_npc_info(
    npc_id: UUID,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed information about a specific NPC."""
    from sqlmodel import select
    import json

    # Get NPC
    result = await db.execute(select(NPC).where(NPC.id == npc_id))
    npc = result.scalar_one_or_none()

    if not npc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="NPC not found"
        )

    # Get relationship level
    relationships = json.loads(current_player.npc_relationships or "{}")
    relationship_level = relationships.get(npc.slug, 0.0)

    return NPCInfo(
        id=npc.id,
        slug=npc.slug,
        name=npc.name,
        sprite_name=npc.sprite_name,
        position=(npc.position_x, npc.position_y),
        facing_direction=npc.facing_direction,
        is_trainer=npc.is_trainer,
        can_battle=npc.can_battle,
        approachable=npc.approachable,
        relationship_level=relationship_level,
    )


@router.post("/{npc_id}/interact", response_model=DialogueResponse)
async def interact_with_npc(
    npc_id: UUID,
    interaction_request: NPCInteractionRequest,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    """Interact with an NPC and get AI-generated dialogue."""
    from sqlmodel import select
    import json

    # Get NPC
    result = await db.execute(select(NPC).where(NPC.id == npc_id))
    npc = result.scalar_one_or_none()

    if not npc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="NPC not found"
        )

    if not npc.approachable:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="NPC is not approachable right now"
        )

    try:
        # Get current relationship level
        relationships = json.loads(current_player.npc_relationships or "{}")
        relationship_level = relationships.get(npc.slug, 0.0)

        # Build interaction context
        context = NPCInteractionContext(
            player_id=current_player.id,
            npc_id=npc.id,
            interaction_type=interaction_request.interaction_type,
            player_position=(current_player.position_x, current_player.position_y),
            player_party_summary=interaction_request.player_party_summary,
            recent_achievements=interaction_request.recent_achievements,
            relationship_level=relationship_level,
            time_of_day=_get_time_of_day(),
        )

        # Parse NPC personality
        personality_data = json.loads(npc.personality_traits or "{}")
        personality = PersonalityTraits(**personality_data) if personality_data else PersonalityTraits()

        # Get NPC memories about this player with context
        query_context = f"{interaction_request.interaction_type} conversation"
        if interaction_request.recent_achievements:
            query_context += f" {' '.join(interaction_request.recent_achievements)}"

        memories = await ai_manager.get_npc_memories(
            npc_id=npc.id,
            player_id=current_player.id,
            query=query_context,
            limit=5,
            context_type=interaction_request.interaction_type
        )

        # Generate AI dialogue
        dialogue_response = await ai_manager.generate_dialogue(
            npc_id=npc.id,
            context=context,
            personality=personality,
            memories=memories,
            db_session=db,
        )

        # Update relationship and trigger emotional response if significant change
        old_relationship = relationship_level
        new_relationship = min(1.0, relationship_level + dialogue_response.relationship_change)
        relationships[npc.slug] = new_relationship
        current_player.npc_relationships = json.dumps(relationships)

        # Trigger emotional response to relationship change if significant
        if abs(new_relationship - old_relationship) > 0.1:
            from app.game.emotion_system import emotion_manager
            try:
                await emotion_manager.trigger_relationship_change(
                    db=db,
                    npc_id=npc.id,
                    player_id=current_player.id,
                    old_level=old_relationship,
                    new_level=new_relationship,
                )
            except Exception as e:
                logger.warning(f"Failed to trigger emotional response: {e}")

        # Update NPC interaction stats
        npc.last_interaction = datetime.utcnow()
        npc.total_interactions += 1

        # Commit changes
        db.add(current_player)
        db.add(npc)
        await db.commit()

        logger.info(f"Player {current_player.username} interacted with NPC {npc.name}")

        return dialogue_response

    except Exception as e:
        logger.error(f"NPC interaction error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process NPC interaction"
        )


@router.get("/{npc_id}/memories", response_model=NPCMemoryResponse)
async def get_npc_memories(
    npc_id: UUID,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    """Get NPC's memories about the current player."""
    from sqlmodel import select
    import json

    # Verify NPC exists
    result = await db.execute(select(NPC).where(NPC.id == npc_id))
    npc = result.scalar_one_or_none()

    if not npc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="NPC not found"
        )

    # Get memories
    memories = await ai_manager.get_npc_memories(
        npc_id=npc.id,
        player_id=current_player.id,
        limit=20
    )

    # Get relationship level
    relationships = json.loads(current_player.npc_relationships or "{}")
    relationship_level = relationships.get(npc.slug, 0.0)

    # Analyze favorite topics
    topics = {}
    for memory in memories:
        for tag in memory.tags:
            topics[tag] = topics.get(tag, 0) + 1

    favorite_topics = sorted(topics.keys(), key=lambda x: topics[x], reverse=True)[:5]

    # Format memories for response
    memory_dicts = [
        {
            "id": str(memory.id),
            "content": memory.content,
            "importance": memory.importance,
            "timestamp": memory.timestamp.isoformat(),
            "tags": memory.tags,
            "emotional_context": memory.emotional_context,
        }
        for memory in memories
    ]

    return NPCMemoryResponse(
        memories=memory_dicts,
        total_interactions=npc.total_interactions,
        relationship_level=relationship_level,
        favorite_topics=favorite_topics,
    )


@router.get("/{npc_id}/schedule")
async def get_npc_schedule(
    npc_id: UUID,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    """Get NPC's current schedule state."""
    from sqlmodel import select

    # Get NPC by ID first
    result = await db.execute(select(NPC).where(NPC.id == npc_id))
    npc = result.scalar_one_or_none()

    if not npc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="NPC not found"
        )

    # Get current schedule state using the schedule manager
    schedule_state = await npc_schedule_manager.get_npc_current_state(db, npc.slug)

    if not schedule_state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="NPC schedule not found"
        )

    return {
        "current_period": schedule_state["current_period"],
        "activity": schedule_state["activity"],
        "position": schedule_state["position"],
        "map_name": schedule_state["map_name"],
        "approachable": schedule_state["approachable"],
        "dialogue_context": schedule_state["dialogue_context"],
        "can_patrol": schedule_state["can_patrol"],
        "patrol_radius": schedule_state["patrol_radius"],
    }


@router.post("/{npc_id}/schedule")
async def update_npc_schedule(
    npc_id: UUID,
    schedule_data: Dict[str, Any],
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    """Update NPC's daily schedule (admin only for now)."""
    # TODO: Add admin check
    from sqlmodel import select
    import json

    result = await db.execute(select(NPC).where(NPC.id == npc_id))
    npc = result.scalar_one_or_none()

    if not npc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="NPC not found"
        )

    npc.schedule = json.dumps(schedule_data)
    db.add(npc)
    await db.commit()

    # Immediately update position based on new schedule
    await npc_schedule_manager.update_npc_positions(db)

    return {"message": "NPC schedule updated successfully"}


@router.post("/update-all-positions")
async def force_update_all_positions(
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    """Force update all NPC positions based on current time (admin/debug endpoint)."""
    try:
        updated_count = await npc_schedule_manager.update_npc_positions(db)
        current_period = npc_schedule_manager.get_current_day_period()

        return {
            "message": f"Updated {updated_count} NPCs",
            "current_period": current_period,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to update NPC positions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update NPC positions"
        )


def _get_time_of_day() -> str:
    """Get current time of day for context."""
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 21:
        return "evening"
    else:
        return "night"


from pydantic import BaseModel