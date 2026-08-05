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
import { formatWorkbenchCopy, getWorkbenchCopy } from '../../../shared/workbench-i18n.mjs';
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
import { isHanSurface } from './wildcard-slot.ts';
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
  const copy = getWorkbenchCopy(uiLang);
  const [uiTheme, setUiTheme] = useState<'light' | 'dark'>(() => {
    const theme = getTheme();
    return theme === 'light' || theme === 'dark' ? theme : 'dark';
  });
  const [entrySize, setEntrySize] = useEntrySize();

  const previewOrigin = useRef<HTMLButtonElement | null>(null);
  const lineInputFormRef = useRef<HTMLFormElement | null>(null);
  const workbenchScrollTopRef = useRef(0);
  const [showReturnToInput, setShowReturnToInput] = useState(false);

  const coordinator = useWorkbenchSessionCoordinator({
    adapter,
    active,
    isReady,
    initialize,
    initialPosFilter: resetPosFilter(),
  });
  const {
    session,
    readings,
    preview,
    activeRelaxation,
    posFilter,
    spanInputError,
    notice,
  } = coordinator.model;
  const {
    resolveReadings,
    previewCandidate,
    dismissPreview,
    rememberRelaxation,
    changePosFilter,
    reportSpanError,
  } = coordinator.actions;

  const draft = session.draft;
  const {
    mode,
    semanticIntent,
    rhymeProfile,
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

  // 搜尋殼押韻模式 → 句格 constraints（ADR-0078 session 共用）
  useEffect(() => {
    if (!active) return;
    let unsub = () => {};
    void import('../rhyme-profile-ui.ts').then(({ getUiRhymeProfile, subscribeUiRhymeProfile }) => {
      const sync = () => {
        const p = getUiRhymeProfile();
        if (p !== (session.constraints.rhymeProfile ?? 'exact')) {
          coordinator.actions.chooseRhymeProfile(p);
        }
      };
      sync();
      unsub = subscribeUiRhymeProfile(sync);
    });
    return () => unsub();
  }, [active, coordinator.actions, session.constraints.rhymeProfile]);

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
      setMessage(copy.routeBackFailed);
      return;
    }
    navigateAppRoute('search');
  };

  const changeMode = useCallback((next: ReplacementPlanV1['mode']) => {
    coordinator.actions.chooseMode(next);
  }, [coordinator.actions]);
  const changeSemantic = useCallback((next: ReplacementPlanV1['semanticIntent']) => {
    coordinator.actions.chooseSemanticIntent(next);
  }, [coordinator.actions]);
  const changeRhymeProfile = useCallback((next: import('./session/types.ts').ConstraintsUI['rhymeProfile']) => {
    coordinator.actions.chooseRhymeProfile(next);
    // keep search shell session in sync (ADR-0078 P1)
    import('../rhyme-profile-ui.ts').then(({ setUiRhymeProfile }) => setUiRhymeProfile(next));
  }, [coordinator.actions]);
  const changeCodeConstraint = useCallback((next: CodeConstraintMode) => {
    coordinator.actions.chooseCodeConstraint(next);
  }, [coordinator.actions]);
  const changeExplicitCode = useCallback((raw: string) => {
    coordinator.actions.changeExplicitCode(raw);
  }, [coordinator.actions]);

  const handleToggleLock = useCallback((pos: number) => {
    if (!session.draft) {
      setMessage(copy.noDraft);
      return;
    }
    const slot = session.draft.slots[pos];
    if (!slot || (!slot.surface && !slot.code)) {
      setMessage(copy.blankLock);
      return;
    }
    coordinator.actions.toggleLock(pos);
    setMessage('');
    reportSpanError('');
  }, [coordinator.actions, copy, reportSpanError, session]);

  const handleClearLocks = useCallback(() => {
    if (!session.draft?.slots.some((slot) => slot.locked)) return;
    coordinator.actions.clearLocks();
    reportSpanError('');
    setMessage(copy.locksCleared);
  }, [coordinator.actions, copy, reportSpanError, session]);

  const changeRhymePicks = useCallback((next: PhonemeDimPicks) => {
    coordinator.actions.changeRhymePicks(next);
  }, [coordinator.actions]);
  const changeInitialPicks = useCallback((next: PhonemeDimPicks) => {
    coordinator.actions.changeInitialPicks(next);
  }, [coordinator.actions]);
  const changeRhymeRef = useCallback((value: string) => {
    coordinator.actions.changeRhymeRef(value);
  }, [coordinator.actions]);
  const changeInitialRef = useCallback((value: string) => {
    coordinator.actions.changeInitialRef(value);
  }, [coordinator.actions]);

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
      setMessage(copy.readingFailed);
    } else if (notice?.code === 'storage_failed') {
      setMessage(copy.storageFailed);
    } else if (notice?.code === 'stale_candidate') {
      setMessage(copy.staleCandidate);
    }
  }, [copy.readingFailed, copy.storageFailed, copy.staleCandidate, notice]);

  useEffect(() => {
    if (!readings.length) return;
    setMessage(readings.some((slot) => slot.kind === 'unresolved')
      ? copy.readingsPartial
      : copy.readingsReady);
  }, [copy.readingsPartial, copy.readingsReady, readings]);

  useEffect(() => {
    if (!active) return;
    const payload = consumeIngest(sessionStorage);
    if (!payload) return;

    if (payload.mode === 'insert') {
      if (!session.draft?.selection) {
        setMessage(copy.insertNoSpan);
        return;
      }
      coordinator.actions.insertLiteral(payload.literal);
      setMessage(copy.inserted);
      return;
    }

    const parsed = parseLineInput(payload.literal);
    if (!parsed.ok || parsed.kind !== 'surface') {
      setMessage(copy.ingestInvalid);
      return;
    }
    if (session.draft) coordinator.actions.replaceSurface(payload.literal);
    else coordinator.actions.createDraft(createLineDraft(parsed));
    setMessage(copy.ingested);
  }, [active, coordinator.actions, copy, session.draft]);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const parsed = parseLineInput(input);
    if (!parsed.ok) {
      setMessage(
        parsed.error === 'too_long'
          ? copy.tooLong
          : copy.invalidInput,
      );
      return;
    }
    coordinator.actions.createDraft(createLineDraft(parsed));
    setMessage(
      parsed.kind === 'code'
        ? copy.createdCode
        : parsed.kind === 'mixed'
          ? copy.createdMixed
          : copy.createdSurface,
    );
  };

  const handleChooseReading = useCallback((pos: number, jyutping: string, code: string) => {
    coordinator.actions.chooseReading(pos, jyutping, code);
  }, [coordinator.actions]);

  const handleSetSlotManual = useCallback((pos: number, surface: string, code?: string) => {
    coordinator.actions.changeManualSlot(pos, surface, code ?? '');
    reportSpanError('');
    setMessage(surface ? copy.manualSurface : copy.manualCode);
  }, [coordinator.actions, copy, reportSpanError]);

  const handleClearSurfaces = useCallback(() => {
    if (!session.draft) return;
    coordinator.actions.clearDraft();
    reportSpanError('');
    setMessage(copy.cleared);
  }, [coordinator.actions, copy, reportSpanError, session]);

  const handleApplySpanInput = useCallback((parsed: Extract<ReturnType<typeof parseSpanManual>, { ok: true }>) => {
    if (!session.draft?.selection) {
      reportSpanError(copy.spanRequired);
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
    coordinator.actions.applySpanInput({
      selectionVersion: session.version,
      slots,
      constraints: parsed.constraints,
    });
    reportSpanError('');
    setMessage(copy.spanApplied);
  }, [coordinator.actions, copy, reportSpanError, session]);

  const performUndo = useCallback(() => {
    if (!session.undo) return;
    coordinator.actions.undo();
    reportSpanError('');
    setMessage(session.draft ? copy.undoChange : copy.undoClear);
  }, [coordinator.actions, copy, reportSpanError, session]);

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
    dismissPreview();
    requestAnimationFrame(() => previewOrigin.current?.focus());
  };

  const applyPreview = (candidate: WorkbenchCandidate) => {
    const current = session;
    if (!current.draft?.selection) return;
    coordinator.actions.applyCandidate({
      selectionVersion: candidates.response?.selectionVersion ?? current.version,
      literal: candidate.literal,
      jyutping: candidate.jyutping,
      code: candidate.code,
      relaxationId: candidate.relaxationId ?? activeRelaxation?.id,
    });
    dismissPreview();
    setTimeout(() => document.querySelector<HTMLButtonElement>(`[data-line-slot="${current.draft!.selection!.start}"]`)?.focus(), 0);
  };

  const handlePreview = useCallback((candidate: WorkbenchCandidate, origin: HTMLButtonElement) => {
    previewOrigin.current = origin;
    previewCandidate(candidate);
  }, [previewCandidate]);

  const openInSearch = (literal: string) => {
    if (onOpenSearchLiteral) {
      onOpenSearchLiteral(literal);
      return;
    }
    try {
      writeOpenSearch(sessionStorage, { literal });
      navigateAppRoute('search');
    } catch (error) {
      setMessage(error instanceof WorkbenchBridgeError ? error.message : copy.searchOpenFailed);
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
        previewCandidate(candidate);
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, activeRelaxation, candidates, preview, session]);

  const intro = workbenchIntroCopy(uiLang);
  const canUndo = Boolean(session.undo);
  const headingExtra = useMemo(() => (
    <>
      <PosFilterControl value={posFilter} onChange={changePosFilter} lang={uiLang} />
      {isPosFilterActive(posFilter) ? (
        <span className="constraint-bar__pos-status">
          {copy.filtering}
        </span>
      ) : null}
    </>
  ), [changePosFilter, copy.filtering, posFilter, uiLang]);
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
                {copy.createSentence}
              </button>
              {!draft && canUndo ? (
                <button
                  type="button"
                  className="canvas-clear-surfaces line-input-form__undo"
                  title={copy.undoClearTitle}
                  aria-label={copy.undoClearTitle}
                  onClick={performUndo}
                >
                  {copy.undo}
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
              onSpanInputError={reportSpanError}
              spanInputError={spanInputError}
            />
            <ConstraintBar
              mode={mode}
              semanticIntent={semanticIntent}
              rhymeProfile={rhymeProfile ?? 'exact'}
              codeConstraint={codeConstraint}
              explicitCode={explicitCode}
              onModeChange={changeMode}
              onSemanticChange={changeSemantic}
              onRhymeProfileChange={changeRhymeProfile}
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
                return parsePhonemeRef(rhymeRef, n).ok
                  ? ''
                  : formatWorkbenchCopy(copy.spanWidth, { count: n });
              })()}
              initialRefError={(() => {
                const n = phonemeCheckedOffsets(initialPicks, draft.selection?.width ?? 0).length;
                return parsePhonemeRef(initialRef, n).ok
                  ? ''
                  : formatWorkbenchCopy(copy.spanWidth, { count: n });
              })()}
              canUndo={canUndo}
              onUndo={performUndo}
              headingExtra={headingExtra}
            />
            <div className="candidate-status" aria-live="polite">
              {!draft.selection
                ? copy.noSelection
                : candidates.loading
                  ? copy.organizingCandidates
                  : candidates.error
                    ? copy.candidatesUnavailable
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
                  <p className="eyebrow">{copy.relaxEyebrow}</p>
                  <h2 id="relaxHeading">
                    {formatWorkbenchCopy(copy.relaxTitle, {
                      kind: relaxationKindLabel(candidates.response.relaxation.kind, uiLang),
                    })}
                  </h2>
                  <p>
                    {isPosFilterActive(posFilter)
                      ? copy.filterCountHidden
                      : formatWorkbenchCopy(copy.relaxEstimate, {
                        count: candidates.response.relaxation.candidateCount,
                      })}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    if (!draft.selection || !candidates.response?.relaxation) return;
                    const suggestion = candidates.response.relaxation;
                    coordinator.actions.applyRelaxation({
                      selectionVersion: session.version,
                      relaxationId: suggestion.id,
                      kind: suggestion.kind,
                      plan: suggestion.plan,
                    });
                    rememberRelaxation({
                      id: suggestion.id,
                      kind: suggestion.kind,
                      from: suggestion.from,
                      to: suggestion.to,
                    }, session.version + 1);
                  }}
                >
                  {copy.relaxConfirm}
                </button>
              </section>
            ) : null}
          </>
        ) : (
          <section className="workbench-empty">
            <p>{copy.emptyHelp}</p>
          </section>
        )}
      </main>
      {showReturnToInput ? (
        <button
          type="button"
          className="workbench-return-to-input"
          aria-label={copy.returnInputAria}
          onClick={returnToInput}
        >
          {copy.returnInput}
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
