<template>
  <section class="page-card anchor-panel">
    <header class="anchor-panel__header">
      <div>
        <h2 class="section-title">锚点预览</h2>
        <p class="section-desc">保存模板字段后，后端会自动抽取周围稳定文本作为锚点。</p>
      </div>
    </header>

    <ElEmpty v-if="!anchors?.length" description="当前字段还没有锚点，保存后会自动生成。" />

    <div v-else class="anchor-panel__list">
      <article
        v-for="anchor in anchors"
        :key="`${anchor.text}-${anchor.template_bbox.x1}-${anchor.template_bbox.y1}`"
        class="anchor-panel__item"
      >
        <div class="anchor-panel__text">{{ anchor.text }}</div>
        <div class="anchor-panel__meta">
          x: {{ anchor.template_bbox.x1 }} - {{ anchor.template_bbox.x2 }} ·
          y: {{ anchor.template_bbox.y1 }} - {{ anchor.template_bbox.y2 }}
        </div>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  anchors?: Array<{
    text: string;
    template_bbox: { x1: number; y1: number; x2: number; y2: number };
  }> | null;
}>();
</script>

<style scoped>
.anchor-panel {
  padding: 20px;
}

.anchor-panel__header {
  margin-bottom: 16px;
}

.anchor-panel__list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.anchor-panel__item {
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: rgba(15, 118, 110, 0.05);
}

.anchor-panel__text {
  font-weight: 700;
}

.anchor-panel__meta {
  margin-top: 4px;
  color: var(--muted);
  font-size: 13px;
}
</style>
