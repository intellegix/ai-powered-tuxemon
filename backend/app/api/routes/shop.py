# Shop API Routes for AI-Powered Tuxemon
# Austin Kidwell | Intellegix | Mobile-First Pokemon-Style Game

from typing import Dict, List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, and_
from pydantic import BaseModel
from loguru import logger

from app.database import get_db
from app.game.models import Player, NPC
from app.game.items import PlayerInventorySlot, item_manager
from app.game.economy import (
    ShopTransaction, ShopInventorySlot, TransactionType,
    ShopListing, ShopItemListing, PurchaseRequest, SellRequest,
    TransactionResult, economy_manager
)
from app.api.routes.auth import get_current_player

router = APIRouter()


@router.get("/{npc_id}", response_model=ShopListing)
async def get_shop_inventory(
    npc_id: UUID,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    """Get NPC shop inventory with current prices."""
    try:
        # Get NPC details
        npc_result = await db.execute(
            select(NPC).where(NPC.id == npc_id)
        )
        npc = npc_result.scalar_one_or_none()

        if not npc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shop not found"
            )

        # Get shop inventory
        inventory_result = await db.execute(
            select(ShopInventorySlot).where(ShopInventorySlot.npc_id == npc_id)
        )
        inventory_slots = inventory_result.scalars().all()

        # If no inventory exists, generate default inventory
        if not inventory_slots:
            logger.info(f"Generating shop inventory for NPC {npc.slug}")

            # Determine shop type from NPC name/slug
            shop_type = "general"
            if "medic" in npc.slug or "healer" in npc.slug:
                shop_type = "healing"
                categories = ["healing"]
            elif "trainer" in npc.slug:
                shop_type = "battle"
                categories = ["capture", "battle"]
            else:
                categories = ["healing", "capture", "battle"]

            # Generate inventory
            generated_inventory = economy_manager.generate_shop_inventory(
                npc_type=shop_type,
                level_range=(1, 20),
                item_categories=categories
            )

            # Save to database
            for inv_data in generated_inventory:
                inventory_slot = ShopInventorySlot(
                    npc_id=npc_id,
                    item_slug=inv_data["item_slug"],
                    current_stock=inv_data["current_stock"],
                    max_stock=inv_data["max_stock"],
                    restock_rate=inv_data["restock_rate"],
                    base_price=inv_data["base_price"],
                    current_price=inv_data["current_price"],
                    sales_today=inv_data["sales_today"],
                    sales_week=inv_data["sales_week"],
                )
                db.add(inventory_slot)
                inventory_slots.append(inventory_slot)

            await db.commit()

        # Format items for API response
        shop_items = []
        for slot in inventory_slots:
            if slot.item_slug in item_manager.predefined_items:
                item_data = item_manager.predefined_items[slot.item_slug]

                # Calculate current price with market factors
                current_price, _ = economy_manager.calculate_dynamic_price(
                    base_price=slot.base_price,
                    current_stock=slot.current_stock,
                    max_stock=slot.max_stock,
                    recent_sales=slot.sales_today
                )

                # Update slot with new price
                slot.current_price = current_price
                db.add(slot)

                # Determine price trend (simplified)
                price_trend = "stable"
                price_modifier = current_price / slot.base_price
                if price_modifier > 1.1:
                    price_trend = "rising"
                elif price_modifier < 0.9:
                    price_trend = "falling"

                # Determine demand level
                demand_level = "low"
                if slot.sales_today > 5:
                    demand_level = "high"
                elif slot.sales_today > 2:
                    demand_level = "medium"

                shop_item = ShopItemListing(
                    item_slug=slot.item_slug,
                    item_name=item_data.name,
                    description=item_data.description,
                    category=item_data.category.value,
                    sprite_name=item_data.sprite_name,
                    current_price=current_price,
                    base_price=slot.base_price,
                    price_modifier=price_modifier,
                    current_stock=slot.current_stock,
                    max_stock=slot.max_stock,
                    in_stock=slot.current_stock > 0,
                    price_trend=price_trend,
                    demand_level=demand_level,
                    popularity=min(100, slot.sales_week * 5)
                )

                shop_items.append(shop_item)

        await db.commit()

        return ShopListing(
            npc_id=str(npc_id),
            npc_name=npc.name,
            shop_type="general",  # TODO: Determine from NPC data
            items=shop_items,
            total_items=len(shop_items),
            accepts_selling=True,
            buy_back_rate=0.6
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Shop inventory error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve shop inventory"
        )


