<template>
  <div class="field-panel">
    <ElEmpty v-if="!fields.length" description="当前页没有识别字段。" />

    <article
      v-for="field in fields"
      :key="field.id"
      class="page-card field-panel__card"
      :class="{ 'field-panel__card--selected': selectedId === field.id }"
      @click="emit('select', field.id)"
    >
      <header class="field-panel__header">
        <div>
          <div class="field-panel__label">{{ field.field_label || field.field_name }}</div>
          <div class="field-panel__name">{{ field.field_name }}</div>
        </div>

        <div class="field-panel__meta">
          <ElTag
            :type="field.alignment_status === 'alignment_failed' ? 'danger' : field.edited_value != null ? 'success' : 'info'"
          >
            {{ field.alignment_status }}
          </ElTag>
          <span v-if="field.confidence != null" class="field-panel__confidence">
            置信度 {{ Math.round(field.confidence * 100) }}%
          </span>
        </div>
      </header>

      <div class="field-panel__body">
        <ElInput
          v-if="resolveFieldType(field) === 'text' || resolveFieldType(field) === 'multiline_text' || resolveFieldType(field) === 'date'"
          :model-value="resolveStringValue(field)"
          :rows="resolveFieldType(field) === 'multiline_text' ? 4 : 2"
          :type="resolveFieldType(field) === 'multiline_text' ? 'textarea' : 'textarea'"
          @update:model-value="emit('update-value', field.id, $event)"
        />

        <ElCheckbox
          v-else-if="resolveFieldType(field) === 'checkbox'"
          :model-value="Boolean(resolveValue(field))"
          @update:model-value="emit('update-value', field.id, $event)"
        >
          已勾选
        </ElCheckbox>

        <ElRadioGroup
          v-else-if="resolveFieldType(field) === 'option_select' && field.options?.length"
          :model-value="String(resolveValue(field) ?? '')"
          @update:model-value="emit('update-value', field.id, $event)"
        >
          <ElRadio v-for="option in field.options" :key="option.value" :label="option.value">
            {{ option.value }} · {{ option.labels.join(' / ') }}
          </ElRadio>
        </ElRadioGroup>

        <div v-else-if="resolveFieldType(field) === 'signature'" class="field-panel__signature">
          <img v-if="resolveImageSrc(field)" :src="resolveImageSrc(field)" alt="signature crop" />
          <ElEmpty v-else description="签名字段仅保留切图片预览。" />
        </div>

        <TableFieldEditor
          v-else-if="resolveFieldType(field) === 'table'"
          :columns="resolveColumns(field)"
          :model-value="resolveRows(field)"
          @update:model-value="emit('update-value', field.id, $event)"
        />

        <ElInput
          v-else
          :model-value="resolveStringValue(field)"
          type="textarea"
          :rows="2"
          @update:model-value="emit('update-value', field.id, $event)"
        />
      </div>

      <footer class="field-panel__footer">
        <ElButton plain size="small" @click.stop="emit('re-extract', field.id)">重新识别</ElButton>
      </footer>
    </article>
  </div>
</template>

<script setup lang="ts">
import { buildApiUrl } from '@/api/http';
import type { RecognitionField } from '@/types/recognition';

import TableFieldEditor from './TableFieldEditor.vue';

const props = defineProps<{
  fields: RecognitionField[];
  selectedId: string;
}>();

const emit = defineEmits<{
  select: [string];
  'update-value': [string, unknown];
  're-extract': [string];
}>();

/**
 * 解析字段类型，优先使用后端返回的元数据。
 */
function resolveFieldType(field: RecognitionField): string {
  if (field.field_type) {
    return field.field_type;
  }

  if (Array.isArray(resolveValue(field))) {
    return 'table';
  }

  if (typeof resolveValue(field) === 'boolean') {
    return 'checkbox';
  }

  return 'text';
}

/**
 * 获取字段当前展示值，优先取编辑值。
 */
function resolveValue(field: RecognitionField): unknown {
  return field.edited_value ?? field.raw_value;
}

/**
 * 将字段值转成字符串，便于文本框展示。
 */
function resolveStringValue(field: RecognitionField): string {
  const value = resolveValue(field);
  if (value == null) {
    return '';
  }
  return typeof value === 'string' ? value : JSON.stringify(value, null, 2);
}

/**
 * 解析表格列定义。
 */
function resolveColumns(field: RecognitionField) {
  if (field.columns?.length) {
    return field.columns.map((column) => ({
      name: column.name,
      label: column.label,
      type: column.type,
    }));
  }

  const firstRow = Array.isArray(resolveValue(field))
    ? (resolveValue(field) as Record<string, unknown>[])[0]
    : null;
  return Object.keys(firstRow ?? {});
}

/**
 * 解析表格行数据。
 */
function resolveRows(field: RecognitionField): Record<string, unknown>[] {
  const value = resolveValue(field);
  return Array.isArray(value) ? (value as Record<string, unknown>[]) : [];
}

/**
 * 解析签名切图地址。
 */
function resolveImageSrc(field: RecognitionField): string {
  if (!field.crop_path) {
    return '';
  }

  if (field.crop_path.startsWith('http://') || field.crop_path.startsWith('https://')) {
    return field.crop_path;
  }

  return field.crop_path.startsWith('/api/') || field.crop_path.startsWith('/')
    ? field.crop_path
    : buildApiUrl(`/${field.crop_path}`);
}
</script>

<style scoped>
.field-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.field-panel__card {
  padding: 18px;
  cursor: pointer;
  transition:
    border-color 0.2s ease,
    transform 0.2s ease;
}

.field-panel__card:hover,
.field-panel__card--selected {
  border: 1px solid rgba(15, 118, 110, 0.36);
  transform: translateY(-1px);
}

.field-panel__header,
.field-panel__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.field-panel__label {
  font-size: 16px;
  font-weight: 700;
}

.field-panel__name {
  margin-top: 4px;
  color: var(--muted);
  font-size: 13px;
}

.field-panel__meta {
  display: flex;
  align-items: center;
  gap: 10px;
}

.field-panel__confidence {
  color: var(--muted);
  font-size: 12px;
}

.field-panel__body {
  margin-top: 14px;
}

.field-panel__footer {
  margin-top: 12px;
}

.field-panel__signature img {
  display: block;
  max-width: 100%;
  border: 1px solid var(--line);
  border-radius: 12px;
}
</style>
