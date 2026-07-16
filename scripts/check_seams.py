#!/usr/bin/env python3
"""架構接縫靜態檢查（CI 第二步；唔計入 unittest discover）。"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ast
import json
import unittest
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# --- paths ---
INDEX_PATH = REPO_ROOT / "frontend" / "index.html"
READY_GATE_CSS_PATH = REPO_ROOT / "frontend" / "ready-gate.css"
CLIENT_INDEX_PATH = REPO_ROOT / "client" / "index.html"
PWA_BOOT_GATE_CSS_PATH = REPO_ROOT / "client" / "public" / "pwa-boot-gate.css"
CLIENT_FONT_BUILD_PATH = REPO_ROOT / "client" / "scripts" / "build-fonts.ts"
BRAND_SVG_DEFS_PATH = REPO_ROOT / "client" / "src" / "brand-svg-defs.tsx"
PAGES_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "pages.yml"
RELEASE_WINDOWS_PATH = REPO_ROOT / "scripts" / "release-windows-local.ps1"
RELEASE_MACOS_PATH = REPO_ROOT / "scripts" / "release-macos-local.sh"
APP_CONTEXT_PATH = REPO_ROOT / "frontend" / "app-context.mjs"
LAYOUT_PATH = REPO_ROOT / "frontend" / "chrome-tabs-layout.mjs"
CLIENT_APP_PATH = REPO_ROOT / "client" / "src" / "App.tsx"
PORTABLE_READY_PATH = REPO_ROOT / "client" / "src" / "hooks" / "use-portable-ready.ts"
PORTABLE_EXIT_PATH = REPO_ROOT / "client" / "src" / "portable-exit.ts"
CHROME_TABS_BAR_PATH = REPO_ROOT / "client" / "src" / "query-tabs" / "chrome-tabs-bar.tsx"
READINESS_GATE_PATH = REPO_ROOT / "app" / "startup" / "readiness_gate.py"
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
        self.assertIn('HTML_SUFFIX = "/app/index.html"', source)
        self.assertIn("/app/index.html", before_open)
        self.assertIn("wait_for_url.py", before_open)
        gate_idx = source.find("--gate")
        self.assertGreater(gate_idx, open_idx)

    def test_local_launch_prints_starting_first(self):
        source = LAUNCH_PATH.read_text(encoding="utf-8")
        starting_idx = source.find('msgs["starting"]')
        free_idx = source.find("free_port.py")
        self.assertGreater(starting_idx, 0)
        self.assertGreater(free_idx, starting_idx)

    def test_local_launch_ensures_app_ui_before_server(self):
        source = LAUNCH_PATH.read_text(encoding="utf-8")
        ensure_idx = source.find("ensure_app_ui(")
        main_py_idx = source.find('["main.py"]')
        self.assertGreater(ensure_idx, 0)
        self.assertGreater(main_py_idx, ensure_idx)
        self.assertIn("client/dist-portable", source)
        start_sh = (REPO_ROOT / "start.sh").read_text(encoding="utf-8")
        self.assertIn("dist-portable/index.html", start_sh)

    def test_start_sh_delegates_to_local_launch(self):
        source = START_SH.read_text(encoding="utf-8")
        self.assertIn("local_launch.py", source)
        self.assertNotIn("wait_for_url.py", source)

    def test_portable_entries_delegate_to_local_launch(self):
        for path in (START_BAT, START_SH_PORTABLE, MACOS_LAUNCHER):
            with self.subTest(path=path.name):
                self.assertIn("local_launch.py", path.read_text(encoding="utf-8"))

    def test_macos_launcher_clears_download_quarantine(self):
        source = MACOS_LAUNCHER.read_text(encoding="utf-8")
        self.assertIn("portable_macos.py", source)

    def test_build_portable_macos_tar_is_arch_specific(self):
        source = (REPO_ROOT / "scripts" / "build-portable.sh").read_text(encoding="utf-8")
        self.assertIn('canto-0243-portable-macos-${MAC_ARCH}.tar.gz', source)
        self.assertNotIn("canto-0243-portable-macos.tar.gz", source)

    def test_build_portable_warms_word_cache(self):
        source = (REPO_ROOT / "scripts" / "build-portable.sh").read_text(encoding="utf-8")
        self.assertIn("warm_word_cache.py", source)
        ps1 = (REPO_ROOT / "scripts" / "build-portable.ps1").read_text(encoding="utf-8")
        self.assertIn("warm_word_cache.py", ps1)
        self.assertIn("PyInstaller", ps1)
        self.assertIn("Canto-0243.exe", ps1)

    def test_portable_win_launcher_exists(self):
        path = REPO_ROOT / "scripts" / "portable_win_launcher.py"
        source = path.read_text(encoding="utf-8")
        self.assertIn("local_launch.py", source)
        self.assertIn("--gui", source)
        self.assertIn("_ensure_env_local", source)
        self.assertIn("_patch_pyvenv_home", source)
        self.assertIn("python-home", source)
        self.assertIn("查韻介面未能啟動", source)

    def test_portable_win_start_bat_patches_pyvenv_home(self):
        source = START_BAT.read_text(encoding="utf-8")
        self.assertIn("python-home", source)
        self.assertIn("pyvenv.cfg", source)
        self.assertIn("home = ", source)

    def test_portable_venv_materializes_windows_runtime(self):
        source = (REPO_ROOT / "scripts" / "portable_venv.py").read_text(encoding="utf-8")
        self.assertIn("materialize_windows_python_home", source)
        self.assertIn("_assert_cfg_home_local", source)
        self.assertIn("base_prefix", source)
        win_rt = (REPO_ROOT / "scripts" / "portable_win_runtime.py").read_text(encoding="utf-8")
        self.assertIn("python-home", win_rt)
        self.assertIn("materialize_windows_python_home", win_rt)

    def test_main_exposes_portable_shutdown(self):
        source = MAIN_PATH.read_text(encoding="utf-8")
        self.assertIn('"/shutdown"', source)
        self.assertIn("PORTABLE", source)
        self.assertIn("serve_app_index", source)
        self.assertIn('"/app/index.html"', source)
        self.assertIn('name="canto-portable"', source)

    def test_ready_includes_portable_flag(self):
        source = MAIN_PATH.read_text(encoding="utf-8")
        self.assertIn('snap["portable"]', source)

    def test_portable_host_menu_plus_exit(self):
        """Product chrome lives in client; frontend/index.html is only a /app redirect stub."""
        app = CLIENT_APP_PATH.read_text(encoding="utf-8")
        menu = (REPO_ROOT / "client" / "src" / "mode-menu.tsx").read_text(encoding="utf-8")
        exit_src = PORTABLE_EXIT_PATH.read_text(encoding="utf-8")
        stub = INDEX_PATH.read_text(encoding="utf-8")
        self.assertIn('id="portableExitBtn"', menu)
        self.assertIn("onExitPortable", app)
        self.assertIn("header-chrome__actions", app)
        self.assertIn("exitPortable", app)
        self.assertIn("onOpenAbout", menu)
        self.assertIn('fetch("/shutdown"', exit_src)
        self.assertIn('location.replace("/app/")', stub)
        self.assertNotIn('src="./main.mjs"', stub)
        self.assertIn("!isPortableHost() && isReady && getActiveDbBackendMode()", app)
        self.assertIn("!isPortableHost() && !shellGated", app)

    def test_local_launch_supports_gui_reuse(self):
        source = LAUNCH_PATH.read_text(encoding="utf-8")
        self.assertIn("--gui", source)
        self.assertIn("_html_ready", source)
        self.assertIn("_probe_home_portable", source)
        self.assertIn('_spawn_detached(python, root, ["main.py"]', source)
        self.assertIn("return 0 if html_ready else 1", source)

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


class TestTransitionFacadeRemoval(unittest.TestCase):
    """#3: shallow pass-through modules removed; callers use real modules."""

    REMOVED = (
        REPO_ROOT / "app" / "services" / "query_route_registry.py",
        REPO_ROOT / "app" / "services" / "word_query_parser.py",
        REPO_ROOT / "app" / "domain" / "relations" / "pool_chars.py",
        REPO_ROOT / "ingest" / "relation_canonical.py",
    )

    def test_shallow_facade_files_removed(self):
        for path in self.REMOVED:
            with self.subTest(path=path.name):
                self.assertFalse(path.is_file(), f"facade still present: {path}")

    def test_query_dispatch_imports_query_kind_registry(self):
        source = DISPATCH_PATH.read_text(encoding="utf-8")
        self.assertIn("query_kind_registry", source)
        self.assertNotIn("query_route_registry", source)


