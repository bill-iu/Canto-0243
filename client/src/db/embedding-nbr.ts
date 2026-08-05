/**
 * Embedding neighbor CSR e1.v1 — lockstep with
 * app/domain/lexicon/embedding_nbr_codec.py
 */
export const EMBEDDING_NBR_VERSION = 'e1.v1';
export const EMBEDDING_NBR_SOURCE = 'embedding_cosine';
export const EMBEDDING_NBR_RELATION = 'semantic_related' as const;

const MAGIC = 0x52424e45; // 'ENBR' little-endian as u32... actually check bytes

export type NbrHit = { id: number; score: number };

export class EmbeddingNbrIndex {
  constructor(
    readonly heads: Uint32Array,
    readonly indptr: Uint32Array,
    readonly neighbors: Uint32Array,
    readonly scoresU16: Uint16Array,
    readonly floorMilli: number,
    readonly spanMilli: number,
  ) {}

  neighborsOf(headId: number): NbrHit[] {
    const i = lowerBound(this.heads, headId >>> 0);
    if (i >= this.heads.length || this.heads[i] !== headId) return [];
    const lo = this.indptr[i]!;
    const hi = this.indptr[i + 1]!;
    const span = this.spanMilli || 1;
    const out: NbrHit[] = [];
    for (let j = lo; j < hi; j++) {
      const q = this.scoresU16[j]!;
      const milli = this.floorMilli + (q / 65535) * span;
      out.push({ id: this.neighbors[j]!, score: milli / 1000 });
    }
    return out;
  }
}

function lowerBound(arr: Uint32Array, x: number): number {
  let lo = 0;
  let hi = arr.length;
  while (lo < hi) {
    const mid = (lo + hi) >>> 1;
    if (arr[mid]! < x) lo = mid + 1;
    else hi = mid;
  }
  return lo;
}

export function decodeEmbeddingNbrBlob(data: ArrayBuffer): EmbeddingNbrIndex {
  const view = new DataView(data);
  if (data.byteLength < 18) throw new Error('embedding nbr blob too short');
  const m0 = view.getUint8(0);
  const m1 = view.getUint8(1);
  const m2 = view.getUint8(2);
  const m3 = view.getUint8(3);
  if (m0 !== 0x45 || m1 !== 0x4e || m2 !== 0x42 || m3 !== 0x52) {
    throw new Error('bad embedding nbr magic');
  }
  let off = 4;
  const ver = view.getUint16(off, true);
  off += 2;
  if (ver !== 1) throw new Error(`unsupported nbr ver ${ver}`);
  const nHeads = view.getUint32(off, true);
  off += 4;
  const nEdges = view.getUint32(off, true);
  off += 4;
  const floorMilli = view.getUint16(off, true);
  off += 2;
  const spanMilli = view.getUint16(off, true);
  off += 2;
  const heads = new Uint32Array(nHeads);
  for (let i = 0; i < nHeads; i++) {
    heads[i] = view.getUint32(off, true);
    off += 4;
  }
  const indptr = new Uint32Array(nHeads + 1);
  for (let i = 0; i < nHeads + 1; i++) {
    indptr[i] = view.getUint32(off, true);
    off += 4;
  }
  const neighbors = new Uint32Array(nEdges);
  for (let i = 0; i < nEdges; i++) {
    neighbors[i] = view.getUint32(off, true);
    off += 4;
  }
  const scoresU16 = new Uint16Array(nEdges);
  for (let i = 0; i < nEdges; i++) {
    scoresU16[i] = view.getUint16(off, true);
    off += 2;
  }
  return new EmbeddingNbrIndex(heads, indptr, neighbors, scoresU16, floorMilli, spanMilli);
}

let globalIndex: EmbeddingNbrIndex | null = null;

export function setEmbeddingNbrIndex(idx: EmbeddingNbrIndex | null): void {
  globalIndex = idx;
}

export function getEmbeddingNbrIndex(): EmbeddingNbrIndex | null {
  return globalIndex;
}

export function clearEmbeddingNbrIndex(): void {
  globalIndex = null;
}
