# Form OCR Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现表单 OCR 模板化识别系统前端，支持模板列表、模板编辑、识别上传、处理中轮询、识别校对、重识别、保存结果和导出。

**Architecture:** 前端采用 Vue 3 + TypeScript + Vite + Pinia + Vue Router。页面按设计文档拆成模板列表、模板编辑器、识别校对页三大视图；PDF 渲染与框选能力沉到通用组件层，业务状态沉到 Pinia store，API 请求统一走 axios 封装，避免视图层直接拼接请求和状态。

**Tech Stack:** Vue 3, TypeScript, Vite, Pinia, Vue Router, Element Plus, axios, pdfjs-dist, fabric, Vitest, @vue/test-utils

---

## 文件结构总览

```text
frontend/
├── package.json
├── tsconfig.json
├── vite.config.ts
├── index.html
├── src/
│   ├── main.ts
│   ├── App.vue
│   ├── styles/
│   │   └── main.css
│   ├── router/
│   │   └── index.ts
│   ├── api/
│   │   ├── http.ts
│   │   ├── templates.ts
│   │   └── recognitions.ts
│   ├── types/
│   │   ├── common.ts
│   │   ├── template.ts
│   │   └── recognition.ts
│   ├── stores/
│   │   ├── template-list.ts
│   │   ├── template-editor.ts
│   │   └── recognition.ts
│   ├── composables/
│   │   ├── usePdfPages.ts
│   │   ├── useCanvasScale.ts
│   │   └── useRecognitionPolling.ts
│   ├── components/
│   │   ├── layout/
│   │   │   └── AppShell.vue
│   │   ├── template/
│   │   │   ├── TemplateCreateDialog.vue
│   │   │   ├── FieldListPanel.vue
│   │   │   ├── FieldConfigPanel.vue
│   │   │   └── AnchorPreviewPanel.vue
│   │   ├── recognition/
│   │   │   ├── RecognitionCreateDialog.vue
│   │   │   ├── RecognitionToolbar.vue
│   │   │   ├── RecognitionFieldPanel.vue
│   │   │   └── TableFieldEditor.vue
│   │   └── pdf/
│   │       └── PdfCanvas.vue
│   └── views/
│       ├── TemplateListView.vue
│       ├── TemplateEditorView.vue
│       └── RecognitionView.vue
└── tests/
    ├── setup.ts
    ├── unit/
    │   ├── template-list.store.spec.ts
    │   ├── recognition.store.spec.ts
    │   └── pdf-canvas.spec.ts
    └── components/
        ├── FieldConfigPanel.spec.ts
        └── RecognitionFieldPanel.spec.ts
```

---

## Task 1: 搭建 Vue 3 + Vite 前端脚手架

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.ts`
- Create: `frontend/src/App.vue`
- Create: `frontend/src/styles/main.css`

- [ ] **Step 1: 创建 `frontend/package.json`**

```json
{
  "name": "form-ocr-frontend",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc --noEmit && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "dependencies": {
    "axios": "1.8.1",
    "element-plus": "2.9.4",
    "fabric": "6.5.3",
    "pdfjs-dist": "4.10.38",
    "pinia": "2.3.1",
    "vue": "3.5.13",
    "vue-router": "4.5.0"
  },
  "devDependencies": {
    "@testing-library/dom": "10.4.0",
    "@vitejs/plugin-vue": "5.2.1",
    "@vue/test-utils": "2.4.6",
    "jsdom": "26.0.0",
    "typescript": "5.7.3",
    "vite": "6.0.11",
    "vitest": "2.1.8",
    "vue-tsc": "2.2.0"
  }
}
```

- [ ] **Step 2: 创建 `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "strict": true,
    "jsx": "preserve",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "types": ["vitest/globals", "jsdom"],
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src/**/*.ts", "src/**/*.d.ts", "src/**/*.vue", "tests/**/*.ts"]
}
```

- [ ] **Step 3: 创建 `frontend/vite.config.ts`**

```ts
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { fileURLToPath, URL } from 'node:url';

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./tests/setup.ts'],
    css: true,
  },
});
```

- [ ] **Step 4: 创建入口文件**

```html
<!-- frontend/index.html -->
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Form OCR</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

```ts
// frontend/src/main.ts
import { createApp } from 'vue';
import { createPinia } from 'pinia';
import ElementPlus from 'element-plus';
import 'element-plus/dist/index.css';

import App from './App.vue';
import router from './router';
import './styles/main.css';

const app = createApp(App);
app.use(createPinia());
app.use(router);
app.use(ElementPlus);
app.mount('#app');
```

```vue
<!-- frontend/src/App.vue -->
<template>
  <RouterView />
</template>

<script setup lang="ts">
</script>
```

```css
/* frontend/src/styles/main.css */
:root {
  color-scheme: light;
  --bg: #f4f6f8;
  --panel: #ffffff;
  --line: #d8dee4;
  --text: #1f2937;
  --muted: #6b7280;
  --accent: #0f766e;
  --danger: #c2410c;
}

html,
body,
#app {
  margin: 0;
  min-height: 100%;
  background: linear-gradient(180deg, #eef6f6 0%, #f8fafc 100%);
  color: var(--text);
  font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
}

* {
  box-sizing: border-box;
}
```

- [ ] **Step 5: 安装依赖并验证脚手架**

Run: `cd frontend && npm install && npm run build`  
Expected: `vue-tsc` 与 `vite build` 成功，无 TypeScript 报错。

- [ ] **Step 6: Commit**

```bash
git add frontend/
git commit -m "feat: scaffold frontend with Vue 3 and Vite"
```

---

## Task 2: 路由、共享类型与 API 封装

**Files:**
- Create: `frontend/src/router/index.ts`
- Create: `frontend/src/api/http.ts`
- Create: `frontend/src/api/templates.ts`
- Create: `frontend/src/api/recognitions.ts`
- Create: `frontend/src/types/common.ts`
- Create: `frontend/src/types/template.ts`
- Create: `frontend/src/types/recognition.ts`
- Create: `frontend/src/components/layout/AppShell.vue`

- [ ] **Step 1: 创建共享类型**

```ts
// frontend/src/types/common.ts
export interface BBox {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

export interface ApiErrorPayload {
  detail: string;
  code: string;
}
```

