"""add_validation_sessions_table

Revision ID: a35f1091313c
Revises: 3_add_doc_title
Create Date: 2025-12-20 05:36:24.605311

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a35f1091313c'
down_revision: Union[str, Sequence[str], None] = '3_add_doc_title'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
