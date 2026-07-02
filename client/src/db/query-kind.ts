/** QueryKind enum — extracted to avoid circular imports with position-match registry */

export enum QueryKind {
  DIGIT_CODE = 'digit_code',
  WORD_LOOKUP = 'word_lookup',
  JYUTPING_FRAGMENT = 'jyutping_fragment',
  MASK = 'mask',
  RELATION_LOOKUP = 'relation_lookup',
  UNMATCHED = 'unmatched',
  COMPOUND_SYN = 'compound_syn',
  COMPOUND_ANT = 'compound_ant',
  COMPOUND_DOUBLED_SYLLABLE = 'compound_doubled_syllable',
  HYBRID_TAIL_EQUALS_ALIAS = 'hybrid_tail_equals_alias',
  EQUALS = 'equals',
  PREFIX_WILDCARD_EQUALS = 'prefix_wildcard_equals',
  PARTIAL_RHYME_MASK = 'partial_rhyme_mask',
  PARTIAL_INITIAL_MASK = 'partial_initial_mask',
  SERIAL_PHONEME = 'serial_phoneme',
  PLUS_ANCHOR = 'plus_anchor',
  WILDCARD_CODE_ANCHOR = 'wildcard_code_anchor',
  CODE_REF_MIDDLE_RHYME = 'code_ref_middle_rhyme',
  LITERAL_REF = 'literal_ref',
  RHYME_ANCHOR = 'rhyme_anchor',
  TRIPLE_RHYME_ANCHOR = 'triple_rhyme_anchor',
  JYUTPING_ANCHOR = 'jyutping_anchor',
  HYBRID_CODE = 'hybrid_code',
  HETERONYM_CODE = 'heteronym_code',
}

export enum RouteKind {
  DIGIT = 'digit',
  LOOKUP = 'lookup',
  MASK_FAMILY = 'mask_family',
  RELATION = 'relation',
  HETERONYM = 'heteronym',
  UNMATCHED = 'unmatched',
  EMPTY = 'empty',
}
