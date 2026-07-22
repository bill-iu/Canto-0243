import type { PosFilterState } from '../../pos/filter.ts';
import type {
  ReplacementPlanV1,
  WorkbenchCandidateResponse,
} from '../contracts.ts';

/** Plan 身份（無 paging）— candidate session 用嚟 reset／組 adapter 請求。 */
export type CandidatePlanBase = Omit<ReplacementPlanV1, 'offset' | 'limit'>;

export interface CandidateSessionState {
  planBase: CandidatePlanBase | null;
  posFilter: PosFilterState;
  pageSize: number;
  /** 下一 stat 引擎 offset（已累積 raw 之後）。 */
  engineCursor: number;
  engineTotal: number;
  /** 篩後目標張數（首屏 = pageSize；每次 loadMore +pageSize）。 */
  filteredTarget: number;
  /** 未套 POS 嘅累積回應（exact 為引擎列）。 */
  raw: WorkbenchCandidateResponse | null;
  loading: boolean;
  error: Error | null;
  /** 單調 generation；async 完成時核對。 */
  generation: number;
}

export interface CandidateSessionView {
  /** 展示用：exact 已套 POS；engineTotal 雙寫 total。 */
  response: WorkbenchCandidateResponse | null;
  engineTotal: number;
  engineFetched: number;
  filteredCount: number;
  hasMore: boolean;
  loading: boolean;
  error: Error | null;
}

export type FindCandidates = (
  plan: ReplacementPlanV1,
  signal?: AbortSignal,
) => Promise<WorkbenchCandidateResponse>;
