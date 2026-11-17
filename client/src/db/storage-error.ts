/** Keep storage failures actionable across the Worker boundary. */
export function storageError(error: unknown, stage: string, fileName?: string) {
  const source = error as { name?: string; message?: string; stage?: string; fileName?: string } | null;
  return Object.assign(new Error(source?.message || String(error), { cause: error }), {
    name: source?.name || 'Error', stage: source?.stage || stage, fileName: source?.fileName || fileName,
  });
}

export function isMissingFile(error: unknown): boolean {
  return (error as { name?: string } | null)?.name === 'NotFoundError';
}

export function storageFailureMessage(error: unknown): string | null {
  const { name, stage } = (error ?? {}) as { name?: string; stage?: string };
  if (name === 'QuotaExceededError') return '本機儲存空間不足，請釋放空間後重試';
  if (name === 'NotAllowedError' || name === 'SecurityError') {
    return '瀏覽器限制本機儲存，請使用一般瀏覽模式並檢查網站儲存設定後重試';
  }
  if (name === 'NoModificationAllowedError' || name === 'InvalidStateError') {
    return '詞庫暫時被使用，請關閉其他 Canto 分頁後重試';
  }
  if (name === 'NotSupportedError') return '此瀏覽器未能寫入離線詞庫，請更新瀏覽器後重試';
  return stage ? '本機詞庫儲存失敗，請重試；如持續失敗，請檢查儲存空間及網站儲存設定' : null;
}
