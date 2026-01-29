# NPC Schedule System for AI-Powered Tuxemon
# Austin Kidwell | Intellegix | Mobile-First Pokemon-Style Game

import json
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, time
from enum import Enum

from pydantic import BaseModel, Field
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.game.models import NPC


class DayPeriod(str, Enum):
    """Time periods for NPC scheduling."""
    EARLY_MORNING = "early_morning"  # 6:00-9:00
    MORNING = "morning"              # 9:00-12:00
    AFTERNOON = "afternoon"          # 12:00-17:00
    EVENING = "evening"              # 17:00-21:00
    NIGHT = "night"                  # 21:00-6:00


class ApproachabilityLevel(str, Enum):
    """How approachable an NPC is during different activities."""
    FULLY_APPROACHABLE = "fully_approachable"      # Normal dialogue
    PARTIALLY_APPROACHABLE = "partially_approachable"  # Brief dialogue only
    NOT_APPROACHABLE = "not_approachable"          # Cannot interact


class ScheduleEntry(BaseModel):
    """Single schedule entry for an NPC."""
    time_period: DayPeriod
    location: Tuple[int, int] = Field(description="Map coordinates (x, y)")
    map_name: str = Field(description="Name of the map")
    activity: str = Field(description="What the NPC is doing")
    approachability: ApproachabilityLevel = ApproachabilityLevel.FULLY_APPROACHABLE
    facing_direction: str = Field(default="down", description="Direction NPC faces")
    dialogue_context: Optional[str] = Field(default=None, description="Context for AI dialogue")

    # Movement behavior
    patrol_radius: int = Field(default=0, description="Tiles NPC can wander from base position")
    movement_speed: float = Field(default=1.0, description="Movement speed multiplier")
    stays_in_place: bool = Field(default=True, description="Whether NPC stays at exact coordinates")


