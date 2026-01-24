"""Add document_title to bounding_boxes table

Revision ID: 3_add_doc_title
Revises: 2_add_api_key_id_to_sessions
Create Date: 2025-12-18 21:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3_add_doc_title'
down_revision: Union[str, Sequence[str], None] = '2_add_api_key_id_to_sessions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add document_title column to bounding_boxes table
    op.add_column('bounding_boxes', sa.Column('document_title', sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Drop document_title column
    op.drop_column('bounding_boxes', 'document_title')
