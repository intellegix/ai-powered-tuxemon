# Memory Cleanup Background Task for AI-Powered Tuxemon
# Austin Kidwell | Intellegix | Mobile-First Pokemon-Style Game

from datetime import datetime, timedelta
from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.http import models

from app.config import get_settings
from app.database import qdrant_client

settings = get_settings()


async def cleanup_old_memories():
    """
    Background task to clean up old, low-importance memories.
    Runs daily to maintain optimal vector database performance.

    Retention Policy:
    - Memories with importance < 0.3 and age > 90 days: Delete
    - Memories with importance < 0.5 and age > 180 days: Delete
    - Memories with importance >= 0.7: Keep indefinitely
    """
    try:
        logger.info("🧹 Starting memory cleanup task...")

        # Calculate cutoff timestamps
        cutoff_90_days = datetime.utcnow() - timedelta(days=90)
        cutoff_180_days = datetime.utcnow() - timedelta(days=180)

        # Clean up low-importance, old memories (90+ days)
        low_importance_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="importance",
                    range=models.Range(lt=0.3)
                ),
                models.FieldCondition(
                    key="timestamp",
                    range=models.Range(lt=cutoff_90_days.isoformat())
                )
            ]
        )

        # Get memories to delete
        low_importance_results = qdrant_client.scroll(
            collection_name="npc_memories",
            scroll_filter=low_importance_filter,
            with_vectors=False,
            limit=1000  # Process in batches
        )

        if low_importance_results[0]:
            point_ids = [point.id for point in low_importance_results[0]]
            qdrant_client.delete(
                collection_name="npc_memories",
                points_selector=models.PointIdsList(points=point_ids)
            )
            logger.info(f"🗑️  Deleted {len(point_ids)} low-importance old memories (90+ days)")

        # Clean up medium-importance, very old memories (180+ days)
        medium_importance_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="importance",
                    range=models.Range(gte=0.3, lt=0.5)
                ),
                models.FieldCondition(
                    key="timestamp",
                    range=models.Range(lt=cutoff_180_days.isoformat())
                )
            ]
        )

        medium_importance_results = qdrant_client.scroll(
            collection_name="npc_memories",
            scroll_filter=medium_importance_filter,
            with_vectors=False,
            limit=1000
        )

        if medium_importance_results[0]:
            point_ids = [point.id for point in medium_importance_results[0]]
            qdrant_client.delete(
                collection_name="npc_memories",
                points_selector=models.PointIdsList(points=point_ids)
            )
            logger.info(f"🗑️  Deleted {len(point_ids)} medium-importance old memories (180+ days)")

        # Get final collection stats
        collection_info = qdrant_client.get_collection("npc_memories")
        total_memories = collection_info.points_count

        logger.info(f"✅ Memory cleanup complete. Total memories: {total_memories}")

    except Exception as e:
        logger.error(f"❌ Memory cleanup failed: {e}")


async def optimize_vector_database():
    """Optimize vector database for better performance."""
    try:
        logger.info("⚡ Optimizing vector database...")

        # Force index optimization (compaction) for better search performance
        qdrant_client.update_collection(
            collection_name="npc_memories",
            optimizer_config=models.OptimizersConfigDiff(
                indexing_threshold=10000,  # Build index after 10K points
                max_optimization_threads=2  # Optimize performance
            )
        )

        logger.info("✅ Vector database optimization complete")

    except Exception as e:
        logger.error(f"❌ Vector optimization failed: {e}")


# Scheduled task configuration
MEMORY_CLEANUP_SCHEDULE = {
    "task": cleanup_old_memories,
    "schedule": "daily",  # Run once per day
    "time": "02:00",  # 2 AM when usage is low
    "description": "Clean up old, low-importance NPC memories"
}

VECTOR_OPTIMIZE_SCHEDULE = {
    "task": optimize_vector_database,
    "schedule": "weekly", # Run once per week
    "time": "03:00",  # 3 AM Sunday
    "description": "Optimize vector database for performance"
}