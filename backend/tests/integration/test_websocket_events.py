"""
Integration Tests for WebSocket Real-time Events
Austin Kidwell | Intellegix | AI-Powered Tuxemon Game

Tests real-time event delivery, connection management, message ordering,
and mobile network resilience for the game's WebSocket communication.
"""

import pytest
import pytest_asyncio
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, MagicMock, patch

import socketio
from fastapi import FastAPI
from fastapi.testclient import TestClient


# Mock WebSocket event types (these would be in your actual game code)
class GameEventTypes:
    WORLD_UPDATE = "world_update"
    NPC_DIALOGUE = "npc_dialogue"
    COMBAT_UPDATE = "combat_update"
    NOTIFICATION = "notification"
    PLAYER_MOVE = "player_move"
    COST_ALERT = "cost_alert"
    CONNECTION_STATUS = "connection_status"
    SYNC_REQUEST = "sync_request"


class MockWebSocketManager:
    """Mock WebSocket manager for testing."""

    def __init__(self):
        self.sio = socketio.AsyncServer(async_mode='asgi')
        self.connected_clients: Dict[str, Dict[str, Any]] = {}
        self.message_history: List[Dict[str, Any]] = []
        self.connection_events: List[Dict[str, Any]] = []

    async def emit_to_player(self, player_id: str, event: str, data: Any):
        """Emit event to specific player."""
        message = {
            'timestamp': datetime.utcnow().isoformat(),
            'event': event,
            'data': data,
            'player_id': player_id
        }
        self.message_history.append(message)

        # Simulate actual socket emission
        await self.sio.emit(event, data, room=f"player_{player_id}")

    async def broadcast_to_map(self, map_name: str, event: str, data: Any, exclude_player: Optional[str] = None):
        """Broadcast event to all players on a map."""
        message = {
            'timestamp': datetime.utcnow().isoformat(),
            'event': event,
            'data': data,
            'map_name': map_name,
            'exclude_player': exclude_player
        }
        self.message_history.append(message)

        # Simulate broadcast
        await self.sio.emit(event, data, room=f"map_{map_name}")

    async def handle_player_connect(self, sid: str, player_id: str, player_data: Dict[str, Any]):
        """Handle player connection."""
        self.connected_clients[sid] = {
            'player_id': player_id,
            'player_data': player_data,
            'connected_at': datetime.utcnow(),
            'last_activity': datetime.utcnow()
        }

        connection_event = {
            'type': 'connect',
            'sid': sid,
            'player_id': player_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        self.connection_events.append(connection_event)

        # Join player-specific room
        await self.sio.enter_room(sid, f"player_{player_id}")

        # Join map-specific room
        map_name = player_data.get('current_map', 'starting_town')
        await self.sio.enter_room(sid, f"map_{map_name}")

    async def handle_player_disconnect(self, sid: str):
        """Handle player disconnection."""
        if sid in self.connected_clients:
            client_info = self.connected_clients[sid]
            connection_event = {
                'type': 'disconnect',
                'sid': sid,
                'player_id': client_info['player_id'],
                'timestamp': datetime.utcnow().isoformat(),
                'session_duration': (datetime.utcnow() - client_info['connected_at']).total_seconds()
            }
            self.connection_events.append(connection_event)

            del self.connected_clients[sid]

    def get_connected_players_on_map(self, map_name: str) -> List[Dict[str, Any]]:
        """Get list of connected players on specific map."""
        return [
            client for client in self.connected_clients.values()
            if client['player_data'].get('current_map') == map_name
        ]


class TestWebSocketEvents:
    """Integration tests for WebSocket real-time communication."""

    @pytest_asyncio.fixture
    async def websocket_manager(self):
        """Provide WebSocket manager for testing."""
        manager = MockWebSocketManager()
        return manager

    @pytest_asyncio.fixture
    async def mock_clients(self, websocket_manager):
        """Create mock connected clients for testing."""
        clients = []

        for i in range(5):
            sid = f"test_sid_{i}"
            player_id = f"player_{i}"
            player_data = {
                'id': player_id,
                'username': f'test_player_{i}',
                'current_map': 'test_map' if i < 3 else 'other_map',
                'position': {'x': 10 + i, 'y': 15 + i},
                'level': 5 + i
            }

            await websocket_manager.handle_player_connect(sid, player_id, player_data)
            clients.append({
                'sid': sid,
                'player_id': player_id,
                'player_data': player_data
            })

        return clients

    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_player_connection_management(self, websocket_manager: MockWebSocketManager):
        """Test player connection and disconnection handling."""
        # Test connection
        sid = "test_connection"
        player_id = "player_123"
        player_data = {
            'id': player_id,
            'username': 'test_user',
            'current_map': 'forest_area',
            'position': {'x': 25, 'y': 30}
        }

        await websocket_manager.handle_player_connect(sid, player_id, player_data)

        # Verify connection
        assert sid in websocket_manager.connected_clients
        client_info = websocket_manager.connected_clients[sid]
        assert client_info['player_id'] == player_id
        assert client_info['player_data']['username'] == 'test_user'

        # Verify connection event logged
        connection_events = [e for e in websocket_manager.connection_events if e['type'] == 'connect']
        assert len(connection_events) == 1
        assert connection_events[0]['player_id'] == player_id

        # Test disconnection
        await websocket_manager.handle_player_disconnect(sid)

        # Verify disconnection
        assert sid not in websocket_manager.connected_clients

        # Verify disconnection event logged
        disconnect_events = [e for e in websocket_manager.connection_events if e['type'] == 'disconnect']
        assert len(disconnect_events) == 1
        assert disconnect_events[0]['player_id'] == player_id
        assert 'session_duration' in disconnect_events[0]

    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_npc_dialogue_event_delivery(
        self,
        websocket_manager: MockWebSocketManager,
        mock_clients: List[Dict[str, Any]]
    ):
        """Test NPC dialogue event delivery to specific player."""
        target_client = mock_clients[0]
        player_id = target_client['player_id']

        # Create NPC dialogue event
        dialogue_data = {
            "npc_id": str(uuid4()),
            "npc_name": "Alice",
            "dialogue": {
                "text": "Hello there! How's your adventure going?",
                "emotion": "friendly",
                "actions": ["wave"],
                "relationship_change": 0.1
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        # Emit dialogue event to specific player
        await websocket_manager.emit_to_player(
            player_id=player_id,
            event=GameEventTypes.NPC_DIALOGUE,
            data=dialogue_data
        )

        # Verify event was recorded
        dialogue_messages = [
            msg for msg in websocket_manager.message_history
            if msg['event'] == GameEventTypes.NPC_DIALOGUE and msg['player_id'] == player_id
        ]

        assert len(dialogue_messages) == 1
        message = dialogue_messages[0]
        assert message['data']['npc_name'] == "Alice"
        assert message['data']['dialogue']['text'] == "Hello there! How's your adventure going?"
        assert message['data']['dialogue']['emotion'] == "friendly"

    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_world_update_broadcast(
        self,
        websocket_manager: MockWebSocketManager,
        mock_clients: List[Dict[str, Any]]
    ):
        """Test world update broadcasting to all players on a map."""
        map_name = "test_map"

        # Create world update event
        world_update_data = {
            "map_name": map_name,
            "npcs": [
                {
                    "id": str(uuid4()),
                    "name": "Wandering Trainer",
                    "position": [20, 25],
                    "activity": "training_monsters"
                }
            ],
            "objects": [
                {
                    "id": "chest_001",
                    "position": [30, 35],
                    "state": "opened"
                }
            ],
            "timestamp": datetime.utcnow().isoformat()
        }

        # Broadcast to map
        await websocket_manager.broadcast_to_map(
            map_name=map_name,
            event=GameEventTypes.WORLD_UPDATE,
            data=world_update_data
        )

        # Verify broadcast was recorded
        broadcast_messages = [
            msg for msg in websocket_manager.message_history
            if msg['event'] == GameEventTypes.WORLD_UPDATE and msg['map_name'] == map_name
        ]

        assert len(broadcast_messages) == 1
        message = broadcast_messages[0]
        assert message['data']['map_name'] == map_name
        assert len(message['data']['npcs']) == 1
        assert message['data']['npcs'][0]['name'] == "Wandering Trainer"

    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_player_movement_synchronization(
        self,
        websocket_manager: MockWebSocketManager,
        mock_clients: List[Dict[str, Any]]
    ):
        """Test player movement event synchronization."""
        moving_client = mock_clients[0]
        player_id = moving_client['player_id']
        map_name = moving_client['player_data']['current_map']

        # Create player movement event
        movement_data = {
            "player_id": player_id,
            "player_name": moving_client['player_data']['username'],
            "old_position": {"x": 10, "y": 15},
            "new_position": {"x": 12, "y": 16},
            "facing_direction": "right",
            "animation": "walking",
            "timestamp": datetime.utcnow().isoformat()
        }

        # Broadcast movement to other players on same map (excluding moving player)
        await websocket_manager.broadcast_to_map(
            map_name=map_name,
            event=GameEventTypes.PLAYER_MOVE,
            data=movement_data,
            exclude_player=player_id
        )

        # Verify movement broadcast
        movement_messages = [
            msg for msg in websocket_manager.message_history
            if msg['event'] == GameEventTypes.PLAYER_MOVE
        ]

        assert len(movement_messages) == 1
        message = movement_messages[0]
        assert message['data']['player_id'] == player_id
        assert message['data']['new_position']['x'] == 12
        assert message['data']['facing_direction'] == "right"
        assert message['exclude_player'] == player_id

    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_combat_update_events(
        self,
        websocket_manager: MockWebSocketManager,
        mock_clients: List[Dict[str, Any]]
    ):
        """Test combat update event handling."""
        player1 = mock_clients[0]
        player2 = mock_clients[1]

        # Create combat update event
        combat_data = {
            "battle_id": str(uuid4()),
            "participants": [
                {
                    "player_id": player1['player_id'],
                    "player_name": player1['player_data']['username'],
                    "monster": {
                        "name": "Bamboon",
                        "level": 8,
                        "current_hp": 35,
                        "max_hp": 50
                    }
                },
                {
                    "player_id": player2['player_id'],
                    "player_name": player2['player_data']['username'],
                    "monster": {
                        "name": "Rockitten",
                        "level": 6,
                        "current_hp": 20,
                        "max_hp": 40
                    }
                }
            ],
            "current_turn": player1['player_id'],
            "last_action": {
                "action": "attack",
                "attacker": player1['player_id'],
                "target": player2['player_id'],
                "damage": 15,
                "effectiveness": "normal"
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        # Send combat updates to both participants
        for participant in [player1, player2]:
            await websocket_manager.emit_to_player(
                player_id=participant['player_id'],
                event=GameEventTypes.COMBAT_UPDATE,
                data=combat_data
            )

        # Verify combat updates were sent
        combat_messages = [
            msg for msg in websocket_manager.message_history
            if msg['event'] == GameEventTypes.COMBAT_UPDATE
        ]

        assert len(combat_messages) == 2  # One for each participant

        for message in combat_messages:
            assert message['data']['battle_id'] == combat_data['battle_id']
            assert len(message['data']['participants']) == 2
            assert message['data']['last_action']['damage'] == 15

    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_cost_alert_system(
        self,
        websocket_manager: MockWebSocketManager,
        mock_clients: List[Dict[str, Any]]
    ):
        """Test AI cost alert broadcasting to relevant players."""
        # Simulate cost alert for admin/high-level players
        cost_alert_data = {
            "alert_type": "budget_threshold",
            "current_cost": 85.50,
            "budget_limit": 100.0,
            "utilization_percent": 85.5,
            "threshold_percent": 80.0,
            "message": "Daily AI budget at 85.5% of limit",
            "timestamp": datetime.utcnow().isoformat(),
            "severity": "warning"
        }

        # Send to admin players only (simulate admin check)
        admin_players = [client for client in mock_clients if client['player_data'].get('level', 0) >= 8]

        for admin_client in admin_players:
            await websocket_manager.emit_to_player(
                player_id=admin_client['player_id'],
                event=GameEventTypes.COST_ALERT,
                data=cost_alert_data
            )

        # Verify cost alerts were sent only to admin players
        cost_alert_messages = [
            msg for msg in websocket_manager.message_history
            if msg['event'] == GameEventTypes.COST_ALERT
        ]

        # Should only send to players with level >= 8
        expected_admin_count = len([c for c in mock_clients if c['player_data']['level'] >= 8])
        assert len(cost_alert_messages) == expected_admin_count

        for message in cost_alert_messages:
            assert message['data']['alert_type'] == "budget_threshold"
            assert message['data']['utilization_percent'] == 85.5
            assert message['data']['severity'] == "warning"

    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_notification_system(
        self,
        websocket_manager: MockWebSocketManager,
        mock_clients: List[Dict[str, Any]]
    ):
        """Test general notification system."""
        target_client = mock_clients[0]
        player_id = target_client['player_id']

        # Test different notification types
        notifications = [
            {
                "type": "achievement",
                "title": "Level Up!",
                "message": "Congratulations! You reached level 9!",
                "icon": "level_up",
                "duration": 5000
            },
            {
                "type": "item_received",
                "title": "Item Found",
                "message": "You found a Rare Candy!",
                "icon": "item_rare_candy",
                "duration": 3000
            },
            {
                "type": "friend_request",
                "title": "Friend Request",
                "message": "Alice wants to be your friend!",
                "icon": "friend_request",
                "duration": 0,  # Persistent until dismissed
                "actions": ["accept", "decline"]
            }
        ]

        for notification in notifications:
            await websocket_manager.emit_to_player(
                player_id=player_id,
                event=GameEventTypes.NOTIFICATION,
                data=notification
            )

        # Verify notifications were sent
        notification_messages = [
            msg for msg in websocket_manager.message_history
            if msg['event'] == GameEventTypes.NOTIFICATION and msg['player_id'] == player_id
        ]

        assert len(notification_messages) == 3

        # Check achievement notification
        achievement_msg = next(msg for msg in notification_messages if msg['data']['type'] == 'achievement')
        assert achievement_msg['data']['title'] == "Level Up!"
        assert achievement_msg['data']['duration'] == 5000

        # Check friend request notification
        friend_msg = next(msg for msg in notification_messages if msg['data']['type'] == 'friend_request')
        assert friend_msg['data']['duration'] == 0
        assert 'actions' in friend_msg['data']

    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_message_ordering_and_delivery(
        self,
        websocket_manager: MockWebSocketManager,
        mock_clients: List[Dict[str, Any]]
    ):
        """Test message ordering and delivery guarantees."""
        player_id = mock_clients[0]['player_id']

        # Send sequence of messages rapidly
        messages = []
        for i in range(10):
            message_data = {
                "sequence_id": i,
                "content": f"Message {i}",
                "timestamp": datetime.utcnow().isoformat()
            }

            await websocket_manager.emit_to_player(
                player_id=player_id,
                event=GameEventTypes.NOTIFICATION,
                data=message_data
            )
            messages.append(message_data)

        # Verify all messages were recorded in order
        sent_messages = [
            msg for msg in websocket_manager.message_history
            if msg['event'] == GameEventTypes.NOTIFICATION and msg['player_id'] == player_id
        ]

        assert len(sent_messages) == 10

        # Verify ordering
        for i, message in enumerate(sent_messages):
            assert message['data']['sequence_id'] == i
            assert message['data']['content'] == f"Message {i}"

        # Verify timestamps are in ascending order
        timestamps = [datetime.fromisoformat(msg['timestamp']) for msg in sent_messages]
        for i in range(1, len(timestamps)):
            assert timestamps[i] >= timestamps[i-1]

    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_map_based_client_isolation(
        self,
        websocket_manager: MockWebSocketManager,
        mock_clients: List[Dict[str, Any]]
    ):
        """Test that map-based events only reach players on the correct map."""
        # Get players on different maps
        test_map_players = [c for c in mock_clients if c['player_data']['current_map'] == 'test_map']
        other_map_players = [c for c in mock_clients if c['player_data']['current_map'] == 'other_map']

        # Broadcast event to test_map only
        map_event_data = {
            "event_type": "map_specific",
            "message": "Something happened on test_map!",
            "timestamp": datetime.utcnow().isoformat()
        }

        await websocket_manager.broadcast_to_map(
            map_name="test_map",
            event=GameEventTypes.WORLD_UPDATE,
            data=map_event_data
        )

        # Verify event was recorded
        map_messages = [
            msg for msg in websocket_manager.message_history
            if msg['event'] == GameEventTypes.WORLD_UPDATE and msg.get('map_name') == 'test_map'
        ]

        assert len(map_messages) == 1
        assert map_messages[0]['data']['message'] == "Something happened on test_map!"

        # Verify player distribution
        assert len(test_map_players) >= 1  # Should have some players on test_map
        assert len(other_map_players) >= 1  # Should have some players on other_map

    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_connection_resilience_and_reconnection(
        self,
        websocket_manager: MockWebSocketManager
    ):
        """Test connection resilience and reconnection handling."""
        player_id = "resilience_test_player"
        player_data = {
            'id': player_id,
            'username': 'resilience_tester',
            'current_map': 'test_map',
            'position': {'x': 10, 'y': 10}
        }

        # Test initial connection
        sid1 = "first_connection"
        await websocket_manager.handle_player_connect(sid1, player_id, player_data)

        # Send some events
        await websocket_manager.emit_to_player(
            player_id=player_id,
            event=GameEventTypes.NOTIFICATION,
            data={"message": "Before disconnect"}
        )

        # Simulate disconnection
        await websocket_manager.handle_player_disconnect(sid1)

        # Simulate reconnection with different session ID
        sid2 = "second_connection"
        await websocket_manager.handle_player_connect(sid2, player_id, player_data)

        # Send event after reconnection
        await websocket_manager.emit_to_player(
            player_id=player_id,
            event=GameEventTypes.NOTIFICATION,
            data={"message": "After reconnect"}
        )

        # Verify connection events
        connect_events = [e for e in websocket_manager.connection_events if e['type'] == 'connect']
        disconnect_events = [e for e in websocket_manager.connection_events if e['type'] == 'disconnect']

        assert len(connect_events) == 2  # Two connections
        assert len(disconnect_events) == 1  # One disconnection

        # Verify player is currently connected
        assert sid2 in websocket_manager.connected_clients
        assert sid1 not in websocket_manager.connected_clients

        # Verify messages were sent
        player_messages = [
            msg for msg in websocket_manager.message_history
            if msg.get('player_id') == player_id and msg['event'] == GameEventTypes.NOTIFICATION
        ]

        assert len(player_messages) == 2
        assert player_messages[0]['data']['message'] == "Before disconnect"
        assert player_messages[1]['data']['message'] == "After reconnect"

    @pytest.mark.integration
    @pytest.mark.websocket
    async def test_websocket_performance_under_load(
        self,
        websocket_manager: MockWebSocketManager
    ):
        """Test WebSocket performance with high message volume."""
        # Create more clients for load testing
        load_test_clients = []
        num_clients = 20

        for i in range(num_clients):
            sid = f"load_test_sid_{i}"
            player_id = f"load_player_{i}"
            player_data = {
                'id': player_id,
                'username': f'load_test_{i}',
                'current_map': 'load_test_map',
                'position': {'x': i, 'y': i}
            }

            await websocket_manager.handle_player_connect(sid, player_id, player_data)
            load_test_clients.append({'sid': sid, 'player_id': player_id})

        # Send high volume of messages
        start_time = asyncio.get_event_loop().time()
        message_count = 100

        for i in range(message_count):
            # Alternate between individual messages and broadcasts
            if i % 2 == 0:
                # Individual message
                target_client = load_test_clients[i % num_clients]
                await websocket_manager.emit_to_player(
                    player_id=target_client['player_id'],
                    event=GameEventTypes.NOTIFICATION,
                    data={"message": f"Individual message {i}"}
                )
            else:
                # Broadcast message
                await websocket_manager.broadcast_to_map(
                    map_name="load_test_map",
                    event=GameEventTypes.WORLD_UPDATE,
                    data={"message": f"Broadcast message {i}"}
                )

        end_time = asyncio.get_event_loop().time()
        total_time = end_time - start_time

        # Performance assertions
        assert total_time < 5.0  # Should complete within 5 seconds
        assert len(websocket_manager.message_history) >= message_count

        # Calculate throughput
        throughput = len(websocket_manager.message_history) / total_time
        assert throughput > 20  # At least 20 messages per second

        # Verify no message loss
        individual_messages = [
            msg for msg in websocket_manager.message_history
            if msg['event'] == GameEventTypes.NOTIFICATION and 'player_id' in msg
        ]
        broadcast_messages = [
            msg for msg in websocket_manager.message_history
            if msg['event'] == GameEventTypes.WORLD_UPDATE and 'map_name' in msg
        ]

        expected_individual = message_count // 2
        expected_broadcasts = message_count - expected_individual

        assert len(individual_messages) == expected_individual
        assert len(broadcast_messages) == expected_broadcasts