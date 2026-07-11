import {
  mergeResultsByLiteral,
  resolveListClickAction,
  code0243FromJyutping,
  buildEntryDetailModel,
  buildEntryDetailModelFromPick,
} from '../../frontend/entry-detail-core.mjs';

const rows = [
  { word: '就', jyutping: 'zau6', code: '42' },
  { word: '就', jyutping: 'zau2', code: '69' },
  { word: '香港', jyutping: 'hoeng1 gong2', code: '39' },
];

const merged = mergeResultsByLiteral(rows);
if (merged.length !== 2 || merged[0].readingCount !== 2) {
  throw new Error('mergeResultsByLiteral');
}

if (resolveListClickAction({ panelOpen: true, activeLiteral: '就', targetLiteral: '香港' }) !== 'close') {
  throw new Error('resolveListClickAction');
}

if (code0243FromJyutping('hoeng1 gong2') !== '39') {
  throw new Error('code0243FromJyutping');
}

const model = buildEntryDetailModel({
  literal: '香港',
  length: 2,
  corpusWeight: 100,
  readings: [{ jyutping: 'hoeng1 gong2', code: '39', initials: '["h","g"]', finals: '["oeng","ong"]' }],
  syns: [],
  ants: [],
});

if (model.readings[0]?.initials.join(' ') !== 'h g') {
  throw new Error('buildEntryDetailModel phonetic');
}

const compactModel = buildEntryDetailModel({
  literal: '香港',
  length: 2,
  corpusWeight: 100,
  readings: [{ jyutping: 'hoeng1 gong2', code: '39', initials: '10.8', finals: '43.48' }],
  syns: [],
  ants: [],
});
if (compactModel.readings[0]?.initials.join(' ') !== 'h g') {
  throw new Error('buildEntryDetailModel compact initials');
}
if (compactModel.readings[0]?.finals.join(' ') !== 'oeng ong') {
  throw new Error('buildEntryDetailModel compact finals');
}

const instant = buildEntryDetailModelFromPick('香港', [{ jyutping: 'hoeng1 gong2', code: '39' }]);
if (instant?.readings[0]?.code0243 !== '39') {
  throw new Error('buildEntryDetailModelFromPick');
}

console.log('entry-detail-core self-check ok');