```ts
// frontend/src/types/template.ts
import type { BBox } from './common';

export type FieldType =
  | 'text'
  | 'multiline_text'
  | 'date'
  | 'checkbox'
  | 'option_select'
  | 'signature'
  | 'table';

export interface OptionDef {
  value: string;
  labels: string[];
}

export interface ColumnDef {
  name: string;
  label: string;
  type: 'text' | 'multiline_text' | 'date' | 'checkbox';
  x_ratio: [number, number];
}

export interface RowDetectionConfig {
  mode: 'by_horizontal_lines' | 'by_text_rows' | 'fixed_count';
  count?: number | null;
}

export interface TemplateField {
  id?: string;
  template_id?: string;
  page: number;
  name: string;
  label: string;
  field_type: FieldType;
  bbox: BBox;
  anchors?: Array<{
    text: string;
    template_bbox: BBox;
    offset_from_field: [number, number];
  }>;
  options?: OptionDef[] | null;
  columns?: ColumnDef[] | null;
  row_detection?: RowDetectionConfig | null;
  sort_order: number;
}

export interface TemplateSummary {
  id: string;
  name: string;
  description: string | null;
  page_count: number;
  field_count: number;
  updated_at: string;
}

export interface TemplateDetail {
  id: string;
  name: string;
  description: string | null;
  page_count: number;
  render_dpi: number;
  created_at: string;
  updated_at: string;
  fields: TemplateField[];
}
```

```ts
// frontend/src/types/recognition.ts
import type { BBox } from './common';

export type RecognitionStatus = 'pending' | 'processing' | 'success' | 'failed';
export type AlignmentStatus = 'auto' | 'manual_adjusted' | 'alignment_failed';

export interface RecognitionField {
  id: string;
  template_field_id: string;
  field_name: string;
  aligned_bbox: BBox;
  raw_value: unknown;
  edited_value: unknown;
  confidence: number | null;
  crop_path: string | null;
  alignment_status: AlignmentStatus;
}

export interface RecognitionDetail {
  id: string;
  template_id: string;
  status: RecognitionStatus;
  error_message: string | null;
  page_count: number;
  created_at: string;
  updated_at: string;
  fields: RecognitionField[];
}
```

- [ ] **Step 2: 创建 axios 客户端与错误映射**

```ts
// frontend/src/api/http.ts
import axios from 'axios';
import type { ApiErrorPayload } from '@/types/common';

export const http = axios.create({
  baseURL: '/api',
  timeout: 30_000,
});

export function extractErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const payload = error.response?.data as ApiErrorPayload | undefined;
    if (payload?.detail) {
      return payload.detail;
    }
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return '请求失败';
}
```

- [ ] **Step 3: 创建模板与识别 API 模块**

```ts
// frontend/src/api/templates.ts
import { http } from './http';
import type { TemplateDetail, TemplateField, TemplateSummary } from '@/types/template';

export async function fetchTemplates(): Promise<TemplateSummary[]> {
  const { data } = await http.get<TemplateSummary[]>('/templates');
  return data;
}

export async function fetchTemplate(templateId: string): Promise<TemplateDetail> {
  const { data } = await http.get<TemplateDetail>(`/templates/${templateId}`);
  return data;
}

export async function createTemplate(form: FormData): Promise<TemplateDetail> {
  const { data } = await http.post<TemplateDetail>('/templates', form);
  return data;
}

export async function saveTemplateFields(templateId: string, fields: TemplateField[]): Promise<TemplateDetail> {
  const { data } = await http.post<TemplateDetail>(`/templates/${templateId}/fields`, { fields });
  return data;
}

export async function updateTemplateField(
  templateId: string,
  fieldId: string,
  field: TemplateField,
): Promise<TemplateDetail> {
  const { data } = await http.put<TemplateDetail>(`/templates/${templateId}/fields/${fieldId}`, field);
  return data;
}

export async function deleteTemplateField(templateId: string, fieldId: string): Promise<void> {
  await http.delete(`/templates/${templateId}/fields/${fieldId}`);
}
```

```ts
// frontend/src/api/recognitions.ts
import { http } from './http';
import type { BBox } from '@/types/common';
import type { RecognitionDetail, RecognitionField } from '@/types/recognition';

export async function createRecognition(form: FormData): Promise<{ id: string; status: string }> {
  const { data } = await http.post<{ id: string; status: string }>('/recognitions', form);
  return data;
}

export async function fetchRecognition(recognitionId: string): Promise<RecognitionDetail> {
  const { data } = await http.get<RecognitionDetail>(`/recognitions/${recognitionId}`);
  return data;
}

export async function reExtractField(
  recognitionId: string,
  fieldId: string,
  aligned_bbox: BBox,
): Promise<RecognitionField> {
  const { data } = await http.post<RecognitionField>(`/recognitions/${recognitionId}/re-extract/${fieldId}`, {
    aligned_bbox,
  });
  return data;
}

export async function saveRecognitionFields(recognitionId: string, fields: RecognitionField[]): Promise<RecognitionDetail> {
  const { data } = await http.put<RecognitionDetail>(`/recognitions/${recognitionId}/fields`, {
    fields: fields.map((field) => ({
      id: field.id,
      aligned_bbox: field.aligned_bbox,
      edited_value: field.edited_value,
      alignment_status: field.alignment_status,
    })),
  });
  return data;
}
```

- [ ] **Step 4: 创建路由和布局壳**

```ts
// frontend/src/router/index.ts
import { createRouter, createWebHistory } from 'vue-router';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'template-list', component: () => import('@/views/TemplateListView.vue') },
    { path: '/templates/:id', name: 'template-editor', component: () => import('@/views/TemplateEditorView.vue') },
    { path: '/recognitions/:id', name: 'recognition', component: () => import('@/views/RecognitionView.vue') },
  ],
});

export default router;
```

```vue
<!-- frontend/src/components/layout/AppShell.vue -->
<template>
  <div class="app-shell">
    <header class="app-shell__header">
      <div>
        <h1>Form OCR Demo</h1>
        <p>模板配置、识别校对与导出</p>
      </div>
      <RouterLink to="/">返回模板列表</RouterLink>
    </header>
    <main class="app-shell__body">
      <slot />
    </main>
  </div>
</template>

<style scoped>
.app-shell {
  padding: 24px;
}

.app-shell__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.app-shell__header h1 {
  margin: 0;
  font-size: 24px;
}

.app-shell__header p {
  margin: 6px 0 0;
  color: var(--muted);
}
</style>
```

- [ ] **Step 5: 运行构建验证**

Run: `cd frontend && npm run build`  
Expected: 路由、类型、API 封装编译通过。

- [ ] **Step 6: Commit**

```bash
git add frontend/
git commit -m "feat: add frontend router types and API client"
```

---

## Task 3: 模板列表页与上传入口

**Files:**
- Create: `frontend/src/stores/template-list.ts`
- Create: `frontend/src/components/template/TemplateCreateDialog.vue`
- Create: `frontend/src/components/recognition/RecognitionCreateDialog.vue`
- Create: `frontend/src/views/TemplateListView.vue`
- Test: `frontend/tests/unit/template-list.store.spec.ts`

- [ ] **Step 1: 写 store 单测**

