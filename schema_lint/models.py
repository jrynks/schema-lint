"""Report shapes — schema-lint/v1. Extra internal fields stay off the JSON chip."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from schema_lint import SCHEMA_VERSION


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass
class Issue:
    level: str  # "error" | "warning"
    type: str
    path: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {
            "level": self.level,
            "type": self.type,
            "path": self.path,
            "message": self.message,
        }


@dataclass
class UrlResult:
    url: str
    status: str  # OK | ERRORS | FETCH_FAILED
    types_found: list[str] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    jsonld_count: int = 0

    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.level == "error")

    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.level == "warning")

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "status": self.status,
            "types_found": list(self.types_found),
            "issues": [i.to_dict() for i in self.issues],
            "jsonld_count": self.jsonld_count,
        }


@dataclass
class Report:
    schema: str = SCHEMA_VERSION
    generated_at: str = field(default_factory=utc_now_iso)
    results: list[UrlResult] = field(default_factory=list)
    error_count: int = 0
    warning_count: int = 0

    def recount(self) -> None:
        self.error_count = sum(r.error_count() for r in self.results)
        self.warning_count = sum(r.warning_count() for r in self.results)

    def to_dict(self) -> dict[str, Any]:
        self.recount()
        return {
            "schema": self.schema,
            "generated_at": self.generated_at,
            "results": [r.to_dict() for r in self.results],
            "error_count": self.error_count,
            "warning_count": self.warning_count,
        }

    def exit_code(self) -> int:
        self.recount()
        return 2 if self.error_count > 0 else 0


def issue_error(type_: str, path: str, message: str) -> Issue:
    return Issue(level="error", type=type_, path=path, message=message)


def issue_warn(type_: str, path: str, message: str) -> Issue:
    return Issue(level="warning", type=type_, path=path, message=message)


# Silence unused import if asdict is handy for tests
_ = asdict
