"""架構接縫測試（靜態契約）；registry parity 見 test_*_registry_parity。"""
from __future__ import annotations

import ast
import unittest
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# --- paths ---
INDEX_PATH = REPO_ROOT / "frontend" / "index.html"
MAIN_MJS_PATH = REPO_ROOT / "frontend" / "main.mjs"
APP_CONTEXT_PATH = REPO_ROOT / "frontend" / "app-context.mjs"
GATE_MJS_PATH = REPO_ROOT / "frontend" / "gate.mjs"
SEARCH_MJS_PATH = REPO_ROOT / "frontend" / "search-workbench.mjs"
LAYOUT_PATH = REPO_ROOT / "frontend" / "chrome-tabs-layout.js"
MAIN_PATH = REPO_ROOT / "main.py"
DISPATCH_PATH = REPO_ROOT / "app" / "services" / "query_dispatch.py"
PARSE_PATH = REPO_ROOT / "app" / "services" / "query_parse.py"
TYPES_PATH = REPO_ROOT / "app" / "services" / "query_types.py"
SOURCES_PATH = REPO_ROOT / "app" / "services" / "position_match" / "sources.py"
PRELOAD_PATH = REPO_ROOT / "app" / "startup" / "offline_preload.py"
SERVICE_PATH = REPO_ROOT / "app" / "services" / "manual_relation_service.py"
ROUTER_PATH = REPO_ROOT / "app" / "routers" / "relation.py"
LAUNCH_PATH = REPO_ROOT / "scripts" / "local_launch.py"
START_SH = REPO_ROOT / "start.sh"
START_BAT = REPO_ROOT / "portable" / "START.bat"
START_SH_PORTABLE = REPO_ROOT / "portable" / "START.sh"
MACOS_LAUNCHER = REPO_ROOT / "portable" / "macos" / "launcher"
RELATION_ENTRY_PATH = REPO_ROOT / "frontend" / "relation-entry.html"
RELATION_ENTRY_CSS_PATH = REPO_ROOT / "frontend" / "relation-entry.css"
SERVED_BASE = "http://127.0.0.1:8000/frontend"


def _fetch_served(path: str) -> str:
    url = f"{SERVED_BASE}/{path.lstrip('/')}"
    try:
        return urllib.request.urlopen(url, timeout=5).read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError) as exc:
        raise unittest.SkipTest(f"no server at {SERVED_BASE}: {exc}") from exc


class TestLocalLaunchSeam(unittest.TestCase):
    def test_local_launch_waits_html_before_browser(self):
        source = LAUNCH_PATH.read_text(encoding="utf-8")
        open_idx = source.find("webbrowser.open")
        self.assertGreater(open_idx, 0)
        before_open = source[:open_idx]
        self.assertIn("frontend/index.html", before_open)
        self.assertIn("wait_for_url.py", before_open)
        gate_idx = source.find("--gate")
        self.assertGreater(gate_idx, open_idx)

    def test_local_launch_prints_starting_first(self):
        source = LAUNCH_PATH.read_text(encoding="utf-8")
        starting_idx = source.find('msgs["starting"]')
        free_idx = source.find("free_port.py")
        self.assertGreater(starting_idx, 0)
        self.assertGreater(free_idx, starting_idx)

    def test_start_sh_delegates_to_local_launch(self):
        source = START_SH.read_text(encoding="utf-8")
        self.assertIn("local_launch.py", source)
        self.assertNotIn("wait_for_url.py", source)

    def test_portable_entries_delegate_to_local_launch(self):
        for path in (START_BAT, START_SH_PORTABLE, MACOS_LAUNCHER):
            with self.subTest(path=path.name):
                self.assertIn("local_launch.py", path.read_text(encoding="utf-8"))

    def test_main_does_not_run_main_block_startup(self):
        source = MAIN_PATH.read_text(encoding="utf-8")
        self.assertNotIn("run_main_block_startup", source)


class TestManualRelationCommandSeam(unittest.TestCase):
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

    def test_router_has_no_persistence_or_expand_logic(self):
        source = ROUTER_PATH.read_text(encoding="utf-8")
        for symbol in self.FORBIDDEN_IN_ROUTER:
            with self.subTest(symbol=symbol):
                self.assertNotIn(symbol, source)

    def test_service_exposes_command_skeleton(self):
        source = SERVICE_PATH.read_text(encoding="utf-8")
        for symbol in self.REQUIRED_IN_SERVICE:
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


