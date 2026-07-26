import {
  type FormEvent,
  useMemo,
  useRef,
  useState,
  useEffect,
  useCallback,
  useDeferredValue,
} from 'react';

import { getLang, setLang, getTheme, setTheme, readLexiconVersionMeta } from '../../../shared/app-context.mjs';
import { getWorkbenchCopy } from '../../../shared/workbench-i18n.mjs';
import { navigateAppRoute } from '../app-navigation.ts';
import { BrandLogo } from '../brand-logo.tsx';
import { BrandSvgDefs } from '../brand-svg-defs.tsx';
import { getActiveDbBackendMode } from '../db/init.ts';
import { HeaderHero } from '../header-hero.tsx';
import { useDB } from '../hooks/useDB.ts';
import { isPortableHost } from '../host-mode.ts';
import { useEntrySize } from '../entry-size';
import { ModeMenu } from '../mode-menu.tsx';
import { exitPortable } from '../portable-exit.ts';
import { PosFilterControl } from '../pos/PosFilterControl.tsx';
import { isPosFilterActive, resetPosFilter } from '../pos/filter.ts';
import { revealPwaShell } from '../pwa-shell-boot.ts';
import { CandidateGrid } from './CandidateGrid.tsx';
import { ComparePanel } from './ComparePanel.tsx';
import { ConstraintBar } from './ConstraintBar.tsx';
import type { CodeConstraintMode } from './code-constraint.ts';
import {
  type CandidateGroups,
  type ReplacementPlanV1,
  type WorkbenchCandidate,
} from './contracts.ts';
import { workbenchIntroCopy } from './intro-copy.ts';
import { createLineDraft } from './line-draft.ts';
import { WORKBENCH_LINE_INPUT_COPY } from './line-input-copy.ts';
import { parseLineInput } from './line-input.ts';
import { parsePhonemeRef, parseSpanManual } from './manual-slot-input.ts';
import { relaxationKindLabel } from './relaxation-i18n.ts';
import { phonemeCheckedOffsets, type PhonemeDimPicks } from './replacement-span.ts';
import {
  derivePlanBase,
} from './session/index.ts';
import { SentenceCanvas } from './SentenceCanvas.tsx';
import { useWorkbenchCandidates } from './useWorkbenchCandidates.ts';
import { isHanSurface, normalizeWildcardChar } from './wildcard-slot.ts';
import { selectWorkbenchAdapter } from './workbench-adapter.ts';
import { useWorkbenchSessionCoordinator } from './useWorkbenchSessionCoordinator.ts';
import {
  WorkbenchBridgeError,
  consumeIngest,
  writeNavigate,
  writeOpenSearch,
  type SearchModeFamily,
} from './workbench-bridge.ts';
import './workbench-page.css';

