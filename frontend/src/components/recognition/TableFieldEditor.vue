<template>
  <div class="table-field-editor">
    <div class="table-field-editor__actions">
      <ElButton size="small" @click="addRow">新增行</ElButton>
    </div>

    <ElTable :data="rows" border>
      <ElTableColumn
        v-for="column in normalizedColumns"
        :key="column.key"
        :label="column.label"
        min-width="140"
      >
        <template #default="{ row, $index }">
          <ElCheckbox
            v-if="column.type === 'checkbox'"
            :model-value="Boolean(row[column.key])"
            @update:model-value="updateCell($index, column.key, $event)"
          />
          <ElInput
            v-else
            :model-value="String(row[column.key] ?? '')"
            @update:model-value="updateCell($index, column.key, $event)"
          />
        </template>
      </ElTableColumn>

      <ElTableColumn label="操作" width="88" fixed="right">
        <template #default="{ $index }">
          <ElButton link type="danger" @click="removeRow($index)">删除</ElButton>
        </template>
      </ElTableColumn>
    </ElTable>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

interface ColumnMeta {
  key: string;
  label: string;
  type: 'text' | 'multiline_text' | 'date' | 'checkbox';
}

const props = defineProps<{
  modelValue: Record<string, unknown>[];
  columns: Array<string | { name: string; label: string; type?: ColumnMeta['type'] }>;
}>();

const emit = defineEmits<{
  'update:modelValue': [Record<string, unknown>[]];
}>();

const normalizedColumns = computed<ColumnMeta[]>(() => {
  return props.columns.map((column) => {
    if (typeof column === 'string') {
      return {
        key: column,
        label: column,
        type: 'text',
      };
    }

    return {
      key: column.name,
      label: column.label,
      type: column.type ?? 'text',
    };
  });
});

const rows = computed(() => props.modelValue);

/**
 * 复制并返回当前表格数据。
 */
function cloneRows(): Record<string, unknown>[] {
  return structuredClone(props.modelValue ?? []);
}

/**
 * 新增一行空数据。
 */
function addRow(): void {
  const nextRows = cloneRows();
  const row: Record<string, unknown> = {};
  for (const column of normalizedColumns.value) {
    row[column.key] = column.type === 'checkbox' ? false : '';
  }
  nextRows.push(row);
  emit('update:modelValue', nextRows);
}

/**
 * 删除指定索引的行。
 */
function removeRow(index: number): void {
  const nextRows = cloneRows();
  nextRows.splice(index, 1);
  emit('update:modelValue', nextRows);
}

/**
 * 更新单元格值。
 */
function updateCell(index: number, key: string, value: unknown): void {
  const nextRows = cloneRows();
  if (!nextRows[index]) {
    nextRows[index] = {};
  }
  nextRows[index][key] = value;
  emit('update:modelValue', nextRows);
}
</script>

<style scoped>
.table-field-editor {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.table-field-editor__actions {
  display: flex;
  justify-content: flex-end;
}
</style>
