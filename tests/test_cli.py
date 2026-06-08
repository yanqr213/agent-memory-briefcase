import json
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from pathlib import Path

from agent_memory_briefcase.cli import main


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _run(self, argv):
        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_init_command_creates_bundle(self) -> None:
        code, out, err = self._run(["init", "--root", str(self.root), "--project-name", "demo"])
        self.assertEqual(code, 0)
        self.assertIn("Initialized briefcase", out)
        self.assertEqual(err, "")

    def test_add_decision_command_creates_entry(self) -> None:
        self._run(["init", "--root", str(self.root), "--project-name", "demo"])
        code, out, _ = self._run(
            [
                "add-decision",
                "--root",
                str(self.root),
                "--title",
                "CLI decision",
                "--context",
                "Need command",
                "--decision",
                "Create one",
                "--consequence",
                "It works",
            ]
        )
        self.assertEqual(code, 0)
        self.assertIn("Created decision", out)

    def test_add_session_command_creates_entry(self) -> None:
        self._run(["init", "--root", str(self.root), "--project-name", "demo"])
        code, out, _ = self._run(
            [
                "add-session",
                "--root",
                str(self.root),
                "--summary",
                "CLI session",
                "--change",
                "Added flow",
                "--deliverable",
                "CLI",
                "--test",
                "unit",
                "--risk",
                "manual",
            ]
        )
        self.assertEqual(code, 0)
        self.assertIn("Created session", out)

    def test_brief_command_prints_markdown(self) -> None:
        self._run(["init", "--root", str(self.root), "--project-name", "demo"])
        code, out, _ = self._run(["brief", "--root", str(self.root), "--max-words", "200", "--max-tokens", "400"])
        self.assertEqual(code, 0)
        self.assertIn("# Agent Memory Brief", out)

    def test_brief_command_writes_output_with_parent_creation(self) -> None:
        self._run(["init", "--root", str(self.root), "--project-name", "demo"])
        target = self.root / "build" / "brief.md"
        code, out, _ = self._run(
            [
                "brief",
                "--root",
                str(self.root),
                "--output",
                str(target),
                "--max-words",
                "200",
                "--max-tokens",
                "400",
            ]
        )
        self.assertEqual(code, 0)
        self.assertTrue(target.exists())
        self.assertIn("Wrote brief", out)

    def test_export_command_writes_json(self) -> None:
        self._run(["init", "--root", str(self.root), "--project-name", "demo"])
        target = self.root / "out" / "export.json"
        code, out, _ = self._run(["export", "--root", str(self.root), "--format", "json", "--output", str(target)])
        self.assertEqual(code, 0)
        self.assertTrue(target.exists())
        payload = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(payload["bundle"]["profile"]["project_name"], "demo")
        self.assertIn("Wrote export", out)

    def test_export_command_writes_handoff(self) -> None:
        self._run(["init", "--root", str(self.root), "--project-name", "demo"])
        self._run(
            [
                "add-session",
                "--root",
                str(self.root),
                "--summary",
                "Prepared handoff",
                "--deliverable",
                "handoff brief",
                "--test",
                "unit",
            ]
        )
        target = self.root / "out" / "handoff.md"
        code, out, _ = self._run(["export", "--root", str(self.root), "--format", "handoff", "--output", str(target)])
        self.assertEqual(code, 0)
        content = target.read_text(encoding="utf-8")
        self.assertIn("# Agent Handoff Brief", content)
        self.assertIn("Prepared handoff", content)
        self.assertIn("Wrote export", out)

    def test_lint_command_returns_zero_without_threshold(self) -> None:
        self._run(["init", "--root", str(self.root), "--project-name", "demo"])
        code, out, _ = self._run(["lint", "--root", str(self.root)])
        self.assertEqual(code, 0)
        self.assertIn("W012", out)

    def test_lint_command_fails_on_warning_threshold(self) -> None:
        self._run(["init", "--root", str(self.root), "--project-name", "demo"])
        code, out, _ = self._run(["lint", "--root", str(self.root), "--check", "warning"])
        self.assertEqual(code, 1)
        self.assertIn("W012", out)

    def test_check_command_defaults_to_error_threshold(self) -> None:
        self._run(["init", "--root", str(self.root), "--project-name", "demo"])
        code, _, _ = self._run(["check", "--root", str(self.root)])
        self.assertEqual(code, 0)

    def test_check_command_can_fail_on_warning(self) -> None:
        self._run(["init", "--root", str(self.root), "--project-name", "demo"])
        code, _, _ = self._run(["check", "--root", str(self.root), "--check", "warning"])
        self.assertEqual(code, 1)

    def test_doctor_command_prints_json(self) -> None:
        self._run(["init", "--root", str(self.root), "--project-name", "demo"])
        code, out, _ = self._run(["doctor", "--root", str(self.root), "--format", "json"])
        payload = json.loads(out)

        self.assertEqual(code, 0)
        self.assertEqual(payload["project_name"], "demo")
        self.assertEqual(payload["status"], "attention")

    def test_doctor_command_writes_output_with_parent_creation(self) -> None:
        self._run(["init", "--root", str(self.root), "--project-name", "demo"])
        target = self.root / "build" / "doctor.md"
        code, out, _ = self._run(["doctor", "--root", str(self.root), "--output", str(target)])

        self.assertEqual(code, 0)
        self.assertTrue(target.exists())
        self.assertIn("# Agent Memory Doctor", target.read_text(encoding="utf-8"))
        self.assertIn("Wrote doctor report", out)

    def test_doctor_command_can_fail_on_warning_threshold(self) -> None:
        self._run(["init", "--root", str(self.root), "--project-name", "demo"])
        code, out, _ = self._run(["doctor", "--root", str(self.root), "--check", "warning"])

        self.assertEqual(code, 1)
        self.assertIn("## Next Actions", out)

    def test_command_returns_error_when_uninitialized(self) -> None:
        code, _, err = self._run(["brief", "--root", str(self.root)])
        self.assertEqual(code, 2)
        self.assertIn("Run `agent-memory-briefcase init` first", err)
