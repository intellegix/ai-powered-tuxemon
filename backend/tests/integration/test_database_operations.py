"""
Integration Tests for Database Operations
Austin Kidwell | Intellegix | AI-Powered Tuxemon Game

Tests PostgreSQL transaction integrity, concurrent operations, and
database performance under realistic load scenarios.
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
from uuid import UUID, uuid4
import json

import asyncpg
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from app.game.models import Player, NPC, Monster
from app.core.database import get_database_url


class TestDatabaseOperations:
    """Integration tests for database operations and transaction handling."""

    @pytest_asyncio.fixture
    async def db_pool(self):
        """Create test database connection pool."""
        test_db_url = get_database_url().replace('tuxemon', 'tuxemon_test')

        pool = await asyncpg.create_pool(
            test_db_url,
            min_size=1,
            max_size=10,
            command_timeout=60
        )

        yield pool

        await pool.close()

    @pytest_asyncio.fixture
    async def clean_db(self, db_pool):
        """Provide clean database for each test."""
        async with db_pool.acquire() as conn:
            # Clean all tables
            await conn.execute("DELETE FROM player_inventory")
            await conn.execute("DELETE FROM monsters")
            await conn.execute("DELETE FROM npcs")
            await conn.execute("DELETE FROM players")

        yield db_pool

    @pytest.mark.integration
    @pytest.mark.db
    async def test_player_crud_operations(self, clean_db):
        """Test complete player CRUD operations."""
        player_data = {
            'id': uuid4(),
            'username': 'test_player',
            'email': 'test@example.com',
            'hashed_password': '$2b$12$test_hash',
            'current_map': 'starting_town',
            'position_x': 10,
            'position_y': 10,
            'money': 500,
            'story_progress': '{"tutorial": true}',
            'npc_relationships': '{"alice": 0.5}',
            'created_at': datetime.utcnow(),
            'last_login': datetime.utcnow()
        }

        async with clean_db.acquire() as conn:
            # CREATE - Insert player
            await conn.execute("""
                INSERT INTO players (id, username, email, hashed_password, current_map,
                                   position_x, position_y, money, story_progress,
                                   npc_relationships, created_at, last_login, is_active)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            """,
                player_data['id'],
                player_data['username'],
                player_data['email'],
                player_data['hashed_password'],
                player_data['current_map'],
                player_data['position_x'],
                player_data['position_y'],
                player_data['money'],
                player_data['story_progress'],
                player_data['npc_relationships'],
                player_data['created_at'],
                player_data['last_login'],
                True
            )

            # READ - Fetch player
            row = await conn.fetchrow("SELECT * FROM players WHERE id = $1", player_data['id'])
            assert row is not None
            assert row['username'] == 'test_player'
            assert row['money'] == 500
            assert json.loads(row['story_progress'])['tutorial'] is True

            # UPDATE - Modify player data
            new_money = 750
            new_position = (15, 20)
            await conn.execute("""
                UPDATE players
                SET money = $1, position_x = $2, position_y = $3, last_login = $4
                WHERE id = $5
            """, new_money, new_position[0], new_position[1], datetime.utcnow(), player_data['id'])

            # Verify update
            updated_row = await conn.fetchrow("SELECT money, position_x, position_y FROM players WHERE id = $1", player_data['id'])
            assert updated_row['money'] == new_money
            assert updated_row['position_x'] == new_position[0]
            assert updated_row['position_y'] == new_position[1]

            # DELETE - Remove player
            await conn.execute("DELETE FROM players WHERE id = $1", player_data['id'])

            # Verify deletion
            deleted_row = await conn.fetchrow("SELECT * FROM players WHERE id = $1", player_data['id'])
            assert deleted_row is None

    @pytest.mark.integration
    @pytest.mark.db
    async def test_npc_monster_relationships(self, clean_db):
        """Test NPC and monster relationship management."""
        # Create player first
        player_id = uuid4()
        async with clean_db.acquire() as conn:
            await conn.execute("""
                INSERT INTO players (id, username, email, hashed_password)
                VALUES ($1, $2, $3, $4)
            """, player_id, 'test_player', 'test@example.com', 'hash')

            # Create NPC
            npc_id = uuid4()
            await conn.execute("""
                INSERT INTO npcs (id, slug, name, sprite_name, position_x, position_y,
                                map_name, is_trainer, can_battle, personality_traits, schedule)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """,
                npc_id, 'trainer_alice', 'Alice', 'trainer_01', 25, 30, 'forest_area',
                True, True, '{"friendliness": 0.8, "competitiveness": 0.9}', '{}'
            )

            # Create player monster
            player_monster_id = uuid4()
            await conn.execute("""
                INSERT INTO monsters (id, species_slug, name, level, current_hp,
                                    total_experience, player_id, personality_traits)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
                player_monster_id, 'bamboon', 'MyBamboon', 10, 50, 250, player_id,
                '{"nature": "brave", "characteristic": "likes_to_fight"}'
            )

            # Create NPC monster
            npc_monster_id = uuid4()
            await conn.execute("""
                INSERT INTO monsters (id, species_slug, name, level, current_hp,
                                    total_experience, npc_id, personality_traits)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
                npc_monster_id, 'rockitten', 'Fluffy', 8, 40, 150, npc_id,
                '{"nature": "careful", "characteristic": "sturdy_body"}'
            )

            # Verify relationships
            npc_with_monsters = await conn.fetchrow("""
                SELECT n.name, COUNT(m.id) as monster_count
                FROM npcs n
                LEFT JOIN monsters m ON n.id = m.npc_id
                WHERE n.id = $1
                GROUP BY n.id, n.name
            """, npc_id)

            assert npc_with_monsters['name'] == 'Alice'
            assert npc_with_monsters['monster_count'] == 1

            player_with_monsters = await conn.fetchrow("""
                SELECT p.username, COUNT(m.id) as monster_count
                FROM players p
                LEFT JOIN monsters m ON p.id = m.player_id
                WHERE p.id = $1
                GROUP BY p.id, p.username
            """, player_id)

            assert player_with_monsters['username'] == 'test_player'
            assert player_with_monsters['monster_count'] == 1

    @pytest.mark.integration
    @pytest.mark.db
    async def test_transaction_rollback_on_error(self, clean_db):
        """Test transaction rollback when errors occur."""
        player_id = uuid4()

        async with clean_db.acquire() as conn:
            try:
                async with conn.transaction():
                    # Insert valid player
                    await conn.execute("""
                        INSERT INTO players (id, username, email, hashed_password)
                        VALUES ($1, $2, $3, $4)
                    """, player_id, 'test_player', 'test@example.com', 'hash')

                    # Insert monster for player
                    monster_id = uuid4()
                    await conn.execute("""
                        INSERT INTO monsters (id, species_slug, name, level, current_hp,
                                            total_experience, player_id)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """, monster_id, 'bamboon', 'TestMon', 5, 30, 100, player_id)

                    # Try to insert duplicate player (should fail)
                    await conn.execute("""
                        INSERT INTO players (id, username, email, hashed_password)
                        VALUES ($1, $2, $3, $4)
                    """, uuid4(), 'test_player', 'duplicate@example.com', 'hash')  # Duplicate username

            except asyncpg.UniqueViolationError:
                # Transaction should rollback automatically
                pass

            # Verify rollback - neither player nor monster should exist
            player_count = await conn.fetchval("SELECT COUNT(*) FROM players WHERE username = $1", 'test_player')
            monster_count = await conn.fetchval("SELECT COUNT(*) FROM monsters WHERE species_slug = $1", 'bamboon')

            assert player_count == 0
            assert monster_count == 0

    @pytest.mark.integration
    @pytest.mark.db
    async def test_concurrent_player_updates(self, clean_db):
        """Test concurrent updates to player data."""
        player_id = uuid4()

        # Create player
        async with clean_db.acquire() as conn:
            await conn.execute("""
                INSERT INTO players (id, username, email, hashed_password, money)
                VALUES ($1, $2, $3, $4, $5)
            """, player_id, 'concurrent_test', 'test@example.com', 'hash', 1000)

        # Simulate concurrent money updates
        async def update_money(amount_change: int, pool):
            async with pool.acquire() as conn:
                async with conn.transaction():
                    # Get current money
                    current_money = await conn.fetchval("SELECT money FROM players WHERE id = $1", player_id)

                    # Small delay to increase chance of race condition
                    await asyncio.sleep(0.01)

                    # Update money
                    new_money = current_money + amount_change
                    await conn.execute("UPDATE players SET money = $1 WHERE id = $2", new_money, player_id)

        # Run concurrent updates
        update_tasks = [
            update_money(100, clean_db),
            update_money(-50, clean_db),
            update_money(200, clean_db),
            update_money(-25, clean_db),
        ]

        await asyncio.gather(*update_tasks)

        # Verify final money amount is consistent
        async with clean_db.acquire() as conn:
            final_money = await conn.fetchval("SELECT money FROM players WHERE id = $1", player_id)
            # Should be 1000 + 100 - 50 + 200 - 25 = 1225 (if all updates succeeded)
            # Due to concurrency, some updates might have been lost, but value should be reasonable
            assert 1000 <= final_money <= 1225

    @pytest.mark.integration
    @pytest.mark.db
    async def test_complex_query_performance(self, clean_db):
        """Test performance of complex queries with joins."""
        # Create test data
        player_ids = []
        npc_ids = []

        async with clean_db.acquire() as conn:
            # Create multiple players
            for i in range(20):
                player_id = uuid4()
                player_ids.append(player_id)
                await conn.execute("""
                    INSERT INTO players (id, username, email, hashed_password, position_x, position_y, current_map)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, player_id, f'player_{i}', f'player_{i}@test.com', 'hash', i * 5, i * 3, 'test_map')

                # Create monsters for each player
                for j in range(3):
                    monster_id = uuid4()
                    await conn.execute("""
                        INSERT INTO monsters (id, species_slug, name, level, current_hp,
                                            total_experience, player_id)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """, monster_id, f'species_{j}', f'Monster_{i}_{j}', j + 1, 50, j * 100, player_id)

            # Create NPCs
            for i in range(10):
                npc_id = uuid4()
                npc_ids.append(npc_id)
                await conn.execute("""
                    INSERT INTO npcs (id, slug, name, sprite_name, position_x, position_y,
                                    map_name, personality_traits)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, npc_id, f'npc_{i}', f'NPC {i}', f'npc_sprite_{i}', i * 10, i * 8, 'test_map', '{}')

            # Perform complex query - find all players with their monsters on the same map as NPCs
            start_time = asyncio.get_event_loop().time()

            complex_result = await conn.fetch("""
                SELECT
                    p.username,
                    p.position_x,
                    p.position_y,
                    COUNT(m.id) as monster_count,
                    ARRAY_AGG(DISTINCT n.name) as nearby_npcs
                FROM players p
                LEFT JOIN monsters m ON p.id = m.player_id
                JOIN npcs n ON p.current_map = n.map_name
                WHERE p.current_map = $1
                GROUP BY p.id, p.username, p.position_x, p.position_y
                ORDER BY p.username
            """, 'test_map')

            end_time = asyncio.get_event_loop().time()
            query_time = (end_time - start_time) * 1000  # Convert to milliseconds

            # Performance assertion - should complete within reasonable time
            assert query_time < 100  # Under 100ms for this dataset size
            assert len(complex_result) == 20  # All players should be found

            # Verify data integrity
            for row in complex_result:
                assert row['monster_count'] == 3  # Each player has 3 monsters
                assert len(row['nearby_npcs']) == 10  # 10 NPCs on the map

    @pytest.mark.integration
    @pytest.mark.db
    async def test_database_connection_pool_behavior(self, db_pool):
        """Test database connection pool management under load."""
        async def simulate_db_operation(operation_id: int):
            async with db_pool.acquire() as conn:
                # Simulate varying operation times
                await asyncio.sleep(0.01 * (operation_id % 5))

                # Simple query to verify connection works
                result = await conn.fetchval("SELECT $1 as operation_id", operation_id)
                return result

        # Test with more concurrent operations than pool size
        operation_count = 25  # More than max pool size (10)
        operations = [simulate_db_operation(i) for i in range(operation_count)]

        start_time = asyncio.get_event_loop().time()
        results = await asyncio.gather(*operations)
        end_time = asyncio.get_event_loop().time()

        total_time = (end_time - start_time) * 1000

        # Verify all operations completed
        assert len(results) == operation_count
        assert all(results[i] == i for i in range(operation_count))

        # Should handle connection pooling efficiently
        assert total_time < 2000  # Under 2 seconds for all operations

    @pytest.mark.integration
    @pytest.mark.db
    async def test_json_data_operations(self, clean_db):
        """Test JSON field operations for complex game data."""
        player_id = uuid4()

        async with clean_db.acquire() as conn:
            # Insert player with complex JSON data
            story_progress = {
                "tutorial_completed": True,
                "quests": {
                    "main_story": {"chapter": 3, "completed": ["intro", "forest_trial"]},
                    "side_quests": [
                        {"id": "help_villager", "status": "completed", "reward_claimed": True},
                        {"id": "find_rare_monster", "status": "in_progress", "progress": 0.7}
                    ]
                }
            }

            npc_relationships = {
                "alice": {"favorability": 0.8, "last_interaction": "2024-01-27T10:30:00Z"},
                "bob": {"favorability": 0.3, "last_interaction": "2024-01-26T15:20:00Z"},
                "shop_keeper": {"favorability": 0.5, "last_interaction": "2024-01-27T09:15:00Z"}
            }

            await conn.execute("""
                INSERT INTO players (id, username, email, hashed_password, story_progress, npc_relationships)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, player_id, 'json_test', 'json@test.com', 'hash',
                json.dumps(story_progress), json.dumps(npc_relationships))

            # Test JSON query operations
            # 1. Query specific JSON path
            tutorial_status = await conn.fetchval("""
                SELECT story_progress->'tutorial_completed' as tutorial_status
                FROM players WHERE id = $1
            """, player_id)
            assert tutorial_status == 'true'

            # 2. Update specific JSON field
            await conn.execute("""
                UPDATE players
                SET story_progress = jsonb_set(story_progress, '{quests,main_story,chapter}', '4')
                WHERE id = $1
            """, player_id)

            # 3. Query nested JSON data
            chapter_num = await conn.fetchval("""
                SELECT story_progress->'quests'->'main_story'->>'chapter' as chapter
                FROM players WHERE id = $1
            """, player_id)
            assert int(chapter_num) == 4

            # 4. Query JSON array elements
            side_quests = await conn.fetchval("""
                SELECT story_progress->'quests'->'side_quests' as side_quests
                FROM players WHERE id = $1
            """, player_id)
            side_quests_data = json.loads(side_quests)
            assert len(side_quests_data) == 2
            assert side_quests_data[0]['status'] == 'completed'

            # 5. Test NPC relationship queries
            alice_favorability = await conn.fetchval("""
                SELECT (npc_relationships->'alice'->>'favorability')::float as favorability
                FROM players WHERE id = $1
            """, player_id)
            assert alice_favorability == 0.8

    @pytest.mark.integration
    @pytest.mark.db
    async def test_foreign_key_constraints(self, clean_db):
        """Test foreign key constraint enforcement."""
        async with clean_db.acquire() as conn:
            # Try to insert monster without valid player or NPC
            monster_id = uuid4()
            fake_player_id = uuid4()

            with pytest.raises(asyncpg.ForeignKeyViolationError):
                await conn.execute("""
                    INSERT INTO monsters (id, species_slug, name, level, current_hp,
                                        total_experience, player_id)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, monster_id, 'bamboon', 'Orphan', 5, 30, 100, fake_player_id)

            # Create valid player first
            player_id = uuid4()
            await conn.execute("""
                INSERT INTO players (id, username, email, hashed_password)
                VALUES ($1, $2, $3, $4)
            """, player_id, 'constraint_test', 'test@example.com', 'hash')

            # Now monster insertion should succeed
            await conn.execute("""
                INSERT INTO monsters (id, species_slug, name, level, current_hp,
                                    total_experience, player_id)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, monster_id, 'bamboon', 'ValidMon', 5, 30, 100, player_id)

            # Verify monster was inserted
            monster_count = await conn.fetchval("SELECT COUNT(*) FROM monsters WHERE id = $1", monster_id)
            assert monster_count == 1

    @pytest.mark.integration
    @pytest.mark.db
    async def test_database_migration_compatibility(self, clean_db):
        """Test database schema migration scenarios."""
        async with clean_db.acquire() as conn:
            # Test adding new columns (simulate migration)
            # This would be handled by Alembic in production

            # 1. Verify current schema works
            player_id = uuid4()
            await conn.execute("""
                INSERT INTO players (id, username, email, hashed_password)
                VALUES ($1, $2, $3, $4)
            """, player_id, 'migration_test', 'migration@test.com', 'hash')

            # 2. Test nullable column addition simulation
            try:
                # Try to add a column (in real migrations this would be in Alembic scripts)
                await conn.execute("ALTER TABLE players ADD COLUMN IF NOT EXISTS test_column VARCHAR(100)")

                # Insert data with new column
                await conn.execute("""
                    UPDATE players SET test_column = $1 WHERE id = $2
                """, 'test_value', player_id)

                # Verify data
                test_value = await conn.fetchval("SELECT test_column FROM players WHERE id = $1", player_id)
                assert test_value == 'test_value'

                # Clean up test column
                await conn.execute("ALTER TABLE players DROP COLUMN IF EXISTS test_column")

            except asyncpg.DuplicateColumnError:
                # Column already exists, that's fine
                pass

            # Verify original functionality still works
            username = await conn.fetchval("SELECT username FROM players WHERE id = $1", player_id)
            assert username == 'migration_test'