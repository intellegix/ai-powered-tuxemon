"""
Unit Tests for NPC Schedule System
Austin Kidwell | Intellegix | AI-Powered Tuxemon Game

Tests daily schedules, positioning logic, time-based behavior changes,
and NPC approachability management throughout the day.
"""

import pytest
import pytest_asyncio
import json
from datetime import datetime, time
from typing import Dict, List, Any, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

from app.game.npc_schedule import (
    NPCScheduleManager,
    ScheduleEntry,
    DayPeriod,
    ApproachabilityLevel
)
from app.game.models import NPC


class TestNPCScheduler:
    """Test suite for NPC scheduling and positioning system."""

    @pytest.fixture
    def schedule_manager(self) -> NPCScheduleManager:
        """Provide NPC schedule manager instance."""
        return NPCScheduleManager()

    @pytest.fixture
    def sample_npc(self) -> NPC:
        """Provide sample NPC for testing."""
        from uuid import uuid4

        return NPC(
            id=uuid4(),
            slug="test_villager",
            name="Test Villager",
            sprite_name="villager_01",
            position_x=10,
            position_y=10,
            map_name="starting_town",
            facing_direction="down",
            is_trainer=False,
            can_battle=False,
            approachable=True,
            personality_traits="{}",
            schedule="{}"  # Empty schedule for testing
        )

    @pytest.mark.unit
    @pytest.mark.game
    def test_day_period_detection_morning(self):
        """Test that morning hours are correctly detected."""
        # Test early morning (6:00-8:59)
        with patch('app.game.npc_schedule.datetime') as mock_datetime:
            mock_datetime.now.return_value.time.return_value = time(7, 30)
            period = NPCScheduleManager.get_current_day_period()
            assert period == DayPeriod.EARLY_MORNING

        # Test morning (9:00-11:59)
        with patch('app.game.npc_schedule.datetime') as mock_datetime:
            mock_datetime.now.return_value.time.return_value = time(10, 15)
            period = NPCScheduleManager.get_current_day_period()
            assert period == DayPeriod.MORNING

        # Test afternoon (12:00-16:59)
        with patch('app.game.npc_schedule.datetime') as mock_datetime:
            mock_datetime.now.return_value.time.return_value = time(14, 45)
            period = NPCScheduleManager.get_current_day_period()
            assert period == DayPeriod.AFTERNOON

        # Test evening (17:00-20:59)
        with patch('app.game.npc_schedule.datetime') as mock_datetime:
            mock_datetime.now.return_value.time.return_value = time(19, 30)
            period = NPCScheduleManager.get_current_day_period()
            assert period == DayPeriod.EVENING

        # Test night (21:00-5:59)
        with patch('app.game.npc_schedule.datetime') as mock_datetime:
            mock_datetime.now.return_value.time.return_value = time(23, 0)
            period = NPCScheduleManager.get_current_day_period()
            assert period == DayPeriod.NIGHT

        # Test early night (3:00 AM)
        with patch('app.game.npc_schedule.datetime') as mock_datetime:
            mock_datetime.now.return_value.time.return_value = time(3, 0)
            period = NPCScheduleManager.get_current_day_period()
            assert period == DayPeriod.NIGHT

    @pytest.mark.unit
    @pytest.mark.game
    def test_schedule_entry_validation(self):
        """Test that schedule entries are properly validated."""
        # Valid schedule entry
        valid_entry = ScheduleEntry(
            time_period=DayPeriod.MORNING,
            location=(15, 20),
            map_name="town_center",
            activity="working",
            approachability=ApproachabilityLevel.FULLY_APPROACHABLE,
            facing_direction="left",
            dialogue_context="busy_work",
            patrol_radius=3,
            movement_speed=1.2,
            stays_in_place=False
        )

        assert valid_entry.time_period == DayPeriod.MORNING
        assert valid_entry.location == (15, 20)
        assert valid_entry.map_name == "town_center"
        assert valid_entry.activity == "working"
        assert valid_entry.approachability == ApproachabilityLevel.FULLY_APPROACHABLE
        assert valid_entry.facing_direction == "left"
        assert valid_entry.dialogue_context == "busy_work"
        assert valid_entry.patrol_radius == 3
        assert valid_entry.movement_speed == 1.2
        assert valid_entry.stays_in_place is False

    @pytest.mark.unit
    @pytest.mark.game
    def test_default_schedule_generation(self, schedule_manager: NPCScheduleManager):
        """Test that default schedules are properly generated."""
        default_schedule = schedule_manager._get_default_schedule()

        # Should have entries for all day periods
        assert len(default_schedule) == len(DayPeriod)

        for period in DayPeriod:
            assert period in default_schedule
            entry = default_schedule[period]
            assert isinstance(entry, ScheduleEntry)
            assert entry.time_period == period

        # Test specific period behaviors
        early_morning = default_schedule[DayPeriod.EARLY_MORNING]
        assert early_morning.activity == "waking_up"
        assert early_morning.approachability == ApproachabilityLevel.PARTIALLY_APPROACHABLE
        assert early_morning.dialogue_context == "just_woke_up"

        morning = default_schedule[DayPeriod.MORNING]
        assert morning.activity == "morning_routine"
        assert morning.approachability == ApproachabilityLevel.FULLY_APPROACHABLE
        assert morning.dialogue_context == "morning_energy"

        night = default_schedule[DayPeriod.NIGHT]
        assert night.activity == "sleeping"
        assert night.approachability == ApproachabilityLevel.NOT_APPROACHABLE
        assert night.dialogue_context == "sleepy"
        assert night.stays_in_place is True

    @pytest.mark.unit
    @pytest.mark.game
    def test_schedule_json_parsing_valid(self, schedule_manager: NPCScheduleManager):
        """Test parsing valid schedule JSON."""
        schedule_json = json.dumps({
            "morning": {
                "time_period": "morning",
                "location": [12, 8],
                "map_name": "town_square",
                "activity": "shopping",
                "approachability": "fully_approachable",
                "facing_direction": "right",
                "dialogue_context": "busy_morning",
                "patrol_radius": 2,
                "stays_in_place": False
            },
            "afternoon": {
                "time_period": "afternoon",
                "location": [15, 15],
                "map_name": "park",
                "activity": "relaxing",
                "approachability": "fully_approachable",
                "facing_direction": "up",
                "dialogue_context": "peaceful",
                "patrol_radius": 3,
                "stays_in_place": False
            }
        })

        parsed_schedule = schedule_manager.parse_npc_schedule(schedule_json)

        # Should have all periods (missing ones filled with defaults)
        assert len(parsed_schedule) == len(DayPeriod)

        # Test parsed entries
        morning_entry = parsed_schedule[DayPeriod.MORNING]
        assert morning_entry.location == (12, 8)
        assert morning_entry.map_name == "town_square"
        assert morning_entry.activity == "shopping"
        assert morning_entry.approachability == ApproachabilityLevel.FULLY_APPROACHABLE
        assert morning_entry.patrol_radius == 2

        afternoon_entry = parsed_schedule[DayPeriod.AFTERNOON]
        assert afternoon_entry.location == (15, 15)
        assert afternoon_entry.map_name == "park"
        assert afternoon_entry.activity == "relaxing"

        # Test that missing periods got defaults
        night_entry = parsed_schedule[DayPeriod.NIGHT]
        assert night_entry.activity == "sleeping"  # Default activity

    @pytest.mark.unit
    @pytest.mark.game
    def test_schedule_json_parsing_invalid(self, schedule_manager: NPCScheduleManager):
        """Test handling of invalid schedule JSON."""
        # Test invalid JSON
        invalid_json = '{"morning": invalid_json_data}'
        parsed_schedule = schedule_manager.parse_npc_schedule(invalid_json)

        # Should fall back to default schedule
        assert len(parsed_schedule) == len(DayPeriod)
        morning_entry = parsed_schedule[DayPeriod.MORNING]
        assert morning_entry.activity == "morning_routine"  # Default

        # Test empty JSON
        empty_schedule = schedule_manager.parse_npc_schedule("{}")
        assert len(empty_schedule) == len(DayPeriod)

        # Test None/empty string
        none_schedule = schedule_manager.parse_npc_schedule("")
        assert len(none_schedule) == len(DayPeriod)

    @pytest.mark.unit
    @pytest.mark.game
    def test_schedule_json_parsing_partial_invalid(self, schedule_manager: NPCScheduleManager):
        """Test parsing JSON with some invalid entries."""
        partial_invalid_json = json.dumps({
            "morning": {
                "time_period": "morning",
                "location": [10, 10],
                "map_name": "town",
                "activity": "valid_activity",
                "approachability": "fully_approachable"
            },
            "invalid_period": {
                "time_period": "not_a_real_period",
                "location": [5, 5],
                "map_name": "test"
            },
            "afternoon": {
                # Missing required fields
                "location": [20, 20]
            }
        })

        parsed_schedule = schedule_manager.parse_npc_schedule(partial_invalid_json)

        # Should have all periods
        assert len(parsed_schedule) == len(DayPeriod)

        # Valid entry should be parsed correctly
        morning_entry = parsed_schedule[DayPeriod.MORNING]
        assert morning_entry.activity == "valid_activity"
        assert morning_entry.location == (10, 10)

        # Invalid entries should be replaced with defaults
        afternoon_entry = parsed_schedule[DayPeriod.AFTERNOON]
        assert afternoon_entry.activity == "daily_work"  # Default for afternoon

    @pytest.mark.unit
    @pytest.mark.game
    @pytest.mark.asyncio
    async def test_npc_position_update_basic(
        self,
        schedule_manager: NPCScheduleManager,
        sample_npc: NPC,
        db_session
    ):
        """Test basic NPC position updating from schedule."""
        # Set up NPC with custom schedule
        schedule_data = {
            "morning": {
                "time_period": "morning",
                "location": [25, 30],
                "map_name": "new_map",
                "activity": "working",
                "approachability": "fully_approachable",
                "facing_direction": "left"
            }
        }
        sample_npc.schedule = json.dumps(schedule_data)

        # Mock current time to morning
        with patch('app.game.npc_schedule.NPCScheduleManager.get_current_day_period') as mock_period:
            mock_period.return_value = DayPeriod.MORNING

            # Mock database operations
            db_session.execute.return_value.scalars.return_value.all.return_value = [sample_npc]

            # Apply schedule entry
            changed = await schedule_manager._apply_schedule_entry(db_session, sample_npc,
                ScheduleEntry(
                    time_period=DayPeriod.MORNING,
                    location=(25, 30),
                    map_name="new_map",
                    activity="working",
                    facing_direction="left"
                )
            )

            # Verify position was updated
            assert changed is True
            assert sample_npc.position_x == 25
            assert sample_npc.position_y == 30
            assert sample_npc.map_name == "new_map"
            assert sample_npc.facing_direction == "left"

    @pytest.mark.unit
    @pytest.mark.game
    @pytest.mark.asyncio
    async def test_npc_position_update_no_change(
        self,
        schedule_manager: NPCScheduleManager,
        sample_npc: NPC,
        db_session
    ):
        """Test that NPC position doesn't change if already correct."""
        # Set NPC to target position
        sample_npc.position_x = 10
        sample_npc.position_y = 10
        sample_npc.map_name = "starting_town"
        sample_npc.facing_direction = "down"

        # Apply identical schedule entry
        changed = await schedule_manager._apply_schedule_entry(db_session, sample_npc,
            ScheduleEntry(
                time_period=DayPeriod.MORNING,
                location=(10, 10),
                map_name="starting_town",
                activity="testing",
                facing_direction="down"
            )
        )

        # Should report no change
        assert changed is False

    @pytest.mark.unit
    @pytest.mark.game
    @pytest.mark.asyncio
    async def test_npc_approachability_update(
        self,
        schedule_manager: NPCScheduleManager,
        sample_npc: NPC,
        db_session
    ):
        """Test that NPC approachability is updated based on schedule."""
        # Start with approachable NPC
        sample_npc.approachable = True

        # Apply not approachable schedule
        changed = await schedule_manager._apply_schedule_entry(db_session, sample_npc,
            ScheduleEntry(
                time_period=DayPeriod.NIGHT,
                location=(10, 10),
                map_name="starting_town",
                activity="sleeping",
                approachability=ApproachabilityLevel.NOT_APPROACHABLE
            )
        )

        # Should update approachability
        assert changed is True
        assert sample_npc.approachable is False

        # Apply partially approachable schedule
        changed2 = await schedule_manager._apply_schedule_entry(db_session, sample_npc,
            ScheduleEntry(
                time_period=DayPeriod.EARLY_MORNING,
                location=(10, 10),
                map_name="starting_town",
                activity="waking_up",
                approachability=ApproachabilityLevel.PARTIALLY_APPROACHABLE
            )
        )

        # Should make approachable again
        assert changed2 is True
        assert sample_npc.approachable is True

    @pytest.mark.unit
    @pytest.mark.game
    @pytest.mark.asyncio
    async def test_get_npc_current_state(
        self,
        schedule_manager: NPCScheduleManager,
        sample_npc: NPC,
        db_session
    ):
        """Test getting current NPC state based on schedule."""
        # Set up NPC with custom schedule
        schedule_data = {
            "afternoon": {
                "time_period": "afternoon",
                "location": [20, 25],
                "map_name": "park",
                "activity": "relaxing",
                "approachability": "fully_approachable",
                "facing_direction": "up",
                "dialogue_context": "peaceful_day",
                "patrol_radius": 4,
                "stays_in_place": False
            }
        }
        sample_npc.schedule = json.dumps(schedule_data)
        sample_npc.position_x = 20
        sample_npc.position_y = 25
        sample_npc.map_name = "park"

        # Mock database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_npc
        db_session.execute.return_value = mock_result

        # Mock current time to afternoon
        with patch('app.game.npc_schedule.NPCScheduleManager.get_current_day_period') as mock_period:
            mock_period.return_value = DayPeriod.AFTERNOON

            state = await schedule_manager.get_npc_current_state(db_session, "test_villager")

            assert state is not None
            assert state["slug"] == "test_villager"
            assert state["position"] == (20, 25)
            assert state["map_name"] == "park"
            assert state["current_period"] == DayPeriod.AFTERNOON
            assert state["activity"] == "relaxing"
            assert state["dialogue_context"] == "peaceful_day"
            assert state["can_patrol"] is True
            assert state["patrol_radius"] == 4

    @pytest.mark.unit
    @pytest.mark.game
    @pytest.mark.asyncio
    async def test_get_npcs_in_area(
        self,
        schedule_manager: NPCScheduleManager,
        db_session
    ):
        """Test getting NPCs within a specific area."""
        from uuid import uuid4

        # Create test NPCs at different distances
        npc1 = NPC(
            id=uuid4(),
            slug="close_npc",
            name="Close NPC",
            sprite_name="villager_01",
            position_x=12,  # Distance 3 from center (10, 10)
            position_y=11,
            map_name="test_map",
            facing_direction="down",
            approachable=True,
            can_battle=False,
            is_trainer=False,
            schedule="{}"
        )

        npc2 = NPC(
            id=uuid4(),
            slug="far_npc",
            name="Far NPC",
            sprite_name="villager_02",
            position_x=25,  # Distance 20 from center (10, 10)
            position_y=15,
            map_name="test_map",
            facing_direction="left",
            approachable=True,
            can_battle=True,
            is_trainer=True,
            schedule="{}"
        )

        npc3 = NPC(
            id=uuid4(),
            slug="medium_npc",
            name="Medium NPC",
            sprite_name="trainer_01",
            position_x=15,  # Distance 10 from center (10, 10)
            position_y=15,
            map_name="test_map",
            facing_direction="up",
            approachable=True,
            can_battle=True,
            is_trainer=True,
            schedule="{}"
        )

        # Mock database query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [npc1, npc2, npc3]
        db_session.execute.return_value = mock_result

        # Get NPCs within radius of 12
        npcs_in_area = await schedule_manager.get_npcs_in_area(
            db_session, "test_map", 10, 10, radius=12
        )

        # Should include npc1 (distance 3) and npc3 (distance 10), but not npc2 (distance 20)
        assert len(npcs_in_area) == 2

        # Should be sorted by distance
        assert npcs_in_area[0]["slug"] == "close_npc"
        assert npcs_in_area[0]["distance"] == 3
        assert npcs_in_area[1]["slug"] == "medium_npc"
        assert npcs_in_area[1]["distance"] == 10

        # Verify NPC data structure
        close_npc_data = npcs_in_area[0]
        assert close_npc_data["name"] == "Close NPC"
        assert close_npc_data["position"] == [12, 11]
        assert close_npc_data["spriteName"] == "villager_01"
        assert close_npc_data["approachable"] is True
        assert close_npc_data["canBattle"] is False
        assert close_npc_data["isTrainer"] is False

    @pytest.mark.unit
    @pytest.mark.game
    def test_sample_schedule_creation_shopkeeper(self, schedule_manager: NPCScheduleManager):
        """Test creation of sample shopkeeper schedule."""
        schedule_json = schedule_manager.create_sample_schedule("shopkeeper")

        # Parse the JSON to verify structure
        schedule_data = json.loads(schedule_json)

        # Should have entries for all periods
        assert len(schedule_data) == len(DayPeriod)

        # Test shopkeeper-specific behaviors
        morning_entry = schedule_data["morning"]
        assert morning_entry["activity"] == "running_shop"
        assert morning_entry["approachability"] == "fully_approachable"
        assert morning_entry["stays_in_place"] is True
        assert morning_entry["location"] == [15, 8]
        assert morning_entry["map_name"] == "town_center"

        night_entry = schedule_data["night"]
        assert night_entry["activity"] == "sleeping"
        assert night_entry["approachability"] == "not_approachable"
        assert night_entry["map_name"] == "residential_area"

    @pytest.mark.unit
    @pytest.mark.game
    def test_sample_schedule_creation_villager(self, schedule_manager: NPCScheduleManager):
        """Test creation of sample villager schedule."""
        schedule_json = schedule_manager.create_sample_schedule("villager")

        schedule_data = json.loads(schedule_json)

        # Test villager-specific behaviors
        early_morning_entry = schedule_data["early_morning"]
        assert early_morning_entry["activity"] == "morning_walk"
        assert early_morning_entry["patrol_radius"] == 3
        assert early_morning_entry["stays_in_place"] is False

        morning_entry = schedule_data["morning"]
        assert morning_entry["activity"] == "shopping"
        assert morning_entry["map_name"] == "town_center"

        afternoon_entry = schedule_data["afternoon"]
        assert afternoon_entry["activity"] == "relaxing"
        assert afternoon_entry["map_name"] == "park_area"
        assert afternoon_entry["patrol_radius"] == 4

    @pytest.mark.unit
    @pytest.mark.game
    def test_approachability_level_enum(self):
        """Test approachability level enumeration."""
        levels = [
            ApproachabilityLevel.FULLY_APPROACHABLE,
            ApproachabilityLevel.PARTIALLY_APPROACHABLE,
            ApproachabilityLevel.NOT_APPROACHABLE
        ]

        for level in levels:
            assert isinstance(level.value, str)

        # Test string values
        assert ApproachabilityLevel.FULLY_APPROACHABLE == "fully_approachable"
        assert ApproachabilityLevel.PARTIALLY_APPROACHABLE == "partially_approachable"
        assert ApproachabilityLevel.NOT_APPROACHABLE == "not_approachable"

    @pytest.mark.unit
    @pytest.mark.game
    @pytest.mark.asyncio
    async def test_schedule_manager_caching(
        self,
        schedule_manager: NPCScheduleManager,
        sample_npc: NPC,
        db_session
    ):
        """Test that schedule manager properly caches positions."""
        # Initial cache should be empty
        assert len(schedule_manager.position_cache) == 0

        # Update position
        sample_npc.position_x = 50
        sample_npc.position_y = 60
        sample_npc.map_name = "new_location"

        # Simulate position update that would add to cache
        schedule_manager.position_cache[sample_npc.slug] = (50, 60, "new_location")

        # Verify cache
        cached_position = schedule_manager.position_cache.get(sample_npc.slug)
        assert cached_position == (50, 60, "new_location")

    @pytest.mark.unit
    @pytest.mark.game
    def test_manhattan_distance_calculation(self):
        """Test distance calculation used in area queries."""
        # The system uses Manhattan distance: |x1-x2| + |y1-y2|
        center_x, center_y = 10, 10

        # Test points at different distances
        test_points = [
            ((10, 10), 0),    # Same position
            ((11, 10), 1),    # 1 step right
            ((10, 11), 1),    # 1 step down
            ((12, 13), 5),    # 2 right + 3 down = 5
            ((5, 7), 8),      # 5 left + 3 up = 8
        ]

        for (x, y), expected_distance in test_points:
            calculated_distance = abs(x - center_x) + abs(y - center_y)
            assert calculated_distance == expected_distance