class TestOfflinePreloadSeam(unittest.TestCase):
    FORBIDDEN = (
        "ensure_thesaurus_loaded",
        "ensure_lexicon_loaded",
        "ensure_rime_char_loaded",
        "ensure_essay_loaded",
        "ensure_curated_loaded",
        "ensure_compound_syn_snapshot",
        "bootstrap_local_db",
        "ensure_length_column",
        "start_word_cache_preload_background",
        "Base.metadata.create_all",
    )
    REQUIRED = (
        "run_lifespan_startup",
        "get_readiness_snapshot",
        "offline_preload",
    )

    def test_main_delegates_to_offline_preload(self):
        source = MAIN_PATH.read_text(encoding="utf-8")
        for symbol in self.FORBIDDEN:
            with self.subTest(symbol=symbol):
                self.assertNotIn(symbol, source)
        for symbol in self.REQUIRED:
            with self.subTest(symbol=symbol):
                self.assertIn(symbol, source)


class TestPoolProjectionSeam(unittest.TestCase):
    def test_runtime_services_do_not_import_build_pool(self):
        path = REPO_ROOT / "app" / "services" / "relation_syntax_executor.py"
        source = path.read_text(encoding="utf-8")
        for symbol in ("build_pool",):
            with self.subTest(symbol=symbol):
                self.assertNotIn(symbol, source)
        for symbol in ("pool_projection",):
            with self.subTest(symbol=symbol):
                self.assertIn(symbol, source)


class TestCompoundSynSeam(unittest.TestCase):
    SOURCES_FORBIDDEN = (
        "load_compound_synonyms",
        "_scan_morpheme_compounds",
        "synthesize_compound_literals",
        "build_compound_syn_snapshot",
        "ensure_compound_syn_snapshot",
        "CompoundSynSnapshot",
        "narrow_compound_syn_literals",
        "load_compound_antonyms",
    )
    SOURCES_ALLOWED = ("search_compound_syn", "search_compound_ant", "search_connective_compound")
    PRELOAD_FORBIDDEN = (
        "ensure_compound_syn_cache",
        "build_compound_syn_cache",
        "build_compound_syn_tiers",
        "search_compound_syn",
    )
    PRELOAD_ALLOWED = (
        "ensure_compound_syn_snapshot",
        "preload_compound_syn_runtime_cache",
        "ensure_compound_ant_snapshot",
        "preload_compound_ant_runtime_cache",
    )

    def test_sources_delegates_to_domain_compound_search(self):
        source = SOURCES_PATH.read_text(encoding="utf-8")
        for symbol in self.SOURCES_FORBIDDEN:
            with self.subTest(symbol=symbol):
                self.assertNotIn(symbol, source)
        for symbol in self.SOURCES_ALLOWED:
            with self.subTest(symbol=symbol):
                self.assertIn(symbol, source)

    def test_preload_only_builds_snapshot(self):
        source = PRELOAD_PATH.read_text(encoding="utf-8")
        for symbol in self.PRELOAD_FORBIDDEN:
            with self.subTest(symbol=symbol):
                self.assertNotIn(symbol, source)
        for symbol in self.PRELOAD_ALLOWED:
            with self.subTest(symbol=symbol):
                self.assertIn(symbol, source)


class TestMaskFamilyDispatchSeam(unittest.TestCase):
    FORBIDDEN = (
        "build_match_spec",
        "build_equals_match_spec",
        "execute_mask_family_search",
        "CandidateSource",
        "run_position_query",
        "run_position_query_tracked",
        "literal_priority_sort_key",
        "MaskWildcardCandidateSource",
        "LengthCodeCandidateSource",
        "LengthMaskCandidateSource",
        "RhymeAnchorCandidateSource",
        "_dispatch_position_query",
        "anchor_dimension",
        "_dual_phoneme_anchor_search_result",
    )
    ALLOWED = (
        "execute_match_spec",
        "normalize_to_match_spec",
        "_mask_family_search_result",
        "route_kind_for",
    )

    def test_query_dispatch_source_has_no_leaked_symbols(self):
        source = DISPATCH_PATH.read_text(encoding="utf-8")
        for symbol in self.FORBIDDEN:
            with self.subTest(symbol=symbol):
                self.assertNotIn(symbol, source)

    def test_query_dispatch_uses_single_mask_family_entry(self):
        source = DISPATCH_PATH.read_text(encoding="utf-8")
        for symbol in self.ALLOWED:
            with self.subTest(symbol=symbol):
                self.assertIn(symbol, source)

    def test_query_dispatch_has_no_compound_handler_registry(self):
        source = DISPATCH_PATH.read_text(encoding="utf-8")
        self.assertNotIn("CompoundSynQuery", source)
        self.assertNotIn("CompoundAntQuery", source)