@router.post("/{npc_id}/purchase", response_model=TransactionResult)
async def purchase_item(
    npc_id: UUID,
    request: PurchaseRequest,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    """Purchase items from NPC shop."""
    try:
        # Get NPC
        npc_result = await db.execute(
            select(NPC).where(NPC.id == npc_id)
        )
        npc = npc_result.scalar_one_or_none()

        if not npc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shop not found"
            )

        # Get shop inventory slot
        slot_result = await db.execute(
            select(ShopInventorySlot).where(
                and_(
                    ShopInventorySlot.npc_id == npc_id,
                    ShopInventorySlot.item_slug == request.item_slug
                )
            )
        )
        slot = slot_result.scalar_one_or_none()

        if not slot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not available in this shop"
            )

        # Check stock availability
        if slot.current_stock < request.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Not enough stock. Available: {slot.current_stock}"
            )

        # Calculate current price
        current_price, _ = economy_manager.calculate_dynamic_price(
            base_price=slot.base_price,
            current_stock=slot.current_stock,
            max_stock=slot.max_stock,
            recent_sales=slot.sales_today
        )

        total_cost = current_price * request.quantity

        # Check player's money
        if current_player.money < total_cost:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Not enough money. Cost: {total_cost}, You have: {current_player.money}"
            )

        # Update player money
        current_player.money -= total_cost
        db.add(current_player)

        # Update shop stock
        slot.current_stock -= request.quantity
        slot.sales_today += request.quantity
        slot.sales_week += request.quantity
        slot.last_sale = datetime.utcnow()
        db.add(slot)

        # Add items to player inventory
        player_slot_result = await db.execute(
            select(PlayerInventorySlot).where(
                and_(
                    PlayerInventorySlot.player_id == current_player.id,
                    PlayerInventorySlot.item_slug == request.item_slug
                )
            )
        )
        player_slot = player_slot_result.scalar_one_or_none()

        if player_slot:
            # Update existing inventory slot
            item_data = item_manager.predefined_items.get(request.item_slug)
            max_quantity = item_data.max_quantity if item_data else 99

            if player_slot.quantity + request.quantity > max_quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot carry more than {max_quantity} of this item"
                )

            player_slot.quantity += request.quantity
            db.add(player_slot)
        else:
            # Create new inventory slot
            new_player_slot = PlayerInventorySlot(
                player_id=current_player.id,
                item_slug=request.item_slug,
                quantity=request.quantity
            )
            db.add(new_player_slot)

        # Record transaction
        transaction = ShopTransaction(
            player_id=current_player.id,
            npc_id=npc_id,
            transaction_type=TransactionType.PURCHASE,
            item_slug=request.item_slug,
            quantity=request.quantity,
            unit_price=current_price,
            total_amount=total_cost,
            base_price=slot.base_price,
            price_modifier=current_price / slot.base_price,
            market_supply=slot.current_stock + request.quantity,  # Stock before purchase
            market_demand=slot.sales_today
        )
        db.add(transaction)

        await db.commit()

        logger.info(f"Player {current_player.username} purchased {request.quantity}x {request.item_slug} for {total_cost}")

        return TransactionResult(
            success=True,
            message=f"Purchased {request.quantity}x {request.item_slug}",
            transaction_id=str(transaction.id),
            unit_price=current_price,
            total_cost=total_cost,
            new_money_balance=current_player.money,
            items_transferred=request.quantity,
            new_stock_level=slot.current_stock
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Purchase error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete purchase"
        )


