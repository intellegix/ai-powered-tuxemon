# Gossip System API Routes for AI-Powered Tuxemon
# Austin Kidwell | Intellegix | Mobile-First Pokemon-Style Game

from typing import Dict, List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from loguru import logger

from app.database import get_db
from app.api.routes.auth import get_current_player
from app.game.models import Player
from app.game.gossip_propagation import gossip_manager, GossipType, GossipItem


router = APIRouter()


# Request/Response models
class CreateGossipRequest(BaseModel):
    """Request to manually create gossip (for testing)."""
    gossip_type: str
    content: str
    target_player_id: UUID
    source_npc_id: UUID
    importance: float = 0.5
    tags: List[str] = []


class GossipItemResponse(BaseModel):
    """Gossip item for API responses."""
    id: str
    gossip_type: str
    content: str
    importance: float
    reliability: float
    timestamp: datetime
    source_npc_id: UUID
    spread_count: int
    tags: List[str]


class PlayerReputationResponse(BaseModel):
    """Player reputation summary."""
    trainer_skill: float
    helpfulness: float
    trustworthiness: float
    popularity: float


class GossipStatsResponse(BaseModel):
    """Gossip system statistics."""
    total_active_gossip: int
    npcs_with_gossip: int
    gossip_networks: int
    average_gossip_per_npc: float
    gossip_by_type: Dict[str, int]


@router.get("/stats", response_model=GossipStatsResponse)
async def get_gossip_statistics(
    current_player: Player = Depends(get_current_player),
):
    """Get gossip system statistics."""
    try:
        stats = await gossip_manager.get_gossip_statistics()
        return GossipStatsResponse(**stats)

    except Exception as e:
        logger.error(f"Failed to get gossip statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve gossip statistics"
        )


@router.get("/player/{player_id}/reputation", response_model=PlayerReputationResponse)
async def get_player_reputation(
    player_id: UUID,
    npc_id: UUID,
    current_player: Player = Depends(get_current_player),
):
    """Get what a specific NPC thinks about a player based on gossip."""
    try:
        reputation = await gossip_manager.generate_player_reputation_summary(player_id, npc_id)
        return PlayerReputationResponse(**reputation)

    except Exception as e:
        logger.error(f"Failed to get player reputation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve player reputation"
        )


@router.get("/player/{player_id}/gossip", response_model=List[GossipItemResponse])
async def get_gossip_about_player(
    player_id: UUID,
    npc_id: UUID,
    gossip_types: Optional[List[str]] = None,
    current_player: Player = Depends(get_current_player),
):
    """Get all gossip a specific NPC knows about a player."""
    try:
        # Convert string gossip types to enum
        filter_types = None
        if gossip_types:
            filter_types = []
            for gossip_type_str in gossip_types:
                try:
                    filter_types.append(GossipType(gossip_type_str))
                except ValueError:
                    pass  # Skip invalid types

        gossip_items = await gossip_manager.get_npc_gossip_about_player(
            npc_id, player_id, filter_types
        )

        # Convert to response format
        response_items = []
        for gossip in gossip_items:
            response_items.append(GossipItemResponse(
                id=gossip.id,
                gossip_type=gossip.gossip_type.value,
                content=gossip.content,
                importance=gossip.importance,
                reliability=gossip.reliability,
                timestamp=gossip.timestamp,
                source_npc_id=gossip.source_npc_id,
                spread_count=gossip.spread_count,
                tags=gossip.tags
            ))

        return response_items

    except Exception as e:
        logger.error(f"Failed to get gossip about player: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve gossip about player"
        )


@router.post("/create", response_model=Dict[str, str])
async def create_gossip(
    request: CreateGossipRequest,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    """Create a new piece of gossip (for testing and admin purposes)."""
    try:
        # Verify the target player exists
        from sqlmodel import select
        player_result = await db.execute(
            select(Player).where(Player.id == request.target_player_id)
        )
        target_player = player_result.scalar_one_or_none()

        if not target_player:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target player not found"
            )

        # Verify the source NPC exists
        from app.game.models import NPC
        npc_result = await db.execute(
            select(NPC).where(NPC.id == request.source_npc_id)
        )
        source_npc = npc_result.scalar_one_or_none()

        if not source_npc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source NPC not found"
            )

        # Convert string gossip type to enum
        try:
            gossip_type = GossipType(request.gossip_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid gossip type: {request.gossip_type}"
            )

        # Create the gossip
        gossip_id = await gossip_manager.create_gossip(
            gossip_type=gossip_type,
            content=request.content,
            player_id=request.target_player_id,
            source_npc_id=request.source_npc_id,
            importance=request.importance,
            tags=request.tags
        )

        logger.info(f"Admin created gossip: {gossip_id} by player {current_player.id}")

        return {
            "message": "Gossip created successfully",
            "gossip_id": gossip_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create gossip: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create gossip"
        )


@router.post("/record/battle", response_model=Dict[str, str])
async def record_battle_gossip(
    player_id: UUID,
    opponent_npc_id: UUID,
    player_won: bool,
    witness_npc_id: Optional[UUID] = None,
    current_player: Player = Depends(get_current_player),
):
    """Record a battle result for gossip propagation."""
    try:
        gossip_id = await gossip_manager.record_battle_result(
            player_id=player_id,
            opponent_npc_id=opponent_npc_id,
            player_won=player_won,
            witness_npc_id=witness_npc_id
        )

        return {
            "message": "Battle gossip recorded successfully",
            "gossip_id": gossip_id
        }

    except Exception as e:
        logger.error(f"Failed to record battle gossip: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record battle gossip"
        )


@router.post("/record/achievement", response_model=Dict[str, str])
async def record_achievement_gossip(
    player_id: UUID,
    achievement: str,
    witness_npc_id: UUID,
    current_player: Player = Depends(get_current_player),
):
    """Record a player achievement for gossip propagation."""
    try:
        gossip_id = await gossip_manager.record_player_achievement(
            player_id=player_id,
            achievement=achievement,
            witness_npc_id=witness_npc_id
        )

        return {
            "message": "Achievement gossip recorded successfully",
            "gossip_id": gossip_id
        }

    except Exception as e:
        logger.error(f"Failed to record achievement gossip: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record achievement gossip"
        )


@router.post("/propagate/{gossip_id}", response_model=Dict[str, int])
async def force_gossip_propagation(
    gossip_id: str,
    current_player: Player = Depends(get_current_player),
):
    """Force propagation of a specific gossip item (for testing)."""
    try:
        spread_count = await gossip_manager.propagate_gossip(gossip_id)

        return {
            "message": f"Gossip propagated to {spread_count} NPCs",
            "spread_count": spread_count
        }

    except Exception as e:
        logger.error(f"Failed to propagate gossip: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to propagate gossip"
        )


@router.delete("/cleanup", response_model=Dict[str, int])
async def cleanup_old_gossip(
    current_player: Player = Depends(get_current_player),
):
    """Clean up expired gossip (admin function)."""
    try:
        removed_count = await gossip_manager.cleanup_old_gossip()

        return {
            "message": f"Cleaned up {removed_count} expired gossip items",
            "removed_count": removed_count
        }

    except Exception as e:
        logger.error(f"Failed to cleanup gossip: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup gossip"
        )