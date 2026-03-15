"""Initial appointments table

Revision ID: 0001
Revises:
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "appointments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("booking_ref", sa.String(10), nullable=False, unique=True),
        sa.Column("patient_name", sa.String(200), nullable=False),
        sa.Column("phone", sa.String(50), nullable=False),
        sa.Column("appointment_date", sa.Date(), nullable=False),
        sa.Column("appointment_time", sa.Time(), nullable=False),
        sa.Column("reason_for_visit", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="CONFIRMED"),
        sa.Column("google_event_id", sa.String(200), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
        ),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_appointments_booking_ref", "appointments", ["booking_ref"])
    op.create_index("ix_appointments_date_time", "appointments", ["appointment_date", "appointment_time"])


def downgrade() -> None:
    op.drop_index("ix_appointments_date_time", table_name="appointments")
    op.drop_index("ix_appointments_booking_ref", table_name="appointments")
    op.drop_table("appointments")
