/**
 * Portable maintainer: 關係補錄 — mirrors shared/relation-form.mjs main path.
 */
import { useEffect, useRef, useState, type FormEvent } from 'react';
import { getRelationCopy } from '../../../shared/relation-i18n.mjs';

export interface RelationFormState {
  seed_char: string;
  opposite_char: string;
  relation_type: 'syn' | 'ant';
}

export interface RelationViewProps {
  lang?: 'zh' | 'zh-Hans' | 'en';
  initial?: Partial<RelationFormState>;
  onFormChange?: (next: RelationFormState) => void;
}

function apiDetail(body: { detail?: unknown }, fallback: string): string {
  const d = body.detail;
  if (typeof d === 'string' && d.trim()) return d;
  return fallback;
}

async function postRelation(path: string, payload: RelationFormState) {
  const response = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const body = (await response.json().catch(() => ({}))) as {
    detail?: unknown;
    message?: string;
  };
  return { response, body };
}

export function RelationView({ lang = 'zh', initial, onFormChange }: RelationViewProps) {
  const [seed, setSeed] = useState(initial?.seed_char ?? '');
  const [opposite, setOpposite] = useState(initial?.opposite_char ?? '');
  const [relationType, setRelationType] = useState<'syn' | 'ant'>(
    initial?.relation_type === 'ant' ? 'ant' : 'syn',
  );
  const [ok, setOk] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const seedRef = useRef<HTMLInputElement>(null);
  const copy = getRelationCopy(lang);

  useEffect(() => {
    seedRef.current?.focus({ preventScroll: true });
  }, []);

  const payload = (): RelationFormState => ({
    seed_char: seed.trim(),
    opposite_char: opposite.trim(),
    relation_type: relationType,
  });

  const emit = (next: RelationFormState) => onFormChange?.(next);

  const run = async (path: string, okFallback: string, errFallback: string) => {
    setOk(null);
    setErr(null);
    setBusy(true);
    const bodyPayload = payload();
    emit(bodyPayload);
    try {
      const { response, body } = await postRelation(path, bodyPayload);
      if (!response.ok) {
        setErr(apiDetail(body, errFallback));
        return;
      }
      setOk(body.message || okFallback);
    } catch {
      setErr(copy.cannotReach);
    } finally {
      setBusy(false);
    }
  };

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    void run('/relations/manual', copy.relationAdded, copy.submitFailed);
  };

  const onRevoke = () => {
    void run(
      '/relations/manual/revoke',
      copy.relationRevoked,
      copy.revokeFailed,
    );
  };

  return (
    <section className="relation-view relation-main" aria-labelledby="relationTitle">
      <header className="relation-hero">
        <h1 id="relationTitle">{copy.title}</h1>
        <p className="relation-lede">
          {copy.lede}
        </p>
      </header>

      <form className="relation-form" onSubmit={onSubmit}>
        <div className="field">
          <label htmlFor="seedChar">{copy.seed}</label>
          <span className="hint">
            {copy.seedHint}
          </span>
          <div className="search-input-wrap" data-input-wrap="">
            <input
              ref={seedRef}
              type="text"
              id="seedChar"
              name="seed_char"
              required
              autoComplete="off"
              spellCheck={false}
              value={seed}
              onChange={(e) => {
                const v = e.target.value;
                setSeed(v);
                emit({ seed_char: v.trim(), opposite_char: opposite.trim(), relation_type: relationType });
              }}
            />
          </div>
        </div>

        <div className="field">
          <label htmlFor="oppositeChar">{copy.opposite}</label>
          <span className="hint">
            {copy.oppositeHint}
          </span>
          <div className="search-input-wrap" data-input-wrap="">
            <input
              type="text"
              id="oppositeChar"
              name="opposite_char"
              required
              autoComplete="off"
              spellCheck={false}
              value={opposite}
              onChange={(e) => {
                const v = e.target.value;
                setOpposite(v);
                emit({ seed_char: seed.trim(), opposite_char: v.trim(), relation_type: relationType });
              }}
            />
          </div>
        </div>

        <div className="field">
          <span id="relationTypeLabel">{copy.relationType}</span>
          <div className="relation-type" role="radiogroup" aria-labelledby="relationTypeLabel">
            <label>
              <input
                type="radio"
                name="relation_type"
                value="syn"
                checked={relationType === 'syn'}
                onChange={() => {
                  setRelationType('syn');
                  emit({ seed_char: seed.trim(), opposite_char: opposite.trim(), relation_type: 'syn' });
                }}
              />{' '}
              {copy.synonym}
            </label>
            <label>
              <input
                type="radio"
                name="relation_type"
                value="ant"
                checked={relationType === 'ant'}
                onChange={() => {
                  setRelationType('ant');
                  emit({ seed_char: seed.trim(), opposite_char: opposite.trim(), relation_type: 'ant' });
                }}
              />{' '}
              {copy.antonym}
            </label>
          </div>
        </div>

        <div className="actions">
          <button className="primary-button" type="submit" disabled={busy}>
            {copy.add}
          </button>
          <button className="danger-button" type="button" disabled={busy} onClick={onRevoke}>
            {copy.revoke}
          </button>
        </div>

        {ok ? (
          <div className="status ok" role="status">
            {ok}
          </div>
        ) : null}
        {err ? (
          <div className="status err" role="alert">
            {err}
          </div>
        ) : null}
      </form>
    </section>
  );
}
