"""
Test Configuration and Fixtures for AI-Powered Tuxemon Backend
Austin Kidwell | Intellegix | Mobile-First Pokemon-Style Game

Provides comprehensive test fixtures for async testing, database management,
AI service mocking, and test data generation.
"""

import asyncio
import os
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from typing import AsyncGenerator, Dict, Any, Optional
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, MagicMock, patch

import asyncpg
from fastapi.testclient import TestClient
from httpx import AsyncClient
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from redis.asyncio import Redis

# Import app components
from app.main import app
from app.core.config import settings
from app.core.database import DatabaseManager
from app.models.player import Player, PlayerCreate
from app.models.npc import NPC, NPCCreate
from app.models.monster import Monster, MonsterCreate
from app.ai.memory_manager import MemoryManager
from app.ai.cost_tracker import CostTracker
from app.ai.personality import PersonalityTraits


# Test environment configuration
TEST_DATABASE_URL = "postgresql://postgres:test@localhost:5432/tuxemon_test"
TEST_REDIS_URL = "redis://localhost:6379/1"
TEST_QDRANT_URL = "http://localhost:6333"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_db() -> AsyncGenerator[asyncpg.Pool, None]:
    """Create test database connection pool."""
    # Create test database if it doesn't exist
    conn = await asyncpg.connect(
        host="localhost",
        port=5432,
        user="postgres",
        password="test",
        database="postgres"
    )

    try:
        await conn.execute("CREATE DATABASE tuxemon_test")
    except asyncpg.DuplicateDatabaseError:
        pass  # Database already exists
    finally:
        await conn.close()

    # Connect to test database
    pool = await asyncpg.create_pool(TEST_DATABASE_URL, min_size=1, max_size=10)

    # Run migrations/schema setup here if needed
    # For now, we'll assume schema exists or create basic tables

    yield pool

    # Cleanup
    await pool.close()


@pytest_asyncio.fixture
async def db_session(test_db: asyncpg.Pool) -> AsyncGenerator[asyncpg.Connection, None]:
    """Provide database session with transaction rollback."""
    async with test_db.acquire() as conn:
        async with conn.transaction():
            yield conn
            # Transaction automatically rolls back at end of fixture


@pytest_asyncio.fixture
async def test_redis() -> AsyncGenerator[Redis, None]:
    """Provide Redis connection for testing."""
    redis_client = Redis.from_url(TEST_REDIS_URL, decode_responses=True)

    # Clear test database
    await redis_client.flushdb()

    yield redis_client

    # Cleanup
    await redis_client.flushdb()
    await redis_client.close()


@pytest_asyncio.fixture
async def test_qdrant() -> AsyncGenerator[QdrantClient, None]:
    """Provide Qdrant client with test collection."""
    client = QdrantClient(url=TEST_QDRANT_URL)

    # Create test collection for memories
    collection_name = f"test_memories_{uuid4().hex[:8]}"

    try:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE)
        )

        # Store collection name for cleanup
        client._test_collection = collection_name

        yield client

    finally:
        # Cleanup test collection
        try:
            client.delete_collection(collection_name)
        except Exception:
            pass  # Collection may not exist


@pytest.fixture
def test_client() -> TestClient:
    """Provide FastAPI test client."""
    return TestClient(app)


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Provide async HTTP client for testing."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


# Mock AI Services
@pytest.fixture
def mock_claude_api():
    """Mock Claude API for testing."""
    with patch('app.ai.dialogue_generator.anthropic.AsyncAnthropic') as mock:
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = [AsyncMock()]
        mock_response.content[0].text = "Hello! How can I help you today?"
        mock_client.messages.create.return_value = mock_response
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_local_llm():
    """Mock local LLM (Ollama) for testing."""
    with patch('app.ai.dialogue_generator.httpx.AsyncClient') as mock:
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "response": "Hello! I'm a friendly NPC. How are you doing?",
            "done": True
        }
        mock_client.post.return_value = mock_response
        mock.return_value.__aenter__.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_sentence_transformer():
    """Mock sentence transformer for embeddings."""
    with patch('app.ai.memory_manager.SentenceTransformer') as mock:
        mock_instance = MagicMock()
        mock_instance.encode.return_value = [0.1] * 384  # 384-dimensional vector
        mock.return_value = mock_instance
        yield mock_instance


# Test Data Fixtures
@pytest.fixture
def sample_player_data() -> PlayerCreate:
    """Provide sample player data for testing."""
    return PlayerCreate(
        username=f"test_player_{uuid4().hex[:8]}",
        email=f"test_{uuid4().hex[:8]}@example.com",
        password="test_password_123"
    )


@pytest.fixture
def sample_npc_data() -> NPCCreate:
    """Provide sample NPC data for testing."""
    return NPCCreate(
        slug=f"test_npc_{uuid4().hex[:8]}",
        name="Test NPC Alice",
        sprite_name="trainer_alice",
        position_x=100,
        position_y=100,
        map_name="test_town",
        facing_direction="down",
        is_trainer=True,
        can_battle=True,
        approachable=True,
        personality_traits=PersonalityTraits(
            openness=0.8,
            conscientiousness=0.6,
            extraversion=0.7,
            agreeableness=0.8,
            neuroticism=0.3,
            curiosity=0.9,
            verbosity=0.7,
            humor=0.6,
            friendliness=0.8,
            battle_enthusiasm=0.8
        ),
        schedule={
            "09:00": {"x": 100, "y": 100, "activity": "waiting"},
            "12:00": {"x": 150, "y": 100, "activity": "training"},
            "15:00": {"x": 200, "y": 150, "activity": "exploring"}
        }
    )