export interface WorkbenchPageProps {
  active?: boolean;
  hidden?: boolean;
  embedded?: boolean;
  lang?: 'zh' | 'zh-Hans' | 'en';
  theme?: 'light' | 'dark';
  onLangChange?: (lang: 'zh' | 'zh-Hans' | 'en') => void;
  onThemeChange?: (theme: 'light' | 'dark') => void;
  onOpenSearchHome?: () => void;
  onOpenSearchNavigation?: (input: { kind: 'mode'; family: SearchModeFamily } | { kind: 'guide' } | { kind: 'about' }) => void;
  onOpenSearchLiteral?: (literal: string) => void;
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

export function WorkbenchPage({
  active = true,
  hidden = false,
  embedded = false,
  lang,
  theme,
  onLangChange,
  onThemeChange,
  onOpenSearchHome,
  onOpenSearchNavigation,
  onOpenSearchLiteral,
}: WorkbenchPageProps = {}) {
  const lexiconVersion =
    (isPortableHost() ? readLexiconVersionMeta() : null) ||
    (import.meta as any).env?.VITE_LEXICON_VERSION ||
    'dev';
  const adapter = useMemo(
    () => selectWorkbenchAdapter(isPortableHost(), { lexiconIdentity: lexiconVersion }),
    [lexiconVersion],
  );
  const { isReady, initialize } = useDB();

  const [input, setInput] = useState('');
  const [message, setMessage] = useState('');
  const [uiLang, setUiLang] = useState<'zh' | 'zh-Hans' | 'en'>(() => getLang() as 'zh' | 'zh-Hans' | 'en');
  const [uiTheme, setUiTheme] = useState<'light' | 'dark'>(() => {
    const theme = getTheme();
    return theme === 'light' || theme === 'dark' ? theme : 'dark';
  });
  const [entrySize, setEntrySize] = useEntrySize();

  const previewOrigin = useRef<HTMLButtonElement | null>(null);
  const lineInputFormRef = useRef<HTMLFormElement | null>(null);
  const workbenchScrollTopRef = useRef(0);
  const [showReturnToInput, setShowReturnToInput] = useState(false);

  const {
    session,
    readings,
    preview,
    activeRelaxation,
    posFilter,
    spanInputError,
    dispatchSession: dispatch,
    resolveReadings,
    setPreview,
    setActiveRelaxation,
    setPosFilter,
    setSpanInputError,
    notice,
  } = useWorkbenchSessionCoordinator({
    adapter,
    active,
    isReady,
    initialize,
    initialPosFilter: resetPosFilter(),
  });

  const draft = session.draft;
  const {
    mode,
    semanticIntent,
    codeConstraint,
    explicitCode,
    rhymePicks,
    initialPicks,
    rhymeRef,
    initialRef,
  } = session.constraints;

  useEffect(() => {
    if (!active) return;
    revealPwaShell();
    document.body.classList.add('workbench-route');
    return () => document.body.classList.remove('workbench-route');
  }, [active]);

  useEffect(() => {
    if (!active) return;
    requestAnimationFrame(() => window.scrollTo({ top: workbenchScrollTopRef.current, behavior: 'auto' }));
    const save = () => { workbenchScrollTopRef.current = window.scrollY; };
    window.addEventListener('scroll', save, { passive: true });
    return () => {
      save();
      window.removeEventListener('scroll', save);
    };
  }, [active]);

  useEffect(() => {
    if (!active) {
      setShowReturnToInput(false);
      return;
    }
    const form = lineInputFormRef.current;
    if (!form || typeof IntersectionObserver === 'undefined') return;
    const observer = new IntersectionObserver(([entry]) => {
      setShowReturnToInput(!entry.isIntersecting);
    }, { threshold: 0 });
    observer.observe(form);
    return () => observer.disconnect();
  }, [active, draft]);

  useEffect(() => {
    void initialize();
  }, [initialize]);

  useEffect(() => {
    setTheme(uiTheme);
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', uiTheme === 'dark' ? '#1C1917' : '#DFD2C2');
  }, [uiTheme]);

  useEffect(() => {
    if (lang) setUiLang(lang);
  }, [lang]);

  useEffect(() => {
    if (theme) setUiTheme(theme);
  }, [theme]);

  useEffect(() => {
    setLang(uiLang);
    document.documentElement.lang = uiLang === 'zh' ? 'zh-Hant' : uiLang === 'zh-Hans' ? 'zh-Hans' : 'en';
  }, [uiLang]);

  const goSearchHome = () => {
    if (onOpenSearchHome) {
      onOpenSearchHome();
      return;
    }
    navigateAppRoute('search');
  };

  const goSearchWithNavigate = (input: { kind: 'mode'; family: SearchModeFamily } | { kind: 'guide' } | { kind: 'about' }) => {
    if (onOpenSearchNavigation) {
      onOpenSearchNavigation(input);
      return;
    }
    try {
      writeNavigate(sessionStorage, input);
    } catch (error) {
      if (!(error instanceof WorkbenchBridgeError)) throw error;
      setMessage('暫時無法回到查韻；請再試一次。');
      return;
    }
    navigateAppRoute('search');
  };

  const changeMode = useCallback((next: ReplacementPlanV1['mode']) => {
    dispatch({ type: 'set_mode', mode: next });
  }, [dispatch]);
  const changeSemantic = useCallback((next: ReplacementPlanV1['semanticIntent']) => {
    dispatch({ type: 'set_semantic', semanticIntent: next });
  }, [dispatch]);
  const changeCodeConstraint = useCallback((next: CodeConstraintMode) => {
    dispatch({ type: 'set_code_constraint', mode: next });
  }, [dispatch]);
  const changeExplicitCode = useCallback((raw: string) => {
    dispatch({ type: 'set_explicit_code', raw });
  }, [dispatch]);

  const handleToggleLock = useCallback((pos: number) => {
    if (!session.draft) {
      setMessage('尚未建立句格。');
      return;
    }
    const slot = session.draft.slots[pos];
    if (!slot || (!slot.surface && !slot.code)) {
      setMessage('空白格不能鎖定；請先有字面、通配或碼。');
      return;
    }
    dispatch({ type: 'toggle_lock', pos });
    setMessage('');
    setSpanInputError('');
  }, [dispatch, session, setSpanInputError]);

  const handleClearLocks = useCallback(() => {
    if (!session.draft?.slots.some((slot) => slot.locked)) return;
    dispatch({ type: 'clear_locks' });
    setSpanInputError('');
    setMessage('已解除全部鎖定。');
  }, [dispatch, session, setSpanInputError]);

  const changeRhymePicks = useCallback((next: PhonemeDimPicks) => {
    dispatch({ type: 'set_rhyme_picks', picks: next });
  }, [dispatch]);
  const changeInitialPicks = useCallback((next: PhonemeDimPicks) => {
    dispatch({ type: 'set_initial_picks', picks: next });
  }, [dispatch]);
  const changeRhymeRef = useCallback((value: string) => {
    dispatch({ type: 'set_rhyme_ref', value });
  }, [dispatch]);
  const changeInitialRef = useCallback((value: string) => {
    dispatch({ type: 'set_initial_ref', value });
  }, [dispatch]);

  useEffect(() => {
    const needed: string[] = [];
    const seen = new Set<string>();
    const known = session.constraints.refReadings;
    for (const raw of [rhymeRef, initialRef]) {
      for (const ch of Array.from(raw.trim())) {
        const normalized = normalizeWildcardChar(ch);
        if (!isHanSurface(normalized) || seen.has(normalized) || known[normalized]) continue;
        seen.add(normalized);
        needed.push(normalized);
      }
    }
    if (!needed.length || !isReady) return;
    const controller = new AbortController();
    void (async () => {
      try {
        const resolved = await adapter.resolveLine(needed.join(''), controller.signal);
        const readingsMap: Record<string, string> = {};
        needed.forEach((ch, index) => {
          const jyutping = resolved[index]?.choices[0]?.jyutping;
          if (jyutping) readingsMap[ch] = jyutping;
        });
        if (Object.keys(readingsMap).length) {
          dispatch({ type: 'merge_ref_readings', readings: readingsMap });
        }
      } catch {
        // ponytail: keep surface fallbacks until lexicon answers
      }
    })();
    return () => controller.abort();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rhymeRef, initialRef, isReady]);

  const surfaceOnlyOf = (slots: { surface: string }[]) => slots
    .map((slot) => slot.surface)
    .filter((surface) => isHanSurface(surface))
    .join('');

  useEffect(() => {
    if (!active || !isReady || !session.draft?.surface || readings.length > 0) return;
    const surface = surfaceOnlyOf(session.draft.slots) || session.draft.surface;
    void resolveReadings(surface, session.version, session.draft.slots);
  }, [active, isReady, readings.length, resolveReadings, session]);

  useEffect(() => {
    if (notice?.code === 'reading_failed') {
      setMessage('詞庫暫未就緒；句稿已建立，可繼續編輯並稍後重試。');
    } else if (notice?.code === 'storage_failed') {
      setMessage('這次未能自動保存；句稿仍可繼續編輯。');
    }
  }, [notice]);

  useEffect(() => {
    if (!readings.length) return;
    setMessage(readings.some((slot) => slot.kind === 'unresolved')
      ? '部分字未有收錄讀音；你仍可鎖定字位或改用碼起句。'
      : '已解析逐字讀音；請點擊鎖定替換段。');
  }, [readings]);

  useEffect(() => {
    if (!active) return;
    const payload = consumeIngest(sessionStorage);
    if (!payload) return;

    if (payload.mode === 'insert') {
      if (!session.draft?.selection) {
        setMessage('無法插入：工作台沒有已鎖範圍；請改用取代整句。');
        return;
      }
      dispatch({ type: 'insert_literal', literal: payload.literal });
      setMessage('已插入字面到選段；請確認讀音。');
      return;
    }

    const parsed = parseLineInput(payload.literal);
    if (!parsed.ok || parsed.kind !== 'surface') {
      setMessage('放入的字面無法建立句格。');
      return;
    }
    dispatch(session.draft
      ? { type: 'replace_surface', literal: payload.literal }
      : { type: 'create_from_parsed', draft: createLineDraft(parsed) });
    setMessage('已從搜尋放入字面；請點擊鎖定替換段。');
  }, [active, dispatch, session.draft]);

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
    dispatch({ type: 'create_from_parsed', draft: createLineDraft(parsed) });
    setMessage(
      parsed.kind === 'code'
        ? '已按碼建立空白句格，不會自動填入字面；請點擊碼格鎖定並查看候選。'
        : parsed.kind === 'mixed'
          ? '已建立混合句格；請點擊鎖定一至四格以查看候選。'
          : '句格已建立；請點擊鎖定一至四格以查看候選。',
    );
  };

