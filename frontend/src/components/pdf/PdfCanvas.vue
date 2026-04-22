<template>
  <section class="page-card pdf-canvas">
    <div
      ref="viewportRef"
      class="pdf-canvas__viewport"
      :class="{ 'pdf-canvas__viewport--create': createMode }"
      @pointerdown="handleViewportPointerDown"
    >
      <img
        v-if="imageUrl"
        ref="imageRef"
        class="pdf-canvas__image"
        :src="imageUrl"
        alt="pdf page preview"
        draggable="false"
        @load="handleImageLoad"
      />

      <ElEmpty v-else class="pdf-canvas__empty" description="当前页图像不可用。" />

      <div v-if="imageLoaded" class="pdf-canvas__overlay">
        <button
          v-for="box in displayBoxes"
          :key="box.id"
          class="pdf-canvas__box"
          :class="{ 'pdf-canvas__box--selected': box.id === selectedId }"
          :style="box.style"
          data-box-interactive="true"
          type="button"
          @click.stop="handleBoxClick(box.id)"
          @pointerdown.stop="handleBoxMoveStart(box.id, $event)"
        >
          <span v-if="box.label" class="pdf-canvas__label">{{ box.label }}</span>
          <span
            v-if="editable"
            class="pdf-canvas__edge-handle pdf-canvas__edge-handle--top"
            data-box-interactive="true"
            data-resize-edge="top"
            @pointerdown.stop.prevent="handleBoxResizeStart(box.id, 'top', $event)"
          />
          <span
            v-if="editable"
            class="pdf-canvas__edge-handle pdf-canvas__edge-handle--right"
            data-box-interactive="true"
            data-resize-edge="right"
            @pointerdown.stop.prevent="handleBoxResizeStart(box.id, 'right', $event)"
          />
          <span
            v-if="editable"
            class="pdf-canvas__edge-handle pdf-canvas__edge-handle--bottom"
            data-box-interactive="true"
            data-resize-edge="bottom"
            @pointerdown.stop.prevent="handleBoxResizeStart(box.id, 'bottom', $event)"
          />
          <span
            v-if="editable"
            class="pdf-canvas__edge-handle pdf-canvas__edge-handle--left"
            data-box-interactive="true"
            data-resize-edge="left"
            @pointerdown.stop.prevent="handleBoxResizeStart(box.id, 'left', $event)"
          />
        </button>

        <div v-if="draftStyle" class="pdf-canvas__draft" :style="draftStyle" />
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';

import {
  clampBBox,
  clampNumber,
  createBBoxFromPoints,
  getBBoxSize,
  scaleBBox,
} from '@/composables/useCanvasScale';
import type { BBox, CanvasBoundary } from '@/types/common';

interface PdfCanvasBox {
  id: string;
  bbox: BBox;
  color?: string;
  label?: string;
}

type ResizeEdge = 'top' | 'right' | 'bottom' | 'left';

interface DragState {
  mode: 'move' | 'resize' | 'create';
  boxId?: string;
  resizeEdge?: ResizeEdge;
  start: { x: number; y: number };
  originBBox?: BBox;
}

const MIN_BOX_SIZE = 12;

/**
 * 复制框选坐标，避免依赖 structuredClone。
 */
function cloneBBox(bbox: BBox): BBox {
  return {
    x1: bbox.x1,
    y1: bbox.y1,
    x2: bbox.x2,
    y2: bbox.y2,
  };
}

const props = withDefaults(
  defineProps<{
    imageUrl: string;
    boxes: PdfCanvasBox[];
    editable?: boolean;
    selectedId?: string;
    createMode?: boolean;
  }>(),
  {
    editable: false,
    selectedId: '',
    createMode: false,
  },
);

const emit = defineEmits<{
  'box-changed': [{ id: string; bbox: BBox }];
  'box-created': [BBox];
  'box-selected': [string];
}>();

const viewportRef = ref<HTMLDivElement | null>(null);
const imageRef = ref<HTMLImageElement | null>(null);
const imageLoaded = ref(false);
const ratio = ref(1);
const naturalBoundary = ref<CanvasBoundary>({ width: 1000, height: 1000 });
const draftBox = ref<BBox | null>(null);
const transientBoxes = ref<Record<string, BBox>>({});

let dragState: DragState | null = null;

const displayBoxes = computed(() => {
  return props.boxes.map((box) => {
    const currentBBox = transientBoxes.value[box.id] ?? box.bbox;
    const scaled = scaleBBox(currentBBox, ratio.value || 1);
    return {
      ...box,
      style: {
        left: `${scaled.x1}px`,
        top: `${scaled.y1}px`,
        width: `${Math.max(0, scaled.x2 - scaled.x1)}px`,
        height: `${Math.max(0, scaled.y2 - scaled.y1)}px`,
        borderColor: box.color ?? '#0f766e',
      },
    };
  });
});

