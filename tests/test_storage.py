import json
import tempfile
import unittest
from pathlib import Path

from agent_memory_briefcase.storage import (
    BriefcaseError,
    add_decision,
    add_session,
    init_bundle,
    load_bundle,
    parse_constraints,
    read_profile,
    resolve_paths,
)


class StorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_init_bundle_creates_expected_files(self) -> None:
        paths = init_bundle(self.root, project_name="demo")
        self.assertTrue(paths.bundle_dir.exists())
        self.assertTrue(paths.profile_path.exists())
        self.assertTrue(paths.constraints_path.exists())
        self.assertTrue(paths.decisions_dir.exists())
        self.assertTrue(paths.sessions_dir.exists())

    def test_init_bundle_rejects_existing_without_force(self) -> None:
        init_bundle(self.root, project_name="demo")
        with self.assertRaises(BriefcaseError):
            init_bundle(self.root, project_name="demo")

    def test_parse_constraints_extracts_sections(self) -> None:
        parsed = parse_constraints(
            "# Constraints\n\n## Hard Constraints\n- one\n## Taboos\n- two\n## Risk Hotspots\n- three\n"
        )
        self.assertEqual(parsed["hard_constraints"], ["one"])
        self.assertEqual(parsed["taboos"], ["two"])
        self.assertEqual(parsed["risk_hotspots"], ["three"])

    def test_add_decision_creates_json_and_markdown(self) -> None:
        init_bundle(self.root, project_name="demo")
        entry = add_decision(
            self.root,
            title="Use mirrored records",
            status="accepted",
            context="Need both forms.",
            decision="Store both JSON and Markdown.",
            consequences=["Easy diffs"],
            tags=["storage"],
        )
        paths = resolve_paths(self.root)
        self.assertTrue((paths.decisions_dir / f"{entry['id']}.json").exists())
        self.assertTrue((paths.decisions_dir / f"{entry['id']}.md").exists())

    def test_add_decision_deduplicates_ids(self) -> None:
        init_bundle(self.root, project_name="demo")
        first = add_decision(
            self.root,
            title="Same title",
            status="accepted",
            context="A",
            decision="B",
            consequences=["C"],
        )
        second = add_decision(
            self.root,
            title="Same title",
            status="accepted",
            context="A",
            decision="B",
            consequences=["C"],
        )
        self.assertNotEqual(first["id"], second["id"])

    def test_add_session_creates_json_and_markdown(self) -> None:
        init_bundle(self.root, project_name="demo")
        entry = add_session(
            self.root,
            summary="Ship CLI",
            changes=["Added commands"],
            deliverables=["CLI"],
            tests=["unit"],
            risks=["none"],
            artifacts=["dist/app.whl"],
        )
        paths = resolve_paths(self.root)
        self.assertTrue((paths.sessions_dir / f"{entry['id']}.json").exists())
        self.assertTrue((paths.sessions_dir / f"{entry['id']}.md").exists())

    def test_load_bundle_includes_entries(self) -> None:
        init_bundle(self.root, project_name="demo")
        add_decision(
            self.root,
            title="Use storage",
            status="accepted",
            context="A",
            decision="B",
            consequences=["C"],
        )
        add_session(
            self.root,
            summary="Session one",
            changes=["A"],
            deliverables=["B"],
            tests=["C"],
            risks=["D"],
        )
        bundle = load_bundle(self.root)
        self.assertEqual(len(bundle["decisions"]), 1)
        self.assertEqual(len(bundle["sessions"]), 1)

    def test_read_profile_returns_profile(self) -> None:
        init_bundle(self.root, project_name="demo", summary="summary")
        profile = read_profile(self.root)
        self.assertEqual(profile["project_name"], "demo")
        self.assertEqual(profile["project_summary"], "summary")

    def test_load_bundle_raises_without_init(self) -> None:
        with self.assertRaises(BriefcaseError):
            load_bundle(self.root)

    def test_init_bundle_writes_json_defaults(self) -> None:
        init_bundle(self.root, project_name="demo")
        paths = resolve_paths(self.root)
        glossary = json.loads(paths.glossary_path.read_text(encoding="utf-8"))
        commands = json.loads(paths.commands_path.read_text(encoding="utf-8"))
        self.assertEqual(glossary, {"terms": []})
        self.assertEqual(commands, {"commands": []})

