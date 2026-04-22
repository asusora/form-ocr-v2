import { computed, ref, unref, watch, type MaybeRef } from 'vue';

/**
 * 统一管理多页 PDF 的页码切换状态。
 */
export function usePdfPages(totalPages: MaybeRef<number>, initialPage = 1) {
  const currentPage = ref(initialPage);

  const safeTotalPages = computed(() => Math.max(1, unref(totalPages) || 1));
  const canGoPrev = computed(() => currentPage.value > 1);
  const canGoNext = computed(() => currentPage.value < safeTotalPages.value);

  watch(
    safeTotalPages,
    (value) => {
      if (currentPage.value > value) {
        currentPage.value = value;
      }
    },
    { immediate: true },
  );

  /**
   * 设置当前页码。
   */
  function setPage(page: number): void {
    currentPage.value = Math.min(Math.max(1, page), safeTotalPages.value);
  }

  /**
   * 切换到上一页。
   */
  function prevPage(): void {
    setPage(currentPage.value - 1);
  }

  /**
   * 切换到下一页。
   */
  function nextPage(): void {
    setPage(currentPage.value + 1);
  }

  return {
    currentPage,
    safeTotalPages,
    canGoPrev,
    canGoNext,
    setPage,
    prevPage,
    nextPage,
  };
}