const draftStyle = computed(() => {
  if (!draftBox.value) {
    return null;
  }

  const scaled = scaleBBox(draftBox.value, ratio.value || 1);
  return {
    left: `${scaled.x1}px`,
    top: `${scaled.y1}px`,
    width: `${Math.max(0, scaled.x2 - scaled.x1)}px`,
    height: `${Math.max(0, scaled.y2 - scaled.y1)}px`,
  };
});

watch(
  () => props.imageUrl,
  () => {
    imageLoaded.value = false;
    draftBox.value = null;
    transientBoxes.value = {};
  },
);

watch(
  () => props.createMode,
  (enabled) => {
    if (!enabled) {
      draftBox.value = null;
    }
  },
);

onMounted(() => {
  window.addEventListener('pointermove', handleWindowPointerMove);
  window.addEventListener('pointerup', handleWindowPointerUp);
  window.addEventListener('resize', updateRatio);
});

onBeforeUnmount(() => {
  window.removeEventListener('pointermove', handleWindowPointerMove);
  window.removeEventListener('pointerup', handleWindowPointerUp);
  window.removeEventListener('resize', updateRatio);
});

/**
 * 获取当前图像边界。
 */
function getBoundary(): CanvasBoundary {
  return naturalBoundary.value;
}

/**
 * 根据图片显示宽度刷新缩放比例。
 */
function updateRatio(): void {
  if (!imageRef.value) {
    return;
  }

  const currentWidth = imageRef.value.clientWidth || imageRef.value.naturalWidth;
  const currentHeight = imageRef.value.clientHeight || imageRef.value.naturalHeight;
  if (!imageRef.value.naturalWidth || !imageRef.value.naturalHeight) {
    return;
  }

  naturalBoundary.value = {
    width: imageRef.value.naturalWidth,
    height: imageRef.value.naturalHeight,
  };
  ratio.value = currentWidth / imageRef.value.naturalWidth;

  if (!Number.isFinite(ratio.value) || ratio.value <= 0) {
    ratio.value = currentHeight / imageRef.value.naturalHeight;
  }
}

/**
 * 将指针坐标转换为图像坐标。
 */
function toImagePoint(event: PointerEvent): { x: number; y: number } {
  const rect = viewportRef.value?.getBoundingClientRect();
  const currentRatio = ratio.value || 1;
  const boundary = getBoundary();

  if (!rect) {
    return { x: 0, y: 0 };
  }

  return {
    x: clampNumber((event.clientX - rect.left) / currentRatio, 0, boundary.width),
    y: clampNumber((event.clientY - rect.top) / currentRatio, 0, boundary.height),
  };
}

/**
 * 图片加载完成后初始化边界信息。
 */
function handleImageLoad(): void {
  imageLoaded.value = true;
  updateRatio();
}

/**
 * 选中某个框。
 */
function handleBoxClick(id: string): void {
  emit('box-selected', id);
}

/**
 * 开始拖动已有框。
 */
function handleBoxMoveStart(boxId: string, event: PointerEvent): void {
  emit('box-selected', boxId);
  if (!props.editable) {
    return;
  }

  event.preventDefault();

  const box = props.boxes.find((item) => item.id === boxId);
  if (!box) {
    return;
  }

  dragState = {
    mode: 'move',
    boxId,
    start: toImagePoint(event),
    originBBox: cloneBBox(transientBoxes.value[boxId] ?? box.bbox),
  };
}

/**
 * 开始缩放已有框。
 */
function handleBoxResizeStart(boxId: string, resizeEdge: ResizeEdge, event: PointerEvent): void {
  emit('box-selected', boxId);
  if (!props.editable) {
    return;
  }

  event.preventDefault();

  const box = props.boxes.find((item) => item.id === boxId);
  if (!box) {
    return;
  }

  dragState = {
    mode: 'resize',
    boxId,
    start: toImagePoint(event),
    resizeEdge,
    originBBox: cloneBBox(transientBoxes.value[boxId] ?? box.bbox),
  };
}

/**
 * 在创建模式下开始画新框。
 */
function handleViewportPointerDown(event: PointerEvent): void {
  if (!props.editable || !props.createMode) {
    return;
  }

  const target = event.target as HTMLElement;
  if (target.dataset.boxInteractive === 'true') {
    return;
  }

  const point = toImagePoint(event);
  event.preventDefault();
  dragState = {
    mode: 'create',
    start: point,
  };
  draftBox.value = {
    x1: point.x,
    y1: point.y,
    x2: point.x,
    y2: point.y,
  };
}

/**
 * 按移动模式计算新矩形。
 */
function buildMoveBBox(originBBox: BBox, currentPoint: { x: number; y: number }, startPoint: { x: number; y: number }): BBox {
  const deltaX = currentPoint.x - startPoint.x;
  const deltaY = currentPoint.y - startPoint.y;
  return clampBBox(
    {
      x1: originBBox.x1 + deltaX,
      y1: originBBox.y1 + deltaY,
      x2: originBBox.x2 + deltaX,
      y2: originBBox.y2 + deltaY,
    },
    getBoundary(),
  );
}

