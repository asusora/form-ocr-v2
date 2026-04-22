<template>
  <section class="page-card field-config-panel">
    <header class="field-config-panel__header">
      <div>
        <h2 class="section-title">字段配置</h2>
        <p class="section-desc">配置字段名称、类型、坐标以及类型专属选项。</p>
      </div>
      <ElButton v-if="draft" plain type="danger" @click="emit('remove')">删除字段</ElButton>
    </header>

    <ElEmpty v-if="!draft" description="请先在左侧选择一个字段。" />

    <ElForm v-else label-position="top" class="field-config-panel__form">
      <div class="field-config-panel__grid">
        <ElFormItem label="字段名">
          <ElInput v-model.trim="draft.name" />
        </ElFormItem>
        <ElFormItem label="显示名">
          <ElInput v-model.trim="draft.label" />
        </ElFormItem>
        <ElFormItem label="页码">
          <ElInputNumber v-model="draft.page" :min="1" :step="1" />
        </ElFormItem>
        <ElFormItem label="排序">
          <ElInputNumber v-model="draft.sort_order" :min="0" :step="1" />
        </ElFormItem>
      </div>

      <ElFormItem label="字段类型">
        <ElSelect v-model="draft.field_type" @change="handleFieldTypeChange">
          <ElOption label="文本" value="text" />
          <ElOption label="多行文本" value="multiline_text" />
          <ElOption label="日期" value="date" />
          <ElOption label="勾选框" value="checkbox" />
          <ElOption label="单选项" value="option_select" />
          <ElOption label="签名" value="signature" />
          <ElOption label="表格" value="table" />
        </ElSelect>
      </ElFormItem>

      <section class="field-config-panel__bbox">
        <h3>坐标框</h3>
        <div class="field-config-panel__grid">
          <ElFormItem label="x1">
            <ElInputNumber v-model="draft.bbox.x1" :step="1" />
          </ElFormItem>
          <ElFormItem label="y1">
            <ElInputNumber v-model="draft.bbox.y1" :step="1" />
          </ElFormItem>
          <ElFormItem label="x2">
            <ElInputNumber v-model="draft.bbox.x2" :step="1" />
          </ElFormItem>
          <ElFormItem label="y2">
            <ElInputNumber v-model="draft.bbox.y2" :step="1" />
          </ElFormItem>
        </div>
      </section>

      <section v-if="draft.field_type === 'option_select'" class="field-config-panel__section">
        <div class="field-config-panel__section-head">
          <h3>选项定义</h3>
          <ElButton size="small" @click="addOption">新增选项</ElButton>
        </div>

        <ElEmpty v-if="!draft.options?.length" description="当前还没有选项，至少添加一个。" />

        <div v-else class="field-config-panel__stack">
          <div v-for="(option, index) in draft.options" :key="index" class="option-row">
            <ElInput v-model.trim="option.value" placeholder="归一化值，例如 yes" />
            <ElInput
              :model-value="option.labels.join(', ')"
              placeholder="匹配词，用逗号分隔"
              @update:model-value="handleOptionLabelsChange(index, $event)"
            />
            <ElButton plain type="danger" @click="removeOption(index)">删除</ElButton>
          </div>
        </div>
      </section>

      <section v-if="draft.field_type === 'table'" class="field-config-panel__section">
        <div class="field-config-panel__section-head">
          <h3>表格列定义</h3>
          <ElButton size="small" @click="addColumn">新增列</ElButton>
        </div>

        <ElFormItem label="行检测模式">
          <ElSelect v-model="draft.row_detection!.mode">
            <ElOption label="按文本行聚类" value="by_text_rows" />
            <ElOption label="按横线检测" value="by_horizontal_lines" />
            <ElOption label="固定行数" value="fixed_count" />
          </ElSelect>
        </ElFormItem>

        <ElFormItem v-if="draft.row_detection?.mode === 'fixed_count'" label="固定行数">
          <ElInputNumber v-model="draft.row_detection!.count" :min="1" :step="1" />
        </ElFormItem>

        <ElEmpty v-if="!draft.columns?.length" description="当前还没有表格列定义。" />

        <div v-else class="field-config-panel__stack">
          <div v-for="(column, index) in draft.columns" :key="index" class="column-row">
            <ElInput v-model.trim="column.name" placeholder="列英文名" />
            <ElInput v-model.trim="column.label" placeholder="列显示名" />
            <ElSelect v-model="column.type">
              <ElOption label="文本" value="text" />
              <ElOption label="多行文本" value="multiline_text" />
              <ElOption label="日期" value="date" />
              <ElOption label="勾选框" value="checkbox" />
            </ElSelect>
            <ElInputNumber v-model="column.x_ratio[0]" :step="0.05" :min="0" :max="1" />
            <ElInputNumber v-model="column.x_ratio[1]" :step="0.05" :min="0" :max="1" />
            <ElButton plain type="danger" @click="removeColumn(index)">删除</ElButton>
          </div>
        </div>
      </section>

      <p class="field-config-panel__hint">右侧修改会自动暂存，点击顶部“保存模板字段”后统一提交。</p>
    </ElForm>
  </section>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';

