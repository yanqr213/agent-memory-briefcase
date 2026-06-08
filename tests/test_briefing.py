import tempfile
import unittest
from datetime import date
from pathlib import Path

from agent_memory_briefcase.briefing import brief_as_json, generate_brief, generate_brief_from_root
from agent_memory_briefcase.storage import add_decision, add_session, init_bundle, load_bundle, resolve_paths


class BriefingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        init_bundle(self.root, project_name="demo", review_after_days=10)
        paths = resolve_paths(self.root)
        paths.glossary_path.write_text(
            '{\n  "terms": [{"term": "brief", "definition": "compact summary"}]\n}\n',
            encoding="utf-8",
        )
        paths.commands_path.write_text(
            '{\n  "commands": [{"name": "test", "command": "python -m unittest", "purpose": "run tests"}]\n}\n',
            encoding="utf-8",
        )
        paths.ownership_path.write_text(
            '{\n  "owners": [{"path": "src/", "owner": "team", "validated_at": "2026-06-08", "notes": "core"}]\n}\n',
            encoding="utf-8",
        )
        paths.test_evidence_path.write_text(
            '{\n  "evidence": [{"name": "unit", "status": "passed", "last_run": "2026-06-08", "command": "python -m unittest"}]\n}\n',
            encoding="utf-8",
        )
        add_decision(
            self.root,
            title="Use brief generation",
            status="accepted",
            context="Need compact context.",
            decision="Generate markdown brief.",
            consequences=["Reusable prompts"],
        )
        add_session(
            self.root,
            summary="Initial delivery",
            changes=["Implemented brief flow"],
            deliverables=["CLI"],
            tests=["unit"],
            risks=["manual maintenance"],
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_generate_brief_returns_markdown(self) -> None:
        bundle = load_bundle(self.root)
        result = generate_brief(bundle, max_words=500, max_tokens=1000)
        self.assertIn("# Agent Memory Brief", result.content)
        self.assertFalse(result.truncated)

    def test_generate_brief_truncates_by_budget(self) -> None:
        bundle = load_bundle(self.root)
        result = generate_brief(bundle, max_words=30, max_tokens=70)
        self.assertTrue(result.truncated)
        self.assertLessEqual(result.word_count, 30)
        self.assertLessEqual(result.estimated_tokens, 70)

    def test_generate_brief_from_root_includes_stale_hints(self) -> None:
        result = generate_brief_from_root(
            self.root,
            bundle_loader=load_bundle,
            max_words=500,
            max_tokens=1000,
            today=date(2026, 7, 1),
        )
        self.assertTrue(any(hint.startswith("W020") or hint.startswith("W021") for hint in result.stale_hints))

    def test_generate_brief_can_disable_stale_hints(self) -> None:
        bundle = load_bundle(self.root)
        result = generate_brief(
            bundle,
            max_words=500,
            max_tokens=1000,
            include_stale_hints=False,
        )
        self.assertNotIn("## Stale Hints", result.content)

    def test_brief_as_json_contains_metadata(self) -> None:
        bundle = load_bundle(self.root)
        result = generate_brief(bundle, max_words=500, max_tokens=1000)
        payload = brief_as_json(bundle, result)
        self.assertIn('"project_name": "demo"', payload)
        self.assertIn('"truncated": false', payload)