class TestWordSerializerReexport(unittest.TestCase):
    def test_getters_reexport_word_row(self):
        from app.domain.lexicon import word_row
        from app.services import word_serializer

        self.assertIs(word_serializer.get_word_text, word_row.get_word_text)
        self.assertIs(word_serializer.get_word_jyutping, word_row.get_word_jyutping)
        self.assertIs(word_serializer.get_rhyme_finals, word_row.get_rhyme_finals)
        self.assertIs(word_serializer.get_word_parts, word_row.get_word_parts)


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
        "normalize_to_match_spec",
    )
    ALLOWED = (
        "execute_match_spec",
        "build_match_spec_for_parsed",
        "dispatch_parsed",
        "_mask_family_search_result",
        "route_kind_for",
    )

    def test_query_dispatch_source_has_no_leaked_symbols(self):
        source = DISPATCH_PATH.read_text(encoding="utf-8")
        for symbol in self.FORBIDDEN:
            with self.subTest(symbol=symbol):
                self.assertNotIn(symbol, source)
        self.assertNotIn("def build_match_spec(", source)

    def test_query_dispatch_uses_single_mask_family_entry(self):
        source = DISPATCH_PATH.read_text(encoding="utf-8")
        for symbol in self.ALLOWED:
            with self.subTest(symbol=symbol):
                self.assertIn(symbol, source)

    def test_query_dispatch_has_no_compound_handler_registry(self):
        source = DISPATCH_PATH.read_text(encoding="utf-8")
        self.assertNotIn("CompoundSynQuery", source)
        self.assertNotIn("CompoundAntQuery", source)


