import type { BBox, CanvasBoundary } from '@/types/common';

/**
 * 将图像坐标系中的矩形缩放到视口坐标系。
 */
export function scaleBBox(bbox: BBox, ratio: number): BBox {
  return {
    x1: bbox.x1 * ratio,
    y1: bbox.y1 * ratio,
    x2: bbox.x2 * ratio,
    y2: bbox.y2 * ratio,
  };
}

/**
 * 将视口坐标系中的矩形还原回图像坐标系。
 */
export function unscaleBBox(bbox: BBox, ratio: number): BBox {
  if (ratio === 0) {
    return bbox;
  }

  return {
    x1: bbox.x1 / ratio,
    y1: bbox.y1 / ratio,
    x2: bbox.x2 / ratio,
    y2: bbox.y2 / ratio,
  };
}

/**
 * 规范化拖拽产生的矩形，确保左上和右下顺序正确。
 */
export function normalizeBBox(bbox: BBox): BBox {
  return {
    x1: Math.min(bbox.x1, bbox.x2),
    y1: Math.min(bbox.y1, bbox.y2),
    x2: Math.max(bbox.x1, bbox.x2),
    y2: Math.max(bbox.y1, bbox.y2),
  };
}

/**
 * 将矩形限制在页面边界内。
 */
export function clampBBox(bbox: BBox, boundary: CanvasBoundary): BBox {
  const normalized = normalizeBBox(bbox);

  return {
    x1: clampNumber(normalized.x1, 0, boundary.width),
    y1: clampNumber(normalized.y1, 0, boundary.height),
    x2: clampNumber(normalized.x2, 0, boundary.width),
    y2: clampNumber(normalized.y2, 0, boundary.height),
  };
}

/**
 * 根据两个点生成矩形。
 */
export function createBBoxFromPoints(
  start: { x: number; y: number },
  end: { x: number; y: number },
): BBox {
  return normalizeBBox({
    x1: start.x,
    y1: start.y,
    x2: end.x,
    y2: end.y,
  });
}

/**
 * 返回矩形的宽高。
 */
export function getBBoxSize(bbox: BBox): { width: number; height: number } {
  const normalized = normalizeBBox(bbox);
  return {
    width: normalized.x2 - normalized.x1,
    height: normalized.y2 - normalized.y1,
  };
}

/**
 * 将数值限制在指定范围内。
 */
export function clampNumber(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}