@pytest.fixture
def sample_monster_data() -> MonsterCreate:
    """Provide sample monster data for testing."""
    return MonsterCreate(
        species="Bamboon",
        name="TestBamboon",
        level=5,
        experience=120,
        stats={
            "hp": 45,
            "max_hp": 45,
            "attack": 30,
            "defense": 25,
            "speed": 35
        },
        moves=[
            {
                "name": "Tackle",
                "type": "normal",
                "power": 35,
                "accuracy": 95,
                "pp": 15,
                "current_pp": 15
            }
        ],
        personality_traits={
            "nature": "brave",
            "characteristic": "likes_to_fight"
        }
    )


@pytest_asyncio.fixture
async def sample_player(db_session: asyncpg.Connection, sample_player_data: PlayerCreate) -> Player:
    """Create sample player in database."""
    # This would use your actual player creation logic
    player_id = uuid4()
    await db_session.execute(
        """
        INSERT INTO players (id, username, email, password_hash, position_x, position_y, current_map)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        """,
        player_id,
        sample_player_data.username,
        sample_player_data.email,
        "$2b$12$example_hash",  # Mock password hash
        0, 0, "starter_town"
    )

    return Player(
        id=player_id,
        username=sample_player_data.username,
        email=sample_player_data.email,
        position_x=0,
        position_y=0,
        current_map="starter_town",
        level=1,
        experience=0,
        npc_relationships={},
        story_progress={},
        created_at=datetime.utcnow(),
        last_active=datetime.utcnow()
    )


@pytest_asyncio.fixture
async def sample_npc(db_session: asyncpg.Connection, sample_npc_data: NPCCreate) -> NPC:
    """Create sample NPC in database."""
    npc_id = uuid4()
    await db_session.execute(
        """
        INSERT INTO npcs (id, slug, name, sprite_name, position_x, position_y, map_name,
                         facing_direction, is_trainer, can_battle, approachable,
                         personality_traits, schedule)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
        """,
        npc_id,
        sample_npc_data.slug,
        sample_npc_data.name,
        sample_npc_data.sprite_name,
        sample_npc_data.position_x,
        sample_npc_data.position_y,
        sample_npc_data.map_name,
        sample_npc_data.facing_direction,
        sample_npc_data.is_trainer,
        sample_npc_data.can_battle,
        sample_npc_data.approachable,
        sample_npc_data.personality_traits.model_dump() if sample_npc_data.personality_traits else {},
        sample_npc_data.schedule
    )

    return NPC(
        id=npc_id,
        slug=sample_npc_data.slug,
        name=sample_npc_data.name,
        sprite_name=sample_npc_data.sprite_name,
        position_x=sample_npc_data.position_x,
        position_y=sample_npc_data.position_y,
        map_name=sample_npc_data.map_name,
        facing_direction=sample_npc_data.facing_direction,
        is_trainer=sample_npc_data.is_trainer,
        can_battle=sample_npc_data.can_battle,
        approachable=sample_npc_data.approachable,
        personality_traits=sample_npc_data.personality_traits.model_dump() if sample_npc_data.personality_traits else {},
        schedule=sample_npc_data.schedule,
        dialogue_cache={},
        total_interactions=0,
        last_interaction=None,
        created_at=datetime.utcnow()
    )


# AI Testing Utilities
@pytest.fixture
def sample_memory_content() -> Dict[str, Any]:
    """Provide sample memory content for testing."""
    return {
        "content": "The player asked about rare monsters in the forest area.",
        "importance": 0.8,
        "interaction_type": "dialogue",
        "emotional_context": "curious",
        "tags": ["rare_monsters", "forest", "exploration"]
    }


@pytest.fixture
def cost_tracker_with_history() -> CostTracker:
    """Provide cost tracker with sample usage history."""
    tracker = CostTracker()
    # Add sample cost history
    tracker._daily_costs = {
        datetime.now().date(): 25.50,
        (datetime.now() - timedelta(days=1)).date(): 18.75,
        (datetime.now() - timedelta(days=2)).date(): 32.20
    }
    return tracker


# Performance Testing Utilities
@pytest.fixture
def performance_monitor():
    """Provide performance monitoring utilities."""
    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.memory_usage = {}

        def start_timing(self):
            self.start_time = asyncio.get_event_loop().time()

        def get_elapsed_ms(self) -> float:
            if not self.start_time:
                return 0
            return (asyncio.get_event_loop().time() - self.start_time) * 1000

        def assert_response_time(self, max_ms: float):
            elapsed = self.get_elapsed_ms()
            assert elapsed <= max_ms, f"Response time {elapsed:.2f}ms exceeded limit {max_ms}ms"

    return PerformanceMonitor()


# Cleanup utilities
def pytest_runtest_teardown(item, nextitem):
    """Clean up after each test."""
    # Clear any global state if needed
    pass


def pytest_sessionfinish(session, exitstatus):
    """Clean up after test session."""
    # Final cleanup if needed
    pass