"""模板模块导出。"""

from app.template.repository import (
    create_template,
    delete_template_field,
    get_template,
    get_template_field,
    list_templates,
    replace_fields,
    soft_delete,
    update_meta,
)
from app.template.service import (
    delete_field,
    save_fields_with_anchors,
    save_template_from_pdf,
    suggest_table_structure,
    update_field_with_anchor,
)

__all__ = [
    "create_template",
    "delete_field",
    "delete_template_field",
    "get_template",
    "get_template_field",
    "list_templates",
    "replace_fields",
    "save_fields_with_anchors",
    "save_template_from_pdf",
    "soft_delete",
    "suggest_table_structure",
    "update_field_with_anchor",
    "update_meta",
]
