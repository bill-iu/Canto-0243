/**
 * Portable maintainer: 關係補錄 — mirrors shared/relation-form.mjs main path.
 */
import { useEffect, useRef, useState, type FormEvent } from 'react';

export interface RelationFormState {
  seed_char: string;
  opposite_char: string;
  relation_type: 'syn' | 'ant';
}

export interface RelationViewProps {
  lang?: 'zh' | 'en';
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
      setErr(lang === 'en' ? 'Cannot reach the server. Is it running?' : '無法連線後端。請確認伺服器已啟動。');
    } finally {
      setBusy(false);
    }
  };

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    void run('/relations/manual', lang === 'en' ? 'Relation added.' : '已補上關係。', lang === 'en' ? 'Submit failed.' : '提交失敗，請稍後再試。');
  };

  const onRevoke = () => {
    void run(
      '/relations/manual/revoke',
      lang === 'en' ? 'Relation revoked.' : '已撤回關係。',
      lang === 'en' ? 'Revoke failed.' : '撤回失敗，請稍後再試。',
    );
  };

  return (
    <section className="relation-view relation-main" aria-labelledby="relationTitle">
      <header className="relation-hero">
        <h1 id="relationTitle">{lang === 'en' ? 'Add relations' : '關係補錄'}</h1>
        <p className="relation-lede">
          {lang === 'en'
            ? 'Add synonym or antonym links for lexicon entries. Seed is the expansion start; opposite is the one-hop neighbour.'
            : '為已收錄字面補近義或反義關係。種子字面為擴展起點；對端字面提供一跳鄰居來源。'}
        </p>
      </header>

      <form className="relation-form" onSubmit={onSubmit}>
        <div className="field">
          <label htmlFor="seedChar">{lang === 'en' ? 'Seed' : '種子字面'}</label>
          <span className="hint">
            {lang === 'en'
              ? 'Expansion starts here (e.g. 快樂 when adding links for 快樂)'
              : '擴展從此字面出發（例如要補「快樂」的關係時填快樂）'}
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
          <label htmlFor="oppositeChar">{lang === 'en' ? 'Opposite' : '對端字面'}</label>
          <span className="hint">
            {lang === 'en' ? 'The other literal linked directly to the seed' : '與種子建立 direct 關係的另一字面'}
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
          <span id="relationTypeLabel">{lang === 'en' ? 'Relation type' : '關係類型'}</span>
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
              {lang === 'en' ? 'Synonym' : '近義'}
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
              {lang === 'en' ? 'Antonym' : '反義'}
            </label>
          </div>
        </div>

        <div className="actions">
          <button className="primary-button" type="submit" disabled={busy}>
            {lang === 'en' ? 'Add relation' : '補上關係'}
          </button>
          <button className="danger-button" type="button" disabled={busy} onClick={onRevoke}>
            {lang === 'en' ? 'Revoke relation' : '撤回關係'}
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
