# Economy System for AI-Powered Tuxemon
# Austin Kidwell | Intellegix | Mobile-First Pokemon-Style Game

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from uuid import UUID, uuid4
from dataclasses import dataclass
import random

from pydantic import BaseModel, Field
from sqlmodel import SQLModel, Field as SQLField

from app.game.items import ItemStats, item_manager


class TransactionType(str, Enum):
    PURCHASE = "purchase"
    SALE = "sale"
    REWARD = "reward"
    ADMIN = "admin"


@dataclass
class PriceModifier:
    """Price modification factors for dynamic pricing."""
    base_modifier: float = 1.0
    supply_modifier: float = 1.0  # Lower supply = higher prices
    demand_modifier: float = 1.0  # Higher demand = higher prices
    time_modifier: float = 1.0    # Time-based fluctuation
    npc_modifier: float = 1.0     # NPC-specific pricing


class ShopTransaction(SQLModel, table=True):
    """Database model for shop transactions."""
    __tablename__ = "shop_transactions"

    id: Optional[UUID] = SQLField(default_factory=uuid4, primary_key=True)

    # Transaction details
    player_id: UUID = SQLField(foreign_key="players.id", index=True)
    npc_id: Optional[UUID] = SQLField(foreign_key="npcs.id", index=True)
    transaction_type: TransactionType

    # Items and pricing
    item_slug: str = SQLField(index=True)
    quantity: int = Field(gt=0)
    unit_price: int  # Price per item
    total_amount: int  # Total transaction value

    # Market data
    base_price: int  # Original item price
    price_modifier: float = 1.0  # Applied modifier
    market_supply: int = 0  # Supply level when purchased
    market_demand: int = 0  # Demand level when purchased

    # Metadata
    created_at: datetime = SQLField(default_factory=datetime.utcnow)
    notes: Optional[str] = None


class ShopInventorySlot(SQLModel, table=True):
    """NPC shop inventory tracking."""
    __tablename__ = "shop_inventory"

    id: Optional[UUID] = SQLField(default_factory=uuid4, primary_key=True)

    npc_id: UUID = SQLField(foreign_key="npcs.id", index=True)
    item_slug: str = SQLField(index=True)

    # Stock levels
    current_stock: int = Field(ge=0)
    max_stock: int = Field(gt=0)
    restock_rate: int = Field(gt=0)  # Items restocked per hour

    # Pricing
    base_price: int = Field(gt=0)
    current_price: int = Field(gt=0)
    last_price_update: datetime = SQLField(default_factory=datetime.utcnow)

    # Market tracking
    sales_today: int = 0
    sales_week: int = 0
    last_sale: Optional[datetime] = None

    # Metadata
    created_at: datetime = SQLField(default_factory=datetime.utcnow)
    updated_at: datetime = SQLField(default_factory=datetime.utcnow)


# Pydantic Models

class ShopItemListing(BaseModel):
    """Shop item with pricing and availability."""
    item_slug: str
    item_name: str
    description: str
    category: str
    sprite_name: str

    # Pricing
    current_price: int
    base_price: int
    price_modifier: float

    # Availability
    current_stock: int
    max_stock: int
    in_stock: bool

    # Market indicators
    price_trend: str  # "rising", "falling", "stable"
    demand_level: str  # "low", "medium", "high"
    popularity: int = 0  # 0-100 popularity score


class ShopListing(BaseModel):
    """Complete shop information."""
    npc_id: str
    npc_name: str
    shop_type: str = "general"
    items: List[ShopItemListing]
    total_items: int
    accepts_selling: bool = True
    buy_back_rate: float = 0.5  # Percentage of original price when buying back


class PurchaseRequest(BaseModel):
    """Request to purchase items."""
    item_slug: str
    quantity: int = Field(gt=0, le=99)


class SellRequest(BaseModel):
    """Request to sell items to shop."""
    item_slug: str
    quantity: int = Field(gt=0, le=99)


class TransactionResult(BaseModel):
    """Result of a shop transaction."""
    success: bool
    message: str
    transaction_id: Optional[str] = None

    # Financial details
    unit_price: int = 0
    total_cost: int = 0
    new_money_balance: int = 0

    # Item details
    items_transferred: int = 0
    new_stock_level: int = 0


