import { GUIDE_SECTIONS, type GuideExample, type GuideMode } from './guide-examples';

export interface GuideViewProps {
  onPick: (query: string, mode: GuideMode) => void;
  onBack: () => void;
}

export function GuideView({ onPick, onBack }: GuideViewProps) {
  return (
    <div className="guide-view">
      <header className="guide-view__header">
        <h2 className="guide-view__title" id="guideTitle" tabIndex={-1}>
          搜尋教學
        </h2>
        <button type="button" className="guide-back" onClick={onBack}>
          返回搜尋
        </button>
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
