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


def render_handoff_export(bundle: Dict[str, Any]) -> str:
    profile = bundle["profile"]
    constraints = bundle["constraints"]
    sessions = bundle["sessions"][:3]
    decisions = bundle["decisions"][:5]
    commands = bundle["commands"].get("commands", [])[:8]
    evidence = bundle["test_evidence"].get("evidence", [])[:6]
    owners = bundle["ownership"].get("owners", [])[:8]

    lines: List[str] = [
        "# Agent Handoff Brief",
        f"Generated: {utc_now()}",
        "",
        "## Project Snapshot",
        f"- Project: {profile.get('project_name', '')}",
        f"- Summary: {profile.get('project_summary', '')}",
        f"- Owners: {', '.join(profile.get('owners', [])) or 'none listed'}",
        f"- Default branch: {profile.get('default_branch', '')}",
        f"- Primary language: {profile.get('primary_language', '')}",
        "",
    ]

    lines.extend(_bulleted_section("Operating Constraints", constraints["hard_constraints"][:8]))
    lines.extend(_bulleted_section("Do Not Do", constraints["taboos"][:8]))
    lines.extend(_bulleted_section("Risk Hotspots", constraints["risk_hotspots"][:8]))

    lines.extend(["## Recent Work", ""])
    if sessions:
        for item in sessions:
            lines.append(f"- {item.get('date', '')} {item.get('summary', '')}")
            _append_nested(lines, "Changes", item.get("changes", [])[:4])
            _append_nested(lines, "Deliverables", item.get("deliverables", [])[:4])
            _append_nested(lines, "Tests", item.get("tests", [])[:4])
            _append_nested(lines, "Risks", item.get("risks", [])[:4])
    else:
        lines.append("- No session summaries recorded yet.")

    lines.extend(["", "## Decisions To Preserve", ""])
    if decisions:
        for item in decisions:
            lines.append(f"- {item.get('date', '')} [{item.get('status', '')}] {item.get('title', '')}: {item.get('decision', '')}")
    else:
        lines.append("- No decisions recorded yet.")

    lines.extend(["", "## Verification Commands", ""])
    if commands:
        for item in commands:
            lines.append(f"- {item.get('name', '')}: `{item.get('command', '')}`")
            if item.get("purpose"):
                lines.append(f"  Purpose: {item.get('purpose', '')}")
    else:
        lines.append("- No common commands recorded yet.")

    lines.extend(["", "## Test Evidence", ""])
    if evidence:
        for item in evidence:
            lines.append(f"- {item.get('name', '')}: {item.get('status', 'unknown')} on {item.get('last_run', 'unknown date')} via `{item.get('command', '')}`")
            if item.get("notes"):
                lines.append(f"  Notes: {item.get('notes', '')}")
    else:
        lines.append("- No test evidence recorded yet.")

    lines.extend(["", "## Ownership Map", ""])
    if owners:
        for item in owners:
            lines.append(f"- `{item.get('path', '')}` -> {item.get('owner', '')} ({item.get('validated_at', 'unknown date')})")
            if item.get("notes"):
                lines.append(f"  Notes: {item.get('notes', '')}")
    else:
        lines.append("- No ownership entries recorded yet.")

    lines.extend(
        [
            "",
            "## Suggested Next-Agent Prompt",
            "",
            "Continue from this handoff. Respect the operating constraints, preserve accepted decisions, run the listed verification commands after edits, and update this briefcase with a new session summary before handing off again.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _bulleted_section(title: str, items: List[str]) -> List[str]:
    lines = [f"## {title}", ""]
    if items:
        lines.extend(f"- {item}" for item in items)
    else:
        lines.append("- None recorded.")
    lines.append("")
    return lines


def _append_nested(lines: List[str], label: str, items: List[str]) -> None:
    if not items:
        return
    lines.append(f"  {label}:")
    for item in items:
        lines.append(f"  - {item}")
