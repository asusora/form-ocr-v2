/**
 * 表示图像或页面坐标系中的矩形框。
 */
export interface BBox {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

/**
 * 表示后端统一错误响应结构。
 */
export interface ApiErrorPayload {
  detail?: string;
  code?: string;
}

/**
 * 表示二维边界尺寸。
 */
export interface CanvasBoundary {
  width: number;
  height: number;
}
