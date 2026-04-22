<template>
  <ElDialog
    :model-value="visible"
    width="520px"
    title="创建识别任务"
    @close="emit('close')"
  >
    <div class="dialog-copy">
      为模板“{{ templateName }}”上传一份待识别 PDF。创建后会进入处理中页面，并自动轮询状态。
    </div>

    <ElForm label-position="top">
      <ElFormItem label="待识别 PDF" required>
        <input ref="fileInputRef" accept="application/pdf" type="file" @change="handleFileChange" />
        <p v-if="file" class="file-hint">已选择：{{ file.name }}</p>
      </ElFormItem>
    </ElForm>

    <template #footer>
      <ElButton @click="emit('close')">取消</ElButton>
      <ElButton type="primary" :disabled="!file" @click="handleSubmit">开始识别</ElButton>
    </template>
  </ElDialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { ElMessage } from 'element-plus';

const props = defineProps<{
  visible: boolean;
  templateName: string;
}>();

const emit = defineEmits<{
  close: [];
  submit: [File];
}>();

const file = ref<File | null>(null);
const fileInputRef = ref<HTMLInputElement | null>(null);

watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      resetState();
    }
  },
);

/**
 * 重置上传状态。
 */
function resetState(): void {
  file.value = null;
  if (fileInputRef.value) {
    fileInputRef.value.value = '';
  }
}

/**
 * 处理识别 PDF 选择。
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
 * 提交识别任务创建。
 */
function handleSubmit(): void {
  if (!file.value) {
    return;
  }

  emit('submit', file.value);
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
