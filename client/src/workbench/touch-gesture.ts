export const TOUCH_DOUBLE_TAP_MS = 320;
export const TOUCH_POINTER_SLOP_PX = 10;

export type TouchGestureEvent =
  | { type: 'down'; pointerId: number; pos: number; x: number; y: number; at: number }
  | { type: 'move'; pointerId: number; x: number; y: number }
  | { type: 'up'; pointerId: number; pos: number; x: number; y: number; at: number }
  | { type: 'cancel'; pointerId: number };

export type TouchGestureIntent =
  | { type: 'lock'; pos: number }
  | { type: 'edit'; pos: number };

interface ActivePointer {
  pos: number;
  x: number;
  y: number;
  cancelled: boolean;
}

export interface TouchGestureState {
  active: Map<number, ActivePointer>;
  ambiguous: boolean;
  lastTap: { pos: number; at: number } | null;
}

export function createTouchGestureState(): TouchGestureState {
  return { active: new Map(), ambiguous: false, lastTap: null };
}

function clearTap(state: TouchGestureState): TouchGestureState {
  return { ...state, lastTap: null };
}

export function reduceTouchGesture(
  state: TouchGestureState,
  event: TouchGestureEvent,
): { state: TouchGestureState; intent: TouchGestureIntent | null } {
  if (event.type === 'down') {
    const active = new Map(state.active);
    const ambiguous = state.ambiguous || active.size > 0;
    active.set(event.pointerId, {
      pos: event.pos,
      x: event.x,
      y: event.y,
      cancelled: false,
    });
    return {
      state: { ...state, active, ambiguous, lastTap: ambiguous ? null : state.lastTap },
      intent: null,
    };
  }

  const pointer = state.active.get(event.pointerId);
  if (!pointer) return { state, intent: null };

  if (event.type === 'move') {
    if (pointer.cancelled) return { state, intent: null };
    if (Math.hypot(event.x - pointer.x, event.y - pointer.y) <= TOUCH_POINTER_SLOP_PX) {
      return { state, intent: null };
    }
    const active = new Map(state.active);
    active.set(event.pointerId, { ...pointer, cancelled: true });
    return { state: { ...state, active, lastTap: null }, intent: null };
  }

  const active = new Map(state.active);
  active.delete(event.pointerId);
  const noMorePointers = active.size === 0;
  const nextBase: TouchGestureState = {
    ...state,
    active,
    ambiguous: noMorePointers ? false : state.ambiguous,
  };
  if (
    event.type === 'cancel'
    || pointer.cancelled
    || event.pos !== pointer.pos
    || state.ambiguous
  ) {
    return { state: noMorePointers ? clearTap(nextBase) : nextBase, intent: null };
  }

  const isDouble = Boolean(
    state.lastTap
    && state.lastTap.pos === pointer.pos
    && event.at - state.lastTap.at <= TOUCH_DOUBLE_TAP_MS,
  );
  const nextState = {
    ...nextBase,
    lastTap: isDouble ? null : { pos: pointer.pos, at: event.at },
  };
  return {
    state: nextState,
    intent: isDouble ? { type: 'edit', pos: pointer.pos } : { type: 'lock', pos: pointer.pos },
  };
}
