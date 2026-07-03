import { tabLabel, type QueryTab } from '@shared/query-tabs';

export interface QueryTabsBarProps {
  tabs: QueryTab[];
  activeId: number;
  onSelect: (id: number) => void;
  onClose: (id: number) => void;
  onAdd: () => void;
}

export function QueryTabsBar({ tabs, activeId, onSelect, onClose, onAdd }: QueryTabsBarProps) {
  const canClose = tabs.length > 1;

  return (
    <div className="query-tabs-bar" role="tablist" aria-label="查詢分頁">
      {tabs.map((tab) => {
        const isActive = tab.id === activeId;
        const label = tabLabel(tab);
        return (
          <div
            key={tab.id}
            className={`query-tab-pill${isActive ? ' is-active' : ''}`}
            data-view={tab.view}
          >
            <button
              type="button"
              role="tab"
              className="query-tab-pill__label"
              aria-selected={isActive}
              tabIndex={isActive ? 0 : -1}
              onClick={() => onSelect(tab.id)}
            >
              {label}
            </button>
            {canClose && (
              <button
                type="button"
                className="query-tab-pill__close"
                aria-label={`關閉「${label}」`}
                onClick={(event) => {
                  event.stopPropagation();
                  onClose(tab.id);
                }}
              >
                ×
              </button>
            )}
          </div>
        );
      })}
      <button type="button" className="query-tab-add" aria-label="新增查詢分頁" onClick={onAdd}>
        +
      </button>
    </div>
  );
}