  const handleChooseReading = useCallback((pos: number, jyutping: string, code: string) => {
    dispatch({ type: 'choose_reading', pos, jyutping, code });
  }, [dispatch]);

  const handleSetSlotManual = useCallback((pos: number, surface: string, code?: string) => {
    dispatch({ type: 'set_slot_manual', pos, surface, code });
    setSpanInputError('');
    setMessage(surface ? '已手改一字；正在對齊讀音。' : '已手改為碼格。');
  }, [dispatch, setSpanInputError]);

  const handleClearSurfaces = useCallback(() => {
    if (!session.draft) return;
    dispatch({ type: 'clear' });
    setSpanInputError('');
    setMessage('已清空句格。');
  }, [dispatch, session, setSpanInputError]);

  const handleApplySpanInput = useCallback((parsed: Extract<ReturnType<typeof parseSpanManual>, { ok: true }>) => {
    if (!session.draft?.selection) {
      setSpanInputError('請先鎖定替換段。');
      return;
    }
    const slots = parsed.slots.map((slot, pos) => {
      const digit = parsed.constraints.find(
        (item) => item.kind === 'code_digit' && item.pos === pos,
      );
      return {
        surface: slot.surface,
        reading: slot.reading,
        code: slot.code || (digit as { digit?: string })?.digit,
      };
    });
    dispatch({
      type: 'apply_span_input',
      selectionVersion: session.version,
      slots,
      constraints: parsed.constraints,
    });
    setSpanInputError('');
    setMessage('已手打替換段。');
  }, [dispatch, session, setSpanInputError]);

