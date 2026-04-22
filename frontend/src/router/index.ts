import { createRouter, createWebHistory } from 'vue-router';

/**
 * 创建前端路由实例。
 */
const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'template-list',
      component: () => import('@/views/TemplateListView.vue'),
    },
    {
      path: '/templates/:id',
      name: 'template-editor',
      component: () => import('@/views/TemplateEditorView.vue'),
    },
    {
      path: '/recognitions/:id',
      name: 'recognition',
      component: () => import('@/views/RecognitionView.vue'),
    },
  ],
});

export default router;
