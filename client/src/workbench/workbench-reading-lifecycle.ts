import { LineReadingCoordinator } from './line-reading-coordinator.ts';
import type { LineSlot } from './line-draft.ts';
import { isHanSurface, normalizeWildcardChar } from './wildcard-slot.ts';
import type { WorkbenchAdapter } from './workbench-adapter.ts';

function abortError(): DOMException {
  return new DOMException('Aborted', 'AbortError');
}

export function missingReferenceChars(
  refs: readonly string[],
  known: Readonly<Record<string, string>>,
): string[] {
  const result: string[] = [];
  const seen = new Set<string>();
  for (const raw of refs) {
    for (const char of Array.from(raw.trim())) {
      const normalized = normalizeWildcardChar(char);
      if (!isHanSurface(normalized) || seen.has(normalized) || known[normalized]) continue;
      seen.add(normalized);
      result.push(normalized);
    }
  }
  return result;
}

export class WorkbenchReadingLifecycle {
  readonly #adapter: WorkbenchAdapter;
  readonly #line: LineReadingCoordinator;
  #active = true;
  #references: AbortController | null = null;

  constructor(adapter: WorkbenchAdapter) {
    this.#adapter = adapter;
    this.#line = new LineReadingCoordinator(adapter);
  }

  setActive(active: boolean): void {
    this.#active = active;
    if (!active) this.cancel();
  }

  cancel(): void {
    this.#line.cancel();
    this.#references?.abort();
    this.#references = null;
  }

  async resolveLine(
    version: number,
    slots: LineSlot[],
    previous: Parameters<LineReadingCoordinator['resolve']>[2] = [],
  ): ReturnType<LineReadingCoordinator['resolve']> {
    if (!this.#active) throw abortError();
    const result = await this.#line.resolve(version, slots, previous);
    if (!this.#active) throw abortError();
    return result;
  }

  async resolveReferences(chars: readonly string[]): Promise<Record<string, string>> {
    if (!this.#active || !chars.length) return {};
    this.#references?.abort();
    const controller = new AbortController();
    this.#references = controller;
    const resolved = await this.#adapter.resolveLine(chars.join(''), controller.signal);
    if (!this.#active || controller.signal.aborted || this.#references !== controller) {
      throw abortError();
    }
    this.#references = null;
    const readings: Record<string, string> = {};
    chars.forEach((char, index) => {
      const jyutping = resolved[index]?.choices[0]?.jyutping;
      if (jyutping) readings[char] = jyutping;
    });
    return readings;
  }
}
