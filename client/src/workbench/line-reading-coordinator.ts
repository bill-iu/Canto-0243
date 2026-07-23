import { splitJyutping } from '../db/jyutping-codec.ts';
import type { LineSlot } from './line-draft.ts';
import type { PwaLineReadingChoice, PwaLineReadingSlot } from './pwa-line-readings.ts';
import type { WorkbenchAdapter } from './workbench-adapter.ts';
import { isHanSurface } from './wildcard-slot.ts';

export interface LineReadingResolution {
  version: number;
  readings: PwaLineReadingSlot[];
  autoChoices: Array<{ pos: number; choice: PwaLineReadingChoice }>;
}

function existingSlot(slot: LineSlot): PwaLineReadingSlot {
  if (!slot.reading) {
    return { surface: slot.surface, kind: 'unresolved', choices: [], needsChoice: false };
  }
  const [initials, finals] = splitJyutping(slot.reading);
  return {
    surface: slot.surface,
    kind: 'resolved',
    choices: [{
      jyutping: slot.reading,
      code: slot.code ?? '',
      initial: initials[0] ?? '',
      final: finals[0] ?? '',
    }],
    needsChoice: false,
  };
}

export class LineReadingCoordinator {
  private controller: AbortController | null = null;
  private requestId = 0;
  private readonly adapter: WorkbenchAdapter;

  constructor(adapter: WorkbenchAdapter) {
    this.adapter = adapter;
  }

  cancel(): void {
    this.requestId += 1;
    this.controller?.abort();
    this.controller = null;
  }

  async resolve(
    version: number,
    slots: LineSlot[],
    previous: PwaLineReadingSlot[] = [],
  ): Promise<LineReadingResolution> {
    this.cancel();
    const requestId = this.requestId;
    const controller = new AbortController();
    this.controller = controller;
    const positions = slots
      .map((slot, pos) => ({ slot, pos }))
      .filter(({ slot }) => isHanSurface(slot.surface) && !slot.reading);
    const resolved = positions.length
      ? await this.adapter.resolveLine(
        positions.map(({ slot }) => slot.surface).join(''),
        controller.signal,
      )
      : [];
    if (controller.signal.aborted || requestId !== this.requestId) {
      throw new DOMException('Aborted', 'AbortError');
    }

    const byPosition = new Map(positions.map(({ pos }, index) => [pos, resolved[index]]));
    const readings = slots.map((slot, pos): PwaLineReadingSlot => {
      if (!isHanSurface(slot.surface)) {
        return { surface: slot.surface || '', kind: 'punctuation', choices: [], needsChoice: false };
      }
      if (slot.reading) {
        const prior = previous[pos];
        return prior?.surface === slot.surface ? prior : existingSlot(slot);
      }
      return byPosition.get(pos) ?? existingSlot(slot);
    });
    const autoChoices = positions.flatMap(({ pos }, index) => {
      const choice = resolved[index]?.choices[0];
      return choice ? [{ pos, choice }] : [];
    });
    if (this.controller === controller) this.controller = null;
    return { version, readings, autoChoices };
  }
}
