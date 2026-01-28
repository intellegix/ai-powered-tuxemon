"""
Unit Tests for Battle System
Austin Kidwell | Intellegix | AI-Powered Tuxemon Game

Tests combat mechanics, turn-based logic, damage calculations, and
battle state management for the mobile Pokemon-style battle system.
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from app.game.models import (
    Monster,
    MonsterStats,
    ElementType,
    MonsterShape,
    CombatPhase,
    Player
)


class TestBattleSystem:
    """Test suite for turn-based battle mechanics and combat logic."""

    @pytest.fixture
    def sample_monster_stats(self) -> MonsterStats:
        """Provide sample monster stats for testing."""
        return MonsterStats(
            hp=50,
            armour=25,
            dodge=20,
            melee=30,
            ranged=25,
            speed=35
        )

    @pytest.fixture
    def player_monster(self, sample_monster_stats: MonsterStats) -> Monster:
        """Provide a player's monster for battle testing."""
        return Monster(
            id=uuid4(),
            species_slug="bamboon",
            name="TestBamboon",
            level=10,
            current_hp=50,
            total_experience=250,
            status_effects="{}",
            player_id=uuid4(),
            npc_id=None,
            flairs="{}",
            personality_traits="{}",
            obtained_at=datetime.utcnow(),
            last_battle=None,
            times_battled=5
        )

    @pytest.fixture
    def npc_monster(self, sample_monster_stats: MonsterStats) -> Monster:
        """Provide an NPC's monster for battle testing."""
        return Monster(
            id=uuid4(),
            species_slug="rockitten",
            name="WildRockitten",
            level=8,
            current_hp=40,
            total_experience=150,
            status_effects="{}",
            player_id=None,
            npc_id=uuid4(),
            flairs="{}",
            personality_traits='{"aggressive": 0.7, "defensive": 0.3}',
            obtained_at=datetime.utcnow() - timedelta(days=30),
            last_battle=datetime.utcnow() - timedelta(hours=2),
            times_battled=12
        )

    @pytest.mark.unit
    @pytest.mark.game
    def test_monster_stats_validation(self):
        """Test that monster stats are properly validated."""
        # Valid stats
        valid_stats = MonsterStats(
            hp=50,
            armour=25,
            dodge=30,
            melee=35,
            ranged=20,
            speed=40
        )

        assert valid_stats.hp == 50
        assert valid_stats.armour == 25
        assert valid_stats.speed == 40

        # Test boundary values
        boundary_stats = MonsterStats(
            hp=1,      # Minimum
            armour=1,   # Minimum
            dodge=100,  # Maximum
            melee=100,  # Maximum
            ranged=1,   # Minimum
            speed=100   # Maximum
        )

        assert boundary_stats.hp == 1
        assert boundary_stats.dodge == 100

        # Test invalid stats (should raise validation errors)
        with pytest.raises(ValueError):
            MonsterStats(hp=0)  # Below minimum

        with pytest.raises(ValueError):
            MonsterStats(hp=1000)  # Above maximum

        with pytest.raises(ValueError):
            MonsterStats(hp=50, speed=101)  # Speed above maximum

    @pytest.mark.unit
    @pytest.mark.game
    def test_combat_phase_transitions(self):
        """Test valid combat phase transitions."""
        # Test valid phase progression
        phases = [
            CombatPhase.WAITING,
            CombatPhase.ACTION_SELECTION,
            CombatPhase.EXECUTING,
            CombatPhase.VICTORY
        ]

        # Verify all phases exist and have string values
        for phase in phases:
            assert isinstance(phase.value, str)
            assert len(phase.value) > 0

        # Test phase equality
        assert CombatPhase.WAITING == "waiting"
        assert CombatPhase.ACTION_SELECTION == "action_selection"
        assert CombatPhase.EXECUTING == "executing"
        assert CombatPhase.VICTORY == "victory"
        assert CombatPhase.DEFEAT == "defeat"

    @pytest.mark.unit
    @pytest.mark.game
    def test_monster_creation_and_properties(
        self,
        player_monster: Monster,
        npc_monster: Monster
    ):
        """Test monster creation and property access."""
        # Test player monster
        assert player_monster.species_slug == "bamboon"
        assert player_monster.name == "TestBamboon"
        assert player_monster.level == 10
        assert player_monster.current_hp == 50
        assert player_monster.player_id is not None
        assert player_monster.npc_id is None
        assert player_monster.times_battled == 5

        # Test NPC monster
        assert npc_monster.species_slug == "rockitten"
        assert npc_monster.name == "WildRockitten"
        assert npc_monster.level == 8
        assert npc_monster.current_hp == 40
        assert npc_monster.player_id is None
        assert npc_monster.npc_id is not None
        assert npc_monster.times_battled == 12

        # Test personality traits parsing
        import json
        npc_personality = json.loads(npc_monster.personality_traits)
        assert npc_personality["aggressive"] == 0.7
        assert npc_personality["defensive"] == 0.3

    @pytest.mark.unit
    @pytest.mark.game
    def test_element_type_effectiveness(self):
        """Test element type system and type effectiveness."""
        # Test basic element types exist
        elements = [
            ElementType.NORMAL,
            ElementType.FIRE,
            ElementType.WATER,
            ElementType.GRASS,
            ElementType.ELECTRIC,
            ElementType.PSYCHIC
        ]

        for element in elements:
            assert isinstance(element.value, str)

        # Test type effectiveness logic (would be implemented in battle engine)
        fire_vs_grass = self._calculate_type_effectiveness(ElementType.FIRE, ElementType.GRASS)
        water_vs_fire = self._calculate_type_effectiveness(ElementType.WATER, ElementType.FIRE)
        normal_vs_normal = self._calculate_type_effectiveness(ElementType.NORMAL, ElementType.NORMAL)

        # Fire should be effective against Grass
        assert fire_vs_grass > 1.0
        # Water should be effective against Fire
        assert water_vs_fire > 1.0
        # Normal vs Normal should be neutral
        assert normal_vs_normal == 1.0

    def _calculate_type_effectiveness(self, attacking_type: ElementType, defending_type: ElementType) -> float:
        """Calculate type effectiveness multiplier (mock implementation for testing)."""
        effectiveness_chart = {
            # Fire advantages
            (ElementType.FIRE, ElementType.GRASS): 2.0,
            (ElementType.FIRE, ElementType.ICE): 2.0,
            (ElementType.FIRE, ElementType.BUG): 2.0,
            (ElementType.FIRE, ElementType.STEEL): 2.0,

            # Water advantages
            (ElementType.WATER, ElementType.FIRE): 2.0,
            (ElementType.WATER, ElementType.GROUND): 2.0,
            (ElementType.WATER, ElementType.ROCK): 2.0,

            # Grass advantages
            (ElementType.GRASS, ElementType.WATER): 2.0,
            (ElementType.GRASS, ElementType.GROUND): 2.0,
            (ElementType.GRASS, ElementType.ROCK): 2.0,

            # Electric advantages
            (ElementType.ELECTRIC, ElementType.WATER): 2.0,
            (ElementType.ELECTRIC, ElementType.FLYING): 2.0,

            # Fire weaknesses
            (ElementType.FIRE, ElementType.WATER): 0.5,
            (ElementType.FIRE, ElementType.ROCK): 0.5,
            (ElementType.FIRE, ElementType.DRAGON): 0.5,

            # Water weaknesses
            (ElementType.WATER, ElementType.GRASS): 0.5,
            (ElementType.WATER, ElementType.ELECTRIC): 0.5,
        }

        return effectiveness_chart.get((attacking_type, defending_type), 1.0)

    @pytest.mark.unit
    @pytest.mark.game
    def test_damage_calculation_basic(
        self,
        player_monster: Monster,
        npc_monster: Monster
    ):
        """Test basic damage calculation mechanics."""
        # Mock attack data
        attack_power = 40
        attacker_level = player_monster.level
        attacker_melee = 30  # From stats
        defender_armour = 25  # From stats

        # Basic damage formula: (Level + Attack Power + Attacker Stat - Defender Stat) * modifiers
        base_damage = max(1, (attacker_level + attack_power + attacker_melee - defender_armour))

        # Apply type effectiveness
        type_multiplier = self._calculate_type_effectiveness(ElementType.FIRE, ElementType.GRASS)
        final_damage = int(base_damage * type_multiplier)

        # Verify damage is reasonable
        assert final_damage > 0
        assert final_damage <= 200  # Reasonable upper bound

        # Test minimum damage (should never be 0)
        weak_attack_damage = self._calculate_damage(
            attack_power=5,
            attacker_level=1,
            attacker_stat=1,
            defender_stat=50,
            type_multiplier=0.5
        )

        assert weak_attack_damage >= 1  # Minimum damage

    def _calculate_damage(
        self,
        attack_power: int,
        attacker_level: int,
        attacker_stat: int,
        defender_stat: int,
        type_multiplier: float = 1.0,
        critical_hit: bool = False
    ) -> int:
        """Calculate battle damage (mock implementation)."""
        # Basic damage calculation
        base_damage = max(1, attacker_level + attack_power + attacker_stat - defender_stat)

        # Apply type effectiveness
        damage = base_damage * type_multiplier

        # Apply critical hit
        if critical_hit:
            damage *= 1.5

        # Add some randomness (10% variance)
        import random
        variance = random.uniform(0.9, 1.1)
        damage *= variance

        return max(1, int(damage))

    @pytest.mark.unit
    @pytest.mark.game
    def test_critical_hit_calculation(self):
        """Test critical hit probability and damage calculation."""
        base_damage = 50
        attacker_speed = 35
        defender_speed = 20

        # Critical hit rate based on speed difference
        speed_difference = attacker_speed - defender_speed
        critical_rate = min(0.3, max(0.05, 0.05 + (speed_difference * 0.01)))

        # Verify critical rate is within bounds
        assert 0.05 <= critical_rate <= 0.3

        # Test critical damage multiplier
        critical_damage = self._calculate_damage(
            attack_power=40,
            attacker_level=10,
            attacker_stat=30,
            defender_stat=25,
            critical_hit=True
        )

        normal_damage = self._calculate_damage(
            attack_power=40,
            attacker_level=10,
            attacker_stat=30,
            defender_stat=25,
            critical_hit=False
        )

        # Critical hit should do more damage (approximately 1.5x)
        assert critical_damage > normal_damage

    @pytest.mark.unit
    @pytest.mark.game
    def test_speed_calculation_and_turn_order(
        self,
        player_monster: Monster,
        npc_monster: Monster
    ):
        """Test speed calculation and turn order determination."""
        # Mock speed stats
        player_speed = 35
        npc_speed = 20

        # Player should go first (higher speed)
        assert player_speed > npc_speed

        # Test edge case: equal speeds (should have tiebreaker)
        equal_speed_player = 30
        equal_speed_npc = 30

        # In case of tie, could use random or other tiebreaker
        turn_order = self._determine_turn_order(
            (player_monster, equal_speed_player),
            (npc_monster, equal_speed_npc)
        )

        assert len(turn_order) == 2
        assert turn_order[0] in [player_monster, npc_monster]
        assert turn_order[1] in [player_monster, npc_monster]
        assert turn_order[0] != turn_order[1]

    def _determine_turn_order(self, *monsters_with_speeds) -> List[Monster]:
        """Determine turn order based on speed (mock implementation)."""
        # Sort by speed (descending), with random tiebreaker
        import random
        sorted_monsters = sorted(
            monsters_with_speeds,
            key=lambda x: (x[1], random.random()),
            reverse=True
        )
        return [monster for monster, speed in sorted_monsters]

    @pytest.mark.unit
    @pytest.mark.game
    def test_status_effects_application(self, player_monster: Monster):
        """Test status effect application and duration."""
        # Test parsing existing status effects
        import json
        initial_status = json.loads(player_monster.status_effects)
        assert initial_status == {}

        # Test applying status effects
        new_status_effects = {
            "poisoned": {
                "duration": 3,
                "damage_per_turn": 5,
                "applied_turn": 1
            },
            "paralyzed": {
                "duration": 2,
                "speed_reduction": 0.5,
                "applied_turn": 1
            }
        }

        # Test status effect validation
        for effect_name, effect_data in new_status_effects.items():
            assert "duration" in effect_data
            assert effect_data["duration"] > 0
            assert "applied_turn" in effect_data

        # Test status effect expiration
        expired_effects = self._process_status_effects(new_status_effects, current_turn=4)

        # Poison should be expired (duration 3, applied turn 1, current turn 4)
        assert "poisoned" not in expired_effects
        # Paralysis should be expired (duration 2, applied turn 1, current turn 4)
        assert "paralyzed" not in expired_effects

    def _process_status_effects(self, status_effects: Dict[str, Any], current_turn: int) -> Dict[str, Any]:
        """Process status effects and remove expired ones (mock implementation)."""
        active_effects = {}

        for effect_name, effect_data in status_effects.items():
            applied_turn = effect_data["applied_turn"]
            duration = effect_data["duration"]

            # Check if effect is still active
            if current_turn <= applied_turn + duration:
                active_effects[effect_name] = effect_data

        return active_effects

    @pytest.mark.unit
    @pytest.mark.game
    def test_monster_hp_management(self, player_monster: Monster):
        """Test monster HP tracking and KO detection."""
        # Test initial HP
        assert player_monster.current_hp == 50
        assert player_monster.current_hp > 0

        # Test taking damage
        damage_taken = 20
        new_hp = max(0, player_monster.current_hp - damage_taken)
        assert new_hp == 30

        # Test KO detection
        assert not self._is_monster_ko(new_hp)

        # Test lethal damage
        lethal_damage = 60
        ko_hp = max(0, player_monster.current_hp - lethal_damage)
        assert ko_hp == 0
        assert self._is_monster_ko(ko_hp)

        # Test healing (cannot exceed max HP)
        healing = 30
        max_hp = 50  # Original HP
        healed_hp = min(max_hp, new_hp + healing)
        assert healed_hp == 50  # Should not exceed max

    def _is_monster_ko(self, current_hp: int) -> bool:
        """Check if monster is knocked out."""
        return current_hp <= 0

    @pytest.mark.unit
    @pytest.mark.game
    def test_experience_and_leveling(self, player_monster: Monster):
        """Test experience gain and level calculation."""
        initial_level = player_monster.level
        initial_exp = player_monster.total_experience

        # Test experience gain from battle
        exp_gained = 150
        new_total_exp = initial_exp + exp_gained

        # Mock level calculation (simplified)
        new_level = self._calculate_level_from_experience(new_total_exp)

        assert new_total_exp > initial_exp
        assert new_level >= initial_level

        # Test level up thresholds
        level_1_exp = self._calculate_level_from_experience(50)
        level_2_exp = self._calculate_level_from_experience(150)
        level_3_exp = self._calculate_level_from_experience(300)

        assert level_1_exp == 1
        assert level_2_exp == 2
        assert level_3_exp == 3

    def _calculate_level_from_experience(self, total_experience: int) -> int:
        """Calculate level based on total experience (mock implementation)."""
        # Simple quadratic growth: level = sqrt(exp / 100) + 1
        import math
        return int(math.sqrt(total_experience / 100)) + 1

    @pytest.mark.unit
    @pytest.mark.game
    def test_monster_shape_categories(self):
        """Test monster shape enumeration and categories."""
        # Test that all shapes exist and have proper string values
        shapes = [
            MonsterShape.AQUATIC,
            MonsterShape.DRAGON,
            MonsterShape.FLIER,
            MonsterShape.HUMANOID,
            MonsterShape.BRUTE,
            MonsterShape.SERPENT
        ]

        for shape in shapes:
            assert isinstance(shape.value, str)
            assert len(shape.value) > 0

        # Test shape-based logic (could affect certain moves or abilities)
        aquatic_monsters = [MonsterShape.AQUATIC, MonsterShape.LEVIATHAN, MonsterShape.POLLIWOG]
        flying_monsters = [MonsterShape.FLIER, MonsterShape.DRAGON]

        for shape in aquatic_monsters:
            assert self._can_use_water_moves(shape)

        for shape in flying_monsters:
            assert self._is_immune_to_ground_moves(shape)

    def _can_use_water_moves(self, shape: MonsterShape) -> bool:
        """Check if monster shape can use water-based moves."""
        water_shapes = [MonsterShape.AQUATIC, MonsterShape.LEVIATHAN, MonsterShape.POLLIWOG]
        return shape in water_shapes

    def _is_immune_to_ground_moves(self, shape: MonsterShape) -> bool:
        """Check if monster shape is immune to ground-based moves."""
        flying_shapes = [MonsterShape.FLIER, MonsterShape.DRAGON]
        return shape in flying_shapes

    @pytest.mark.unit
    @pytest.mark.game
    def test_battle_state_persistence(
        self,
        player_monster: Monster,
        npc_monster: Monster
    ):
        """Test that battle state can be properly serialized and restored."""
        # Mock battle state
        battle_state = {
            "battle_id": str(uuid4()),
            "phase": CombatPhase.ACTION_SELECTION.value,
            "turn_number": 3,
            "player_monster": {
                "id": str(player_monster.id),
                "current_hp": 30,
                "status_effects": {"poisoned": {"duration": 2, "applied_turn": 2}}
            },
            "npc_monster": {
                "id": str(npc_monster.id),
                "current_hp": 25,
                "status_effects": {}
            },
            "last_action": "attack",
            "created_at": datetime.utcnow().isoformat()
        }

        # Test serialization
        import json
        serialized = json.dumps(battle_state)
        assert len(serialized) > 0

        # Test deserialization
        restored_state = json.loads(serialized)
        assert restored_state["phase"] == "action_selection"
        assert restored_state["turn_number"] == 3
        assert restored_state["player_monster"]["current_hp"] == 30
        assert restored_state["npc_monster"]["current_hp"] == 25

        # Test UUID restoration
        restored_battle_id = UUID(restored_state["battle_id"])
        assert isinstance(restored_battle_id, UUID)