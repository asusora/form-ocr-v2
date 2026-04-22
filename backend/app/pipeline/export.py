"""识别结果导出模块。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from openpyxl import Workbook


def _resolved_value(field: dict[str, Any]) -> Any:
    """优先返回人工编辑后的字段值。"""
    return field["edited_value"] if field.get("edited_value") is not None else field.get("raw_value")


def build_json_output(recognition_payload: dict[str, Any]) -> dict[str, Any]:
    """构造用于下载的 JSON 数据。"""
    field_map = {
        field["name"]: _resolved_value(field)
        for field in recognition_payload.get("fields", [])
    }
    return {
        "recognition_id": recognition_payload.get("id"),
        "template_id": recognition_payload.get("template_id"),
        "template_name": recognition_payload.get("template_name"),
        "status": recognition_payload.get("status"),
        "fields": field_map,
        "field_details": [
            {
                "name": field.get("name"),
                "label": field.get("label"),
                "field_type": field.get("field_type"),
                "value": _resolved_value(field),
                "raw_value": field.get("raw_value"),
                "edited_value": field.get("edited_value"),
            }
            for field in recognition_payload.get("fields", [])
        ],
    }


def _stringify_excel_value(value: Any) -> str | int | float | bool | None:
    """把复杂值转成 Excel 可写入的标量。"""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return json.dumps(value, ensure_ascii=False)


def _safe_sheet_name(name: str, fallback: str) -> str:
    """生成符合 Excel 约束的工作表名称。"""
    invalid_chars = set(r"[]:*?/\\")
    candidate = "".join("_" if char in invalid_chars else char for char in name).strip()
    return (candidate or fallback)[:31]


def write_excel(recognition_payload: dict[str, Any], destination: str | Path) -> None:
    """把识别结果写入 Excel。"""
    workbook = Workbook()
    summary_sheet = workbook.active
    summary_sheet.title = _safe_sheet_name(
        str(recognition_payload.get("template_name") or "Recognition"),
        "Recognition",
    )
    summary_sheet.append(["字段名", "显示名", "字段类型", "值"])

    table_fields: list[dict[str, Any]] = []
    for field in recognition_payload.get("fields", []):
        value = _resolved_value(field)
        if field.get("field_type") == "table" and isinstance(value, list):
            table_fields.append(field)
            summary_sheet.append(
                [
                    field.get("name"),
                    field.get("label"),
                    field.get("field_type"),
                    f"见工作表：{_safe_sheet_name(str(field.get('label') or field.get('name')), 'Table')}",
                ]
            )
            continue
        summary_sheet.append(
            [
                field.get("name"),
                field.get("label"),
                field.get("field_type"),
                _stringify_excel_value(value),
            ]
        )

    for table_field in table_fields:
        sheet_name = _safe_sheet_name(
            str(table_field.get("label") or table_field.get("name") or "Table"),
            "Table",
        )
        sheet = workbook.create_sheet(sheet_name)
        rows = _resolved_value(table_field)
        if not isinstance(rows, list) or not rows:
            sheet.append(["无表格数据"])
            continue

        headers = list(rows[0].keys()) if isinstance(rows[0], dict) else ["value"]
        sheet.append(headers)
        for row in rows:
            if isinstance(row, dict):
                sheet.append([_stringify_excel_value(row.get(header)) for header in headers])
                continue
            sheet.append([_stringify_excel_value(row)])

    workbook.save(Path(destination))
