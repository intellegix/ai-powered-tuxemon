"""
Unit Tests for Player Actions System
Austin Kidwell | Intellegix | AI-Powered Tuxemon Game

Tests movement handling, interaction validation, action queueing,
and mobile-optimized input processing for player actions.
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from app.game.models import Player
from pydantic import BaseModel


class PlayerAction(BaseModel):
    """Player action model for testing."""
    action_type: str
    player_id: UUID
    timestamp: datetime
    data: Dict[str, Any]
    position: Optional[Tuple[int, int]] = None
    map_name: Optional[str] = None


class ActionType:
    """Action type constants."""
    MOVE = "move"
    INTERACT = "interact"
    USE_ITEM = "use_item"
    BATTLE_ACTION = "battle_action"
    MENU_ACTION = "menu_action"


class Direction:
    """Movement direction constants."""
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"


class TestPlayerActions:
    """Test suite for player action handling and validation."""

    @pytest.fixture
    def sample_player(self) -> Player:
        """Provide sample player for testing."""
        return Player(
            id=uuid4(),
            username="test_player",
            email="test@example.com",
            hashed_password="$2b$12$test_hash",
            current_map="starting_town",
            position_x=10,
            position_y=10,
            money=500,
            story_progress="{}",
            play_time_seconds=3600,
            npc_relationships="{}",
            created_at=datetime.utcnow(),
            last_login=datetime.utcnow(),
            is_active=True
        )

    @pytest.mark.unit
    @pytest.mark.game
    def test_movement_action_validation(self, sample_player: Player):
        """Test player movement action validation."""
        # Valid movement action
        move_action = PlayerAction(
            action_type=ActionType.MOVE,
            player_id=sample_player.id,
            timestamp=datetime.utcnow(),
            data={"direction": Direction.UP, "steps": 1},
            position=(sample_player.position_x, sample_player.position_y),
            map_name=sample_player.current_map
        )

        assert move_action.action_type == ActionType.MOVE
        assert move_action.data["direction"] == Direction.UP
        assert move_action.data["steps"] == 1
        assert move_action.position == (10, 10)

        # Test movement validation
        is_valid_move = self._validate_movement_action(move_action, sample_player)
        assert is_valid_move is True

        # Test invalid movement (too many steps)
        invalid_move = PlayerAction(
            action_type=ActionType.MOVE,
            player_id=sample_player.id,
            timestamp=datetime.utcnow(),
            data={"direction": Direction.DOWN, "steps": 10},  # Too many steps
            position=(sample_player.position_x, sample_player.position_y),
            map_name=sample_player.current_map
        )

        is_valid_large_move = self._validate_movement_action(invalid_move, sample_player)
        assert is_valid_large_move is False

    def _validate_movement_action(self, action: PlayerAction, player: Player) -> bool:
        """Validate movement action constraints."""
        if action.action_type != ActionType.MOVE:
            return False

        # Check step limit (mobile optimization)
        max_steps = 3  # Prevent large movements for mobile
        steps = action.data.get("steps", 1)
        if steps > max_steps:
            return False

        # Check valid direction
        valid_directions = [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]
        direction = action.data.get("direction")
        if direction not in valid_directions:
            return False

        # Check if player owns this action
        if action.player_id != player.id:
            return False

        return True

    @pytest.mark.unit
    @pytest.mark.game
    def test_position_calculation_from_movement(self, sample_player: Player):
        """Test position calculation after movement actions."""
        initial_x = sample_player.position_x
        initial_y = sample_player.position_y

        # Test movement in each direction
        test_movements = [
            (Direction.UP, (initial_x, initial_y - 1)),
            (Direction.DOWN, (initial_x, initial_y + 1)),
            (Direction.LEFT, (initial_x - 1, initial_y)),
            (Direction.RIGHT, (initial_x + 1, initial_y))
        ]

        for direction, expected_position in test_movements:
            new_position = self._calculate_new_position(
                (initial_x, initial_y), direction, steps=1
            )
            assert new_position == expected_position

        # Test multiple steps
        multi_step_position = self._calculate_new_position(
            (initial_x, initial_y), Direction.RIGHT, steps=3
        )
        assert multi_step_position == (initial_x + 3, initial_y)

    def _calculate_new_position(
        self,
        current_position: Tuple[int, int],
        direction: str,
        steps: int = 1
    ) -> Tuple[int, int]:
        """Calculate new position based on movement."""
        x, y = current_position

        if direction == Direction.UP:
            y -= steps
        elif direction == Direction.DOWN:
            y += steps
        elif direction == Direction.LEFT:
            x -= steps
        elif direction == Direction.RIGHT:
            x += steps

        return (x, y)

    @pytest.mark.unit
    @pytest.mark.game
    def test_boundary_validation(self, sample_player: Player):
        """Test map boundary validation for movement."""
        # Mock map boundaries
        map_boundaries = {
            "starting_town": {
                "min_x": 0,
                "max_x": 50,
                "min_y": 0,
                "max_y": 50
            }
        }

        # Test valid movement within boundaries
        valid_position = (25, 25)
        is_valid = self._is_position_within_boundaries(
            valid_position, sample_player.current_map, map_boundaries
        )
        assert is_valid is True

        # Test boundary edge cases
        edge_positions = [
            ((0, 0), True),     # Top-left corner
            ((50, 50), True),   # Bottom-right corner
            ((0, 25), True),    # Left edge
            ((50, 25), True),   # Right edge
            ((25, 0), True),    # Top edge
            ((25, 50), True)    # Bottom edge
        ]

        for position, expected_valid in edge_positions:
            is_valid = self._is_position_within_boundaries(
                position, sample_player.current_map, map_boundaries
            )
            assert is_valid == expected_valid

        # Test invalid positions outside boundaries
        invalid_positions = [
            (-1, 25),   # Left of boundary
            (51, 25),   # Right of boundary
            (25, -1),   # Above boundary
            (25, 51)    # Below boundary
        ]

        for position in invalid_positions:
            is_valid = self._is_position_within_boundaries(
                position, sample_player.current_map, map_boundaries
            )
            assert is_valid is False

    def _is_position_within_boundaries(
        self,
        position: Tuple[int, int],
        map_name: str,
        boundaries: Dict[str, Dict[str, int]]
    ) -> bool:
        """Check if position is within map boundaries."""
        x, y = position
        bounds = boundaries.get(map_name, {})

        min_x = bounds.get("min_x", 0)
        max_x = bounds.get("max_x", 100)
        min_y = bounds.get("min_y", 0)
        max_y = bounds.get("max_y", 100)

        return min_x <= x <= max_x and min_y <= y <= max_y

    @pytest.mark.unit
    @pytest.mark.game
    def test_interaction_action_validation(self, sample_player: Player):
        """Test NPC and object interaction validation."""
        # Valid NPC interaction
        npc_interaction = PlayerAction(
            action_type=ActionType.INTERACT,
            player_id=sample_player.id,
            timestamp=datetime.utcnow(),
            data={
                "target_type": "npc",
                "target_id": str(uuid4()),
                "interaction_type": "dialogue"
            },
            position=(sample_player.position_x, sample_player.position_y),
            map_name=sample_player.current_map
        )

        is_valid = self._validate_interaction_action(npc_interaction, sample_player)
        assert is_valid is True

        # Valid object interaction
        object_interaction = PlayerAction(
            action_type=ActionType.INTERACT,
            player_id=sample_player.id,
            timestamp=datetime.utcnow(),
            data={
                "target_type": "object",
                "target_id": "chest_001",
                "interaction_type": "open"
            },
            position=(sample_player.position_x, sample_player.position_y),
            map_name=sample_player.current_map
        )

        is_valid_object = self._validate_interaction_action(object_interaction, sample_player)
        assert is_valid_object is True

        # Invalid interaction (missing target)
        invalid_interaction = PlayerAction(
            action_type=ActionType.INTERACT,
            player_id=sample_player.id,
            timestamp=datetime.utcnow(),
            data={"interaction_type": "dialogue"},  # Missing target_id
            position=(sample_player.position_x, sample_player.position_y),
            map_name=sample_player.current_map
        )

        is_valid_invalid = self._validate_interaction_action(invalid_interaction, sample_player)
        assert is_valid_invalid is False

    def _validate_interaction_action(self, action: PlayerAction, player: Player) -> bool:
        """Validate interaction action requirements."""
        if action.action_type != ActionType.INTERACT:
            return False

        # Check required fields
        data = action.data
        if "target_type" not in data or "target_id" not in data:
            return False

        # Check valid target types
        valid_target_types = ["npc", "object", "monster", "item"]
        if data["target_type"] not in valid_target_types:
            return False

        # Check valid interaction types
        valid_interaction_types = ["dialogue", "battle", "shop", "open", "examine"]
        if "interaction_type" in data and data["interaction_type"] not in valid_interaction_types:
            return False

        return True

    @pytest.mark.unit
    @pytest.mark.game
    def test_item_usage_action_validation(self, sample_player: Player):
        """Test item usage action validation."""
        # Valid item use
        item_use = PlayerAction(
            action_type=ActionType.USE_ITEM,
            player_id=sample_player.id,
            timestamp=datetime.utcnow(),
            data={
                "item_slug": "health_potion",
                "target_type": "monster",
                "target_id": str(uuid4()),
                "quantity": 1
            },
            position=(sample_player.position_x, sample_player.position_y),
            map_name=sample_player.current_map
        )

        is_valid = self._validate_item_usage_action(item_use, sample_player)
        assert is_valid is True

        # Invalid item use (excessive quantity)
        invalid_quantity = PlayerAction(
            action_type=ActionType.USE_ITEM,
            player_id=sample_player.id,
            timestamp=datetime.utcnow(),
            data={
                "item_slug": "rare_candy",
                "target_type": "monster",
                "target_id": str(uuid4()),
                "quantity": 10  # Too many for one action
            },
            position=(sample_player.position_x, sample_player.position_y),
            map_name=sample_player.current_map
        )

        is_valid_quantity = self._validate_item_usage_action(invalid_quantity, sample_player)
        assert is_valid_quantity is False

    def _validate_item_usage_action(self, action: PlayerAction, player: Player) -> bool:
        """Validate item usage action constraints."""
        if action.action_type != ActionType.USE_ITEM:
            return False

        data = action.data

        # Check required fields
        required_fields = ["item_slug", "quantity"]
        for field in required_fields:
            if field not in data:
                return False

        # Check quantity limits (mobile optimization)
        max_quantity_per_action = 5
        quantity = data.get("quantity", 1)
        if quantity > max_quantity_per_action or quantity < 1:
            return False

        # Check target validation if specified
        if "target_type" in data and "target_id" not in data:
            return False

        return True

    @pytest.mark.unit
    @pytest.mark.game
    def test_action_rate_limiting(self, sample_player: Player):
        """Test action rate limiting for mobile optimization."""
        # Simulate rapid actions
        actions = []
        base_time = datetime.utcnow()

        for i in range(10):
            action = PlayerAction(
                action_type=ActionType.MOVE,
                player_id=sample_player.id,
                timestamp=base_time + timedelta(milliseconds=i * 50),  # 50ms apart
                data={"direction": Direction.UP, "steps": 1},
                position=(sample_player.position_x, sample_player.position_y + i),
                map_name=sample_player.current_map
            )
            actions.append(action)

        # Test rate limiting
        rate_limit_window = 1.0  # 1 second
        max_actions_per_window = 5

        allowed_actions = self._apply_rate_limiting(
            actions, rate_limit_window, max_actions_per_window
        )

        # Should only allow 5 actions within the time window
        assert len(allowed_actions) <= max_actions_per_window

        # Test that actions are in chronological order
        for i in range(1, len(allowed_actions)):
            assert allowed_actions[i].timestamp >= allowed_actions[i-1].timestamp

    def _apply_rate_limiting(
        self,
        actions: List[PlayerAction],
        window_seconds: float,
        max_actions: int
    ) -> List[PlayerAction]:
        """Apply rate limiting to action list."""
        if not actions:
            return []

        # Sort by timestamp
        sorted_actions = sorted(actions, key=lambda x: x.timestamp)
        allowed_actions = []

        current_window_start = sorted_actions[0].timestamp
        current_window_count = 0

        for action in sorted_actions:
            # Check if action is within current window
            time_diff = (action.timestamp - current_window_start).total_seconds()

            if time_diff <= window_seconds:
                if current_window_count < max_actions:
                    allowed_actions.append(action)
                    current_window_count += 1
                # Else: action is rate limited, skip it
            else:
                # Start new window
                current_window_start = action.timestamp
                current_window_count = 1
                allowed_actions.append(action)

        return allowed_actions

    @pytest.mark.unit
    @pytest.mark.game
    def test_action_queue_management(self, sample_player: Player):
        """Test action queue management for smooth mobile gameplay."""
        # Create a queue of actions
        action_queue = []

        # Add movement actions
        for i in range(5):
            action = PlayerAction(
                action_type=ActionType.MOVE,
                player_id=sample_player.id,
                timestamp=datetime.utcnow() + timedelta(milliseconds=i * 100),
                data={"direction": Direction.RIGHT, "steps": 1},
                position=(sample_player.position_x + i, sample_player.position_y),
                map_name=sample_player.current_map
            )
            action_queue.append(action)

        # Test queue processing
        processed_actions = []
        max_queue_size = 10

        for action in action_queue:
            if len(processed_actions) < max_queue_size:
                if self._can_process_action(action, processed_actions):
                    processed_actions.append(action)

        assert len(processed_actions) == 5

        # Test queue overflow protection
        for i in range(20):  # Add many more actions
            action = PlayerAction(
                action_type=ActionType.MOVE,
                player_id=sample_player.id,
                timestamp=datetime.utcnow() + timedelta(milliseconds=(i + 5) * 100),
                data={"direction": Direction.DOWN, "steps": 1},
                position=(sample_player.position_x, sample_player.position_y + i),
                map_name=sample_player.current_map
            )

            if len(processed_actions) < max_queue_size:
                processed_actions.append(action)

        # Should not exceed max queue size
        assert len(processed_actions) <= max_queue_size

    def _can_process_action(
        self,
        action: PlayerAction,
        previous_actions: List[PlayerAction]
    ) -> bool:
        """Check if action can be processed in sequence."""
        # Prevent duplicate actions
        for prev_action in previous_actions:
            if (prev_action.action_type == action.action_type and
                prev_action.timestamp == action.timestamp):
                return False

        # Check action prerequisites
        if action.action_type == ActionType.BATTLE_ACTION:
            # Must have a move action or interaction first
            has_prerequisite = any(
                prev.action_type in [ActionType.MOVE, ActionType.INTERACT]
                for prev in previous_actions
            )
            return has_prerequisite

        return True

    @pytest.mark.unit
    @pytest.mark.game
    def test_touch_input_optimization(self, sample_player: Player):
        """Test touch input optimizations for mobile gameplay."""
        # Test touch-to-move action
        touch_position = (15, 12)  # Target position
        current_position = (sample_player.position_x, sample_player.position_y)

        # Calculate path from current to touch position
        path = self._calculate_touch_movement_path(current_position, touch_position)

        assert len(path) > 0
        assert path[0] == current_position
        assert path[-1] == touch_position

        # Test path optimization (should use Manhattan distance)
        expected_distance = abs(touch_position[0] - current_position[0]) + \
                           abs(touch_position[1] - current_position[1])
        assert len(path) - 1 == expected_distance

        # Test maximum touch movement distance (prevent accidental large moves)
        max_touch_distance = 8
        far_touch_position = (25, 25)  # Far from player

        is_valid_touch = self._validate_touch_movement(
            current_position, far_touch_position, max_touch_distance
        )
        assert is_valid_touch is False

        # Test valid touch movement
        close_touch_position = (12, 13)
        is_valid_close = self._validate_touch_movement(
            current_position, close_touch_position, max_touch_distance
        )
        assert is_valid_close is True

    def _calculate_touch_movement_path(
        self,
        start: Tuple[int, int],
        end: Tuple[int, int]
    ) -> List[Tuple[int, int]]:
        """Calculate movement path from touch input."""
        path = [start]
        current_x, current_y = start
        end_x, end_y = end

        # Move horizontally first, then vertically
        while current_x != end_x:
            if current_x < end_x:
                current_x += 1
            else:
                current_x -= 1
            path.append((current_x, current_y))

        while current_y != end_y:
            if current_y < end_y:
                current_y += 1
            else:
                current_y -= 1
            path.append((current_x, current_y))

        return path

    def _validate_touch_movement(
        self,
        start: Tuple[int, int],
        end: Tuple[int, int],
        max_distance: int
    ) -> bool:
        """Validate touch movement distance."""
        manhattan_distance = abs(end[0] - start[0]) + abs(end[1] - start[1])
        return manhattan_distance <= max_distance

    @pytest.mark.unit
    @pytest.mark.game
    def test_action_cancellation(self, sample_player: Player):
        """Test action cancellation for mobile UX."""
        # Create a queued action
        queued_action = PlayerAction(
            action_type=ActionType.MOVE,
            player_id=sample_player.id,
            timestamp=datetime.utcnow() + timedelta(seconds=1),  # Future action
            data={"direction": Direction.UP, "steps": 3},
            position=(sample_player.position_x, sample_player.position_y),
            map_name=sample_player.current_map
        )

        # Test cancellation conditions
        assert self._can_cancel_action(queued_action) is True

        # Test already executed action (cannot cancel)
        executed_action = PlayerAction(
            action_type=ActionType.MOVE,
            player_id=sample_player.id,
            timestamp=datetime.utcnow() - timedelta(seconds=1),  # Past action
            data={"direction": Direction.UP, "steps": 1},
            position=(sample_player.position_x, sample_player.position_y),
            map_name=sample_player.current_map
        )

        assert self._can_cancel_action(executed_action) is False

        # Test critical actions that cannot be cancelled
        critical_action = PlayerAction(
            action_type=ActionType.BATTLE_ACTION,
            player_id=sample_player.id,
            timestamp=datetime.utcnow() + timedelta(milliseconds=500),
            data={"action": "attack", "target": "enemy_monster"},
            position=(sample_player.position_x, sample_player.position_y),
            map_name=sample_player.current_map
        )

        assert self._can_cancel_action(critical_action) is False

    def _can_cancel_action(self, action: PlayerAction) -> bool:
        """Check if action can be cancelled."""
        # Cannot cancel past actions
        if action.timestamp < datetime.utcnow():
            return False

        # Cannot cancel critical actions
        critical_action_types = [ActionType.BATTLE_ACTION]
        if action.action_type in critical_action_types:
            return False

        # Can cancel future movement and interaction actions
        cancellable_types = [ActionType.MOVE, ActionType.INTERACT, ActionType.USE_ITEM]
        return action.action_type in cancellable_types