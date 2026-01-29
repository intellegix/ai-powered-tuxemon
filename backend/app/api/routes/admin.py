# Admin API Routes for AI-Powered Tuxemon
# Austin Kidwell | Intellegix | Mobile-First Pokemon-Style Game

from typing import Dict, List, Any, Optional
from uuid import UUID
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from loguru import logger

from app.database import get_db, check_postgres_health, check_redis_health, check_qdrant_health
from app.game.models import Player, NPC, Monster, PersonalityTraits
from app.api.routes.auth import get_current_player
from app.ai.ai_manager import ai_manager
from app.ai.validation import dialogue_validator, CanonFact

router = APIRouter()


# Admin models
class CreateNPCRequest(BaseModel):
    """Request to create a new NPC."""
    slug: str
    name: str
    sprite_name: str
    map_name: str
    position_x: int
    position_y: int
    personality_traits: Optional[PersonalityTraits] = None
    ai_enabled: bool = True
    is_trainer: bool = False
    can_battle: bool = False


class AdminCanonFactRequest(BaseModel):
    """Request to add a custom canon fact."""
    id: str
    category: str
    fact: str
    keywords: List[str]
    importance: float = 1.0


class SystemStats(BaseModel):
    """System statistics for monitoring."""
    total_players: int
    active_players: int
    total_npcs: int
    ai_enabled_npcs: int
    total_monsters: int
    database_health: Dict[str, bool]
    ai_usage_stats: Dict[str, Any]


@router.get("/stats", response_model=SystemStats)
async def get_system_stats(
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    """Get system statistics (admin only)."""
    # TODO: Add proper admin authentication
    from sqlmodel import select, func

    try:
        # Count players
        total_players_result = await db.execute(select(func.count(Player.id)))
        total_players = total_players_result.scalar()

        active_players_result = await db.execute(
            select(func.count(Player.id)).where(Player.is_active == True)
        )
        active_players = active_players_result.scalar()

        # Count NPCs
        total_npcs_result = await db.execute(select(func.count(NPC.id)))
        total_npcs = total_npcs_result.scalar()

        ai_enabled_npcs_result = await db.execute(
            select(func.count(NPC.id)).where(NPC.ai_enabled == True)
        )
        ai_enabled_npcs = ai_enabled_npcs_result.scalar()

        # Count monsters
        total_monsters_result = await db.execute(select(func.count(Monster.id)))
        total_monsters = total_monsters_result.scalar()

        # Check database health
        database_health = {
            "postgres": await check_postgres_health(),
            "redis": await check_redis_health(),
            "qdrant": check_qdrant_health(),
        }

        # AI usage stats from cost tracker
        try:
            daily_stats = await ai_manager.cost_tracker.get_daily_stats()
            cost_projection = await ai_manager.cost_tracker.get_cost_projection()

            ai_usage_stats = {
                "requests_today": daily_stats["total_requests"],
                "cost_today_usd": daily_stats["total_cost"],
                "budget_limit_usd": daily_stats["budget_limit"],
                "budget_utilization_percent": daily_stats["budget_utilization"],
                "average_cost_per_request": daily_stats["avg_cost_per_request"],
                "average_response_time_ms": daily_stats["avg_response_time_ms"],
                "monthly_projection_usd": cost_projection["monthly_projection"],
                "requests_by_model": daily_stats["requests_by_model"],
            }
        except Exception as e:
            logger.warning(f"Could not get AI usage stats: {e}")
            ai_usage_stats = {
                "requests_today": 0,
                "cost_today_usd": 0.0,
                "error": "Cost tracking unavailable",
            }

        return SystemStats(
            total_players=total_players or 0,
            active_players=active_players or 0,
            total_npcs=total_npcs or 0,
            ai_enabled_npcs=ai_enabled_npcs or 0,
            total_monsters=total_monsters or 0,
            database_health=database_health,
            ai_usage_stats=ai_usage_stats,
        )

    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system statistics"
        )


