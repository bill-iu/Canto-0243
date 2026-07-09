/** Skip client gunzip when the server already decoded (e.g. Vite dev Content-Encoding: gzip). */

export function shouldClientGunzip(response: Response, requested: boolean): boolean {
  if (!requested || typeof DecompressionStream === 'undefined') return false;
  const enc = (response.headers.get('Content-Encoding') ?? '').toLowerCase();
  if (enc.includes('gzip') || enc.includes('deflate') || enc.includes('br')) {
    return false;
  }
  return true;
}

export function bodyStreamForLexiconFetch(
  response: Response,
  requestedGzip: boolean,
): ReadableStream<Uint8Array> {
  if (!response.body) {
    throw new Error('ReadableStream unavailable for lexicon fetch');
  }
  if (shouldClientGunzip(response, requestedGzip)) {
    return response.body.pipeThrough(new DecompressionStream('gzip'));
  }
  return response.body;
}