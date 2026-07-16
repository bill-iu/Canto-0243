/**
 * Explain IR render — port of app/services/query_explain_render.py (ADR-0021)
 */
import type {
  CodePrefixIr,
  ExplainIr,
  PositionConstraintIr,
} from './query-explain-ir.ts';

const CN_WIDTH = ['', '一', '兩', '三', '四', '五', '六', '七', '八', '九', '十'];
const RHYME_LABELS = ['', '單押', '雙押', '三押', '四押'];

export function renderExplainIr(ir: ExplainIr): string {
  switch (ir.variant) {
    case 'whole_word_equals':
      return renderWholeWordEquals(ir);
    case 'prefix_wildcard_equals':
      return renderPrefixWildcardEquals(ir);
    case 'code_sandwich_whole_word':
      return renderCodeSandwichWholeWord(ir);
    case 'code_sandwich_scan':
      return renderCodeSandwichScan(ir);
    case 'compound':
      return renderCompound(ir);
    case 'slot_scan':
      return renderSlotScan(ir);
    default:
      return widthLabel(ir.width);
  }
}

function wordPos(n: number): string {
  return `第 ${n + 1} 個字`;
}

export function widthLabel(width: number): string {
  const cn = width < CN_WIDTH.length ? CN_WIDTH[width] : String(width);
  return `${cn}個字`;
}

function rhymeLabel(n: number): string {
  return n < RHYME_LABELS.length ? RHYME_LABELS[n]! : `${n}押`;
}

function rhymeOrInitial(dimension: string): string {
  return dimension === 'final' || dimension === 'rhyme' ? '同韻' : '同聲';
}

function posListLabel(positions: number[]): string {
  if (positions.length === 1) {
    return wordPos(positions[0]!);
  }
  const nums = positions.map((p) => `第 ${p + 1}`).join('、');
  return `${nums} 個字`;
}

function renderCodePrefixPhrase(codePrefix: CodePrefixIr): string {
  if (codePrefix.per_digit_full) {
    const parts = [...codePrefix.digits].map((digit, i) => `${wordPos(i)}同 ${digit} 同音`);
    return parts.join('，');
  }
  return `前 ${codePrefix.digits.length} 個字為碼 ${codePrefix.digits}`;
}

function renderWholeWordEquals(ir: ExplainIr): string {
  const equals = ir.equals!;
  const dim = rhymeOrInitial(equals.dimension);
  const label = rhymeLabel(equals.ref_literal.length);
  const line = `整詞同「${equals.ref_literal}」${dim}（${label}）`;
  if (ir.code_prefix) {
    return `${line}；${renderCodePrefixPhrase(ir.code_prefix)}`;
  }
  return line;
}

function renderPrefixWildcardEquals(ir: ExplainIr): string {
  const equals = ir.equals!;
  const dim = rhymeOrInitial(equals.dimension);
  const label = rhymeLabel(equals.ref_literal.length);
  const positions = Array.from(
    { length: ir.width - equals.start_pos },
    (_, i) => equals.start_pos + i,
  );
  const posLabel = posListLabel(positions);
  return `首個字任意；${posLabel}同「${equals.ref_literal}」${dim}（${label}）`;
}

function renderCodeSandwichWholeWord(ir: ExplainIr): string {
  const equals = ir.equals!;
  const dim = rhymeOrInitial(equals.dimension);
  const label = rhymeLabel(equals.ref_literal.length);
  const rhymeLine = `同「${equals.ref_literal}」${dim}（${label}）`;
  const body = ir.code_prefix
    ? `${rhymeLine}；${renderCodePrefixPhrase(ir.code_prefix)}`
    : rhymeLine;
  return `數字夾字「${ir.raw_q}」：${body}`;
}

function renderConstraintPhrase(c: PositionConstraintIr): string {
  const label = wordPos(c.pos);
  if (c.kind === 'code_digit') {
    return `${label}同 ${c.digit} 同音`;
  }
  if (c.kind === 'literal_char') {
    return `${label}為「${c.char}」`;
  }
  if (c.kind === 'wildcard') {
    return `${label}任意字`;
  }
  if (c.kind === 'hybrid_tail_rhyme') {
    return `${label}同 ${c.digit} 同音且同「${c.ref}」同韻`;
  }
  if (c.kind === 'hybrid_tail_initial') {
    return `${label}同 ${c.digit} 同音且同「${c.ref}」同聲`;
  }
  if (c.kind === 'hybrid_code_literal') {
    return `${label}同 ${c.digit} 同音且限定為${c.ref}`;
  }
  if (c.kind === 'final_anchor') {
    return `${label}同「${c.ref}」同韻`;
  }
  if (c.kind === 'initial_anchor') {
    return `${label}同「${c.ref}」同聲`;
  }
  if (c.kind === 'rhyme_letters') {
    return `${label}同韻母 ${c.letters}`;
  }
  if (c.kind === 'initial_letters') {
    return `${label}同聲母 ${c.letters}`;
  }
  if (c.kind === 'syllable_letters') {
    return `${label}粵拼音節 ${c.letters}`;
  }
  return `${label}為「${c.ref ?? ''}」`;
}

function renderConstraints(constraints: PositionConstraintIr[]): string {
  return constraints.map((c) => renderConstraintPhrase(c)).join('，');
}

function renderCodeSandwichScan(ir: ExplainIr): string {
  const constraints = ir.constraints ?? [];
  if (constraints.length) {
    return `數字夾字「${ir.raw_q}」：${renderConstraints(constraints)}`;
  }
  return `數字夾字「${ir.raw_q}」`;
}

function renderCompound(ir: ExplainIr): string {
  const compound = ir.compound!;
  if (compound.kind === 'doubled_syllable') {
    const n = compound.width;
    const base = `查${n}字雙聲疊韻字（各字音節相同，聲調不限）`;
    if (compound.code && compound.tail_rhyme) {
      return `查${n}字雙聲疊韻字（碼 ${compound.code}，尾字同「${compound.tail_rhyme}」同韻）`;
    }
    if (compound.code) {
      return `查${n}字雙聲疊韻字（碼 ${compound.code}）`;
    }
    if (compound.tail_rhyme) {
      return `查${n}字雙聲疊韻字（尾字同「${compound.tail_rhyme}」同韻）`;
    }
    return base;
  }
  const label = compound.kind === 'syn' ? '近義' : '反義';
  if (compound.connective) {
    return `查詢含「${compound.connective}」嘅${label}複合詞`;
  }
  return `查詢${label}複合詞`;
}

function renderSlotScan(ir: ExplainIr): string {
  const constraints = ir.constraints ?? [];
  if (!constraints.length) {
    return widthLabel(ir.width);
  }
  return `${widthLabel(ir.width)}：${renderConstraints(constraints)}`;
}