class NPCScheduleManager:
    """Manages NPC schedules and positions based on time of day."""

    def __init__(self):
        self.schedule_cache: Dict[str, Dict[DayPeriod, ScheduleEntry]] = {}
        self.position_cache: Dict[str, Tuple[int, int, str]] = {}  # npc_id -> (x, y, map)

    @staticmethod
    def get_current_day_period() -> DayPeriod:
        """Get the current time period based on system time."""
        current_time = datetime.now().time()

        if time(6, 0) <= current_time < time(9, 0):
            return DayPeriod.EARLY_MORNING
        elif time(9, 0) <= current_time < time(12, 0):
            return DayPeriod.MORNING
        elif time(12, 0) <= current_time < time(17, 0):
            return DayPeriod.AFTERNOON
        elif time(17, 0) <= current_time < time(21, 0):
            return DayPeriod.EVENING
        else:
            return DayPeriod.NIGHT

    def parse_npc_schedule(self, schedule_json: str) -> Dict[DayPeriod, ScheduleEntry]:
        """Parse NPC schedule from JSON string."""
        try:
            if not schedule_json or schedule_json == "{}":
                return self._get_default_schedule()

            schedule_data = json.loads(schedule_json)
            parsed_schedule = {}

            for period_str, entry_data in schedule_data.items():
                try:
                    period = DayPeriod(period_str)
                    entry = ScheduleEntry(**entry_data)
                    parsed_schedule[period] = entry
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid schedule entry for period {period_str}: {e}")
                    continue

            # Fill missing periods with default entries
            for period in DayPeriod:
                if period not in parsed_schedule:
                    parsed_schedule[period] = self._get_default_entry_for_period(period)

            return parsed_schedule

        except json.JSONDecodeError:
            logger.warning(f"Invalid schedule JSON: {schedule_json}")
            return self._get_default_schedule()

    def _get_default_schedule(self) -> Dict[DayPeriod, ScheduleEntry]:
        """Get a default schedule for NPCs without custom schedules."""
        return {
            period: self._get_default_entry_for_period(period)
            for period in DayPeriod
        }

    def _get_default_entry_for_period(self, period: DayPeriod) -> ScheduleEntry:
        """Get default schedule entry for a time period."""
        base_entry = {
            "time_period": period,
            "location": (10, 10),  # Default position
            "map_name": "starting_town",
            "facing_direction": "down",
            "patrol_radius": 1,
            "stays_in_place": False,
        }

        if period == DayPeriod.EARLY_MORNING:
            return ScheduleEntry(
                **base_entry,
                activity="waking_up",
                approachability=ApproachabilityLevel.PARTIALLY_APPROACHABLE,
                dialogue_context="just_woke_up"
            )
        elif period == DayPeriod.MORNING:
            return ScheduleEntry(
                **base_entry,
                activity="morning_routine",
                approachability=ApproachabilityLevel.FULLY_APPROACHABLE,
                dialogue_context="morning_energy"
            )
        elif period == DayPeriod.AFTERNOON:
            return ScheduleEntry(
                **base_entry,
                activity="daily_work",
                approachability=ApproachabilityLevel.FULLY_APPROACHABLE,
                dialogue_context="productive_afternoon"
            )
        elif period == DayPeriod.EVENING:
            return ScheduleEntry(
                **base_entry,
                activity="relaxing",
                approachability=ApproachabilityLevel.FULLY_APPROACHABLE,
                dialogue_context="winding_down"
            )
        else:  # NIGHT
            return ScheduleEntry(
                **base_entry,
                activity="sleeping",
                approachability=ApproachabilityLevel.NOT_APPROACHABLE,
                dialogue_context="sleepy",
                stays_in_place=True
            )

    async def update_npc_positions(self, db: AsyncSession) -> int:
        """Update all NPC positions based on current time. Returns number of NPCs updated."""
        current_period = self.get_current_day_period()

        try:
            # Get all NPCs
            result = await db.execute(select(NPC))
            npcs = result.scalars().all()

            updated_count = 0

            for npc in npcs:
                try:
                    # Parse the NPC's schedule
                    schedule = self.parse_npc_schedule(npc.schedule)

                    # Get current schedule entry
                    current_entry = schedule.get(current_period)
                    if not current_entry:
                        logger.warning(f"No schedule entry for {npc.slug} at period {current_period}")
                        continue

                    # Update NPC position and state
                    position_changed = await self._apply_schedule_entry(db, npc, current_entry)

                    if position_changed:
                        updated_count += 1

                        # Cache the new position
                        self.position_cache[npc.slug] = (
                            npc.position_x,
                            npc.position_y,
                            npc.map_name
                        )

                except Exception as e:
                    logger.error(f"Failed to update schedule for NPC {npc.slug}: {e}")
                    continue

            await db.commit()
            logger.info(f"Updated positions for {updated_count} NPCs for period {current_period}")
            return updated_count

        except Exception as e:
            logger.error(f"Failed to update NPC positions: {e}")
            await db.rollback()
            return 0

    async def _apply_schedule_entry(self, db: AsyncSession, npc: NPC, entry: ScheduleEntry) -> bool:
        """Apply a schedule entry to an NPC. Returns True if position changed."""
        position_changed = False

        # Check if position needs to be updated
        new_x, new_y = entry.location
        if npc.position_x != new_x or npc.position_y != new_y or npc.map_name != entry.map_name:
            npc.position_x = new_x
            npc.position_y = new_y
            npc.map_name = entry.map_name
            position_changed = True

        # Update facing direction
        if npc.facing_direction != entry.facing_direction:
            npc.facing_direction = entry.facing_direction
            position_changed = True

        # Update approachability
        approachable = entry.approachability != ApproachabilityLevel.NOT_APPROACHABLE
        if npc.approachable != approachable:
            npc.approachable = approachable
            position_changed = True

        return position_changed

    async def get_npc_current_state(self, db: AsyncSession, npc_slug: str) -> Optional[Dict[str, Any]]:
        """Get the current state of an NPC based on their schedule."""
        try:
            result = await db.execute(select(NPC).where(NPC.slug == npc_slug))
            npc = result.scalar_one_or_none()

            if not npc:
                return None

            # Parse schedule and get current entry
            schedule = self.parse_npc_schedule(npc.schedule)
            current_period = self.get_current_day_period()
            current_entry = schedule.get(current_period)

            if not current_entry:
                return None

            return {
                "npc_id": npc.id,
                "slug": npc.slug,
                "name": npc.name,
                "position": (npc.position_x, npc.position_y),
                "map_name": npc.map_name,
                "facing_direction": npc.facing_direction,
                "approachable": npc.approachable,
                "current_period": current_period,
                "activity": current_entry.activity,
                "dialogue_context": current_entry.dialogue_context,
                "can_patrol": not current_entry.stays_in_place,
                "patrol_radius": current_entry.patrol_radius,
            }

        except Exception as e:
            logger.error(f"Failed to get NPC state for {npc_slug}: {e}")
            return None

    async def get_npcs_in_area(
        self,
        db: AsyncSession,
        map_name: str,
        center_x: int,
        center_y: int,
        radius: int = 10
    ) -> List[Dict[str, Any]]:
        """Get all NPCs in a specific area based on their current schedules."""
        try:
            # Get NPCs on the specified map
            result = await db.execute(
                select(NPC).where(NPC.map_name == map_name)
            )
            npcs = result.scalars().all()

            current_period = self.get_current_day_period()
            npcs_in_area = []

            for npc in npcs:
                # Calculate distance from center
                distance = abs(npc.position_x - center_x) + abs(npc.position_y - center_y)

                if distance <= radius:
                    # Parse schedule to get current activity
                    schedule = self.parse_npc_schedule(npc.schedule)
                    current_entry = schedule.get(current_period)

                    npc_data = {
                        "id": str(npc.id),
                        "slug": npc.slug,
                        "name": npc.name,
                        "position": [npc.position_x, npc.position_y],
                        "spriteName": npc.sprite_name,
                        "approachable": npc.approachable,
                        "canBattle": npc.can_battle,
                        "isTrainer": npc.is_trainer,
                        "facingDirection": npc.facing_direction,
                        "distance": distance,
                    }

                    if current_entry:
                        npc_data.update({
                            "activity": current_entry.activity,
                            "dialogueContext": current_entry.dialogue_context,
                            "approachabilityLevel": current_entry.approachability.value,
                        })

                    npcs_in_area.append(npc_data)

            # Sort by distance
            npcs_in_area.sort(key=lambda x: x["distance"])

            return npcs_in_area

        except Exception as e:
            logger.error(f"Failed to get NPCs in area: {e}")
            return []

    def create_sample_schedule(self, npc_type: str = "villager") -> str:
        """Create a sample schedule for testing purposes."""
        if npc_type == "shopkeeper":
            schedule = {
                DayPeriod.EARLY_MORNING: ScheduleEntry(
                    time_period=DayPeriod.EARLY_MORNING,
                    location=(15, 8),
                    map_name="town_center",
                    activity="preparing_shop",
                    approachability=ApproachabilityLevel.PARTIALLY_APPROACHABLE,
                    facing_direction="down",
                    dialogue_context="getting_ready",
                    stays_in_place=True
                ),
                DayPeriod.MORNING: ScheduleEntry(
                    time_period=DayPeriod.MORNING,
                    location=(15, 8),
                    map_name="town_center",
                    activity="running_shop",
                    approachability=ApproachabilityLevel.FULLY_APPROACHABLE,
                    facing_direction="down",
                    dialogue_context="business_hours",
                    stays_in_place=True
                ),
                DayPeriod.AFTERNOON: ScheduleEntry(
                    time_period=DayPeriod.AFTERNOON,
                    location=(15, 8),
                    map_name="town_center",
                    activity="running_shop",
                    approachability=ApproachabilityLevel.FULLY_APPROACHABLE,
                    facing_direction="down",
                    dialogue_context="busy_afternoon",
                    stays_in_place=True
                ),
                DayPeriod.EVENING: ScheduleEntry(
                    time_period=DayPeriod.EVENING,
                    location=(12, 12),
                    map_name="town_center",
                    activity="socializing",
                    approachability=ApproachabilityLevel.FULLY_APPROACHABLE,
                    facing_direction="left",
                    dialogue_context="after_work",
                    patrol_radius=2,
                    stays_in_place=False
                ),
                DayPeriod.NIGHT: ScheduleEntry(
                    time_period=DayPeriod.NIGHT,
                    location=(10, 15),
                    map_name="residential_area",
                    activity="sleeping",
                    approachability=ApproachabilityLevel.NOT_APPROACHABLE,
                    facing_direction="up",
                    dialogue_context="sleepy",
                    stays_in_place=True
                ),
            }
        else:  # villager
            schedule = {
                DayPeriod.EARLY_MORNING: ScheduleEntry(
                    time_period=DayPeriod.EARLY_MORNING,
                    location=(8, 12),
                    map_name="residential_area",
                    activity="morning_walk",
                    approachability=ApproachabilityLevel.FULLY_APPROACHABLE,
                    facing_direction="right",
                    dialogue_context="fresh_morning",
                    patrol_radius=3,
                    stays_in_place=False
                ),
                DayPeriod.MORNING: ScheduleEntry(
                    time_period=DayPeriod.MORNING,
                    location=(12, 8),
                    map_name="town_center",
                    activity="shopping",
                    approachability=ApproachabilityLevel.FULLY_APPROACHABLE,
                    facing_direction="down",
                    dialogue_context="busy_morning",
                    patrol_radius=2,
                    stays_in_place=False
                ),
                DayPeriod.AFTERNOON: ScheduleEntry(
                    time_period=DayPeriod.AFTERNOON,
                    location=(20, 15),
                    map_name="park_area",
                    activity="relaxing",
                    approachability=ApproachabilityLevel.FULLY_APPROACHABLE,
                    facing_direction="left",
                    dialogue_context="peaceful_afternoon",
                    patrol_radius=4,
                    stays_in_place=False
                ),
                DayPeriod.EVENING: ScheduleEntry(
                    time_period=DayPeriod.EVENING,
                    location=(10, 10),
                    map_name="residential_area",
                    activity="cooking_dinner",
                    approachability=ApproachabilityLevel.PARTIALLY_APPROACHABLE,
                    facing_direction="up",
                    dialogue_context="dinner_time",
                    stays_in_place=True
                ),
                DayPeriod.NIGHT: ScheduleEntry(
                    time_period=DayPeriod.NIGHT,
                    location=(8, 8),
                    map_name="residential_area",
                    activity="sleeping",
                    approachability=ApproachabilityLevel.NOT_APPROACHABLE,
                    facing_direction="up",
                    dialogue_context="sleepy",
                    stays_in_place=True
                ),
            }

        # Convert to JSON
        schedule_dict = {
            period.value: entry.model_dump()
            for period, entry in schedule.items()
        }

        return json.dumps(schedule_dict, indent=2)


# Global schedule manager instance
npc_schedule_manager = NPCScheduleManager()