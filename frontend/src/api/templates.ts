import { buildApiUrl, http } from './http';

import type { TemplateDetail, TemplateField, TemplateSummary } from '@/types/template';

/**
 * 序列化模板字段写入载荷。
 *
 * 锚点由后端根据当前 bbox 自动提取；前端不应回传旧 anchors，
 * 否则会把新建字段的空数组和已移动字段的陈旧锚点一并写回去。
 */
function serializeTemplateField(field: TemplateField): Omit<TemplateField, 'anchors'> {
  return {
    id: field.id,
    template_id: field.template_id,
    page: field.page,
    name: field.name,
    label: field.label,
    field_type: field.field_type,
    bbox: field.bbox,
    options: field.options,
    columns: field.columns,
    row_detection: field.row_detection,
    sort_order: field.sort_order,
  };
}

/**
 * 获取模板列表。
 */
export async function fetchTemplates(): Promise<TemplateSummary[]> {
  const { data } = await http.get<TemplateSummary[]>('/templates');
  return data;
}

/**
 * 获取模板详情。
 */
export async function fetchTemplate(templateId: string): Promise<TemplateDetail> {
  const { data } = await http.get<TemplateDetail>(`/templates/${templateId}`);
  return data;
}

/**
 * 上传 PDF 并创建模板。
 */
export async function createTemplate(form: FormData): Promise<TemplateDetail> {
  const { data } = await http.post<TemplateDetail>('/templates', form);
  return data;
}

/**
 * 批量保存模板字段。
 */
export async function saveTemplateFields(
  templateId: string,
  fields: TemplateField[],
): Promise<TemplateDetail> {
  const payload = {
    fields: fields.map((field) => ({
      ...serializeTemplateField(field),
      id: field.id?.startsWith('draft-') ? undefined : field.id,
    })),
  };
  const { data } = await http.post<TemplateDetail>(`/templates/${templateId}/fields`, payload);
  return data;
}

/**
 * 更新单个模板字段。
 */
export async function updateTemplateField(
  templateId: string,
  fieldId: string,
  field: TemplateField,
): Promise<TemplateDetail> {
  const { data } = await http.put<TemplateDetail>(
    `/templates/${templateId}/fields/${fieldId}`,
    serializeTemplateField(field),
  );
  return data;
}

/**
 * 删除单个模板字段。
 */
export async function deleteTemplateField(templateId: string, fieldId: string): Promise<void> {
  await http.delete(`/templates/${templateId}/fields/${fieldId}`);
}

/**
 * 生成模板页图像地址。
 */
export function buildTemplatePageUrl(templateId: string, page: number): string {
  return buildApiUrl(`/templates/${templateId}/pages/${page}`);
}