  const performUndo = () => {
    if (!session.undo) return;
    dispatch({ type: 'undo' });
    setSpanInputError('');
    setMessage(session.draft ? '已復原最近一次改動。' : '已復原清空前的句稿。');
  };

  // 候選 session 擁有 cursor；page 只傳 plan 身份（無 paging）
  // 句格 session 即時；候選 plan 延後，避免鎖格被查詢／重繪拖慢（CONTEXT 字位鎖定）
  const planBase = useMemo(() => derivePlanBase(session), [session]);
  const deferredPlanBase = useDeferredValue(planBase);
  const candidates = useWorkbenchCandidates(
    isReady ? deferredPlanBase : null,
    adapter,
    posFilter,
    active,
  );
  const semanticGap = Boolean(
    planBase
    && planBase.semanticIntent !== 'off'
    && candidates.response
    && candidates.response.exact.direct_syn.length === 0
    && candidates.response.exact.semantic_related.length === 0,
  );

  const closePreview = () => {
    setPreview(null);
    requestAnimationFrame(() => previewOrigin.current?.focus());
  };

  const applyPreview = (candidate: WorkbenchCandidate) => {
    const current = session;
    if (!current.draft?.selection) return;
    dispatch({
      type: 'apply_candidate',
      selectionVersion: candidates.response?.selectionVersion ?? current.version,
      literal: candidate.literal,
      jyutping: candidate.jyutping,
      code: candidate.code,
      relaxationId: candidate.relaxationId ?? activeRelaxation?.id,
    });
    setPreview(null);
    setTimeout(() => document.querySelector<HTMLButtonElement>(`[data-line-slot="${current.draft!.selection!.start}"]`)?.focus(), 0);
  };

