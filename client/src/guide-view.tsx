import { GUIDE_SECTIONS, type GuideExample, type GuideMode } from './guide-examples';

export interface GuideViewProps {
  onPick: (query: string, mode: GuideMode) => void;
}

export function GuideView({ onPick }: GuideViewProps) {
  return (
    <div className="guide-view">
      <header className="guide-hero">
        <p className="eyebrow">Guide</p>
        <h1 id="guideTitle" tabIndex={-1}>
          搜尋教學
        </h1>
        <p>0243／粵拼／韻母規則與近反義語法，揀例子即試。</p>
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
