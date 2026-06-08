from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent_memory_briefcase.utils import dump_json, load_json, slugify, utc_now


class BriefcaseError(RuntimeError):
    """Raised when the bundle layout or command input is invalid."""


@dataclass(frozen=True)
class BundlePaths:
    root: Path
    bundle_dir: Path
    manifest_path: Path
    profile_path: Path
    constraints_path: Path
    glossary_path: Path
    commands_path: Path
    ownership_path: Path
    test_evidence_path: Path
    decisions_dir: Path
    sessions_dir: Path
    exports_dir: Path


def resolve_paths(root: Path) -> BundlePaths:
    root = Path(root).resolve()
    bundle_dir = root / ".agent-memory-briefcase"
    return BundlePaths(
        root=root,
        bundle_dir=bundle_dir,
        manifest_path=bundle_dir / "briefcase.json",
        profile_path=bundle_dir / "profile.json",
        constraints_path=bundle_dir / "constraints.md",
        glossary_path=bundle_dir / "glossary.json",
        commands_path=bundle_dir / "commands.json",
        ownership_path=bundle_dir / "ownership.json",
        test_evidence_path=bundle_dir / "test_evidence.json",
        decisions_dir=bundle_dir / "decisions",
        sessions_dir=bundle_dir / "sessions",
        exports_dir=bundle_dir / "exports",
    )


def _default_constraints(project_name: str) -> str:
    return "\n".join(
        [
            "# Constraints",
            "",
            "## Hard Constraints",
            f"- Keep `{project_name}` offline-first and free of LLM API calls.",
            "- Prefer the Python standard library before adding runtime dependencies.",
            "- Keep artifacts versionable in Markdown and JSON.",
            "",
            "## Taboos",
            "- Do not commit secrets, private keys, or customer-sensitive data.",
            "- Do not rely on a hosted service to reconstruct project memory.",
            "",
            "## Risk Hotspots",
            "- Stale ownership or test evidence can mislead coding agents.",
            "- Briefs that exceed budget can hide important recent decisions.",
            "",
        ]
    )


def _unique_stem(directory: Path, stem: str) -> str:
    candidate = stem
    index = 2
    while (directory / f"{candidate}.json").exists() or (directory / f"{candidate}.md").exists():
        candidate = f"{stem}-{index}"
        index += 1
    return candidate


def _ensure_bundle_exists(paths: BundlePaths) -> None:
    if not paths.bundle_dir.exists():
        raise BriefcaseError(
            f"No briefcase found under {paths.bundle_dir}. Run `agent-memory-briefcase init` first."
        )


def init_bundle(
    root: Path,
    *,
    project_name: Optional[str] = None,
    summary: str = "",
    owners: Optional[List[str]] = None,
    default_branch: str = "main",
    primary_language: str = "Python",
    review_after_days: int = 30,
    force: bool = False,
) -> BundlePaths:
    paths = resolve_paths(root)
    if paths.bundle_dir.exists() and any(paths.bundle_dir.iterdir()) and not force:
        raise BriefcaseError(
            f"Briefcase already exists at {paths.bundle_dir}. Use `--force` to overwrite top-level files."
        )

    paths.bundle_dir.mkdir(parents=True, exist_ok=True)
    paths.decisions_dir.mkdir(parents=True, exist_ok=True)
    paths.sessions_dir.mkdir(parents=True, exist_ok=True)
    paths.exports_dir.mkdir(parents=True, exist_ok=True)

    now = utc_now()
    effective_name = project_name or paths.root.name
    profile = {
        "schema_version": 1,
        "project_name": effective_name,
        "project_summary": summary or "Offline memory bundle for AI coding agents.",
        "owners": owners or [],
        "default_branch": default_branch,
        "primary_language": primary_language,
        "review_after_days": int(review_after_days),
        "brief_defaults": {
            "max_words": 450,
            "max_tokens": 900,
        },
        "created_at": now,
        "updated_at": now,
    }
    manifest = {
        "schema_version": 1,
        "bundle_dir": ".agent-memory-briefcase",
        "files": {
            "profile": "profile.json",
            "constraints": "constraints.md",
            "glossary": "glossary.json",
            "commands": "commands.json",
            "ownership": "ownership.json",
            "test_evidence": "test_evidence.json",
            "decisions": "decisions/",
            "sessions": "sessions/",
            "exports": "exports/",
        },
    }

    dump_json(paths.manifest_path, manifest)
    dump_json(paths.profile_path, profile)
    paths.constraints_path.write_text(
        _default_constraints(effective_name),
        encoding="utf-8",
    )
    dump_json(paths.glossary_path, {"terms": []})
    dump_json(paths.commands_path, {"commands": []})
    dump_json(paths.ownership_path, {"owners": []})
    dump_json(paths.test_evidence_path, {"evidence": []})
    return paths


def parse_constraints(markdown_text: str) -> Dict[str, List[str]]:
    sections = {
        "hard_constraints": [],
        "taboos": [],
        "risk_hotspots": [],
    }
    current: Optional[str] = None
    mapping = {
        "hard constraints": "hard_constraints",
        "taboos": "taboos",
        "risk hotspots": "risk_hotspots",
    }
    for raw_line in markdown_text.splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            current = mapping.get(line[3:].strip().lower())
            continue
        if line.startswith("- ") and current:
            sections[current].append(line[2:].strip())
    return sections