```ts
// frontend/tests/unit/template-list.store.spec.ts
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';

vi.mock('@/api/templates', () => ({
  fetchTemplates: vi.fn().mockResolvedValue([{ id: 'tpl-1', name: 'WR1A', description: null, page_count: 1, field_count: 2, updated_at: '2026-04-22T10:00:00' }]),
}));

import { useTemplateListStore } from '@/stores/template-list';

describe('template-list store', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('loads template list', async () => {
    const store = useTemplateListStore();
    await store.load();
    expect(store.items).toHaveLength(1);
    expect(store.items[0].name).toBe('WR1A');
  });
});
```

- [ ] **Step 2: 创建列表 store**

```ts
// frontend/src/stores/template-list.ts
import { defineStore } from 'pinia';
import { fetchTemplates } from '@/api/templates';
import type { TemplateSummary } from '@/types/template';

export const useTemplateListStore = defineStore('template-list', {
  state: () => ({
    items: [] as TemplateSummary[],
    loading: false,
  }),
  actions: {
    async load() {
      this.loading = true;
      try {
        this.items = await fetchTemplates();
      } finally {
        this.loading = false;
      }
    },
  },
});
```

- [ ] **Step 3: 创建模板上传与识别上传弹窗**

```vue
<!-- frontend/src/components/template/TemplateCreateDialog.vue -->
<template>
  <ElDialog :model-value="visible" title="新建模板" width="480px" @close="$emit('close')">
    <ElForm label-position="top">
      <ElFormItem label="模板名称">
        <ElInput v-model="name" />
      </ElFormItem>
      <ElFormItem label="模板 PDF">
        <input type="file" accept="application/pdf" @change="onFileChange" />
      </ElFormItem>
      <ElFormItem label="渲染 DPI">
        <ElInputNumber v-model="renderDpi" :min="120" :max="300" />
      </ElFormItem>
    </ElForm>
    <template #footer>
      <ElButton @click="$emit('close')">取消</ElButton>
      <ElButton type="primary" :disabled="!file || !name" @click="submit">创建</ElButton>
    </template>
  </ElDialog>
</template>

<script setup lang="ts">
import { ref } from 'vue';

const props = defineProps<{ visible: boolean }>();
const emit = defineEmits<{
  close: [];
  submit: [{ name: string; file: File; renderDpi: number }];
}>();

const name = ref('');
const renderDpi = ref(200);
const file = ref<File | null>(null);

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement;
  file.value = input.files?.[0] ?? null;
}

function submit() {
  if (!file.value || !name.value) return;
  emit('submit', { name: name.value, file: file.value, renderDpi: renderDpi.value });
}
</script>
```

```vue
<!-- frontend/src/components/recognition/RecognitionCreateDialog.vue -->
<template>
  <ElDialog :model-value="visible" title="开始识别" width="480px" @close="$emit('close')">
    <p class="hint">为模板 {{ templateName }} 上传一份待识别 PDF。</p>
    <input type="file" accept="application/pdf" @change="onFileChange" />
    <template #footer>
      <ElButton @click="$emit('close')">取消</ElButton>
      <ElButton type="primary" :disabled="!file" @click="submit">创建识别任务</ElButton>
    </template>
  </ElDialog>
</template>

<script setup lang="ts">
import { ref } from 'vue';

defineProps<{ visible: boolean; templateName: string }>();
const emit = defineEmits<{ close: []; submit: [File] }>();
const file = ref<File | null>(null);

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement;
  file.value = input.files?.[0] ?? null;
}

function submit() {
  if (!file.value) return;
  emit('submit', file.value);
}
</script>
```

- [ ] **Step 4: 创建模板列表页**

```vue
<!-- frontend/src/views/TemplateListView.vue -->
<template>
  <AppShell>
    <section class="toolbar">
      <ElButton type="primary" @click="showCreate = true">新建模板</ElButton>
    </section>

    <ElTable :data="store.items" v-loading="store.loading" border>
      <ElTableColumn prop="name" label="模板名称" />
      <ElTableColumn prop="page_count" label="页数" width="90" />
      <ElTableColumn prop="field_count" label="字段数" width="90" />
      <ElTableColumn prop="updated_at" label="更新时间" min-width="180" />
      <ElTableColumn label="操作" width="240">
        <template #default="{ row }">
          <ElButton link type="primary" @click="goEdit(row.id)">编辑模板</ElButton>
          <ElButton link type="success" @click="openRecognition(row.id, row.name)">去识别</ElButton>
        </template>
      </ElTableColumn>
    </ElTable>

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
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';

import AppShell from '@/components/layout/AppShell.vue';
import TemplateCreateDialog from '@/components/template/TemplateCreateDialog.vue';
import RecognitionCreateDialog from '@/components/recognition/RecognitionCreateDialog.vue';
import { createTemplate } from '@/api/templates';
import { createRecognition } from '@/api/recognitions';
import { extractErrorMessage } from '@/api/http';
import { useTemplateListStore } from '@/stores/template-list';

const router = useRouter();
const store = useTemplateListStore();

const showCreate = ref(false);
const showRecognition = ref(false);
const recognitionTemplateId = ref('');
const recognitionTemplateName = ref('');

onMounted(() => {
  store.load();
});

function goEdit(id: string) {
  router.push({ name: 'template-editor', params: { id } });
}

function openRecognition(id: string, name: string) {
  recognitionTemplateId.value = id;
  recognitionTemplateName.value = name;
  showRecognition.value = true;
}

async function handleCreate(payload: { name: string; file: File; renderDpi: number }) {
  try {
    const form = new FormData();
    form.append('name', payload.name);
    form.append('render_dpi', String(payload.renderDpi));
    form.append('file', payload.file);
    const template = await createTemplate(form);
    showCreate.value = false;
    router.push({ name: 'template-editor', params: { id: template.id } });
  } catch (error) {
    ElMessage.error(extractErrorMessage(error));
  }
}

async function handleRecognitionCreate(file: File) {
  try {
    const form = new FormData();
    form.append('template_id', recognitionTemplateId.value);
    form.append('file', file);
    const recognition = await createRecognition(form);
    showRecognition.value = false;
    router.push({ name: 'recognition', params: { id: recognition.id } });
  } catch (error) {
    ElMessage.error(extractErrorMessage(error));
  }
}
</script>
```

- [ ] **Step 5: 运行测试**

Run: `cd frontend && npm run test -- template-list.store.spec.ts`  
Expected: store 加载模板列表测试通过。

- [ ] **Step 6: Commit**

```bash
git add frontend/
git commit -m "feat: add template list page and upload dialogs"
```

---

## Task 4: 实现 PDF 渲染与画框基础组件

