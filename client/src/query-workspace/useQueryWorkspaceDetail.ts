import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { QueryTab } from '@shared/query-tabs';
import type { EntryPickPayload } from '../result-list-logic.ts';
import type { EntryDetailModel } from '../entry-detail/types.ts';
import {
  createProductionQueryWorkspaceDetailAdapter,
  type QueryWorkspaceDetailAdapter,
} from './detail-adapter.ts';

type DetailSnapshot = {
  open: boolean;
  literal: string | null;
  jyutping: string | null;
};

export interface UseQueryWorkspaceDetailOptions {
  activeTab: QueryTab | null;
  isReady: boolean;
  adapter?: QueryWorkspaceDetailAdapter;
  waitForPickMerge?: (signal: AbortSignal) => Promise<void>;
}

export function useQueryWorkspaceDetail({
  activeTab,
  isReady,
  adapter: providedAdapter,
  waitForPickMerge,
}: UseQueryWorkspaceDetailOptions) {
  const adapter = useMemo(
    () => providedAdapter ?? createProductionQueryWorkspaceDetailAdapter(),
    [providedAdapter],
  );
  const [open, setOpen] = useState(false);
  const [model, setModel] = useState<EntryDetailModel | null>(null);
  const [relationsLoading, setRelationsLoading] = useState(false);
  const [literal, setLiteral] = useState<string | null>(null);
  const [preferredJyutping, setPreferredJyutping] = useState<string | null>(null);
  const generationRef = useRef(0);
  const abortRef = useRef<AbortController | null>(null);
  const pendingRef = useRef<{ literal: string; seed: EntryDetailModel | null } | null>(null);
  const lastPickReadingsRef = useRef<EntryPickPayload['readings']>(undefined);
  const detailByTabRef = useRef(new Map<number, DetailSnapshot>());

  const close = useCallback(() => {
    generationRef.current += 1;
    abortRef.current?.abort();
    abortRef.current = null;
    pendingRef.current = null;
    setOpen(false);
    setLiteral(null);
    setModel(null);
    setRelationsLoading(false);
    setPreferredJyutping(null);
  }, []);

  const saveActive = useCallback(() => {
    if (activeTab?.view !== 'search') return;
    detailByTabRef.current.set(activeTab.id, {
      open,
      literal,
      jyutping: preferredJyutping,
    });
  }, [activeTab, literal, open, preferredJyutping]);

  const forgetTab = useCallback((tabId: number) => {
    detailByTabRef.current.delete(tabId);
  }, []);

  const schedule = useCallback(
    (nextLiteral: string, seed: EntryDetailModel | null, generation: number) => {
      const run = () => {
        void (async () => {
          const controller = abortRef.current;
          if (!controller || generation !== generationRef.current || !isReady) return;
          try {
            const full = await adapter.load(nextLiteral, seed, {
              signal: controller.signal,
              waitForPickMerge: waitForPickMerge
                ? () => waitForPickMerge(controller.signal)
                : undefined,
              onStage: (stage) => {
                if (generation !== generationRef.current) return;
                if (stage.kind === 'core') setModel(stage.model);
                else setRelationsLoading(true);
              },
            });
            if (generation !== generationRef.current || controller.signal.aborted) return;
            setModel(full);
            setRelationsLoading(false);
          } catch (error) {
            if (controller.signal.aborted || (error instanceof DOMException && error.name === 'AbortError')) return;
            if (generation === generationRef.current) setRelationsLoading(false);
          }
        })();
      };
      if (!seed) queueMicrotask(run);
      else if (typeof requestIdleCallback !== 'undefined') requestIdleCallback(run, { timeout: 800 });
      else setTimeout(run, 32);
    },
    [adapter, isReady, waitForPickMerge],
  );

  const openLiteral = useCallback(
    (nextLiteral: string, jyutping?: string | null, readings?: EntryPickPayload['readings']) => {
      const text = nextLiteral.trim();
      if (!text) return;
      const generation = ++generationRef.current;
      abortRef.current?.abort();
      abortRef.current = new AbortController();
      lastPickReadingsRef.current = readings;
      const cached = adapter.instantFromPick(text, []);
      const instant = cached ?? adapter.instantFromPick(text, readings);
      pendingRef.current = !cached && !isReady ? { literal: text, seed: instant } : null;
      setOpen(true);
      setLiteral(text);
      setPreferredJyutping(jyutping ?? null);
      setModel(instant);
      setRelationsLoading(false);
      if (cached || !isReady) return;
      schedule(text, instant, generation);
    },
    [adapter, isReady, schedule],
  );

  const openFromPick = useCallback(
    (payload: EntryPickPayload) => openLiteral(payload.literal, payload.jyutping, payload.readings),
    [openLiteral],
  );

  useEffect(() => {
    if (activeTab?.view !== 'search') {
      close();
      return;
    }
    const saved = detailByTabRef.current.get(activeTab.id);
    if (!saved?.open || !saved.literal) {
      close();
      return;
    }
    openLiteral(saved.literal, saved.jyutping);
  }, [activeTab?.id, activeTab?.view, close, openLiteral]);

  useEffect(() => {
    const pending = pendingRef.current;
    if (!isReady || !open || !pending || pending.literal !== literal) return;
    pendingRef.current = null;
    schedule(pending.literal, pending.seed, generationRef.current);
  }, [isReady, literal, open, schedule]);

  return {
    open,
    model,
    relationsLoading,
    literal,
    preferredJyutping,
    close,
    saveActive,
    forgetTab,
    openLiteral,
    openFromPick,
  };
}
