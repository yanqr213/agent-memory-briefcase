import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import List, Optional

from agent_memory_briefcase.briefing import brief_as_json, generate_brief_from_root
from agent_memory_briefcase.linting import highest_severity, run_lint
from agent_memory_briefcase.render import render_json_export, render_markdown_export
from agent_memory_briefcase.storage import (
    BriefcaseError,
    add_decision,
    add_session,
    init_bundle,
    load_bundle,
    read_profile,
)
from agent_memory_briefcase.utils import dump_json, ensure_parent


def _parse_date(raw: Optional[str]) -> Optional[date]:
    if not raw:
        return None
    return date.fromisoformat(raw)


def _write_output(path: Path, content: str) -> None:
    ensure_parent(path)
    path.write_text(content, encoding="utf-8")


def _print_findings(findings, output_format: str) -> None:
    if output_format == "json":
        print(json.dumps([item.as_dict() for item in findings], indent=2, ensure_ascii=False))
        return
    if not findings:
        print("No findings.")
        return
    for finding in findings:
        print(f"[{finding.severity.upper()}] {finding.code} {finding.message} ({finding.path})")


def _exit_for_threshold(findings, threshold: Optional[str]) -> int:
    if not threshold:
        return 0
    rank = {"warning": 1, "error": 2}
    highest = highest_severity(findings)
    if highest and rank[highest] >= rank[threshold]:
        return 1
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    paths = init_bundle(
        Path(args.root),
        project_name=args.project_name,
        summary=args.summary,
        owners=args.owner or [],
        default_branch=args.default_branch,
        primary_language=args.primary_language,
        review_after_days=args.review_after_days,
        force=args.force,
    )
    print(f"Initialized briefcase at {paths.bundle_dir}")
    return 0


def cmd_add_decision(args: argparse.Namespace) -> int:
    entry = add_decision(
        Path(args.root),
        title=args.title,
        status=args.status,
        context=args.context,
        decision=args.decision,
        consequences=args.consequence or [],
        tags=args.tag or [],
        date_value=_parse_date(args.date),
    )
    print(f"Created decision {entry['id']}")
    return 0


def cmd_add_session(args: argparse.Namespace) -> int:
    entry = add_session(
        Path(args.root),
        summary=args.summary,
        changes=args.change or [],
        deliverables=args.deliverable or [],
        tests=args.test or [],
        risks=args.risk or [],
        artifacts=args.artifact or [],
        date_value=_parse_date(args.date),
    )
    print(f"Created session {entry['id']}")
    return 0


def cmd_brief(args: argparse.Namespace) -> int:
    profile = read_profile(Path(args.root))
    defaults = profile.get("brief_defaults", {})
    max_words = args.max_words or int(defaults.get("max_words", 450))
    max_tokens = args.max_tokens or int(defaults.get("max_tokens", 900))
    bundle = load_bundle(Path(args.root))
    result = generate_brief_from_root(
        Path(args.root),
        bundle_loader=load_bundle,
        max_words=max_words,
        max_tokens=max_tokens,
        include_stale_hints=args.include_stale_hints,
        today=_parse_date(args.today),
    )
    content = (
        brief_as_json(bundle, result)
        if args.format == "json"
        else result.content
    )
    if args.output:
        target = Path(args.output)
        _write_output(target, content)
        print(f"Wrote brief to {target.resolve()}")
    else:
        print(content, end="")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    bundle = load_bundle(Path(args.root))
    content = (
        render_json_export(bundle)
        if args.format == "json"
        else render_markdown_export(bundle)
    )
    if args.output:
        target = Path(args.output)
        _write_output(target, content)
        print(f"Wrote export to {target.resolve()}")
    else:
        print(content, end="")
    return 0


def cmd_lint(args: argparse.Namespace) -> int:
    findings = run_lint(Path(args.root), today=_parse_date(args.today))
    _print_findings(findings, args.format)
    return _exit_for_threshold(findings, args.check)


