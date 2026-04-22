<template>
  <ElDialog
    :model-value="visible"
    width="560px"
    title="新建模板"
    @close="emit('close')"
  >
    <div class="dialog-copy">
      上传一份空白模板 PDF。后端会负责转图与页级缓存，前端直接进入模板编辑器。
    </div>

    <ElForm label-position="top">
      <ElFormItem label="模板名称" required>
        <ElInput v-model.trim="name" maxlength="128" placeholder="例如：WR1A 电业工程证明" />
      </ElFormItem>

      <ElFormItem label="模板描述">
        <ElInput
          v-model.trim="description"
          maxlength="500"
          placeholder="可选，用于区分模板版本和适用场景"
          type="textarea"
          :rows="3"
        />
      </ElFormItem>

      <ElFormItem label="模板 PDF" required>
        <input ref="fileInputRef" accept="application/pdf" type="file" @change="handleFileChange" />
        <p v-if="file" class="file-hint">已选择：{{ file.name }}</p>
      </ElFormItem>

      <ElFormItem label="渲染 DPI">
        <ElInputNumber v-model="renderDpi" :min="120" :max="300" :step="10" />
      </ElFormItem>
    </ElForm>

    <template #footer>
      <ElButton @click="emit('close')">取消</ElButton>
      <ElButton type="primary" :disabled="!canSubmit" @click="handleSubmit">创建模板</ElButton>
    </template>
  </ElDialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { ElMessage } from 'element-plus';

const props = defineProps<{
  visible: boolean;
}>();

const emit = defineEmits<{
  close: [];
  submit: [{ name: string; description: string; file: File; renderDpi: number }];
}>();

const name = ref('');
const description = ref('');
const renderDpi = ref(200);
const file = ref<File | null>(null);
const fileInputRef = ref<HTMLInputElement | null>(null);

const canSubmit = computed(() => Boolean(name.value.trim()) && Boolean(file.value));

watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      resetForm();
    }
  },
);

/**
 * 重置对话框表单状态。
 */
function resetForm(): void {
  name.value = '';
  description.value = '';
  renderDpi.value = 200;
  file.value = null;
  if (fileInputRef.value) {
    fileInputRef.value.value = '';
  }
}

/**
 * 处理文件选择事件。
 */
function handleFileChange(event: Event): void {
  const input = event.target as HTMLInputElement;
  const nextFile = input.files?.[0] ?? null;
  if (!nextFile) {
    file.value = null;
    return;
  }

  if (!nextFile.name.toLowerCase().endsWith('.pdf')) {
    ElMessage.error('只允许上传 PDF 文件');
    file.value = null;
    if (fileInputRef.value) {
      fileInputRef.value.value = '';
    }
    return;
  }

  file.value = nextFile;
}

/**
 * 提交新建模板表单。
 */
function handleSubmit(): void {
  if (!file.value || !name.value.trim()) {
    return;
  }

  emit('submit', {
    name: name.value.trim(),
    description: description.value.trim(),
    file: file.value,
    renderDpi: renderDpi.value,
  });
}
</script>

<style scoped>
.dialog-copy {
  margin-bottom: 16px;
  color: var(--muted);
  line-height: 1.7;
}

.file-hint {
  margin: 8px 0 0;
  color: var(--muted);
  font-size: 13px;
}
</style>
