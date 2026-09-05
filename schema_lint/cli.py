"""schema-lint CLI — agent Site Audit chip generator."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from schema_lint import (
    DEFAULT_OUTPUT_DIR,
    DEFAULT_TIMEOUT_SEC,
    DEFAULT_USER_AGENT,
    SCHEMA_VERSION,
    __version__,
)
from schema_lint.const import DEFAULT_TYPES, OPTIONAL_TYPES, PRIMARY_TYPES
from schema_lint.extract import extract_jsonld, parser_backend
from schema_lint.fetch import fetch
from schema_lint.report import build_report, format_human, format_json, write_report
from schema_lint.validate import check_url


def _read_url_file(path: str) -> list[str]:
    text = Path(path).read_text(encoding="utf-8")
    urls: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        urls.append(s)
    return urls


def _collect_targets(urls: list[str] | None, url_files: list[str] | None) -> list[str]:
    targets: list[str] = []
    for f in url_files or []:
        targets.extend(_read_url_file(f))
    targets.extend(urls or [])
    seen: set[str] = set()
    out: list[str] = []
    for t in targets:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def cmd_doctor(args: argparse.Namespace) -> int:
    backend = parser_backend()
    lines = [
        f"schema-lint {__version__}",
        f"schema: {SCHEMA_VERSION}",
        f"python: {sys.version.split()[0]}",
        f"parser: {backend['parser']}",
        f"beautifulsoup4: {'installed' if backend['beautifulsoup4'] else 'not installed'}",
        f"lxml: {'installed' if backend['lxml'] else 'not installed'}",
        f"output_dir: {args.out}",
        f"default_types: {', '.join(DEFAULT_TYPES)}",
        f"optional_types (warn-only): {', '.join(OPTIONAL_TYPES)}",
        f"primary_types: {', '.join(PRIMARY_TYPES)}",
        f"fail_on_fetch: {args.fail_on_fetch}",
        f"timeout_sec: {args.timeout_sec}",
        f"user_agent: {args.user_agent}",
    ]
    if args.json:
        payload = {
            "schema": SCHEMA_VERSION,
            "version": __version__,
            "python": sys.version.split()[0],
            **backend,
            "output_dir": args.out,
            "default_types": list(DEFAULT_TYPES),
            "optional_types": list(OPTIONAL_TYPES),
            "fail_on_fetch": args.fail_on_fetch,
            "timeout_sec": args.timeout_sec,
            "user_agent": args.user_agent,
        }
        sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    else:
        sys.stdout.write("\n".join(lines) + "\n")
    return 0


def cmd_dump_ld(args: argparse.Namespace) -> int:
    targets = _collect_targets(args.urls, args.url_files)
    if not targets:
        sys.stderr.write("schema-lint dump-ld: no URLs given\n")
        return 1
    failed = False
    dumped: list[dict] = []
    for target in targets:
        fetched = fetch(target, timeout_sec=args.timeout_sec, user_agent=args.user_agent)
        if not fetched.ok:
            failed = True
            dumped.append({"url": target, "error": fetched.error, "blocks": []})
            if not args.json:
                sys.stdout.write(f"# {target}\n# FETCH_FAILED {fetched.error}\n\n")
            continue
        extraction = extract_jsonld(fetched.html)
        blocks_out = []
        for b in extraction.blocks:
            if b.error:
                blocks_out.append({"index": b.index, "error": b.error, "raw": b.raw})
            else:
                blocks_out.append({"index": b.index, "jsonld": b.parsed})
        dumped.append({"url": target, "blocks": blocks_out, "types_found": extraction.types_found})
        if not args.json:
            sys.stdout.write(f"# {target}\n")
            if not extraction.blocks:
                sys.stdout.write("# (no JSON-LD blocks)\n\n")
            for b in extraction.blocks:
                if b.error:
                    sys.stdout.write(f"# block {b.index} ERROR {b.error}\n{b.raw}\n\n")
                else:
                    sys.stdout.write(json.dumps(b.parsed, indent=2, ensure_ascii=False) + "\n\n")
    if args.json:
        sys.stdout.write(json.dumps(dumped, indent=2, ensure_ascii=False) + "\n")
    return 2 if failed else 0


def cmd_check(args: argparse.Namespace) -> int:
    targets = _collect_targets(args.urls, args.url_files)
    if not targets:
        sys.stderr.write("schema-lint check: no URLs given (pass URL arguments or --urls FILE)\n")
        return 1
    # None → library default (primary + optional warn-only)
    types_arg: str | None
    if args.types is None:
        types_arg = None
    else:
        types_arg = args.types
    results = []
    for target in targets:
        result, _fetched = check_url(
            target,
            types=types_arg,
            strict_types=args.strict_types,
            timeout_sec=args.timeout_sec,
            user_agent=args.user_agent,
            fail_on_fetch=args.fail_on_fetch,
        )
        results.append(result)
    report = build_report(results)
    path = write_report(report, output_dir=args.out)
    if args.json:
        sys.stdout.write(format_json(report))
    else:
        sys.stdout.write(format_human(report))
        sys.stderr.write(f"wrote {path}\n")
    return report.exit_code()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="schema-lint",
        description="Fetch pages, extract JSON-LD, validate Course / LocalBusiness / FAQPage. Never invent structured data.",
    )
    parser.add_argument("--json", action="store_true", help="write schema-lint/v1 JSON to stdout")
    parser.add_argument("--out", default=DEFAULT_OUTPUT_DIR, help="directory for report-*.json (default: /tmp/schema-lint)")
    parser.add_argument("--timeout-sec", type=int, default=DEFAULT_TIMEOUT_SEC)
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    parser.add_argument(
        "--fail-on-fetch",
        dest="fail_on_fetch",
        action="store_true",
        default=True,
        help="treat FETCH_FAILED as an error (default)",
    )
    parser.add_argument(
        "--no-fail-on-fetch",
        dest="fail_on_fetch",
        action="store_false",
        help="treat FETCH_FAILED as a warning",
    )
    parser.add_argument("--version", action="version", version=f"schema-lint {__version__}")

    sub = parser.add_subparsers(dest="cmd")

    p_check = sub.add_parser("check", help="fetch + validate one or more URLs")
    p_check.add_argument("urls", nargs="*", help="page URLs or local HTML files")
    p_check.add_argument("--urls", dest="url_files", action="append", metavar="FILE", help="file of URLs (one per line)")
    p_check.add_argument(
        "--types",
        default=None,
        help="comma-separated types to validate (default: Course,LocalBusiness,FAQPage; optional types warn-only)",
    )
    p_check.add_argument(
        "--strict-types",
        action="store_true",
        help="error when none of the requested types are present on the page",
    )
    p_check.set_defaults(func=cmd_check)

    p_doc = sub.add_parser("doctor", help="print parser deps, output_dir, default types")
    p_doc.set_defaults(func=cmd_doctor)

    p_dump = sub.add_parser("dump-ld", help="extract and pretty-print JSON-LD only (never invent)")
    p_dump.add_argument("urls", nargs="*", help="page URLs or local HTML files")
    p_dump.add_argument("--urls", dest="url_files", action="append", metavar="FILE")
    p_dump.set_defaults(func=cmd_dump_ld)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    if not args.cmd:
        parser.print_help()
        return 1
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
