"""Extract JSON-LD from HTML. Never invent blocks that were not on the page."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any

from schema_lint.const import types_of


@dataclass
class LdBlock:
    """One <script type=application/ld+json> block as published."""

    raw: str
    index: int
    parsed: Any = None
    error: str | None = None


@dataclass
class Entity:
    """A flattened JSON-LD node with an @type (from a block or @graph)."""

    node: dict[str, Any]
    types: list[str]
    block_index: int
    path: str
    context: Any = None


@dataclass
class Extraction:
    blocks: list[LdBlock] = field(default_factory=list)
    entities: list[Entity] = field(default_factory=list)
    types_found: list[str] = field(default_factory=list)
    parse_errors: list[str] = field(default_factory=list)


class _JsonLdCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[str] = []
        self._in_ld = False
        self._buf: list[str] = []
        self._script_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "script":
            return
        attr = {k.lower(): (v or "") for k, v in attrs}
        typ = attr.get("type", "").lower().strip()
        # type="application/ld+json" or with charset parameter
        if typ.startswith("application/ld+json"):
            self._in_ld = True
            self._buf = []
            self._script_depth = 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._in_ld:
            raw = "".join(self._buf)
            self.blocks.append(raw)
            self._in_ld = False
            self._buf = []
            self._script_depth = 0

    def handle_data(self, data: str) -> None:
        if self._in_ld:
            self._buf.append(data)

    def handle_comment(self, data: str) -> None:
        # Comments inside the script are still on the page; keep them so the
        # sanitizer can strip them before json.loads. HTMLParser may drop them
        # from handle_data — re-wrap so we do not silently lose payload.
        if self._in_ld:
            self._buf.append("<!--" + data + "-->")


_SCRIPT_RE = re.compile(
    r"<script\b([^>]*)>([\s\S]*?)</script>",
    re.IGNORECASE,
)
_TYPE_RE = re.compile(
    r"""type\s*=\s*(['"])\s*(application/ld\+json[^'"]*)\1""",
    re.IGNORECASE,
)
_TYPE_RE_UNQUOTED = re.compile(
    r"""type\s*=\s*(application/ld\+json[^\s>]*)""",
    re.IGNORECASE,
)


def _extract_with_bs4(html: str) -> list[str] | None:
    try:
        from bs4 import BeautifulSoup  # type: ignore
    except ImportError:
        return None
    features = "html.parser"
    try:
        import lxml  # noqa: F401

        features = "lxml"
    except ImportError:
        pass
    soup = BeautifulSoup(html, features)
    out: list[str] = []
    for script in soup.find_all("script"):
        typ = (script.get("type") or "").lower().strip()
        if typ.startswith("application/ld+json"):
            out.append(script.string if script.string is not None else script.get_text() or "")
    return out


def extract_script_texts(html: str) -> list[str]:
    """Return raw text of every ld+json script, in document order."""
    bs4_blocks = _extract_with_bs4(html)
    if bs4_blocks is not None:
        return bs4_blocks

    parser = _JsonLdCollector()
    try:
        parser.feed(html)
        parser.close()
        if parser.blocks:
            return parser.blocks
    except Exception:
        pass

    # Fallback regex if the parser choked on broken HTML
    blocks: list[str] = []
    for m in _SCRIPT_RE.finditer(html):
        attrs, body = m.group(1), m.group(2)
        if _TYPE_RE.search(attrs) or _TYPE_RE_UNQUOTED.search(attrs):
            blocks.append(body)
    return blocks


def _strip_wrappers(raw: str) -> str:
    s = raw.strip().lstrip("\ufeff")
    # CDATA wrappers (with optional // prefix)
    s = re.sub(r"^//\s*<!\[CDATA\[", "", s)
    s = re.sub(r"//\s*\]\]>\s*$", "", s)
    if s.startswith("<![CDATA[") and s.rstrip().endswith("]]>"):
        s = s[9:].rstrip()
        if s.endswith("]]>"):
            s = s[:-3]
    s = re.sub(r"<!--.*?-->", "", s, flags=re.DOTALL)
    return s.strip().lstrip("\ufeff")


def parse_jsonld_text(raw: str) -> Any:
    """Parse one script body. Raises json.JSONDecodeError on failure."""
    s = _strip_wrappers(raw)
    if not s:
        raise json.JSONDecodeError("empty JSON-LD block", s, 0)
    decoder = json.JSONDecoder()
    objs: list[Any] = []
    idx = 0
    length = len(s)
    while idx < length:
        while idx < length and s[idx].isspace():
            idx += 1
        if idx >= length:
            break
        try:
            obj, end = decoder.raw_decode(s, idx)
        except json.JSONDecodeError:
            if not objs:
                raise
            break
        objs.append(obj)
        idx = end
    if not objs:
        raise json.JSONDecodeError("empty JSON-LD block", s, 0)
    if len(objs) == 1:
        return objs[0]
    return objs


def _context_of(node: dict[str, Any], inherited: Any) -> Any:
    if "@context" in node:
        return node["@context"]
    return inherited


def flatten_entities(parsed: Any, block_index: int, inherited_ctx: Any = None, path: str = "$") -> list[Entity]:
    entities: list[Entity] = []

    def walk(node: Any, ctx: Any, p: str) -> None:
        if isinstance(node, list):
            for i, item in enumerate(node):
                walk(item, ctx, f"{p}[{i}]")
            return
        if not isinstance(node, dict):
            return
        ctx = _context_of(node, ctx)
        graph = node.get("@graph")
        node_types = types_of(node)
        # A typed node is an entity even if it also has @graph.
        if node_types:
            entities.append(
                Entity(node=node, types=node_types, block_index=block_index, path=p, context=ctx)
            )
        elif graph is None and "@type" not in node and p == "$":
            # Top-level object with neither @type nor @graph — still record so
            # @context warnings can fire, but it is not a typed entity.
            pass
        if graph is not None:
            walk(graph, ctx, f"{p}.@graph")

    walk(parsed, inherited_ctx, path)
    return entities


def extract_jsonld(html: str) -> Extraction:
    texts = extract_script_texts(html)
    extraction = Extraction()
    type_order: list[str] = []
    seen_types: set[str] = set()

    for i, raw in enumerate(texts):
        block = LdBlock(raw=raw, index=i)
        try:
            block.parsed = parse_jsonld_text(raw)
        except json.JSONDecodeError as exc:
            block.error = f"invalid JSON in ld+json script: {exc.msg}"
            extraction.parse_errors.append(block.error)
        extraction.blocks.append(block)
        if block.error or block.parsed is None:
            continue
        ents = flatten_entities(block.parsed, i)
        extraction.entities.extend(ents)
        for ent in ents:
            for t in ent.types:
                if t not in seen_types:
                    seen_types.add(t)
                    type_order.append(t)

    extraction.types_found = type_order
    return extraction


def parser_backend() -> dict[str, Any]:
    bs4 = False
    lxml = False
    try:
        import bs4 as _bs4  # noqa: F401

        bs4 = True
    except ImportError:
        pass
    try:
        import lxml  # noqa: F401

        lxml = True
    except ImportError:
        pass
    if bs4:
        name = "beautifulsoup4+lxml" if lxml else "beautifulsoup4+html.parser"
    else:
        name = "stdlib html.parser"
    return {
        "parser": name,
        "beautifulsoup4": bs4,
        "lxml": lxml,
    }
