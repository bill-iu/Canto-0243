import { isPortableHost } from '../host-mode.ts';
import type { ReplacementPlanV1, WorkbenchCandidateResponse } from './contracts.ts';
import { createPortableWorkbenchAdapter } from './portable-workbench-adapter.ts';
import { createPwaWorkbenchAdapter } from './pwa-workbench-adapter.ts';
import type { PwaLineReadingSlot } from './pwa-line-readings.ts';

export type WorkbenchAdapterErrorKind = 'not_ready' | 'invalid_plan' | 'network';

export class WorkbenchAdapterError extends Error {
  kind: WorkbenchAdapterErrorKind;

  constructor(kind: WorkbenchAdapterErrorKind, message: string) {
    super(message);
    this.kind = kind;
  }
}

export interface WorkbenchAdapter {
  resolveLine(input: string, signal?: AbortSignal): Promise<PwaLineReadingSlot[]>;
  findCandidates(plan: ReplacementPlanV1, signal?: AbortSignal): Promise<WorkbenchCandidateResponse>;
}

export interface WorkbenchAdapterOptions {
  lexiconIdentity?: string;
  lineReadingCacheSize?: number;
}

export function selectWorkbenchAdapter(
  portable = isPortableHost(),
  options: WorkbenchAdapterOptions = {},
): WorkbenchAdapter {
  return portable
    ? createPortableWorkbenchAdapter(fetch, options)
    : createPwaWorkbenchAdapter(options);
}
