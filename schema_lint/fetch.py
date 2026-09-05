"""HTTP GET with redirects. Local files are allowed so agents can lint fixtures."""

from __future__ import annotations

import ssl
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from schema_lint import DEFAULT_TIMEOUT_SEC, DEFAULT_USER_AGENT

MAX_BODY_BYTES = 5 * 1024 * 1024


@dataclass
class FetchResult:
    url: str
    ok: bool
    html: str = ""
    error: str = ""
    status_code: int | None = None
    final_url: str = ""
    content_type: str = ""


def _looks_like_path(target: str) -> bool:
    if target.startswith("file:"):
        return True
    parsed = urlparse(target)
    if parsed.scheme in ("http", "https"):
        return False
    # bare paths, Windows-ish, or scheme-less
    if parsed.scheme in ("", "file"):
        return True
    return False


def _read_limited(fp: BinaryIO, limit: int = MAX_BODY_BYTES) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        buf = fp.read(64 * 1024)
        if not buf:
            break
        total += len(buf)
        if total > limit:
            raise OSError(f"response exceeded {limit} bytes")
        chunks.append(buf)
    return b"".join(chunks)


def _decode(body: bytes, content_type: str) -> str:
    charset = "utf-8"
    if "charset=" in content_type.lower():
        charset = content_type.lower().split("charset=", 1)[1].split(";")[0].strip().strip("\"'")
    for enc in (charset, "utf-8", "utf-8-sig", "latin-1"):
        try:
            return body.decode(enc)
        except (LookupError, UnicodeDecodeError):
            continue
    return body.decode("utf-8", errors="replace")


def fetch(target: str, timeout_sec: int = DEFAULT_TIMEOUT_SEC, user_agent: str = DEFAULT_USER_AGENT) -> FetchResult:
    """Fetch a URL or read a local HTML file. Does not invent page content."""
    target = (target or "").strip()
    if not target:
        return FetchResult(url=target, ok=False, error="empty URL")

    if _looks_like_path(target):
        path_str = target[7:] if target.startswith("file://") else target[5:] if target.startswith("file:") else target
        path = Path(path_str)
        if not path.is_file():
            return FetchResult(url=target, ok=False, error=f"file not found: {path}")
        try:
            data = path.read_bytes()
            if len(data) > MAX_BODY_BYTES:
                return FetchResult(url=target, ok=False, error="file exceeded size limit")
            html = _decode(data, "text/html; charset=utf-8")
            return FetchResult(url=str(path), ok=True, html=html, status_code=200, final_url=str(path.resolve()), content_type="text/html")
        except OSError as exc:
            return FetchResult(url=target, ok=False, error=f"cannot read file: {exc}")

    parsed = urlparse(target)
    if parsed.scheme not in ("http", "https"):
        return FetchResult(url=target, ok=False, error=f"unsupported scheme: {parsed.scheme or '(none)'}")

    req = Request(target, headers={"User-Agent": user_agent, "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8"})
    ctx = ssl.create_default_context()
    try:
        with urlopen(req, timeout=timeout_sec, context=ctx) as resp:  # nosec B310 - scheme checked
            status = getattr(resp, "status", None) or resp.getcode()
            final = resp.geturl() or target
            ctype = resp.headers.get("Content-Type", "") if resp.headers else ""
            body = _read_limited(resp)
            html = _decode(body, ctype)
            return FetchResult(
                url=target,
                ok=True,
                html=html,
                status_code=int(status) if status else 200,
                final_url=final,
                content_type=ctype,
            )
    except HTTPError as exc:
        # Still try to parse error-page HTML if present — but a 4xx/5xx is a
        # fetch failure for scoring (the page the agent asked for did not load).
        return FetchResult(
            url=target,
            ok=False,
            error=f"HTTP {exc.code} {exc.reason}",
            status_code=exc.code,
        )
    except TimeoutError:
        return FetchResult(url=target, ok=False, error=f"timeout after {timeout_sec}s")
    except URLError as exc:
        reason = getattr(exc, "reason", exc)
        return FetchResult(url=target, ok=False, error=f"fetch failed: {reason}")
    except OSError as exc:
        return FetchResult(url=target, ok=False, error=f"fetch failed: {exc}")
