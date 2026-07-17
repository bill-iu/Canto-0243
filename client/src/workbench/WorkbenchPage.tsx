import { type FormEvent, useMemo, useRef, useState, useEffect } from 'react';

import { searchPageHref } from '../app-page.ts';
import { CandidateGrid } from './CandidateGrid.tsx';
import { ComparePanel } from './ComparePanel.tsx';
import { ConstraintBar } from './ConstraintBar.tsx';
import type { CandidateGroups, RelaxationKind, ReplacementPlanV1, WorkbenchCandidate, WorkbenchSlotConstraintV1 } from './contracts.ts';
import { createLineDraft, lineDraftReducer, type LineDraft } from './line-draft.ts';
import { loadLineDraft, saveLineDraft } from './line-draft-storage.ts';
import { parseLineInput } from './line-input.ts';
import type { PwaLineReadingSlot } from './pwa-line-readings.ts';
import { SentenceCanvas } from './SentenceCanvas.tsx';
import { selectWorkbenchAdapter } from './workbench-adapter.ts';
import { useWorkbenchCandidates } from './useWorkbenchCandidates.ts';
import { WorkbenchBridgeError, consumeIngest, writeOpenSearch } from './workbench-bridge.ts';
import './workbench-page.css';

function initialDraft(): LineDraft | null {
  try { return loadLineDraft(localStorage); } catch { return null; }
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
  const [input, setInput] = useState('');
  const [draft, setDraft] = useState<LineDraft | null>(initialDraft);
  const [readings, setReadings] = useState<PwaLineReadingSlot[]>([]);
  const [mode, setMode] = useState<ReplacementPlanV1['mode']>('m1');
  const [semanticIntent, setSemanticIntent] = useState<ReplacementPlanV1['semanticIntent']>('ranked');
  const [message, setMessage] = useState('');
  const [preview, setPreview] = useState<WorkbenchCandidate | null>(null);
  const [relaxedPrevious, setRelaxedPrevious] = useState<{ mode: ReplacementPlanV1['mode']; semanticIntent: ReplacementPlanV1['semanticIntent'] } | null>(null);
  const [activeRelaxation, setActiveRelaxation] = useState<ActiveRelaxation | null>(null);
  const previewOrigin = useRef<HTMLButtonElement | null>(null);
  const draftRef = useRef(draft);
  const previewRef = useRef(preview);
  const ingestDone = useRef(false);
  draftRef.current = draft;
  previewRef.current = preview;

  useEffect(() => {
    if (!draft) return;
    try { saveLineDraft(localStorage, draft); } catch { setMessage('這次未能自動保存；句稿仍可繼續編輯。'); }
  }, [draft]);

  const changeMode = (next: ReplacementPlanV1['mode']) => {
    setMode(next);
    setActiveRelaxation(null);
  };
  const changeSemantic = (next: ReplacementPlanV1['semanticIntent']) => {
    setSemanticIntent(next);
    setActiveRelaxation(null);
  };

  const resolveReadings = async (surface: string, baseDraft: LineDraft) => {
    if (!surface) return;
    try {
      const resolved = await adapter.resolveLine(surface);
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
      setMessage(resolved.some((slot) => slot.kind === 'unresolved') ? '部分字未有收錄讀音；你仍可鎖字或改用碼起句。' : '已解析逐字讀音；請圈選一至四格。');
    } catch {
      setMessage('詞庫暫未就緒；句稿已建立，可繼續編輯並稍後重試。');
    }
  };

  useEffect(() => {
    if (ingestDone.current) return;
    ingestDone.current = true;
    const payload = consumeIngest(sessionStorage);
    if (!payload) return;

    if (payload.mode === 'insert') {
      setDraft((current) => {
        if (!current?.selection) {
          setMessage('無法插入：工作台沒有選段；請改用取代整句。');
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
      setMessage('已從搜尋放入字面；請圈選一至四格。');
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
    setMessage(
      parsed.kind === 'code'
        ? '已按碼建立空白句格，不會自動填入字面；請圈選一至四格。'
        : '句格已建立；請圈選一至四格以查看候選。',
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
      if (slot.locked && slot.surface) slots.push({ pos: offset, kind: 'literal_char', literal: slot.surface });
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
  const candidates = useWorkbenchCandidates(plan, adapter);
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

      if (event.key === 'l' || event.key === 'L') {
        if (!current.selection) return;
        event.preventDefault();
        setDraft(lineDraftReducer(current, { type: 'lock_selection' }));
        return;
      }
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
      <header className="workbench-header">
        <a className="workbench-brand" href={searchPageHref()} aria-label="返回搜尋首頁">Canto-0243</a>
        <div><p className="eyebrow">創作主導權在你手上</p><h1>句格工作台</h1></div>
        <a className="back-search" href={searchPageHref()}>返回查韻</a>
      </header>
      <main className="workbench-main">
        <section className="workbench-intro">
          <div><h2>把一句拆開，看清每個選擇</h2><p>工具會整理聲調、押韻與原意取捨；不會替你自動填詞。</p></div>
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
              onSelect={(start, width) => setDraft((current) => current ? lineDraftReducer(current, { type: 'select', start, width }) : current)}
              onToggleLock={(pos) => setDraft((current) => current ? lineDraftReducer(current, { type: 'toggle_lock', pos }) : current)}
              onChooseReading={(pos, jyutping, code) => setDraft((current) => current ? lineDraftReducer(current, { type: 'choose_reading', pos, jyutping, code }) : current)}
            />
            <ConstraintBar
              mode={mode}
              semanticIntent={semanticIntent}
              onModeChange={changeMode}
              onSemanticChange={changeSemantic}
              finalAnchorDisabled={!draft.selection || !draft.slots[draft.selection.start + draft.selection.width - 1]?.surface}
              initialAnchorDisabled={!draft.selection || !draft.slots[draft.selection.start]?.surface}
              onAddFinalAnchor={() => setDraft((current) => {
                if (!current?.selection) return current;
                const pos = current.selection.start + current.selection.width - 1;
                const ref = current.slots[pos]?.surface;
                return ref ? lineDraftReducer(current, { type: 'set_constraint', constraint: { pos, kind: 'final_anchor', ref } }) : current;
              })}
              onAddInitialAnchor={() => setDraft((current) => {
                if (!current?.selection) return current;
                const pos = current.selection.start;
                const ref = current.slots[pos]?.surface;
                return ref ? lineDraftReducer(current, { type: 'set_constraint', constraint: { pos, kind: 'initial_anchor', ref } }) : current;
              })}
            />
            <div className="candidate-status" aria-live="polite">
              {!draft.selection
                ? '尚未圈選字位；候選會在你選段後出現。'
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
                <div><p className="eyebrow">零結果時只改一項</p><h2 id="relaxHeading">可選放寬：{candidates.response.relaxation.kind}</h2><p>預計可找到 {candidates.response.relaxation.candidateCount} 項；不會自動採用。</p></div>
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
        ) : <section className="workbench-empty"><p>貼入你正在寫的一句，或先用碼與平仄搭起空白格。</p></section>}
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
