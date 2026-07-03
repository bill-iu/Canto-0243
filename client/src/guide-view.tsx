import { GUIDE_SECTIONS, type GuideExample, type GuideMode } from './guide-examples';
import { MODE_META, modeMetaFor, uiModeToUrlMode, type UiMode } from './mode-meta';
import { modeHelp } from './mode-menu';

const GUIDE_MODE_OPTIONS: Array<{ uiMode: UiMode; key: string }> = [
  { uiMode: '0243', key: '0243' },
  { uiMode: '02493', key: '02493' },
  { uiMode: 'synonym', key: '~ / !' },
];

export interface GuideViewProps {
  currentMode: UiMode;
  onPick: (query: string, mode: GuideMode) => void;
  onModePick: (mode: UiMode) => void;
}

export function GuideView({ currentMode, onPick, onModePick }: GuideViewProps) {
  const activeUrlMode = uiModeToUrlMode(currentMode);

  return (
    <div className="guide-view">
      <header className="guide-hero">
        <p className="eyebrow">Guide</p>
        <h1 id="guideTitle" tabIndex={-1}>
          搜尋教學
        </h1>
        <p>0243／粵拼／韻母規則與近反義語法，揀例子即試。</p>
        <div className="guide-actions" role="group" aria-label="0243搜尋模式">
          {GUIDE_MODE_OPTIONS.map((option) => {
            const meta = MODE_META[uiModeToUrlMode(option.uiMode)];
            const checked = uiModeToUrlMode(option.uiMode) === activeUrlMode;
            return (
              <button
                key={option.uiMode}
                type="button"
                className="mode-option guide-mode-pick"
                aria-checked={checked}
                onClick={() => onModePick(option.uiMode)}
              >
                <span>
                  <span className="mode-name">
                    {meta.title}
                    <span className="mode-note">{meta.note}</span>
                  </span>
                  <span className="mode-help">{modeHelp(option.uiMode)}</span>
                </span>
                <span className="mode-key">{option.key}</span>
              </button>
            );
          })}
        </div>
      </header>

      <div className="guide-grid">
        {GUIDE_SECTIONS.map((section) => (
          <article key={section.id} className="guide-card">
            <h3>{section.title}</h3>
            <p>{section.intro}</p>
            <div className="guide-examples">
              {section.examples.map((example) => (
                <GuideExampleButton
                  key={`${section.id}-${example.query}-${example.mode}`}
                  example={example}
                  onPick={onPick}
                />
              ))}
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function GuideExampleButton({
  example,
  onPick,
}: {
  example: GuideExample;
  onPick: (query: string, mode: GuideMode) => void;
}) {
  return (
    <button
      type="button"
      className="guide-example"
      title={example.title}
      onClick={() => onPick(example.query, example.mode)}
    >
      <code translate="no">{example.query}</code>
      <span>{example.label}</span>
    </button>
  );
}

/** ponytail: runnable self-check — guide mode pick count */
export function guideViewSelfCheck(): void {
  if (GUIDE_MODE_OPTIONS.length !== 3) {
    throw new Error('guideViewSelfCheck: mode options');
  }
  if (modeMetaFor('0243').title !== '0243模式') {
    throw new Error('guideViewSelfCheck: m1 meta');
  }
}
