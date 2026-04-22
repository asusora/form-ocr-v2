import type { BBox } from './common';
import type { ColumnDef, FieldType, OptionDef, RowDetectionConfig } from './template';

export type RecognitionStatus = 'pending' | 'processing' | 'success' | 'failed';
export type AlignmentStatus = 'auto' | 'manual_adjusted' | 'alignment_failed';
export type ExportFormat = 'json' | 'xlsx';

/**
 * 表示识别结果中的单个字段。
 */
export interface RecognitionField {
  id: string;
  template_field_id: string;
  field_name: string;
  field_label?: string;
  page?: number;
  field_type?: FieldType;
  sort_order?: number;
  options?: OptionDef[] | null;
  columns?: ColumnDef[] | null;
  row_detection?: RowDetectionConfig | null;
  aligned_bbox: BBox;
  raw_value: unknown;
  edited_value: unknown;
  confidence: number | null;
  crop_path: string | null;
  alignment_status: AlignmentStatus;
}

/**
 * 表示识别详情响应。
 */
export interface RecognitionDetail {
  id: string;
  template_id: string;
  template_name?: string;
  status: RecognitionStatus;
  error_message: string | null;
  page_count: number;
  created_at: string;
  updated_at: string;
  fields: RecognitionField[];
}
