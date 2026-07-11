const body = { nums: '33', sess: null, mode: 'm1', category: 'all', topic: null, dicts: [] };
const res = await fetch('https://www.0243.hk/api/cls/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
  body: JSON.stringify(body),
});
const data = await res.json();
console.log('m1 query=33 total', data.length);
console.log('first10', data.slice(0, 10));
console.log('unique-ish sample', [...new Set(data.slice(0, 200))].length, 'in first 200');

const body2 = { ...body, mode: 'm2' };
const res2 = await fetch('https://www.0243.hk/api/cls/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
  body: JSON.stringify(body2),
});
const data2 = await res2.json();
console.log('m2 query=33 total', data2.length);
console.log('DOM batch size from bundle: 50 per scroll (pageStart + 50)');
console.log('Grid spacing: MUI spacing(2) ~= 16px');