<template>
  <section class="page-card recognition-toolbar">
    <div>
      <h2 class="section-title">识别校对</h2>
      <p class="section-desc">拖拽左侧框调整位置，右侧修正文案，保存后即可导出。</p>
    </div>

    <div class="recognition-toolbar__actions">
      <div class="recognition-toolbar__pager">
        <ElButton :disabled="page <= 1" @click="emit('prev-page')">上一页</ElButton>
        <span>第 {{ page }} / {{ totalPages }} 页</span>
        <ElButton :disabled="page >= totalPages" @click="emit('next-page')">下一页</ElButton>
      </div>

      <ElButton :loading="busy" :disabled="disableActions" type="primary" @click="emit('save')">
        保存结果
      </ElButton>
      <ElButton :disabled="disableActions" @click="emit('download-json')">下载 JSON</ElButton>
      <ElButton :disabled="disableActions" @click="emit('download-xlsx')">下载 Excel</ElButton>
    </div>
  </section>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    page: number;
    totalPages: number;
    busy?: boolean;
    disableActions?: boolean;
  }>(),
  {
    busy: false,
    disableActions: false,
  },
);

const emit = defineEmits<{
  save: [];
  'download-json': [];
  'download-xlsx': [];
  'prev-page': [];
  'next-page': [];
}>();
</script>

<style scoped>
.recognition-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 18px 20px;
}

.recognition-toolbar__actions,
.recognition-toolbar__pager {
  display: flex;
  align-items: center;
  gap: 10px;
}

.recognition-toolbar__pager span {
  min-width: 96px;
  text-align: center;
  color: var(--muted);
  font-size: 14px;
}

@media (max-width: 1080px) {
  .recognition-toolbar {
    flex-direction: column;
    align-items: flex-start;
  }

  .recognition-toolbar__actions {
    flex-wrap: wrap;
  }
}
</style>
