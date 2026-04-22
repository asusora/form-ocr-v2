import { defineStore } from 'pinia';
import { computed, ref } from 'vue';

import {
  deleteTemplateField,
  fetchTemplate,
  saveTemplateFields,
} from '@/api/templates';
import type { BBox } from '@/types/common';
import type { TemplateDetail, TemplateField } from '@/types/template';

/**
 * 为字段配置补齐默认值。
 */
function normalizeTemplateField(field: TemplateField): TemplateField {
  return {
    ...field,
    anchors: field.anchors ?? [],
    options: field.field_type === 'option_select' ? field.options ?? [] : null,
    columns:
      field.field_type === 'table'
        ? field.columns ?? [
            { name: 'col_1', label: '列 1', type: 'text', x_ratio: [0, 1] },
          ]
        : null,
    row_detection:
      field.field_type === 'table'
        ? field.row_detection ?? { mode: 'by_text_rows', count: null }
        : null,
  };
}

/**
 * 创建新的默认字段。
 */
function createDraftField(page: number, sortOrder: number, bbox?: BBox): TemplateField {
  return normalizeTemplateField({
    id: `draft-${crypto.randomUUID()}`,
    page,
    name: `field_${sortOrder + 1}`,
    label: `字段 ${sortOrder + 1}`,
    field_type: 'text',
    bbox: bbox ?? {
      x1: 80,
      y1: 80,
      x2: 300,
      y2: 140,
    },
    anchors: [],
    options: null,
    columns: null,
    row_detection: null,
    sort_order: sortOrder,
  });
}

export const useTemplateEditorStore = defineStore('template-editor', () => {
  const template = ref<TemplateDetail | null>(null);
  const selectedFieldId = ref('');
  const loading = ref(false);
  const saving = ref(false);
  const dirty = ref(false);
  const persistedFieldIds = ref<Set<string>>(new Set());

  const selectedField = computed<TemplateField | null>(() => {
    return template.value?.fields.find((field) => field.id === selectedFieldId.value) ?? null;
  });

  /**
   * 用当前模板字段刷新已持久化字段集合。
   */
  function syncPersistedFieldIds(): void {
    persistedFieldIds.value = new Set(
      (template.value?.fields ?? [])
        .map((field) => field.id)
        .filter((fieldId): fieldId is string => Boolean(fieldId)),
    );
  }

  /**
   * 拉取模板详情。
   */
  async function load(templateId: string): Promise<void> {
    loading.value = true;
    try {
      const detail = await fetchTemplate(templateId);
      template.value = {
        ...detail,
        fields: detail.fields
          .map((field) => normalizeTemplateField(field))
          .sort((left, right) => left.sort_order - right.sort_order),
      };
      syncPersistedFieldIds();
      selectedFieldId.value = template.value.fields[0]?.id ?? '';
      dirty.value = false;
    } finally {
      loading.value = false;
    }
  }

  /**
   * 选中字段。
   */
  function setSelectedField(fieldId: string): void {
    selectedFieldId.value = fieldId;
  }

  /**
   * 创建一个新的草稿字段。
   */
  function createField(page: number, bbox?: BBox): string {
    if (!template.value) {
      return '';
    }

    const field = createDraftField(page, template.value.fields.length, bbox);
    template.value.fields.push(field);
    selectedFieldId.value = field.id ?? '';
    dirty.value = true;
    return field.id ?? '';
  }

  /**
   * 更新指定字段。
   */
  function patchField(fieldId: string, next: Partial<TemplateField>): void {
    if (!template.value) {
      return;
    }

    const index = template.value.fields.findIndex((field) => field.id === fieldId);
    if (index < 0) {
      return;
    }

    const merged = normalizeTemplateField({
      ...template.value.fields[index],
      ...next,
    });
    template.value.fields.splice(index, 1, merged);
    dirty.value = true;
  }

  /**
   * 删除指定字段。
   */
  async function removeField(fieldId: string): Promise<void> {
    if (!template.value) {
      return;
    }

    const shouldCallApi = persistedFieldIds.value.has(fieldId);
    if (shouldCallApi) {
      await deleteTemplateField(template.value.id, fieldId);
    }

    template.value.fields = template.value.fields
      .filter((field) => field.id !== fieldId)
      .map((field, index) => ({ ...field, sort_order: index }));

    if (selectedFieldId.value === fieldId) {
      selectedFieldId.value = template.value.fields[0]?.id ?? '';
    }

    dirty.value = true;
  }

  /**
   * 批量保存模板字段。
   */
  async function saveAll(): Promise<void> {
    if (!template.value) {
      return;
    }

    saving.value = true;
    const templateId = template.value.id;
    const selectedFieldName = selectedField.value?.name;
    try {
      const payload = template.value.fields.map((field, index) =>
        normalizeTemplateField({ ...field, sort_order: index }),
      );
      await saveTemplateFields(templateId, payload);
      const detail = await fetchTemplate(templateId);
      template.value = {
        ...detail,
        fields: detail.fields
          .map((field) => normalizeTemplateField(field))
          .sort((left, right) => left.sort_order - right.sort_order),
      };
      syncPersistedFieldIds();
      selectedFieldId.value =
        template.value.fields.find((field) => field.name === selectedFieldName)?.id ??
        template.value.fields[0]?.id ??
        '';
      dirty.value = false;
    } finally {
      saving.value = false;
    }
  }

  return {
    template,
    selectedFieldId,
    selectedField,
    loading,
    saving,
    dirty,
    load,
    setSelectedField,
    createField,
    patchField,
    removeField,
    saveAll,
  };
});
