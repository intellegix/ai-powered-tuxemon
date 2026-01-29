# Item System for AI-Powered Tuxemon
# Austin Kidwell | Intellegix | Mobile-First Pokemon-Style Game

from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator
from sqlmodel import SQLModel, Field as SQLField, Relationship


class ItemCategory(str, Enum):
    HEALING = "healing"
    CAPTURE = "capture"
    EVOLUTION = "evolution"
    BATTLE = "battle"
    KEY = "key"
    MISC = "misc"


class ItemRarity(str, Enum):
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


class UseContext(str, Enum):
    FIELD = "field"  # Can use outside of battle
    BATTLE = "battle"  # Can use in battle
    BOTH = "both"  # Can use anywhere


class ItemBase(SQLModel, table=True):
    """Database model for item definitions."""
    __tablename__ = "items"

    id: Optional[int] = SQLField(default=None, primary_key=True)
    slug: str = SQLField(unique=True, index=True)
    name: str
    description: str
    category: ItemCategory
    rarity: ItemRarity = ItemRarity.COMMON
    use_context: UseContext = UseContext.FIELD

    # Effects and usage
    effects: str = "{}"  # JSON dict of effects
    use_animation: Optional[str] = None
    use_sound: Optional[str] = None
    consumable: bool = True
    max_quantity: int = 99

    # Economy
    base_price: int = 0
    sell_price: int = 0  # If 0, calculated as base_price // 2

    # Metadata
    sprite_name: str
    sort_order: int = 0
    obtainable: bool = True
    created_at: datetime = SQLField(default_factory=datetime.utcnow)


