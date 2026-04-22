import type { BBox } from './common';

export type FieldType =
  | 'text'
  | 'multiline_text'
  | 'date'
  | 'checkbox'
  | 'option_select'
  | 'signature'
  | 'table';

/**
 * 表示字段自动提取的锚点。
 */
export interface AnchorDef {
  text: string;
  template_bbox: BBox;
  offset_from_field: [number, number];
}

/**
 * 表示单选项字段的可选值定义。
 */
export interface OptionDef {
  value: string;
  labels: string[];
}

/**
 * 表示表格字段中的列定义。
 */
export interface ColumnDef {
  name: string;
  label: string;
  type: 'text' | 'multiline_text' | 'date' | 'checkbox';
  x_ratio: [number, number];
}

/**
 * 表示表格行识别策略。
 */
export interface RowDetectionConfig {
  mode: 'by_horizontal_lines' | 'by_text_rows' | 'fixed_count';
  count?: number | null;
}

/**
 * 表示模板中的单个字段定义。
 */
export interface TemplateField {
  id?: string;
  template_id?: string;
  page: number;
  name: string;
  label: string;
  field_type: FieldType;
  bbox: BBox;
  anchors: AnchorDef[];
  options: OptionDef[] | null;
  columns: ColumnDef[] | null;
  row_detection: RowDetectionConfig | null;
  sort_order: number;
}

/**
 * 表示模板列表摘要。
 */
export interface TemplateSummary {
  id: string;
  name: string;
  description: string | null;
  page_count: number;
  field_count: number;
  updated_at: string;
}

/**
 * 表示模板详情。
 */
export interface TemplateDetail {
  id: string;
  name: string;
  description: string | null;
  page_count: number;
  render_dpi: number;
  created_at: string;
  updated_at: string;
  fields: TemplateField[];
}