import type { TemplateField } from '@/types/template';

const props = defineProps<{
  modelValue: TemplateField | null;
}>();

const emit = defineEmits<{
  'update:modelValue': [TemplateField];
  remove: [];
}>();

const draft = ref<TemplateField | null>(null);
const lastSyncedSnapshot = ref('null');

watch(
  () => props.modelValue,
  (value) => {
    const nextDraft = value ? cloneField(value) : null;
    if (nextDraft) {
      ensureFieldTypeShape(nextDraft);
    }

    const nextSnapshot = serializeField(nextDraft);
    lastSyncedSnapshot.value = nextSnapshot;
    if (nextSnapshot === serializeField(draft.value)) {
      return;
    }

    draft.value = nextDraft;
  },
  { immediate: true },
);

watch(
  draft,
  (value) => {
    if (!value) {
      return;
    }

    const preparedField = cloneField(value);
    ensureFieldTypeShape(preparedField);
    const nextSnapshot = serializeField(preparedField);
    if (nextSnapshot === lastSyncedSnapshot.value) {
      return;
    }

    lastSyncedSnapshot.value = nextSnapshot;
    emit('update:modelValue', preparedField);
  },
  { deep: true },
);

/**
 * 深拷贝字段配置，避免直接修改父组件状态。
 */
function cloneField(field: TemplateField): TemplateField {
  return JSON.parse(JSON.stringify(field)) as TemplateField;
}

/**
 * 序列化字段配置，用于判断父子同步是否只是同一份数据回灌。
 */
function serializeField(field: TemplateField | null): string {
  return JSON.stringify(field);
}

/**
 * 根据字段类型补齐专属配置。
 */
function ensureFieldTypeShape(field: TemplateField): void {
  if (field.field_type === 'option_select') {
    field.options = field.options ?? [];
    field.columns = null;
    field.row_detection = null;
    return;
  }

  if (field.field_type === 'table') {
    field.columns =
      field.columns ?? [{ name: 'col_1', label: '列 1', type: 'text', x_ratio: [0, 1] }];
    field.row_detection = field.row_detection ?? { mode: 'by_text_rows', count: null };
    field.options = null;
    return;
  }

  field.options = null;
  field.columns = null;
  field.row_detection = null;
}

/**
 * 在字段类型变化后刷新默认配置。
 */
function handleFieldTypeChange(): void {
  if (!draft.value) {
    return;
  }

  ensureFieldTypeShape(draft.value);
}

/**
 * 新增单选项定义。
 */
function addOption(): void {
  if (!draft.value) {
    return;
  }

  draft.value.options = draft.value.options ?? [];
  draft.value.options.push({ value: '', labels: [] });
}

/**
 * 删除单选项定义。
 */
function removeOption(index: number): void {
  draft.value?.options?.splice(index, 1);
}

/**
 * 将标签输入框拆分为标签数组。
 */
function handleOptionLabelsChange(index: number, input: string): void {
  if (!draft.value?.options?.[index]) {
    return;
  }

  draft.value.options[index].labels = input
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
}

/**
 * 新增表格列定义。
 */
function addColumn(): void {
  if (!draft.value) {
    return;
  }

  draft.value.columns = draft.value.columns ?? [];
  draft.value.columns.push({
    name: `col_${draft.value.columns.length + 1}`,
    label: `列 ${draft.value.columns.length + 1}`,
    type: 'text',
    x_ratio: [0, 1],
  });
}

/**
 * 删除表格列定义。
 */
function removeColumn(index: number): void {
  draft.value?.columns?.splice(index, 1);
}
</script>

<style scoped>
.field-config-panel {
  padding: 20px;
}

.field-config-panel__header,
.field-config-panel__section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.field-config-panel__header {
  margin-bottom: 16px;
}

.field-config-panel__form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.field-config-panel__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px 16px;
}

.field-config-panel__bbox h3,
.field-config-panel__section h3 {
  margin: 0 0 12px;
  font-size: 15px;
}

.field-config-panel__stack {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.option-row,
.column-row {
  display: grid;
  gap: 10px;
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.7);
}

.option-row {
  grid-template-columns: 1fr 1.5fr auto;
}

.column-row {
  grid-template-columns: 1fr 1fr 1fr 120px 120px auto;
}

.field-config-panel__hint {
  margin: 0;
  color: var(--muted);
  font-size: 13px;
}

@media (max-width: 1280px) {
  .column-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .field-config-panel__grid,
  .option-row {
    grid-template-columns: 1fr;
  }
}
</style>
