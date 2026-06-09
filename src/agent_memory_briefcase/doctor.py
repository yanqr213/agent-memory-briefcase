import json
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from agent_memory_briefcase.linting import run_lint
from agent_memory_briefcase.models import Finding
from agent_memory_briefcase.storage import BriefcaseError, load_bundle, resolve_paths
from agent_memory_briefcase.utils import utc_now


GATE_DEFINITIONS = (
    ("bundle", "Bundle layout", ("E000",)),
    ("profile", "Profile metadata", ("E001", "E002", "E003")),
    (
        "prompt_inputs",
        "Prompt inputs",
        ("W010", "W011", "W012", "W013", "W014", "W015"),
    ),
    ("freshness", "Freshness", ("W020", "W021", "W022", "W023", "W024")),
    ("mirroring", "Mirrored records", ("W030", "W031")),
)

ACTION_BY_CODE = {
    "E000": "Run `agent-memory-briefcase init` at the repository root.",
    "E001": "Fill `.agent-memory-briefcase/profile.json` with a stable `project_name`.",
    "E002": "Add a short, current `project_summary` to `.agent-memory-briefcase/profile.json`.",
    "E003": "Set `review_after_days` in `.agent-memory-briefcase/profile.json` to a positive integer.",
    "W010": "Add the hard constraints that every coding agent must preserve.",
    "W011": "Add the taboos that agents must not violate.",
    "W012": "Update `.agent-memory-briefcase/glossary.json` with project terms and definitions.",
    "W013": "Update `.agent-memory-briefcase/commands.json` with the commands agents should run.",
    "W014": "Update `.agent-memory-briefcase/ownership.json` with path owners.",
    "W015": "Update `.agent-memory-briefcase/test_evidence.json` with the latest verification evidence.",
    "W020": "Refresh `.agent-memory-briefcase/profile.json` after validating the project summary.",
    "W021": "Record the latest meaningful work with `agent-memory-briefcase add-session`.",
    "W022": "Revalidate stale ownership entries or replace them with current owners.",
    "W023": "Rerun stale verification commands and update `test_evidence.json`.",
    "W024": "Resolve old proposed, trial, or draft decisions as accepted, rejected, or superseded.",
    "W030": "Restore missing Markdown or JSON decision mirrors.",
    "W031": "Restore missing Markdown or JSON session mirrors.",
}


def run_doctor(root: Path, *, today: Optional[date] = None) -> Dict[str, Any]:
    paths = resolve_paths(root)
    findings = run_lint(root, today=today)
    bundle = _load_bundle_if_available(root)
    report = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "root": str(paths.root),
        "bundle_dir": str(paths.bundle_dir),
        "project_name": _project_name(bundle, paths.root.name),
        "status": _overall_status(findings),
        "score": _score(findings),
        "counts": _counts(bundle),
        "gates": _gates(findings),
        "findings": [finding.as_dict() for finding in findings],
        "next_actions": _next_actions(findings),
    }
    return report


def render_doctor_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Agent Memory Doctor",
        f"Generated: {report.get('generated_at', '')}",
        "",
        f"- Project: {report.get('project_name', '')}",
        f"- Status: `{report.get('status', '')}`",
        f"- Score: {report.get('score', 0)}/100",
        f"- Bundle: `{report.get('bundle_dir', '')}`",
        "",
        "## Counts",
        "",
    ]
    for key, value in report.get("counts", {}).items():
        lines.append(f"- {key}: {value}")

    lines.extend(["", "## Gates", ""])
    for gate in report.get("gates", []):
        lines.append(
            f"- {gate.get('status', '').upper()} {gate.get('name', '')}: {gate.get('summary', '')}"
        )

    lines.extend(["", "## Findings", ""])
    findings = report.get("findings", [])
    if findings:
        for finding in findings:
            lines.append(
                f"- [{finding.get('severity', '').upper()}] {finding.get('code', '')} "
                f"{finding.get('message', '')} ({finding.get('path', '')})"
            )
    else:
        lines.append("- No findings.")

    lines.extend(["", "## Next Actions", ""])
    actions = report.get("next_actions", [])
    if actions:
        lines.extend(f"- {action}" for action in actions)
    else:
        lines.append("- No immediate fixes. Add a new session summary after the next meaningful delivery.")

    lines.extend(["", "## Agent Usage Advice", ""])
    status = report.get("status")
    if status == "ready":
        lines.append("- This briefcase is ready for a Codex, Claude Code, or custom agent handoff.")
    elif status == "attention":
        lines.append("- This briefcase is usable, but refresh the warnings before relying on it for a long task.")
    else:
        lines.append("- Fix blocking errors before using this briefcase as trusted agent context.")
    return "\n".join(lines).rstrip() + "\n"