class TestQueryParseTypesSeam(unittest.TestCase):
    def test_types_live_in_query_types_module(self):
        self.assertTrue(TYPES_PATH.is_file())
        types_src = TYPES_PATH.read_text(encoding="utf-8")
        self.assertIn("class QueryKind", types_src)
        self.assertIn("class MaskQuery", types_src)

    def test_query_parse_does_not_define_query_kind(self):
        src = PARSE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("class QueryKind", src)
        self.assertIn("from app.services.query_types import", src)


class TestQueryTabsSeam(unittest.TestCase):
    FRONTEND_ASSETS = (
        "chrome-tabs.css",
        "chrome-tabs-layout.js",
        "query-tabs.css",
        "query-tabs-state.mjs",
        "tab-geometry.js",
        "main.mjs",
        "app-context.mjs",
        "vendor/draggabilly.pkgd.min.js",
    )
    INDEX_REQUIRED = (
        'href="chrome-tabs.css"',
        'href="query-tabs.css"',
        'src="tab-geometry.js"',
        'src="vendor/draggabilly.pkgd.min.js"',
        'src="chrome-tabs-layout.js"',
        'src="./main.mjs"',
        'id="queryChromeTabs"',
        'id="queryTabstrip"',
        "app-header--tabs",
        "view=relation",
    )
    MAIN_MJS_REQUIRED = (
        'from "./gate.mjs"',
        "waitForPreloadReady",
        "syncViewPanels",
        "openSingletonView",
        "reorderTabsByIds",
        "setupTabDrag",
        "activateTabOnPress",
        "wireTabstripKeyboard",
        "wireModeMenuKeyboard",
        "stripLauncherBootFromUrl",
        'fetch("/ready"',
    )
    APP_CONTEXT_REQUIRED = (
        'from "./query-tabs-state.mjs"',
        "SESSION_KEY",
    )
    INDEX_FORBIDDEN = (
        "prototype-ribbon",
        "prototype-state-toggle",
        "prototype-query-tabs",
        "canto0243:prototype:query-tabs",
        "relation-entry.html",
        "relation-entry.css",
        "display=block",
        "PROTOTYPE ·",
    )
    MAIN_FORBIDDEN = (
        '@app.get("/prototype")',
        "prototype/query-tabs.html",
    )

    def test_frontend_assets_promoted_to_root(self):
        for name in self.FRONTEND_ASSETS:
            path = REPO_ROOT / "frontend" / name
            with self.subTest(asset=name):
                self.assertTrue(path.is_file(), f"missing frontend/{name}")

    def test_index_html_wires_query_tabs(self):
        source = INDEX_PATH.read_text(encoding="utf-8")
        for symbol in self.INDEX_REQUIRED:
            with self.subTest(symbol=symbol):
                self.assertIn(symbol, source)

    def test_main_mjs_wires_query_tabs(self):
        source = MAIN_MJS_PATH.read_text(encoding="utf-8")
        app_ctx = APP_CONTEXT_PATH.read_text(encoding="utf-8")
        gate = GATE_MJS_PATH.read_text(encoding="utf-8")
        tabs_ui = (REPO_ROOT / "frontend" / "tabs-ui.mjs").read_text(encoding="utf-8")
        layout = LAYOUT_PATH.read_text(encoding="utf-8")
        bundle = source + app_ctx + gate + tabs_ui + layout
        for symbol in self.MAIN_MJS_REQUIRED:
            with self.subTest(symbol=symbol):
                self.assertIn(symbol, bundle)
        for symbol in self.APP_CONTEXT_REQUIRED:
            with self.subTest(symbol=symbol):
                self.assertIn(symbol, app_ctx)
        self.assertIn("data.gate_ready", gate)
        self.assertIn("setupDraggabilly", layout)

    def test_index_html_has_no_prototype_or_relation_entry_links(self):
        source = INDEX_PATH.read_text(encoding="utf-8")
        for symbol in self.INDEX_FORBIDDEN:
            with self.subTest(symbol=symbol):
                self.assertNotIn(symbol, source)

    def test_relation_entry_page_removed(self):
        with self.subTest(path=str(RELATION_ENTRY_PATH.relative_to(REPO_ROOT))):
            self.assertFalse(RELATION_ENTRY_PATH.exists())

    def test_relation_entry_css_merged_into_index(self):
        self.assertFalse(RELATION_ENTRY_CSS_PATH.exists())
        source = INDEX_PATH.read_text(encoding="utf-8")
        self.assertIn(".relation-main", (REPO_ROOT / "frontend" / "index.css").read_text(encoding="utf-8"))
        self.assertNotIn("relation-entry.css", source)
        self.assertIn("display=swap", source)
        self.assertIn('use[filter="url(#brush-roughen-brand)"]', (REPO_ROOT / "frontend" / "index.css").read_text(encoding="utf-8"))

    def test_main_py_has_no_prototype_route(self):
        source = MAIN_PATH.read_text(encoding="utf-8")
        for symbol in self.MAIN_FORBIDDEN:
            with self.subTest(symbol=symbol):
                self.assertNotIn(symbol, source)

    def test_setup_draggabilly_relayouts_after_destroy(self):
        source = LAYOUT_PATH.read_text(encoding="utf-8")
        pattern = (
            r"(?s)"
            r"this\.draggabillies\.forEach\(\(d\) => d\.destroy\(\)\);"
            r".*?this\.layout\(\);"
            r".*?const tabEls = this\.normalTabEls"
        )
        self.assertRegex(
            source,
            pattern,
            "setupDraggabilly must call layout() after Draggabilly teardown",
        )

    def test_brand_ink_svg_symbols_dry(self):
        source = INDEX_PATH.read_text(encoding="utf-8")
        self.assertIn('id="brand-ink-blob"', source)
        self.assertIn('id="brush-roughen-brand"', source)
        self.assertIn('href="#brand-ink-blob"', source)
        ink_blob_path = "M4 55.5 C14 54.9 24 55.1 34 55.7"
        self.assertEqual(source.count(ink_blob_path), 1)
        for legacy in (
            "brush-roughen-brand-gate",
            "brush-roughen-brand-meter",
            "brush-roughen-brand-header",
        ):
            with self.subTest(filter=legacy):
                self.assertNotIn(legacy, source)

    def test_mode_menu_keyboard_wired(self):
        search = SEARCH_MJS_PATH.read_text(encoding="utf-8")
        main = MAIN_MJS_PATH.read_text(encoding="utf-8")
        self.assertIn("function wireModeMenuKeyboard", search)
        self.assertIn("ArrowDown", search)
        self.assertIn("wireModeMenuKeyboard", main)

    def test_gate_mjs_exports_public_api(self):
        source = GATE_MJS_PATH.read_text(encoding="utf-8")
        self.assertIn("export {", source)
        self.assertIn("waitForPreloadReady", source)
        self.assertNotRegex(source, r"\nlet lastReadySnapshot\s*=")

    def test_frontend_esm_modules_export_public_api(self):
        exports_required = {
            "relation-form.mjs": ("relationPayloadFromForm", "postRelation"),
            "tabs-core.mjs": ("activeTab", "persistTabs"),
            "tabs-ui.mjs": ("renderTabstrip", "showSearch"),
            "view-sync.mjs": ("syncViewPanels",),
            "search-workbench.mjs": ("searchDict", "toggleMenu"),
        }
        frontend = REPO_ROOT / "frontend"
        for name, symbols in exports_required.items():
            source = (frontend / name).read_text(encoding="utf-8")
            with self.subTest(module=name):
                self.assertIn("export {", source)
                for symbol in symbols:
                    self.assertIn(symbol, source)


