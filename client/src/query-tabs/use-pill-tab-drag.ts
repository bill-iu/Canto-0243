import { useCallback, useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from 'react';

/** ponytail: tune on device; Scenario G-mobile assumes 400ms */
export const LONG_PRESS_MS = 400;
const DRAG_THRESHOLD_PX = 6;
const MOVE_CANCEL_PX = 10;

type TouchPhase = 'pending' | 'cancelled' | 'armed' | 'dragging';

interface DragSession {
  id: number;
  fromIndex: number;
  startX: number;
  startY: number;
  pointerType: 'mouse' | 'touch';
  dragging: boolean;
  touchPhase?: TouchPhase;
  timerId?: ReturnType<typeof setTimeout>;
}

export interface UsePillTabDragOptions {
  tabIds: number[];
  barRef: React.RefObject<HTMLElement | null>;
  onSelect: (id: number) => void;
  onReorder: (fromIndex: number, toIndex: number) => void;
}

export function usePillTabDrag({ tabIds, barRef, onSelect, onReorder }: UsePillTabDragOptions) {
  const dragRef = useRef<DragSession | null>(null);
  const suppressClickRef = useRef(false);
  const [draggingId, setDraggingId] = useState<number | null>(null);
  const [touchArmId, setTouchArmId] = useState<number | null>(null);
  const [overIndex, setOverIndex] = useState<number | null>(null);
  const [touchDragLock, setTouchDragLock] = useState(false);

  const clearTimer = useCallback((session: DragSession | null) => {
    if (session?.timerId != null) {
      clearTimeout(session.timerId);
      session.timerId = undefined;
    }
  }, []);

  const resetTouchUi = useCallback(() => {
    setDraggingId(null);
    setTouchArmId(null);
    setOverIndex(null);
    setTouchDragLock(false);
    barRef.current?.classList.remove('query-tabs-bar--touch-drag');
  }, [barRef]);

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

      clearTimer(d);

      if (d.pointerType === 'mouse') {
        if (d.dragging) {
          event.preventDefault();
          suppressClickRef.current = true;
          const toIndex = indexFromPointer(event.clientX);
          if (toIndex !== d.fromIndex) {
            onReorder(d.fromIndex, toIndex);
          }
        }
        dragRef.current = null;
        resetTouchUi();
      } else if (d.pointerType === 'touch') {
        if (d.touchPhase === 'dragging') {
          event.preventDefault();
          suppressClickRef.current = true;
          const toIndex = indexFromPointer(event.clientX);
          if (toIndex !== d.fromIndex) {
            onReorder(d.fromIndex, toIndex);
          }
        } else if (d.touchPhase === 'pending') {
          onSelect(d.id);
        }
        dragRef.current = null;
        resetTouchUi();
      }

      try {
        event.currentTarget.releasePointerCapture(event.pointerId);
      } catch {
        /* released */
      }
    },
    [clearTimer, indexFromPointer, onReorder, onSelect, resetTouchUi],
  );

  const handlePointerDown = useCallback(
    (event: ReactPointerEvent<HTMLButtonElement>, id: number) => {
      if (event.button !== 0) return;
      const fromIndex = tabIds.indexOf(id);
      if (fromIndex < 0) return;

      if (event.pointerType === 'mouse') {
        onSelect(id);
        dragRef.current = {
          id,
          fromIndex,
          startX: event.clientX,
          startY: event.clientY,
          pointerType: 'mouse',
          dragging: false,
        };
        event.currentTarget.setPointerCapture(event.pointerId);
        return;
      }

      if (event.pointerType === 'touch') {
        clearTimer(dragRef.current);
        const session: DragSession = {
          id,
          fromIndex,
          startX: event.clientX,
          startY: event.clientY,
          pointerType: 'touch',
          dragging: false,
          touchPhase: 'pending',
        };
        session.timerId = setTimeout(() => {
          const current = dragRef.current;
          if (!current || current.id !== id || current.touchPhase !== 'pending') return;
          current.touchPhase = 'armed';
          onSelect(id);
          setTouchArmId(id);
          setTouchDragLock(true);
          barRef.current?.classList.add('query-tabs-bar--touch-drag');
        }, LONG_PRESS_MS);
        dragRef.current = session;
        event.currentTarget.setPointerCapture(event.pointerId);
      }
    },
    [tabIds, onSelect, clearTimer, barRef],
  );

  const handlePointerMove = useCallback(
    (event: ReactPointerEvent<HTMLButtonElement>) => {
      const d = dragRef.current;
      if (!d) return;

      if (d.pointerType === 'mouse') {
        if (event.pointerType !== 'mouse') return;
        if (!d.dragging && Math.abs(event.clientX - d.startX) >= DRAG_THRESHOLD_PX) {
          d.dragging = true;
          setDraggingId(d.id);
        }
        if (d.dragging) {
          setOverIndex(indexFromPointer(event.clientX));
        }
        return;
      }

      if (d.pointerType !== 'touch' || event.pointerType !== 'touch') return;

      const dx = event.clientX - d.startX;
      const dy = event.clientY - d.startY;
      const dist = Math.hypot(dx, dy);

      if (d.touchPhase === 'pending') {
        if (dist > MOVE_CANCEL_PX) {
          clearTimer(d);
          d.touchPhase = 'cancelled';
        }
        return;
      }

      if (d.touchPhase === 'armed') {
        if (Math.abs(dx) >= DRAG_THRESHOLD_PX) {
          d.touchPhase = 'dragging';
          d.dragging = true;
          setDraggingId(d.id);
        }
        return;
      }

      if (d.touchPhase === 'dragging') {
        setOverIndex(indexFromPointer(event.clientX));
      }
    },
    [clearTimer, indexFromPointer],
  );

  const handleClick = useCallback((event: React.MouseEvent<HTMLButtonElement>) => {
    if (suppressClickRef.current) {
      suppressClickRef.current = false;
      event.preventDefault();
      return;
    }
    if (event.nativeEvent instanceof PointerEvent && event.nativeEvent.pointerType === 'touch') {
      event.preventDefault();
    }
  }, []);

  useEffect(
    () => () => {
      clearTimer(dragRef.current);
    },
    [clearTimer],
  );

  return {
    draggingId,
    touchArmId,
    touchDragLock,
    overIndex,
    handlePointerDown,
    handlePointerMove,
    handlePointerUp: finishDrag,
    handlePointerCancel: finishDrag,
    handleClick,
  };
}
