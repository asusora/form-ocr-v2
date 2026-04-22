import axios from 'axios';
import type { AxiosError } from 'axios';

import type { ApiErrorPayload } from '@/types/common';

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() || '/api';

/**
 * 统一的 HTTP 客户端实例。
 */
export const http = axios.create({
  baseURL: apiBaseUrl,
  timeout: 30_000,
});

/**
 * 构建可直接用于 `<img>` 或 `window.open` 的接口地址。
 */
export function buildApiUrl(path: string): string {
  const normalizedBase = apiBaseUrl.endsWith('/') ? apiBaseUrl.slice(0, -1) : apiBaseUrl;
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${normalizedBase}${normalizedPath}`;
}

/**
 * 提取用户可读的错误消息。
 */
export function extractErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const response = error as AxiosError<ApiErrorPayload>;
    return response.response?.data?.detail || response.message || '请求失败';
  }

  if (error instanceof Error) {
    return error.message;
  }

  return '请求失败';
}
