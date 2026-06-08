import json
import tempfile
import unittest
from pathlib import Path

from agent_memory_briefcase.render import render_handoff_export, render_json_export, render_markdown_export
from agent_memory_briefcase.storage import add_decision, add_session, init_bundle, load_bundle


class RenderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        init_bundle(self.root, project_name="demo")
        add_decision(
            self.root,
            title="Use render export",
            status="accepted",
            context="Need durable output",
            decision="Offer markdown and json exports",
            consequences=["Easy handoff"],
        )
        add_session(
            self.root,
            summary="Exported bundle",
            changes=["Added renderer"],
            deliverables=["exports"],
            tests=["unit"],
            risks=["none"],
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_render_markdown_export_contains_sections(self) -> None:
        bundle = load_bundle(self.root)
        content = render_markdown_export(bundle)
        self.assertIn("## Decisions", content)
        self.assertIn("## Sessions", content)

    def test_render_json_export_is_valid_json(self) -> None:
        bundle = load_bundle(self.root)
        payload = json.loads(render_json_export(bundle))
        self.assertEqual(payload["bundle"]["profile"]["project_name"], "demo")

    def test_render_json_export_contains_decisions(self) -> None:
        bundle = load_bundle(self.root)
        payload = json.loads(render_json_export(bundle))
        self.assertEqual(len(payload["bundle"]["decisions"]), 1)

    def test_render_handoff_export_contains_agent_prompt(self) -> None:
        bundle = load_bundle(self.root)
        content = render_handoff_export(bundle)

        self.assertIn("# Agent Handoff Brief", content)
        self.assertIn("## Recent Work", content)
        self.assertIn("## Suggested Next-Agent Prompt", content)
        self.assertIn("Exported bundle", content)
