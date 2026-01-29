# Combat API Routes for AI-Powered Tuxemon
# Austin Kidwell | Intellegix | Mobile-First Pokemon-Style Game

from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from loguru import logger

from app.database import get_db
from app.game.models import Player, NPC, Monster, CombatSession, CombatPhase, CombatAction
from app.api.routes.auth import get_current_player

router = APIRouter()


# Request/Response models
class StartBattleRequest(BaseModel):
    """Request to start a battle."""
    opponent_npc_id: UUID
    player_monster_ids: List[UUID]


class CombatActionRequest(BaseModel):
    """Request to submit a combat action."""
    battle_id: UUID
    action_type: str  # "attack", "switch", "item", "flee"
    target_id: Optional[UUID] = None
    technique_slug: Optional[str] = None
    item_slug: Optional[str] = None
    monster_switch_to: Optional[UUID] = None


class CombatMonster(BaseModel):
    """Monster state during combat."""
    id: UUID
    name: str
    species_slug: str
    level: int
    current_hp: int
    max_hp: int
    element_types: List[str]
    status_effects: List[str]
    stats: Dict[str, int]


class CombatParticipant(BaseModel):
    """Combat participant (player or NPC)."""
    id: UUID
    name: str
    is_player: bool
    active_monster: Optional[CombatMonster]
    party: List[CombatMonster]
    defeated: bool


class CombatStateResponse(BaseModel):
    """Current combat state."""
    battle_id: UUID
    phase: CombatPhase
    participants: List[CombatParticipant]
    current_turn: int
    turn_queue: List[Dict[str, Any]]
    weather: Optional[str]
    field_effects: List[str]
    battle_log: List[str]
    can_act: bool
    valid_actions: List[str]


class BattleResult(BaseModel):
    """Battle completion result."""
    battle_id: UUID
    winner: str  # "player" or "npc"
    experience_gained: Dict[UUID, int]
    money_gained: int
    items_found: List[str]
    battle_duration_seconds: int


@router.post("/start", response_model=CombatStateResponse)
async def start_battle(
    battle_request: StartBattleRequest,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    """Start a battle with an NPC."""
    from sqlmodel import select
    import json

    # Verify NPC exists and can battle
    npc_result = await db.execute(select(NPC).where(NPC.id == battle_request.opponent_npc_id))
    opponent_npc = npc_result.scalar_one_or_none()

    if not opponent_npc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="NPC not found"
        )

    if not opponent_npc.can_battle:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This NPC cannot battle"
        )

    # Verify player has monsters
    if not battle_request.player_monster_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No monsters selected for battle"
        )

    try:
        # Get player's monsters
        player_monsters_result = await db.execute(
            select(Monster).where(
                Monster.player_id == current_player.id,
                Monster.id.in_(battle_request.player_monster_ids)
            )
        )
        player_monsters = player_monsters_result.scalars().all()

        # Get NPC's monsters
        npc_monsters_result = await db.execute(
            select(Monster).where(Monster.npc_id == opponent_npc.id)
        )
        npc_monsters = npc_monsters_result.scalars().all()

        if not npc_monsters:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="NPC has no monsters to battle with"
            )

        # Create combat session
        battle_id = uuid4()
        combat_session = CombatSession(
            id=battle_id,
            player_id=current_player.id,
            opponent_npc_id=opponent_npc.id,
            phase=CombatPhase.ACTION_SELECTION,
            current_turn=0,
            turn_queue="[]",
            weather=None,
            field_effects="[]",
        )

        db.add(combat_session)
        await db.commit()

        # Format combat state
        player_combat_monsters = [_format_combat_monster(m) for m in player_monsters]
        npc_combat_monsters = [_format_combat_monster(m) for m in npc_monsters]

        player_participant = CombatParticipant(
            id=current_player.id,
            name=current_player.username,
            is_player=True,
            active_monster=player_combat_monsters[0] if player_combat_monsters else None,
            party=player_combat_monsters,
            defeated=False,
        )

        npc_participant = CombatParticipant(
            id=opponent_npc.id,
            name=opponent_npc.name,
            is_player=False,
            active_monster=npc_combat_monsters[0] if npc_combat_monsters else None,
            party=npc_combat_monsters,
            defeated=False,
        )

        logger.info(f"Battle started between {current_player.username} and {opponent_npc.name}")

        return CombatStateResponse(
            battle_id=battle_id,
            phase=CombatPhase.ACTION_SELECTION,
            participants=[player_participant, npc_participant],
            current_turn=1,
            turn_queue=[],
            weather=None,
            field_effects=[],
            battle_log=[f"Battle started between {current_player.username} and {opponent_npc.name}!"],
            can_act=True,
            valid_actions=["attack", "switch", "item", "flee"],
        )

    except Exception as e:
        logger.error(f"Start battle error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start battle"
        )


