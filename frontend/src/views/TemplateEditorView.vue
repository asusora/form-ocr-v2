<template>
  <AppShell
    title="模板编辑器"
    subtitle="在左侧模板页上画框或拖拽调整，右侧维护字段类型、坐标和表格配置。"
  >
    <section class="page-card editor-toolbar">
      <div>
        <h2 class="section-title">{{ store.template?.name || '模板加载中' }}</h2>
        <p class="section-desc">
          当前共 {{ safeTotalPages }} 页，字段数 {{ store.template?.fields.length || 0 }}。先画框，再补字段配置。
        </p>
      </div>

      <div class="editor-toolbar__actions">
        <ElButton :type="createMode ? 'warning' : 'primary'" @click="toggleCreateMode">
          {{ createMode ? '退出画框模式' : '画框新增字段' }}
        </ElButton>
        <ElButton
          :disabled="!store.dirty"
          :loading="store.saving"
          type="success"
          @click="saveAll"
        >
          保存模板字段
        </ElButton>
      </div>
    </section>

    <ElAlert
      v-if="createMode"
      title="画框模式已开启：在左侧页面上拖拽即可创建新字段。"
      type="info"
      :closable="false"
    />

    <div class="editor-layout" v-loading="store.loading">
      <section class="editor-main">
        <div class="page-card editor-pagebar">
          <ElButton :disabled="!canGoPrev" @click="prevPage">上一页</ElButton>
          <span>第 {{ currentPage }} / {{ safeTotalPages }} 页</span>
          <ElButton :disabled="!canGoNext" @click="nextPage">下一页</ElButton>
        </div>

        <PdfCanvas
          v-if="pageImageUrl"
          :boxes="canvasBoxes"
          :create-mode="createMode"
          :editable="true"
          :image-url="pageImageUrl"
          :selected-id="store.selectedFieldId"
          @box-changed="handleBoxChanged"
          @box-created="handleBoxCreated"
          @box-selected="handleFieldSelected"
        />
      </section>

      <aside class="editor-side">
        <FieldListPanel
          :fields="currentFields"
          :selected-id="store.selectedFieldId"
          @create="toggleCreateMode"
          @remove="handleRemoveField"
          @select="handleFieldSelected"
        />

        <FieldConfigPanel
          :model-value="store.selectedField"
          @remove="handleRemoveSelectedField"
          @update:modelValue="handleFieldConfigChange"
        />

        <AnchorPreviewPanel :anchors="store.selectedField?.anchors" />
      </aside>
    </div>
  </AppShell>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';

import { buildTemplatePageUrl } from '@/api/templates';
import { extractErrorMessage } from '@/api/http';
import { usePdfPages } from '@/composables/usePdfPages';
import AppShell from '@/components/layout/AppShell.vue';
import PdfCanvas from '@/components/pdf/PdfCanvas.vue';
import AnchorPreviewPanel from '@/components/template/AnchorPreviewPanel.vue';
import FieldConfigPanel from '@/components/template/FieldConfigPanel.vue';
import FieldListPanel from '@/components/template/FieldListPanel.vue';
import { useTemplateEditorStore } from '@/stores/template-editor';
import type { BBox } from '@/types/common';
import type { TemplateField } from '@/types/template';

const route = useRoute();
const store = useTemplateEditorStore();
const createMode = ref(false);

const { currentPage, safeTotalPages, canGoPrev, canGoNext, prevPage, nextPage } = usePdfPages(
  computed(() => store.template?.page_count ?? 1),
);

const currentFields = computed(() => {
  return (store.template?.fields ?? [])
    .filter((field) => field.page === currentPage.value)
    .sort((left, right) => left.sort_order - right.sort_order);
});

const canvasBoxes = computed(() => {
  return currentFields.value.map((field) => ({
    id: field.id || field.name,
    bbox: field.bbox,
    color:
      store.selectedFieldId === field.id ? '#0f766e' : field.field_type === 'table' ? '#d97706' : '#64748b',
    label: field.label || field.name,
  }));
});

const pageImageUrl = computed(() => {
  if (!store.template) {
    return '';
  }

  return buildTemplatePageUrl(store.template.id, currentPage.value);
});

onMounted(() => {
  void loadTemplate();
});

watch(
  () => route.params.id,
  () => {
    void loadTemplate();
  },
);

/**
 * 拉取当前模板详情。
 */
async function loadTemplate(): Promise<void> {
  const templateId = String(route.params.id || '');
  if (!templateId) {
    return;
  }

  try {
    await store.load(templateId);
  } catch (error) {
    ElMessage.error(extractErrorMessage(error));
  }
}

/**
 * 切换画框模式。
 */
function toggleCreateMode(): void {
  createMode.value = !createMode.value;
}

/**
 * 选中某个字段。
 */
function handleFieldSelected(fieldId: string): void {
  store.setSelectedField(fieldId);
}

/**
 * 根据新画的框创建字段。
 */
function handleBoxCreated(bbox: BBox): void {
  const fieldId = store.createField(currentPage.value, bbox);
  if (fieldId) {
    store.setSelectedField(fieldId);
  }
  createMode.value = false;
}

/**
 * 更新字段框坐标。
 */
function handleBoxChanged(payload: { id: string; bbox: BBox }): void {
  store.patchField(payload.id, { bbox: payload.bbox });
}

/**
 * 应用右侧字段配置修改。
 */
function handleFieldConfigChange(field: TemplateField): void {
  if (!field.id) {
    return;
  }

  store.patchField(field.id, field);
}

/**
 * 删除指定字段。
 */
async function handleRemoveField(fieldId: string): Promise<void> {
  try {
    await ElMessageBox.confirm('删除后将从当前模板中移除该字段，是否继续？', '删除字段', {
      type: 'warning',
    });
    await store.removeField(fieldId);
    ElMessage.success('字段已删除');
  } catch (error) {
    if (error === 'cancel' || error === 'close') {
      return;
    }
    ElMessage.error(extractErrorMessage(error));
  }
}

/**
 * 删除当前选中字段。
 */
async function handleRemoveSelectedField(): Promise<void> {
  if (!store.selectedFieldId) {
    return;
  }

  await handleRemoveField(store.selectedFieldId);
}

/**
 * 保存全部模板字段。
 */
async function saveAll(): Promise<void> {
  try {
    await store.saveAll();
    ElMessage.success('模板字段已保存');
  } catch (error) {
    ElMessage.error(extractErrorMessage(error));
  }
}
</script>

<style scoped>
.editor-toolbar,
.editor-pagebar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 18px 20px;
}

.editor-toolbar__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.editor-pagebar span {
  color: var(--muted);
}

.editor-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(360px, 0.9fr);
  gap: 20px;
}

.editor-main,
.editor-side {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

@media (max-width: 1200px) {
  .editor-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .editor-toolbar,
  .editor-pagebar {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
