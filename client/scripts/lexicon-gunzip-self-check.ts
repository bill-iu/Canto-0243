import { shouldClientGunzip } from '../src/db/lexicon-gunzip.ts';

function fakeResponse(headers: Record<string, string>): Response {
  return { headers: { get: (k: string) => headers[k.toLowerCase()] ?? headers[k] ?? null } } as Response;
}

if (shouldClientGunzip(fakeResponse({ 'Content-Encoding': 'gzip' }), true)) {
  throw new Error('lexicon-gunzip-self-check: should skip when server already gzip');
}
if (!shouldClientGunzip(fakeResponse({}), true)) {
  throw new Error('lexicon-gunzip-self-check: should gunzip raw .gz body');
}
if (shouldClientGunzip(fakeResponse({}), false)) {
  throw new Error('lexicon-gunzip-self-check: plain db');
}

console.log('lexicon-gunzip-self-check ok');