@router.post("/{npc_id}/sell", response_model=TransactionResult)
async def sell_item(
    npc_id: UUID,
    request: SellRequest,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    """Sell items to NPC shop."""
    try:
        # Get NPC
        npc_result = await db.execute(
            select(NPC).where(NPC.id == npc_id)
        )
        npc = npc_result.scalar_one_or_none()

        if not npc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shop not found"
            )

        # Check if player has the item
        player_slot_result = await db.execute(
            select(PlayerInventorySlot).where(
                and_(
                    PlayerInventorySlot.player_id == current_player.id,
                    PlayerInventorySlot.item_slug == request.item_slug
                )
            )
        )
        player_slot = player_slot_result.scalar_one_or_none()

        if not player_slot or player_slot.quantity < request.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You don't have enough of this item to sell"
            )

        # Get current market price (if shop sells this item)
        slot_result = await db.execute(
            select(ShopInventorySlot).where(
                and_(
                    ShopInventorySlot.npc_id == npc_id,
                    ShopInventorySlot.item_slug == request.item_slug
                )
            )
        )
        slot = slot_result.scalar_one_or_none()

        current_market_price = slot.current_price if slot else None

        # Calculate sell price
        sell_price = economy_manager.calculate_sell_price(
            item_slug=request.item_slug,
            current_market_price=current_market_price or 0,
            buy_back_rate=0.6
        )

        if sell_price <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This shop doesn't buy that item"
            )

        total_payment = sell_price * request.quantity

        # Update player money
        current_player.money += total_payment
        db.add(current_player)

        # Remove items from player inventory
        if player_slot.quantity == request.quantity:
            await db.delete(player_slot)
        else:
            player_slot.quantity -= request.quantity
            player_slot.times_used += request.quantity
            db.add(player_slot)

        # Update shop stock if shop sells this item
        if slot:
            slot.current_stock += request.quantity
            # Prevent overstocking
            if slot.current_stock > slot.max_stock:
                excess = slot.current_stock - slot.max_stock
                slot.current_stock = slot.max_stock
                # Could implement overflow handling here

            db.add(slot)

        # Record transaction
        transaction = ShopTransaction(
            player_id=current_player.id,
            npc_id=npc_id,
            transaction_type=TransactionType.SALE,
            item_slug=request.item_slug,
            quantity=request.quantity,
            unit_price=sell_price,
            total_amount=total_payment,
            base_price=current_market_price or sell_price,
            price_modifier=1.0,
            market_supply=slot.current_stock if slot else 0,
            market_demand=0
        )
        db.add(transaction)

        await db.commit()

        logger.info(f"Player {current_player.username} sold {request.quantity}x {request.item_slug} for {total_payment}")

        return TransactionResult(
            success=True,
            message=f"Sold {request.quantity}x {request.item_slug}",
            transaction_id=str(transaction.id),
            unit_price=sell_price,
            total_cost=-total_payment,  # Negative because player receives money
            new_money_balance=current_player.money,
            items_transferred=request.quantity,
            new_stock_level=slot.current_stock if slot else 0
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sell error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete sale"
        )


@router.get("/{npc_id}/transactions")
async def get_shop_transactions(
    npc_id: UUID,
    limit: int = 50,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    """Get recent transactions for a shop (player's own transactions only)."""
    try:
        # Get transactions
        result = await db.execute(
            select(ShopTransaction).where(
                and_(
                    ShopTransaction.npc_id == npc_id,
                    ShopTransaction.player_id == current_player.id
                )
            ).order_by(ShopTransaction.created_at.desc()).limit(limit)
        )
        transactions = result.scalars().all()

        formatted_transactions = []
        for transaction in transactions:
            item_data = item_manager.predefined_items.get(transaction.item_slug)
            item_name = item_data.name if item_data else transaction.item_slug

            formatted_transactions.append({
                "id": str(transaction.id),
                "type": transaction.transaction_type.value,
                "item_slug": transaction.item_slug,
                "item_name": item_name,
                "quantity": transaction.quantity,
                "unit_price": transaction.unit_price,
                "total_amount": transaction.total_amount,
                "created_at": transaction.created_at.isoformat(),
            })

        return {
            "transactions": formatted_transactions,
            "total": len(formatted_transactions),
        }

    except Exception as e:
        logger.error(f"Transaction history error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve transaction history"
        )


@router.get("/market/prices")
async def get_market_prices(
    item_slugs: Optional[str] = None,  # Comma-separated list
    db: AsyncSession = Depends(get_db),
):
    """Get current market prices across all shops."""
    try:
        # Parse item filters
        filter_items = None
        if item_slugs:
            filter_items = [slug.strip() for slug in item_slugs.split(",")]

        # Get all shop inventory
        query = select(ShopInventorySlot)
        if filter_items:
            query = query.where(ShopInventorySlot.item_slug.in_(filter_items))

        result = await db.execute(query)
        inventory_slots = result.scalars().all()

        # Aggregate market data
        market_data = {}
        for slot in inventory_slots:
            item_slug = slot.item_slug
            if item_slug not in market_data:
                item_data = item_manager.predefined_items.get(item_slug)
                market_data[item_slug] = {
                    "item_name": item_data.name if item_data else item_slug,
                    "base_price": item_data.base_price if item_data else 0,
                    "prices": [],
                    "stock_levels": [],
                    "shops": 0,
                }

            market_data[item_slug]["prices"].append(slot.current_price)
            market_data[item_slug]["stock_levels"].append(slot.current_stock)
            market_data[item_slug]["shops"] += 1

        # Calculate statistics
        for item_slug, data in market_data.items():
            prices = data["prices"]
            stocks = data["stock_levels"]

            data["min_price"] = min(prices)
            data["max_price"] = max(prices)
            data["avg_price"] = int(sum(prices) / len(prices))
            data["total_stock"] = sum(stocks)
            data["avg_stock"] = int(sum(stocks) / len(stocks))

            # Remove raw data for cleaner response
            del data["prices"]
            del data["stock_levels"]

        return {
            "market_data": market_data,
            "last_updated": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Market prices error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve market prices"
        )