@router.post("/npcs", response_model=Dict[str, str])
async def create_npc(
    npc_request: CreateNPCRequest,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    """Create a new NPC (admin only)."""
    # TODO: Add proper admin authentication
    from sqlmodel import select
    import json

    # Check if slug already exists
    existing_result = await db.execute(select(NPC).where(NPC.slug == npc_request.slug))
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="NPC with this slug already exists"
        )

    try:
        # Create NPC
        personality_data = {}
        if npc_request.personality_traits:
            personality_data = npc_request.personality_traits.dict()

        new_npc = NPC(
            slug=npc_request.slug,
            name=npc_request.name,
            sprite_name=npc_request.sprite_name,
            map_name=npc_request.map_name,
            position_x=npc_request.position_x,
            position_y=npc_request.position_y,
            ai_enabled=npc_request.ai_enabled,
            personality_traits=json.dumps(personality_data),
            is_trainer=npc_request.is_trainer,
            can_battle=npc_request.can_battle,
        )

        db.add(new_npc)
        await db.commit()
        await db.refresh(new_npc)

        logger.info(f"Created new NPC: {npc_request.name} ({npc_request.slug})")

        return {
            "message": f"NPC '{npc_request.name}' created successfully",
            "npc_id": str(new_npc.id),
            "slug": new_npc.slug,
        }

    except Exception as e:
        logger.error(f"Error creating NPC: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create NPC"
        )


@router.get("/npcs/{npc_id}/memories")
async def get_npc_all_memories(
    npc_id: UUID,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    """Get all memories for an NPC (admin only)."""
    # TODO: Add proper admin authentication
    from sqlmodel import select

    # Verify NPC exists
    npc_result = await db.execute(select(NPC).where(NPC.id == npc_id))
    npc = npc_result.scalar_one_or_none()

    if not npc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="NPC not found"
        )

    try:
        # Get all memories for this NPC from Qdrant
        from qdrant_client.http import models

        search_result = qdrant_client.scroll(
            collection_name="npc_memories",
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="npc_id",
                        match=models.MatchValue(value=str(npc_id))
                    )
                ]
            ),
            limit=100,
        )

        memories = []
        points = search_result[0] if isinstance(search_result, tuple) else search_result.points

        for point in points:
            payload = point.payload
            memory_data = {
                "id": point.id,
                "player_id": payload.get("player_id"),
                "content": payload.get("content"),
                "timestamp": payload.get("timestamp"),
                "importance": payload.get("importance", 0.5),
                "interaction_type": payload.get("interaction_type"),
            }
            memories.append(memory_data)

        return {
            "npc_id": str(npc_id),
            "npc_name": npc.name,
            "total_memories": len(memories),
            "memories": memories,
        }

    except Exception as e:
        logger.error(f"Error getting NPC memories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve NPC memories"
        )


@router.delete("/npcs/{npc_id}/memories")
async def clear_npc_memories(
    npc_id: UUID,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    """Clear all memories for an NPC (admin only)."""
    # TODO: Add proper admin authentication
    from sqlmodel import select

    # Verify NPC exists
    npc_result = await db.execute(select(NPC).where(NPC.id == npc_id))
    npc = npc_result.scalar_one_or_none()

    if not npc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="NPC not found"
        )

    try:
        # Delete memories from Qdrant
        from qdrant_client.http import models

        # Get all memory point IDs for this NPC
        search_result = qdrant_client.scroll(
            collection_name="npc_memories",
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="npc_id",
                        match=models.MatchValue(value=str(npc_id))
                    )
                ]
            ),
            limit=1000,
        )

        points = search_result[0] if isinstance(search_result, tuple) else search_result.points
        point_ids = [point.id for point in points]

        if point_ids:
            qdrant_client.delete(
                collection_name="npc_memories",
                points_selector=models.PointIdsList(points=point_ids)
            )

        logger.info(f"Cleared {len(point_ids)} memories for NPC {npc.name}")

        return {
            "message": f"Cleared {len(point_ids)} memories for NPC '{npc.name}'",
            "memories_deleted": len(point_ids),
        }

    except Exception as e:
        logger.error(f"Error clearing NPC memories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear NPC memories"
        )


