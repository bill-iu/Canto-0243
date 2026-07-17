interface Props {
  literal: string;
  currentSurface: string;
  selectionWidth: number | null;
  onReplace: () => void;
  onInsert: () => void;
  onCancel: () => void;
}

export function PutInWorkbenchModal({
  literal,
  currentSurface,
  selectionWidth,
  onReplace,
  onInsert,
  onCancel,
}: Props) {
  const width = Array.from(literal).length;
  const canInsert = selectionWidth != null && selectionWidth === width;
  return (
    <div className="put-workbench-modal" role="dialog" aria-modal="true" aria-labelledby="putWorkbenchHeading">
      <div className="put-workbench-modal__card">
        <h2 id="putWorkbenchHeading">放入句格</h2>
        <p>將放入：<strong>{literal}</strong>（{width} 字）</p>
        <p className="put-workbench-modal__preview">目前句稿：{currentSurface || '（空白）'}</p>
        {!canInsert ? (
          <p className="put-workbench-modal__hint">
            {selectionWidth == null
              ? '工作台目前沒有選段，只能取代整句。'
              : `選段是 ${selectionWidth} 格，與放入字數不符，只能取代整句。`}
          </p>
        ) : (
          <p className="put-workbench-modal__hint">可插入到目前選段，或取代整句。</p>
        )}
        <div className="put-workbench-modal__actions">
          <button type="button" className="put-workbench-modal__primary" onClick={onReplace}>取代整句</button>
          <button type="button" disabled={!canInsert} onClick={onInsert}>插入到目前選段</button>
          <button type="button" onClick={onCancel}>取消</button>
        </div>
      </div>
    </div>
  );
}
