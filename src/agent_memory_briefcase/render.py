import json
from typing import Any, Dict, List

from agent_memory_briefcase.utils import utc_now


def render_markdown_export(bundle: Dict[str, Any]) -> str:
    profile = bundle["profile"]
    constraints = bundle["constraints"]
    lines: List[str] = [
        "# Agent Memory Briefcase Export",
        f"Generated: {utc_now()}",
        "",
        "## Profile",
        f"- Project: {profile.get('project_name', '')}",
        f"- Summary: {profile.get('project_summary', '')}",
        f"- Owners: {', '.join(profile.get('owners', [])) or 'none listed'}",
        f"- Default branch: {profile.get('default_branch', '')}",
        f"- Primary language: {profile.get('primary_language', '')}",
        f"- Review cadence: every {profile.get('review_after_days', 30)} days",
        "",
        "## Hard Constraints",
    ]
    lines.extend(f"- {item}" for item in constraints["hard_constraints"])
    lines.extend(["", "## Taboos"])
    lines.extend(f"- {item}" for item in constraints["taboos"])
    lines.extend(["", "## Risk Hotspots"])
    lines.extend(f"- {item}" for item in constraints["risk_hotspots"])
    lines.extend(["", "## Glossary"])
    lines.extend(
        f"- {item.get('term', '')}: {item.get('definition', '')}"
        for item in bundle["glossary"].get("terms", [])
    )
    lines.extend(["", "## Commands"])
    lines.extend(
        f"- {item.get('name', '')}: `{item.get('command', '')}` - {item.get('purpose', '')}"
        for item in bundle["commands"].get("commands", [])
    )
    lines.extend(["", "## Ownership"])
    lines.extend(
        f"- `{item.get('path', '')}` -> {item.get('owner', '')} ({item.get('validated_at', 'unknown date')})"
        for item in bundle["ownership"].get("owners", [])
    )
    lines.extend(["", "## Test Evidence"])
    lines.extend(
        f"- {item.get('name', '')}: {item.get('status', '')} on {item.get('last_run', 'unknown date')}"
        for item in bundle["test_evidence"].get("evidence", [])
    )
    lines.extend(["", "## Decisions"])
    for item in bundle["decisions"]:
        lines.extend(
            [
                f"- {item.get('date', '')} [{item.get('status', '')}] {item.get('title', '')}",
                f"  Decision: {item.get('decision', '')}",
            ]
        )
    lines.extend(["", "## Sessions"])
    for item in bundle["sessions"]:
        lines.extend(
            [
                f"- {item.get('date', '')} {item.get('summary', '')}",
                f"  Deliverables: {', '.join(item.get('deliverables', [])) or 'none listed'}",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def render_json_export(bundle: Dict[str, Any]) -> str:
    payload = {
        "generated_at": utc_now(),
        "bundle": bundle,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"