  const handlePreview = useCallback((candidate: WorkbenchCandidate, origin: HTMLButtonElement) => {
    previewOrigin.current = origin;
    setPreview(candidate);
  }, [setPreview]);

  const openInSearch = (literal: string) => {
    if (onOpenSearchLiteral) {
      onOpenSearchLiteral(literal);
      return;
    }
    try {
      writeOpenSearch(sessionStorage, { literal });
      navigateAppRoute('search');
    } catch (error) {
      setMessage(error instanceof WorkbenchBridgeError ? error.message : '無法打開搜尋頁。');
    }
  };

  useEffect(() => {
    if (!active) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (isTypingTarget(event.target)) return;
      const current = session;
      const open = preview;

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
        if (!current.undo) return;
        event.preventDefault();
        performUndo();
        return;
      }
      if (!current.draft) return;

      if (event.key === '1' || event.key === '2' || event.key === '3') {
        const heading = document.getElementById(GROUP_FOCUS_IDS[Number(event.key) - 1]!);
        if (!heading) return;
        event.preventDefault();
        heading.focus();
        return;
      }
      if (event.key === 'Enter') {
        if (event.target instanceof HTMLElement && event.target.closest('[data-line-slot]')) return;
        const candidate = firstCandidate(candidates.response?.exact);
        if (!candidate) return;
        event.preventDefault();
        setPreview(candidate);
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, activeRelaxation, candidates, preview, session]);

  const intro = workbenchIntroCopy(uiLang);
  const copy = getWorkbenchCopy(uiLang);
  const canUndo = Boolean(session.undo);
  const returnToInput = () => {
    lineInputFormRef.current?.scrollIntoView({ block: 'start', behavior: 'auto' });
  };

