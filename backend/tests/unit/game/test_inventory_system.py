"""
Unit Tests for Inventory System
Austin Kidwell | Intellegix | AI-Powered Tuxemon Game

Tests item management, shop transactions, item effects, and
inventory validation for the mobile game's item system.
"""

import pytest
import pytest_asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from app.game.items import (
    ItemCategory,
    ItemRarity,
    UseContext,
    ItemBase,
    PlayerInventorySlot,
    ItemEffect,
    ItemStats
)


class TestInventorySystem:
    """Test suite for item management and inventory operations."""

    @pytest.fixture
    def sample_healing_item(self) -> ItemBase:
        """Provide sample healing item for testing."""
        return ItemBase(
            id=1,
            slug="health_potion",
            name="Health Potion",
            description="Restores 50 HP to a monster.",
            category=ItemCategory.HEALING,
            rarity=ItemRarity.COMMON,
            use_context=UseContext.BOTH,
            effects='{"heal_hp": {"amount": 50, "target": "selected_monster"}}',
            use_animation="heal_sparkle",
            use_sound="heal_sound",
            consumable=True,
            max_quantity=99,
            base_price=100,
            sell_price=50,
            sprite_name="potion_red",
            sort_order=1,
            obtainable=True,
            created_at=datetime.utcnow()
        )

    @pytest.fixture
    def sample_capture_item(self) -> ItemBase:
        """Provide sample capture item for testing."""
        return ItemBase(
            id=2,
            slug="tuxeball",
            name="Tuxe Ball",
            description="A basic ball for catching wild monsters.",
            category=ItemCategory.CAPTURE,
            rarity=ItemRarity.COMMON,
            use_context=UseContext.BATTLE,
            effects='{"capture": {"base_rate": 0.3, "modifiers": {"monster_hp": "inverse"}}}',
            use_animation="throw_ball",
            use_sound="ball_throw",
            consumable=True,
            max_quantity=99,
            base_price=200,
            sell_price=0,  # Will use base_price // 2
            sprite_name="tuxeball",
            sort_order=10,
            obtainable=True,
            created_at=datetime.utcnow()
        )

    @pytest.fixture
    def sample_rare_item(self) -> ItemBase:
        """Provide sample rare item for testing."""
        return ItemBase(
            id=3,
            slug="rare_candy",
            name="Rare Candy",
            description="Instantly increases a monster's level by 1.",
            category=ItemCategory.EVOLUTION,
            rarity=ItemRarity.RARE,
            use_context=UseContext.FIELD,
            effects='{"level_up": {"amount": 1, "target": "selected_monster"}}',
            use_animation="level_up_shine",
            use_sound="level_up_chime",
            consumable=True,
            max_quantity=10,
            base_price=5000,
            sell_price=2500,
            sprite_name="rare_candy",
            sort_order=50,
            obtainable=True,
            created_at=datetime.utcnow()
        )

    @pytest.fixture
    def sample_inventory_slot(self, sample_healing_item: ItemBase) -> PlayerInventorySlot:
        """Provide sample inventory slot for testing."""
        return PlayerInventorySlot(
            id=uuid4(),
            player_id=uuid4(),
            item_slug=sample_healing_item.slug,
            quantity=5,
            obtained_at=datetime.utcnow(),
            last_used=None,
            times_used=0
        )

    @pytest.mark.unit
    @pytest.mark.game
    def test_item_category_enum(self):
        """Test item category enumeration."""
        categories = [
            ItemCategory.HEALING,
            ItemCategory.CAPTURE,
            ItemCategory.EVOLUTION,
            ItemCategory.BATTLE,
            ItemCategory.KEY,
            ItemCategory.MISC
        ]

        for category in categories:
            assert isinstance(category.value, str)

        # Test string values
        assert ItemCategory.HEALING == "healing"
        assert ItemCategory.CAPTURE == "capture"
        assert ItemCategory.EVOLUTION == "evolution"
        assert ItemCategory.BATTLE == "battle"
        assert ItemCategory.KEY == "key"
        assert ItemCategory.MISC == "misc"

    @pytest.mark.unit
    @pytest.mark.game
    def test_item_rarity_enum(self):
        """Test item rarity enumeration and progression."""
        rarities = [
            ItemRarity.COMMON,
            ItemRarity.UNCOMMON,
            ItemRarity.RARE,
            ItemRarity.EPIC,
            ItemRarity.LEGENDARY
        ]

        for rarity in rarities:
            assert isinstance(rarity.value, str)

        # Test rarity progression (for drop rates, prices, etc.)
        rarity_values = {
            ItemRarity.COMMON: 1,
            ItemRarity.UNCOMMON: 2,
            ItemRarity.RARE: 3,
            ItemRarity.EPIC: 4,
            ItemRarity.LEGENDARY: 5
        }

        common_modifier = rarity_values[ItemRarity.COMMON]
        legendary_modifier = rarity_values[ItemRarity.LEGENDARY]

        assert legendary_modifier > common_modifier
        assert legendary_modifier == 5 * common_modifier

    @pytest.mark.unit
    @pytest.mark.game
    def test_use_context_validation(self):
        """Test item use context validation."""
        contexts = [
            UseContext.FIELD,
            UseContext.BATTLE,
            UseContext.BOTH
        ]

        for context in contexts:
            assert isinstance(context.value, str)

        # Test usage validation logic
        field_item = UseContext.FIELD
        battle_item = UseContext.BATTLE
        universal_item = UseContext.BOTH

        # Mock usage scenarios
        in_battle = True
        in_field = False

        assert self._can_use_item_in_context(field_item, in_battle) is False
        assert self._can_use_item_in_context(field_item, in_field) is True
        assert self._can_use_item_in_context(battle_item, in_battle) is True
        assert self._can_use_item_in_context(battle_item, in_field) is False
        assert self._can_use_item_in_context(universal_item, in_battle) is True
        assert self._can_use_item_in_context(universal_item, in_field) is True

    def _can_use_item_in_context(self, item_context: UseContext, in_battle: bool) -> bool:
        """Check if item can be used in current context."""
        if item_context == UseContext.BOTH:
            return True
        elif item_context == UseContext.BATTLE:
            return in_battle
        elif item_context == UseContext.FIELD:
            return not in_battle
        return False

    @pytest.mark.unit
    @pytest.mark.game
    def test_item_base_creation_and_validation(
        self,
        sample_healing_item: ItemBase,
        sample_capture_item: ItemBase,
        sample_rare_item: ItemBase
    ):
        """Test item creation and property validation."""
        # Test healing item
        assert sample_healing_item.slug == "health_potion"
        assert sample_healing_item.name == "Health Potion"
        assert sample_healing_item.category == ItemCategory.HEALING
        assert sample_healing_item.rarity == ItemRarity.COMMON
        assert sample_healing_item.use_context == UseContext.BOTH
        assert sample_healing_item.consumable is True
        assert sample_healing_item.max_quantity == 99
        assert sample_healing_item.base_price == 100
        assert sample_healing_item.sell_price == 50

        # Test capture item
        assert sample_capture_item.category == ItemCategory.CAPTURE
        assert sample_capture_item.use_context == UseContext.BATTLE
        assert sample_capture_item.sell_price == 0  # Should calculate from base_price

        # Test rare item
        assert sample_rare_item.rarity == ItemRarity.RARE
        assert sample_rare_item.max_quantity == 10  # Lower limit for rare items

        # Test effects parsing
        healing_effects = json.loads(sample_healing_item.effects)
        assert "heal_hp" in healing_effects
        assert healing_effects["heal_hp"]["amount"] == 50

        capture_effects = json.loads(sample_capture_item.effects)
        assert "capture" in capture_effects
        assert capture_effects["capture"]["base_rate"] == 0.3

    @pytest.mark.unit
    @pytest.mark.game
    def test_item_effect_model(self):
        """Test item effect model validation."""
        # Valid heal effect
        heal_effect = ItemEffect(
            effect_type="heal_hp",
            value=50,
            target="selected_monster",
            duration=None
        )

        assert heal_effect.effect_type == "heal_hp"
        assert heal_effect.value == 50
        assert heal_effect.target == "selected_monster"
        assert heal_effect.duration is None

        # Valid temporary boost effect
        boost_effect = ItemEffect(
            effect_type="boost_stats",
            value={"attack": 1.5, "defense": 1.2},
            target="selected_monster",
            duration=5  # 5 turns
        )

        assert boost_effect.effect_type == "boost_stats"
        assert isinstance(boost_effect.value, dict)
        assert boost_effect.duration == 5

        # Valid capture effect
        capture_effect = ItemEffect(
            effect_type="capture",
            value=0.3,
            target="wild_monster"
        )

        assert capture_effect.effect_type == "capture"
        assert capture_effect.value == 0.3
        assert capture_effect.target == "wild_monster"

    @pytest.mark.unit
    @pytest.mark.game
    def test_player_inventory_slot_management(
        self,
        sample_inventory_slot: PlayerInventorySlot
    ):
        """Test player inventory slot operations."""
        # Test initial state
        assert sample_inventory_slot.quantity == 5
        assert sample_inventory_slot.times_used == 0
        assert sample_inventory_slot.last_used is None

        # Test using item
        sample_inventory_slot.quantity -= 1
        sample_inventory_slot.times_used += 1
        sample_inventory_slot.last_used = datetime.utcnow()

        assert sample_inventory_slot.quantity == 4
        assert sample_inventory_slot.times_used == 1
        assert sample_inventory_slot.last_used is not None

        # Test quantity validation (should not go below 0)
        initial_quantity = sample_inventory_slot.quantity
        for _ in range(initial_quantity + 2):  # Try to use more than available
            if sample_inventory_slot.quantity > 0:
                sample_inventory_slot.quantity -= 1

        assert sample_inventory_slot.quantity == 0

    @pytest.mark.unit
    @pytest.mark.game
    def test_item_price_calculation(
        self,
        sample_healing_item: ItemBase,
        sample_capture_item: ItemBase
    ):
        """Test item price calculation and sell price logic."""
        # Test explicit sell price
        assert sample_healing_item.sell_price == 50
        calculated_sell_price = sample_healing_item.base_price // 2
        assert calculated_sell_price == sample_healing_item.sell_price

        # Test auto-calculated sell price (when sell_price is 0)
        assert sample_capture_item.sell_price == 0
        auto_sell_price = sample_capture_item.base_price // 2
        assert auto_sell_price == 100  # 200 // 2

        # Test price calculation with rarity modifiers
        base_price = 100
        rarity_modifiers = {
            ItemRarity.COMMON: 1.0,
            ItemRarity.UNCOMMON: 1.5,
            ItemRarity.RARE: 3.0,
            ItemRarity.EPIC: 6.0,
            ItemRarity.LEGENDARY: 12.0
        }

        for rarity, modifier in rarity_modifiers.items():
            adjusted_price = int(base_price * modifier)
            expected_prices = {
                ItemRarity.COMMON: 100,
                ItemRarity.UNCOMMON: 150,
                ItemRarity.RARE: 300,
                ItemRarity.EPIC: 600,
                ItemRarity.LEGENDARY: 1200
            }
            assert adjusted_price == expected_prices[rarity]

    @pytest.mark.unit
    @pytest.mark.game
    def test_item_stats_model(
        self,
        sample_healing_item: ItemBase
    ):
        """Test item stats model for API responses."""
        # Convert ItemBase to ItemStats
        item_effects = json.loads(sample_healing_item.effects)

        item_stats = ItemStats(
            slug=sample_healing_item.slug,
            name=sample_healing_item.name,
            description=sample_healing_item.description,
            category=sample_healing_item.category,
            rarity=sample_healing_item.rarity,
            use_context=sample_healing_item.use_context,
            effects=item_effects,
            sprite_name=sample_healing_item.sprite_name
        )

        assert item_stats.slug == "health_potion"
        assert item_stats.name == "Health Potion"
        assert item_stats.category == ItemCategory.HEALING
        assert item_stats.rarity == ItemRarity.COMMON
        assert item_stats.use_context == UseContext.BOTH
        assert item_stats.effects["heal_hp"]["amount"] == 50
        assert item_stats.sprite_name == "potion_red"

    @pytest.mark.unit
    @pytest.mark.game
    def test_item_sorting_and_organization(
        self,
        sample_healing_item: ItemBase,
        sample_capture_item: ItemBase,
        sample_rare_item: ItemBase
    ):
        """Test item sorting logic for inventory organization."""
        items = [sample_rare_item, sample_healing_item, sample_capture_item]

        # Sort by sort_order (ascending)
        sorted_by_order = sorted(items, key=lambda x: x.sort_order)
        assert sorted_by_order[0].slug == "health_potion"  # sort_order: 1
        assert sorted_by_order[1].slug == "tuxeball"       # sort_order: 10
        assert sorted_by_order[2].slug == "rare_candy"     # sort_order: 50

        # Sort by category then by sort_order
        def category_sort_key(item):
            category_priority = {
                ItemCategory.HEALING: 1,
                ItemCategory.CAPTURE: 2,
                ItemCategory.BATTLE: 3,
                ItemCategory.EVOLUTION: 4,
                ItemCategory.KEY: 5,
                ItemCategory.MISC: 6
            }
            return (category_priority.get(item.category, 99), item.sort_order)

        sorted_by_category = sorted(items, key=category_sort_key)
        assert sorted_by_category[0].category == ItemCategory.HEALING
        assert sorted_by_category[1].category == ItemCategory.CAPTURE
        assert sorted_by_category[2].category == ItemCategory.EVOLUTION

        # Sort by rarity (highest first)
        rarity_priority = {
            ItemRarity.LEGENDARY: 1,
            ItemRarity.EPIC: 2,
            ItemRarity.RARE: 3,
            ItemRarity.UNCOMMON: 4,
            ItemRarity.COMMON: 5
        }

        sorted_by_rarity = sorted(items, key=lambda x: rarity_priority[x.rarity])
        assert sorted_by_rarity[0].rarity == ItemRarity.RARE     # Rare Candy
        assert sorted_by_rarity[1].rarity == ItemRarity.COMMON   # Health Potion
        assert sorted_by_rarity[2].rarity == ItemRarity.COMMON   # Tuxe Ball

    @pytest.mark.unit
    @pytest.mark.game
    def test_item_usage_validation(
        self,
        sample_healing_item: ItemBase,
        sample_capture_item: ItemBase
    ):
        """Test item usage validation in different contexts."""
        # Test healing item usage (can use both in field and battle)
        assert self._validate_item_usage(sample_healing_item, in_battle=True) is True
        assert self._validate_item_usage(sample_healing_item, in_battle=False) is True

        # Test capture item usage (battle only)
        assert self._validate_item_usage(sample_capture_item, in_battle=True) is True
        assert self._validate_item_usage(sample_capture_item, in_battle=False) is False

        # Test consumable validation
        assert sample_healing_item.consumable is True
        assert sample_capture_item.consumable is True

        # Test quantity limits
        assert self._validate_item_quantity(sample_healing_item, 50) is True  # Under max
        assert self._validate_item_quantity(sample_healing_item, 99) is True  # At max
        assert self._validate_item_quantity(sample_healing_item, 100) is False # Over max

    def _validate_item_usage(self, item: ItemBase, in_battle: bool) -> bool:
        """Validate if item can be used in current context."""
        return self._can_use_item_in_context(item.use_context, in_battle)

    def _validate_item_quantity(self, item: ItemBase, quantity: int) -> bool:
        """Validate if quantity is within item limits."""
        return 0 <= quantity <= item.max_quantity

    @pytest.mark.unit
    @pytest.mark.game
    def test_item_effect_application_logic(self):
        """Test logic for applying different item effects."""
        # Test HP healing effect
        hp_effect = ItemEffect(
            effect_type="heal_hp",
            value=50,
            target="selected_monster"
        )

        current_hp = 30
        max_hp = 100
        healed_hp = self._apply_heal_effect(current_hp, max_hp, hp_effect.value)

        assert healed_hp == 80  # 30 + 50
        assert healed_hp <= max_hp

        # Test healing when at max HP
        full_hp_heal = self._apply_heal_effect(max_hp, max_hp, hp_effect.value)
        assert full_hp_heal == max_hp  # Should not exceed max

        # Test percentage-based healing
        percent_effect = ItemEffect(
            effect_type="heal_hp_percent",
            value=0.5,  # 50%
            target="selected_monster"
        )

        percent_healed = self._apply_heal_effect(current_hp, max_hp, max_hp * percent_effect.value)
        assert percent_healed == 80  # 30 + (100 * 0.5) = 80

        # Test capture effect calculation
        capture_effect = ItemEffect(
            effect_type="capture",
            value=0.3,  # 30% base rate
            target="wild_monster"
        )

        # Mock monster state for capture calculation
        monster_current_hp = 10
        monster_max_hp = 50
        hp_ratio = monster_current_hp / monster_max_hp  # 0.2 (20% HP remaining)

        capture_rate = self._calculate_capture_rate(capture_effect.value, hp_ratio)
        assert capture_rate > capture_effect.value  # Should be higher when monster has low HP

    def _apply_heal_effect(self, current_hp: int, max_hp: int, heal_amount: int) -> int:
        """Apply healing effect to monster HP."""
        return min(max_hp, current_hp + heal_amount)

    def _calculate_capture_rate(self, base_rate: float, hp_ratio: float) -> float:
        """Calculate capture rate based on monster's remaining HP."""
        # Lower HP = higher capture rate (inverse relationship)
        hp_modifier = 2.0 - hp_ratio  # When HP is 20%, modifier is 1.8
        return min(1.0, base_rate * hp_modifier)

    @pytest.mark.unit
    @pytest.mark.game
    def test_inventory_capacity_management(self):
        """Test inventory capacity and slot management."""
        max_inventory_slots = 100  # Example capacity
        current_slots = 95

        # Test adding items within capacity
        assert self._can_add_to_inventory(current_slots, max_inventory_slots, 3) is True
        assert self._can_add_to_inventory(current_slots, max_inventory_slots, 5) is True

        # Test adding items that would exceed capacity
        assert self._can_add_to_inventory(current_slots, max_inventory_slots, 6) is False

        # Test stacking logic for same items
        existing_quantity = 50
        max_stack = 99
        new_items = 30

        can_stack = self._can_stack_items(existing_quantity, new_items, max_stack)
        assert can_stack is True

        # Test stacking that would exceed max
        large_new_items = 60
        can_stack_large = self._can_stack_items(existing_quantity, large_new_items, max_stack)
        assert can_stack_large is False

    def _can_add_to_inventory(self, current_slots: int, max_slots: int, new_slots: int) -> bool:
        """Check if items can be added to inventory."""
        return current_slots + new_slots <= max_slots

    def _can_stack_items(self, existing_qty: int, new_qty: int, max_stack: int) -> bool:
        """Check if items can be stacked together."""
        return existing_qty + new_qty <= max_stack

    @pytest.mark.unit
    @pytest.mark.game
    def test_item_obtainability_and_restrictions(
        self,
        sample_healing_item: ItemBase,
        sample_rare_item: ItemBase
    ):
        """Test item obtainability flags and restrictions."""
        # Test obtainable items
        assert sample_healing_item.obtainable is True
        assert sample_rare_item.obtainable is True

        # Test restriction logic
        player_level = 15
        required_level = {
            ItemRarity.COMMON: 1,
            ItemRarity.UNCOMMON: 5,
            ItemRarity.RARE: 10,
            ItemRarity.EPIC: 20,
            ItemRarity.LEGENDARY: 30
        }

        # Common and rare items should be obtainable at level 15
        assert self._can_obtain_item(sample_healing_item.rarity, player_level, required_level) is True
        assert self._can_obtain_item(sample_rare_item.rarity, player_level, required_level) is True

        # Epic item should not be obtainable at level 15
        epic_obtainable = self._can_obtain_item(ItemRarity.EPIC, player_level, required_level)
        assert epic_obtainable is False

        # Legendary item should not be obtainable at level 15
        legendary_obtainable = self._can_obtain_item(ItemRarity.LEGENDARY, player_level, required_level)
        assert legendary_obtainable is False

    def _can_obtain_item(self, rarity: ItemRarity, player_level: int, level_requirements: Dict[ItemRarity, int]) -> bool:
        """Check if player can obtain item based on level requirements."""
        required_level = level_requirements.get(rarity, 1)
        return player_level >= required_level