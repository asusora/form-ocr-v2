<template>
  <AppShell
    title="模板工作台"
    subtitle="维护模板、上传识别文件，并从这里进入模板编辑与识别校对流程。"
  >
    <section class="page-card overview-card">
      <div class="overview-card__stats">
        <article class="overview-stat">
          <span>模板总数</span>
          <strong>{{ store.items.length }}</strong>
        </article>
        <article class="overview-stat">
          <span>字段总数</span>
          <strong>{{ totalFields }}</strong>
        </article>
        <article class="overview-stat">
          <span>多页模板</span>
          <strong>{{ multiPageTemplates }}</strong>
        </article>
      </div>

      <div class="overview-card__actions">
        <ElButton size="large" type="primary" @click="showCreate = true">新建模板</ElButton>
      </div>
    </section>

    <section class="page-card table-card">
      <header class="table-card__header">
        <div>
          <h2 class="section-title">模板列表</h2>
          <p class="section-desc">点击“编辑模板”维护字段，点击“去识别”上传真实表单并进入轮询流程。</p>
        </div>
      </header>

      <ElTable :data="store.items" v-loading="store.loading" border>
        <ElTableColumn prop="name" label="模板名称" min-width="180" />
        <ElTableColumn prop="description" label="描述" min-width="220">
          <template #default="{ row }">
            {{ row.description || '—' }}
          </template>
        </ElTableColumn>
        <ElTableColumn prop="page_count" label="页数" width="90" />
        <ElTableColumn prop="field_count" label="字段数" width="100" />
        <ElTableColumn prop="updated_at" label="更新时间" min-width="180">
          <template #default="{ row }">
            {{ formatTime(row.updated_at) }}
          </template>
        </ElTableColumn>
        <ElTableColumn label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <ElButton link type="primary" @click="goEdit(row.id)">编辑模板</ElButton>
            <ElButton link type="success" @click="openRecognition(row.id, row.name)">去识别</ElButton>
          </template>
        </ElTableColumn>
      </ElTable>
    </section>

    <TemplateCreateDialog
      :visible="showCreate"
      @close="showCreate = false"
      @submit="handleCreate"
    />

    <RecognitionCreateDialog
      :visible="showRecognition"
      :template-name="recognitionTemplateName"
      @close="showRecognition = false"
      @submit="handleRecognitionCreate"
    />
  </AppShell>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';

import { createRecognition } from '@/api/recognitions';
import { extractErrorMessage } from '@/api/http';
import { createTemplate } from '@/api/templates';
import AppShell from '@/components/layout/AppShell.vue';
import RecognitionCreateDialog from '@/components/recognition/RecognitionCreateDialog.vue';
import TemplateCreateDialog from '@/components/template/TemplateCreateDialog.vue';
import { useTemplateListStore } from '@/stores/template-list';

const router = useRouter();
const store = useTemplateListStore();

const showCreate = ref(false);
const showRecognition = ref(false);
const recognitionTemplateId = ref('');
const recognitionTemplateName = ref('');

const totalFields = computed(() =>
  store.items.reduce((sum, item) => sum + item.field_count, 0),
);
const multiPageTemplates = computed(() =>
  store.items.filter((item) => item.page_count > 1).length,
);

onMounted(() => {
  void store.load();
});

/**
 * 格式化 ISO 时间字符串。
 */
function formatTime(value: string): string {
  if (!value) {
    return '—';
  }

  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

/**
 * 跳转到模板编辑器。
 */
function goEdit(id: string): void {
  void router.push({ name: 'template-editor', params: { id } });
}

/**
 * 打开识别上传弹窗。
 */
function openRecognition(id: string, name: string): void {
  recognitionTemplateId.value = id;
  recognitionTemplateName.value = name;
  showRecognition.value = true;
}

/**
 * 创建模板并跳转到编辑页。
 */
async function handleCreate(payload: {
  name: string;
  description: string;
  file: File;
  renderDpi: number;
}): Promise<void> {
  try {
    const form = new FormData();
    form.append('name', payload.name);
    form.append('description', payload.description);
    form.append('render_dpi', String(payload.renderDpi));
    form.append('file', payload.file);

    const template = await createTemplate(form);
    showCreate.value = false;
    await store.load();
    await router.push({ name: 'template-editor', params: { id: template.id } });
  } catch (error) {
    ElMessage.error(extractErrorMessage(error));
  }
}

/**
 * 创建识别任务并跳转到识别页。
 */
async function handleRecognitionCreate(file: File): Promise<void> {
  try {
    const form = new FormData();
    form.append('template_id', recognitionTemplateId.value);
    form.append('file', file);

    const recognition = await createRecognition(form);
    showRecognition.value = false;
    await router.push({ name: 'recognition', params: { id: recognition.id } });
  } catch (error) {
    ElMessage.error(extractErrorMessage(error));
  }
}
</script>

<style scoped>
.overview-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 22px 24px;
}

.overview-card__stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  width: 100%;
}

.overview-stat {
  padding: 16px 18px;
  border: 1px solid var(--line);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.65);
}

.overview-stat span {
  display: block;
  color: var(--muted);
  font-size: 13px;
}

.overview-stat strong {
  display: block;
  margin-top: 8px;
  font-size: 30px;
}

.table-card {
  padding: 22px;
}

.table-card__header {
  margin-bottom: 18px;
}

@media (max-width: 960px) {
  .overview-card {
    flex-direction: column;
    align-items: stretch;
  }

  .overview-card__stats {
    grid-template-columns: 1fr;
  }
}
</style>