class PlayerInventorySlot(SQLModel, table=True):
    """Database model for player inventory slots."""
    __tablename__ = "player_inventory"

    id: Optional[UUID] = SQLField(default_factory=uuid4, primary_key=True)
    player_id: UUID = SQLField(foreign_key="players.id", index=True)
    item_slug: str = SQLField(foreign_key="items.slug")
    quantity: int = Field(ge=0)

    # Metadata
    obtained_at: datetime = SQLField(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = None
    times_used: int = 0


# Pydantic Models for API

class ItemEffect(BaseModel):
    """Single item effect definition."""
    effect_type: str  # "heal_hp", "heal_status", "boost_stats", "capture", etc.
    value: Union[int, float, str]  # Amount or identifier
    target: str = "selected_monster"  # "selected_monster", "all_party", "player"
    duration: Optional[int] = None  # For temporary effects


class ItemStats(BaseModel):
    """Complete item information."""
    slug: str
    name: str
    description: str
    category: ItemCategory
    rarity: ItemRarity
    use_context: UseContext
    effects: Dict[str, Any]
    sprite_name: str
    base_price: int
    sell_price: int
    consumable: bool
    max_quantity: int


class InventorySlot(BaseModel):
    """Player inventory slot with item info."""
    item_slug: str
    item_name: str
    quantity: int
    category: ItemCategory
    description: str
    sprite_name: str
    can_use_now: bool = True  # Based on current context
    stack_info: Optional[str] = None  # "3/99" for stacked items


class UseItemRequest(BaseModel):
    """Request to use an item."""
    item_slug: str
    target_monster_id: Optional[UUID] = None
    quantity: int = 1


class UseItemResult(BaseModel):
    """Result of using an item."""
    success: bool
    message: str
    effects_applied: List[str] = []
    item_consumed: bool = False
    remaining_quantity: int = 0


class ItemManager:
    """Manager class for item operations."""

    def __init__(self):
        self.predefined_items = self._load_predefined_items()

    def _load_predefined_items(self) -> Dict[str, ItemStats]:
        """Load predefined game items."""
        items = {
            # Healing Items
            "potion": ItemStats(
                slug="potion",
                name="Potion",
                description="Restores 20 HP to a monster",
                category=ItemCategory.HEALING,
                rarity=ItemRarity.COMMON,
                use_context=UseContext.BOTH,
                effects={
                    "heal_hp": {"amount": 20, "target": "selected_monster"}
                },
                sprite_name="potion",
                base_price=100,
                sell_price=50,
                consumable=True,
                max_quantity=99
            ),

            "super_potion": ItemStats(
                slug="super_potion",
                name="Super Potion",
                description="Restores 50 HP to a monster",
                category=ItemCategory.HEALING,
                rarity=ItemRarity.UNCOMMON,
                use_context=UseContext.BOTH,
                effects={
                    "heal_hp": {"amount": 50, "target": "selected_monster"}
                },
                sprite_name="super_potion",
                base_price=250,
                sell_price=125,
                consumable=True,
                max_quantity=99
            ),

            "hyper_potion": ItemStats(
                slug="hyper_potion",
                name="Hyper Potion",
                description="Restores 120 HP to a monster",
                category=ItemCategory.HEALING,
                rarity=ItemRarity.RARE,
                use_context=UseContext.BOTH,
                effects={
                    "heal_hp": {"amount": 120, "target": "selected_monster"}
                },
                sprite_name="hyper_potion",
                base_price=600,
                sell_price=300,
                consumable=True,
                max_quantity=99
            ),

            "full_restore": ItemStats(
                slug="full_restore",
                name="Full Restore",
                description="Fully restores HP and heals all status ailments",
                category=ItemCategory.HEALING,
                rarity=ItemRarity.EPIC,
                use_context=UseContext.BOTH,
                effects={
                    "heal_hp": {"amount": "full", "target": "selected_monster"},
                    "heal_status": {"conditions": "all", "target": "selected_monster"}
                },
                sprite_name="full_restore",
                base_price=1500,
                sell_price=750,
                consumable=True,
                max_quantity=99
            ),

            # Capture Items
            "tuxeball": ItemStats(
                slug="tuxeball",
                name="Tuxeball",
                description="Standard device for capturing wild monsters",
                category=ItemCategory.CAPTURE,
                rarity=ItemRarity.COMMON,
                use_context=UseContext.BATTLE,
                effects={
                    "capture": {"rate_modifier": 1.0}
                },
                sprite_name="tuxeball",
                base_price=200,
                sell_price=100,
                consumable=True,
                max_quantity=99
            ),

            "great_ball": ItemStats(
                slug="great_ball",
                name="Great Ball",
                description="High-performance capturing device",
                category=ItemCategory.CAPTURE,
                rarity=ItemRarity.UNCOMMON,
                use_context=UseContext.BATTLE,
                effects={
                    "capture": {"rate_modifier": 1.5}
                },
                sprite_name="great_ball",
                base_price=400,
                sell_price=200,
                consumable=True,
                max_quantity=99
            ),

            "ultra_ball": ItemStats(
                slug="ultra_ball",
                name="Ultra Ball",
                description="Ultra-high-performance capturing device",
                category=ItemCategory.CAPTURE,
                rarity=ItemRarity.RARE,
                use_context=UseContext.BATTLE,
                effects={
                    "capture": {"rate_modifier": 2.0}
                },
                sprite_name="ultra_ball",
                base_price=800,
                sell_price=400,
                consumable=True,
                max_quantity=99
            ),

            # Battle Items
            "attack_boost": ItemStats(
                slug="attack_boost",
                name="Attack Boost",
                description="Raises a monster's attack for one battle",
                category=ItemCategory.BATTLE,
                rarity=ItemRarity.UNCOMMON,
                use_context=UseContext.BATTLE,
                effects={
                    "boost_stat": {
                        "stat": "melee",
                        "amount": 1,
                        "duration": "battle",
                        "target": "selected_monster"
                    }
                },
                sprite_name="attack_boost",
                base_price=300,
                sell_price=150,
                consumable=True,
                max_quantity=50
            ),

            "defense_boost": ItemStats(
                slug="defense_boost",
                name="Defense Boost",
                description="Raises a monster's defense for one battle",
                category=ItemCategory.BATTLE,
                rarity=ItemRarity.UNCOMMON,
                use_context=UseContext.BATTLE,
                effects={
                    "boost_stat": {
                        "stat": "armour",
                        "amount": 1,
                        "duration": "battle",
                        "target": "selected_monster"
                    }
                },
                sprite_name="defense_boost",
                base_price=300,
                sell_price=150,
                consumable=True,
                max_quantity=50
            ),

            # Evolution Items
            "evolution_crystal": ItemStats(
                slug="evolution_crystal",
                name="Evolution Crystal",
                description="Mysterious crystal that helps certain monsters evolve",
                category=ItemCategory.EVOLUTION,
                rarity=ItemRarity.RARE,
                use_context=UseContext.FIELD,
                effects={
                    "evolution": {"type": "crystal"}
                },
                sprite_name="evolution_crystal",
                base_price=2000,
                sell_price=1000,
                consumable=True,
                max_quantity=10
            ),

            # Misc Items
            "monster_treats": ItemStats(
                slug="monster_treats",
                name="Monster Treats",
                description="Delicious treats that monsters love. Increases friendship.",
                category=ItemCategory.MISC,
                rarity=ItemRarity.COMMON,
                use_context=UseContext.FIELD,
                effects={
                    "friendship": {"amount": 10, "target": "selected_monster"}
                },
                sprite_name="monster_treats",
                base_price=150,
                sell_price=75,
                consumable=True,
                max_quantity=99
            ),
        }

        return items

    async def apply_item_effects(
        self,
        item_slug: str,
        target_monster_id: Optional[UUID],
        player,  # Player model
        context: str = "field"  # "field" or "battle"
    ) -> UseItemResult:
        """Apply item effects to target."""

        if item_slug not in self.predefined_items:
            return UseItemResult(
                success=False,
                message="Unknown item"
            )

        item = self.predefined_items[item_slug]

        # Check if item can be used in this context
        if item.use_context == UseContext.BATTLE and context != "battle":
            return UseItemResult(
                success=False,
                message="This item can only be used in battle"
            )
        elif item.use_context == UseContext.FIELD and context == "battle":
            return UseItemResult(
                success=False,
                message="This item cannot be used in battle"
            )

        effects_applied = []

        # Apply healing effects
        if "heal_hp" in item.effects:
            heal_effect = item.effects["heal_hp"]
            amount = heal_effect["amount"]

            if amount == "full":
                effects_applied.append("Fully restored HP")
            else:
                effects_applied.append(f"Restored {amount} HP")

        # Apply status healing
        if "heal_status" in item.effects:
            heal_effect = item.effects["heal_status"]
            conditions = heal_effect.get("conditions", "all")
            effects_applied.append("Cured status ailments")

        # Apply stat boosts
        if "boost_stat" in item.effects:
            boost_effect = item.effects["boost_stat"]
            stat = boost_effect["stat"]
            amount = boost_effect["amount"]
            effects_applied.append(f"Boosted {stat}")

        # Apply friendship changes
        if "friendship" in item.effects:
            friendship_effect = item.effects["friendship"]
            amount = friendship_effect["amount"]
            effects_applied.append(f"Increased friendship (+{amount})")

        # Handle capture attempts (would integrate with battle system)
        if "capture" in item.effects and context == "battle":
            capture_effect = item.effects["capture"]
            rate_modifier = capture_effect["rate_modifier"]
            effects_applied.append("Attempted to capture wild monster")

        return UseItemResult(
            success=True,
            message=f"Used {item.name}",
            effects_applied=effects_applied,
            item_consumed=item.consumable,
            remaining_quantity=0  # Would be calculated from actual inventory
        )


# Global item manager instance
item_manager = ItemManager()