def cmd_check(args: argparse.Namespace) -> int:
    findings = run_lint(Path(args.root), today=_parse_date(args.today))
    _print_findings(findings, args.format)
    threshold = args.check or "error"
    return _exit_for_threshold(findings, threshold)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-memory-briefcase",
        description="Manage offline memory bundles for coding agents.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    root_help = "Project root that contains or will contain .agent-memory-briefcase."

    init_parser = subparsers.add_parser("init", help="Initialize a memory briefcase.")
    init_parser.add_argument("--root", default=".", help=root_help)
    init_parser.add_argument("--project-name")
    init_parser.add_argument("--summary", default="")
    init_parser.add_argument("--owner", action="append", help="Repeat to add profile owners.")
    init_parser.add_argument("--default-branch", default="main")
    init_parser.add_argument("--primary-language", default="Python")
    init_parser.add_argument("--review-after-days", type=int, default=30)
    init_parser.add_argument("--force", action="store_true")
    init_parser.set_defaults(func=cmd_init)

    decision_parser = subparsers.add_parser("add-decision", help="Add an ADR-style decision.")
    decision_parser.add_argument("--root", default=".", help=root_help)
    decision_parser.add_argument("--title", required=True)
    decision_parser.add_argument(
        "--status",
        default="accepted",
        choices=["accepted", "proposed", "rejected", "superseded", "trial", "draft"],
    )
    decision_parser.add_argument("--context", required=True)
    decision_parser.add_argument("--decision", required=True)
    decision_parser.add_argument("--consequence", action="append", help="Repeat to add consequences.")
    decision_parser.add_argument("--tag", action="append", help="Repeat to add tags.")
    decision_parser.add_argument("--date")
    decision_parser.set_defaults(func=cmd_add_decision)

    session_parser = subparsers.add_parser("add-session", help="Archive a work session summary.")
    session_parser.add_argument("--root", default=".", help=root_help)
    session_parser.add_argument("--summary", required=True)
    session_parser.add_argument("--change", action="append", help="Repeat to add key changes.")
    session_parser.add_argument("--deliverable", action="append", help="Repeat to add deliverables.")
    session_parser.add_argument("--test", action="append", help="Repeat to add tests.")
    session_parser.add_argument("--risk", action="append", help="Repeat to add risks.")
    session_parser.add_argument("--artifact", action="append", help="Repeat to add artifacts.")
    session_parser.add_argument("--date")
    session_parser.set_defaults(func=cmd_add_session)

    brief_parser = subparsers.add_parser("brief", help="Generate an agent-ready context brief.")
    brief_parser.add_argument("--root", default=".", help=root_help)
    brief_parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    brief_parser.add_argument("--max-words", type=int)
    brief_parser.add_argument("--max-tokens", type=int)
    brief_parser.add_argument("--output")
    brief_parser.add_argument("--today", help="Override the current day in YYYY-MM-DD format.")
    brief_parser.add_argument(
        "--include-stale-hints",
        dest="include_stale_hints",
        action="store_true",
        default=True,
    )
    brief_parser.add_argument(
        "--no-stale-hints",
        dest="include_stale_hints",
        action="store_false",
    )
    brief_parser.set_defaults(func=cmd_brief)

    lint_parent = argparse.ArgumentParser(add_help=False)
    lint_parent.add_argument("--root", default=".", help=root_help)
    lint_parent.add_argument("--format", choices=["text", "json"], default="text")
    lint_parent.add_argument("--today", help="Override the current day in YYYY-MM-DD format.")
    lint_parent.add_argument(
        "--check",
        choices=["warning", "error"],
        help="Return a failing exit code when the selected severity is present.",
    )

    lint_parser = subparsers.add_parser("lint", parents=[lint_parent], help="Report bundle findings.")
    lint_parser.set_defaults(func=cmd_lint)

    check_parser = subparsers.add_parser("check", parents=[lint_parent], help="CI-friendly validation.")
    check_parser.set_defaults(func=cmd_check)

    export_parser = subparsers.add_parser("export", help="Export the full bundle as Markdown or JSON.")
    export_parser.add_argument("--root", default=".", help=root_help)
    export_parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    export_parser.add_argument("--output")
    export_parser.set_defaults(func=cmd_export)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except BriefcaseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
