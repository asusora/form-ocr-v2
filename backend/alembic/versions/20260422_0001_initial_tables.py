"""创建模板与识别核心表。"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260422_0001"
down_revision = None
branch_labels = None
depends_on = None

field_type_enum = sa.Enum(
    "text",
    "multiline_text",
    "date",
    "checkbox",
    "option_select",
    "signature",
    "table",
    name="field_type_enum",
)
recognition_status_enum = sa.Enum(
    "pending",
    "processing",
    "success",
    "failed",
    name="recognition_status_enum",
)
alignment_status_enum = sa.Enum(
    "auto",
    "manual_adjusted",
    "alignment_failed",
    name="alignment_status_enum",
)


def upgrade() -> None:
    """执行数据库升级。"""
    op.create_table(
        "templates",
        sa.Column("id", sa.CHAR(length=36), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_pdf_path", sa.String(length=512), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("render_dpi", sa.Integer(), nullable=False, server_default="200"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "recognitions",
        sa.Column("id", sa.CHAR(length=36), nullable=False),
        sa.Column("template_id", sa.CHAR(length=36), nullable=False),
        sa.Column("template_snapshot", sa.JSON(), nullable=False),
        sa.Column("input_pdf_path", sa.String(length=512), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", recognition_status_enum, nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["template_id"], ["templates.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "template_fields",
        sa.Column("id", sa.CHAR(length=36), nullable=False),
        sa.Column("template_id", sa.CHAR(length=36), nullable=False),
        sa.Column("page", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=128), nullable=False),
        sa.Column("field_type", field_type_enum, nullable=False),
        sa.Column("bbox", sa.JSON(), nullable=False),
        sa.Column("anchors", sa.JSON(), nullable=False),
        sa.Column("options", sa.JSON(), nullable=True),
        sa.Column("columns", sa.JSON(), nullable=True),
        sa.Column("row_detection", sa.JSON(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["template_id"], ["templates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("template_id", "name", name="uq_template_field_name"),
    )
    op.create_table(
        "recognition_fields",
        sa.Column("id", sa.CHAR(length=36), nullable=False),
        sa.Column("recognition_id", sa.CHAR(length=36), nullable=False),
        sa.Column("template_field_id", sa.CHAR(length=36), nullable=False),
        sa.Column("field_name", sa.String(length=64), nullable=False),
        sa.Column("aligned_bbox", sa.JSON(), nullable=False),
        sa.Column("raw_value", sa.JSON(), nullable=True),
        sa.Column("edited_value", sa.JSON(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("crop_path", sa.String(length=512), nullable=True),
        sa.Column("alignment_status", alignment_status_enum, nullable=False, server_default="auto"),
        sa.ForeignKeyConstraint(["recognition_id"], ["recognitions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """执行数据库回滚。"""
    op.drop_table("recognition_fields")
    op.drop_table("template_fields")
    op.drop_table("recognitions")
    op.drop_table("templates")