class TestGateFrontendSeam(unittest.TestCase):
    FORBIDDEN = (
        "canOpenSearchGate",
        "PRELOAD_TIMEOUT",
        "budget_ms",
        "budget_active",
        "pauseBudget",
        "resumeBudget",
        "data.ready ||",
    )
    REQUIRED = (
        "data.gate_ready",
        "data.degraded",
        "formatGateStatusLabel",
        'fetch("/ready"',
        "仲未開得工",
    )

    def test_index_html_has_no_client_gate_policy(self):
        source = INDEX_PATH.read_text(encoding="utf-8")
        for symbol in self.FORBIDDEN:
            with self.subTest(symbol=symbol):
                self.assertNotIn(symbol, source)

    def test_gate_ink_clip_constant_in_app_context(self):
        source = APP_CONTEXT_PATH.read_text(encoding="utf-8")
        self.assertIn("GATE_INK_CLIP_MAX = 200", source)

    def test_index_html_uses_server_gate_contract(self):
        gate = GATE_MJS_PATH.read_text(encoding="utf-8")
        search = SEARCH_MJS_PATH.read_text(encoding="utf-8")
        bundle = gate + search
        for symbol in self.REQUIRED:
            with self.subTest(symbol=symbol):
                self.assertIn(symbol, bundle)
        self.assertIn('src="./main.mjs"', INDEX_PATH.read_text(encoding="utf-8"))

    def test_served_frontend_gate_modules_match_disk(self):
        html = _fetch_served("index.html?boot=test-ink")
        self.assertIn('src="./main.mjs"', html)
        ctx = _fetch_served("app-context.mjs")
        gate = _fetch_served("gate.mjs")
        self.assertIn("GATE_INK_CLIP_MAX = 200", ctx)
        self.assertIn("data.gate_ready", gate)


if __name__ == "__main__":
    unittest.main()
