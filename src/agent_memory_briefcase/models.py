from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    message: str
    path: str

    def as_dict(self) -> Dict[str, str]:
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "path": self.path,
        }


@dataclass
class BriefResult:
    content: str
    truncated: bool
    word_count: int
    estimated_tokens: int
    stale_hints: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "truncated": self.truncated,
            "word_count": self.word_count,
            "estimated_tokens": self.estimated_tokens,
            "stale_hints": list(self.stale_hints),
        }

