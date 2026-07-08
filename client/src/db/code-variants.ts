/**
 * 0243 / 02493 code variant expansion — port of app/utils/jyutping_codec.get_code_variants
 */

const M1_MAPPING: Record<string, string> = {
  '5': '4',
  '4': '5',
  '6': '2',
  '2': '6',
  '9': '3',
  '3': '9',
};

const M02493_TO_0243: Record<string, string> = {
  '1': '3',
  '5': '4',
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

function looseDigitOptions(digit: string): string[] {
  const mapped = M1_MAPPING[digit];
  if (mapped) {
    return digit < mapped ? [digit, mapped] : [mapped, digit];
  }
  return [digit];
}

function isLooseCodeMode(mode: string): boolean {
  return mode === 'm1' || mode === '0243';
}

/** mode: m1 / 0243 (loose) or m2 / 02493 (strict) */
export function getCodeVariants(code: string, mode: string): string[] {
  if (!code || !/^\d+$/.test(code)) {
    return [code];
  }

  const normalized = normalize02493Code(code);
  if (!isLooseCodeMode(mode)) {
    return [normalized];
  }

  const perDigit = [...normalized].map((d) => looseDigitOptions(d));
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
  !getCodeVariants('39', 'm1').includes('93')
) {
  throw new Error('code-variants self-check failed');
}