class TestPwaQueryDispatchSeam(unittest.TestCase):
    """PWA dispatch routes only — search entry is query/engine.ts."""

    PWA_DISPATCH = REPO_ROOT / "client" / "src" / "db" / "query" / "dispatch.ts"
    PWA_ENGINE = REPO_ROOT / "client" / "src" / "db" / "query" / "engine.ts"

    def test_dispatch_has_no_shadow_execute_search(self):
        source = self.PWA_DISPATCH.read_text(encoding="utf-8")
        self.assertNotIn("export async function executeSearch", source)
        self.assertNotIn("export function executeSearch", source)
        self.assertIn("export async function dispatchParsed", source)
        self.assertIn("export async function executeListFilter", source)

    def test_engine_owns_execute_search(self):
        source = self.PWA_ENGINE.read_text(encoding="utf-8")
        self.assertIn("export async function executeSearch", source)
        self.assertIn("class QueryEngine", source)


class TestSynAntIngestModulesSeam(unittest.TestCase):
    """#6: syn_ant_merge removed; direct / build / expand split by command."""

    DIRECT_PATH = REPO_ROOT / "ingest" / "syn_ant_direct.py"
    BUILD_PATH = REPO_ROOT / "ingest" / "syn_ant_build.py"
    WORD_REL_BUILD_PATH = REPO_ROOT / "ingest" / "word_relations_build.py"
    EXPAND_PATH = REPO_ROOT / "ingest" / "syn_ant_expand.py"
    MERGE_PATH = REPO_ROOT / "ingest" / "syn_ant_merge.py"
    STAGING_PATH = REPO_ROOT / "ingest" / "syn_ant_staging.py"

    def test_syn_ant_merge_removed(self):
        self.assertFalse(self.MERGE_PATH.is_file())

    def test_staging_module_removed(self):
        self.assertFalse(self.STAGING_PATH.is_file())

    def test_direct_module_boundary(self):
        source = self.DIRECT_PATH.read_text(encoding="utf-8")
        self.assertIn("def ingest_static_relations", source)
        self.assertIn("def ingest_flat_char_edges", source)
        self.assertNotIn("def persist_staging_edges", source)
        self.assertNotIn("expand_antonyms_via_", source)

    def test_word_relations_build_module_boundary(self):
        source = self.WORD_REL_BUILD_PATH.read_text(encoding="utf-8")
        self.assertIn("def build_word_relations", source)
        self.assertIn("insert_relation_records", source)
        self.assertNotIn("bulk_insert_word_relations", source)
        self.assertNotIn("fetch_existing_relation_keys", source)

    def test_ingest_write_modules_use_store_not_bulk(self):
        paths = [
            self.DIRECT_PATH,
            self.BUILD_PATH,
            self.WORD_REL_BUILD_PATH,
            self.EXPAND_PATH,
            REPO_ROOT / "ingest" / "compound_antonyms.py",
            REPO_ROOT / "ingest" / "derived_ant_snapshot.py",
            REPO_ROOT / "ingest" / "bridge_snapshot.py",
        ]
        store_path = REPO_ROOT / "app" / "domain" / "relations" / "store.py"
        store_source = store_path.read_text(encoding="utf-8")
        self.assertIn("bulk_insert_word_relations", store_source)
        for path in paths:
            with self.subTest(path=path.name):
                source = path.read_text(encoding="utf-8")
                self.assertNotIn("bulk_insert_word_relations", source)
                self.assertNotIn("fetch_existing_relation_keys", source)

    def test_build_module_boundary(self):
        source = self.BUILD_PATH.read_text(encoding="utf-8")
        self.assertIn("def ingest_cilin_leaf_direct", source)
        self.assertIn("def clear_word_relations_source", source)
        self.assertNotIn("def persist_staging_edges", source)
        self.assertNotIn("def build_word_relations_from_staging", source)
        self.assertNotIn("expand_antonyms_via_", source)

    def test_expand_module_boundary(self):
        source = self.EXPAND_PATH.read_text(encoding="utf-8")
        self.assertIn("def expand_antonyms_via_cilin_synonyms", source)
        self.assertNotIn("def persist_staging_edges", source)
        self.assertNotIn("def build_word_relations_from_staging", source)

    def test_release_hot_path_is_build_word_relations(self):
        """P2 #6: build-db + legacy ingest-cilin CLI use 關係直寫 only."""
        cli = (REPO_ROOT / "ingest" / "cli.py").read_text(encoding="utf-8")
        self.assertIn('("build-word-relations"', cli)
        # ingest-cilin must delegate, not call leaf_direct
        self.assertIn("def cmd_ingest_cilin", cli)
        self.assertIn("cmd_build_word_relations", cli)
        # body of cmd_ingest_cilin should not invoke direct writer
        start = cli.index("def cmd_ingest_cilin")
        end = cli.index("\ndef cmd_", start + 1)
        body = cli[start:end]
        self.assertIn("cmd_build_word_relations", body)
        self.assertNotIn("ingest_cilin_leaf_direct", body)
        self.assertIn("def build_word_relations", self.WORD_REL_BUILD_PATH.read_text(encoding="utf-8"))


