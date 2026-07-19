import { type FormEvent, useMemo, useRef, useState, useEffect } from 'react';

import { getLang, setLang, getTheme, setTheme } from '../../../shared/app-context.mjs';
import { searchPageHref } from '../app-page.ts';
import { BrandLogo } from '../brand-logo.tsx';
import { BrandSvgDefs } from '../brand-svg-defs.tsx';
import { HeaderHero } from '../header-hero.tsx';
import { useDB } from '../hooks/useDB.ts';
import { isPortableHost } from '../host-mode.ts';
import { ModeMenu } from '../mode-menu.tsx';
import { exitPortable } from '../portable-exit.ts';
import { PosFilterControl } from '../pos/PosFilterControl.tsx';
import { isPosFilterActive, resetPosFilter, type PosFilterState } from '../pos/filter.ts';
import { revealPwaShell } from '../pwa-shell-boot.ts';
import { CandidateGrid } from './CandidateGrid.tsx';
import { ComparePanel } from './ComparePanel.tsx';
import { ConstraintBar } from './ConstraintBar.tsx';
import type { CandidateGroups, RelaxationKind, ReplacementPlanV1, WorkbenchCandidate, WorkbenchSlotConstraintV1 } from './contracts.ts';
import { createLineDraft, lineDraftReducer, type LineDraft } from './line-draft.ts';
import { loadLineDraft, saveLineDraft } from './line-draft-storage.ts';
import { parseLineInput } from './line-input.ts';
import type { PwaLineReadingSlot } from './pwa-line-readings.ts';
import {
  buildPhonemeAnchors,
  emptyPhonemeDimPicks,
  replacementSpanFromLocks,
  sanitizePhonemeDimPicks,
  toggleLockKeepingSpan,
  withPhonemeAnchors,
  type PhonemeDimPicks,
} from './replacement-span.ts';
import { SentenceCanvas } from './SentenceCanvas.tsx';
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
  const [input, setInput] = useState('');
  const [draft, setDraft] = useState<LineDraft | null>(initialDraft);
  const [readings, setReadings] = useState<PwaLineReadingSlot[]>([]);
  const [mode, setMode] = useState<ReplacementPlanV1['mode']>('m1');
  const [semanticIntent, setSemanticIntent] = useState<ReplacementPlanV1['semanticIntent']>('ranked');
  const [message, setMessage] = useState('');
  const [preview, setPreview] = useState<WorkbenchCandidate | null>(null);
  const [relaxedPrevious, setRelaxedPrevious] = useState<{ mode: ReplacementPlanV1['mode']; semanticIntent: ReplacementPlanV1['semanticIntent'] } | null>(null);
  const [activeRelaxation, setActiveRelaxation] = useState<ActiveRelaxation | null>(null);
  const [rhymePicks, setRhymePicks] = useState<PhonemeDimPicks>(emptyPhonemeDimPicks);
  const [initialPicks, setInitialPicks] = useState<PhonemeDimPicks>(emptyPhonemeDimPicks);
  const [posFilter, setPosFilter] = useState<PosFilterState>(resetPosFilter);
  const [uiLang, setUiLang] = useState<'zh' | 'en'>(() => getLang() as 'zh' | 'en');
  const [uiTheme, setUiTheme] = useState<'light' | 'dark'>(() => {
    const theme = getTheme();
    return theme === 'light' || theme === 'dark' ? theme : 'dark';
  });
  const previewOrigin = useRef<HTMLButtonElement | null>(null);
  const draftRef = useRef(draft);
  const previewRef = useRef(preview);
  const ingestDone = useRef(false);
  const pendingResolve = useRef<{ surface: string; version: number } | null>(null);
  draftRef.current = draft;
  previewRef.current = preview;

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
    if (!draft) return;
    try { saveLineDraft(localStorage, draft); } catch { setMessage('這次未能自動保存；句稿仍可繼續編輯。'); }
  }, [draft]);

  const goSearchHome = () => {
    window.location.href = searchPageHref();
  };

  const goSearchWithNavigate = (input: { kind: 'mode'; family: SearchModeFamily } | { kind: 'guide' } | { kind: 'about' }) => {
    try {
      writeNavigate(sessionStorage, input);
    } catch (error) {
      if (!(error instanceof WorkbenchBridgeError)) throw error;
      setMessage('暫時無法回到查韻；請再試一次。');
      return;
    }
    window.location.href = searchPageHref();
  };

  const changeMode = (next: ReplacementPlanV1['mode']) => {
    setMode(next);
    setActiveRelaxation(null);
  };
  const changeSemantic = (next: ReplacementPlanV1['semanticIntent']) => {
    setSemanticIntent(next);
    setActiveRelaxation(null);
  };

  const syncPhonemeAnchors = (
    base: LineDraft,
    rhyme: PhonemeDimPicks,
    initial: PhonemeDimPicks,
  ): LineDraft => {
    const span = base.selection ?? replacementSpanFromLocks(base.slots);
    if (!span) {
      return withPhonemeAnchors(base, []);
    }
    const safeRhyme = sanitizePhonemeDimPicks(rhyme, span.width);
    const safeInitial = sanitizePhonemeDimPicks(initial, span.width);
    return withPhonemeAnchors(
      base,
      buildPhonemeAnchors(span, base.slots, safeRhyme, safeInitial),
    );
  };

  const handleToggleLock = (pos: number) => {
    const current = draftRef.current;
    if (!current) return;
    const result = toggleLockKeepingSpan(current, pos);
    if (!result.ok) {
      setMessage(
        result.reason === 'span_too_wide'
          ? '一次最多改連續四格；請先取消較遠的標定。'
          : '空白格不能標定；請先有字面。',
      );
      return;
    }
    setMessage('');
    const width = result.draft.selection?.width ?? 0;
    const nextRhyme = sanitizePhonemeDimPicks(rhymePicks, width);
    const nextInitial = sanitizePhonemeDimPicks(initialPicks, width);
    setRhymePicks(nextRhyme);
    setInitialPicks(nextInitial);
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

  const resolveReadings = async (surface: string, baseDraft: LineDraft) => {
    if (!surface) return;
    pendingResolve.current = { surface, version: baseDraft.version };
    try {
      if (!isReady) await initialize();
      const resolved = await adapter.resolveLine(surface);
      if (pendingResolve.current?.version !== baseDraft.version) return;
      pendingResolve.current = null;
      setReadings(resolved);
      setDraft((current) => {
        if (!current || current.version !== baseDraft.version) return current;
        return resolved.reduce((next, slot, pos) => {
          const choice = slot.choices[0];
          return choice
            ? lineDraftReducer(next, { type: 'choose_reading', pos, jyutping: choice.jyutping, code: choice.code })
            : next;
        }, current);
      });
      setMessage(resolved.some((slot) => slot.kind === 'unresolved') ? '部分字未有收錄讀音；你仍可標定字位或改用碼起句。' : '已解析逐字讀音；請點擊標定替換段。');
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
      setMessage('已從搜尋放入字面；請點擊標定替換段。');
      return next;
    });
  // ponytail: mount-once ingest; resolveReadings closes over adapter
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const parsed = parseLineInput(input);
    if (!parsed.ok) {
      setMessage(parsed.error === 'too_long' ? '一句最多 64 格。' : '請輸入原句、純數字碼，或純平仄串列。');
      return;
    }
    const next = createLineDraft(parsed);
    setDraft(next);
    setReadings([]);
    setPreview(null);
    setActiveRelaxation(null);
    setRelaxedPrevious(null);
    setRhymePicks(emptyPhonemeDimPicks());
    setInitialPicks(emptyPhonemeDimPicks());
    setMessage(
      parsed.kind === 'code'
        ? '已按碼建立空白句格，不會自動填入字面；請點擊有字位以標定並查看候選。'
        : '句格已建立；請點擊標定一至四格以查看候選。',
    );
    if (parsed.kind === 'surface') void resolveReadings(parsed.slots.map((slot) => slot.surface).join(''), next);
  };

  const plan = useMemo<ReplacementPlanV1 | null>(() => {
    if (!draft?.selection) return null;
    const { start, width } = draft.selection;
    const slots: WorkbenchSlotConstraintV1[] = draft.constraints
      .filter((item) => item.pos >= start && item.pos < start + width)
      .map((item) => ({ ...item, pos: item.pos - start }));
    for (let offset = 0; offset < width; offset += 1) {
      const slot = draft.slots[start + offset]!;
      // ponytail: lock only defines 替換段; never emit literal_char (parity with 29稻草=).
      if (slot.code && !slots.some((item) => item.pos === offset && item.kind === 'code_digit')) {
        slots.push({ pos: offset, kind: 'code_digit', digit: slot.code });
      }
    }
    if (slots.length === 0) return null;
    const semanticSeed = draft.slots.slice(start, start + width).map((slot) => slot.surface).join('');
    return {
      version: 1,
      selectionVersion: draft.version,
      width,
      mode,
      slots,
      semanticIntent: semanticSeed ? semanticIntent : 'off',
      semanticSeed: semanticSeed || undefined,
      limit: 120,
    };
  }, [draft, mode, semanticIntent]);
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
      window.location.href = searchPageHref();
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
      if (!current) return;

      if (event.key === 'u' || event.key === 'U' || (event.key === 'z' && (event.ctrlKey || event.metaKey))) {
        if (!current.undo) return;
        event.preventDefault();
        setDraft(lineDraftReducer(current, { type: 'undo' }));
        setActiveRelaxation(null);
        return;
      }
      if (event.key === '1' || event.key === '2' || event.key === '3') {
        const heading = document.getElementById(GROUP_FOCUS_IDS[Number(event.key) - 1]!);
        if (!heading) return;
        event.preventDefault();
        heading.focus();
        return;
      }
      if (event.key === 'Enter') {
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
              />
            </div>
          </div>
          <HeaderHero lang={uiLang} />
        </div>
      </header>
      <main className="workbench-main">
        <section className="workbench-intro">
          <div>
            <p className="eyebrow">創作主導權在你手上</p>
            <h1>句格工作台</h1>
            <h2>把一句拆開，看清每個選擇</h2>
            <p>工具會整理聲調、押韻與原意取捨；不會替你自動填詞。</p>
          </div>
          <form className="line-input-form" onSubmit={submit}>
            <label htmlFor="lineInput">原句、394052／0243 碼或平仄</label>
            <div><input id="lineInput" value={input} onChange={(event) => setInput(event.target.value)} maxLength={65} placeholder="例如：香港／39／平仄" /><button type="submit">建立句格</button></div>
          </form>
          <p className="workbench-status" aria-live="polite">{message}</p>
        </section>

        {draft ? (
          <>
            <SentenceCanvas
              draft={draft}
              readings={readings}
              onToggleLock={handleToggleLock}
              onChooseReading={(pos, jyutping, code) => setDraft((current) => current ? lineDraftReducer(current, { type: 'choose_reading', pos, jyutping, code }) : current)}
            />
            <ConstraintBar
              mode={mode}
              semanticIntent={semanticIntent}
              onModeChange={changeMode}
              onSemanticChange={changeSemantic}
              spanWidth={draft.selection?.width ?? 0}
              rhyme={rhymePicks}
              initial={initialPicks}
              onRhymeChange={changeRhymePicks}
              onInitialChange={changeInitialPicks}
            />
            <div className="workbench-filter-row">
              <PosFilterControl value={posFilter} onChange={setPosFilter} lang={uiLang} />
              {isPosFilterActive(posFilter) ? <span>{uiLang === 'en' ? 'Filtering candidate cards' : '正篩選候選卡片'}</span> : null}
            </div>
            <div className="candidate-status" aria-live="polite">
              {!draft.selection
                ? '尚未標定替換段；候選會在你標定後出現。'
                : candidates.loading
                  ? '正在整理候選…'
                  : candidates.error
                    ? '候選暫時不可用；句稿不受影響。'
                    : ''}
            </div>
            {candidates.response ? (
              <CandidateGrid
                groups={candidates.response.exact}
                relaxed={activeRelaxation}
                semanticGap={semanticGap}
                onPreview={(candidate, origin) => { previewOrigin.current = origin; setPreview(candidate); }}
              />
            ) : null}
            {candidates.response?.relaxation ? (
              <section className="relaxation-card" aria-labelledby="relaxHeading">
                <div><p className="eyebrow">零結果時只改一項</p><h2 id="relaxHeading">可選放寬：{candidates.response.relaxation.kind}</h2><p>{isPosFilterActive(posFilter) ? (uiLang === 'en' ? 'Candidate count is hidden while filters are active.' : '啟用篩選時不顯示未篩選候選數。') : `預計可找到 ${candidates.response.relaxation.candidateCount} 項；不會自動採用。`}</p></div>
                <button type="button" onClick={() => {
                  if (!draft.selection || !candidates.response?.relaxation) return;
                  const suggestion = candidates.response.relaxation;
                  setRelaxedPrevious({ mode, semanticIntent });
                  setActiveRelaxation({
                    id: suggestion.id,
                    kind: suggestion.kind,
                    from: suggestion.from,
                    to: suggestion.to,
                  });
                  setMode(suggestion.plan.mode);
                  setSemanticIntent(suggestion.plan.semanticIntent);
                  setDraft(lineDraftReducer(draft, {
                    type: 'apply_relaxation',
                    selectionVersion: draft.version,
                    relaxationId: suggestion.id,
                    constraints: suggestion.plan.slots.map((slot) => ({ ...slot, pos: slot.pos + draft.selection!.start })),
                  }));
                }}>確認採用這項放寬</button>
              </section>
            ) : null}
            {draft.undo ? <button type="button" className="undo-action" onClick={() => {
              setDraft((current) => current ? lineDraftReducer(current, { type: 'undo' }) : current);
              if (relaxedPrevious) {
                setMode(relaxedPrevious.mode);
                setSemanticIntent(relaxedPrevious.semanticIntent);
                setRelaxedPrevious(null);
              }
              setActiveRelaxation(null);
            }}>復原最近一次套用／放寬</button> : null}
          </>
        ) : <section className="workbench-empty"><p>貼入你正在寫的一句，或先用碼與平仄搭起空白格；有字後點擊即可標定替換段。</p></section>}
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
