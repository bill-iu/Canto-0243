import { type FormEvent, useMemo, useRef, useState, useEffect } from 'react';

import { getLang, setLang, getTheme, setTheme, readLexiconVersionMeta } from '../../../shared/app-context.mjs';
import { searchPageHref } from '../app-page.ts';
import { navigateAppRoute } from '../app-navigation.ts';
import { BrandLogo } from '../brand-logo.tsx';
import { BrandSvgDefs } from '../brand-svg-defs.tsx';
import { getActiveDbBackendMode } from '../db/init.ts';
import { HeaderHero } from '../header-hero.tsx';
import { useDB } from '../hooks/useDB.ts';
import { isPortableHost } from '../host-mode.ts';
import { ModeMenu } from '../mode-menu.tsx';
import { exitPortable } from '../portable-exit.ts';
import { workbenchIntroCopy } from './intro-copy.ts';
import { WORKBENCH_LINE_INPUT_COPY } from './line-input-copy.ts';
import { PosFilterControl } from '../pos/PosFilterControl.tsx';
import { isPosFilterActive, resetPosFilter, type PosFilterState } from '../pos/filter.ts';
import { revealPwaShell } from '../pwa-shell-boot.ts';
import { CandidateGrid } from './CandidateGrid.tsx';
import { ComparePanel } from './ComparePanel.tsx';
import { ConstraintBar } from './ConstraintBar.tsx';
import {
  buildCodeDigitSlots,
  codeConstraintAfterRemoveCode,
  planHasQueryableSlots,
  sameToneCodePattern,
  sanitizeExplicitCode,
  type CodeConstraintMode,
} from './code-constraint.ts';
import {
  WORKBENCH_CANDIDATE_PAGE_SIZE,
  type CandidateGroups,
  type RelaxationKind,
  type ReplacementPlanV1,
  type WorkbenchCandidate,
  type WorkbenchSlotConstraintV1,
} from './contracts.ts';
import { createLineDraft, lineDraftReducer, type LineDraft } from './line-draft.ts';
import { clearLineDraft, loadLineDraft, saveLineDraft } from './line-draft-storage.ts';
import { parseLineInput } from './line-input.ts';
import { parsePhonemeRef, parseSpanManual } from './manual-slot-input.ts';
import type { PwaLineReadingSlot } from './pwa-line-readings.ts';
import { relaxationKindLabel } from './relaxation-i18n.ts';
import {
  buildPhonemeAnchors,
  emptyPhonemeDimPicks,
  phonemeCheckedOffsets,
  replacementSpanFromLocks,
  sanitizePhonemeDimPicks,
  toggleLockKeepingSpan,
  withPhonemeAnchors,
  type PhonemeDimPicks,
} from './replacement-span.ts';
import { SentenceCanvas } from './SentenceCanvas.tsx';
import { isHanSurface, normalizeWildcardChar } from './wildcard-slot.ts';
import { selectWorkbenchAdapter } from './workbench-adapter.ts';
import { useWorkbenchCandidates } from './useWorkbenchCandidates.ts';
import {
  WorkbenchBridgeError,
  consumeIngest,
  writeNavigate,
  writeOpenSearch,
  type SearchModeFamily,
} from './workbench-bridge.ts';
import './workbench-page.css';

function hydrateDraftCodes(draft: LineDraft): LineDraft {
  let changed = false;
  const slots = draft.slots.map((slot, pos) => {
    if (slot.code) return slot;
    const digit = draft.constraints.find((item) => item.kind === 'code_digit' && item.pos === pos)?.digit;
    if (!digit) return slot;
    changed = true;
    return { ...slot, code: digit };
  });
  if (!changed) return { ...draft, selection: draft.selection ?? replacementSpanFromLocks(draft.slots) };
  return { ...draft, slots, selection: replacementSpanFromLocks(slots) };
}

function initialDraft(): LineDraft | null {
  try {
    const draft = loadLineDraft(localStorage);
    if (!draft) return null;
    return hydrateDraftCodes(draft);
  } catch {
    return null;
  }
}

interface ActiveRelaxation {
  id: string;
  kind: RelaxationKind;
  from?: string;
  to?: string;
}

interface ClearedWorkbenchUndo {
  draft: LineDraft;
  readings: PwaLineReadingSlot[];
  mode: ReplacementPlanV1['mode'];
  semanticIntent: ReplacementPlanV1['semanticIntent'];
  codeConstraint: CodeConstraintMode;
  explicitCode: string;
  rhymePicks: PhonemeDimPicks;
  initialPicks: PhonemeDimPicks;
  rhymeRef: string;
  initialRef: string;
}

const GROUP_FOCUS_IDS = ['candidate-direct_syn', 'candidate-semantic_related', 'candidate-sound_only'] as const;