def read_profile(root: Path) -> Dict[str, Any]:
    paths = resolve_paths(root)
    _ensure_bundle_exists(paths)
    return load_json(paths.profile_path, {})


def load_bundle(root: Path) -> Dict[str, Any]:
    paths = resolve_paths(root)
    _ensure_bundle_exists(paths)
    constraints_text = paths.constraints_path.read_text(encoding="utf-8") if paths.constraints_path.exists() else ""
    return {
        "manifest": load_json(paths.manifest_path, {}),
        "profile": load_json(paths.profile_path, {}),
        "constraints": parse_constraints(constraints_text),
        "constraints_markdown": constraints_text,
        "glossary": load_json(paths.glossary_path, {"terms": []}),
        "commands": load_json(paths.commands_path, {"commands": []}),
        "ownership": load_json(paths.ownership_path, {"owners": []}),
        "test_evidence": load_json(paths.test_evidence_path, {"evidence": []}),
        "decisions": _load_entries(paths.decisions_dir),
        "sessions": _load_entries(paths.sessions_dir),
    }


def _load_entries(directory: Path) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    if not directory.exists():
        return entries
    for path in sorted(directory.glob("*.json")):
        payload = load_json(path, {})
        if payload:
            payload["_source"] = str(path)
            entries.append(payload)
    entries.sort(key=lambda item: (item.get("date", ""), item.get("id", "")), reverse=True)
    return entries


def render_decision_markdown(entry: Dict[str, Any]) -> str:
    consequences = entry.get("consequences", [])
    tags = entry.get("tags", [])
    lines = [
        f"# Decision: {entry['title']}",
        "",
        f"- ID: `{entry['id']}`",
        f"- Date: {entry['date']}",
        f"- Status: {entry['status']}",
    ]
    if tags:
        lines.append(f"- Tags: {', '.join(tags)}")
    lines.extend(
        [
            "",
            "## Context",
            entry["context"],
            "",
            "## Decision",
            entry["decision"],
            "",
            "## Consequences",
        ]
    )
    lines.extend(f"- {item}" for item in consequences)
    lines.append("")
    return "\n".join(lines)


def render_session_markdown(entry: Dict[str, Any]) -> str:
    lines = [
        f"# Session: {entry['summary']}",
        "",
        f"- ID: `{entry['id']}`",
        f"- Date: {entry['date']}",
        "",
        "## Changes",
    ]
    lines.extend(f"- {item}" for item in entry.get("changes", []))
    lines.extend(
        [
            "",
            "## Deliverables",
        ]
    )
    lines.extend(f"- {item}" for item in entry.get("deliverables", []))
    lines.extend(
        [
            "",
            "## Tests",
        ]
    )
    lines.extend(f"- {item}" for item in entry.get("tests", []))
    lines.extend(
        [
            "",
            "## Risks",
        ]
    )
    lines.extend(f"- {item}" for item in entry.get("risks", []))
    if entry.get("artifacts"):
        lines.extend(
            [
                "",
                "## Artifacts",
            ]
        )
        lines.extend(f"- {item}" for item in entry["artifacts"])
    lines.append("")
    return "\n".join(lines)


def add_decision(
    root: Path,
    *,
    title: str,
    status: str,
    context: str,
    decision: str,
    consequences: List[str],
    tags: Optional[List[str]] = None,
    date_value: Optional[date] = None,
) -> Dict[str, Any]:
    paths = resolve_paths(root)
    _ensure_bundle_exists(paths)
    entry_date = date_value or date.today()
    base_stem = f"{entry_date.strftime('%Y%m%d')}-{slugify(title)}"
    stem = _unique_stem(paths.decisions_dir, base_stem)
    now = utc_now()
    payload = {
        "id": stem,
        "title": title.strip(),
        "status": status.strip().lower(),
        "date": entry_date.isoformat(),
        "context": context.strip(),
        "decision": decision.strip(),
        "consequences": [item.strip() for item in consequences if item.strip()],
        "tags": [item.strip() for item in (tags or []) if item.strip()],
        "updated_at": now,
    }
    dump_json(paths.decisions_dir / f"{stem}.json", payload)
    (paths.decisions_dir / f"{stem}.md").write_text(
        render_decision_markdown(payload),
        encoding="utf-8",
    )
    return payload


def add_session(
    root: Path,
    *,
    summary: str,
    changes: List[str],
    deliverables: List[str],
    tests: List[str],
    risks: List[str],
    artifacts: Optional[List[str]] = None,
    date_value: Optional[date] = None,
) -> Dict[str, Any]:
    paths = resolve_paths(root)
    _ensure_bundle_exists(paths)
    entry_date = date_value or date.today()
    base_stem = f"{entry_date.strftime('%Y%m%d')}-{slugify(summary)}"
    stem = _unique_stem(paths.sessions_dir, base_stem)
    now = utc_now()
    payload = {
        "id": stem,
        "summary": summary.strip(),
        "date": entry_date.isoformat(),
        "changes": [item.strip() for item in changes if item.strip()],
        "deliverables": [item.strip() for item in deliverables if item.strip()],
        "tests": [item.strip() for item in tests if item.strip()],
        "risks": [item.strip() for item in risks if item.strip()],
        "artifacts": [item.strip() for item in (artifacts or []) if item.strip()],
        "updated_at": now,
    }
    dump_json(paths.sessions_dir / f"{stem}.json", payload)
    (paths.sessions_dir / f"{stem}.md").write_text(
        render_session_markdown(payload),
        encoding="utf-8",
    )
    return payload

