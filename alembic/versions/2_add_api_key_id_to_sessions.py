"""Add api_key_id to sessions table

Revision ID: 2_add_api_key_id_to_sessions
Revises: 6f00f76a7863
Create Date: 2025-12-09 12:29:46.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2_add_api_key_id_to_sessions'
down_revision: Union[str, Sequence[str], None] = '6f00f76a7863'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add api_key_id column to sessions table
    op.add_column('sessions', sa.Column('api_key_id', sa.Integer(), nullable=True))
    
    # Create index for api_key_id
    op.create_index(op.f('ix_sessions_api_key_id'), 'sessions', ['api_key_id'], unique=False)
    
    # Create foreign key constraint for api_key_id
    op.create_foreign_key(
        'fk_sessions_api_key_id_api_keys',
        'sessions',
        'api_keys',
        ['api_key_id'],
        ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop foreign key constraint first
    op.drop_constraint('fk_sessions_api_key_id_api_keys', 'sessions', type_='foreignkey')
    
    # Drop index
    op.drop_index(op.f('ix_sessions_api_key_id'), table_name='sessions')
    
    # Drop api_key_id column
    op.drop_column('sessions', 'api_key_id')