function firstCandidate(groups: CandidateGroups | undefined): WorkbenchCandidate | null {
  if (!groups) return null;
  return groups.direct_syn[0] ?? groups.semantic_related[0] ?? groups.sound_only[0] ?? null;
}

function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || target.isContentEditable;
}

export function WorkbenchPage() {
  const adapter = useMemo(() => selectWorkbenchAdapter(), []);
  const { isReady, initialize } = useDB();
  const lexiconVersion =
    (isPortableHost() ? readLexiconVersionMeta() : null) ||
    (import.meta as any).env?.VITE_LEXICON_VERSION ||
    'dev';
  const [input, setInput] = useState('');
  const [draft, setDraft] = useState<LineDraft | null>(initialDraft);
  const [readings, setReadings] = useState<PwaLineReadingSlot[]>([]);
  const [mode, setMode] = useState<ReplacementPlanV1['mode']>('m1');
  const [semanticIntent, setSemanticIntent] = useState<ReplacementPlanV1['semanticIntent']>('ranked');
  const [codeConstraint, setCodeConstraint] = useState<CodeConstraintMode>('same_tone');
  const [explicitCode, setExplicitCode] = useState('');
  const [message, setMessage] = useState('');
  const [preview, setPreview] = useState<WorkbenchCandidate | null>(null);
  const [relaxedPrevious, setRelaxedPrevious] = useState<{
    mode: ReplacementPlanV1['mode'];
    semanticIntent: ReplacementPlanV1['semanticIntent'];
    codeConstraint: CodeConstraintMode;
    explicitCode: string;
  } | null>(null);
  const [activeRelaxation, setActiveRelaxation] = useState<ActiveRelaxation | null>(null);
  const [rhymePicks, setRhymePicks] = useState<PhonemeDimPicks>(emptyPhonemeDimPicks);
  const [initialPicks, setInitialPicks] = useState<PhonemeDimPicks>(emptyPhonemeDimPicks);
  const [rhymeRef, setRhymeRef] = useState('');
  const [initialRef, setInitialRef] = useState('');
  const [refReadings, setRefReadings] = useState<Map<string, string>>(() => new Map());
  const [posFilter, setPosFilter] = useState<PosFilterState>(resetPosFilter);
  const [candidateOffset, setCandidateOffset] = useState(0);
  const [spanInputError, setSpanInputError] = useState('');
  const [clearedUndo, setClearedUndo] = useState<ClearedWorkbenchUndo | null>(null);
  const [uiLang, setUiLang] = useState<'zh' | 'en'>(() => getLang() as 'zh' | 'en');
  const [uiTheme, setUiTheme] = useState<'light' | 'dark'>(() => {
    const theme = getTheme();
    return theme === 'light' || theme === 'dark' ? theme : 'dark';
  });
  const previewOrigin = useRef<HTMLButtonElement | null>(null);
  const draftRef = useRef(draft);
  const previewRef = useRef(preview);
  const relaxedPreviousRef = useRef(relaxedPrevious);
  const clearedUndoRef = useRef(clearedUndo);
  const ingestDone = useRef(false);
  const pendingResolve = useRef<{ surface: string; version: number } | null>(null);
  draftRef.current = draft;
  previewRef.current = preview;
  relaxedPreviousRef.current = relaxedPrevious;
  clearedUndoRef.current = clearedUndo;

  useEffect(() => {
    revealPwaShell();
    document.body.classList.add('workbench-route');
    return () => document.body.classList.remove('workbench-route');
  }, []);

  useEffect(() => {
    void initialize();
  }, [initialize]);

  useEffect(() => {
    setTheme(uiTheme);
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', uiTheme === 'dark' ? '#1C1917' : '#DFD2C2');
  }, [uiTheme]);

  useEffect(() => {
    setLang(uiLang);
    document.documentElement.lang = uiLang === 'zh' ? 'zh-Hant' : 'en';
  }, [uiLang]);

  useEffect(() => {
    if (!draft) {
      try { clearLineDraft(localStorage); } catch { /* ignore */ }
      return;
    }
    try { saveLineDraft(localStorage, draft); } catch { setMessage('這次未能自動保存；句稿仍可繼續編輯。'); }
  }, [draft]);

  const goSearchHome = () => {
    navigateAppRoute('search');
  };

  const goSearchWithNavigate = (input: { kind: 'mode'; family: SearchModeFamily } | { kind: 'guide' } | { kind: 'about' }) => {
    try {
      writeNavigate(sessionStorage, input);
    } catch (error) {
      if (!(error instanceof WorkbenchBridgeError)) throw error;
      setMessage('暫時無法回到查韻；請再試一次。');
      return;
    }
    navigateAppRoute('search');
  };

  const changeMode = (next: ReplacementPlanV1['mode']) => {
    setMode(next);
    setActiveRelaxation(null);
  };
  const changeSemantic = (next: ReplacementPlanV1['semanticIntent']) => {
    setSemanticIntent(next);
    setActiveRelaxation(null);
  };
  const changeCodeConstraint = (next: CodeConstraintMode) => {
    if (next === 'explicit') {
      const span = draftRef.current?.selection;
      const slots = draftRef.current?.slots;
      if (span && slots) {
        setExplicitCode(sameToneCodePattern(slots, span));
      }
    }
    setCodeConstraint(next);
    setActiveRelaxation(null);
  };
  const changeExplicitCode = (raw: string) => {
    const width = draftRef.current?.selection?.width ?? 0;
    setExplicitCode(width > 0 ? sanitizeExplicitCode(raw, width) : raw.replace(/[^\d?]/g, ''));
    setActiveRelaxation(null);
  };

  const syncPhonemeAnchors = (
    base: LineDraft,
    rhyme: PhonemeDimPicks,
    initial: PhonemeDimPicks,
    rhymeRaw = rhymeRef,
    initialRaw = initialRef,
    readings: ReadonlyMap<string, string> = refReadings,
  ): LineDraft => {
    const span = base.selection ?? replacementSpanFromLocks(base.slots);
    if (!span) {
      return withPhonemeAnchors(base, []);
    }
    const safeRhyme = sanitizePhonemeDimPicks(rhyme, span.width);
    const safeInitial = sanitizePhonemeDimPicks(initial, span.width);
    const rhymeParsed = parsePhonemeRef(rhymeRaw, phonemeCheckedOffsets(safeRhyme, span.width).length);
    const initialParsed = parsePhonemeRef(initialRaw, phonemeCheckedOffsets(safeInitial, span.width).length);
    return withPhonemeAnchors(
      base,
      buildPhonemeAnchors(
        span,
        base.slots,
        safeRhyme,
        safeInitial,
        rhymeParsed.ok ? rhymeParsed.chars : null,
        initialParsed.ok ? initialParsed.chars : null,
        readings,
      ),
    );
  };

  const handleToggleLock = (pos: number) => {
    const current = draftRef.current;
    if (!current) return;
    const result = toggleLockKeepingSpan(current, pos);
    if (!result.ok) {
      setMessage(
        result.reason === 'span_too_wide'
          ? '一次最多改連續四格；請先取消較遠的鎖定。'
          : '空白格不能鎖定；請先有字面、通配或碼。',
      );
      return;
    }
    setMessage('');
    setSpanInputError('');
    const width = result.draft.selection?.width ?? 0;
    const nextRhyme = sanitizePhonemeDimPicks(rhymePicks, width);
    const nextInitial = sanitizePhonemeDimPicks(initialPicks, width);
    setRhymePicks(nextRhyme);
    setInitialPicks(nextInitial);
    if (codeConstraint === 'explicit' && result.draft.selection) {
      setExplicitCode((prev) => {
        const pref = sameToneCodePattern(result.draft.slots, result.draft.selection!);
        return prev.length === width ? sanitizeExplicitCode(prev, width) : pref;
      });
    }
    setDraft(syncPhonemeAnchors(result.draft, nextRhyme, nextInitial));
  };

  const changeRhymePicks = (next: PhonemeDimPicks) => {
    setRhymePicks(next);
    const current = draftRef.current;
    if (current) setDraft(syncPhonemeAnchors(current, next, initialPicks));
    setActiveRelaxation(null);
  };

  const changeInitialPicks = (next: PhonemeDimPicks) => {
    setInitialPicks(next);
    const current = draftRef.current;
    if (current) setDraft(syncPhonemeAnchors(current, rhymePicks, next));
    setActiveRelaxation(null);
  };

  const changeRhymeRef = (value: string) => {
    setRhymeRef(value);
    const current = draftRef.current;
    if (current) setDraft(syncPhonemeAnchors(current, rhymePicks, initialPicks, value, initialRef));
    setActiveRelaxation(null);
  };

  const changeInitialRef = (value: string) => {
    setInitialRef(value);
    const current = draftRef.current;
    if (current) setDraft(syncPhonemeAnchors(current, rhymePicks, initialPicks, rhymeRef, value));
    setActiveRelaxation(null);
  };

  useEffect(() => {
    const needed: string[] = [];
    const seen = new Set<string>();
    for (const raw of [rhymeRef, initialRef]) {
      for (const ch of Array.from(raw.trim())) {
        const normalized = normalizeWildcardChar(ch);
        if (!isHanSurface(normalized) || seen.has(normalized) || refReadings.has(normalized)) continue;
        seen.add(normalized);
        needed.push(normalized);
      }
    }
    if (!needed.length || !isReady) return;
    let cancelled = false;
    void (async () => {
      try {
        const resolved = await adapter.resolveLine(needed.join(''));
        if (cancelled) return;
        const nextReadings = new Map(refReadings);
        needed.forEach((ch, index) => {
          const jyutping = resolved[index]?.choices[0]?.jyutping;
          if (jyutping) nextReadings.set(ch, jyutping);
        });
        setRefReadings(nextReadings);
        const current = draftRef.current;
        if (current) {
          setDraft(syncPhonemeAnchors(
            current,
            rhymePicks,
            initialPicks,
            rhymeRef,
            initialRef,
            nextReadings,
          ));
        }
      } catch {
        // ponytail: keep surface fallbacks until lexicon answers
      }
    })();
    return () => { cancelled = true; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rhymeRef, initialRef, isReady]);

  const surfaceOnlyOf = (next: LineDraft) => next.slots
    .map((slot) => slot.surface)
    .filter((surface) => isHanSurface(surface))
    .join('');

  const resolveReadings = async (surface: string, baseDraft: LineDraft) => {
    if (!surface) return;
    pendingResolve.current = { surface, version: baseDraft.version };
    try {
      if (!isReady) await initialize();
      const resolved = await adapter.resolveLine(surface);
      if (pendingResolve.current?.version !== baseDraft.version) return;
      pendingResolve.current = null;
      // 混合起句：resolve 只覆蓋有字面格；碼格留空位對齊 draft.slots
      let cursor = 0;
      const aligned: PwaLineReadingSlot[] = baseDraft.slots.map((slot) => {
        if (!isHanSurface(slot.surface)) {
          return { surface: slot.surface || '', kind: 'punctuation', choices: [], needsChoice: false };
        }
        const reading = resolved[cursor] ?? {
          surface: slot.surface,
          kind: 'unresolved' as const,
          choices: [],
          needsChoice: false,
        };
        cursor += 1;
        return reading;
      });
      setReadings(aligned);
      setDraft((current) => {
        if (!current) return current;
        // 手改後 syncPhonemeAnchors 會再 bump version；以漢字面是否仍吻合為準
        if (surfaceOnlyOf(current) !== surface) return current;
        let next = current;
        let readingIdx = 0;
        for (let pos = 0; pos < current.slots.length; pos += 1) {
          if (!isHanSurface(current.slots[pos]?.surface)) continue;
          const choice = resolved[readingIdx]?.choices[0];
          readingIdx += 1;
          if (!choice) continue;
          next = lineDraftReducer(next, {
            type: 'choose_reading',
            pos,
            jyutping: choice.jyutping,
            code: choice.code,
          });
        }
        return syncPhonemeAnchors(next, rhymePicks, initialPicks);
      });
      setMessage(resolved.some((slot) => slot.kind === 'unresolved') ? '部分字未有收錄讀音；你仍可鎖定字位或改用碼起句。' : '已解析逐字讀音；請點擊鎖定替換段。');
    } catch {
      setMessage('詞庫暫未就緒；句稿已建立，可繼續編輯並稍後重試。');
    }
  };

  useEffect(() => {
    if (!isReady || !pendingResolve.current || !draftRef.current) return;
    const pending = pendingResolve.current;
    if (draftRef.current.version !== pending.version) return;
    void resolveReadings(pending.surface, draftRef.current);
  // ponytail: retry once lexicon becomes ready
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isReady]);

  useEffect(() => {
    const current = draftRef.current;
    if (!isReady || !current?.surface || readings.length > 0) return;
    void resolveReadings(current.surface, current);
  // ponytail: hydrate readings for restored surface drafts
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isReady]);

  useEffect(() => {
    if (ingestDone.current) return;
    ingestDone.current = true;
    const payload = consumeIngest(sessionStorage);
    if (!payload) return;

    if (payload.mode === 'insert') {
      setDraft((current) => {
        if (!current?.selection) {
          setMessage('無法插入：工作台沒有已鎖範圍；請改用取代整句。');
          return current;
        }
        const next = lineDraftReducer(current, { type: 'insert_literal', literal: payload.literal });
        if (next === current) {
          setMessage('無法插入：字數與選段不符。');
          return current;
        }
        setPreview(null);
        setActiveRelaxation(null);
        void resolveReadings(next.surface, next);
        setMessage('已插入字面到選段；請確認讀音。');
        return next;
      });
      return;
    }

    const parsed = parseLineInput(payload.literal);
    if (!parsed.ok || parsed.kind !== 'surface') {
      setMessage('放入的字面無法建立句格。');
      return;
    }
    setDraft((current) => {
      const next = current
        ? lineDraftReducer(current, { type: 'replace_surface', literal: payload.literal })
        : createLineDraft(parsed);
      setReadings([]);
      setPreview(null);
      setActiveRelaxation(null);
      setRelaxedPrevious(null);
      void resolveReadings(next.surface, next);
      setMessage('已從搜尋放入字面；請點擊鎖定替換段。');
      return next;
    });
  // ponytail: mount-once ingest; resolveReadings closes over adapter
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const parsed = parseLineInput(input);
    if (!parsed.ok) {
      setMessage(
        parsed.error === 'too_long'
          ? '一句最多 64 格。'
          : '請輸入原句、數字碼、平仄，或漢字與數字混合（如能夠44）；平仄勿同漢字／碼混寫。',
      );
      return;
    }
    const next = createLineDraft(parsed);
    setDraft(next);
    setClearedUndo(null);
    setReadings([]);
    setPreview(null);
    setActiveRelaxation(null);
    setRelaxedPrevious(null);
    setRhymePicks(emptyPhonemeDimPicks());
    setInitialPicks(emptyPhonemeDimPicks());
    setRhymeRef('');
    setInitialRef('');
    setRefReadings(new Map());
    setCodeConstraint('same_tone');
    setExplicitCode('');
    setMessage(
      parsed.kind === 'code'
        ? '已按碼建立空白句格，不會自動填入字面；請點擊碼格鎖定並查看候選。'
        : parsed.kind === 'mixed'
          ? '已建立混合句格；請點擊鎖定一至四格以查看候選。'
          : '句格已建立；請點擊鎖定一至四格以查看候選。',
    );
    if (parsed.kind === 'surface' || parsed.kind === 'mixed') {
      const surfaceOnly = parsed.slots.map((slot) => slot.surface).filter((s) => isHanSurface(s)).join('');
      if (surfaceOnly) void resolveReadings(surfaceOnly, next);
    }
  };

  const handleChooseReading = (pos: number, jyutping: string, code: string) => {
    setDraft((current) => {
      if (!current) return current;
      const next = lineDraftReducer(current, { type: 'choose_reading', pos, jyutping, code });
      return syncPhonemeAnchors(next, rhymePicks, initialPicks);
    });
  };

  const handleSetSlotManual = (pos: number, surface: string, code?: string) => {
    setDraft((current) => {
      if (!current) return current;
      const next = lineDraftReducer(current, { type: 'set_slot_manual', pos, surface, code });
      if (next === current) {
        setMessage('請輸入一個漢字、通配或一位數字碼。');
        return current;
      }
      setSpanInputError('');
      setMessage(surface ? '已手改一字；正在對齊讀音。' : '已手改為碼格。');
      const synced = syncPhonemeAnchors(next, rhymePicks, initialPicks);
      const surfaceOnly = surfaceOnlyOf(synced);
      if (surfaceOnly) void resolveReadings(surfaceOnly, synced);
      return synced;
    });
  };

  const handleClearSurfaces = () => {
    const current = draftRef.current;
    if (!current) return;
    setClearedUndo({
      draft: current,
      readings,
      mode,
      semanticIntent,
      codeConstraint,
      explicitCode,
      rhymePicks,
      initialPicks,
      rhymeRef,
      initialRef,
    });
    setDraft(null);
    setReadings([]);
    setPreview(null);
    setActiveRelaxation(null);
    setRelaxedPrevious(null);
    setSpanInputError('');
    setRhymePicks(emptyPhonemeDimPicks());
    setInitialPicks(emptyPhonemeDimPicks());
    setRhymeRef('');
    setInitialRef('');
    setRefReadings(new Map());
    setExplicitCode('');
    setCodeConstraint('same_tone');
    setMode('m1');
    setSemanticIntent('ranked');
    setMessage('已清空句格。');
  };

  const handleApplySpanInput = (parsed: Extract<ReturnType<typeof parseSpanManual>, { ok: true }>) => {
    setDraft((current) => {
      if (!current?.selection) {
        setSpanInputError('請先鎖定替換段。');
        return current;
      }
      const slots = parsed.slots.map((slot, pos) => {
        const digit = parsed.constraints.find(
          (item) => item.kind === 'code_digit' && item.pos === pos,
        );
        return {
          surface: slot.surface,
          reading: slot.reading,
          code: slot.code || digit?.digit,
        };
      });
      const next = lineDraftReducer(current, {
        type: 'apply_span_input',
        selectionVersion: current.version,
        slots,
        constraints: parsed.constraints,
      });
      if (next === current) {
        setSpanInputError(`長度須為 ${current.selection.width} 格。`);
        return current;
      }
      setSpanInputError('');
      setMessage('已手打替換段。');
      const synced = syncPhonemeAnchors(next, rhymePicks, initialPicks);
      const surfaceOnly = surfaceOnlyOf(synced);
      if (surfaceOnly) void resolveReadings(surfaceOnly, synced);
      return synced;
    });
  };

  const performUndo = () => {
    const stashed = clearedUndoRef.current;
    if (stashed) {
      setDraft(stashed.draft);
      setReadings(stashed.readings);
      setMode(stashed.mode);
      setSemanticIntent(stashed.semanticIntent);
      setCodeConstraint(stashed.codeConstraint);
      setExplicitCode(stashed.explicitCode);
      setRhymePicks(stashed.rhymePicks);
      setInitialPicks(stashed.initialPicks);
      setRhymeRef(stashed.rhymeRef);
      setInitialRef(stashed.initialRef);
      setClearedUndo(null);
      setActiveRelaxation(null);
      setSpanInputError('');
      setMessage('已復原清空前的句稿。');
      return;
    }
    const current = draftRef.current;
    if (!current?.undo) return;
    setDraft(lineDraftReducer(current, { type: 'undo' }));
    const previous = relaxedPreviousRef.current;
    if (previous) {
      setMode(previous.mode);
      setSemanticIntent(previous.semanticIntent);
      setCodeConstraint(previous.codeConstraint);
      setExplicitCode(previous.explicitCode);
      setRelaxedPrevious(null);
    }
    setActiveRelaxation(null);
    setSpanInputError('');
    setMessage('已復原最近一次改動。');
  };

  const planBase = useMemo(() => {
    if (!draft?.selection) return null;
    const { start, width } = draft.selection;
    const span = draft.selection;
    // 音位／平仄約束保留；碼位按碼約束檔重算（同音＝只鎖格）
    const base: WorkbenchSlotConstraintV1[] = draft.constraints
      .filter((item) => item.kind !== 'code_digit' && item.pos >= start && item.pos < start + width)
      .map((item) => ({ ...item, pos: item.pos - start }));
    const codes = buildCodeDigitSlots(codeConstraint, draft.slots, span, explicitCode);
    const slots = [...base, ...codes];
    const semanticSeed = draft.slots
      .slice(start, start + width)
      .map((slot) => slot.surface)
      .filter((surface) => isHanSurface(surface))
      .join('');
    const intent = semanticSeed ? semanticIntent : 'off';
    if (!planHasQueryableSlots(slots, semanticSeed, intent)) return null;
    return {
      version: 1 as const,
      selectionVersion: draft.version,
      width,
      mode,
      slots,
      semanticIntent: intent,
      semanticSeed: semanticSeed || undefined,
    };
  }, [draft, mode, semanticIntent, codeConstraint, explicitCode]);

  const planKey = planBase
    ? `${planBase.selectionVersion}|${planBase.mode}|${planBase.semanticIntent}|${codeConstraint}|${explicitCode}|${JSON.stringify(planBase.slots)}`
    : '';
  const [planKeyHeld, setPlanKeyHeld] = useState(planKey);
  useEffect(() => {
    setPlanKeyHeld(planKey);
    setCandidateOffset(0);
  }, [planKey]);
  const effectiveOffset = planKey === planKeyHeld ? candidateOffset : 0;

  const plan = useMemo<ReplacementPlanV1 | null>(() => {
    if (!planBase) return null;
    return {
      ...planBase,
      limit: WORKBENCH_CANDIDATE_PAGE_SIZE,
      offset: effectiveOffset,
    };
  }, [planBase, effectiveOffset]);

  const candidates = useWorkbenchCandidates(isReady ? plan : null, adapter, posFilter);
  const candidatesRef = useRef(candidates);
  candidatesRef.current = candidates;
  const semanticGap = Boolean(
    plan
    && plan.semanticIntent !== 'off'
    && candidates.response
    && candidates.response.exact.direct_syn.length === 0
    && candidates.response.exact.semantic_related.length === 0,
  );

  const closePreview = () => {
    setPreview(null);
    requestAnimationFrame(() => previewOrigin.current?.focus());
  };

  const applyPreview = (candidate: WorkbenchCandidate) => {
    const current = draftRef.current;
    if (!current?.selection) return;
    setDraft(lineDraftReducer(current, {
      type: 'apply_candidate',
      selectionVersion: candidatesRef.current.response?.selectionVersion ?? -1,
      literal: candidate.literal,
      jyutping: candidate.jyutping,
      code: candidate.code,
      relaxationId: candidate.relaxationId ?? activeRelaxation?.id,
    }));
    setPreview(null);
    setActiveRelaxation(null);
    setTimeout(() => document.querySelector<HTMLButtonElement>(`[data-line-slot="${current.selection!.start}"]`)?.focus(), 0);
  };

  const openInSearch = (literal: string) => {
    try {
      writeOpenSearch(sessionStorage, { literal });
      navigateAppRoute('search');
    } catch (error) {
      setMessage(error instanceof WorkbenchBridgeError ? error.message : '無法打開搜尋頁。');
    }
  };

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (isTypingTarget(event.target)) return;
      const current = draftRef.current;
      const open = previewRef.current;

      if ((event.key === 'a' || event.key === 'A') && open) {
        event.preventDefault();
        applyPreview(open);
        return;
      }
      if (event.key === 'Escape' && open) {
        event.preventDefault();
        closePreview();
        return;
      }
      if (event.key === 'u' || event.key === 'U' || (event.key === 'z' && (event.ctrlKey || event.metaKey))) {
        if (!clearedUndoRef.current && !current?.undo) return;
        event.preventDefault();
        performUndo();
        return;
      }
      if (!current) return;

      if (event.key === '1' || event.key === '2' || event.key === '3') {
        const heading = document.getElementById(GROUP_FOCUS_IDS[Number(event.key) - 1]!);
        if (!heading) return;
        event.preventDefault();
        heading.focus();
        return;
      }
      if (event.key === 'Enter') {
        if (event.target instanceof HTMLElement && event.target.closest('[data-line-slot]')) return;
        const candidate = firstCandidate(candidatesRef.current.response?.exact);
        if (!candidate) return;
        event.preventDefault();
        setPreview(candidate);
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  // ponytail: handlers read refs; applyPreview uses latest activeRelaxation via closure refresh each draft change
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeRelaxation]);

  const intro = workbenchIntroCopy(uiLang);

  return (
    <div className={`workbench-page${preview ? ' has-compare' : ''}`}>
      <BrandSvgDefs />
      <header className="workbench-header">
        <div className="app-bar">
          <div className="header-chrome">
            <div className="header-chrome__center">
              <button
                className="brand"
                type="button"
                aria-label={uiLang === 'zh' ? '返回搜尋首頁' : 'Back to search home'}
                onClick={goSearchHome}
              >
                <BrandLogo variant="header" inkProgress={1} theme={uiTheme} />
              </button>
            </div>
            <div className="header-chrome__actions">
              <ModeMenu
                mode="0243"
                onModeChange={(family) => goSearchWithNavigate({ kind: 'mode', family })}
                onOpenGuide={() => goSearchWithNavigate({ kind: 'guide' })}
                onOpenAbout={() => goSearchWithNavigate({ kind: 'about' })}
                onExitPortable={isPortableHost() ? () => void exitPortable(uiLang) : undefined}
                theme={uiTheme}
                lang={uiLang}
                onThemeChange={setUiTheme}
                onLangChange={setUiLang}
                lexiconVersion={lexiconVersion}
                showOpfsBackend={
                  !isPortableHost() && isReady && getActiveDbBackendMode() === 'opfs-vfs'
                }
              />
            </div>
          </div>
          <HeaderHero lang={uiLang} />
        </div>
      </header>
      <main className="workbench-main">
        <section className="workbench-intro">
          <div className="workbench-intro__titles">
            <p className="eyebrow">{intro.eyebrow}</p>
            <h1>{intro.h1}</h1>
            <h2>{intro.h2}</h2>
          </div>
          <form className="line-input-form" onSubmit={submit}>
            <label className="sr-only" htmlFor="lineInput">
              {WORKBENCH_LINE_INPUT_COPY}
            </label>
            <div>
              <input
                id="lineInput"
                value={input}
                onChange={(event) => setInput(event.target.value)}
                maxLength={65}
                placeholder={WORKBENCH_LINE_INPUT_COPY}
              />
              <button type="submit">建立句格</button>
              {!draft && clearedUndo ? (
                <button
                  type="button"
                  className="canvas-clear-surfaces"
                  title="復原清空前的句稿"
                  aria-label="復原清空前的句稿"
                  onClick={performUndo}
                >
                  復原
                </button>
              ) : null}
            </div>
          </form>
          <p className="workbench-status" aria-live="polite">{message}</p>
        </section>

        {draft ? (
          <>
            <SentenceCanvas
              draft={draft}
              readings={readings}
              onToggleLock={handleToggleLock}
              onChooseReading={handleChooseReading}
              onSetSlotManual={handleSetSlotManual}
              onClearSurfaces={handleClearSurfaces}
              onApplySpanInput={handleApplySpanInput}
              onSpanInputError={setSpanInputError}
              spanInputError={spanInputError}
            />
            <ConstraintBar
              mode={mode}
              semanticIntent={semanticIntent}
              codeConstraint={codeConstraint}
              explicitCode={explicitCode}
              onModeChange={changeMode}
              onSemanticChange={changeSemantic}
              onCodeConstraintChange={changeCodeConstraint}
              onExplicitCodeChange={changeExplicitCode}
              spanWidth={draft.selection?.width ?? 0}
              rhyme={rhymePicks}
              initial={initialPicks}
              onRhymeChange={changeRhymePicks}
              onInitialChange={changeInitialPicks}
              rhymeRef={rhymeRef}
              initialRef={initialRef}
              onRhymeRefChange={changeRhymeRef}
              onInitialRefChange={changeInitialRef}
              rhymeRefError={(() => {
                const n = phonemeCheckedOffsets(rhymePicks, draft.selection?.width ?? 0).length;
                return parsePhonemeRef(rhymeRef, n).ok ? '' : `須為 ${n} 格（漢字或 ?）`;
              })()}
              initialRefError={(() => {
                const n = phonemeCheckedOffsets(initialPicks, draft.selection?.width ?? 0).length;
                return parsePhonemeRef(initialRef, n).ok ? '' : `須為 ${n} 格（漢字或 ?）`;
              })()}
              canUndo={Boolean(draft.undo)}
              onUndo={performUndo}
            />
            <div className="workbench-filter-row">
              <PosFilterControl value={posFilter} onChange={setPosFilter} lang={uiLang} />
              {isPosFilterActive(posFilter) ? <span>{uiLang === 'en' ? 'Filtering candidate cards' : '正篩選候選卡片'}</span> : null}
            </div>
            <div className="candidate-status" aria-live="polite">
              {!draft.selection
                ? '尚未鎖定替換段；候選會在你鎖定後出現。'
                : candidates.loading
                  ? '正在整理候選…'
                  : candidates.error
                    ? '候選暫時不可用；句稿不受影響。'
                    : ''}
            </div>
            {candidates.response ? (
              <CandidateGrid
                groups={candidates.response.exact}
                total={candidates.response.total}
                loadedCount={candidates.loadedCount}
                hasMore={candidates.fetchedCount < candidates.response.total}
                loadingMore={candidates.loading && effectiveOffset > 0}
                posFilterActive={isPosFilterActive(posFilter)}
                relaxed={activeRelaxation}
                semanticGap={semanticGap}
                onPreview={(candidate, origin) => { previewOrigin.current = origin; setPreview(candidate); }}
                onLoadMore={() => setCandidateOffset((n) => n + WORKBENCH_CANDIDATE_PAGE_SIZE)}
              />
            ) : null}
            {candidates.response?.relaxation ? (
              <section className="relaxation-card" aria-labelledby="relaxHeading">
                <div><p className="eyebrow">零結果時只改一項</p><h2 id="relaxHeading">可選放寬：{relaxationKindLabel(candidates.response.relaxation.kind, uiLang)}</h2><p>{isPosFilterActive(posFilter) ? (uiLang === 'en' ? 'Candidate count is hidden while filters are active.' : '啟用篩選時不顯示未篩選候選數。') : `預計可找到 ${candidates.response.relaxation.candidateCount} 項；不會自動採用。`}</p></div>
                <button type="button" onClick={() => {
                  if (!draft.selection || !candidates.response?.relaxation) return;
                  const suggestion = candidates.response.relaxation;
                  setRelaxedPrevious({ mode, semanticIntent, codeConstraint, explicitCode });
                  setActiveRelaxation({
                    id: suggestion.id,
                    kind: suggestion.kind,
                    from: suggestion.from,
                    to: suggestion.to,
                  });
                  setMode(suggestion.plan.mode);
                  setSemanticIntent(suggestion.plan.semanticIntent);
                  if (suggestion.kind === 'remove_code') {
                    const next = codeConstraintAfterRemoveCode(
                      suggestion.plan.slots,
                      suggestion.plan.width,
                    );
                    setCodeConstraint(next.mode);
                    setExplicitCode(next.explicit);
                  }
                  setDraft(lineDraftReducer(draft, {
                    type: 'apply_relaxation',
                    selectionVersion: draft.version,
                    relaxationId: suggestion.id,
                    constraints: suggestion.plan.slots.map((slot) => ({ ...slot, pos: slot.pos + draft.selection!.start })),
                  }));
                }}>確認採用這項放寬</button>
              </section>
            ) : null}
          </>
        ) : <section className="workbench-empty"><p>貼入你正在寫的一句，或先用碼與平仄搭起空白格；有字後點擊即可鎖定替換段。</p></section>}
      </main>
      {preview && draft?.selection ? (
        <ComparePanel
          candidate={preview}
          draft={draft}
          onClose={closePreview}
          onApply={() => applyPreview(preview)}
          onOpenInSearch={() => openInSearch(preview.literal)}
        />
      ) : null}
    </div>
  );
}