**Files:**
- Create: `frontend/src/composables/usePdfPages.ts`
- Create: `frontend/src/composables/useCanvasScale.ts`
- Create: `frontend/src/components/pdf/PdfCanvas.vue`
- Test: `frontend/tests/unit/pdf-canvas.spec.ts`

- [ ] **Step 1: 写坐标转换单测**

```ts
// frontend/tests/unit/pdf-canvas.spec.ts
import { describe, expect, it } from 'vitest';

function scaleBBox(input: { x1: number; y1: number; x2: number; y2: number }, scale: number) {
  return {
    x1: input.x1 * scale,
    y1: input.y1 * scale,
    x2: input.x2 * scale,
    y2: input.y2 * scale,
  };
}

describe('pdf canvas scale', () => {
  it('scales bbox from image space to viewport space', () => {
    const result = scaleBBox({ x1: 100, y1: 50, x2: 200, y2: 100 }, 0.5);
    expect(result).toEqual({ x1: 50, y1: 25, x2: 100, y2: 50 });
  });
});
```

- [ ] **Step 2: 创建 PDF 页加载 composable**

```ts
// frontend/src/composables/usePdfPages.ts
import { getDocument, GlobalWorkerOptions } from 'pdfjs-dist';
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url';

GlobalWorkerOptions.workerSrc = workerUrl;

export async function loadPdfPageCanvas(url: string, pageNumber: number, scale = 1.5): Promise<HTMLCanvasElement> {
  const loadingTask = getDocument(url);
  const pdf = await loadingTask.promise;
  const page = await pdf.getPage(pageNumber);
  const viewport = page.getViewport({ scale });
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  if (!ctx) {
    throw new Error('无法创建 canvas 上下文');
  }
  canvas.width = viewport.width;
  canvas.height = viewport.height;
  await page.render({ canvasContext: ctx, viewport }).promise;
  return canvas;
}
```

- [ ] **Step 3: 创建缩放换算工具和核心 PDF 组件**

```ts
// frontend/src/composables/useCanvasScale.ts
import type { BBox } from '@/types/common';

export function scaleBBox(bbox: BBox, ratio: number): BBox {
  return {
    x1: bbox.x1 * ratio,
    y1: bbox.y1 * ratio,
    x2: bbox.x2 * ratio,
    y2: bbox.y2 * ratio,
  };
}

export function unscaleBBox(bbox: BBox, ratio: number): BBox {
  return {
    x1: bbox.x1 / ratio,
    y1: bbox.y1 / ratio,
    x2: bbox.x2 / ratio,
    y2: bbox.y2 / ratio,
  };
}
```

```vue
<!-- frontend/src/components/pdf/PdfCanvas.vue -->
<template>
  <div class="pdf-canvas">
    <canvas ref="pdfCanvasRef"></canvas>
    <canvas ref="overlayCanvasRef" class="pdf-canvas__overlay"></canvas>
  </div>
</template>

<script setup lang="ts">
import { Canvas, Rect } from 'fabric';
import { onMounted, ref, watch } from 'vue';

import { scaleBBox, unscaleBBox } from '@/composables/useCanvasScale';
import { loadPdfPageCanvas } from '@/composables/usePdfPages';
import type { BBox } from '@/types/common';

const props = defineProps<{
  imageUrl: string;
  boxes: Array<{ id: string; bbox: BBox; color?: string }>;
  editable?: boolean;
}>();

const emit = defineEmits<{ boxChanged: [{ id: string; bbox: BBox }] }>();

const pdfCanvasRef = ref<HTMLCanvasElement | null>(null);
const overlayCanvasRef = ref<HTMLCanvasElement | null>(null);
let fabricCanvas: Canvas | null = null;
let ratio = 1;

async function renderPage() {
  if (!pdfCanvasRef.value || !overlayCanvasRef.value) return;
  const rendered = await loadPdfPageCanvas(props.imageUrl, 1);
  ratio = rendered.width / 1000;
  pdfCanvasRef.value.width = rendered.width;
  pdfCanvasRef.value.height = rendered.height;
  overlayCanvasRef.value.width = rendered.width;
  overlayCanvasRef.value.height = rendered.height;
  const ctx = pdfCanvasRef.value.getContext('2d');
  if (!ctx) return;
  ctx.clearRect(0, 0, rendered.width, rendered.height);
  ctx.drawImage(rendered, 0, 0);

  fabricCanvas?.dispose();
  fabricCanvas = new Canvas(overlayCanvasRef.value, { selection: false });
  paintBoxes();
}

function paintBoxes() {
  if (!fabricCanvas) return;
  fabricCanvas.clear();
  for (const item of props.boxes) {
    const scaled = scaleBBox(item.bbox, ratio);
    const rect = new Rect({
      left: scaled.x1,
      top: scaled.y1,
      width: scaled.x2 - scaled.x1,
      height: scaled.y2 - scaled.y1,
      stroke: item.color ?? '#0f766e',
      fill: 'transparent',
      strokeWidth: 2,
      selectable: props.editable ?? false,
    });
    rect.on('modified', () => {
      const current = {
        x1: rect.left ?? 0,
        y1: rect.top ?? 0,
        x2: (rect.left ?? 0) + (rect.width ?? 0) * (rect.scaleX ?? 1),
        y2: (rect.top ?? 0) + (rect.height ?? 0) * (rect.scaleY ?? 1),
      };
      emit('boxChanged', { id: item.id, bbox: unscaleBBox(current, ratio) });
    });
    fabricCanvas.add(rect);
  }
}

onMounted(() => {
  renderPage();
});

watch(() => [props.imageUrl, props.boxes], () => {
  renderPage();
}, { deep: true });
</script>
```

- [ ] **Step 4: 运行单测**

Run: `cd frontend && npm run test -- pdf-canvas.spec.ts`  
Expected: 坐标缩放测试通过。

- [ ] **Step 5: Commit**

```bash
git add frontend/
git commit -m "feat: add reusable PDF canvas overlay component"
```

---

## Task 5: 模板编辑器页面与字段配置面板

**Files:**
- Create: `frontend/src/stores/template-editor.ts`
- Create: `frontend/src/components/template/FieldListPanel.vue`
- Create: `frontend/src/components/template/FieldConfigPanel.vue`
- Create: `frontend/src/components/template/AnchorPreviewPanel.vue`
- Create: `frontend/src/views/TemplateEditorView.vue`
- Test: `frontend/tests/components/FieldConfigPanel.spec.ts`

- [ ] **Step 1: 写字段配置面板单测**

```ts
// frontend/tests/components/FieldConfigPanel.spec.ts
import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import FieldConfigPanel from '@/components/template/FieldConfigPanel.vue';

describe('FieldConfigPanel', () => {
  it('shows option editor for option_select type', () => {
    const wrapper = mount(FieldConfigPanel, {
      props: {
        modelValue: {
          page: 1,
          name: 'choice',
          label: 'Choice',
          field_type: 'option_select',
          bbox: { x1: 0, y1: 0, x2: 100, y2: 30 },
          options: [],
          sort_order: 0,
        },
      },
    });
    expect(wrapper.text()).toContain('选项定义');
  });
});
```

