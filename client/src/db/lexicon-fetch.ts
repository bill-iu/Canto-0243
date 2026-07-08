/** 詞庫下載（含 gzip 解壓 + 閘前進度） */

import { bodyStreamForLexiconFetch } from './lexicon-gunzip.ts';
import { reportDownloadBytes } from './startup-progress.ts';

async function readStreamToBytes(
  body: ReadableStream<Uint8Array>,
  progressTotal: number,
): Promise<Uint8Array> {
  const reader = body.getReader();
  const chunks: Uint8Array[] = [];
  let loaded = 0;
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    if (value?.byteLength) {
      chunks.push(value);
      loaded += value.byteLength;
      reportDownloadBytes(loaded, progressTotal || loaded);
    }
  }
  const out = new Uint8Array(loaded);
  let offset = 0;
  for (const chunk of chunks) {
    out.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return out;
}

export async function fetchLexiconBytesFromUrl(
  fetchUrl: string,
  opts?: { gzip?: boolean; progressTotal?: number },
): Promise<Uint8Array> {
  const response = await fetch(fetchUrl);
  if (!response.ok) {
    throw new Error(`Failed to fetch lexicon package (${response.status})`);
  }
  const progressTotal =
    opts?.progressTotal && opts.progressTotal > 0
      ? opts.progressTotal
      : Number(response.headers.get('Content-Length')) || 0;

  const body = bodyStreamForLexiconFetch(response, Boolean(opts?.gzip));
  return readStreamToBytes(body, progressTotal);
}