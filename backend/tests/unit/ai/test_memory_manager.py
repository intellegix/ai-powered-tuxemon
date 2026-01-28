"""
Unit Tests for AI Memory Management System
Austin Kidwell | Intellegix | AI-Powered Tuxemon Game

Tests vector embedding storage, retrieval accuracy, and memory persistence
across NPC interactions with comprehensive coverage of the memory system.
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from app.ai.ai_manager import AIManager
from app.game.models import MemoryItem, NPCInteractionContext, PersonalityTraits


class TestMemoryManager:
    """Test suite for AI memory management functionality."""

    @pytest_asyncio.fixture
    async def ai_manager(self, test_qdrant, mock_sentence_transformer):
        """Provide configured AI manager with test dependencies."""
        manager = AIManager()
        manager.embedding_model = mock_sentence_transformer
        # Use test collection name
        manager._test_collection = test_qdrant._test_collection
        return manager

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_store_interaction_memory_basic(
        self,
        ai_manager: AIManager,
        sample_npc: Any,
        sample_player: Any,
        mock_sentence_transformer: MagicMock
    ):
        """Test basic memory storage functionality."""
        # Setup
        npc_id = sample_npc.id
        context = NPCInteractionContext(
            player_id=sample_player.id,
            interaction_type="greeting",
            relationship_level=0.5,
            time_of_day="morning",
            player_party_summary="Bamboon (Level 5)",
            recent_achievements=["Found a rare item"]
        )

        from app.game.models import DialogueResponse
        response = DialogueResponse(
            text="Hello! Nice to see you again!",
            emotion="happy",
            relationship_change=0.1
        )

        # Mock embedding generation
        mock_sentence_transformer.encode.return_value = [0.1] * 384

        # Execute
        with patch('app.ai.ai_manager.qdrant_client') as mock_qdrant:
            await ai_manager._store_interaction_memory(npc_id, context, response)

            # Verify
            mock_qdrant.upsert.assert_called_once()
            call_args = mock_qdrant.upsert.call_args[1]

            assert call_args["collection_name"] == "npc_memories"
            points = call_args["points"]
            assert len(points) == 1

            point = points[0]
            assert point.payload["npc_id"] == str(npc_id)
            assert point.payload["player_id"] == str(sample_player.id)
            assert "Talked with player about greeting" in point.payload["content"]
            assert point.payload["importance"] > 0.1  # Should have some importance
            assert point.payload["emotional_context"] == "happy"

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_memory_importance_calculation(
        self,
        ai_manager: AIManager,
        sample_npc: Any,
        sample_player: Any
    ):
        """Test importance calculation for different interaction types."""
        npc_id = sample_npc.id

        # Test high-importance battle interaction
        battle_context = NPCInteractionContext(
            player_id=sample_player.id,
            interaction_type="battle",
            relationship_level=0.8,
            time_of_day="afternoon",
            player_party_summary="Bamboon (Level 10)",
            recent_achievements=["Won 5 battles in a row"]
        )

        from app.game.models import DialogueResponse
        battle_response = DialogueResponse(
            text="Great battle! Your Bamboon is really strong!",
            emotion="excited",
            relationship_change=0.3,
            triggers_battle=True
        )

        with patch('app.ai.ai_manager.qdrant_client') as mock_qdrant:
            with patch.object(ai_manager.embedding_model, 'encode', return_value=[0.1] * 384):
                await ai_manager._store_interaction_memory(npc_id, battle_context, battle_response)

                # Verify high importance for battle + achievements + positive relationship change
                point = mock_qdrant.upsert.call_args[1]["points"][0]
                importance = point.payload["importance"]

                # Should be high importance due to:
                # - Battle interaction (+0.3)
                # - High relationship level (+0.8)
                # - Recent achievements (+0.2)
                # - Positive relationship change (+0.1)
                assert importance >= 0.9  # Near maximum importance

        # Test low-importance casual interaction
        casual_context = NPCInteractionContext(
            player_id=sample_player.id,
            interaction_type="greeting",
            relationship_level=0.2,
            time_of_day="evening",
            player_party_summary="",
            recent_achievements=[]
        )

        casual_response = DialogueResponse(
            text="Hello.",
            emotion="neutral",
            relationship_change=0.0
        )

        with patch('app.ai.ai_manager.qdrant_client') as mock_qdrant:
            with patch.object(ai_manager.embedding_model, 'encode', return_value=[0.1] * 384):
                await ai_manager._store_interaction_memory(npc_id, casual_context, casual_response)

                point = mock_qdrant.upsert.call_args[1]["points"][0]
                importance = point.payload["importance"]

                # Should be low importance (base + relationship level)
                assert 0.2 <= importance <= 0.4

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_get_npc_memories_semantic_search(
        self,
        ai_manager: AIManager,
        sample_npc: Any,
        sample_player: Any,
        mock_sentence_transformer: MagicMock
    ):
        """Test semantic memory retrieval with relevance scoring."""
        npc_id = sample_npc.id
        player_id = sample_player.id

        # Mock Qdrant search results
        mock_results = [
            MagicMock(
                id="memory_1",
                payload={
                    "npc_id": str(npc_id),
                    "player_id": str(player_id),
                    "content": "Player asked about rare monsters in the forest",
                    "importance": 0.8,
                    "timestamp": datetime.utcnow().isoformat(),
                    "interaction_type": "dialogue",
                    "emotional_context": "curious"
                },
                score=0.95
            ),
            MagicMock(
                id="memory_2",
                payload={
                    "npc_id": str(npc_id),
                    "player_id": str(player_id),
                    "content": "Casual greeting, player seemed friendly",
                    "importance": 0.4,
                    "timestamp": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
                    "interaction_type": "greeting",
                    "emotional_context": "neutral"
                },
                score=0.65
            )
        ]

        with patch('app.ai.ai_manager.qdrant_client') as mock_qdrant:
            mock_qdrant.search.return_value = mock_results

            # Execute semantic search
            memories = await ai_manager.get_npc_memories(
                npc_id=npc_id,
                player_id=player_id,
                query="monsters forest exploration",
                limit=5,
                context_type="dialogue"
            )

            # Verify
            assert len(memories) == 2
            assert memories[0].content == "Player asked about rare monsters in the forest"
            assert memories[0].importance == 0.8
            assert memories[1].content == "Casual greeting, player seemed friendly"

            # Verify search was called with correct parameters
            mock_qdrant.search.assert_called_once()
            call_args = mock_qdrant.search.call_args[1]

            assert call_args["collection_name"] == "npc_memories"
            assert call_args["limit"] == 5
            assert call_args["score_threshold"] == 0.3

            # Verify filter conditions
            filter_conditions = call_args["query_filter"].must
            npc_filter = next(c for c in filter_conditions if c.key == "npc_id")
            player_filter = next(c for c in filter_conditions if c.key == "player_id")

            assert npc_filter.match.value == str(npc_id)
            assert player_filter.match.value == str(player_id)

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_memory_retrieval_no_query_fallback(
        self,
        ai_manager: AIManager,
        sample_npc: Any,
        sample_player: Any
    ):
        """Test memory retrieval with default query when none provided."""
        npc_id = sample_npc.id
        player_id = sample_player.id

        mock_results = [
            MagicMock(
                id="memory_1",
                payload={
                    "npc_id": str(npc_id),
                    "player_id": str(player_id),
                    "content": "General conversation",
                    "importance": 0.6,
                    "timestamp": datetime.utcnow().isoformat(),
                    "interaction_type": "dialogue"
                },
                score=0.75
            )
        ]

        with patch('app.ai.ai_manager.qdrant_client') as mock_qdrant:
            mock_qdrant.search.return_value = mock_results

            # Execute without explicit query
            memories = await ai_manager.get_npc_memories(
                npc_id=npc_id,
                player_id=player_id,
                query="",  # Empty query should trigger fallback
                limit=10,
                context_type="dialogue"
            )

            # Verify default query was used
            call_args = mock_qdrant.search.call_args[1]

            # Should have generated embedding for default query
            ai_manager.embedding_model.encode.assert_called()
            encoded_query = ai_manager.embedding_model.encode.call_args[0][0]
            assert "conversation interaction dialogue talk" in encoded_query.lower()

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_memory_filtering_by_importance(
        self,
        ai_manager: AIManager,
        sample_npc: Any,
        sample_player: Any
    ):
        """Test that low-importance memories are filtered out."""
        npc_id = sample_npc.id
        player_id = sample_player.id

        with patch('app.ai.ai_manager.qdrant_client') as mock_qdrant:
            await ai_manager.get_npc_memories(
                npc_id=npc_id,
                player_id=player_id,
                query="",
                limit=10
            )

            # Verify importance filter was applied
            call_args = mock_qdrant.search.call_args[1]
            filter_conditions = call_args["query_filter"].must

            importance_filter = next(
                (c for c in filter_conditions if c.key == "importance"),
                None
            )

            assert importance_filter is not None
            assert importance_filter.range.gte == 0.3  # Minimum importance threshold

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_memory_retrieval_error_handling(
        self,
        ai_manager: AIManager,
        sample_npc: Any,
        sample_player: Any
    ):
        """Test graceful error handling during memory retrieval."""
        npc_id = sample_npc.id
        player_id = sample_player.id

        with patch('app.ai.ai_manager.qdrant_client') as mock_qdrant:
            # Simulate Qdrant connection error
            mock_qdrant.search.side_effect = Exception("Connection failed")

            # Should return empty list instead of crashing
            memories = await ai_manager.get_npc_memories(
                npc_id=npc_id,
                player_id=player_id,
                query="test query"
            )

            assert memories == []

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_memory_content_enrichment(
        self,
        ai_manager: AIManager,
        sample_npc: Any,
        sample_player: Any
    ):
        """Test that memory content includes rich contextual information."""
        npc_id = sample_npc.id

        context = NPCInteractionContext(
            player_id=sample_player.id,
            interaction_type="shop",
            relationship_level=0.6,
            time_of_day="afternoon",
            player_party_summary="Bamboon (Level 8), Rockitten (Level 3)",
            recent_achievements=["Caught first rare monster", "Defeated gym trainer"]
        )

        from app.game.models import DialogueResponse
        response = DialogueResponse(
            text="Thanks for shopping! That rare monster you caught is impressive!",
            emotion="impressed",
            relationship_change=0.15
        )

        with patch('app.ai.ai_manager.qdrant_client') as mock_qdrant:
            with patch.object(ai_manager.embedding_model, 'encode', return_value=[0.1] * 384):
                await ai_manager._store_interaction_memory(npc_id, context, response)

                point = mock_qdrant.upsert.call_args[1]["points"][0]
                memory_content = point.payload["content"]

                # Verify rich context is included
                assert "shop" in memory_content
                assert "Caught first rare monster" in memory_content
                assert "Defeated gym trainer" in memory_content
                assert "Bamboon (Level 8), Rockitten (Level 3)" in memory_content
                assert "Thanks for shopping" in memory_content

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_memory_timestamp_ordering(
        self,
        ai_manager: AIManager,
        sample_npc: Any,
        sample_player: Any
    ):
        """Test that memories are returned in correct chronological order."""
        npc_id = sample_npc.id
        player_id = sample_player.id

        # Create mock memories with different timestamps
        old_time = datetime.utcnow() - timedelta(hours=5)
        recent_time = datetime.utcnow() - timedelta(minutes=30)
        very_recent_time = datetime.utcnow() - timedelta(minutes=5)

        mock_results = [
            MagicMock(
                id="memory_old",
                payload={
                    "npc_id": str(npc_id),
                    "player_id": str(player_id),
                    "content": "Old interaction",
                    "importance": 0.5,
                    "timestamp": old_time.isoformat(),
                    "interaction_type": "greeting"
                }
            ),
            MagicMock(
                id="memory_recent",
                payload={
                    "npc_id": str(npc_id),
                    "player_id": str(player_id),
                    "content": "Recent interaction",
                    "importance": 0.6,
                    "timestamp": recent_time.isoformat(),
                    "interaction_type": "dialogue"
                }
            ),
            MagicMock(
                id="memory_very_recent",
                payload={
                    "npc_id": str(npc_id),
                    "player_id": str(player_id),
                    "content": "Very recent interaction",
                    "importance": 0.4,
                    "timestamp": very_recent_time.isoformat(),
                    "interaction_type": "greeting"
                }
            )
        ]

        with patch('app.ai.ai_manager.qdrant_client') as mock_qdrant:
            mock_qdrant.search.return_value = mock_results

            memories = await ai_manager.get_npc_memories(
                npc_id=npc_id,
                player_id=player_id,
                query="interaction"
            )

            # Verify memories are sorted by timestamp (most recent first)
            assert len(memories) == 3
            assert memories[0].content == "Very recent interaction"
            assert memories[1].content == "Recent interaction"
            assert memories[2].content == "Old interaction"

    @pytest.mark.unit
    @pytest.mark.ai
    @pytest.mark.slow
    async def test_memory_performance_with_large_dataset(
        self,
        ai_manager: AIManager,
        sample_npc: Any,
        sample_player: Any
    ):
        """Test memory system performance with larger dataset simulation."""
        npc_id = sample_npc.id
        player_id = sample_player.id

        # Simulate large number of memory results
        large_mock_results = []
        for i in range(100):  # Simulate 100 memories
            large_mock_results.append(
                MagicMock(
                    id=f"memory_{i}",
                    payload={
                        "npc_id": str(npc_id),
                        "player_id": str(player_id),
                        "content": f"Interaction number {i}",
                        "importance": 0.3 + (i % 7) * 0.1,  # Vary importance
                        "timestamp": (datetime.utcnow() - timedelta(minutes=i)).isoformat(),
                        "interaction_type": "dialogue"
                    },
                    score=0.8 - (i * 0.005)  # Decreasing relevance
                )
            )

        with patch('app.ai.ai_manager.qdrant_client') as mock_qdrant:
            mock_qdrant.search.return_value = large_mock_results

            # Measure retrieval time
            import time
            start_time = time.time()

            memories = await ai_manager.get_npc_memories(
                npc_id=npc_id,
                player_id=player_id,
                query="interaction",
                limit=10  # Should limit results
            )

            end_time = time.time()
            retrieval_time = (end_time - start_time) * 1000  # Convert to ms

            # Performance assertions
            assert retrieval_time < 100  # Should complete in under 100ms
            assert len(memories) <= 10  # Should respect limit

            # Verify most relevant/recent memories are returned
            assert memories[0].content == "Interaction number 0"  # Most recent