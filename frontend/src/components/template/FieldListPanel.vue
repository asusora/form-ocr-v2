<template>
  <section class="page-card field-list-panel">
    <header class="field-list-panel__header">
      <div>
        <h2 class="section-title">字段列表</h2>
        <p class="section-desc">按当前页显示字段，支持选中、删除和继续画框新增。</p>
      </div>
      <ElButton type="primary" @click="emit('create')">新增字段</ElButton>
    </header>

    <ElEmpty v-if="!fields.length" description="当前页还没有字段，先在左侧进入画框模式。" />

    <div v-else class="field-list-panel__body">
      <article
        v-for="field in fields"
        :key="field.id || field.name"
        class="field-list-panel__item"
        :class="{ 'field-list-panel__item--active': selectedId === (field.id || field.name) }"
        @click="emit('select', field.id || field.name)"
      >
        <div>
          <div class="field-list-panel__name">{{ field.label || field.name }}</div>
          <div class="field-list-panel__meta">{{ field.name }} · {{ field.field_type }}</div>
        </div>

        <ElButton
          circle
          plain
          type="danger"
          @click.stop="emit('remove', field.id || field.name)"
        >
          ×
        </ElButton>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { TemplateField } from '@/types/template';

defineProps<{
  fields: TemplateField[];
  selectedId: string;
}>();

const emit = defineEmits<{
  create: [];
  select: [string];
  remove: [string];
}>();
</script>

<style scoped>
.field-list-panel {
  padding: 20px;
}

.field-list-panel__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.field-list-panel__body {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.field-list-panel__item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 16px;
  border: 1px solid transparent;
  border-radius: 18px;
  background: rgba(15, 118, 110, 0.04);
  cursor: pointer;
  transition:
    border-color 0.2s ease,
    transform 0.2s ease,
    background 0.2s ease;
}

.field-list-panel__item:hover,
.field-list-panel__item--active {
  border-color: var(--accent);
  background: rgba(15, 118, 110, 0.1);
  transform: translateY(-1px);
}

.field-list-panel__name {
  font-weight: 700;
}

.field-list-panel__meta {
  margin-top: 4px;
  color: var(--muted);
  font-size: 13px;
}
</style>