@router.post("/action", response_model=CombatStateResponse)
async def submit_combat_action(
    action_request: CombatActionRequest,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    """Submit a combat action."""
    from sqlmodel import select
    import json

    # Get combat session
    combat_result = await db.execute(
        select(CombatSession).where(CombatSession.id == action_request.battle_id)
    )
    combat_session = combat_result.scalar_one_or_none()

    if not combat_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Battle not found"
        )

    if combat_session.player_id != current_player.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not your battle"
        )

    if combat_session.phase != CombatPhase.ACTION_SELECTION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot submit action at this time"
        )

    try:
        # Process the combat action
        battle_log = []

        # Simulate combat action processing
        if action_request.action_type == "attack":
            battle_log.append(f"{current_player.username} used {action_request.technique_slug or 'Tackle'}!")
            # TODO: Implement damage calculation
            battle_log.append("It was effective!")

        elif action_request.action_type == "flee":
            # End battle with flee
            combat_session.phase = CombatPhase.DEFEAT
            combat_session.ended_at = datetime.utcnow()
            combat_session.winner = "npc"
            battle_log.append(f"{current_player.username} fled from battle!")

        # Update turn
        combat_session.current_turn += 1

        # Save changes
        db.add(combat_session)
        await db.commit()

        # Return updated combat state
        # TODO: Implement full combat state management
        return CombatStateResponse(
            battle_id=action_request.battle_id,
            phase=combat_session.phase,
            participants=[],  # TODO: Update with actual participants
            current_turn=combat_session.current_turn,
            turn_queue=[],
            weather=combat_session.weather,
            field_effects=json.loads(combat_session.field_effects),
            battle_log=battle_log,
            can_act=combat_session.phase == CombatPhase.ACTION_SELECTION,
            valid_actions=["attack", "switch", "item", "flee"] if combat_session.phase == CombatPhase.ACTION_SELECTION else [],
        )

    except Exception as e:
        logger.error(f"Combat action error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process combat action"
        )


@router.get("/{battle_id}/state", response_model=CombatStateResponse)
async def get_combat_state(
    battle_id: UUID,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    """Get current combat state."""
    from sqlmodel import select
    import json

    # Get combat session
    combat_result = await db.execute(
        select(CombatSession).where(CombatSession.id == battle_id)
    )
    combat_session = combat_result.scalar_one_or_none()

    if not combat_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Battle not found"
        )

    if combat_session.player_id != current_player.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not your battle"
        )

    # TODO: Implement full combat state retrieval
    return CombatStateResponse(
        battle_id=battle_id,
        phase=combat_session.phase,
        participants=[],  # TODO: Load actual participants
        current_turn=combat_session.current_turn,
        turn_queue=json.loads(combat_session.turn_queue),
        weather=combat_session.weather,
        field_effects=json.loads(combat_session.field_effects),
        battle_log=["Battle in progress..."],
        can_act=combat_session.phase == CombatPhase.ACTION_SELECTION,
        valid_actions=["attack", "switch", "item", "flee"] if combat_session.phase == CombatPhase.ACTION_SELECTION else [],
    )


@router.post("/{battle_id}/forfeit")
async def forfeit_battle(
    battle_id: UUID,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    """Forfeit the current battle."""
    from sqlmodel import select

    # Get combat session
    combat_result = await db.execute(
        select(CombatSession).where(CombatSession.id == battle_id)
    )
    combat_session = combat_result.scalar_one_or_none()

    if not combat_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Battle not found"
        )

    if combat_session.player_id != current_player.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not your battle"
        )

    if combat_session.ended_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Battle already ended"
        )

    # End battle
    combat_session.phase = CombatPhase.DEFEAT
    combat_session.ended_at = datetime.utcnow()
    combat_session.winner = "npc"

    db.add(combat_session)
    await db.commit()

    logger.info(f"Player {current_player.username} forfeited battle {battle_id}")

    return {"message": "Battle forfeited"}


def _format_combat_monster(monster: Monster) -> CombatMonster:
    """Convert Monster to CombatMonster for battle state."""
    import json

    # TODO: Get actual species data for element types and max HP
    return CombatMonster(
        id=monster.id,
        name=monster.name,
        species_slug=monster.species_slug,
        level=monster.level,
        current_hp=monster.current_hp,
        max_hp=monster.current_hp + 10,  # Placeholder
        element_types=["normal"],  # Placeholder
        status_effects=json.loads(monster.status_effects or "[]"),
        stats={
            "hp": 50,
            "attack": 50,
            "defense": 50,
            "speed": 50,
        },  # Placeholder
    )