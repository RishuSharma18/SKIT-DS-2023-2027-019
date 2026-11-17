"""Associate parking slots with a camera."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002_slot_camera_id"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "parking_slots",
        sa.Column("camera_id", sa.String(length=50), nullable=False, server_default="cam-1"),
    )
    op.create_index("ix_parking_slots_camera_id", "parking_slots", ["camera_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_parking_slots_camera_id", table_name="parking_slots")
    op.drop_column("parking_slots", "camera_id")
