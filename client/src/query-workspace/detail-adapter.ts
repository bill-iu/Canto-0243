import {
  enrichEntryDetailFromDb,
  enrichEntryDetailRelations,
  getCachedEntryDetail,
  hasDirectRelationSources,
  instantEntryDetailModel,
  loadEntryDetailCore,
} from '../entry-detail/load-entry-detail.ts';
import type { EntryPickReading } from '../entry-detail/load-entry-detail.ts';
import type { EntryDetailModel } from '../entry-detail/types.ts';

export type QueryWorkspaceDetailStage =
  | { kind: 'core'; model: EntryDetailModel }
  | { kind: 'relations-start' };

export type QueryWorkspaceDetailLoadOptions = {
  signal?: AbortSignal;
  waitForPickMerge?: () => Promise<void>;
  onStage?: (stage: QueryWorkspaceDetailStage) => void;
};

/**
 * Detail lookup seam used by the query workspace.
 * The caller supplies an optional zero-latency seed; the adapter owns cache,
 * database and relation-pool orchestration behind one cancellable load.
 */
export interface QueryWorkspaceDetailAdapter {
  instantFromPick(literal: string, readings?: EntryPickReading[]): EntryDetailModel | null;
  load(
    literal: string,
    seed?: EntryDetailModel | null,
    options?: QueryWorkspaceDetailLoadOptions,
  ): Promise<EntryDetailModel | null>;
}

function throwIfAborted(signal?: AbortSignal): void {
  if (signal?.aborted) throw new DOMException('Aborted', 'AbortError');
}

export function createProductionQueryWorkspaceDetailAdapter(): QueryWorkspaceDetailAdapter {
  return {
    instantFromPick(literal, readings) {
      const cached = getCachedEntryDetail(literal);
      if (cached) return cached;
      return readings?.length ? instantEntryDetailModel(literal, readings) : null;
    },

    async load(literal, seed, options = {}) {
      const { signal, waitForPickMerge, onStage } = options;
      throwIfAborted(signal);
      await waitForPickMerge?.();
      throwIfAborted(signal);

      const core = seed ?? (await loadEntryDetailCore(literal));
      throwIfAborted(signal);
      if (!core) return null;

      const hasRelations = await hasDirectRelationSources(core.literal);
      throwIfAborted(signal);
      const fromDb = await enrichEntryDetailFromDb(core);
      throwIfAborted(signal);
      onStage?.({ kind: 'core', model: fromDb });
      if (!hasRelations) return fromDb;

      onStage?.({ kind: 'relations-start' });
      const full = await enrichEntryDetailRelations(fromDb);
      throwIfAborted(signal);
      return full;
    },
  };
}

/** Small deterministic adapter for seam self-checks. */
export function createMemoryQueryWorkspaceDetailAdapter(options: {
  instant?: (literal: string, readings?: EntryPickReading[]) => EntryDetailModel | null;
  core?: (literal: string) => Promise<EntryDetailModel | null>;
  hasRelations?: (literal: string) => Promise<boolean>;
  enrichDb?: (model: EntryDetailModel) => Promise<EntryDetailModel>;
  enrichRelations?: (model: EntryDetailModel) => Promise<EntryDetailModel>;
} = {}): QueryWorkspaceDetailAdapter {
  return {
    instantFromPick: options.instant ?? (() => null),
    async load(literal, seed, loadOptions = {}) {
      const { signal, waitForPickMerge, onStage } = loadOptions;
      throwIfAborted(signal);
      await waitForPickMerge?.();
      throwIfAborted(signal);
      const core = seed ?? (await options.core?.(literal) ?? null);
      throwIfAborted(signal);
      if (!core) return null;
      const hasRelations = await options.hasRelations?.(core.literal) ?? false;
      throwIfAborted(signal);
      const fromDb = await options.enrichDb?.(core) ?? core;
      throwIfAborted(signal);
      onStage?.({ kind: 'core', model: fromDb });
      if (!hasRelations) return fromDb;
      onStage?.({ kind: 'relations-start' });
      const full = await options.enrichRelations?.(fromDb) ?? fromDb;
      throwIfAborted(signal);
      return full;
    },
  };
}
