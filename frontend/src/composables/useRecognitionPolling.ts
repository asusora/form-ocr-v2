import { onBeforeUnmount, ref } from 'vue';

import type { RecognitionStatus } from '@/types/recognition';

/**
 * 统一管理识别状态轮询。
 */
export function useRecognitionPolling(
  run: () => Promise<RecognitionStatus>,
  intervalMs = 1500,
) {
  const active = ref(false);
  let timer: number | null = null;

  /**
   * 清理定时器。
   */
  function clearTimer(): void {
    if (timer !== null) {
      window.clearTimeout(timer);
      timer = null;
    }
  }

  /**
   * 停止轮询。
   */
  function stop(): void {
    active.value = false;
    clearTimer();
  }

  /**
   * 继续下一次轮询。
   */
  function schedule(): void {
    clearTimer();
    timer = window.setTimeout(() => {
      void tick();
    }, intervalMs);
  }

  /**
   * 执行单次轮询。
   */
  async function tick(): Promise<void> {
    if (!active.value) {
      return;
    }

    const status = await run();
    if (status === 'pending' || status === 'processing') {
      schedule();
      return;
    }

    stop();
  }

  /**
   * 启动轮询。
   */
  function start(): void {
    stop();
    active.value = true;
    void tick();
  }

  onBeforeUnmount(stop);

  return {
    active,
    start,
    stop,
  };
}
