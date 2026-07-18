/**
 * Opt-in PWA idle/resume diagnostics (`?resumeDebug=1`).
 * ponytail: memory-only, bounded, and deliberately records no query/SQL data.
 */

export type ResumeDebugScalar = string | number | boolean | null;
export type ResumeDebugDetail = Record<string, ResumeDebugScalar>;

export type ResumeDebugEvent = {
  at: number;
  type: string;
  detail: ResumeDebugDetail;
};

export type ResumeDebugWorkerState = {
  exists: boolean;
  pending: Array<{ id: number; type: string; ageMs: number }>;
};

export type ResumeDebugSnapshot = {
  now: number;
  visibilityState: DocumentVisibilityState;
  backendMode: string | null;
  worker: ResumeDebugWorkerState;
  events: ResumeDebugEvent[];
};

export type ResumeDebugState = {
  readonly startedAt: number;
  readonly events: ResumeDebugEvent[];
  snapshot: () => ResumeDebugSnapshot;
};

type BufferOptions = {
  now: () => number;
  getVisibilityState: () => DocumentVisibilityState;
  getBackendMode: () => string | null;
  getWorkerState: () => ResumeDebugWorkerState;
  limit?: number;
};

type InstallOptions = {
  getBackendMode: () => string | null;
  getWorkerState: () => ResumeDebugWorkerState;
};

declare global {
  interface Window {
    __resumeDebug?: ResumeDebugState;
  }
}

const DEFAULT_LIMIT = 200;
let activeRecord: ((type: string, detail?: ResumeDebugDetail) => void) | null = null;

function cloneEvent(event: ResumeDebugEvent): ResumeDebugEvent {
  return { ...event, detail: { ...event.detail } };
}

function assertScalarDetail(detail: ResumeDebugDetail): void {
  if (!detail || Array.isArray(detail) || typeof detail !== 'object') {
    throw new TypeError('resume debug detail must be a scalar record');
  }
  for (const value of Object.values(detail)) {
    if (
      value !== null &&
      typeof value !== 'string' &&
      typeof value !== 'number' &&
      typeof value !== 'boolean'
    ) {
      throw new TypeError('resume debug detail values must be scalar');
    }
  }
}

export function createResumeDebugBuffer(options: BufferOptions): {
  state: ResumeDebugState;
  record: (type: string, detail?: ResumeDebugDetail) => void;
} {
  const events: ResumeDebugEvent[] = [];
  const limit = options.limit ?? DEFAULT_LIMIT;
  const startedAt = options.now();

  const record = (type: string, detail: ResumeDebugDetail = {}) => {
    assertScalarDetail(detail);
    events.push({ at: options.now(), type, detail: { ...detail } });
    if (events.length > limit) events.splice(0, events.length - limit);
  };

  const state: ResumeDebugState = {
    startedAt,
    get events() {
      return events.map(cloneEvent);
    },
    snapshot: () => {
      const worker = options.getWorkerState();
      return {
        now: options.now(),
        visibilityState: options.getVisibilityState(),
        backendMode: options.getBackendMode(),
        worker: {
          exists: worker.exists,
          pending: worker.pending.map((item) => ({ ...item })),
        },
        events: events.map(cloneEvent),
      };
    },
  };

  return { state, record };
}

export function isResumeDebugEnabled(): boolean {
  return (
    typeof location !== 'undefined' &&
    new URLSearchParams(location.search).get('resumeDebug') === '1'
  );
}

export function recordResumeDebug(type: string, detail?: ResumeDebugDetail): void {
  activeRecord?.(type, detail);
}

export function installResumeDebug(options: InstallOptions): void {
  if (
    !isResumeDebugEnabled() ||
    typeof window === 'undefined' ||
    typeof document === 'undefined' ||
    window.__resumeDebug
  ) {
    return;
  }

  const buffer = createResumeDebugBuffer({
    now: () => performance.now(),
    getVisibilityState: () => document.visibilityState,
    getBackendMode: options.getBackendMode,
    getWorkerState: options.getWorkerState,
  });
  activeRecord = buffer.record;
  window.__resumeDebug = buffer.state;

  const lifecycleDetail = (extra: ResumeDebugDetail = {}): ResumeDebugDetail => ({
    ...extra,
    visibility: document.visibilityState,
    backend: options.getBackendMode(),
    pending: options.getWorkerState().pending.length,
  });

  buffer.record('debug-installed', lifecycleDetail());
  document.addEventListener('visibilitychange', () => {
    buffer.record('visibility-change', lifecycleDetail());
  });
  window.addEventListener('pageshow', (event) => {
    buffer.record(
      'pageshow',
      lifecycleDetail({ persisted: (event as PageTransitionEvent).persisted }),
    );
  });
  window.addEventListener('pagehide', (event) => {
    buffer.record(
      'pagehide',
      lifecycleDetail({ persisted: (event as PageTransitionEvent).persisted }),
    );
  });
  window.addEventListener('focus', () => buffer.record('focus', lifecycleDetail()));
  window.addEventListener('blur', () => buffer.record('blur', lifecycleDetail()));

  let lastHeartbeat = performance.now();
  window.setInterval(() => {
    const now = performance.now();
    const gapMs = now - lastHeartbeat;
    lastHeartbeat = now;
    if (gapMs > 2500) {
      buffer.record('heartbeat-gap', lifecycleDetail({ gapMs: Math.round(gapMs) }));
    }
  }, 1000);

  if (
    typeof PerformanceObserver !== 'undefined' &&
    PerformanceObserver.supportedEntryTypes?.includes('longtask')
  ) {
    const observer = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        buffer.record('long-task', {
          startTime: Math.round(entry.startTime),
          durationMs: Math.round(entry.duration),
        });
      }
    });
    observer.observe({ entryTypes: ['longtask'] });
  } else {
    buffer.record('long-task-unsupported');
  }
}
