import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from agent_memory_briefcase.doctor import render_doctor_markdown, run_doctor
from agent_memory_briefcase.storage import add_session, init_bundle, resolve_paths


class DoctorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _write_json(self, path: Path, payload) -> None:
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def test_doctor_reports_blocked_for_missing_bundle(self) -> None:
        report = run_doctor(self.root, today=date(2026, 6, 8))

        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["score"], 0)
        self.assertTrue(any(item["code"] == "E000" for item in report["findings"]))

    def test_doctor_reports_ready_for_complete_bundle(self) -> None:
        init_bundle(self.root, project_name="demo", review_after_days=30)
        paths = resolve_paths(self.root)
        self._write_json(
            paths.glossary_path,
            {"terms": [{"term": "brief", "definition": "compact agent context"}]},
        )
        self._write_json(
            paths.commands_path,
            {
                "commands": [
                    {
                        "name": "unit",
                        "command": "python -m unittest discover -s tests -v",
                        "purpose": "Run regression tests",
                    }
                ]
            },
        )
        self._write_json(
            paths.ownership_path,
            {"owners": [{"path": "src/", "owner": "team", "validated_at": "2026-06-08"}]},
        )
        self._write_json(
            paths.test_evidence_path,
            {
                "evidence": [
                    {
                        "name": "unit",
                        "status": "passed",
                        "last_run": "2026-06-08",
                        "command": "python -m unittest",
                    }
                ]
            },
        )
        add_session(
            self.root,
            summary="Verified complete memory bundle",
            changes=["Updated catalogs"],
            deliverables=["doctor-ready bundle"],
            tests=["unit"],
            risks=["manual updates"],
            date_value=date(2026, 6, 8),
        )

        report = run_doctor(self.root, today=date(2026, 6, 8))

        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["score"], 100)
        self.assertEqual(report["counts"]["commands"], 1)
        self.assertTrue(all(gate["status"] == "pass" for gate in report["gates"]))

    def test_doctor_reports_attention_and_next_actions_for_warnings(self) -> None:
        init_bundle(self.root, project_name="demo", review_after_days=30)

        report = run_doctor(self.root, today=date(2026, 6, 8))

        self.assertEqual(report["status"], "attention")
        self.assertLess(report["score"], 100)
        self.assertTrue(any("glossary.json" in action for action in report["next_actions"]))

    def test_render_doctor_markdown_contains_gate_summary(self) -> None:
        init_bundle(self.root, project_name="demo", review_after_days=30)
        report = run_doctor(self.root, today=date(2026, 6, 8))

        content = render_doctor_markdown(report)

        self.assertIn("# Agent Memory Doctor", content)
        self.assertIn("## Gates", content)
        self.assertIn("## Next Actions", content)
        self.assertIn("Prompt inputs", content)
