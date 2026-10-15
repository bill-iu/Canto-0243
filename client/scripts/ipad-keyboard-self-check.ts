import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { bindIpadSearchKeyboardGuard, isIpadStandalone } from '../src/ipad-keyboard.ts';

let checks = 0;
function check(name: string, test: () => void) {
  test();
  checks++;
  console.log(`  ok: ${name}`);
}

const ipad = { userAgent: 'Mozilla/5.0 (iPad)', platform: 'iPad', maxTouchPoints: 5 };
const desktopIpad = { userAgent: 'Mozilla/5.0 (Macintosh)', platform: 'MacIntel', maxTouchPoints: 5 };
check('iPad and desktop-UA iPad are eligible only in standalone mode', () => {
  assert.equal(isIpadStandalone(ipad, true), true);
  assert.equal(isIpadStandalone(desktopIpad, true), true);
  assert.equal(isIpadStandalone(ipad, false), false);
  assert.equal(isIpadStandalone(desktopIpad, false), false);
});
check('desktop, iPhone and Android are untouched', () => {
  assert.equal(isIpadStandalone({ ...desktopIpad, maxTouchPoints: 0 }, true), false);
  assert.equal(isIpadStandalone({ ...ipad, userAgent: 'iPhone', platform: 'iPhone' }, true), false);
  assert.equal(isIpadStandalone({ ...ipad, userAgent: 'Android', platform: 'Linux' }, true), false);
});

class Events {
  listeners = new Map<string, Set<(event: Event) => void>>();
  addEventListener(name: string, fn: (event: Event) => void) {
    if (!this.listeners.has(name)) this.listeners.set(name, new Set());
    this.listeners.get(name)!.add(fn);
  }
  removeEventListener(name: string, fn: (event: Event) => void) {
    this.listeners.get(name)?.delete(fn);
  }
  emit(name: string, target: unknown = this) {
    const event = new Event(name);
    Object.defineProperty(event, 'target', { value: target });
    for (const fn of this.listeners.get(name) ?? []) fn(event);
  }
}

function fixture() {
  const doc = Object.assign(new Events(), {
    visibilityState: 'visible',
    activeElement: null as unknown,
    querySelector: (_selector: string): unknown => field,
  });
  const win = new Events();
  let blurs = 0;
  let field: ReturnType<typeof makeField> | null;
  function makeField() {
    return {
      value: '𡁻?0243香=', disabled: false, readOnly: false,
      blur() { blurs++; doc.activeElement = null; },
      focus() { throw new Error('Guard must never restore focus automatically'); },
    };
  }
  field = makeField();
  doc.activeElement = field;
  const bind = () => bindIpadSearchKeyboardGuard(doc as unknown as Document, win as unknown as Window);
  const guard = bind();
  return { doc, win, guard, bind, makeField, get field() { return field!; },
    setField(next: typeof field) { field = next; }, get blurs() { return blurs; } };
}

check('backgrounding releases only the active search field, keeping its value', () => {
  const f = fixture();
  f.doc.visibilityState = 'hidden';
  f.doc.emit('visibilitychange');
  assert.equal(f.blurs, 1);
  assert.equal(f.field.value, '𡁻?0243香=');
  f.win.emit('pagehide');
  assert.equal(f.blurs, 1); // paired events do not blur twice
  f.guard.dispose();
});
check('pagehide releases focus even without visibilitychange', () => {
  const f = fixture();
  f.win.emit('pagehide');
  assert.equal(f.blurs, 1);
  f.guard.dispose();
});
check('visible, pageshow, resize and window blur never steal/release focus', () => {
  const f = fixture();
  f.doc.emit('visibilitychange');
  for (const event of ['pageshow', 'resize', 'blur', 'focus']) f.win.emit(event);
  assert.equal(f.blurs, 0);
  assert.equal(f.doc.activeElement, f.field);
  f.guard.dispose();
});
check('workbench/other controls are not blurred', () => {
  const f = fixture();
  const other = { blur() { throw new Error('Do not blur workbench input'); } };
  f.doc.activeElement = other;
  f.doc.visibilityState = 'hidden';
  f.doc.emit('visibilitychange');
  assert.equal(f.blurs, 0);
  assert.equal(f.doc.activeElement, other);
  f.guard.dispose();
});
check('IME composition blocks both automatic release and manual recovery', () => {
  const f = fixture();
  f.doc.emit('compositionstart', f.field);
  f.doc.visibilityState = 'hidden';
  f.doc.emit('visibilitychange');
  f.win.emit('pagehide');
  assert.equal(f.guard.release(), 'composing');
  assert.equal(f.blurs, 0);
  f.doc.emit('compositionend', f.field);
  assert.equal(f.guard.release(), 'ready');
  assert.equal(f.blurs, 1);
  assert.equal(f.field.value, '𡁻?0243香=');
  f.guard.dispose();
});
check('missing, disabled and readonly fields cannot be recovered', () => {
  const f = fixture();
  f.field.disabled = true;
  assert.equal(f.guard.release(), 'unavailable');
  f.field.disabled = false;
  f.field.readOnly = true;
  assert.equal(f.guard.release(), 'unavailable');
  f.setField(null);
  assert.equal(f.guard.release(), 'unavailable');
  assert.equal(f.blurs, 0);
  f.guard.dispose();
});
check('composition in other fields does not block search recovery', () => {
  const f = fixture();
  f.doc.emit('compositionstart', {});
  assert.equal(f.guard.release(), 'ready');
  f.guard.dispose();
});
check('an input remounted by history is not blocked by the old IME target', () => {
  const f = fixture();
  f.doc.emit('compositionstart', f.field);
  f.setField(f.makeField());
  f.doc.activeElement = f.field;
  assert.equal(f.guard.release(), 'ready');
  f.guard.dispose();
});
check('cleanup removes listeners; StrictMode rebind has no duplicate effects', () => {
  const f = fixture();
  f.guard.dispose();
  f.doc.visibilityState = 'hidden';
  f.doc.emit('visibilitychange');
  f.win.emit('pagehide');
  assert.equal(f.blurs, 0);
  const next = f.bind();
  f.doc.emit('visibilitychange');
  assert.equal(f.blurs, 1);
  next.dispose();
  for (const listeners of [...f.doc.listeners.values(), ...f.win.listeners.values()]) {
    assert.equal(listeners.size, 0);
  }
});
check('App integration keeps controlled text/history and gates recovery', () => {
  const app = readFileSync(new URL('../src/App.tsx', import.meta.url), 'utf8');
  assert.ok(app.includes('key={`${historyRestoreNonce}:${keyboardResetNonce}`}'));
  assert.ok(app.includes('value={inputQuery}'));
  assert.ok(app.includes('!isPortableHost() && isIpadStandalone(navigator, isStandalone)'));
  assert.ok(app.includes("if (result === 'ready') setKeyboardResetNonce((n) => n + 1)"));
  assert.ok(app.includes('!hasIpadKeyboardHelp || shellGated || isSearchInputBlockedByHistoryRestore()'));
});
console.log(`ipad-keyboard-self-check: ${checks} passed`);
