<template>
  <div class="app-shell">
    <header class="app-shell__header page-card">
      <div>
        <p class="app-shell__eyebrow">GreenAI / Form OCR</p>
        <h1 class="app-shell__title">{{ title }}</h1>
        <p class="app-shell__subtitle">{{ subtitle }}</p>
      </div>

      <nav class="app-shell__nav">
        <RouterLink class="app-shell__link" to="/">模板列表</RouterLink>
      </nav>
    </header>

    <main class="app-shell__main">
      <slot />
    </main>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    title?: string;
    subtitle?: string;
  }>(),
  {
    title: '表单 OCR 工作台',
    subtitle: '模板配置、识别校对与结果导出的一体化前端实现。',
  },
);
</script>

<style scoped>
.app-shell {
  width: min(1440px, calc(100vw - 32px));
  margin: 0 auto;
  padding: 20px 0 32px;
}

.app-shell__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 24px 28px;
  margin-bottom: 24px;
}

.app-shell__eyebrow {
  margin: 0 0 10px;
  color: var(--accent);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.app-shell__title {
  margin: 0;
  font-size: clamp(24px, 4vw, 34px);
  line-height: 1.1;
}

.app-shell__subtitle {
  margin: 10px 0 0;
  max-width: 720px;
  color: var(--muted);
  line-height: 1.7;
}

.app-shell__nav {
  display: flex;
  align-items: center;
  gap: 12px;
}

.app-shell__link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 10px 16px;
  border: 1px solid var(--line-strong);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.7);
  color: var(--text);
  font-weight: 600;
  transition:
    transform 0.2s ease,
    border-color 0.2s ease,
    color 0.2s ease;
}

.app-shell__link:hover {
  color: var(--accent);
  border-color: var(--accent);
  transform: translateY(-1px);
}

.app-shell__main {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

@media (max-width: 960px) {
  .app-shell {
    width: min(100vw - 20px, 1440px);
    padding-top: 12px;
  }

  .app-shell__header {
    flex-direction: column;
    align-items: flex-start;
    padding: 20px;
  }
}
</style>
