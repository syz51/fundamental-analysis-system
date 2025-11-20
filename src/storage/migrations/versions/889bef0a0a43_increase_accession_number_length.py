"""increase_accession_number_length

Revision ID: 889bef0a0a43
Revises: 774d9680756d
Create Date: 2025-11-19 15:54:50.501572

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '889bef0a0a43'
down_revision: Union[str, Sequence[str], None] = '774d9680756d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Increase accession_number from VARCHAR(20) to VARCHAR(30) to support 4-digit year format
    op.execute("ALTER TABLE document_registry.filings ALTER COLUMN accession_number TYPE VARCHAR(30)")


def downgrade() -> None:
    """Downgrade schema."""
    # Revert accession_number back to VARCHAR(20)
    op.execute("ALTER TABLE document_registry.filings ALTER COLUMN accession_number TYPE VARCHAR(20)")
