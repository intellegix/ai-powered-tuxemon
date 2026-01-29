# Gossip Propagation System for AI-Powered Tuxemon
# Austin Kidwell | Intellegix | Mobile-First Pokemon-Style Game

from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from uuid import UUID
import asyncio
import random
import json
from loguru import logger
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db


class GossipType(Enum):
    """Types of information that can spread between NPCs."""
    PLAYER_ACHIEVEMENT = "player_achievement"
    PLAYER_BEHAVIOR = "player_behavior"
    BATTLE_RESULT = "battle_result"
    RELATIONSHIP_CHANGE = "relationship_change"
    STORY_PROGRESS = "story_progress"
    PLAYER_REPUTATION = "player_reputation"
    NPC_INTERACTION = "npc_interaction"


@dataclass
class GossipItem:
    """Individual piece of gossip that can spread between NPCs."""
    id: str
    gossip_type: GossipType
    content: str
    player_id: UUID
    source_npc_id: UUID
    importance: float  # 0.0-1.0, affects spread probability
    timestamp: datetime
    reliability: float  # 0.0-1.0, decreases as it spreads
    spread_count: int = 0
    max_spread: int = 5
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class NPCGossipKnowledge:
    """What an NPC knows about the player through gossip."""
    npc_id: UUID
    known_gossip: List[GossipItem]
    last_updated: datetime
    gossip_receptiveness: float  # How likely to believe gossip (personality trait)
    gossip_spreading: float  # How likely to share gossip (personality trait)