@router.post("/ai/test-dialogue")
async def test_ai_dialogue(
    npc_slug: str,
    test_message: str,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    """Test AI dialogue generation (admin only)."""
    # TODO: Add proper admin authentication
    from sqlmodel import select
    import json

    # Get NPC
    npc_result = await db.execute(select(NPC).where(NPC.slug == npc_slug))
    npc = npc_result.scalar_one_or_none()

    if not npc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="NPC not found"
        )

    try:
        # Create test context
        from app.game.models import NPCInteractionContext

        context = NPCInteractionContext(
            player_id=current_player.id,
            npc_id=npc.id,
            interaction_type="dialogue",
            player_position=(current_player.position_x, current_player.position_y),
            player_party_summary="Test party with starter monster",
            recent_achievements=["Started the game"],
            relationship_level=0.5,
            time_of_day="afternoon",
        )

        # Get personality
        personality_data = json.loads(npc.personality_traits or "{}")
        personality = PersonalityTraits(**personality_data) if personality_data else PersonalityTraits()

        # Get test memories (empty for test)
        memories = []

        # Generate dialogue
        response = await ai_manager.generate_dialogue(
            npc_id=npc.id,
            context=context,
            personality=personality,
            memories=memories,
        )

        return {
            "npc_name": npc.name,
            "test_message": test_message,
            "ai_response": response.dict(),
            "personality_traits": personality.dict(),
        }

    except Exception as e:
        logger.error(f"Error testing AI dialogue: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate test dialogue"
        )


from app.database import qdrant_client


@router.get("/health-detailed")
async def detailed_health_check():
    """Comprehensive health check for production monitoring."""
    from datetime import datetime

    try:
        # Check all database services
        postgres_healthy = await check_postgres_health()
        redis_healthy = await check_redis_health()
        qdrant_healthy = check_qdrant_health()

        # Get AI system status
        ai_system_status = {
            "cost_tracker_active": True,
            "local_llm_available": True,
        }

        # Try to get AI cost stats for additional health info
        try:
            daily_stats = await ai_manager.cost_tracker.get_daily_stats()
            ai_system_status.update({
                "daily_budget_utilization": daily_stats.get("budget_utilization", 0),
                "requests_today": daily_stats.get("total_requests", 0),
                "avg_response_time_ms": daily_stats.get("avg_response_time_ms", 0),
            })
        except Exception as e:
            logger.warning(f"Could not get AI stats in health check: {e}")
            ai_system_status["cost_tracker_active"] = False

        # Calculate overall health status
        all_services_healthy = postgres_healthy and redis_healthy and qdrant_healthy

        # Production readiness calculation
        readiness_factors = {
            "database_connectivity": 1.0 if postgres_healthy else 0.0,
            "cache_connectivity": 1.0 if redis_healthy else 0.0,
            "vector_db_connectivity": 1.0 if qdrant_healthy else 0.0,
            "ai_system": 1.0 if ai_system_status["cost_tracker_active"] else 0.8,
        }

        # Calculate weighted readiness score
        readiness_score = (
            readiness_factors["database_connectivity"] * 0.4 +
            readiness_factors["cache_connectivity"] * 0.2 +
            readiness_factors["vector_db_connectivity"] * 0.2 +
            readiness_factors["ai_system"] * 0.2
        )

        return {
            "status": "healthy" if all_services_healthy else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "database": "healthy" if postgres_healthy else "unhealthy",
                "redis": "healthy" if redis_healthy else "unhealthy",
                "qdrant": "healthy" if qdrant_healthy else "unhealthy",
            },
            "ai_system": ai_system_status,
            "production_readiness": {
                "score_percent": round(readiness_score * 100, 1),
                "factors": readiness_factors,
                "deployment_ready": readiness_score >= 0.9,
            },
            "version": "1.0.0",
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "production_readiness": {
                "score_percent": 0,
                "deployment_ready": False,
            },
        }


@router.get("/validation/stats")
async def get_validation_stats(
    current_player: Player = Depends(get_current_player),
):
    """Get dialogue validation system statistics (admin only)."""
    # TODO: Add proper admin authentication
    try:
        stats = dialogue_validator.get_validation_stats()
        canon_summary = dialogue_validator.get_canon_summary()

        return {
            "validation_stats": stats,
            "canon_categories": canon_summary,
            "system_status": "active",
        }

    except Exception as e:
        logger.error(f"Error getting validation stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve validation statistics"
        )


@router.post("/validation/canon-facts")
async def add_canon_fact(
    fact_request: AdminCanonFactRequest,
    current_player: Player = Depends(get_current_player),
):
    """Add a custom canon fact to the validation system (admin only)."""
    # TODO: Add proper admin authentication
    try:
        canon_fact = CanonFact(
            id=fact_request.id,
            category=fact_request.category,
            fact=fact_request.fact,
            keywords=fact_request.keywords,
            importance=fact_request.importance,
        )

        dialogue_validator.add_custom_fact(canon_fact)

        return {
            "message": f"Canon fact '{fact_request.id}' added successfully",
            "fact_id": fact_request.id,
            "category": fact_request.category,
        }

    except Exception as e:
        logger.error(f"Error adding canon fact: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add canon fact"
        )


