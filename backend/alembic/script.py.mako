"""${message}"""

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}


def upgrade() -> None:
    """执行数据库升级。"""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """执行数据库回滚。"""
    ${downgrades if downgrades else "pass"}
