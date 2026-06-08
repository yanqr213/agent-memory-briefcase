import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from agent_memory_briefcase.linting import highest_severity, run_lint
from agent_memory_briefcase.storage import init_bundle, resolve_paths


class LintingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        init_bundle(self.root, project_name="demo", review_after_days=10)
        self.paths = resolve_paths(self.root)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _write_json(self, path: Path, payload) -> None:
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def test_lint_reports_empty_catalog_warnings(self) -> None:
        findings = run_lint(self.root, today=date(2026, 6, 8))
        codes = {item.code for item in findings}
        self.assertIn("W012", codes)
        self.assertIn("W013", codes)
        self.assertIn("W014", codes)
        self.assertIn("W015", codes)

    def test_lint_detects_missing_bundle(self) -> None:
        other = self.root / "missing"
        findings = run_lint(other)
        self.assertEqual(findings[0].code, "E000")

    def test_lint_detects_stale_profile(self) -> None:
        profile = json.loads(self.paths.profile_path.read_text(encoding="utf-8"))
        profile["updated_at"] = "2026-05-01T00:00:00Z"
        self._write_json(self.paths.profile_path, profile)
        findings = run_lint(self.root, today=date(2026, 6, 8))
        self.assertTrue(any(item.code == "W020" for item in findings))

    def test_lint_detects_missing_recent_session(self) -> None:
        findings = run_lint(self.root, today=date(2026, 6, 8))
        self.assertTrue(any(item.code == "W021" for item in findings))

    def test_lint_detects_stale_ownership(self) -> None:
        payload = {
            "owners": [
                {
                    "path": "src/",
                    "owner": "team",
                    "validated_at": "2026-05-01",
                    "notes": "old",
                }
            ]
        }
        self._write_json(self.paths.ownership_path, payload)
        findings = run_lint(self.root, today=date(2026, 6, 8))
        self.assertTrue(any(item.code == "W022" for item in findings))

    def test_lint_detects_stale_test_evidence(self) -> None:
        payload = {
            "evidence": [
                {
                    "name": "unit",
                    "status": "passed",
                    "last_run": "2026-05-01",
                    "command": "python -m unittest",
                }
            ]
        }
        self._write_json(self.paths.test_evidence_path, payload)
        findings = run_lint(self.root, today=date(2026, 6, 8))
        self.assertTrue(any(item.code == "W023" for item in findings))

    def test_lint_detects_old_proposed_decision(self) -> None:
        decision_dir = self.paths.decisions_dir
        decision_dir.mkdir(exist_ok=True)
        (decision_dir / "demo.json").write_text(
            json.dumps(
                {
                    "id": "demo",
                    "title": "Pending",
                    "status": "proposed",
                    "date": "2026-05-01",
                    "context": "A",
                    "decision": "B",
                    "consequences": [],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (decision_dir / "demo.md").write_text("# demo\n", encoding="utf-8")
        findings = run_lint(self.root, today=date(2026, 6, 8))
        self.assertTrue(any(item.code == "W024" for item in findings))

    def test_lint_detects_unpaired_decision_files(self) -> None:
        (self.paths.decisions_dir / "lonely.json").write_text("{}", encoding="utf-8")
        findings = run_lint(self.root, today=date(2026, 6, 8))
        self.assertTrue(any(item.code == "W030" for item in findings))

    def test_lint_detects_unpaired_session_files(self) -> None:
        (self.paths.sessions_dir / "lonely.md").write_text("# lonely\n", encoding="utf-8")
        findings = run_lint(self.root, today=date(2026, 6, 8))
        self.assertTrue(any(item.code == "W031" for item in findings))

    def test_highest_severity_prefers_error(self) -> None:
        findings = run_lint(self.root)
        self.assertEqual(highest_severity(findings + [type("F", (), {"severity": "error"})()]), "error")

