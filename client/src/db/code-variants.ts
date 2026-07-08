/**
 * 0243 / 02493 / 394052 code variant expansion — port of app/utils/jyutping_codec.get_code_variants
 */

const M1_MAPPING: Record<string, string> = {
  '5': '4',
  '4': '5',
  '6': '2',
  '2': '6',
  '9': '3',
  '3': '9',
};

const M2_LOOSE_MAPPING: Record<string, string> = {
  '4': '5',
  '5': '4',
};

// ponytail: CONTEXT § 02493 碼 — query-only digits → stored 394052 碼
const M02493_TO_0243: Record<string, string> = {
  '1': '3',
  '5': '5',
  '6': '2',
  '7': '3',
  '8': '4',
};

export function normalize02493Code(code: string): string {
  if (!code || !/^\d+$/.test(code)) {
    return code;
  }
  return code
    .split('')
    .map((d) => M02493_TO_0243[d] ?? d)
    .join('');
}

function looseDigitOptions(digit: string, mapping: Record<string, string>): string[] {
  const mapped = mapping[digit];
  if (mapped) {
    return digit < mapped ? [digit, mapped] : [mapped, digit];
  }
  return [digit];
}

function looseMappingForMode(mode: string): Record<string, string> | null {
  if (mode === 'm1' || mode === '0243') {
    return M1_MAPPING;
  }
  if (mode === 'm2' || mode === '02493') {
    return M2_LOOSE_MAPPING;
  }
  return null;
}

/** mode: m1 / 0243 (full loose), m2 / 02493 (4↔5 only), m3 / 394052 (strict) */
export function getCodeVariants(code: string, mode: string): string[] {
  if (!code || !/^\d+$/.test(code)) {
    return [code];
  }

  const normalized = normalize02493Code(code);
  const mapping = looseMappingForMode(mode);
  if (!mapping) {
    return [normalized];
  }

  const perDigit = [...normalized].map((d) => looseDigitOptions(d, mapping));
  const combos: string[] = [];
  function walk(prefix: string, depth: number): void {
    if (depth === perDigit.length) {
      combos.push(prefix);
      return;
    }
    for (const d of perDigit[depth]!) {
      walk(prefix + d, depth + 1);
    }
  }
  walk('', 0);
  return [...new Set(combos)].sort();
}

// ponytail: self-check — fails bundle if variant logic drifts from Python
const m1_021 = new Set(getCodeVariants('021', 'm1'));
if (
  !m1_021.has('023') ||
  !m1_021.has('069') ||
  getCodeVariants('021', 'm2')[0] !== '023' ||
  !new Set(getCodeVariants('4', 'm2')).has('5') ||
  getCodeVariants('45', 'm3')[0] !== '45' ||
  !getCodeVariants('39', 'm1').includes('93')
) {
  throw new Error('code-variants self-check failed');
}