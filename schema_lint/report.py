"""Write schema-lint/v1 JSON chips and human issue lists."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from schema_lint import DEFAULT_OUTPUT_DIR, SCHEMA_VERSION
from schema_lint.models import Report, UrlResult


def build_report(results: list[UrlResult]) -> Report:
    report = Report(schema=SCHEMA_VERSION, results=results)
    report.recount()
    return report


def write_report(report: Report, output_dir: str = DEFAULT_OUTPUT_DIR) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = out / f"report-{stamp}.json"
    payload = json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n"
    path.write_text(payload, encoding="utf-8")
    latest = out / "report-latest.json"
    try:
        latest.write_text(payload, encoding="utf-8")
    except OSError:
        pass
    return path


def format_human(report: Report) -> str:
    report.recount()
    lines: list[str] = []
    for r in report.results:
        types = ", ".join(r.types_found) if r.types_found else "-"
        lines.append(f"{r.url}")
        lines.append(f"  {r.status}  types: {types}  jsonld: {r.jsonld_count}")
        if not r.issues:
            lines.append("  (no issues)")
        for issue in r.issues:
            typ = issue.type or "-"
            path = issue.path or "-"
            lines.append(f"  [{issue.level}] {typ}  {path}  {issue.message}")
        lines.append("")
    lines.append(f"Summary: {report.error_count} error(s), {report.warning_count} warning(s)")
    return "\n".join(lines).rstrip() + "\n"


def format_json(report: Report) -> str:
    return json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n"
