import { defineStore } from 'pinia';
import { ref } from 'vue';

import {
  fetchRecognition,
  reExtractField,
  saveRecognitionFields,
} from '@/api/recognitions';
import type { BBox } from '@/types/common';
import type { RecognitionDetail } from '@/types/recognition';

export const useRecognitionStore = defineStore('recognition', () => {
  const detail = ref<RecognitionDetail | null>(null);
  const loading = ref(false);
  const saving = ref(false);

  /**
   * 获取识别详情。
   */
  async function load(recognitionId: string): Promise<void> {
    loading.value = true;
    try {
      detail.value = await fetchRecognition(recognitionId);
    } finally {
      loading.value = false;
    }
  }

  /**
   * 更新本地字段值。
   */
  function updateFieldValue(fieldId: string, value: unknown): void {
    const target = detail.value?.fields.find((field) => field.id === fieldId);
    if (!target) {
      return;
    }

    target.edited_value = value;
    target.alignment_status = 'manual_adjusted';
  }

  /**
   * 更新本地字段框位置。
   */
  function updateFieldBBox(fieldId: string, bbox: BBox): void {
    const target = detail.value?.fields.find((field) => field.id === fieldId);
    if (!target) {
      return;
    }

    target.aligned_bbox = bbox;
    target.alignment_status = 'manual_adjusted';
  }

  /**
   * 重新识别单个字段。
   */
  async function reExtract(fieldId: string, alignedBBox: BBox): Promise<void> {
    if (!detail.value) {
      return;
    }

    const updated = await reExtractField(detail.value.id, fieldId, alignedBBox);
    const index = detail.value.fields.findIndex((field) => field.id === fieldId);
    if (index >= 0) {
      detail.value.fields.splice(index, 1, updated);
    }
  }

  /**
   * 保存全部校对结果。
   */
  async function save(): Promise<void> {
    if (!detail.value) {
      return;
    }

    saving.value = true;
    try {
      detail.value = await saveRecognitionFields(detail.value.id, detail.value.fields);
    } finally {
      saving.value = false;
    }
  }

  return {
    detail,
    loading,
    saving,
    load,
    updateFieldValue,
    updateFieldBBox,
    reExtract,
    save,
  };
});