- [ ] **Step 2: 创建模板编辑 store**

```ts
// frontend/src/stores/template-editor.ts
import { defineStore } from 'pinia';

import { fetchTemplate, saveTemplateFields, updateTemplateField, deleteTemplateField } from '@/api/templates';
import type { TemplateDetail, TemplateField } from '@/types/template';

export const useTemplateEditorStore = defineStore('template-editor', {
  state: () => ({
    template: null as TemplateDetail | null,
    selectedFieldId: '' as string,
    dirty: false,
    loading: false,
  }),
  getters: {
    selectedField(state): TemplateField | null {
      return state.template?.fields.find((field) => field.id === state.selectedFieldId) ?? null;
    },
  },
  actions: {
    async load(templateId: string) {
      this.loading = true;
      try {
        this.template = await fetchTemplate(templateId);
      } finally {
        this.loading = false;
      }
    },
    patchField(fieldId: string, next: Partial<TemplateField>) {
      if (!this.template) return;
      const target = this.template.fields.find((field) => field.id === fieldId);
      if (!target) return;
      Object.assign(target, next);
      this.dirty = true;
    },
    async saveAll() {
      if (!this.template) return;
      this.template = await saveTemplateFields(this.template.id, this.template.fields);
      this.dirty = false;
    },
    async saveOne(fieldId: string) {
      if (!this.template) return;
      const target = this.template.fields.find((field) => field.id === fieldId);
      if (!target?.id) return;
      this.template = await updateTemplateField(this.template.id, target.id, target);
      this.dirty = false;
    },
    async removeOne(fieldId: string) {
      if (!this.template) return;
      await deleteTemplateField(this.template.id, fieldId);
      this.template.fields = this.template.fields.filter((field) => field.id !== fieldId);
      if (this.selectedFieldId === fieldId) {
        this.selectedFieldId = '';
      }
    },
  },
});
```

- [ ] **Step 3: 创建字段面板组件**

```vue
<!-- frontend/src/components/template/FieldListPanel.vue -->
<template>
  <ElCard>
    <template #header>字段列表</template>
    <ElButton type="primary" size="small" @click="$emit('create')">新增字段</ElButton>
    <ElMenu :default-active="selectedId" class="field-list">
      <ElMenuItem
        v-for="field in fields"
        :key="field.id || field.name"
        :index="field.id || field.name"
        @click="$emit('select', field.id || field.name)"
      >
        {{ field.label || field.name }} / {{ field.field_type }}
      </ElMenuItem>
    </ElMenu>
  </ElCard>
</template>

<script setup lang="ts">
import type { TemplateField } from '@/types/template';

defineProps<{ fields: TemplateField[]; selectedId: string }>();
defineEmits<{ create: []; select: [string] }>();
</script>
```

```vue
<!-- frontend/src/components/template/FieldConfigPanel.vue -->
<template>
  <ElForm v-if="modelValue" label-position="top">
    <ElFormItem label="字段名"><ElInput v-model="local.name" /></ElFormItem>
    <ElFormItem label="显示名"><ElInput v-model="local.label" /></ElFormItem>
    <ElFormItem label="字段类型">
      <ElSelect v-model="local.field_type">
        <ElOption label="文本" value="text" />
        <ElOption label="多行文本" value="multiline_text" />
        <ElOption label="日期" value="date" />
        <ElOption label="勾选框" value="checkbox" />
        <ElOption label="单选项" value="option_select" />
        <ElOption label="签名" value="signature" />
        <ElOption label="表格" value="table" />
      </ElSelect>
    </ElFormItem>
    <ElFormItem v-if="local.field_type === 'option_select'" label="选项定义">
      <ElButton size="small" @click="addOption">新增选项</ElButton>
      <div v-for="(option, index) in local.options" :key="index" class="option-row">
        <ElInput v-model="option.value" placeholder="value" />
        <ElInput
          :model-value="option.labels.join(',')"
          placeholder="labels，用逗号分隔"
          @update:model-value="(val) => (option.labels = val.split(',').map((item) => item.trim()).filter(Boolean))"
        />
      </div>
    </ElFormItem>
    <ElButton type="primary" @click="$emit('update:modelValue', local)">应用修改</ElButton>
  </ElForm>
</template>

<script setup lang="ts">
import { reactive, watch } from 'vue';
import type { TemplateField } from '@/types/template';

const props = defineProps<{ modelValue: TemplateField | null }>();
const emit = defineEmits<{ 'update:modelValue': [TemplateField] }>();

const local = reactive<TemplateField>({
  page: 1,
  name: '',
  label: '',
  field_type: 'text',
  bbox: { x1: 0, y1: 0, x2: 0, y2: 0 },
  sort_order: 0,
});

watch(
  () => props.modelValue,
  (value) => {
    if (!value) return;
    Object.assign(local, structuredClone(value));
  },
  { immediate: true },
);

function addOption() {
  local.options = local.options ?? [];
  local.options.push({ value: '', labels: [] });
}
</script>
```

```vue
<!-- frontend/src/components/template/AnchorPreviewPanel.vue -->
<template>
  <ElCard>
    <template #header>锚点预览</template>
    <ElEmpty v-if="!anchors?.length" description="保存字段后自动生成锚点" />
    <ElTag v-for="anchor in anchors" :key="anchor.text + anchor.template_bbox.x1" class="anchor-tag">
      {{ anchor.text }}
    </ElTag>
  </ElCard>
</template>

<script setup lang="ts">
defineProps<{
  anchors?: Array<{ text: string; template_bbox: { x1: number; y1: number; x2: number; y2: number } }>;
}>();
</script>
```

- [ ] **Step 4: 创建模板编辑视图**

