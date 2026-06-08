import json
from datetime import date
from typing import Any, Dict, List, Optional, Sequence, Tuple

from agent_memory_briefcase.linting import run_lint
from agent_memory_briefcase.models import BriefResult
from agent_memory_briefcase.utils import clip_text_to_budget, estimate_tokens, utc_now, word_count


def _list_items(values: Sequence[str]) -> List[str]:
    return [f"- {value}" for value in values if value]


def _section(title: str, items: Sequence[str]) -> List[str]:
    items = [item for item in items if item]
    if not items:
        return []
    return [f"## {title}", *items, ""]


def build_brief_markdown(
    bundle: Dict[str, Any],
    *,
    include_stale_hints: bool = True,
    stale_hints: Optional[Sequence[str]] = None,
) -> str:
    profile = bundle["profile"]
    constraints = bundle["constraints"]
    decisions = bundle["decisions"][:3]
    sessions = bundle["sessions"][:3]
    glossary_terms = bundle["glossary"].get("terms", [])[:8]
    command_items = bundle["commands"].get("commands", [])[:6]
    ownership_items = bundle["ownership"].get("owners", [])[:8]
    evidence_items = bundle["test_evidence"].get("evidence", [])[:6]

    sections: List[str] = [
        "# Agent Memory Brief",
        f"Generated: {utc_now()}",
        "",
    ]

    sections.extend(
        _section(
            "Project",
            [
                f"- Name: {profile.get('project_name', '')}",
                f"- Summary: {profile.get('project_summary', '')}",
                f"- Default branch: {profile.get('default_branch', '')}",
                f"- Primary language: {profile.get('primary_language', '')}",
                f"- Review cadence: every {profile.get('review_after_days', 30)} days",
            ],
        )
    )
    sections.extend(_section("Hard Constraints", _list_items(constraints["hard_constraints"][:8])))
    sections.extend(_section("Taboos", _list_items(constraints["taboos"][:8])))
    sections.extend(_section("Risk Hotspots", _list_items(constraints["risk_hotspots"][:8])))
    sections.extend(
        _section(
            "Recent Decisions",
            [
                f"- {item['date']} [{item['status']}] {item['title']}: {item['decision']}"
                for item in decisions
            ],
        )
    )
    sections.extend(
        _section(
            "Recent Sessions",
            [
                f"- {item['date']} {item['summary']}. Deliverables: {', '.join(item.get('deliverables', [])[:3]) or 'none listed'}."
                for item in sessions
            ],
        )
    )
    sections.extend(
        _section(
            "Glossary",
            [
                f"- {item['term']}: {item['definition']}"
                for item in glossary_terms
                if item.get("term") and item.get("definition")
            ],
        )
    )
    sections.extend(
        _section(
            "Common Commands",
            [
                f"- {item['name']}: `{item['command']}` - {item.get('purpose', '')}"
                for item in command_items
                if item.get("name") and item.get("command")
            ],
        )
    )
    sections.extend(
        _section(
            "Ownership",
            [
                f"- `{item['path']}` owned by {item['owner']} ({item.get('notes', 'no notes')})"
                for item in ownership_items
                if item.get("path") and item.get("owner")
            ],
        )
    )
    sections.extend(
        _section(
            "Test Evidence",
            [
                f"- {item['name']}: {item.get('status', 'unknown')} on {item.get('last_run', 'unknown date')}"
                for item in evidence_items
                if item.get("name")
            ],
        )
    )
    if include_stale_hints:
        sections.extend(_section("Stale Hints", _list_items(list(stale_hints or []))))
    return "\n".join(sections).rstrip() + "\n"


def _truncate_markdown(markdown: str, max_words: int, max_tokens: int) -> Tuple[str, bool]:
    if word_count(markdown) <= max_words and estimate_tokens(markdown) <= max_tokens:
        return markdown, False

    lines = markdown.splitlines()
    kept: List[str] = []
    truncated = False
    for line in lines:
        candidate = ("\n".join(kept + [line]).rstrip() + "\n") if kept or line else "\n"
        if word_count(candidate) <= max_words and estimate_tokens(candidate) <= max_tokens:
            kept.append(line)
            continue
        remaining_words = max_words - word_count("\n".join(kept))
        remaining_tokens = max_tokens - estimate_tokens("\n".join(kept))
        clipped = clip_text_to_budget(line, remaining_words, remaining_tokens)
        if clipped:
            kept.append(clipped)
        truncated = True
        break

    result = "\n".join(kept).rstrip()
    note = "\n\n[Truncated for budget]"
    if truncated:
        candidate = result + note
        if word_count(candidate) <= max_words and estimate_tokens(candidate) <= max_tokens:
            result = candidate
    return result.rstrip() + "\n", truncated


def generate_brief(
    bundle: Dict[str, Any],
    *,
    max_words: int,
    max_tokens: int,
    include_stale_hints: bool = True,
    stale_hints: Optional[Sequence[str]] = None,
) -> BriefResult:
    brief_markdown = build_brief_markdown(
        bundle,
        include_stale_hints=include_stale_hints,
        stale_hints=stale_hints,
    )
    content, truncated = _truncate_markdown(brief_markdown, max_words, max_tokens)
    return BriefResult(
        content=content,
        truncated=truncated,
        word_count=word_count(content),
        estimated_tokens=estimate_tokens(content),
        stale_hints=list(stale_hints or []),
    )


def generate_brief_from_root(
    root,
    *,
    bundle_loader,
    max_words: int,
    max_tokens: int,
    include_stale_hints: bool = True,
    today: Optional[date] = None,
) -> BriefResult:
    bundle = bundle_loader(root)
    stale_hints = [
        f"{finding.code}: {finding.message}"
        for finding in run_lint(root, today=today)
        if finding.code.startswith("W02")
    ]
    return generate_brief(
        bundle,
        max_words=max_words,
        max_tokens=max_tokens,
        include_stale_hints=include_stale_hints,
        stale_hints=stale_hints,
    )


def brief_as_json(bundle: Dict[str, Any], result: BriefResult) -> str:
    payload = {
        "generated_at": utc_now(),
        "project_name": bundle["profile"].get("project_name", ""),
        **result.as_dict(),
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"

