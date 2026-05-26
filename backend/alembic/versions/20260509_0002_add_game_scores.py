from typing import Sequence
from uuid import uuid4

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260509_0002"
down_revision: str | None = "20260508_0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "game_scores",
        sa.Column("score_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("game_name", sa.String(length=50), nullable=False, server_default="snake"),
        sa.Column(
            "played_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"]),
        sa.PrimaryKeyConstraint("score_id"),
    )
    op.create_index("ix_game_scores_user_id", "game_scores", ["user_id"], unique=False)
    op.create_index("ix_game_scores_game_name", "game_scores", ["game_name"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_game_scores_game_name", table_name="game_scores")
    op.drop_index("ix_game_scores_user_id", table_name="game_scores")
    op.drop_table("game_scores")
