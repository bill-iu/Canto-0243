const payloads = [
  { nums: '33', sess: null, mode: 'm1', category: 'all', topic: null, dicts: [] },
  { nums: '33', sess: null, mode: 'm2', category: 'all', topic: null, dicts: [] },
  { nums: ['33'], sess: null, mode: 'm1', category: 'all', topic: null, dicts: [] },
];

for (const body of payloads) {
  const res = await fetch('https://www.0243.hk/api/cls/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify(body),
  });
  const text = await res.text();
  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch {
    parsed = text.slice(0, 500);
  }
  const count = Array.isArray(parsed) ? parsed.length : parsed?.results?.length ?? parsed?.matches?.length ?? '?';
  console.log('\n===', JSON.stringify(body), '===');
  console.log('status', res.status, 'count', count);
  if (Array.isArray(parsed) && parsed.length) {
    console.log('sample', parsed.slice(0, 3));
  } else if (parsed && typeof parsed === 'object') {
    console.log('keys', Object.keys(parsed));
    for (const k of ['results', 'matches', 'words', 'items']) {
      if (Array.isArray(parsed[k])) console.log(k, 'len', parsed[k].length, 'sample', parsed[k].slice(0, 2));
    }
  } else {
    console.log(parsed);
  }
}