# Inventory API Routes for AI-Powered Tuxemon
# Austin Kidwell | Intellegix | Mobile-First Pokemon-Style Game

from typing import Dict, List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, and_
from pydantic import BaseModel, Field
from loguru import logger

from app.database import get_db
from app.game.models import Player, Monster
from app.game.items import (
    ItemBase, PlayerInventorySlot, InventorySlot, UseItemRequest, UseItemResult,
    item_manager, ItemCategory, ItemRarity
)
from app.api.routes.auth import get_current_player

router = APIRouter()


# Request/Response Models
class AddItemRequest(BaseModel):
    """Request to add item to inventory."""
    item_slug: str
    quantity: int = 1


class RemoveItemRequest(BaseModel):
    """Request to remove item from inventory."""
    item_slug: str
    quantity: int = 1


class InventoryResponse(BaseModel):
    """Complete inventory response."""
    slots: List[InventorySlot]
    total_items: int
    total_slots: int
    money: int
    categories: Dict[str, List[InventorySlot]]


class ItemCatalogResponse(BaseModel):
    """Available items catalog."""
    items: List[Dict]
    categories: List[str]
    rarities: List[str]


# Pagination models for mobile performance optimization
class PaginationParams(BaseModel):
    """Standard pagination parameters for mobile-optimized responses."""
    page: int = Field(default=1, ge=1, description="Page number (1-based)")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page (max 100)")


class PaginationInfo(BaseModel):
    """Pagination metadata for mobile clients."""
    page: int
    per_page: int
    total_items: int
    total_pages: int
    has_next: bool
    has_previous: bool


class PaginatedInventoryResponse(BaseModel):
    """Paginated inventory response optimized for mobile."""
    slots: List[InventorySlot]
    pagination: PaginationInfo
    categories: List[str]
    total_unique_items: int


@router.get("/", response_model=PaginatedInventoryResponse)
async def get_inventory(
    category: Optional[ItemCategory] = Query(None, description="Filter by item category"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    """Get player's current inventory with pagination for mobile optimization."""
    try:
        # Build base query
        base_query = select(PlayerInventorySlot).where(
            PlayerInventorySlot.player_id == current_player.id
        )

        if category:
            # Join with ItemBase to filter by category
            base_query = base_query.join(ItemBase, PlayerInventorySlot.item_slug == ItemBase.slug)
            base_query = base_query.where(ItemBase.category == category)

        # Get total count for pagination
        count_result = await db.execute(
            select(PlayerInventorySlot).where(
                PlayerInventorySlot.player_id == current_player.id
            ).join(ItemBase, PlayerInventorySlot.item_slug == ItemBase.slug)
            .where(ItemBase.category == category) if category else
            select(PlayerInventorySlot).where(
                PlayerInventorySlot.player_id == current_player.id
            )
        )
        total_count = len(count_result.scalars().all())

        # Apply pagination to main query
        offset = (page - 1) * per_page
        paginated_query = base_query.offset(offset).limit(per_page)
        result = await db.execute(paginated_query)
        inventory_slots = result.scalars().all()

        # Get item details for each slot
        inventory_items = []
        categories_dict = {}

        for slot in inventory_slots:
            if slot.item_slug in item_manager.predefined_items:
                item_data = item_manager.predefined_items[slot.item_slug]

                # Check if item can be used in current context (simplified)
                can_use_now = True
                if item_data.use_context.value == "battle":
                    can_use_now = False  # TODO: Check if player is in battle

                inventory_item = InventorySlot(
                    item_slug=slot.item_slug,
                    item_name=item_data.name,
                    quantity=slot.quantity,
                    category=item_data.category,
                    description=item_data.description,
                    sprite_name=item_data.sprite_name,
                    can_use_now=can_use_now,
                    stack_info=f"{slot.quantity}/{item_data.max_quantity}"
                )

                inventory_items.append(inventory_item)

                # Group by category
                cat_key = item_data.category.value
                if cat_key not in categories_dict:
                    categories_dict[cat_key] = []
                categories_dict[cat_key].append(inventory_item)

        # Calculate pagination metadata
        total_pages = (total_count + per_page - 1) // per_page  # Ceiling division
        has_next = page < total_pages
        has_previous = page > 1

        pagination_info = PaginationInfo(
            page=page,
            per_page=per_page,
            total_items=total_count,
            total_pages=total_pages,
            has_next=has_next,
            has_previous=has_previous
        )

        return PaginatedInventoryResponse(
            slots=inventory_items,
            pagination=pagination_info,
            categories=list(categories_dict.keys()),
            total_unique_items=len(set(item.item_slug for item in inventory_items))
        )

    except Exception as e:
        logger.error(f"Inventory retrieval error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve inventory"
        )


@router.post("/add")
async def add_item_to_inventory(
    request: AddItemRequest,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    """Add item to player's inventory."""
    try:
        # Validate item exists
        if request.item_slug not in item_manager.predefined_items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid item"
            )

        item_data = item_manager.predefined_items[request.item_slug]

        # Check if player already has this item
        existing_result = await db.execute(
            select(PlayerInventorySlot).where(
                and_(
                    PlayerInventorySlot.player_id == current_player.id,
                    PlayerInventorySlot.item_slug == request.item_slug
                )
            )
        )
        existing_slot = existing_result.scalar_one_or_none()

        if existing_slot:
            # Update existing slot
            new_quantity = existing_slot.quantity + request.quantity

            # Check max quantity limit
            if new_quantity > item_data.max_quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot carry more than {item_data.max_quantity} of this item"
                )

            existing_slot.quantity = new_quantity
            db.add(existing_slot)

        else:
            # Create new inventory slot
            new_slot = PlayerInventorySlot(
                player_id=current_player.id,
                item_slug=request.item_slug,
                quantity=request.quantity
            )
            db.add(new_slot)

        await db.commit()

        logger.info(f"Added {request.quantity}x {request.item_slug} to player {current_player.username} inventory")

        return {
            "message": f"Added {request.quantity}x {item_data.name} to inventory",
            "item_name": item_data.name,
            "quantity_added": request.quantity,
            "total_quantity": new_quantity if existing_slot else request.quantity
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Add item error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add item to inventory"
        )


@router.post("/remove")
async def remove_item_from_inventory(
    request: RemoveItemRequest,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    """Remove item from player's inventory."""
    try:
        # Find inventory slot
        result = await db.execute(
            select(PlayerInventorySlot).where(
                and_(
                    PlayerInventorySlot.player_id == current_player.id,
                    PlayerInventorySlot.item_slug == request.item_slug
                )
            )
        )
        slot = result.scalar_one_or_none()

        if not slot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found in inventory"
            )

        if slot.quantity < request.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Not enough items in inventory"
            )

        # Update or remove slot
        if slot.quantity == request.quantity:
            await db.delete(slot)
        else:
            slot.quantity -= request.quantity
            db.add(slot)

        await db.commit()

        item_data = item_manager.predefined_items.get(request.item_slug)
        item_name = item_data.name if item_data else request.item_slug

        logger.info(f"Removed {request.quantity}x {request.item_slug} from player {current_player.username} inventory")

        return {
            "message": f"Removed {request.quantity}x {item_name} from inventory",
            "item_name": item_name,
            "quantity_removed": request.quantity,
            "remaining_quantity": max(0, slot.quantity - request.quantity) if slot.quantity > request.quantity else 0
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Remove item error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove item from inventory"
        )