  return (
    <div
      className={`workbench-page${preview ? ' has-compare' : ''}${hidden ? ' is-query-tab-hidden' : ''}${embedded ? ' is-query-tab-view' : ''}`}
      hidden={hidden}
    >
      {!embedded ? (
        <>
          <BrandSvgDefs />
          <header className="workbench-header">
            <div className="app-bar">
              <div className="header-chrome">
                <div className="header-chrome__center">
                  <button
                    className="brand"
                    type="button"
                    aria-label={copy.returnToSearch}
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
                    onExitPortable={isPortableHost() ? () => void exitPortable(uiLang === 'en' ? 'en' : 'zh') : undefined}
                    theme={uiTheme}
                    lang={uiLang}
                    onThemeChange={(next) => {
                      setUiTheme(next);
                      onThemeChange?.(next);
                    }}
                    onLangChange={(next) => {
                      setUiLang(next);
                      onLangChange?.(next);
                    }}
                    entrySize={entrySize}
                    onEntrySizeChange={setEntrySize}
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
        </>
      ) : null}
      <main className="workbench-main">
        <section className="workbench-intro">
          <div className="workbench-intro__titles">
            <p className="eyebrow">{intro.eyebrow}</p>
            <h1>{intro.h1}</h1>
            <h2>{intro.h2}</h2>
          </div>
          <form ref={lineInputFormRef} className="line-input-form" onSubmit={submit}>
            <label className="sr-only" htmlFor="lineInput">
              {WORKBENCH_LINE_INPUT_COPY}
            </label>
            <div className="line-input-form__row">
              <input
                id="lineInput"
                value={input}
                onChange={(event) => setInput(event.target.value)}
                maxLength={65}
                placeholder={WORKBENCH_LINE_INPUT_COPY}
              />
              <button type="submit" className="line-input-form__submit">
                建立句格
              </button>
              {!draft && canUndo ? (
                <button
                  type="button"
                  className="canvas-clear-surfaces line-input-form__undo"
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
              onClearLocks={handleClearLocks}
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
              canUndo={canUndo}
              onUndo={performUndo}
              headingExtra={(
                <>
                  <PosFilterControl value={posFilter} onChange={setPosFilter} lang={uiLang} />
                  {isPosFilterActive(posFilter) ? (
                    <span className="constraint-bar__pos-status">
                      {copy.filtering}
                    </span>
                  ) : null}
                </>
              )}
            />
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
                total={candidates.engineTotal}
                loadedCount={candidates.loadedCount}
                hasMore={candidates.hasMore}
                loadingMore={candidates.loading && candidates.hasMore}
                posFilterActive={isPosFilterActive(posFilter)}
                spanWidth={draft.selection?.width ?? 0}
                relaxed={activeRelaxation}
                semanticGap={semanticGap}
                onPreview={handlePreview}
                onLoadMore={candidates.loadMore}
              />
            ) : null}
            {candidates.response?.relaxation ? (
              <section className="relaxation-card" aria-labelledby="relaxHeading">
                <div>
                  <p className="eyebrow">零結果時只改一項</p>
                  <h2 id="relaxHeading">可選放寬：{relaxationKindLabel(candidates.response.relaxation.kind, uiLang)}</h2>
                  <p>
                    {isPosFilterActive(posFilter)
                      ? copy.filterCountHidden
                      : `預計可找到 ${candidates.response.relaxation.candidateCount} 項；不會自動採用。`}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    if (!draft.selection || !candidates.response?.relaxation) return;
                    const suggestion = candidates.response.relaxation;
                    dispatch({
                      type: 'apply_relaxation',
                      selectionVersion: session.version,
                      relaxationId: suggestion.id,
                      kind: suggestion.kind,
                      plan: suggestion.plan,
                    });
                    setActiveRelaxation({
                      id: suggestion.id,
                      kind: suggestion.kind,
                      from: suggestion.from,
                      to: suggestion.to,
                    }, session.version + 1);
                  }}
                >
                  確認採用這項放寬
                </button>
              </section>
            ) : null}
          </>
        ) : (
          <section className="workbench-empty">
            <p>貼入你正在寫的一句，或先用碼與平仄搭起空白格；有字後點擊即可鎖定替換段。</p>
          </section>
        )}
      </main>
      {showReturnToInput ? (
        <button
          type="button"
          className="workbench-return-to-input"
          aria-label="回到建立句格輸入欄"
          onClick={returnToInput}
        >
          ↑ 回到輸入
        </button>
      ) : null}
      {preview && draft?.selection ? (
        <ComparePanel
          candidate={preview}
          draft={draft}
          lang={uiLang === 'en' ? 'zh' : uiLang}
          onClose={closePreview}
          onApply={() => applyPreview(preview)}
          onOpenInSearch={() => openInSearch(preview.literal)}
        />
      ) : null}
    </div>
  );
}
