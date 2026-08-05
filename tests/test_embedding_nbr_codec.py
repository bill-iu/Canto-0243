"""Unit: embedding nbr CSR e1.v1 roundtrip."""
from app.domain.lexicon.embedding_nbr_codec import (
    NBR_VERSION,
    build_bidirectional_adj,
    decode_csr_blob,
    encode_csr_blob,
    score_to_u16,
    u16_to_score,
)


def test_score_quantize_roundtrip():
    for s in (0.5, 0.55, 0.77, 0.99, 1.0):
        q = score_to_u16(s)
        back = u16_to_score(q)
        assert abs(back - s) < 0.002


def test_csr_bidirectional_roundtrip():
    edges = [(10, 20, 0.91), (10, 30, 0.7), (40, 10, 0.85)]
    adj = build_bidirectional_adj(edges)
    blob = encode_csr_blob(adj)
    idx = decode_csr_blob(blob)
    n10 = {nid: sc for nid, sc in idx.neighbors_of(10)}
    assert 20 in n10 and 30 in n10 and 40 in n10
    assert abs(n10[20] - 0.91) < 0.01
    n20 = dict(idx.neighbors_of(20))
    assert 10 in n20
    assert NBR_VERSION == "e1.v1"