@router.post("/validation/test")
async def test_dialogue_validation(
    test_text: str,
    current_player: Player = Depends(get_current_player),
):
    """Test dialogue validation on arbitrary text (admin only)."""
    # TODO: Add proper admin authentication
    from app.game.models import DialogueResponse, NPCInteractionContext

    try:
        # Create test dialogue response
        test_dialogue = DialogueResponse(
            text=test_text,
            emotion="neutral",
        )

        # Create test context
        test_context = NPCInteractionContext(
            player_id=current_player.id,
            npc_id=UUID("00000000-0000-0000-0000-000000000000"),
            interaction_type="dialogue",
            player_position=(0, 0),
            player_party_summary="test party",
            recent_achievements=[],
            relationship_level=0.5,
            time_of_day="afternoon",
        )

        # Validate
        validation_result = dialogue_validator.validate_dialogue(
            dialogue=test_dialogue,
            context=test_context,
        )

        return {
            "test_text": test_text,
            "validation_result": {
                "is_valid": validation_result.is_valid,
                "score": validation_result.score,
                "severity": validation_result.severity,
                "issues": validation_result.issues,
                "suggested_fixes": validation_result.suggested_fixes,
            },
        }

    except Exception as e:
        logger.error(f"Error testing validation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test dialogue validation"
        )


@router.get("/ai/cost-stats")
async def get_ai_cost_stats(
    date: Optional[str] = None,
    current_player: Player = Depends(get_current_player),
):
    """Get detailed AI cost statistics (admin only)."""
    # TODO: Add proper admin authentication
    try:
        daily_stats = await ai_manager.cost_tracker.get_daily_stats(date)
        hourly_breakdown = await ai_manager.cost_tracker.get_hourly_breakdown(date)
        cost_projection = await ai_manager.cost_tracker.get_cost_projection()
        budget_alerts = await ai_manager.cost_tracker.check_budget_alerts()

        return {
            "daily_stats": daily_stats,
            "hourly_breakdown": hourly_breakdown,
            "cost_projection": cost_projection,
            "budget_alerts": budget_alerts,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting cost stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cost statistics"
        )


@router.post("/ai/budget-alert")
async def set_budget_alert(
    threshold_percent: float,
    current_player: Player = Depends(get_current_player),
):
    """Set budget alert threshold (admin only)."""
    # TODO: Add proper admin authentication
    if not 0 <= threshold_percent <= 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Threshold must be between 0 and 100 percent"
        )

    try:
        await ai_manager.cost_tracker.set_budget_alert(threshold_percent)

        return {
            "message": f"Budget alert threshold set to {threshold_percent}%",
            "threshold_percent": threshold_percent,
        }

    except Exception as e:
        logger.error(f"Error setting budget alert: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set budget alert"
        )


@router.get("/ai/cost-history")
async def get_cost_history(
    days: int = 7,
    current_player: Player = Depends(get_current_player),
):
    """Get cost history for the last N days (admin only)."""
    # TODO: Add proper admin authentication
    if days < 1 or days > 30:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Days must be between 1 and 30"
        )

    try:
        history = []
        for i in range(days):
            date = (datetime.utcnow() - timedelta(days=i)).date().isoformat()
            stats = await ai_manager.cost_tracker.get_daily_stats(date)
            history.append(stats)

        # Calculate totals
        total_cost = sum(day["total_cost"] for day in history)
        total_requests = sum(day["total_requests"] for day in history)

        return {
            "history": history,
            "period_summary": {
                "total_cost": total_cost,
                "total_requests": total_requests,
                "average_daily_cost": total_cost / days,
                "average_daily_requests": total_requests / days,
                "period_days": days,
            }
        }

    except Exception as e:
        logger.error(f"Error getting cost history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cost history"
        )


