// Satisfies pwa-register.ts lazy chunk when Rolldown still emits it in portable builds.
export function registerSW(_options?: unknown): (reload?: boolean) => Promise<void> {
  return async () => {};
}
