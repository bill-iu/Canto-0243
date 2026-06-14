"""接縫測試：關係補錄命令不得洩漏至 router；補錄／撤回共用骨架。"""
from __future__ import annotations

import ast
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SERVICE_PATH = REPO_ROOT / "app" / "services" / "manual_relation_service.py"
ROUTER_PATH = REPO_ROOT / "app" / "routers" / "relation.py"

FORBIDDEN_IN_ROUTER = (
    "WordRelation",
    "build_expand_plan",
    "insert_relation_candidates",
    "one_hop_syn_neighbors",
    "relation_chars_for_seed",
    "_delete_relation_row",
)

REQUIRED_IN_SERVICE = (
    "validate_manual_relation_request",
    "build_expand_plan",
    "_apply_create",
    "_apply_revoke",
)


class TestManualRelationCommandSeam(unittest.TestCase):
    def test_router_has_no_persistence_or_expand_logic(self):
        source = ROUTER_PATH.read_text(encoding="utf-8")
        for symbol in FORBIDDEN_IN_ROUTER:
            with self.subTest(symbol=symbol):
                self.assertNotIn(symbol, source)

    def test_service_exposes_command_skeleton(self):
        source = SERVICE_PATH.read_text(encoding="utf-8")
        for symbol in REQUIRED_IN_SERVICE:
            with self.subTest(symbol=symbol):
                self.assertIn(symbol, source)

    def test_create_and_revoke_delegate_to_shared_validate_and_plan(self):
        tree = ast.parse(SERVICE_PATH.read_text(encoding="utf-8"))
        bodies: dict[str, list[ast.stmt]] = {}
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name in {
                "create_creator_manual_relation",
                "revoke_creator_manual_relation",
            }:
                bodies[node.name] = node.body

        def _called_names(stmts: list[ast.stmt]) -> set[str]:
            names: set[str] = set()
            for stmt in stmts:
                for sub in ast.walk(stmt):
                    if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name):
                        names.add(sub.func.id)
            return names

        for name, body in bodies.items():
            with self.subTest(fn=name):
                calls = _called_names(body)
                self.assertIn("validate_manual_relation_request", calls)
                self.assertIn("build_expand_plan", calls)

    def test_validation_message_defined_once(self):
        source = SERVICE_PATH.read_text(encoding="utf-8")
        self.assertEqual(source.count("請填寫種子字面與對端字面"), 1)


if __name__ == "__main__":
    unittest.main()