def render_doctor_pr_comment(report: Dict[str, Any]) -> str:
    lines = [
        "<!-- agent-memory-briefcase doctor -->",
        "## Agent Memory Doctor",
        "",
        (
            f"**Project:** {_table_cell(report.get('project_name', ''))} | "
            f"**Status:** `{report.get('status', '')}` | "
            f"**Score:** {report.get('score', 0)}/100"
        ),
        "",
        "### Gates",
        "",
        "| Gate | Status | Summary |",
        "| --- | --- | --- |",
    ]
    for gate in report.get("gates", []):
        lines.append(
            "| "
            f"{_table_cell(gate.get('name', ''))} | "
            f"`{_table_cell(gate.get('status', ''))}` | "
            f"{_table_cell(gate.get('summary', ''))} |"
        )

    lines.extend(["", "### Findings", ""])
    findings = report.get("findings", [])
    if findings:
        lines.extend(["| Severity | Code | Path | Message |", "| --- | --- | --- | --- |"])
        for finding in findings:
            lines.append(
                "| "
                f"`{_table_cell(finding.get('severity', ''))}` | "
                f"`{_table_cell(finding.get('code', ''))}` | "
                f"`{_table_cell(_display_path(report, finding.get('path', '')))}` | "
                f"{_table_cell(finding.get('message', ''))} |"
            )
    else:
        lines.append("No findings.")

    lines.extend(["", "### Next Actions", ""])
    actions = report.get("next_actions", [])
    if actions:
        lines.extend(f"- {action}" for action in actions)
    else:
        lines.append("- No immediate fixes. Add a new session summary after the next meaningful delivery.")

    lines.extend(
        [
            "",
            "_Generated by `agent-memory-briefcase doctor --format pr-comment`._",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def render_doctor_sarif(report: Dict[str, Any]) -> str:
    findings = report.get("findings", [])
    rules_by_code: Dict[str, Dict[str, Any]] = {}
    results: List[Dict[str, Any]] = []

    for finding in findings:
        code = str(finding.get("code", "UNKNOWN"))
        severity = str(finding.get("severity", "warning"))
        message = str(finding.get("message", ""))
        if code not in rules_by_code:
            action = ACTION_BY_CODE.get(code, f"Resolve {code}: {message}")
            rules_by_code[code] = {
                "id": code,
                "name": code,
                "shortDescription": {"text": message or code},
                "fullDescription": {"text": action},
                "help": {"text": action},
                "properties": {
                    "severity": severity,
                    "tags": ["agent-memory", "agent-context", "documentation"],
                },
            }
        results.append(
            {
                "ruleId": code,
                "level": _sarif_level(severity),
                "message": {"text": message},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": _sarif_uri(report, str(finding.get("path", "")))
                            },
                            "region": {"startLine": 1},
                        }
                    }
                ],
                "properties": {
                    "severity": severity,
                    "briefcaseStatus": report.get("status", ""),
                },
            }
        )

    payload = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "agent-memory-briefcase",
                        "informationUri": "https://github.com/yanqr213/agent-memory-briefcase",
                        "rules": list(rules_by_code.values()),
                    }
                },
                "results": results,
                "properties": {
                    "projectName": report.get("project_name", ""),
                    "status": report.get("status", ""),
                    "score": report.get("score", 0),
                    "bundleDir": report.get("bundle_dir", ""),
                },
            }
        ],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def _load_bundle_if_available(root: Path) -> Optional[Dict[str, Any]]:
    try:
        return load_bundle(root)
    except BriefcaseError:
        return None