@router.post("/use", response_model=UseItemResult)
async def use_item(
    request: UseItemRequest,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    """Use an item from inventory."""
    try:
        # Check if player has the item
        result = await db.execute(
            select(PlayerInventorySlot).where(
                and_(
                    PlayerInventorySlot.player_id == current_player.id,
                    PlayerInventorySlot.item_slug == request.item_slug
                )
            )
        )
        slot = result.scalar_one_or_none()

        if not slot or slot.quantity < request.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Not enough items in inventory"
            )

        # Validate target monster if specified
        target_monster = None
        if request.target_monster_id:
            monster_result = await db.execute(
                select(Monster).where(
                    and_(
                        Monster.id == request.target_monster_id,
                        Monster.player_id == current_player.id
                    )
                )
            )
            target_monster = monster_result.scalar_one_or_none()

            if not target_monster:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Target monster not found in your party"
                )

        # Apply item effects
        use_result = await item_manager.apply_item_effects(
            item_slug=request.item_slug,
            target_monster_id=request.target_monster_id,
            player=current_player,
            context="field"  # TODO: Detect if in battle
        )

        if not use_result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=use_result.message
            )

        # Update inventory if item was consumed
        if use_result.item_consumed:
            if slot.quantity == request.quantity:
                await db.delete(slot)
            else:
                slot.quantity -= request.quantity
                db.add(slot)

            # Update usage statistics
            slot.times_used += request.quantity
            slot.last_used = datetime.utcnow()

        await db.commit()

        logger.info(f"Player {current_player.username} used {request.quantity}x {request.item_slug}")

        return UseItemResult(
            success=True,
            message=use_result.message,
            effects_applied=use_result.effects_applied,
            item_consumed=use_result.item_consumed,
            remaining_quantity=slot.quantity if not use_result.item_consumed else max(0, slot.quantity - request.quantity)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Use item error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to use item"
        )


@router.get("/catalog", response_model=ItemCatalogResponse)
async def get_item_catalog():
    """Get catalog of all available items."""
    try:
        items = []
        for slug, item_data in item_manager.predefined_items.items():
            items.append({
                "slug": slug,
                "name": item_data.name,
                "description": item_data.description,
                "category": item_data.category.value,
                "rarity": item_data.rarity.value,
                "base_price": item_data.base_price,
                "sell_price": item_data.sell_price,
                "sprite_name": item_data.sprite_name,
                "max_quantity": item_data.max_quantity,
                "consumable": item_data.consumable,
                "use_context": item_data.use_context.value
            })

        # Sort by category and name
        items.sort(key=lambda x: (x["category"], x["name"]))

        return ItemCatalogResponse(
            items=items,
            categories=[cat.value for cat in ItemCategory],
            rarities=[rarity.value for rarity in ItemRarity]
        )

    except Exception as e:
        logger.error(f"Item catalog error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve item catalog"
        )


@router.get("/stats")
async def get_inventory_stats(
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    """Get player inventory statistics."""
    try:
        # Get total items and value
        result = await db.execute(
            select(PlayerInventorySlot).where(
                PlayerInventorySlot.player_id == current_player.id
            )
        )
        slots = result.scalars().all()

        total_items = sum(slot.quantity for slot in slots)
        total_value = 0
        categories_count = {}
        rarity_count = {}

        for slot in slots:
            item_data = item_manager.predefined_items.get(slot.item_slug)
            if item_data:
                total_value += item_data.sell_price * slot.quantity

                # Count by category
                cat = item_data.category.value
                categories_count[cat] = categories_count.get(cat, 0) + slot.quantity

                # Count by rarity
                rarity = item_data.rarity.value
                rarity_count[rarity] = rarity_count.get(rarity, 0) + slot.quantity

        return {
            "total_unique_items": len(slots),
            "total_items": total_items,
            "total_value": total_value,
            "categories": categories_count,
            "rarities": rarity_count,
            "money": current_player.money
        }

    except Exception as e:
        logger.error(f"Inventory stats error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve inventory statistics"
        )