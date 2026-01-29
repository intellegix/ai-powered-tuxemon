# Background Tasks for AI-Powered Tuxemon
# Austin Kidwell | Intellegix | Mobile-First Pokemon-Style Game

import asyncio
from typing import Optional
from datetime import datetime, timedelta

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.game.npc_schedule import npc_schedule_manager
from app.config import get_settings

settings = get_settings()


class BackgroundTaskManager:
    """Manages background tasks for the game."""

    def __init__(self):
        self.running = False
        self.tasks: list[asyncio.Task] = []
        self.last_schedule_update = datetime.utcnow()
        self.schedule_update_interval = timedelta(minutes=5)  # Update every 5 minutes

    async def start(self):
        """Start all background tasks."""
        if self.running:
            logger.warning("Background tasks already running")
            return

        self.running = True
        logger.info("Starting background tasks...")

        # Start individual task loops
        self.tasks = [
            asyncio.create_task(self._npc_schedule_updater()),
            asyncio.create_task(self._cleanup_expired_data()),
            asyncio.create_task(self._cost_monitor()),
        ]

        logger.info(f"Started {len(self.tasks)} background tasks")

    async def stop(self):
        """Stop all background tasks."""
        if not self.running:
            return

        logger.info("Stopping background tasks...")
        self.running = False

        # Cancel all tasks
        for task in self.tasks:
            task.cancel()

        # Wait for tasks to finish
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()

        logger.info("Background tasks stopped")

    async def _npc_schedule_updater(self):
        """Background task to update NPC positions based on schedules."""
        logger.info("NPC schedule updater started")

        while self.running:
            try:
                current_time = datetime.utcnow()

                # Check if it's time to update schedules
                if current_time - self.last_schedule_update >= self.schedule_update_interval:
                    async with AsyncSessionLocal() as db:
                        try:
                            updated_count = await npc_schedule_manager.update_npc_positions(db)
                            current_period = npc_schedule_manager.get_current_day_period()

                            if updated_count > 0:
                                logger.info(f"Updated {updated_count} NPCs for period {current_period}")

                            self.last_schedule_update = current_time

                        except Exception as e:
                            logger.error(f"Failed to update NPC schedules: {e}")
                            await db.rollback()

                # Sleep for 1 minute before checking again
                await asyncio.sleep(60)

            except asyncio.CancelledError:
                logger.info("NPC schedule updater cancelled")
                break
            except Exception as e:
                logger.error(f"Error in NPC schedule updater: {e}")
                # Continue running even if there's an error
                await asyncio.sleep(60)

    async def _cleanup_expired_data(self):
        """Background task to clean up expired data."""
        logger.info("Data cleanup task started")

        while self.running:
            try:
                # Run cleanup every hour
                await asyncio.sleep(3600)

                if not self.running:
                    break

                async with AsyncSessionLocal() as db:
                    try:
                        # Clean up old combat sessions
                        await self._cleanup_old_combat_sessions(db)

                        # Clean up old cached data
                        await self._cleanup_old_cached_data()

                        logger.info("Completed data cleanup")

                    except Exception as e:
                        logger.error(f"Error during data cleanup: {e}")
                        await db.rollback()

            except asyncio.CancelledError:
                logger.info("Data cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in data cleanup task: {e}")

    async def _cleanup_old_combat_sessions(self, db: AsyncSession):
        """Clean up combat sessions older than 24 hours."""
        from sqlmodel import select, delete
        from app.game.models import CombatSession

        cutoff_time = datetime.utcnow() - timedelta(hours=24)

        # Delete old combat sessions
        result = await db.execute(
            delete(CombatSession).where(
                CombatSession.started_at < cutoff_time,
                CombatSession.ended_at.is_not(None)
            )
        )

        deleted_count = result.rowcount
        if deleted_count > 0:
            await db.commit()
            logger.info(f"Cleaned up {deleted_count} old combat sessions")

    async def _cleanup_old_cached_data(self):
        """Clean up old cached data from Redis."""
        from app.database import redis_client

        try:
            # Clean up old dialogue cache entries
            # This is handled by Redis TTL, but we could add additional cleanup here

            # Clean up old cost tracking data (keep last 7 days)
            import datetime as dt
            cutoff_date = (dt.datetime.utcnow() - timedelta(days=7)).date()

            # Get all cost tracking keys
            pattern = "ai_cost_tracker"
            keys = await redis_client.hkeys(pattern)

            deleted_count = 0
            for key in keys:
                try:
                    key_date = dt.datetime.fromisoformat(key).date()
                    if key_date < cutoff_date:
                        await redis_client.hdel(pattern, key)
                        deleted_count += 1
                except (ValueError, TypeError):
                    # Invalid date format, skip
                    continue

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old cost tracking entries")

        except Exception as e:
            logger.error(f"Error cleaning cached data: {e}")

    async def _cost_monitor(self):
        """Background task to monitor AI costs and send alerts."""
        logger.info("Cost monitor started")

        while self.running:
            try:
                # Check costs every 30 minutes
                await asyncio.sleep(1800)

                if not self.running:
                    break

                from app.ai.ai_manager import DailyCostTracker
                from app.database import redis_client

                cost_tracker = DailyCostTracker()

                # Get today's cost
                today = datetime.utcnow().date().isoformat()
                daily_cost = await redis_client.hget(cost_tracker.redis_key, today)

                if daily_cost:
                    current_cost = float(daily_cost)
                    max_cost = settings.max_cost_per_day_usd

                    # Alert at 80% and 90% thresholds
                    if current_cost >= max_cost * 0.9:
                        logger.warning(f"🚨 Daily AI cost at {current_cost:.2f} (90% of limit)")
                    elif current_cost >= max_cost * 0.8:
                        logger.warning(f"⚠️ Daily AI cost at {current_cost:.2f} (80% of limit)")

                    # Log current cost for monitoring
                    logger.info(f"💰 Current daily AI cost: ${current_cost:.2f} / ${max_cost:.2f}")

            except asyncio.CancelledError:
                logger.info("Cost monitor cancelled")
                break
            except Exception as e:
                logger.error(f"Error in cost monitor: {e}")


# Global background task manager
background_tasks = BackgroundTaskManager()