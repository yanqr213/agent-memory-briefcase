# Decision: Mirror memory records in JSON and Markdown

- ID: `20260608-json-and-markdown-mirror`
- Date: 2026-06-08
- Status: accepted
- Tags: storage, documentation

## Context
Agents and humans both need to inspect durable project memory.

## Decision
Store decisions and session summaries in paired JSON and Markdown files.

## Consequences
- Structured tooling can consume JSON directly.
- Code review remains readable with Markdown mirrors.

