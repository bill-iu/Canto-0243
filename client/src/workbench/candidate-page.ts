import type { WorkbenchCandidateResponse } from './contracts.ts';

const SNAPSHOT_RESTARTED = Symbol('workbench.snapshot-restarted');

export type CandidatePageResponse = WorkbenchCandidateResponse & {
  [SNAPSHOT_RESTARTED]?: true;
};

export function markSnapshotRestarted(
  response: WorkbenchCandidateResponse,
): CandidatePageResponse {
  return Object.assign(response, { [SNAPSHOT_RESTARTED]: true as const });
}

export function snapshotWasRestarted(response: CandidatePageResponse): boolean {
  return response[SNAPSHOT_RESTARTED] === true;
}