class TestQueryModeDispatchSeam(unittest.TestCase):
    """#4: syn-mode branches live in query_mode_dispatch, not nested in execute."""

    def test_query_dispatch_delegates_syn_mode(self):
        source = DISPATCH_PATH.read_text(encoding="utf-8")
        self.assertIn("dispatch_syn_mode", source)
        self.assertNotIn("syn_mode_page", source)
        self.assertNotIn("is_relation_syntax_query", source)
        self.assertNotIn("is_jyutping_query", source)

    def test_query_mode_dispatch_module_exists(self):
        path = REPO_ROOT / "app" / "services" / "query_mode_dispatch.py"
        self.assertTrue(path.is_file())


class TestQueryParseTypesSeam(unittest.TestCase):
    def test_types_live_in_query_types_module(self):
        self.assertTrue(TYPES_PATH.is_file())
        types_src = TYPES_PATH.read_text(encoding="utf-8")
        # QueryKind SSOT is codegen (ADR-0035); query_types re-exports via import
        self.assertIn("QueryKind", types_src)
        self.assertIn("class MaskQuery", types_src)
        gen = REPO_ROOT / "app" / "services" / "_generated" / "query_kind_registry.py"
        self.assertTrue(gen.is_file())
        self.assertIn("class QueryKind", gen.read_text(encoding="utf-8"))

    def test_query_parse_does_not_define_query_kind(self):
        src = PARSE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("class QueryKind", src)
        self.assertIn("from app.services.query_types import", src)

    def test_query_kind_codegen_clean(self):
        import subprocess

        script = REPO_ROOT / "scripts" / "codegen_query_kind_manifest.py"
        proc = subprocess.run(
            [sys.executable, str(script), "--check"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)

    def test_query_mode_detect_codegen_clean(self):
        import subprocess

        script = REPO_ROOT / "scripts" / "codegen_query_mode_detect.py"
        proc = subprocess.run(
            [sys.executable, str(script), "--check"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)

    def test_fillword_connectives_codegen_clean(self):
        import subprocess

        script = REPO_ROOT / "scripts" / "codegen_fillword_connectives.py"
        proc = subprocess.run(
            [sys.executable, str(script), "--check"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)

    def test_candidate_source_policy_codegen_clean(self):
        import subprocess

        script = REPO_ROOT / "scripts" / "codegen_candidate_source_policy.py"
        proc = subprocess.run(
            [sys.executable, str(script), "--check"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)

    def test_relation_pool_ranking_codegen_clean(self):
        import subprocess

        script = REPO_ROOT / "scripts" / "codegen_relation_pool_ranking.py"
        proc = subprocess.run(
            [sys.executable, str(script), "--check"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)

    def test_candidate_fallback_limit_not_hand_copied(self):
        """P3 #7: 2000 only from contract/generated (+ docs)."""
        allow = {
            REPO_ROOT / "contracts" / "candidate-source-policy.json",
            REPO_ROOT / "app" / "services" / "_generated" / "candidate_source_policy.py",
            REPO_ROOT / "client" / "src" / "db" / "_generated" / "candidate-source-policy.ts",
            REPO_ROOT / "scripts" / "codegen_candidate_source_policy.py",
        }
        # Literal LIMIT 2000 / = 2000 in sources is forbidden outside allowlist
        roots = [
            REPO_ROOT / "app" / "services" / "position_match",
            REPO_ROOT / "client" / "src" / "db" / "position-match",
        ]
        hits: list[str] = []
        for root in roots:
            if not root.is_dir():
                continue
            for path in root.rglob("*"):
                if not path.is_file() or path.suffix not in {".py", ".ts"}:
                    continue
                if path in allow:
                    continue
                text = path.read_text(encoding="utf-8")
                if "CANDIDATE_FALLBACK_LIMIT = 2000" in text or "LIMIT 2000" in text:
                    hits.append(str(path.relative_to(REPO_ROOT)))
        self.assertEqual(hits, [], msg=f"hand-copied fallback limit: {hits}")

    def test_fillword_alphabet_not_hand_copied(self):
        """P1 #1: alphabet only in contract + generated + mode-detect inline."""
        alphabet = "與和或共同及跟而且並向"
        allow = {
            REPO_ROOT / "contracts" / "fillword-connectives.json",
            REPO_ROOT / "app" / "services" / "_generated" / "fillword_connectives.py",
            REPO_ROOT / "client" / "src" / "db" / "_generated" / "fillword-connectives.ts",
            REPO_ROOT / "client" / "src" / "db" / "query" / "mode-detect.ts",
            REPO_ROOT / "frontend" / "query-mode-detect.mjs",
            REPO_ROOT / "scripts" / "codegen_fillword_connectives.py",
        }
        roots = [
            REPO_ROOT / "app",
            REPO_ROOT / "client" / "src",
            REPO_ROOT / "frontend",
            REPO_ROOT / "ingest",
        ]
        hits: list[str] = []
        for root in roots:
            if not root.is_dir():
                continue
            for path in root.rglob("*"):
                if not path.is_file():
                    continue
                if path.suffix not in {".py", ".ts", ".tsx", ".mjs", ".js", ".json"}:
                    continue
                if "node_modules" in path.parts or "__pycache__" in path.parts:
                    continue
                if path in allow:
                    continue
                try:
                    text = path.read_text(encoding="utf-8")
                except OSError:
                    continue
                if alphabet in text:
                    hits.append(str(path.relative_to(REPO_ROOT)))
        self.assertEqual(hits, [], msg=f"hand-copied FILLWORD alphabet: {hits}")

    def test_relation_syntax_detect_cases_contract(self):
        """P1 #3: shared detect case table exists and is non-empty."""
        path = REPO_ROOT / "contracts" / "relation-syntax-detect-cases.json"
        self.assertTrue(path.is_file())
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertIsInstance(data.get("relation"), list)
        self.assertIsInstance(data.get("ping_ze"), list)
        self.assertGreaterEqual(len(data["relation"]), 20)
        self.assertGreaterEqual(len(data["ping_ze"]), 5)
        smoke = REPO_ROOT / "tests" / "smoke" / "test_mode_detect_parity.py"
        self.assertTrue(smoke.is_file())
        src = smoke.read_text(encoding="utf-8")
        self.assertIn("relation-syntax-detect-cases.json", src)
        self.assertNotIn('CASES_RELATION = [', src)

    def test_pwa_query_grammar_mirrors_python_families(self):
        """P1 #2: PWA parse split into grammar/* families (mirror query_grammar)."""
        grammar = REPO_ROOT / "client" / "src" / "db" / "query" / "grammar"
        for name in (
            "shared.ts",
            "normalize.ts",
            "equals.ts",
            "heteronym.ts",
            "relation.ts",
            "rhyme.ts",
            "wca.ts",
            "serial.ts",
            "plus.ts",
            "mask.ts",
            "index.ts",
        ):
            with self.subTest(file=name):
                self.assertTrue((grammar / name).is_file(), msg=f"missing {name}")
        parse_ts = REPO_ROOT / "client" / "src" / "db" / "query" / "parse.ts"
        parse_src = parse_ts.read_text(encoding="utf-8")
        self.assertIn("tryParseBeforeMask", parse_src)
        self.assertIn("./grammar/index.ts", parse_src)
        # thin entry — not the old mega bag
        self.assertLess(len(parse_src.splitlines()), 400)
        self.assertTrue(
            (REPO_ROOT / "client" / "src" / "db" / "query" / "result-map.ts").is_file()
        )
        self.assertTrue(
            (REPO_ROOT / "client" / "src" / "db" / "query" / "equals-empty-hint.ts").is_file()
        )


class TestQueryTabsSeam(unittest.TestCase):
    """Shared SSOT + chrome-tabs remain under frontend/; product chrome is client."""

    SHARED_ASSETS = (
        "chrome-tabs.css",
        "chrome-tabs-layout.mjs",
        "query-tabs.css",
        "query-tabs-state.mjs",
        "tab-geometry.mjs",
        "app-context.mjs",
        "search-navigation.mjs",
        "committed-search.mjs",
        "vendor/draggabilly.pkgd.min.js",
    )
    REMOVED_SHELL = (
        "main.mjs",
        "gate.mjs",
        "search-workbench.mjs",
        "tabs-core.mjs",
        "tabs-ui.mjs",
        "view-sync.mjs",
        "relation-form.mjs",
        "lexicon-corrections.mjs",
        "entry-detail-portable.mjs",
        "query-explain.mjs",
        "mode-policy.mjs",
        "ping-ze-syntax.mjs",
        "dom-escape.mjs",
    )
    INDEX_FORBIDDEN = (
        "prototype-ribbon",
        "prototype-state-toggle",
        "prototype-query-tabs",
        "canto0243:prototype:query-tabs",
        "relation-entry.html",
        "relation-entry.css",
        "PROTOTYPE ·",
        'src="./main.mjs"',
    )
    MAIN_FORBIDDEN = (
        '@app.get("/prototype")',
        "prototype/query-tabs.html",
    )

    def test_shared_frontend_assets_remain(self):
        for name in self.SHARED_ASSETS:
            path = REPO_ROOT / "frontend" / name
            with self.subTest(asset=name):
                self.assertTrue(path.is_file(), f"missing frontend/{name}")

    def test_portable_shell_modules_removed(self):
        for name in self.REMOVED_SHELL:
            path = REPO_ROOT / "frontend" / name
            with self.subTest(removed=name):
                self.assertFalse(path.is_file(), f"shell module still present: {name}")

    def test_frontend_index_is_app_redirect_stub(self):
        source = INDEX_PATH.read_text(encoding="utf-8")
        self.assertIn('location.replace("/app/")', source)
        self.assertIn('url=/app/', source)
        for symbol in self.INDEX_FORBIDDEN:
            with self.subTest(symbol=symbol):
                self.assertNotIn(symbol, source)

    def test_client_wires_chrome_tabs_and_portable_ready(self):
        bar = CHROME_TABS_BAR_PATH.read_text(encoding="utf-8")
        app = CLIENT_APP_PATH.read_text(encoding="utf-8")
        ready = PORTABLE_READY_PATH.read_text(encoding="utf-8")
        app_ctx = APP_CONTEXT_PATH.read_text(encoding="utf-8")
        layout = LAYOUT_PATH.read_text(encoding="utf-8")
        self.assertIn("QueryChromeTabsLayout", bar)
        self.assertIn("chrome-tabs-layout.mjs", bar)
        self.assertIn("isPortableHost", app)
        self.assertIn("fetch('/ready'", ready)
        self.assertIn("gate_ready", ready)
        self.assertIn('from "./query-tabs-state.mjs"', app_ctx)
        self.assertIn("SESSION_KEY", app_ctx)
        self.assertIn("setupDraggabilly", layout)

    def test_word_router_exposes_query_explain(self):
        source = (REPO_ROOT / "app" / "routers" / "word.py").read_text(encoding="utf-8")
        self.assertIn("/query/explain", source)
        self.assertIn("explain_query", source)

    def test_query_explain_parity_contract_exists(self):
        """Phase D: dual-port explain gated by neutral parity contract (ADR-0021)."""
        path = REPO_ROOT / "contracts" / "query-explain-parity.json"
        self.assertTrue(path.is_file(), msg=str(path))
        data = json.loads(path.read_text(encoding="utf-8"))
        cases = data.get("cases") or []
        self.assertGreaterEqual(len(cases), 4)
        self.assertTrue((REPO_ROOT / "client" / "src" / "db" / "query-explain.ts").is_file())
        self.assertTrue((REPO_ROOT / "app" / "services" / "query_explain.py").is_file())

    def test_tab_geometry_js_shim_removed(self):
        path = REPO_ROOT / "frontend" / "tab-geometry.js"
        self.assertFalse(path.is_file())

    def test_tab_geometry_mjs_self_contained(self):
        path = REPO_ROOT / "frontend" / "tab-geometry.mjs"
        source = path.read_text(encoding="utf-8")
        self.assertIn("export const TAB_GEOMETRY_SVG", source)
        self.assertIn("#query-tab-geometry", source)
        self.assertNotIn("globalThis.TAB_GEOMETRY", source)

    def test_chrome_tabs_layout_js_shim_removed(self):
        path = REPO_ROOT / "frontend" / "chrome-tabs-layout.js"
        self.assertFalse(path.is_file())

    def test_chrome_tabs_layout_mjs_esm(self):
        source = LAYOUT_PATH.read_text(encoding="utf-8")
        self.assertIn("export class QueryChromeTabsLayout", source)
        self.assertIn("globalThis.Draggabilly", source)
        self.assertNotIn("global.QueryChromeTabsLayout", source)

    def test_relation_entry_page_removed(self):
        with self.subTest(path=str(RELATION_ENTRY_PATH.relative_to(REPO_ROOT))):
            self.assertFalse(RELATION_ENTRY_PATH.exists())

    def test_relation_entry_css_merged_into_shell(self):
        self.assertFalse(RELATION_ENTRY_CSS_PATH.exists())
        shell = (REPO_ROOT / "frontend" / "shell.css").read_text(encoding="utf-8")
        workbench = (REPO_ROOT / "frontend" / "workbench.css").read_text(encoding="utf-8")
        self.assertIn(".relation-main", shell)
        self.assertIn("a.result-item", workbench)

    def test_ready_gate_css_ssot(self):
        self.assertTrue(READY_GATE_CSS_PATH.is_file())
        self.assertFalse(PWA_BOOT_GATE_CSS_PATH.is_file())
        ready_gate = READY_GATE_CSS_PATH.read_text(encoding="utf-8")
        shell = (REPO_ROOT / "frontend" / "shell.css").read_text(encoding="utf-8")
        client_index = CLIENT_INDEX_PATH.read_text(encoding="utf-8")
        main_tsx = (REPO_ROOT / "client" / "src" / "main.tsx").read_text(encoding="utf-8")
        pwa_boot = (REPO_ROOT / "client" / "src" / "pwa-shell-boot.ts").read_text(encoding="utf-8")
        portable_ready = PORTABLE_READY_PATH.read_text(encoding="utf-8")
        self.assertIn(".ready-gate", ready_gate)
        self.assertIn(".preload-overlay", ready_gate)
        self.assertIn('use[filter=\'url(#brush-roughen-brand)\']', ready_gate)
        self.assertIn("html:not(.shell-revealed) .app-shell", ready_gate)
        self.assertNotIn("pwa-shell-revealed", ready_gate)
        self.assertNotIn(".preload-overlay {", shell)
        self.assertNotIn(".gate-brand {", shell)
        self.assertIn("ready-gate.css", client_index)
        self.assertIn("../../frontend/ready-gate.css", main_tsx)
        self.assertIn('class="ready-gate pwa-boot-gate"', client_index)
        self.assertIn("shell-revealed", pwa_boot)
        self.assertIn("gate_ready", portable_ready)
        self.assertNotIn("pwa-shell-revealed", pwa_boot)
        self.assertNotIn("pwa-shell-revealed", client_index)

    def test_shared_css_single_source_in_frontend(self):
        client_src = REPO_ROOT / "client" / "src"
        for name in ("open-design.css", "shell.css"):
            with self.subTest(duplicate=name):
                self.assertFalse((client_src / name).is_file(), f"remove duplicate client/src/{name}")
        self.assertTrue((REPO_ROOT / "frontend" / "shell.css").is_file())
        self.assertTrue((REPO_ROOT / "frontend" / "workbench.css").is_file())
        self.assertFalse((REPO_ROOT / "frontend" / "index.css").is_file())

    def test_pwa_main_imports_frontend_css(self):
        source = (REPO_ROOT / "client" / "src" / "main.tsx").read_text(encoding="utf-8")
        for path in (
            "../../frontend/open-design.css",
            "../../frontend/ready-gate.css",
            "../../frontend/shell.css",
            "../../frontend/workbench.css",
        ):
            with self.subTest(import_path=path):
                self.assertIn(path, source)
        self.assertIn("./root.css", source)
        self.assertIn("./pwa-app.css", source)

    def test_pwa_preloads_critical_display_subset(self):
        source = CLIENT_INDEX_PATH.read_text(encoding="utf-8")
        # %BASE_URL% so portable (/app/) and Pages (/Canto-0243/) both resolve
        self.assertIn("%BASE_URL%fonts/PlayfairDisplay-600.woff2", source)
        self.assertIn("%BASE_URL%fonts/CantoLogoSerif-700.woff2", source)
        self.assertIn("%BASE_URL%fonts/fonts.css", source)
        for weight in ("500", "600", "700"):
            with self.subTest(weight=weight):
                self.assertIn(f"%BASE_URL%fonts/CantoCriticalSerif-{weight}.woff2", source)
                self.assertNotIn(f'NotoSerifTC-{weight}.woff2" as="font"', source)

    def test_pwa_display_css_uses_critical_serif(self):
        shell = (REPO_ROOT / "frontend" / "shell.css").read_text(encoding="utf-8")
        stack = '"Playfair Display", "Canto Critical Serif", "Noto Serif TC", serif'
        self.assertIn(stack, shell)
        self.assertNotIn('"Playfair Display", "Noto Serif TC", serif', shell)

    def test_pwa_font_builder_generates_critical_subset(self):
        source = CLIENT_FONT_BUILD_PATH.read_text(encoding="utf-8")
        self.assertIn("criticalDisplayText", source)
        self.assertIn("logoText", source)
        self.assertIn("Canto Critical Serif", source)
        self.assertIn("Canto Logo Serif", source)
        self.assertIn("CantoCriticalSerif-", source)
        self.assertIn("CantoLogoSerif-", source)
        self.assertIn("text=", source)
        self.assertIn("display=block", source)
        self.assertIn("fonts.css still contains remote Google font URLs", source)

    def test_brand_wordmark_spec_parity(self):
        logo_serif = "'Canto Logo Serif', 'Noto Serif TC', serif"
        sources = {
            "brand-svg-defs.tsx": BRAND_SVG_DEFS_PATH.read_text(encoding="utf-8"),
            "client/index.html": CLIENT_INDEX_PATH.read_text(encoding="utf-8"),
        }
        for name, source in sources.items():
            normalized = source.replace('fontWeight="700"', 'font-weight="700"').replace('fontWeight="900"', 'font-weight="900"')
            with self.subTest(file=name):
                self.assertIn('font-weight="700"', normalized)
                self.assertNotIn('font-weight="900"', normalized)
                self.assertNotIn("Songti TC", source)
        self.assertIn(logo_serif, sources["client/index.html"])
        self.assertIn("LOGO_SERIF", sources["brand-svg-defs.tsx"])
        self.assertIn('fontWeight="700"', sources["brand-svg-defs.tsx"])

    def test_pages_workflow_requires_merged_release_source(self):
        source = PAGES_WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("Verify release source is current", source)
        self.assertIn("GITHUB_REF_NAME", source)
        self.assertIn("merge-base --is-ancestor origin/dev origin/main", source)

    def test_release_script_requires_merged_main_source(self):
        source = RELEASE_WINDOWS_PATH.read_text(encoding="utf-8")
        self.assertIn("function Assert-ReleaseSource", source)
        self.assertIn('branch -ne "main"', source)
        self.assertIn("merge-base --is-ancestor origin/dev origin/main", source)

    def test_macos_release_script_requires_merged_main_source(self):
        source = RELEASE_MACOS_PATH.read_text(encoding="utf-8")
        self.assertIn("_assert_release_source", source)
        self.assertIn("merge-base --is-ancestor origin/dev origin/main", source)
        self.assertIn('merge-base --is-ancestor "${TAG}^{commit}" origin/main', source)

    def test_client_imports_shared_css_ssot(self):
        source = (REPO_ROOT / "client" / "src" / "main.tsx").read_text(encoding="utf-8")
        for href in ("ready-gate.css", "shell.css", "workbench.css"):
            with self.subTest(href=href):
                self.assertIn(href, source)
        self.assertNotIn('href="index.css"', source)

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
        source = BRAND_SVG_DEFS_PATH.read_text(encoding="utf-8")
        logo = (REPO_ROOT / "client" / "src" / "brand-logo.tsx").read_text(encoding="utf-8")
        self.assertIn('id="brand-ink-blob"', source)
        self.assertIn('id="brand-ink-blob-dark"', source)
        self.assertIn('id="brush-roughen-brand"', source)
        self.assertIn("#brand-ink-blob", logo)
        ink_blob_path = "M4 55.5 C14 54.9 24 55.1 34 55.7"
        self.assertEqual(source.count(ink_blob_path), 1)
        self.assertIn("INK_BLOB_D", source)
        for legacy in (
            "brush-roughen-brand-gate",
            "brush-roughen-brand-meter",
            "brush-roughen-brand-header",
        ):
            with self.subTest(filter=legacy):
                self.assertNotIn(legacy, source)

    def test_mode_menu_escape_closes(self):
        menu = (REPO_ROOT / "client" / "src" / "mode-menu.tsx").read_text(encoding="utf-8")
        self.assertIn("Escape", menu)
        self.assertIn("setOpen(false)", menu)

    def test_shared_esm_modules_export_public_api(self):
        exports_required = {
            "search-navigation.mjs": (
                "withResultClickQuery",
                "commitSearchHistoryFrame",
                "shouldApplySearchPopstate",
            ),
            "query-tabs-state.mjs": ("openSingletonView", "createSearchTab"),
            "chrome-tabs-layout.mjs": ("QueryChromeTabsLayout",),
        }
        frontend = REPO_ROOT / "frontend"
        for name, symbols in exports_required.items():
            source = (frontend / name).read_text(encoding="utf-8")
            with self.subTest(module=name):
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

    def test_readiness_gate_includes_compound_ant_phase(self):
        source = READINESS_GATE_PATH.read_text(encoding="utf-8")
        self.assertIn("compound_ant", source)
        preload = (REPO_ROOT / "app" / "startup" / "offline_preload.py").read_text(encoding="utf-8")
        self.assertIn("compound_ant", preload)

    def test_portable_ready_hook_has_no_client_gate_policy(self):
        source = PORTABLE_READY_PATH.read_text(encoding="utf-8")
        for symbol in self.FORBIDDEN:
            with self.subTest(symbol=symbol):
                self.assertNotIn(symbol, source)

    def test_gate_ink_clip_constant_in_app_context(self):
        source = APP_CONTEXT_PATH.read_text(encoding="utf-8")
        self.assertIn("GATE_INK_CLIP_MAX = 200", source)

    def test_portable_ready_uses_server_gate_contract(self):
        ready = PORTABLE_READY_PATH.read_text(encoding="utf-8")
        self.assertIn("gate_ready", ready)
        self.assertIn("degraded", ready)
        self.assertIn("fetch('/ready'", ready)
        self.assertIn('location.replace("/app/")', INDEX_PATH.read_text(encoding="utf-8"))

    def test_served_frontend_shared_modules_match_disk(self):
        html = _fetch_served("index.html")
        self.assertIn("/app/", html)
        self.assertNotIn('src="./main.mjs"', html)
        ctx = _fetch_served("app-context.mjs")
        self.assertIn("GATE_INK_CLIP_MAX = 200", ctx)


class TestGuideManifestSync(unittest.TestCase):
    """guide renderer is the only execution source (搜尋教學驗收)."""

    def test_manifest_matches_html_guide_buttons(self):
        from scripts.guide_manifest import (
            load_html_examples,
            load_manifest_examples,
        )

        manifest = load_manifest_examples()
        self.assertGreater(len(manifest), 0, "empty guide manifest")
        self.assertEqual(load_html_examples(), [], "index.html must not duplicate guide examples")
        source = (REPO_ROOT / "frontend" / "guide-i18n.mjs").read_text(encoding="utf-8")
        self.assertIn("renderGuideGridHtml", source)
        self.assertEqual(
            len(manifest),
            len(set(manifest)),
            f"duplicate manifest entries: {manifest}",
        )


if __name__ == "__main__":
    import sys

    result = unittest.main(exit=False)
    sys.exit(0 if result.result.wasSuccessful() else 1)
