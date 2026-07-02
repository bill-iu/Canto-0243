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

/** mode: m1 / 0243 (loose) or m2 / 02493 (strict) */
export function getCodeVariants(code: string, mode: string): string[] {
  if (!code || !/^\d+$/.test(code)) {
    return [code];
  }

  const normalized = normalize02493Code(code);
  const variants = new Set<string>([normalized]);

  if (mode === 'm1' || mode === '0243') {
    for (const [old, neu] of Object.entries(M1_MAPPING)) {
      if (normalized.includes(old)) {
        variants.add(normalized.replaceAll(old, neu));
      }
    }
    for (let i = 0; i < normalized.length; i++) {
      const digit = normalized[i];
      if (digit in M1_MAPPING) {
        variants.add(
          normalized.slice(0, i) + M1_MAPPING[digit] + normalized.slice(i + 1),
        );
      }
    }
  }

  return [...variants].sort();
}

// ponytail: self-check — fails bundle if variant logic drifts from Python
const _probe = getCodeVariants('021', 'm1');
if (!_probe.includes('023') || getCodeVariants('021', 'm2')[0] !== '023') {
  throw new Error('code-variants self-check failed');
}
