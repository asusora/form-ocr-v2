<template>
  <AppShell
    title="识别校对页"
    subtitle="轮询识别状态、调整对齐框、人工修正文案，并导出 JSON 或 Excel。"
  >
    <section v-if="isProcessing" class="page-card state-card">
      <ElResult
        icon="info"
        title="识别处理中"
        sub-title="后端正在执行 OCR、锚点对齐和字段抽取，页面会自动轮询刷新。"
      />
    </section>

    <section v-else-if="isFailed" class="page-card state-card">
      <ElResult
        icon="error"
        title="识别失败"
        :sub-title="store.detail?.error_message || '任务执行失败，请重新上传文件。'"
      />
    </section>

    <template v-else-if="store.detail">
      <RecognitionToolbar
        :busy="store.saving"
        :disable-actions="!store.detail.fields.length"
        :page="currentPage"
        :total-pages="safeTotalPages"
        @download-json="download('json')"
        @download-xlsx="download('xlsx')"
        @next-page="nextPage"
        @prev-page="prevPage"
        @save="save"
      />

      <div class="review-layout">
        <section class="review-main">
          <PdfCanvas
            :boxes="pageBoxes"
            :editable="true"
            :image-url="pageImageUrl"
            :selected-id="selectedFieldId"
            @box-changed="handleBoxChanged"
            @box-selected="handleSelectField"
          />
        </section>

        <aside class="review-side">
          <RecognitionFieldPanel
            :fields="currentFields"
            :selected-id="selectedFieldId"
            @re-extract="handleReExtract"
            @select="handleSelectField"
            @update-value="handleValueChange"
          />
        </aside>
      </div>
    </template>
  </AppShell>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { ElMessage } from 'element-plus';

import {
  buildRecognitionExportUrl,
  buildRecognitionPageUrl,
} from '@/api/recognitions';
import { extractErrorMessage } from '@/api/http';
import { usePdfPages } from '@/composables/usePdfPages';
import { useRecognitionPolling } from '@/composables/useRecognitionPolling';
import AppShell from '@/components/layout/AppShell.vue';
import PdfCanvas from '@/components/pdf/PdfCanvas.vue';
import RecognitionFieldPanel from '@/components/recognition/RecognitionFieldPanel.vue';
import RecognitionToolbar from '@/components/recognition/RecognitionToolbar.vue';
import { useRecognitionStore } from '@/stores/recognition';
import type { BBox } from '@/types/common';
import type { ExportFormat } from '@/types/recognition';

const route = useRoute();
const store = useRecognitionStore();
const selectedFieldId = ref('');

const { currentPage, safeTotalPages, prevPage, nextPage } = usePdfPages(
  computed(() => store.detail?.page_count ?? 1),
);

const isProcessing = computed(() => {
  return store.detail?.status === 'pending' || store.detail?.status === 'processing';
});
const isFailed = computed(() => store.detail?.status === 'failed');

const currentFields = computed(() => {
  return (store.detail?.fields ?? [])
    .filter((field) => (field.page ?? 1) === currentPage.value)
    .sort((left, right) => (left.sort_order ?? 0) - (right.sort_order ?? 0));
});

const pageBoxes = computed(() => {
  return currentFields.value.map((field) => ({
    id: field.id,
    bbox: field.aligned_bbox,
    color:
      field.alignment_status === 'alignment_failed'
        ? '#dc2626'
        : selectedFieldId.value === field.id
          ? '#0f766e'
          : field.edited_value != null
            ? '#16a34a'
            : '#64748b',
    label: field.field_label || field.field_name,
  }));
});

const pageImageUrl = computed(() => {
  if (!store.detail) {
    return '';
  }
  return buildRecognitionPageUrl(store.detail.id, currentPage.value);
});

const polling = useRecognitionPolling(async () => {
  await loadRecognition(false);
  return store.detail?.status ?? 'failed';
});

onMounted(() => {
  void loadRecognition(true);
});

watch(
  () => route.params.id,
  () => {
    polling.stop();
    void loadRecognition(true);
  },
);

watch(currentFields, (fields) => {
  if (!fields.length) {
    return;
  }

  if (!fields.some((field) => field.id === selectedFieldId.value)) {
    selectedFieldId.value = fields[0].id;
  }
});

/**
 * 拉取识别详情并根据状态启动轮询。
 */
async function loadRecognition(allowStartPolling: boolean): Promise<void> {
  const recognitionId = String(route.params.id || '');
  if (!recognitionId) {
    return;
  }

  try {
    await store.load(recognitionId);
    if (store.detail?.fields.length && !selectedFieldId.value) {
      selectedFieldId.value = store.detail.fields[0].id;
    }

    if (
      allowStartPolling &&
      (store.detail?.status === 'pending' || store.detail?.status === 'processing')
    ) {
      polling.start();
    } else if (store.detail?.status !== 'pending' && store.detail?.status !== 'processing') {
      polling.stop();
    }
  } catch (error) {
    polling.stop();
    ElMessage.error(extractErrorMessage(error));
  }
}

/**
 * 选中识别字段。
 */
function handleSelectField(fieldId: string): void {
  selectedFieldId.value = fieldId;
}

/**
 * 更新字段框。
 */
function handleBoxChanged(payload: { id: string; bbox: BBox }): void {
  store.updateFieldBBox(payload.id, payload.bbox);
}

/**
 * 更新字段值。
 */
function handleValueChange(fieldId: string, value: unknown): void {
  store.updateFieldValue(fieldId, value);
}

/**
 * 重新识别单个字段。
 */
async function handleReExtract(fieldId: string): Promise<void> {
  try {
    const target = store.detail?.fields.find((field) => field.id === fieldId);
    if (!target) {
      return;
    }

    await store.reExtract(fieldId, target.aligned_bbox);
    ElMessage.success('字段已重新识别');
  } catch (error) {
    ElMessage.error(extractErrorMessage(error));
  }
}

/**
 * 保存识别结果。
 */
async function save(): Promise<void> {
  try {
    await store.save();
    ElMessage.success('识别结果已保存');
  } catch (error) {
    ElMessage.error(extractErrorMessage(error));
  }
}

/**
 * 导出识别结果文件。
 */
function download(format: ExportFormat): void {
  if (!store.detail) {
    return;
  }

  window.open(buildRecognitionExportUrl(store.detail.id, format), '_blank', 'noopener');
}
</script>

<style scoped>
.state-card {
  padding: 40px 24px;
}

.review-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(360px, 0.95fr);
  gap: 20px;
}

.review-main,
.review-side {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

@media (max-width: 1200px) {
  .review-layout {
    grid-template-columns: 1fr;
  }
}
</style>