```vue
<!-- frontend/src/views/TemplateEditorView.vue -->
<template>
  <AppShell>
    <div class="editor-layout" v-loading="store.loading">
      <section class="editor-main">
        <PdfCanvas
          v-if="pageImageUrl"
          :image-url="pageImageUrl"
          :boxes="canvasBoxes"
          :editable="true"
          @boxChanged="handleBoxChanged"
        />
        <div class="page-switcher">
          <ElButton @click="currentPage = Math.max(1, currentPage - 1)">上一页</ElButton>
          <span>第 {{ currentPage }} / {{ store.template?.page_count ?? 1 }} 页</span>
          <ElButton @click="currentPage = Math.min(store.template?.page_count ?? 1, currentPage + 1)">下一页</ElButton>
        </div>
      </section>

      <aside class="editor-side">
        <FieldListPanel
          :fields="currentFields"
          :selected-id="store.selectedFieldId"
          @create="createField"
          @select="(id) => (store.selectedFieldId = id)"
        />
        <FieldConfigPanel
          :model-value="store.selectedField"
          @update:model-value="handleFieldConfigChange"
        />
        <AnchorPreviewPanel :anchors="store.selectedField?.anchors" />
        <ElButton type="primary" :disabled="!store.dirty" @click="saveAll">保存模板字段</ElButton>
      </aside>
    </div>
  </AppShell>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import { ElMessage } from 'element-plus';

import AppShell from '@/components/layout/AppShell.vue';
import PdfCanvas from '@/components/pdf/PdfCanvas.vue';
import FieldListPanel from '@/components/template/FieldListPanel.vue';
import FieldConfigPanel from '@/components/template/FieldConfigPanel.vue';
import AnchorPreviewPanel from '@/components/template/AnchorPreviewPanel.vue';
import { extractErrorMessage } from '@/api/http';
import { useTemplateEditorStore } from '@/stores/template-editor';

const route = useRoute();
const store = useTemplateEditorStore();
const currentPage = ref(1);

onMounted(() => {
  store.load(String(route.params.id));
});

const currentFields = computed(() =>
  (store.template?.fields ?? []).filter((field) => field.page === currentPage.value),
);

const canvasBoxes = computed(() =>
  currentFields.value.map((field) => ({
    id: field.id || field.name,
    bbox: field.bbox,
    color: store.selectedFieldId === field.id ? '#0f766e' : '#64748b',
  })),
);

const pageImageUrl = computed(() =>
  store.template ? `/api/templates/${store.template.id}/pages/${currentPage.value}` : '',
);

function createField() {
  if (!store.template) return;
  const id = crypto.randomUUID();
  store.template.fields.push({
    id,
    page: currentPage.value,
    name: `field_${store.template.fields.length + 1}`,
    label: `字段 ${store.template.fields.length + 1}`,
    field_type: 'text',
    bbox: { x1: 100, y1: 100, x2: 300, y2: 140 },
    sort_order: store.template.fields.length,
  });
  store.selectedFieldId = id;
  store.dirty = true;
}

function handleFieldConfigChange(field: any) {
  if (!field.id) return;
  store.patchField(field.id, field);
}

function handleBoxChanged(payload: { id: string; bbox: { x1: number; y1: number; x2: number; y2: number } }) {
  store.patchField(payload.id, { bbox: payload.bbox });
}

async function saveAll() {
  try {
    await store.saveAll();
    ElMessage.success('模板字段已保存');
  } catch (error) {
    ElMessage.error(extractErrorMessage(error));
  }
}
</script>
```

- [ ] **Step 5: 运行测试**

Run: `cd frontend && npm run test -- FieldConfigPanel.spec.ts`  
Expected: `option_select` 时渲染选项编辑器的测试通过。

- [ ] **Step 6: Commit**

```bash
git add frontend/
git commit -m "feat: add template editor view and field config panels"
```

---

## Task 6: 识别状态管理、轮询与处理中界面

**Files:**
- Create: `frontend/src/stores/recognition.ts`
- Create: `frontend/src/composables/useRecognitionPolling.ts`
- Create: `frontend/src/components/recognition/RecognitionToolbar.vue`
- Modify: `frontend/src/views/RecognitionView.vue`
- Test: `frontend/tests/unit/recognition.store.spec.ts`

- [ ] **Step 1: 写识别 store 单测**

```ts
// frontend/tests/unit/recognition.store.spec.ts
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';

vi.mock('@/api/recognitions', () => ({
  fetchRecognition: vi.fn().mockResolvedValue({ id: 'rec-1', template_id: 'tpl-1', status: 'processing', error_message: null, page_count: 0, created_at: '', updated_at: '', fields: [] }),
}));

import { useRecognitionStore } from '@/stores/recognition';

describe('recognition store', () => {
  beforeEach(() => setActivePinia(createPinia()));

  it('loads recognition detail', async () => {
    const store = useRecognitionStore();
    await store.load('rec-1');
    expect(store.detail?.status).toBe('processing');
  });
});
```

- [ ] **Step 2: 创建识别 store 与轮询 composable**

```ts
// frontend/src/stores/recognition.ts
import { defineStore } from 'pinia';

import { fetchRecognition, reExtractField, saveRecognitionFields } from '@/api/recognitions';
import type { BBox } from '@/types/common';
import type { RecognitionDetail } from '@/types/recognition';

export const useRecognitionStore = defineStore('recognition', {
  state: () => ({
    detail: null as RecognitionDetail | null,
    loading: false,
  }),
  actions: {
    async load(recognitionId: string) {
      this.loading = true;
      try {
        this.detail = await fetchRecognition(recognitionId);
      } finally {
        this.loading = false;
      }
    },
    async reExtract(fieldId: string, aligned_bbox: BBox) {
      if (!this.detail) return;
      const updated = await reExtractField(this.detail.id, fieldId, aligned_bbox);
      const index = this.detail.fields.findIndex((field) => field.id === fieldId);
      if (index >= 0) {
        this.detail.fields[index] = updated;
      }
    },
    async save() {
      if (!this.detail) return;
      this.detail = await saveRecognitionFields(this.detail.id, this.detail.fields);
    },
  },
});
```

```ts
// frontend/src/composables/useRecognitionPolling.ts
import { onBeforeUnmount } from 'vue';
import type { RecognitionStatus } from '@/types/recognition';

export function useRecognitionPolling(run: () => Promise<RecognitionStatus>) {
  let timer: number | null = null;

  async function tick() {
    const status = await run();
    if (status === 'processing' || status === 'pending') {
      timer = window.setTimeout(tick, 1500);
    }
  }

  function start() {
    stop();
    timer = window.setTimeout(tick, 0);
  }

  function stop() {
    if (timer !== null) {
      window.clearTimeout(timer);
      timer = null;
    }
  }

  onBeforeUnmount(stop);
  return { start, stop };
}
```

- [ ] **Step 3: 创建识别页顶部工具栏与处理中状态**

```vue
<!-- frontend/src/components/recognition/RecognitionToolbar.vue -->
<template>
  <div class="recognition-toolbar">
    <ElButton type="primary" @click="$emit('save')">保存结果</ElButton>
    <ElButton @click="$emit('download-json')">下载 JSON</ElButton>
    <ElButton @click="$emit('download-xlsx')">下载 Excel</ElButton>
  </div>
</template>

<script setup lang="ts">
defineEmits<{ save: []; 'download-json': []; 'download-xlsx': [] }>();
</script>
```

- [ ] **Step 4: 创建识别视图基础骨架**