def _project_name(bundle: Optional[Dict[str, Any]], fallback: str) -> str:
    if not bundle:
        return fallback
    return str(bundle.get("profile", {}).get("project_name") or fallback)


def _counts(bundle: Optional[Dict[str, Any]]) -> Dict[str, int]:
    if not bundle:
        return {
            "hard_constraints": 0,
            "taboos": 0,
            "risk_hotspots": 0,
            "glossary_terms": 0,
            "commands": 0,
            "owners": 0,
            "test_evidence": 0,
            "decisions": 0,
            "sessions": 0,
        }
    constraints = bundle.get("constraints", {})
    return {
        "hard_constraints": len(constraints.get("hard_constraints", [])),
        "taboos": len(constraints.get("taboos", [])),
        "risk_hotspots": len(constraints.get("risk_hotspots", [])),
        "glossary_terms": len(bundle.get("glossary", {}).get("terms", [])),
        "commands": len(bundle.get("commands", {}).get("commands", [])),
        "owners": len(bundle.get("ownership", {}).get("owners", [])),
        "test_evidence": len(bundle.get("test_evidence", {}).get("evidence", [])),
        "decisions": len(bundle.get("decisions", [])),
        "sessions": len(bundle.get("sessions", [])),
    }


def _overall_status(findings: Sequence[Finding]) -> str:
    if any(finding.severity == "error" for finding in findings):
        return "blocked"
    if findings:
        return "attention"
    return "ready"


def _score(findings: Sequence[Finding]) -> int:
    if any(finding.code == "E000" for finding in findings):
        return 0
    penalties = 0
    for finding in findings:
        penalties += 30 if finding.severity == "error" else 8
    return max(0, 100 - min(100, penalties))


def _gates(findings: Sequence[Finding]) -> List[Dict[str, Any]]:
    gates: List[Dict[str, Any]] = []
    for gate_id, name, codes in GATE_DEFINITIONS:
        related = [finding for finding in findings if finding.code in codes]
        if any(item.severity == "error" for item in related):
            status = "fail"
        elif related:
            status = "warn"
        else:
            status = "pass"
        gates.append(
            {
                "id": gate_id,
                "name": name,
                "status": status,
                "summary": _gate_summary(related),
                "finding_codes": [item.code for item in related],
            }
        )
    return gates


def _gate_summary(findings: Sequence[Finding]) -> str:
    if not findings:
        return "No issues found."
    return "; ".join(f"{finding.code}: {finding.message}" for finding in findings)


def _next_actions(findings: Sequence[Finding]) -> List[str]:
    actions: List[str] = []
    for finding in findings:
        action = ACTION_BY_CODE.get(finding.code)
        if not action:
            action = f"Resolve {finding.code}: {finding.message}"
        if action not in actions:
            actions.append(action)
    return actions


def _table_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def _display_path(report: Dict[str, Any], raw_path: str) -> str:
    root = Path(str(report.get("root") or ".")).resolve()
    path = Path(raw_path)
    try:
        return str(path.resolve().relative_to(root)).replace("\\", "/")
    except (OSError, ValueError):
        return str(path).replace("\\", "/")


def _sarif_uri(report: Dict[str, Any], raw_path: str) -> str:
    uri = _display_path(report, raw_path)
    if uri in {"", "."}:
        return "."
    return uri


def _sarif_level(severity: str) -> str:
    if severity == "error":
        return "error"
    if severity == "warning":
        return "warning"
    return "note"
