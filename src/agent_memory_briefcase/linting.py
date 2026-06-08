from datetime import date, timedelta
from pathlib import Path
from typing import Iterable, List, Optional

from agent_memory_briefcase.models import Finding
from agent_memory_briefcase.storage import BundlePaths, load_bundle, resolve_paths


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    snippet = value[:10]
    try:
        return date.fromisoformat(snippet)
    except ValueError:
        return None


def _age_in_days(value: Optional[str], today: date) -> Optional[int]:
    parsed = _parse_date(value)
    if not parsed:
        return None
    return (today - parsed).days


def _entry_path(paths: BundlePaths, relative: Path) -> str:
    return str((paths.bundle_dir / relative).resolve())


def run_lint(root: Path, *, today: Optional[date] = None) -> List[Finding]:
    paths = resolve_paths(root)
    findings: List[Finding] = []
    if not paths.bundle_dir.exists():
        return [
            Finding(
                severity="error",
                code="E000",
                message="Briefcase directory is missing.",
                path=str(paths.bundle_dir),
            )
        ]

    bundle = load_bundle(root)
    profile = bundle["profile"]
    review_after_days = int(profile.get("review_after_days") or 30)
    current_day = today or date.today()

    if not profile.get("project_name"):
        findings.append(
            Finding("error", "E001", "Profile is missing `project_name`.", str(paths.profile_path))
        )
    if not profile.get("project_summary"):
        findings.append(
            Finding("error", "E002", "Profile is missing `project_summary`.", str(paths.profile_path))
        )
    if review_after_days <= 0:
        findings.append(
            Finding(
                "error",
                "E003",
                "`review_after_days` must be a positive integer.",
                str(paths.profile_path),
            )
        )

    constraints = bundle["constraints"]
    if not constraints["hard_constraints"]:
        findings.append(
            Finding(
                "warning",
                "W010",
                "No hard constraints were captured.",
                str(paths.constraints_path),
            )
        )
    if not constraints["taboos"]:
        findings.append(
            Finding(
                "warning",
                "W011",
                "No taboos were captured.",
                str(paths.constraints_path),
            )
        )
    if not bundle["glossary"].get("terms"):
        findings.append(
            Finding("warning", "W012", "Glossary is empty.", str(paths.glossary_path))
        )
    if not bundle["commands"].get("commands"):
        findings.append(
            Finding("warning", "W013", "Command catalog is empty.", str(paths.commands_path))
        )
    if not bundle["ownership"].get("owners"):
        findings.append(
            Finding("warning", "W014", "Ownership map is empty.", str(paths.ownership_path))
        )
    if not bundle["test_evidence"].get("evidence"):
        findings.append(
            Finding("warning", "W015", "Test evidence catalog is empty.", str(paths.test_evidence_path))
        )

    stale_cutoff = timedelta(days=review_after_days)
    profile_age = _age_in_days(profile.get("updated_at"), current_day)
    if profile_age is not None and profile_age > stale_cutoff.days:
        findings.append(
            Finding(
                "warning",
                "W020",
                f"Profile has not been updated in {profile_age} days.",
                str(paths.profile_path),
            )
        )

    sessions = bundle["sessions"]
    if sessions:
        most_recent_session = max((_parse_date(item.get("date")) for item in sessions), default=None)
        if most_recent_session and current_day - most_recent_session > stale_cutoff:
            findings.append(
                Finding(
                    "warning",
                    "W021",
                    f"No recent session archive within {review_after_days} days.",
                    str(paths.sessions_dir),
                )
            )
    else:
        findings.append(
            Finding(
                "warning",
                "W021",
                f"No recent session archive within {review_after_days} days.",
                str(paths.sessions_dir),
            )
        )

    for entry in bundle["ownership"].get("owners", []):
        age = _age_in_days(entry.get("validated_at"), current_day)
        if age is not None and age > stale_cutoff.days:
            findings.append(
                Finding(
                    "warning",
                    "W022",
                    f"Ownership entry `{entry.get('path', '(unknown)')}` is {age} days old.",
                    str(paths.ownership_path),
                )
            )

    for entry in bundle["test_evidence"].get("evidence", []):
        age = _age_in_days(entry.get("last_run"), current_day)
        if age is not None and age > stale_cutoff.days:
            findings.append(
                Finding(
                    "warning",
                    "W023",
                    f"Test evidence `{entry.get('name', '(unknown)')}` is {age} days old.",
                    str(paths.test_evidence_path),
                )
            )

    for entry in bundle["decisions"]:
        age = _age_in_days(entry.get("date"), current_day)
        if entry.get("status") in {"proposed", "trial", "draft"} and age is not None and age > stale_cutoff.days:
            findings.append(
                Finding(
                    "warning",
                    "W024",
                    f"Decision `{entry.get('title', '(unknown)')}` is still {entry.get('status')} after {age} days.",
                    entry.get("_source", str(paths.decisions_dir)),
                )
            )

    findings.extend(_pair_findings(paths.decisions_dir, "W030"))
    findings.extend(_pair_findings(paths.sessions_dir, "W031"))
    return findings


def _pair_findings(directory: Path, code: str) -> Iterable[Finding]:
    stems = {}
    for path in directory.glob("*.*"):
        if path.suffix.lower() not in {".json", ".md"}:
            continue
        stems.setdefault(path.stem, set()).add(path.suffix.lower())
    for stem, suffixes in sorted(stems.items()):
        if suffixes != {".json", ".md"}:
            yield Finding(
                "warning",
                code,
                f"Entry `{stem}` is missing a paired Markdown or JSON file.",
                str(directory / stem),
            )


def highest_severity(findings: Iterable[Finding]) -> Optional[str]:
    rank = {"warning": 1, "error": 2}
    highest = 0
    label = None
    for finding in findings:
        score = rank.get(finding.severity, 0)
        if score > highest:
            highest = score
            label = finding.severity
    return label