class GossipPropagationManager:
    """Manages the spread of information between NPCs in the game world."""

    def __init__(self):
        # Gossip storage - in production, this would be in Redis or database
        self.active_gossip: Dict[str, GossipItem] = {}
        self.npc_knowledge: Dict[UUID, NPCGossipKnowledge] = {}

        # Network topology - which NPCs can share gossip with each other
        self.gossip_networks: Dict[str, Set[UUID]] = {
            "starter_town": set(),
            "research_lab": set(),
            "pokemon_center": set(),
            "marketplace": set()
        }

        # Propagation settings
        self.base_spread_probability = 0.3
        self.distance_decay_factor = 0.1
        self.time_decay_hours = 24
        self.max_gossip_per_npc = 20

    async def initialize_npc_networks(self, db: AsyncSession) -> None:
        """Initialize gossip networks based on NPC locations and relationships."""
        from app.game.models import NPC

        try:
            # Get all NPCs
            result = await db.execute(select(NPC))
            npcs = result.scalars().all()

            # Group NPCs by map and initialize networks
            for npc in npcs:
                map_name = npc.map_name
                if map_name not in self.gossip_networks:
                    self.gossip_networks[map_name] = set()

                self.gossip_networks[map_name].add(npc.id)

                # Initialize NPC gossip knowledge if not exists
                if npc.id not in self.npc_knowledge:
                    # Extract personality traits for gossip behavior
                    personality = json.loads(npc.personality_traits or "{}")

                    self.npc_knowledge[npc.id] = NPCGossipKnowledge(
                        npc_id=npc.id,
                        known_gossip=[],
                        last_updated=datetime.utcnow(),
                        gossip_receptiveness=personality.get("agreeableness", 0.5),
                        gossip_spreading=personality.get("extraversion", 0.5)
                    )

            logger.info(f"Initialized gossip networks for {len(self.gossip_networks)} maps")

        except Exception as e:
            logger.error(f"Failed to initialize NPC gossip networks: {e}")

    async def create_gossip(
        self,
        gossip_type: GossipType,
        content: str,
        player_id: UUID,
        source_npc_id: UUID,
        importance: float = 0.5,
        tags: List[str] = None
    ) -> str:
        """Create a new piece of gossip and start its propagation."""
        gossip_id = f"gossip_{datetime.utcnow().timestamp()}_{random.randint(1000, 9999)}"

        gossip_item = GossipItem(
            id=gossip_id,
            gossip_type=gossip_type,
            content=content,
            player_id=player_id,
            source_npc_id=source_npc_id,
            importance=importance,
            timestamp=datetime.utcnow(),
            reliability=1.0,  # Starts at full reliability
            tags=tags or []
        )

        # Store the gossip
        self.active_gossip[gossip_id] = gossip_item

        # Add to source NPC's knowledge
        if source_npc_id in self.npc_knowledge:
            self.npc_knowledge[source_npc_id].known_gossip.append(gossip_item)
            self._cleanup_npc_gossip(source_npc_id)

        logger.info(f"Created gossip: {gossip_type.value} from NPC {source_npc_id}")

        # Start propagation in background
        asyncio.create_task(self._propagate_gossip_async(gossip_id))

        return gossip_id

    async def _propagate_gossip_async(self, gossip_id: str) -> None:
        """Asynchronously propagate gossip through the NPC network."""
        try:
            await asyncio.sleep(random.uniform(5, 15))  # Random delay for realism
            await self.propagate_gossip(gossip_id)
        except Exception as e:
            logger.error(f"Error in async gossip propagation: {e}")

    async def propagate_gossip(self, gossip_id: str) -> int:
        """Propagate a piece of gossip to connected NPCs."""
        if gossip_id not in self.active_gossip:
            return 0

        gossip = self.active_gossip[gossip_id]

        # Check if gossip has reached max spread
        if gossip.spread_count >= gossip.max_spread:
            return 0

        # Check if gossip is too old
        hours_old = (datetime.utcnow() - gossip.timestamp).total_seconds() / 3600
        if hours_old > self.time_decay_hours:
            # Remove old gossip
            self._expire_gossip(gossip_id)
            return 0

        spread_count = 0

        # Find NPCs to spread gossip to
        async for db in get_db():
            try:
                from app.game.models import NPC

                # Get source NPC details
                source_result = await db.execute(
                    select(NPC).where(NPC.id == gossip.source_npc_id)
                )
                source_npc = source_result.scalar_one_or_none()

                if not source_npc:
                    break

                # Get NPCs in the same network (map)
                network_npcs = self.gossip_networks.get(source_npc.map_name, set())

                for target_npc_id in network_npcs:
                    if target_npc_id == gossip.source_npc_id:
                        continue  # Don't spread to self

                    # Check if target NPC already knows this gossip
                    if self._npc_knows_gossip(target_npc_id, gossip_id):
                        continue

                    # Calculate spread probability
                    spread_prob = self._calculate_spread_probability(
                        gossip, gossip.source_npc_id, target_npc_id
                    )

                    # Random roll for spreading
                    if random.random() < spread_prob:
                        await self._spread_to_npc(gossip, target_npc_id)
                        spread_count += 1

                break  # Exit the db session generator

            except Exception as e:
                logger.error(f"Error during gossip propagation: {e}")
                break

        # Update spread count
        gossip.spread_count += spread_count

        if spread_count > 0:
            logger.info(f"Gossip {gossip_id} spread to {spread_count} NPCs")

        return spread_count

    def _calculate_spread_probability(
        self,
        gossip: GossipItem,
        source_npc_id: UUID,
        target_npc_id: UUID
    ) -> float:
        """Calculate probability of gossip spreading between two NPCs."""
        base_prob = self.base_spread_probability

        # Importance factor
        importance_factor = gossip.importance

        # Reliability factor (decreases as gossip spreads)
        reliability_factor = gossip.reliability

        # Target NPC's receptiveness to gossip
        target_knowledge = self.npc_knowledge.get(target_npc_id)
        if target_knowledge:
            receptiveness = target_knowledge.gossip_receptiveness
        else:
            receptiveness = 0.5

        # Source NPC's tendency to spread gossip
        source_knowledge = self.npc_knowledge.get(source_npc_id)
        if source_knowledge:
            spreading_tendency = source_knowledge.gossip_spreading
        else:
            spreading_tendency = 0.5

        # Time decay factor
        hours_old = (datetime.utcnow() - gossip.timestamp).total_seconds() / 3600
        time_decay = max(0, 1 - (hours_old / self.time_decay_hours))

        # Calculate final probability
        final_prob = (
            base_prob *
            importance_factor *
            reliability_factor *
            receptiveness *
            spreading_tendency *
            time_decay
        )

        return min(1.0, final_prob)

    async def _spread_to_npc(self, gossip: GossipItem, target_npc_id: UUID) -> None:
        """Spread gossip to a specific NPC."""
        # Create a copy with reduced reliability
        gossip_copy = GossipItem(
            id=gossip.id,
            gossip_type=gossip.gossip_type,
            content=gossip.content,
            player_id=gossip.player_id,
            source_npc_id=target_npc_id,  # New source
            importance=gossip.importance * 0.9,  # Slight importance decay
            timestamp=gossip.timestamp,
            reliability=gossip.reliability * 0.85,  # Reliability decay
            spread_count=gossip.spread_count,
            max_spread=gossip.max_spread,
            tags=gossip.tags.copy()
        )

        # Add to target NPC's knowledge
        if target_npc_id not in self.npc_knowledge:
            self.npc_knowledge[target_npc_id] = NPCGossipKnowledge(
                npc_id=target_npc_id,
                known_gossip=[],
                last_updated=datetime.utcnow(),
                gossip_receptiveness=0.5,
                gossip_spreading=0.5
            )

        self.npc_knowledge[target_npc_id].known_gossip.append(gossip_copy)
        self.npc_knowledge[target_npc_id].last_updated = datetime.utcnow()

        # Clean up old gossip
        self._cleanup_npc_gossip(target_npc_id)

    def _npc_knows_gossip(self, npc_id: UUID, gossip_id: str) -> bool:
        """Check if an NPC already knows a specific piece of gossip."""
        if npc_id not in self.npc_knowledge:
            return False

        return any(
            g.id == gossip_id
            for g in self.npc_knowledge[npc_id].known_gossip
        )

    def _cleanup_npc_gossip(self, npc_id: UUID) -> None:
        """Clean up old gossip from an NPC's knowledge."""
        if npc_id not in self.npc_knowledge:
            return

        knowledge = self.npc_knowledge[npc_id]

        # Sort by importance and recency, keep only the most important
        knowledge.known_gossip.sort(
            key=lambda g: (g.importance, g.timestamp),
            reverse=True
        )

        # Limit number of gossip items per NPC
        if len(knowledge.known_gossip) > self.max_gossip_per_npc:
            knowledge.known_gossip = knowledge.known_gossip[:self.max_gossip_per_npc]

        # Remove expired gossip
        cutoff_time = datetime.utcnow() - timedelta(hours=self.time_decay_hours)
        knowledge.known_gossip = [
            g for g in knowledge.known_gossip
            if g.timestamp > cutoff_time
        ]

    def _expire_gossip(self, gossip_id: str) -> None:
        """Remove expired gossip from the active gossip store."""
        if gossip_id in self.active_gossip:
            del self.active_gossip[gossip_id]
            logger.debug(f"Expired gossip: {gossip_id}")

    async def get_npc_gossip_about_player(
        self,
        npc_id: UUID,
        player_id: UUID,
        gossip_types: List[GossipType] = None
    ) -> List[GossipItem]:
        """Get all gossip an NPC knows about a specific player."""
        if npc_id not in self.npc_knowledge:
            return []

        relevant_gossip = [
            gossip for gossip in self.npc_knowledge[npc_id].known_gossip
            if gossip.player_id == player_id
        ]

        # Filter by gossip types if specified
        if gossip_types:
            relevant_gossip = [
                gossip for gossip in relevant_gossip
                if gossip.gossip_type in gossip_types
            ]

        # Sort by importance and recency
        relevant_gossip.sort(
            key=lambda g: (g.importance, g.timestamp),
            reverse=True
        )

        return relevant_gossip

    async def generate_player_reputation_summary(
        self,
        player_id: UUID,
        npc_id: UUID
    ) -> Dict[str, float]:
        """Generate a reputation summary for dialogue context."""
        gossip_items = await self.get_npc_gossip_about_player(npc_id, player_id)

        reputation_scores = {
            "trainer_skill": 0.0,
            "helpfulness": 0.0,
            "trustworthiness": 0.0,
            "popularity": 0.0
        }

        if not gossip_items:
            return reputation_scores

        # Analyze gossip to build reputation
        total_weight = 0

        for gossip in gossip_items:
            weight = gossip.importance * gossip.reliability
            total_weight += weight

            # Categorize gossip and update scores
            if gossip.gossip_type == GossipType.BATTLE_RESULT:
                if "won" in gossip.content.lower():
                    reputation_scores["trainer_skill"] += weight * 0.8
                else:
                    reputation_scores["trainer_skill"] -= weight * 0.3

            elif gossip.gossip_type == GossipType.PLAYER_BEHAVIOR:
                if any(word in gossip.content.lower() for word in ["helped", "kind", "generous"]):
                    reputation_scores["helpfulness"] += weight * 0.9
                    reputation_scores["trustworthiness"] += weight * 0.5
                elif any(word in gossip.content.lower() for word in ["rude", "mean", "ignored"]):
                    reputation_scores["helpfulness"] -= weight * 0.7
                    reputation_scores["trustworthiness"] -= weight * 0.4

            elif gossip.gossip_type == GossipType.RELATIONSHIP_CHANGE:
                if "improved" in gossip.content.lower():
                    reputation_scores["popularity"] += weight * 0.6
                elif "worsened" in gossip.content.lower():
                    reputation_scores["popularity"] -= weight * 0.6

        # Normalize scores
        if total_weight > 0:
            for key in reputation_scores:
                reputation_scores[key] = max(-1.0, min(1.0, reputation_scores[key] / total_weight))

        return reputation_scores

    async def record_player_achievement(
        self,
        player_id: UUID,
        achievement: str,
        witness_npc_id: UUID
    ) -> str:
        """Record a player achievement that can become gossip."""
        return await self.create_gossip(
            gossip_type=GossipType.PLAYER_ACHIEVEMENT,
            content=f"The trainer achieved: {achievement}",
            player_id=player_id,
            source_npc_id=witness_npc_id,
            importance=0.8,
            tags=["achievement", "positive"]
        )

    async def record_battle_result(
        self,
        player_id: UUID,
        opponent_npc_id: UUID,
        player_won: bool,
        witness_npc_id: Optional[UUID] = None
    ) -> str:
        """Record a battle result that can become gossip."""
        result_text = "won against" if player_won else "lost to"

        return await self.create_gossip(
            gossip_type=GossipType.BATTLE_RESULT,
            content=f"The trainer {result_text} {opponent_npc_id} in battle",
            player_id=player_id,
            source_npc_id=witness_npc_id or opponent_npc_id,
            importance=0.7,
            tags=["battle", "positive" if player_won else "negative"]
        )

    async def record_relationship_change(
        self,
        player_id: UUID,
        npc_id: UUID,
        change_description: str
    ) -> str:
        """Record a relationship change that can become gossip."""
        return await self.create_gossip(
            gossip_type=GossipType.RELATIONSHIP_CHANGE,
            content=f"The trainer's relationship with {npc_id}: {change_description}",
            player_id=player_id,
            source_npc_id=npc_id,
            importance=0.5,
            tags=["relationship"]
        )

    async def cleanup_old_gossip(self) -> int:
        """Clean up expired gossip across the entire system."""
        cutoff_time = datetime.utcnow() - timedelta(hours=self.time_decay_hours)
        removed_count = 0

        # Clean up active gossip
        expired_gossip_ids = [
            gossip_id for gossip_id, gossip in self.active_gossip.items()
            if gossip.timestamp < cutoff_time
        ]

        for gossip_id in expired_gossip_ids:
            del self.active_gossip[gossip_id]
            removed_count += 1

        # Clean up NPC knowledge
        for npc_id in self.npc_knowledge:
            self._cleanup_npc_gossip(npc_id)

        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} expired gossip items")

        return removed_count

    async def get_gossip_statistics(self) -> Dict[str, any]:
        """Get statistics about the gossip system for monitoring."""
        return {
            "total_active_gossip": len(self.active_gossip),
            "npcs_with_gossip": len([
                npc_id for npc_id, knowledge in self.npc_knowledge.items()
                if knowledge.known_gossip
            ]),
            "gossip_networks": len(self.gossip_networks),
            "average_gossip_per_npc": sum(
                len(knowledge.known_gossip)
                for knowledge in self.npc_knowledge.values()
            ) / max(1, len(self.npc_knowledge)),
            "gossip_by_type": {
                gossip_type.value: sum(
                    1 for gossip in self.active_gossip.values()
                    if gossip.gossip_type == gossip_type
                )
                for gossip_type in GossipType
            }
        }


# Create singleton instance
gossip_manager = GossipPropagationManager()