```vue
<!-- frontend/src/views/RecognitionView.vue -->
<template>
  <AppShell>
    <div v-if="store.detail?.status === 'processing' || store.detail?.status === 'pending'" class="processing-card">
      <ElResult icon="info" title="识别处理中" sub-title="后端正在进行 OCR、对齐和字段抽取，页面会自动刷新状态。" />
    </div>

    <div v-else-if="store.detail?.status === 'failed'" class="processing-card">
      <ElResult icon="error" title="识别失败" :sub-title="store.detail.error_message || '任务失败'" />
    </div>

    <div v-else class="review-layout">
      <RecognitionToolbar @save="save" @download-json="download('json')" @download-xlsx="download('xlsx')" />
      <div class="review-placeholder">下一任务补充框选校对与字段编辑面板。</div>
    </div>
  </AppShell>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { ElMessage } from 'element-plus';

import AppShell from '@/components/layout/AppShell.vue';
import RecognitionToolbar from '@/components/recognition/RecognitionToolbar.vue';
import { extractErrorMessage } from '@/api/http';
import { useRecognitionStore } from '@/stores/recognition';
import { useRecognitionPolling } from '@/composables/useRecognitionPolling';

const route = useRoute();
const store = useRecognitionStore();

const polling = useRecognitionPolling(async () => {
  await store.load(String(route.params.id));
  return store.detail?.status ?? 'failed';
});

onMounted(async () => {
  await store.load(String(route.params.id));
  if (store.detail?.status === 'processing' || store.detail?.status === 'pending') {
    polling.start();
  }
});

async function save() {
  try {
    await store.save();
    ElMessage.success('识别结果已保存');
  } catch (error) {
    ElMessage.error(extractErrorMessage(error));
  }
}

function download(format: 'json' | 'xlsx') {
  if (!store.detail) return;
  window.open(`/api/recognitions/${store.detail.id}/export?format=${format}`, '_blank');
}
</script>
```

- [ ] **Step 5: 运行测试**

Run: `cd frontend && npm run test -- recognition.store.spec.ts`  
Expected: 识别 store 的基础加载逻辑测试通过。

- [ ] **Step 6: Commit**

```bash
git add frontend/
git commit -m "feat: add recognition state and processing polling flow"
```

---

## Task 7: 识别校对页、重识别与字段编辑面板

**Files:**
- Create: `frontend/src/components/recognition/RecognitionFieldPanel.vue`
- Create: `frontend/src/components/recognition/TableFieldEditor.vue`
- Modify: `frontend/src/views/RecognitionView.vue`
- Test: `frontend/tests/components/RecognitionFieldPanel.spec.ts`

- [ ] **Step 1: 写字段面板单测**

```ts
// frontend/tests/components/RecognitionFieldPanel.spec.ts
import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';

import RecognitionFieldPanel from '@/components/recognition/RecognitionFieldPanel.vue';

describe('RecognitionFieldPanel', () => {
  it('renders text field editor', () => {
    const wrapper = mount(RecognitionFieldPanel, {
      props: {
        fields: [
          {
            id: 'f-1',
            template_field_id: 'tf-1',
            field_name: 'rew_name',
            aligned_bbox: { x1: 0, y1: 0, x2: 100, y2: 20 },
            raw_value: 'WONG',
            edited_value: null,
            confidence: 0.9,
            crop_path: null,
            alignment_status: 'auto',
          },
        ],
        selectedId: 'f-1',
      },
    });
    expect(wrapper.text()).toContain('rew_name');
  });
});
```

- [ ] **Step 2: 创建识别字段编辑组件**

```vue
<!-- frontend/src/components/recognition/TableFieldEditor.vue -->
<template>
  <ElTable :data="rows" border>
    <ElTableColumn
      v-for="column in columns"
      :key="column"
      :prop="column"
      :label="column"
    >
      <template #default="{ row }">
        <ElInput v-model="row[column]" />
      </template>
    </ElTableColumn>
  </ElTable>
</template>

<script setup lang="ts">
defineProps<{ rows: Record<string, unknown>[]; columns: string[] }>();
</script>
```

```vue
<!-- frontend/src/components/recognition/RecognitionFieldPanel.vue -->
<template>
  <div class="field-panel">
    <ElCard
      v-for="field in fields"
      :key="field.id"
      class="field-card"
      :class="{ 'field-card--selected': selectedId === field.id }"
      @click="$emit('select', field.id)"
    >
      <template #header>
        <div class="field-card__header">
          <span>{{ field.field_name }}</span>
          <ElTag
            :type="field.alignment_status === 'alignment_failed' ? 'danger' : field.edited_value != null ? 'success' : 'info'"
          >
            {{ field.alignment_status }}
          </ElTag>
        </div>
      </template>

      <ElInput
        v-if="typeof field.raw_value === 'string' || typeof field.edited_value === 'string' || field.raw_value == null"
        :model-value="String(field.edited_value ?? field.raw_value ?? '')"
        type="textarea"
        :rows="field.field_name.includes('address') ? 3 : 2"
        @update:model-value="$emit('update-value', field.id, $event)"
      />

      <ElCheckbox
        v-else-if="typeof field.raw_value === 'boolean' || typeof field.edited_value === 'boolean'"
        :model-value="Boolean(field.edited_value ?? field.raw_value)"
        @update:model-value="$emit('update-value', field.id, $event)"
      >
        已勾选
      </ElCheckbox>

      <TableFieldEditor
        v-else-if="Array.isArray(field.edited_value ?? field.raw_value)"
        :rows="(field.edited_value ?? field.raw_value) as Record<string, unknown>[]"
        :columns="Object.keys(((field.edited_value ?? field.raw_value) as Record<string, unknown>[])[0] ?? {})"
      />

      <div class="field-card__actions">
        <ElButton size="small" @click.stop="$emit('re-extract', field.id)">重新识别</ElButton>
      </div>
    </ElCard>
  </div>
</template>

<script setup lang="ts">
import TableFieldEditor from './TableFieldEditor.vue';
import type { RecognitionField } from '@/types/recognition';

defineProps<{ fields: RecognitionField[]; selectedId: string }>();
defineEmits<{
  select: [string];
  'update-value': [string, unknown];
  're-extract': [string];
}>();
</script>
```

- [ ] **Step 3: 完成识别校对页**

