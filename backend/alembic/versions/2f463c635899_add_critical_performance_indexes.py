"""Add critical performance indexes

Revision ID: 2f463c635899
Revises: 
Create Date: 2026-01-27 15:27:22.519265

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2f463c635899'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add critical database indexes for performance optimization."""

    # Critical foreign key indexes - highest ROI for performance
    op.create_index(
        'idx_monsters_player_id',
        'monsters',
        ['player_id'],
        postgresql_concurrently=True,
        if_not_exists=True
    )

    op.create_index(
        'idx_monsters_npc_id',
        'monsters',
        ['npc_id'],
        postgresql_concurrently=True,
        if_not_exists=True
    )

    op.create_index(
        'idx_monsters_species_slug',
        'monsters',
        ['species_slug'],
        postgresql_concurrently=True,
        if_not_exists=True
    )

    op.create_index(
        'idx_npcs_map_name',
        'npcs',
        ['map_name'],
        postgresql_concurrently=True,
        if_not_exists=True
    )

    op.create_index(
        'idx_players_current_map',
        'players',
        ['current_map'],
        postgresql_concurrently=True,
        if_not_exists=True
    )

    # Composite indexes for common query patterns
    op.create_index(
        'idx_npcs_map_position',
        'npcs',
        ['map_name', 'position_x', 'position_y'],
        postgresql_concurrently=True,
        if_not_exists=True
    )

    op.create_index(
        'idx_monsters_player_obtained',
        'monsters',
        ['player_id', 'obtained_at'],
        postgresql_concurrently=True,
        if_not_exists=True
    )

    # Index for inventory queries (if player_inventory_slots table exists)
    try:
        op.create_index(
            'idx_inventory_player_item',
            'player_inventory_slots',
            ['player_id', 'item_slug'],
            postgresql_concurrently=True,
            if_not_exists=True
        )
    except Exception:
        # Table might not exist yet - will be created in future migration
        pass


def downgrade() -> None:
    """Remove the performance indexes."""

    # Drop composite indexes first
    op.drop_index('idx_inventory_player_item', 'player_inventory_slots', if_exists=True)
    op.drop_index('idx_monsters_player_obtained', 'monsters', if_exists=True)
    op.drop_index('idx_npcs_map_position', 'npcs', if_exists=True)

    # Drop single-column indexes
    op.drop_index('idx_players_current_map', 'players', if_exists=True)
    op.drop_index('idx_npcs_map_name', 'npcs', if_exists=True)
    op.drop_index('idx_monsters_species_slug', 'monsters', if_exists=True)
    op.drop_index('idx_monsters_npc_id', 'monsters', if_exists=True)
    op.drop_index('idx_monsters_player_id', 'monsters', if_exists=True)
