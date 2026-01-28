"""
Unit Tests for AI Personality System
Austin Kidwell | Intellegix | AI-Powered Tuxemon Game

Tests personality trait calculations, dialogue prompt generation, and
personality consistency across NPC interactions.
"""

import pytest
from typing import Dict, Any
from uuid import uuid4

from app.game.models import PersonalityTraits
from app.ai.ai_manager import AIManager


class TestPersonalitySystem:
    """Test suite for AI personality trait management and application."""

    @pytest.mark.unit
    @pytest.mark.ai
    def test_personality_traits_initialization_defaults(self):
        """Test that personality traits initialize with proper defaults."""
        # Test default initialization
        personality = PersonalityTraits()

        # Verify all traits default to 0.5 (neutral)
        assert personality.openness == 0.5
        assert personality.conscientiousness == 0.5
        assert personality.extraversion == 0.5
        assert personality.agreeableness == 0.5
        assert personality.neuroticism == 0.5
        assert personality.curiosity == 0.5
        assert personality.verbosity == 0.5
        assert personality.humor == 0.5
        assert personality.friendliness == 0.5
        assert personality.battle_enthusiasm == 0.5

    @pytest.mark.unit
    @pytest.mark.ai
    def test_personality_traits_custom_values(self):
        """Test personality traits with custom values."""
        # Test custom initialization
        personality = PersonalityTraits(
            openness=0.8,
            conscientiousness=0.3,
            extraversion=0.9,
            agreeableness=0.7,
            neuroticism=0.2,
            curiosity=0.85,
            verbosity=0.6,
            humor=0.4,
            friendliness=0.95,
            battle_enthusiasm=0.1
        )

        # Verify custom values
        assert personality.openness == 0.8
        assert personality.conscientiousness == 0.3
        assert personality.extraversion == 0.9
        assert personality.agreeableness == 0.7
        assert personality.neuroticism == 0.2
        assert personality.curiosity == 0.85
        assert personality.verbosity == 0.6
        assert personality.humor == 0.4
        assert personality.friendliness == 0.95
        assert personality.battle_enthusiasm == 0.1

    @pytest.mark.unit
    @pytest.mark.ai
    def test_personality_traits_validation_bounds(self):
        """Test that personality traits are properly bounded between 0.0 and 1.0."""
        # Test extreme values
        personality = PersonalityTraits(
            openness=1.0,
            conscientiousness=0.0,
            extraversion=0.5,
            agreeableness=1.0,
            neuroticism=0.0
        )

        assert 0.0 <= personality.openness <= 1.0
        assert 0.0 <= personality.conscientiousness <= 1.0
        assert 0.0 <= personality.extraversion <= 1.0
        assert 0.0 <= personality.agreeableness <= 1.0
        assert 0.0 <= personality.neuroticism <= 1.0

    @pytest.mark.unit
    @pytest.mark.ai
    def test_personality_prompt_generation_high_extraversion(self):
        """Test personality prompt generation for high extraversion characters."""
        ai_manager = AIManager()

        personality = PersonalityTraits(
            extraversion=0.8,
            agreeableness=0.6,
            humor=0.3,
            verbosity=0.4
        )

        prompt_text = ai_manager._format_personality(personality)

        # Verify high extraversion traits
        assert "outgoing and social" in prompt_text
        assert "kind and cooperative" in prompt_text
        assert "This character is" in prompt_text

        # Should not include humor traits (below threshold)
        assert "jokes" not in prompt_text

    @pytest.mark.unit
    @pytest.mark.ai
    def test_personality_prompt_generation_low_extraversion(self):
        """Test personality prompt generation for low extraversion characters."""
        ai_manager = AIManager()

        personality = PersonalityTraits(
            extraversion=0.2,
            agreeableness=0.2,
            humor=0.1,
            verbosity=0.2,
            friendliness=0.1
        )

        prompt_text = ai_manager._format_personality(personality)

        # Verify low extraversion traits
        assert "introverted and reserved" in prompt_text
        assert "competitive and direct" in prompt_text
        assert "concise and brief in speech" in prompt_text
        assert "somewhat distant or reserved" in prompt_text

    @pytest.mark.unit
    @pytest.mark.ai
    def test_personality_prompt_generation_high_curiosity(self):
        """Test personality prompt generation for highly curious characters."""
        ai_manager = AIManager()

        personality = PersonalityTraits(
            curiosity=0.9,
            verbosity=0.8,
            humor=0.8
        )

        prompt_text = ai_manager._format_personality(personality)

        # Verify curiosity and related traits
        assert "very curious and asks many questions" in prompt_text
        assert "talkative and gives detailed responses" in prompt_text
        assert "enjoys jokes and lighthearted conversation" in prompt_text

    @pytest.mark.unit
    @pytest.mark.ai
    def test_personality_prompt_generation_battle_enthusiast(self):
        """Test personality prompt generation for battle-loving characters."""
        ai_manager = AIManager()

        personality = PersonalityTraits(
            competitiveness=0.9,
            battle_enthusiasm=0.8,
            friendliness=0.8,
            extraversion=0.7
        )

        prompt_text = ai_manager._format_personality(personality)

        # Verify battle-related traits
        assert "competitive and interested in battles" in prompt_text
        assert "outgoing and social" in prompt_text
        assert "warm and welcoming" in prompt_text

    @pytest.mark.unit
    @pytest.mark.ai
    def test_personality_prompt_generation_neutral_personality(self):
        """Test personality prompt generation for balanced/neutral personality."""
        ai_manager = AIManager()

        # All traits at neutral levels (0.4-0.6 range)
        personality = PersonalityTraits(
            openness=0.5,
            extraversion=0.5,
            agreeableness=0.5,
            curiosity=0.5,
            verbosity=0.5,
            humor=0.5,
            friendliness=0.5,
            competitiveness=0.5
        )

        prompt_text = ai_manager._format_personality(personality)

        # Should result in minimal description due to neutral traits
        # (No traits exceed the 0.7 or fall below 0.3 thresholds)
        assert "This character is ." in prompt_text or "balanced personality" in prompt_text

    @pytest.mark.unit
    @pytest.mark.ai
    def test_personality_trait_combinations(self):
        """Test various personality trait combinations for realistic characters."""
        ai_manager = AIManager()

        # Shy but helpful character
        shy_helper = PersonalityTraits(
            extraversion=0.2,  # Introverted
            agreeableness=0.9,  # Very cooperative
            friendliness=0.8,   # Warm despite being shy
            verbosity=0.3,      # Brief speech
            curiosity=0.7       # Interested in others
        )

        prompt = ai_manager._format_personality(shy_helper)
        assert "introverted and reserved" in prompt
        assert "kind and cooperative" in prompt
        assert "warm and welcoming" in prompt
        assert "concise and brief in speech" in prompt

        # Outgoing comedian character
        comedian = PersonalityTraits(
            extraversion=0.9,   # Very outgoing
            humor=0.95,         # Loves jokes
            verbosity=0.9,      # Very talkative
            friendliness=0.8,   # Very friendly
            curiosity=0.7       # Asks questions
        )

        prompt = ai_manager._format_personality(comedian)
        assert "outgoing and social" in prompt
        assert "enjoys jokes and lighthearted conversation" in prompt
        assert "talkative and gives detailed responses" in prompt
        assert "very curious and asks many questions" in prompt
        assert "warm and welcoming" in prompt

        # Serious trainer character
        serious_trainer = PersonalityTraits(
            competitiveness=0.95,   # Highly competitive
            conscientiousness=0.8,  # Very organized
            humor=0.1,              # Serious, no jokes
            verbosity=0.4,          # Concise
            battle_enthusiasm=0.9   # Loves battles
        )

        prompt = ai_manager._format_personality(serious_trainer)
        assert "competitive and interested in battles" in prompt
        # Should not include humor traits
        assert "jokes" not in prompt

    @pytest.mark.unit
    @pytest.mark.ai
    def test_personality_consistency_across_calls(self):
        """Test that personality prompt generation is consistent across multiple calls."""
        ai_manager = AIManager()

        personality = PersonalityTraits(
            extraversion=0.8,
            agreeableness=0.7,
            humor=0.6,
            verbosity=0.9,
            curiosity=0.8
        )

        # Generate prompt multiple times
        prompt1 = ai_manager._format_personality(personality)
        prompt2 = ai_manager._format_personality(personality)
        prompt3 = ai_manager._format_personality(personality)

        # Should be identical
        assert prompt1 == prompt2 == prompt3

    @pytest.mark.unit
    @pytest.mark.ai
    def test_personality_model_serialization(self):
        """Test that personality traits can be properly serialized and deserialized."""
        original = PersonalityTraits(
            openness=0.75,
            conscientiousness=0.65,
            extraversion=0.85,
            agreeableness=0.45,
            neuroticism=0.35,
            curiosity=0.9,
            verbosity=0.7,
            humor=0.8,
            friendliness=0.95,
            battle_enthusiasm=0.6
        )

        # Test model_dump (serialization)
        personality_dict = original.model_dump()

        expected_dict = {
            'openness': 0.75,
            'conscientiousness': 0.65,
            'extraversion': 0.85,
            'agreeableness': 0.45,
            'neuroticism': 0.35,
            'curiosity': 0.9,
            'verbosity': 0.7,
            'humor': 0.8,
            'friendliness': 0.95,
            'battle_enthusiasm': 0.6
        }

        assert personality_dict == expected_dict

        # Test reconstruction from dict
        reconstructed = PersonalityTraits(**personality_dict)

        assert reconstructed.openness == original.openness
        assert reconstructed.conscientiousness == original.conscientiousness
        assert reconstructed.extraversion == original.extraversion
        assert reconstructed.agreeableness == original.agreeableness
        assert reconstructed.neuroticism == original.neuroticism
        assert reconstructed.curiosity == original.curiosity
        assert reconstructed.verbosity == original.verbosity
        assert reconstructed.humor == original.humor
        assert reconstructed.friendliness == original.friendliness
        assert reconstructed.battle_enthusiasm == original.battle_enthusiasm

    @pytest.mark.unit
    @pytest.mark.ai
    def test_personality_extreme_combinations(self):
        """Test personality combinations at extreme values."""
        ai_manager = AIManager()

        # Maximum extraversion, minimum agreeableness
        extreme_combo1 = PersonalityTraits(
            extraversion=1.0,
            agreeableness=0.0,
            competitiveness=1.0,
            humor=0.0
        )

        prompt1 = ai_manager._format_personality(extreme_combo1)
        assert "outgoing and social" in prompt1
        assert "competitive and direct" in prompt1
        assert "competitive and interested in battles" in prompt1

        # Maximum verbosity, minimum curiosity
        extreme_combo2 = PersonalityTraits(
            verbosity=1.0,
            curiosity=0.0,
            friendliness=1.0,
            humor=1.0
        )

        prompt2 = ai_manager._format_personality(extreme_combo2)
        assert "talkative and gives detailed responses" in prompt2
        assert "not very inquisitive" in prompt2
        assert "warm and welcoming" in prompt2
        assert "enjoys jokes and lighthearted conversation" in prompt2

    @pytest.mark.unit
    @pytest.mark.ai
    def test_personality_trait_thresholds(self):
        """Test that personality trait thresholds work correctly."""
        ai_manager = AIManager()

        # Test exactly at thresholds
        threshold_high = PersonalityTraits(
            extraversion=0.7,  # Exactly at high threshold
            agreeableness=0.3,  # Exactly at low threshold
            curiosity=0.7,     # Exactly at high threshold
            verbosity=0.3      # Exactly at low threshold
        )

        prompt = ai_manager._format_personality(threshold_high)

        # At threshold should trigger the trait description
        assert "outgoing and social" in prompt
        assert "competitive and direct" in prompt
        assert "very curious and asks many questions" in prompt
        assert "concise and brief in speech" in prompt

        # Test just below thresholds
        threshold_below = PersonalityTraits(
            extraversion=0.69,  # Just below high threshold
            agreeableness=0.31,  # Just above low threshold
            curiosity=0.69,     # Just below high threshold
            verbosity=0.31      # Just above low threshold
        )

        prompt2 = ai_manager._format_personality(threshold_below)

        # Just below threshold should not trigger the trait description
        assert "outgoing and social" not in prompt2
        assert "competitive and direct" not in prompt2
        assert "very curious and asks many questions" not in prompt2
        assert "concise and brief in speech" not in prompt2

    @pytest.mark.unit
    @pytest.mark.ai
    def test_personality_empty_traits_handling(self):
        """Test handling when no traits exceed thresholds."""
        ai_manager = AIManager()

        # All traits in middle range (0.4-0.6)
        neutral_personality = PersonalityTraits(
            openness=0.45,
            conscientiousness=0.55,
            extraversion=0.5,
            agreeableness=0.45,
            neuroticism=0.5,
            curiosity=0.6,
            verbosity=0.4,
            humor=0.55,
            friendliness=0.5,
            battle_enthusiasm=0.45,
            competitiveness=0.5
        )

        prompt = ai_manager._format_personality(neutral_personality)

        # Should still generate a valid prompt
        assert "This character is" in prompt
        # With no extreme traits, should result in minimal description
        assert len(prompt.split(", ")) <= 2  # Minimal trait descriptions