```vue
<!-- frontend/src/views/RecognitionView.vue -->
<template>
  <AppShell>
    <div v-if="store.detail?.status === 'processing' || store.detail?.status === 'pending'" class="processing-card">
      <ElResult icon="info" title="识别处理中" sub-title="后端正在进行 OCR、对齐和字段抽取，页面会自动刷新状态。" />
    </div>

    <div v-else-if="store.detail?.status === 'failed'" class="processing-card">
      <ElResult icon="error" title="识别失败" :sub-title="store.detail.error_message || '任务失败'" />
    </div>

    <div v-else-if="store.detail" class="review-layout">
      <RecognitionToolbar @save="save" @download-json="download('json')" @download-xlsx="download('xlsx')" />

      <section class="review-main">
        <PdfCanvas
          :image-url="`/api/recognitions/${store.detail.id}/pages/${currentPage}`"
          :boxes="pageBoxes"
          :editable="true"
          @boxChanged="handleBoxChanged"
        />
      </section>

      <aside class="review-side">
        <RecognitionFieldPanel
          :fields="currentFields"
          :selected-id="selectedFieldId"
          @select="(id) => (selectedFieldId = id)"
          @update-value="handleValueChange"
          @re-extract="handleReExtract"
        />
      </aside>
    </div>
  </AppShell>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import { ElMessage } from 'element-plus';

import AppShell from '@/components/layout/AppShell.vue';
import PdfCanvas from '@/components/pdf/PdfCanvas.vue';
import RecognitionToolbar from '@/components/recognition/RecognitionToolbar.vue';
import RecognitionFieldPanel from '@/components/recognition/RecognitionFieldPanel.vue';
import { extractErrorMessage } from '@/api/http';
import { useRecognitionStore } from '@/stores/recognition';
import { useRecognitionPolling } from '@/composables/useRecognitionPolling';

const route = useRoute();
const store = useRecognitionStore();
const currentPage = ref(1);
const selectedFieldId = ref('');

const polling = useRecognitionPolling(async () => {
  await store.load(String(route.params.id));
  return store.detail?.status ?? 'failed';
});

onMounted(async () => {
  await store.load(String(route.params.id));
  if (store.detail?.status === 'processing' || store.detail?.status === 'pending') {
    polling.start();
  } else {
    selectedFieldId.value = store.detail?.fields[0]?.id ?? '';
  }
});

const currentFields = computed(() => {
  return (store.detail?.fields ?? []).filter((field) => {
    const snapshotField = store.detail?.fields.find((item) => item.id === field.id);
    return Boolean(snapshotField) && currentPage.value >= 1;
  });
});

const pageBoxes = computed(() =>
  currentFields.value.map((field) => ({
    id: field.id,
    bbox: field.aligned_bbox,
    color:
      field.alignment_status === 'alignment_failed'
        ? '#dc2626'
        : selectedFieldId.value === field.id
          ? '#0f766e'
          : '#64748b',
  })),
);

function handleBoxChanged(payload: { id: string; bbox: { x1: number; y1: number; x2: number; y2: number } }) {
  const target = store.detail?.fields.find((field) => field.id === payload.id);
  if (!target) return;
  target.aligned_bbox = payload.bbox;
  target.alignment_status = 'manual_adjusted';
}

function handleValueChange(fieldId: string, value: unknown) {
  const target = store.detail?.fields.find((field) => field.id === fieldId);
  if (!target) return;
  target.edited_value = value;
  target.alignment_status = 'manual_adjusted';
}

async function handleReExtract(fieldId: string) {
  try {
    const target = store.detail?.fields.find((field) => field.id === fieldId);
    if (!target) return;
    await store.reExtract(fieldId, target.aligned_bbox);
    ElMessage.success('字段已重新识别');
  } catch (error) {
    ElMessage.error(extractErrorMessage(error));
  }
}

async function save() {
  try {
    await store.save();
    ElMessage.success('识别结果已保存');
  } catch (error) {
    ElMessage.error(extractErrorMessage(error));
  }
}

function download(format: 'json' | 'xlsx') {
  if (!store.detail) return;
  window.open(`/api/recognitions/${store.detail.id}/export?format=${format}`, '_blank');
}
</script>
```

- [ ] **Step 4: 运行组件测试**

Run: `cd frontend && npm run test -- RecognitionFieldPanel.spec.ts`  
Expected: 字段面板基础渲染测试通过。

- [ ] **Step 5: Commit**

```bash
git add frontend/
git commit -m "feat: add recognition review page and field editors"
```

---

## Task 8: README、手工验收与收尾

**Files:**
- Create: `frontend/tests/setup.ts`
- Create: `frontend/README.md`

- [ ] **Step 1: 创建测试初始化文件**

```ts
// frontend/tests/setup.ts
import { config } from '@vue/test-utils';

config.global.stubs = {
  RouterLink: {
    template: '<a><slot /></a>',
  },
  RouterView: {
    template: '<div><slot /></div>',
  },
};
```

- [ ] **Step 2: 创建 `frontend/README.md`**

```md
# Form OCR Frontend

前端基于 Vue 3 + Vite，实现模板列表、模板编辑、识别校对三类页面。

## 启动

```bash
cd frontend
npm install
npm run dev
```

默认访问 `http://localhost:5173`，并通过 Vite 代理或同源访问后端 `/api`。

## 构建

```bash
npm run build
```

## 测试

```bash
npm run test
```

## 手工验收

1. 模板列表页可以创建模板并跳到模板编辑器。
2. 模板编辑器能看到模板页图、创建字段、修改字段配置并保存。
3. 识别页创建任务后进入处理中，并自动轮询到成功或失败。
4. 成功后能看到对齐框、右侧字段值，拖框后可重识别。
5. 点击保存后字段 `edited_value` 能回写；JSON / Excel 下载可触发。
```

- [ ] **Step 3: 跑最终验证**

Run: `cd frontend && npm run test && npm run build`  
Expected: 单测和构建全部通过。

- [ ] **Step 4: Commit**

```bash
git add frontend/
git commit -m "docs: add frontend setup and verification guide"
```

---

## Self-Review Checklist

- [ ] 页面范围覆盖 spec §7：模板列表、模板编辑器、识别校对页均有对应任务
- [ ] API 对齐 spec §8：模板字段批量保存走 `POST /api/templates/{id}/fields`；识别轮询走 `GET /api/recognitions/{id}`
- [ ] 处理中状态覆盖 spec §2.2 / §7.3：`pending/processing` 有轮询与骨架提示
- [ ] 重识别闭环覆盖 spec §5.3：拖框修改 `aligned_bbox` 后调用 `POST /re-extract/{fid}`
- [ ] 导出覆盖 spec §2.2 / §8：JSON 与 Excel 都从识别页工具栏触发

---

## 覆盖对照表（spec ↔ task）

| Spec 章节 | 实现任务 |
|---|---|
| §7.1 模板列表页 | Tasks 2-3 |
| §7.2 模板编辑器 | Tasks 4-5 |
| §7.3 识别校对页 | Tasks 6-7 |
| §7.4 上传识别入口 | Task 3 |
| §8 前端所需 API 对接 | Tasks 2, 5, 6, 7 |
| §10.3 前端测试 | Tasks 3, 4, 5, 6, 7, 8 |

