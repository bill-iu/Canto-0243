"""ADR-0039: leaf group_codes + undirected syn cap@20."""
from __future__ import annotations

import unittest

from app.domain.relations.cilin_codes import (
    expand_group_codes_field,
    leaf_code_to_hierarchy_codes,
)
from app.domain.relations.degree_cap import SYN_NEIGHBOR_CAP, cap_undirected_syn_tuples
from app.domain.relation_pool.ranking import parse_group_codes


class CilinCodesTests(unittest.TestCase):
    def test_leaf_expand(self):
        h = leaf_code_to_hierarchy_codes("Aa01A01=")
        self.assertEqual(h[0], "A")
        self.assertEqual(h[-1], "Aa01A01=")

    def test_expand_field_leaf_and_json(self):
        leaf = "Aa01A01="
        self.assertEqual(expand_group_codes_field(leaf), leaf_code_to_hierarchy_codes(leaf))
        import json

        full = json.dumps(leaf_code_to_hierarchy_codes(leaf), ensure_ascii=False)
        self.assertEqual(expand_group_codes_field(full)[-1], leaf)

    def test_parse_group_codes_ranking(self):
        codes = parse_group_codes("Aa01A01=")
        self.assertEqual(codes[-1], "Aa01A01=")
        self.assertGreaterEqual(len(codes), 2)


class DegreeCapTests(unittest.TestCase):
    def test_cap_keeps_ants(self):
        rows = [
            (1, 2, "syn", 0.9, "cilin", "Aa01A01="),
            (1, 3, "ant", 0.9, "guotong", None),
        ]
        out = cap_undirected_syn_tuples(rows, k=20)
        self.assertTrue(any(r[2] == "ant" for r in out))

    def test_cap_limits_degree(self):
        # star: 0 connected to 1..30 with decreasing score
        rows = [(0, i, "syn", 1.0 - i * 0.01, "cilin", None) for i in range(1, 31)]
        out = cap_undirected_syn_tuples(rows, k=SYN_NEIGHBOR_CAP)
        syn = [r for r in out if r[2] == "syn"]
        self.assertEqual(len(syn), SYN_NEIGHBOR_CAP)
        # highest scores kept
        related = {r[1] for r in syn}
        self.assertEqual(related, set(range(1, SYN_NEIGHBOR_CAP + 1)))


if __name__ == "__main__":
    unittest.main()
