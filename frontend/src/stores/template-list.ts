import { defineStore } from 'pinia';
import { ref } from 'vue';

import { fetchTemplates } from '@/api/templates';
import type { TemplateSummary } from '@/types/template';

export const useTemplateListStore = defineStore('template-list', () => {
  const items = ref<TemplateSummary[]>([]);
  const loading = ref(false);

  /**
   * 拉取模板列表。
   */
  async function load(): Promise<void> {
    loading.value = true;
    try {
      items.value = await fetchTemplates();
    } finally {
      loading.value = false;
    }
  }

  return {
    items,
    loading,
    load,
  };
});
