import { buildApiUrl, http } from './http';

import type { BBox } from '@/types/common';
import type {
  ExportFormat,
  RecognitionDetail,
  RecognitionField,
} from '@/types/recognition';

/**
 * 创建识别任务。
 */
export async function createRecognition(
  form: FormData,
): Promise<{ id: string; status: string }> {
  const { data } = await http.post<{ id: string; status: string }>('/recognitions', form);
  return data;
}

/**
 * 获取识别任务详情。
 */
export async function fetchRecognition(recognitionId: string): Promise<RecognitionDetail> {
  const { data } = await http.get<RecognitionDetail>(`/recognitions/${recognitionId}`);
  return data;
}

/**
 * 基于新框坐标重新识别单个字段。
 */
export async function reExtractField(
  recognitionId: string,
  fieldId: string,
  aligned_bbox: BBox,
): Promise<RecognitionField> {
  const { data } = await http.post<RecognitionField>(
    `/recognitions/${recognitionId}/re-extract/${fieldId}`,
    { aligned_bbox },
  );
  return data;
}

/**
 * 批量保存识别校对结果。
 */
export async function saveRecognitionFields(
  recognitionId: string,
  fields: RecognitionField[],
): Promise<RecognitionDetail> {
  const payload = {
    fields: fields.map((field) => ({
      id: field.id,
      aligned_bbox: field.aligned_bbox,
      edited_value: field.edited_value,
      alignment_status: field.alignment_status,
    })),
  };
  const { data } = await http.put<RecognitionDetail>(
    `/recognitions/${recognitionId}/fields`,
    payload,
  );
  return data;
}

/**
 * 生成识别页图像地址。
 */
export function buildRecognitionPageUrl(recognitionId: string, page: number): string {
  return buildApiUrl(`/recognitions/${recognitionId}/pages/${page}`);
}

/**
 * 生成识别字段切图片地址。
 */
export function buildRecognitionCropUrl(recognitionId: string, fieldId: string): string {
  return buildApiUrl(`/recognitions/${recognitionId}/crops/${fieldId}`);
}

/**
 * 生成识别结果导出地址。
 */
export function buildRecognitionExportUrl(
  recognitionId: string,
  format: ExportFormat,
): string {
  return buildApiUrl(`/recognitions/${recognitionId}/export?format=${format}`);
}
