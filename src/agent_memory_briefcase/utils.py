import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "entry"


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def dump_json(path: Path, payload: Any) -> None:
    ensure_parent(path)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def word_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, math.ceil(len(text) / 4))


def clip_text_to_budget(text: str, max_words: int, max_tokens: int) -> str:
    if max_words <= 0 or max_tokens <= 0:
        return ""
    words = text.split()
    if not words:
        return ""
    kept = []
    for word in words:
        candidate = " ".join(kept + [word])
        if word_count(candidate) <= max_words and estimate_tokens(candidate) <= max_tokens:
            kept.append(word)
            continue
        break
    if not kept:
        return ""
    clipped = " ".join(kept)
    if clipped != text.strip():
        candidate = clipped.rstrip(" ,;:") + " ..."
        if word_count(candidate) <= max_words and estimate_tokens(candidate) <= max_tokens:
            return candidate
    return clipped