@router.get("/ai/cost-dashboard")
async def get_cost_dashboard(
    current_player: Player = Depends(get_current_player),
):
    """Get comprehensive cost monitoring dashboard (admin only)."""
    # TODO: Add proper admin authentication
    try:
        # Get current stats
        today_stats = await ai_manager.cost_tracker.get_daily_stats()
        cost_projection = await ai_manager.cost_tracker.get_cost_projection()
        budget_alerts = await ai_manager.cost_tracker.check_budget_alerts()

        # Get recent history (last 7 days)
        recent_history = []
        for i in range(7):
            date = (datetime.utcnow() - timedelta(days=i)).date().isoformat()
            day_stats = await ai_manager.cost_tracker.get_daily_stats(date)
            recent_history.append(day_stats)

        # Calculate efficiency metrics
        total_recent_cost = sum(day["total_cost"] for day in recent_history)
        total_recent_requests = sum(day["total_requests"] for day in recent_history)
        avg_cost_per_request = total_recent_cost / total_recent_requests if total_recent_requests > 0 else 0

        # Model usage distribution
        claude_requests = sum(day["requests_by_model"].get("claude", 0) for day in recent_history)
        local_requests = sum(day["requests_by_model"].get("local", 0) for day in recent_history)
        total_requests = claude_requests + local_requests

        model_distribution = {
            "claude_percentage": (claude_requests / total_requests * 100) if total_requests > 0 else 0,
            "local_percentage": (local_requests / total_requests * 100) if total_requests > 0 else 0,
            "total_requests": total_requests,
        }

        # Performance metrics
        recent_response_times = [day["avg_response_time_ms"] for day in recent_history if day["avg_response_time_ms"] > 0]
        avg_response_time = sum(recent_response_times) / len(recent_response_times) if recent_response_times else 0

        return {
            "dashboard_generated_at": datetime.utcnow().isoformat(),
            "today_stats": today_stats,
            "cost_projection": cost_projection,
            "budget_alerts": budget_alerts,
            "recent_history": recent_history,
            "efficiency_metrics": {
                "avg_cost_per_request_7d": avg_cost_per_request,
                "avg_response_time_ms_7d": avg_response_time,
                "cost_savings_estimate": total_recent_cost * 0.8,  # Estimated savings vs 100% Claude
            },
            "model_distribution": model_distribution,
            "recommendations": _generate_cost_recommendations(today_stats, cost_projection, model_distribution),
        }

    except Exception as e:
        logger.error(f"Error generating cost dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate cost dashboard"
        )


def _generate_cost_recommendations(
    today_stats: dict,
    cost_projection: dict,
    model_distribution: dict,
) -> List[str]:
    """Generate cost optimization recommendations based on current metrics."""
    recommendations = []

    # Budget utilization recommendations
    if today_stats["budget_utilization"] > 80:
        recommendations.append("⚠️ Daily budget at 80%+ utilization - consider increasing local LLM usage")

    if cost_projection["monthly_projection"] > 1000:
        recommendations.append("💰 Monthly projection exceeds $1000 - review high-cost interactions")

    # Model usage recommendations
    if model_distribution["claude_percentage"] > 30:
        recommendations.append("🔄 Claude usage above 30% - consider tuning hybrid selection logic")

    if model_distribution["local_percentage"] < 70:
        recommendations.append("🏠 Local LLM usage below 70% - opportunity to reduce costs further")

    # Performance recommendations
    if today_stats.get("avg_response_time_ms", 0) > 2000:
        recommendations.append("⚡ Average response time above 2s - investigate performance bottlenecks")

    # Default positive message
    if not recommendations:
        recommendations.append("✅ Cost and performance metrics look healthy!")

    return recommendations


@router.post("/ai/cost-webhook")
async def cost_webhook_test(
    current_player: Player = Depends(get_current_player),
):
    """Test cost monitoring webhook system (admin only)."""
    # TODO: Add proper admin authentication
    try:
        # Check for budget alerts
        budget_alerts = await ai_manager.cost_tracker.check_budget_alerts()
        today_stats = await ai_manager.cost_tracker.get_daily_stats()

        webhook_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "alert_triggered": budget_alerts is not None,
            "current_stats": today_stats,
            "budget_alert": budget_alerts,
        }

        # In production, this would send to Slack, Discord, email, etc.
        logger.info(f"Cost monitoring webhook: {webhook_data}")

        return {
            "message": "Cost monitoring webhook test completed",
            "webhook_data": webhook_data,
            "production_note": "In production, this would trigger external notifications",
        }

    except Exception as e:
        logger.error(f"Error testing cost webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test cost monitoring webhook"
        )