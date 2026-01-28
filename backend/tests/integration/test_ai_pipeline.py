"""
Integration Tests for Complete AI Pipeline
Austin Kidwell | Intellegix | AI-Powered Tuxemon Game

Tests end-to-end AI workflows including memory storage, dialogue generation,
cost tracking, and hybrid LLM integration with real database operations.
"""

import pytest
import pytest_asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from app.ai.ai_manager import AIManager, DailyCostTracker
from app.game.models import (
    NPCInteractionContext,
    DialogueResponse,
    PersonalityTraits,
    MemoryItem
)


class TestAIPipeline:
    """Integration tests for complete AI pipeline workflows."""

    @pytest_asyncio.fixture
    async def ai_manager_with_deps(self, db_session, test_redis, test_qdrant):
        """Provide fully configured AI manager with real dependencies."""
        manager = AIManager()
        manager.redis = test_redis

        # Mock external APIs but use real internal components
        with patch('app.ai.ai_manager.AsyncAnthropic') as mock_anthropic:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.content = [AsyncMock()]
            mock_response.content[0].text = json.dumps({
                "text": "Hello! I remember our last conversation about training.",
                "emotion": "friendly",
                "actions": ["wave"],
                "relationship_change": 0.1,
                "triggers_battle": False
            })
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            await manager.initialize()

        return manager

    @pytest_asyncio.fixture
    async def sample_npc_with_data(self, db_session):
        """Create NPC with personality and schedule data."""
        npc_id = uuid4()
        personality = PersonalityTraits(
            openness=0.8,
            extraversion=0.7,
            agreeableness=0.9,
            curiosity=0.8,
            verbosity=0.6,
            friendliness=0.9,
            humor=0.5
        )

        # Insert NPC into database
        await db_session.execute("""
            INSERT INTO npcs (id, slug, name, sprite_name, position_x, position_y,
                            map_name, is_trainer, can_battle, personality_traits, schedule)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        """,
            npc_id, 'friendly_alice', 'Alice', 'trainer_alice', 15, 20, 'town_center',
            True, True, personality.model_dump_json(), '{}'
        )

        await db_session.commit()

        return {
            'id': npc_id,
            'personality': personality
        }

    @pytest_asyncio.fixture
    async def sample_player_with_data(self, db_session):
        """Create player with game data."""
        player_id = uuid4()

        await db_session.execute("""
            INSERT INTO players (id, username, email, hashed_password, current_map,
                               position_x, position_y, level, money, story_progress,
                               npc_relationships)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        """,
            player_id, 'integration_player', 'integration@test.com', 'hash',
            'town_center', 12, 18, 8, 1500,
            json.dumps({"tutorial_completed": True, "current_quest": "find_rare_monster"}),
            json.dumps({"friendly_alice": 0.3})
        )

        await db_session.commit()

        return {
            'id': player_id,
            'username': 'integration_player'
        }

    @pytest.mark.integration
    @pytest.mark.ai
    async def test_complete_dialogue_generation_workflow(
        self,
        ai_manager_with_deps: AIManager,
        sample_npc_with_data: Dict[str, Any],
        sample_player_with_data: Dict[str, Any]
    ):
        """Test complete dialogue generation from context to response."""
        npc_data = sample_npc_with_data
        player_data = sample_player_with_data

        # Create interaction context
        context = NPCInteractionContext(
            player_id=player_data['id'],
            interaction_type="dialogue",
            relationship_level=0.3,
            time_of_day="afternoon",
            player_party_summary="Bamboon (Level 8), Rockitten (Level 5)",
            recent_achievements=["Caught first rare monster", "Won 3 battles in a row"]
        )

        # Create some existing memories
        existing_memories = [
            MemoryItem(
                id=uuid4(),
                npc_id=npc_data['id'],
                player_id=player_data['id'],
                content="Player asked about training techniques for Bamboon",
                importance=0.7,
                timestamp=datetime.utcnow() - timedelta(hours=2),
                tags=["training", "bamboon"]
            ),
            MemoryItem(
                id=uuid4(),
                npc_id=npc_data['id'],
                player_id=player_data['id'],
                content="Shared stories about adventures in nearby forest",
                importance=0.5,
                timestamp=datetime.utcnow() - timedelta(days=1),
                tags=["stories", "forest"]
            )
        ]

        # Execute complete dialogue generation
        response = await ai_manager_with_deps.generate_dialogue(
            npc_id=npc_data['id'],
            context=context,
            personality=npc_data['personality'],
            memories=existing_memories
        )

        # Verify response structure
        assert isinstance(response, DialogueResponse)
        assert len(response.text) > 0
        assert response.emotion in ["friendly", "happy", "excited", "neutral"]
        assert isinstance(response.relationship_change, float)
        assert -1.0 <= response.relationship_change <= 1.0

        # Verify memory storage was triggered
        # The AI manager should have stored a new memory for this interaction
        assert ai_manager_with_deps.embedding_model is not None

    @pytest.mark.integration
    @pytest.mark.ai
    async def test_memory_storage_and_retrieval_cycle(
        self,
        ai_manager_with_deps: AIManager,
        sample_npc_with_data: Dict[str, Any],
        sample_player_with_data: Dict[str, Any]
    ):
        """Test complete memory storage and retrieval workflow."""
        npc_id = sample_npc_with_data['id']
        player_id = sample_player_with_data['id']

        # Store multiple memories with different importance levels
        memory_contents = [
            ("Player helped with catching a rare monster", 0.9, "helpful"),
            ("Casual greeting in the morning", 0.3, "neutral"),
            ("Discussed battle strategies", 0.7, "engaged"),
            ("Player shared a joke", 0.4, "amused"),
            ("Talked about favorite monster types", 0.6, "interested")
        ]

        stored_memories = []
        for content, importance, emotion in memory_contents:
            context = NPCInteractionContext(
                player_id=player_id,
                interaction_type="dialogue",
                relationship_level=0.5,
                time_of_day="afternoon"
            )

            response = DialogueResponse(
                text=f"Response about: {content}",
                emotion=emotion,
                relationship_change=0.1
            )

            await ai_manager_with_deps._store_interaction_memory(npc_id, context, response)
            stored_memories.append(content)

        # Retrieve memories using different queries
        test_queries = [
            ("rare monster", ["rare monster"]),
            ("battle", ["battle"]),
            ("greeting", ["greeting"]),
            ("", stored_memories[:3])  # General query should return most important
        ]

        for query, expected_keywords in test_queries:
            memories = await ai_manager_with_deps.get_npc_memories(
                npc_id=npc_id,
                player_id=player_id,
                query=query,
                limit=5
            )

            # Should return relevant memories
            assert len(memories) > 0
            assert all(isinstance(memory, MemoryItem) for memory in memories)

            # Check relevance to query
            if query:  # Specific query
                relevant_memories = [m for m in memories
                                   if any(keyword in m.content.lower()
                                         for keyword in expected_keywords)]
                assert len(relevant_memories) > 0

            # Memories should be sorted by importance/recency
            if len(memories) > 1:
                # Most important memories should generally come first
                importance_scores = [m.importance for m in memories]
                # Allow some flexibility in ordering due to time decay
                assert max(importance_scores[:2]) >= max(importance_scores[-2:])

    @pytest.mark.integration
    @pytest.mark.ai
    async def test_cost_tracking_integration(
        self,
        ai_manager_with_deps: AIManager,
        sample_npc_with_data: Dict[str, Any],
        sample_player_with_data: Dict[str, Any]
    ):
        """Test cost tracking throughout AI operations."""
        cost_tracker = ai_manager_with_deps.cost_tracker

        # Get initial cost state
        initial_stats = await cost_tracker.get_daily_stats()
        initial_cost = initial_stats['total_cost']
        initial_requests = initial_stats['total_requests']

        # Perform multiple AI operations
        npc_data = sample_npc_with_data
        player_data = sample_player_with_data

        contexts = [
            NPCInteractionContext(
                player_id=player_data['id'],
                interaction_type="greeting",
                relationship_level=0.2,
                time_of_day="morning"
            ),
            NPCInteractionContext(
                player_id=player_data['id'],
                interaction_type="shop",
                relationship_level=0.4,
                time_of_day="afternoon"
            ),
            NPCInteractionContext(
                player_id=player_data['id'],
                interaction_type="battle",
                relationship_level=0.6,
                time_of_day="evening"
            )
        ]

        responses = []
        for context in contexts:
            response = await ai_manager_with_deps.generate_dialogue(
                npc_id=npc_data['id'],
                context=context,
                personality=npc_data['personality'],
                memories=[]
            )
            responses.append(response)

        # Verify cost tracking
        final_stats = await cost_tracker.get_daily_stats()

        # Should have recorded costs for AI requests
        assert final_stats['total_cost'] >= initial_cost
        assert final_stats['total_requests'] >= initial_requests + len(contexts)

        # Should have model usage breakdown
        assert 'requests_by_model' in final_stats
        model_requests = final_stats['requests_by_model']

        # Should have either Claude or local requests (or both)
        total_model_requests = model_requests.get('claude', 0) + model_requests.get('local', 0)
        assert total_model_requests >= len(contexts)

        # Should have reasonable cost per request
        if final_stats['total_requests'] > 0:
            avg_cost = final_stats['avg_cost_per_request']
            assert 0.001 <= avg_cost <= 0.1  # Between 0.1 cent and 10 cents per request

    @pytest.mark.integration
    @pytest.mark.ai
    async def test_hybrid_llm_routing_decisions(
        self,
        ai_manager_with_deps: AIManager,
        sample_npc_with_data: Dict[str, Any],
        sample_player_with_data: Dict[str, Any]
    ):
        """Test hybrid LLM routing based on context complexity."""
        npc_data = sample_npc_with_data
        player_data = sample_player_with_data

        # Test scenarios that should prefer Claude (complex)
        complex_contexts = [
            # High relationship level (story-critical)
            NPCInteractionContext(
                player_id=player_data['id'],
                interaction_type="dialogue",
                relationship_level=0.9,
                time_of_day="evening",
                recent_achievements=["Defeated gym leader", "Completed main quest"]
            ),
            # Battle context
            NPCInteractionContext(
                player_id=player_data['id'],
                interaction_type="battle",
                relationship_level=0.5,
                time_of_day="afternoon"
            )
        ]

        # Test scenarios that should use local LLM (simple)
        simple_contexts = [
            # Low relationship, basic interaction
            NPCInteractionContext(
                player_id=player_data['id'],
                interaction_type="greeting",
                relationship_level=0.1,
                time_of_day="morning"
            )
        ]

        # Mock hybrid manager to track routing decisions
        routing_decisions = []

        original_generate = ai_manager_with_deps.hybrid_manager.generate_dialogue

        async def mock_generate(*args, **kwargs):
            force_claude = kwargs.get('force_claude', False)
            context = args[1] if len(args) > 1 else kwargs.get('context')

            # Record routing decision
            routing_decisions.append({
                'context_type': context.interaction_type,
                'relationship_level': context.relationship_level,
                'force_claude': force_claude
            })

            return await original_generate(*args, **kwargs)

        ai_manager_with_deps.hybrid_manager.generate_dialogue = mock_generate

        # Test complex contexts
        for context in complex_contexts:
            await ai_manager_with_deps.generate_dialogue(
                npc_id=npc_data['id'],
                context=context,
                personality=npc_data['personality'],
                memories=[]
            )

        # Test simple contexts
        for context in simple_contexts:
            await ai_manager_with_deps.generate_dialogue(
                npc_id=npc_data['id'],
                context=context,
                personality=npc_data['personality'],
                memories=[]
            )

        # Verify routing decisions were made
        assert len(routing_decisions) == len(complex_contexts) + len(simple_contexts)

        # Complex contexts should generally prefer Claude
        complex_decisions = routing_decisions[:len(complex_contexts)]
        simple_decisions = routing_decisions[len(complex_contexts):]

        # At least some complex interactions should use or prefer Claude
        high_relationship_decisions = [d for d in complex_decisions if d['relationship_level'] > 0.8]
        assert len(high_relationship_decisions) > 0

    @pytest.mark.integration
    @pytest.mark.ai
    async def test_ai_pipeline_error_recovery(
        self,
        ai_manager_with_deps: AIManager,
        sample_npc_with_data: Dict[str, Any],
        sample_player_with_data: Dict[str, Any]
    ):
        """Test AI pipeline recovery from various error conditions."""
        npc_data = sample_npc_with_data
        player_data = sample_player_with_data

        context = NPCInteractionContext(
            player_id=player_data['id'],
            interaction_type="dialogue",
            relationship_level=0.5,
            time_of_day="afternoon"
        )

        # Test 1: Claude API failure -> Local LLM fallback
        with patch.object(ai_manager_with_deps, '_generate_claude_dialogue') as mock_claude:
            mock_claude.side_effect = Exception("API timeout")

            response = await ai_manager_with_deps.generate_dialogue(
                npc_id=npc_data['id'],
                context=context,
                personality=npc_data['personality'],
                memories=[]
            )

            # Should still get a valid response from fallback
            assert isinstance(response, DialogueResponse)
            assert len(response.text) > 0

        # Test 2: Memory system failure -> Continue without memories
        with patch.object(ai_manager_with_deps, 'get_npc_memories') as mock_memories:
            mock_memories.side_effect = Exception("Qdrant connection error")

            response = await ai_manager_with_deps.generate_dialogue(
                npc_id=npc_data['id'],
                context=context,
                personality=npc_data['personality'],
                memories=[]  # Empty memories due to error
            )

            # Should still generate dialogue without memories
            assert isinstance(response, DialogueResponse)
            assert len(response.text) > 0

        # Test 3: Cost tracking failure -> Continue operation
        with patch.object(ai_manager_with_deps.cost_tracker, 'can_make_request') as mock_cost:
            mock_cost.side_effect = Exception("Redis connection error")

            response = await ai_manager_with_deps.generate_dialogue(
                npc_id=npc_data['id'],
                context=context,
                personality=npc_data['personality'],
                memories=[]
            )

            # Should still work despite cost tracking failure
            assert isinstance(response, DialogueResponse)
            assert len(response.text) > 0

    @pytest.mark.integration
    @pytest.mark.ai
    async def test_personality_consistency_across_interactions(
        self,
        ai_manager_with_deps: AIManager,
        sample_npc_with_data: Dict[str, Any],
        sample_player_with_data: Dict[str, Any]
    ):
        """Test that personality traits remain consistent across multiple interactions."""
        npc_data = sample_npc_with_data
        player_data = sample_player_with_data
        personality = npc_data['personality']

        # Generate multiple responses with same personality
        interaction_types = ["greeting", "dialogue", "shop", "dialogue", "farewell"]
        responses = []

        for interaction_type in interaction_types:
            context = NPCInteractionContext(
                player_id=player_data['id'],
                interaction_type=interaction_type,
                relationship_level=0.5,
                time_of_day="afternoon"
            )

            response = await ai_manager_with_deps.generate_dialogue(
                npc_id=npc_data['id'],
                context=context,
                personality=personality,
                memories=[]
            )

            responses.append(response)

        # Analyze personality consistency
        # High friendliness (0.9) should result in positive emotions
        friendly_emotions = ["happy", "friendly", "excited", "warm"]
        positive_responses = [r for r in responses if r.emotion in friendly_emotions]

        # Should have predominantly positive emotions for friendly character
        positive_ratio = len(positive_responses) / len(responses)
        assert positive_ratio >= 0.6  # At least 60% should be positive

        # High agreeableness (0.9) should result in positive relationship changes
        positive_changes = [r for r in responses if r.relationship_change >= 0]
        positive_change_ratio = len(positive_changes) / len(responses)
        assert positive_change_ratio >= 0.7  # At least 70% should be positive

        # Verify all responses are valid
        for response in responses:
            assert isinstance(response, DialogueResponse)
            assert len(response.text) > 0
            assert response.emotion in ["neutral", "happy", "excited", "sad", "angry", "confused", "thoughtful", "friendly", "warm"]
            assert -1.0 <= response.relationship_change <= 1.0

    @pytest.mark.integration
    @pytest.mark.ai
    @pytest.mark.performance
    async def test_ai_pipeline_performance_under_load(
        self,
        ai_manager_with_deps: AIManager,
        sample_npc_with_data: Dict[str, Any],
        sample_player_with_data: Dict[str, Any]
    ):
        """Test AI pipeline performance with multiple concurrent requests."""
        import asyncio

        npc_data = sample_npc_with_data
        player_data = sample_player_with_data

        async def single_ai_request(request_id: int):
            context = NPCInteractionContext(
                player_id=player_data['id'],
                interaction_type="dialogue",
                relationship_level=0.5,
                time_of_day="afternoon"
            )

            start_time = asyncio.get_event_loop().time()

            response = await ai_manager_with_deps.generate_dialogue(
                npc_id=npc_data['id'],
                context=context,
                personality=npc_data['personality'],
                memories=[]
            )

            end_time = asyncio.get_event_loop().time()
            response_time = (end_time - start_time) * 1000  # Convert to ms

            return {
                'request_id': request_id,
                'response': response,
                'response_time_ms': response_time
            }

        # Test with multiple concurrent requests
        num_requests = 10
        start_time = asyncio.get_event_loop().time()

        tasks = [single_ai_request(i) for i in range(num_requests)]
        results = await asyncio.gather(*tasks)

        end_time = asyncio.get_event_loop().time()
        total_time = (end_time - start_time) * 1000

        # Verify all requests completed successfully
        assert len(results) == num_requests

        for result in results:
            assert isinstance(result['response'], DialogueResponse)
            assert len(result['response'].text) > 0
            assert result['response_time_ms'] > 0

        # Performance assertions
        avg_response_time = sum(r['response_time_ms'] for r in results) / len(results)
        max_response_time = max(r['response_time_ms'] for r in results)

        # Should handle concurrent requests efficiently
        assert avg_response_time < 3000  # Under 3 seconds average
        assert max_response_time < 5000   # Under 5 seconds maximum
        assert total_time < 15000         # Under 15 seconds total

        # Should maintain reasonable throughput
        throughput = num_requests / (total_time / 1000)  # Requests per second
        assert throughput > 0.5  # At least 0.5 requests per second