/**
 * 按缩放模式计算新矩形。
 */
function buildResizeBBox(originBBox: BBox, currentPoint: { x: number; y: number }, resizeEdge: ResizeEdge): BBox {
  const boundary = getBoundary();

  if (resizeEdge === 'left') {
    return {
      ...originBBox,
      x1: clampNumber(currentPoint.x, 0, originBBox.x2 - MIN_BOX_SIZE),
    };
  }

  if (resizeEdge === 'right') {
    return {
      ...originBBox,
      x2: clampNumber(currentPoint.x, originBBox.x1 + MIN_BOX_SIZE, boundary.width),
    };
  }

  if (resizeEdge === 'top') {
    return {
      ...originBBox,
      y1: clampNumber(currentPoint.y, 0, originBBox.y2 - MIN_BOX_SIZE),
    };
  }

  return {
    ...originBBox,
    y2: clampNumber(currentPoint.y, originBBox.y1 + MIN_BOX_SIZE, boundary.height),
  };
}

/**
 * 处理全局指针移动，实时更新画框状态。
 */
function handleWindowPointerMove(event: PointerEvent): void {
  if (!dragState) {
    return;
  }

  const currentPoint = toImagePoint(event);
  if (dragState.mode === 'create') {
    draftBox.value = clampBBox(createBBoxFromPoints(dragState.start, currentPoint), getBoundary());
    return;
  }

  if (!dragState.boxId || !dragState.originBBox) {
    return;
  }

  const nextBBox =
    dragState.mode === 'move'
      ? buildMoveBBox(dragState.originBBox, currentPoint, dragState.start)
      : dragState.resizeEdge
        ? buildResizeBBox(dragState.originBBox, currentPoint, dragState.resizeEdge)
        : dragState.originBBox;

  transientBoxes.value = {
    ...transientBoxes.value,
    [dragState.boxId]: nextBBox,
  };
}

/**
 * 处理全局指针抬起，提交当前编辑结果。
 */
function handleWindowPointerUp(): void {
  if (!dragState) {
    return;
  }

  if (dragState.mode === 'create' && draftBox.value) {
    const size = getBBoxSize(draftBox.value);
    if (size.width >= 12 && size.height >= 12) {
      emit('box-created', draftBox.value);
    }
    draftBox.value = null;
    dragState = null;
    return;
  }

  if (dragState.boxId && transientBoxes.value[dragState.boxId]) {
    emit('box-changed', {
      id: dragState.boxId,
      bbox: transientBoxes.value[dragState.boxId],
    });
    const { [dragState.boxId]: _discard, ...rest } = transientBoxes.value;
    transientBoxes.value = rest;
  }

  dragState = null;
}
</script>

<style scoped>
.pdf-canvas {
  padding: 18px;
}

.pdf-canvas__viewport {
  position: relative;
  overflow: hidden;
  border-radius: 18px;
  background:
    linear-gradient(135deg, rgba(15, 118, 110, 0.06), rgba(255, 255, 255, 0.92)),
    #ffffff;
}

.pdf-canvas__viewport--create {
  cursor: crosshair;
}

.pdf-canvas__image {
  display: block;
  width: 100%;
  height: auto;
  user-select: none;
}

.pdf-canvas__overlay {
  position: absolute;
  inset: 0;
}

.pdf-canvas__box,
.pdf-canvas__draft {
  position: absolute;
  border: 2px solid var(--accent);
  border-radius: 0;
}

.pdf-canvas__box {
  background: rgba(15, 118, 110, 0.08);
  cursor: move;
}

.pdf-canvas__box--selected {
  box-shadow: inset 0 0 0 1px #ffffff, 0 0 0 2px rgba(15, 118, 110, 0.2);
}

.pdf-canvas__draft {
  border-style: dashed;
  background: rgba(14, 165, 233, 0.08);
  pointer-events: none;
}

.pdf-canvas__label {
  position: absolute;
  top: -30px;
  left: 0;
  padding: 4px 8px;
  border-radius: 999px;
  background: rgba(15, 118, 110, 0.9);
  color: #ffffff;
  font-size: 12px;
  white-space: nowrap;
}

.pdf-canvas__edge-handle {
  position: absolute;
  z-index: 1;
}

.pdf-canvas__edge-handle--top,
.pdf-canvas__edge-handle--bottom {
  left: 6px;
  right: 6px;
  height: 12px;
}

.pdf-canvas__edge-handle--top {
  top: -6px;
  cursor: ns-resize;
}

.pdf-canvas__edge-handle--right,
.pdf-canvas__edge-handle--left {
  top: 6px;
  bottom: 6px;
  width: 12px;
}

.pdf-canvas__edge-handle--right {
  right: -6px;
  cursor: ew-resize;
}

.pdf-canvas__edge-handle--bottom {
  bottom: -6px;
  cursor: ns-resize;
}

.pdf-canvas__edge-handle--left {
  left: -6px;
  cursor: ew-resize;
}

.pdf-canvas__empty {
  padding: 56px 0;
}
</style>