class EconomyManager:
    """Manages the game economy and dynamic pricing."""

    def __init__(self):
        self.price_fluctuation_range = 0.3  # ±30% price variation
        self.demand_decay_hours = 24  # Demand normalizes after 24 hours
        self.supply_restock_rate = 0.1  # 10% stock restored per hour

    def calculate_dynamic_price(
        self,
        base_price: int,
        current_stock: int,
        max_stock: int,
        recent_sales: int,
        npc_type: str = "general",
        time_of_day: str = "day"
    ) -> Tuple[int, PriceModifier]:
        """Calculate dynamic price based on supply, demand, and other factors."""

        modifier = PriceModifier(base_modifier=1.0)

        # Supply modifier - less stock = higher prices
        stock_ratio = current_stock / max(max_stock, 1)
        if stock_ratio < 0.2:  # Very low stock
            modifier.supply_modifier = 1.4
        elif stock_ratio < 0.5:  # Low stock
            modifier.supply_modifier = 1.2
        elif stock_ratio > 0.9:  # High stock
            modifier.supply_modifier = 0.9
        else:  # Normal stock
            modifier.supply_modifier = 1.0

        # Demand modifier - more recent sales = higher prices
        if recent_sales > 10:  # High demand
            modifier.demand_modifier = 1.3
        elif recent_sales > 5:  # Medium demand
            modifier.demand_modifier = 1.1
        elif recent_sales == 0:  # No demand
            modifier.demand_modifier = 0.8
        else:  # Low demand
            modifier.demand_modifier = 0.95

        # Time-based modifier
        if time_of_day == "evening":
            modifier.time_modifier = 1.05  # Slight evening markup
        elif time_of_day == "night":
            modifier.time_modifier = 0.95  # Night discount for most items

        # NPC type modifier
        if npc_type == "premium":
            modifier.npc_modifier = 1.5  # Premium shops charge more
        elif npc_type == "discount":
            modifier.npc_modifier = 0.8  # Discount shops charge less
        elif npc_type == "specialty":
            modifier.npc_modifier = 1.2  # Specialty shops charge premium

        # Random fluctuation (±5%)
        random_modifier = random.uniform(0.95, 1.05)

        # Calculate final price
        total_modifier = (
            modifier.supply_modifier *
            modifier.demand_modifier *
            modifier.time_modifier *
            modifier.npc_modifier *
            random_modifier
        )

        # Clamp the modifier to reasonable bounds
        total_modifier = max(0.5, min(2.0, total_modifier))

        final_price = int(base_price * total_modifier)

        # Ensure minimum price of 1
        final_price = max(1, final_price)

        return final_price, modifier

    def get_price_trend(self, price_history: List[int]) -> str:
        """Determine price trend based on recent history."""
        if len(price_history) < 2:
            return "stable"

        recent_avg = sum(price_history[-3:]) / min(3, len(price_history))
        older_avg = sum(price_history[:-3]) / max(1, len(price_history) - 3)

        if recent_avg > older_avg * 1.1:
            return "rising"
        elif recent_avg < older_avg * 0.9:
            return "falling"
        else:
            return "stable"

    def calculate_sell_price(
        self,
        item_slug: str,
        current_market_price: int,
        buy_back_rate: float = 0.5
    ) -> int:
        """Calculate price when selling items to NPCs."""

        # Get base item data
        if item_slug not in item_manager.predefined_items:
            return 0

        item_data = item_manager.predefined_items[item_slug]

        # Use the lower of market price or base sell price
        base_sell = item_data.sell_price if item_data.sell_price > 0 else item_data.base_price // 2
        market_sell = int(current_market_price * buy_back_rate)

        return min(base_sell, market_sell)

    def generate_shop_inventory(
        self,
        npc_type: str = "general",
        level_range: Tuple[int, int] = (1, 10),
        item_categories: List[str] = None
    ) -> List[Dict]:
        """Generate random shop inventory for an NPC."""

        if item_categories is None:
            item_categories = ["healing", "capture", "battle"]

        # Filter items by category and level appropriateness
        available_items = []
        for slug, item_data in item_manager.predefined_items.items():
            if item_data.category.value in item_categories:
                # Simple level-based filtering (can be enhanced)
                item_level = 1
                if "super" in slug:
                    item_level = 5
                elif "hyper" in slug or "ultra" in slug:
                    item_level = 10
                elif "full" in slug or "evolution" in slug:
                    item_level = 15

                if level_range[0] <= item_level <= level_range[1]:
                    available_items.append((slug, item_data))

        # Select random subset for shop
        shop_size = random.randint(5, min(12, len(available_items)))
        selected_items = random.sample(available_items, min(shop_size, len(available_items)))

        # Generate inventory slots
        inventory = []
        for slug, item_data in selected_items:
            # Stock levels based on item rarity
            if item_data.rarity.value == "common":
                max_stock = random.randint(20, 50)
            elif item_data.rarity.value == "uncommon":
                max_stock = random.randint(10, 25)
            elif item_data.rarity.value == "rare":
                max_stock = random.randint(5, 15)
            else:  # epic/legendary
                max_stock = random.randint(1, 5)

            current_stock = random.randint(max_stock // 2, max_stock)

            # Calculate initial price
            base_price = item_data.base_price
            if npc_type == "premium":
                base_price = int(base_price * 1.2)
            elif npc_type == "discount":
                base_price = int(base_price * 0.8)

            inventory_slot = {
                "item_slug": slug,
                "current_stock": current_stock,
                "max_stock": max_stock,
                "base_price": base_price,
                "current_price": base_price,
                "restock_rate": max(1, max_stock // 24),  # Restock over 24 hours
                "sales_today": random.randint(0, 3),
                "sales_week": random.randint(0, 20),
            }

            inventory.append(inventory_slot)

        return inventory

    def simulate_market_activity(
        self,
        shop_inventories: List[ShopInventorySlot],
        hours_elapsed: int = 1
    ) -> List[ShopInventorySlot]:
        """Simulate market activity over time (restocking, price changes)."""

        updated_inventories = []

        for slot in shop_inventories:
            # Natural restocking
            if slot.current_stock < slot.max_stock:
                restock_amount = min(
                    slot.restock_rate * hours_elapsed,
                    slot.max_stock - slot.current_stock
                )
                slot.current_stock += int(restock_amount)

            # Price fluctuation based on stock levels and sales
            recent_sales = slot.sales_today
            current_price, _ = self.calculate_dynamic_price(
                base_price=slot.base_price,
                current_stock=slot.current_stock,
                max_stock=slot.max_stock,
                recent_sales=recent_sales
            )
            slot.current_price = current_price

            # Decay daily sales (reset daily)
            if hours_elapsed >= 24:
                slot.sales_today = 0

            slot.updated_at = datetime.utcnow()
            updated_inventories.append(slot)

        return updated_inventories


# Global economy manager instance
economy_manager = EconomyManager()