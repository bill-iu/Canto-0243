import { useCallback, useRef, useState, type PointerEvent as ReactPointerEvent } from 'react';

const DRAG_THRESHOLD_PX = 6;

export interface UsePillTabDragOptions {
  tabIds: number[];
  barRef: React.RefObject<HTMLElement | null>;
  onSelect: (id: number) => void;
  onReorder: (fromIndex: number, toIndex: number) => void;
}

/** ponytail: mouse-only pill reorder; touch → Phase 10b */
export function usePillTabDrag({ tabIds, barRef, onSelect, onReorder }: UsePillTabDragOptions) {
  const dragRef = useRef<{
    id: number;
    fromIndex: number;
    startX: number;
    dragging: boolean;
  } | null>(null);
  const suppressClickRef = useRef(false);
  const [draggingId, setDraggingId] = useState<number | null>(null);
  const [overIndex, setOverIndex] = useState<number | null>(null);

  const indexFromPointer = useCallback(
    (clientX: number) => {
      const bar = barRef.current;
      if (!bar) return 0;
      const pills = [...bar.querySelectorAll<HTMLElement>('.query-tab-pill[data-tab-id]')];
      if (!pills.length) return 0;
      for (let i = 0; i < pills.length; i++) {
        const rect = pills[i].getBoundingClientRect();
        const mid = rect.left + rect.width / 2;
        if (clientX < mid) return i;
      }
      return pills.length - 1;
    },
    [barRef],
  );

  const finishDrag = useCallback(
    (event: ReactPointerEvent<HTMLButtonElement>) => {
      const d = dragRef.current;
      if (!d) return;
      if (d.dragging) {
        event.preventDefault();
        suppressClickRef.current = true;
        const toIndex = indexFromPointer(event.clientX);
        if (toIndex !== d.fromIndex) {
          onReorder(d.fromIndex, toIndex);
        }
      }
      dragRef.current = null;
      setDraggingId(null);
      setOverIndex(null);
      try {
        event.currentTarget.releasePointerCapture(event.pointerId);
      } catch {
        /* released */
      }
    },
    [indexFromPointer, onReorder],
  );

  const handlePointerDown = useCallback(
    (event: ReactPointerEvent<HTMLButtonElement>, id: number) => {
      if (event.pointerType !== 'mouse' || event.button !== 0) return;
      const fromIndex = tabIds.indexOf(id);
      if (fromIndex < 0) return;
      onSelect(id);
      dragRef.current = { id, fromIndex, startX: event.clientX, dragging: false };
      event.currentTarget.setPointerCapture(event.pointerId);
    },
    [tabIds, onSelect],
  );

  const handlePointerMove = useCallback(
    (event: ReactPointerEvent<HTMLButtonElement>) => {
      const d = dragRef.current;
      if (!d || event.pointerType !== 'mouse') return;
      if (!d.dragging && Math.abs(event.clientX - d.startX) >= DRAG_THRESHOLD_PX) {
        d.dragging = true;
        setDraggingId(d.id);
      }
      if (d.dragging) {
        setOverIndex(indexFromPointer(event.clientX));
      }
    },
    [indexFromPointer],
  );

  const handleClick = useCallback((event: React.MouseEvent<HTMLButtonElement>) => {
    if (suppressClickRef.current) {
      suppressClickRef.current = false;
      event.preventDefault();
    }
  }, []);

  return {
    draggingId,
    overIndex,
    handlePointerDown,
    handlePointerMove,
    handlePointerUp: finishDrag,
    handlePointerCancel: finishDrag,
    handleClick,
  };
}
