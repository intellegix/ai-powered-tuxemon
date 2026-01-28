"""
Unit Tests for AI Dialogue Generation System
Austin Kidwell | Intellegix | AI-Powered Tuxemon Game

Tests LLM routing logic, response caching, hybrid AI approach, and dialogue
quality validation for the AI-powered NPC conversation system.
"""

import pytest
import pytest_asyncio
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from app.ai.ai_manager import AIManager
from app.game.models import (
    NPCInteractionContext,
    DialogueResponse,
    PersonalityTraits,
    MemoryItem
)


class TestDialogueGenerator:
    """Test suite for AI dialogue generation and hybrid LLM routing."""

    @pytest_asyncio.fixture
    async def ai_manager(
        self,
        test_redis,
        test_qdrant,
        mock_claude_api,
        mock_local_llm,
        mock_sentence_transformer
    ):
        """Provide configured AI manager with all mocked dependencies."""
        manager = AIManager()
        manager.redis = test_redis
        manager.embedding_model = mock_sentence_transformer

        # Mock settings
        with patch('app.ai.ai_manager.settings') as mock_settings:
            mock_settings.claude_api_key = "test_key"
            mock_settings.ai_enabled = True
            mock_settings.ai_cache_ttl = 300
            mock_settings.max_cost_per_day_usd = 10.0

            # Initialize with mocked components
            await manager.initialize()

        return manager

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_generate_dialogue_with_claude_api(
        self,
        ai_manager: AIManager,
        sample_npc: Any,
        sample_player: Any,
        mock_claude_api: AsyncMock
    ):
        """Test dialogue generation using Claude API for high-quality responses."""
        # Setup
        npc_id = sample_npc.id
        personality = PersonalityTraits(
            openness=0.8,
            extraversion=0.7,
            friendliness=0.9,
            verbosity=0.6,
            humor=0.7
        )

        context = NPCInteractionContext(
            player_id=sample_player.id,
            interaction_type="greeting",
            relationship_level=0.6,
            time_of_day="morning",
            player_party_summary="Bamboon (Level 5)",
            recent_achievements=["Caught first Tuxemon"]
        )

        memories = [
            MemoryItem(
                id=uuid4(),
                npc_id=npc_id,
                player_id=sample_player.id,
                content="Player helped me find a lost item yesterday",
                importance=0.8,
                timestamp=datetime.utcnow() - timedelta(hours=24),
                tags=["helpful", "quest"]
            )
        ]

        # Mock Claude response
        mock_claude_response = {
            "text": "Hello again! I still remember how you helped me find my lost item yesterday. Your Bamboon looks stronger too!",
            "emotion": "grateful",
            "actions": ["wave", "smile"],
            "relationship_change": 0.1,
            "triggers_battle": False
        }

        mock_claude_api.messages.create.return_value.content[0].text = json.dumps(mock_claude_response)

        # Execute
        with patch.object(ai_manager.cost_tracker, 'can_make_request', return_value=True):
            with patch.object(ai_manager.cost_tracker, 'record_request') as mock_record:
                response = await ai_manager.generate_dialogue(
                    npc_id=npc_id,
                    context=context,
                    personality=personality,
                    memories=memories,
                    force_claude=True
                )

                # Verify response structure
                assert isinstance(response, DialogueResponse)
                assert response.text == mock_claude_response["text"]
                assert response.emotion == "grateful"
                assert response.relationship_change == 0.1
                assert response.triggers_battle is False

                # Verify cost tracking
                mock_record.assert_called_once()
                record_args = mock_record.call_args[1]
                assert record_args["model_used"] == "claude"
                assert record_args["estimated_cost"] == 0.02

                # Verify Claude API was called with proper prompt
                mock_claude_api.messages.create.assert_called_once()
                call_args = mock_claude_api.messages.create.call_args[1]

                assert call_args["model"] == "claude-3-5-sonnet-20241022"
                assert call_args["max_tokens"] == 300
                assert call_args["temperature"] == 0.7

                # Verify prompt includes memories
                prompt_content = call_args["messages"][0]["content"]
                assert "helped me find my lost item" in prompt_content
                assert "grateful" in prompt_content.lower() or "remember" in prompt_content.lower()

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_generate_dialogue_with_local_llm_fallback(
        self,
        ai_manager: AIManager,
        sample_npc: Any,
        sample_player: Any,
        mock_local_llm: AsyncMock
    ):
        """Test dialogue generation falling back to local LLM when Claude unavailable."""
        # Setup
        npc_id = sample_npc.id
        personality = PersonalityTraits(
            friendliness=0.5,
            verbosity=0.4
        )

        context = NPCInteractionContext(
            player_id=sample_player.id,
            interaction_type="greeting",
            relationship_level=0.3,
            time_of_day="afternoon",
            player_party_summary="",
            recent_achievements=[]
        )

        # Mock local LLM response
        mock_local_response = {
            "response": json.dumps({
                "text": "Hello there! How are you doing today?",
                "emotion": "neutral",
                "relationship_change": 0.05
            }),
            "done": True
        }

        mock_local_llm.post.return_value.json.return_value = mock_local_response

        # Mock cost limit reached (force local LLM usage)
        with patch.object(ai_manager.cost_tracker, 'can_make_request', return_value=False):
            with patch.object(ai_manager.cost_tracker, 'record_request') as mock_record:
                response = await ai_manager.generate_dialogue(
                    npc_id=npc_id,
                    context=context,
                    personality=personality,
                    memories=[]
                )

                # Verify local LLM response
                assert response.text == "Hello there! How are you doing today?"
                assert response.emotion == "neutral"

                # Verify cost tracking for local usage
                mock_record.assert_called_once()
                record_args = mock_record.call_args[1]
                assert record_args["model_used"] == "local"
                assert record_args["estimated_cost"] == 0.001  # Much lower cost

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_dialogue_caching_functionality(
        self,
        ai_manager: AIManager,
        sample_npc: Any,
        sample_player: Any,
        test_redis
    ):
        """Test that dialogue responses are properly cached and retrieved."""
        # Setup
        npc_id = sample_npc.id
        context = NPCInteractionContext(
            player_id=sample_player.id,
            interaction_type="greeting",
            relationship_level=0.5,
            time_of_day="morning",
            player_party_summary="Bamboon (Level 5)",
            recent_achievements=[]
        )

        personality = PersonalityTraits(friendliness=0.7)
        memories = []

        # Mock response for first call
        cached_response = DialogueResponse(
            text="Hello! Good to see you!",
            emotion="happy",
            relationship_change=0.1
        )

        # First call - should generate and cache
        with patch.object(ai_manager, '_generate_claude_dialogue', return_value=cached_response):
            with patch.object(ai_manager.cost_tracker, 'can_make_request', return_value=True):
                response1 = await ai_manager.generate_dialogue(
                    npc_id=npc_id,
                    context=context,
                    personality=personality,
                    memories=memories
                )

                assert response1.text == "Hello! Good to see you!"

        # Second call with identical parameters - should use cache
        with patch.object(ai_manager, '_generate_claude_dialogue') as mock_claude:
            response2 = await ai_manager.generate_dialogue(
                npc_id=npc_id,
                context=context,
                personality=personality,
                memories=memories
            )

            # Verify Claude was not called again
            mock_claude.assert_not_called()
            assert response2.text == "Hello! Good to see you!"

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_dialogue_prompt_building_with_memories(
        self,
        ai_manager: AIManager,
        sample_npc: Any,
        sample_player: Any
    ):
        """Test that dialogue prompts properly incorporate NPC memories."""
        # Setup with rich context
        context = NPCInteractionContext(
            player_id=sample_player.id,
            interaction_type="dialogue",
            relationship_level=0.7,
            time_of_day="evening",
            player_party_summary="Bamboon (Level 10), Rockitten (Level 5)",
            recent_achievements=["Defeated gym leader", "Caught rare monster"]
        )

        personality = PersonalityTraits(
            openness=0.8,
            extraversion=0.9,
            friendliness=0.8,
            verbosity=0.9,
            humor=0.6
        )

        memories = [
            MemoryItem(
                id=uuid4(),
                npc_id=sample_npc.id,
                player_id=sample_player.id,
                content="Player asked about training techniques for Bamboon",
                importance=0.8,
                timestamp=datetime.utcnow() - timedelta(hours=2),
                tags=["training", "bamboon"],
                emotional_context="curious"
            ),
            MemoryItem(
                id=uuid4(),
                npc_id=sample_npc.id,
                player_id=sample_player.id,
                content="Shared stories about adventures in the forest",
                importance=0.6,
                timestamp=datetime.utcnow() - timedelta(days=1),
                tags=["stories", "adventure"],
                emotional_context="excited"
            )
        ]

        # Execute prompt building
        prompt = ai_manager._build_dialogue_prompt(
            context=context,
            personality=personality,
            memories=memories
        )

        # Verify prompt structure and content
        assert "You are roleplaying as an NPC" in prompt
        assert "Pokemon-style game called Tuxemon" in prompt

        # Verify personality integration
        assert "very curious and asks many questions" in prompt  # High openness
        assert "talkative and gives detailed responses" in prompt  # High verbosity
        assert "warm and welcoming" in prompt  # High friendliness

        # Verify memory integration
        assert "Player asked about training techniques for Bamboon" in prompt
        assert "Shared stories about adventures in the forest" in prompt
        assert "2 hour(s) ago" in prompt or "Recently" in prompt

        # Verify context integration
        assert "dialogue" in prompt
        assert "0.70" in prompt  # Relationship level
        assert "evening" in prompt
        assert "Defeated gym leader" in prompt
        assert "Caught rare monster" in prompt

        # Verify response format requirements
        assert "JSON response" in prompt
        assert '"text":' in prompt
        assert '"emotion":' in prompt
        assert '"relationship_change":' in prompt

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_dialogue_prompt_emotional_influence(
        self,
        ai_manager: AIManager,
        sample_npc: Any,
        sample_player: Any
    ):
        """Test that emotional influence is properly integrated into prompts."""
        context = NPCInteractionContext(
            player_id=sample_player.id,
            interaction_type="greeting",
            relationship_level=0.5,
            time_of_day="morning"
        )

        personality = PersonalityTraits(friendliness=0.6)

        # Test with emotional influence
        emotional_influence = {
            "primary_emotion": "excited",
            "emotion_intensity": 0.8,
            "dialogue_modifiers": {
                "tone": "enthusiastic"
            }
        }

        prompt = ai_manager._build_dialogue_prompt(
            context=context,
            personality=personality,
            memories=[],
            emotional_influence=emotional_influence
        )

        # Verify emotional context is included
        assert "Current Emotional State" in prompt
        assert "feeling excited" in prompt
        assert "intensity: 0.8" in prompt
        assert "enthusiastic manner" in prompt

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_dialogue_prompt_gossip_context(
        self,
        ai_manager: AIManager,
        sample_npc: Any,
        sample_player: Any
    ):
        """Test that gossip context is properly integrated into prompts."""
        context = NPCInteractionContext(
            player_id=sample_player.id,
            interaction_type="dialogue",
            relationship_level=0.6,
            time_of_day="afternoon"
        )

        personality = PersonalityTraits(curiosity=0.7)

        # Test with gossip context
        gossip_context = {
            "gossip_items": [
                MagicMock(
                    content="The player helped someone find their lost pet",
                    importance=0.8,
                    reliability=0.9,
                    timestamp=datetime.utcnow() - timedelta(hours=6)
                ),
                MagicMock(
                    content="The player was seen training late at night",
                    importance=0.6,
                    reliability=0.7,
                    timestamp=datetime.utcnow() - timedelta(days=1)
                )
            ],
            "reputation_summary": {
                "helpfulness": 0.8,
                "trainer_skill": 0.6,
                "trustworthiness": 0.7,
                "popularity": 0.5
            }
        }

        prompt = ai_manager._build_dialogue_prompt(
            context=context,
            personality=personality,
            memories=[],
            gossip_context=gossip_context
        )

        # Verify gossip integration
        assert "What You've Heard About This Player" in prompt
        assert "helpful person" in prompt  # High helpfulness reputation
        assert "skilled trainer" in prompt  # High trainer skill
        assert "trustworthy" in prompt  # High trustworthiness

        # Verify specific gossip items
        assert "helped someone find their lost pet" in prompt
        assert "reliable source" in prompt  # High reliability gossip

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_fallback_dialogue_generation(
        self,
        ai_manager: AIManager,
        sample_npc: Any,
        sample_player: Any
    ):
        """Test fallback dialogue generation when AI systems fail."""
        context = NPCInteractionContext(
            player_id=sample_player.id,
            interaction_type="battle",
            relationship_level=0.4,
            time_of_day="noon"
        )

        personality = PersonalityTraits(
            friendliness=0.8,
            verbosity=0.9,
            battle_enthusiasm=0.7
        )

        # Execute fallback dialogue
        response = await ai_manager._generate_fallback_dialogue(context, personality)

        # Verify fallback response structure
        assert isinstance(response, DialogueResponse)
        assert len(response.text) > 0
        assert response.emotion in ["happy", "neutral", "excited"]
        assert isinstance(response.relationship_change, float)

        # Verify battle-appropriate responses
        battle_keywords = ["battle", "fight", "strong", "ready", "training", "monsters"]
        assert any(keyword in response.text.lower() for keyword in battle_keywords)

        # Verify personality influence (high verbosity should add extra content)
        if personality.verbosity > 0.7:
            assert "How has your journey been going?" in response.text

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_dialogue_validation_integration(
        self,
        ai_manager: AIManager,
        sample_npc: Any,
        sample_player: Any
    ):
        """Test that dialogue validation is properly integrated."""
        context = NPCInteractionContext(
            player_id=sample_player.id,
            interaction_type="greeting",
            relationship_level=0.5,
            time_of_day="morning"
        )

        personality = PersonalityTraits(friendliness=0.6)

        # Mock validation result - critical failure
        with patch('app.ai.ai_manager.dialogue_validator') as mock_validator:
            from app.ai.validation import ValidationResult, ValidationSeverity

            mock_validator.validate_dialogue.return_value = ValidationResult(
                is_valid=False,
                score=0.2,
                severity=ValidationSeverity.CRITICAL,
                issues=["Contains inappropriate content", "Breaks character consistency"],
                suggested_fixes=["Remove inappropriate language", "Align with personality"]
            )

            # Mock Claude response that would fail validation
            with patch.object(ai_manager, '_generate_claude_dialogue') as mock_claude:
                mock_claude.return_value = DialogueResponse(
                    text="This is inappropriate content that breaks validation",
                    emotion="angry"
                )

                with patch.object(ai_manager.cost_tracker, 'can_make_request', return_value=True):
                    response = await ai_manager.generate_dialogue(
                        npc_id=sample_npc.id,
                        context=context,
                        personality=personality,
                        memories=[]
                    )

                    # Should fallback due to critical validation failure
                    assert response.text != "This is inappropriate content that breaks validation"
                    assert response.emotion != "angry"

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_cache_key_generation_consistency(
        self,
        ai_manager: AIManager,
        sample_npc: Any,
        sample_player: Any
    ):
        """Test that cache keys are generated consistently for identical contexts."""
        context1 = NPCInteractionContext(
            player_id=sample_player.id,
            interaction_type="greeting",
            relationship_level=0.5,
            time_of_day="morning"
        )

        context2 = NPCInteractionContext(
            player_id=sample_player.id,
            interaction_type="greeting",
            relationship_level=0.5,
            time_of_day="morning"
        )

        memories = []

        # Generate cache keys
        key1 = ai_manager._get_dialogue_cache_key(sample_npc.id, context1, memories)
        key2 = ai_manager._get_dialogue_cache_key(sample_npc.id, context2, memories)

        # Should be identical for identical contexts
        assert key1 == key2

        # Should be different for different contexts
        context3 = NPCInteractionContext(
            player_id=sample_player.id,
            interaction_type="battle",  # Different interaction type
            relationship_level=0.5,
            time_of_day="morning"
        )

        key3 = ai_manager._get_dialogue_cache_key(sample_npc.id, context3, memories)
        assert key1 != key3

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_dialogue_generation_error_handling(
        self,
        ai_manager: AIManager,
        sample_npc: Any,
        sample_player: Any
    ):
        """Test graceful error handling during dialogue generation."""
        context = NPCInteractionContext(
            player_id=sample_player.id,
            interaction_type="greeting",
            relationship_level=0.5,
            time_of_day="morning"
        )

        personality = PersonalityTraits(friendliness=0.6)

        # Test Claude API error
        with patch.object(ai_manager.cost_tracker, 'can_make_request', return_value=True):
            with patch.object(ai_manager, '_generate_claude_dialogue', side_effect=Exception("API Error")):
                response = await ai_manager.generate_dialogue(
                    npc_id=sample_npc.id,
                    context=context,
                    personality=personality,
                    memories=[]
                )

                # Should fallback to scripted dialogue
                assert response is not None
                assert isinstance(response, DialogueResponse)
                assert len(response.text) > 0

    @pytest.mark.unit
    @pytest.mark.ai
    async def test_memory_storage_from_dialogue(
        self,
        ai_manager: AIManager,
        sample_npc: Any,
        sample_player: Any
    ):
        """Test that dialogue interactions are stored as memories."""
        context = NPCInteractionContext(
            player_id=sample_player.id,
            interaction_type="quest",
            relationship_level=0.6,
            time_of_day="afternoon",
            recent_achievements=["Completed first quest"]
        )

        response = DialogueResponse(
            text="Great job completing that quest! You're becoming quite the adventurer.",
            emotion="proud",
            relationship_change=0.2
        )

        with patch('app.ai.ai_manager.qdrant_client') as mock_qdrant:
            with patch.object(ai_manager.embedding_model, 'encode', return_value=[0.1] * 384):
                await ai_manager._store_interaction_memory(sample_npc.id, context, response)

                # Verify memory was stored
                mock_qdrant.upsert.assert_called_once()
                point = mock_qdrant.upsert.call_args[1]["points"][0]

                # Verify memory content includes dialogue context
                memory_content = point.payload["content"]
                assert "quest" in memory_content
                assert "Completed first quest" in memory_content
                assert "Great job completing" in memory_content

                # Verify importance calculation
                importance = point.payload["importance"]
                assert importance > 0.6  # Should be high due to achievement + positive relationship change