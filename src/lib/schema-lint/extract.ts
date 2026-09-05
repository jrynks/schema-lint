import { typesOf } from "./const";
import type { Entity, Extraction, LdBlock } from "./types";

const SCRIPT_RE = /<script\b([^>]*)>([\s\S]*?)<\/script>/gi;
const TYPE_RE = /type\s*=\s*(['"])\s*(application\/ld\+json[^'"]*)\1/i;
const TYPE_UNQUOTED = /type\s*=\s*(application\/ld\+json[^\s>]*)/i;

export function extractScriptTexts(html: string): string[] {
  if (typeof DOMParser !== "undefined") {
    try {
      const doc = new DOMParser().parseFromString(html, "text/html");
      const nodes = Array.from(doc.querySelectorAll('script[type]'));
      const out: string[] = [];
      for (const el of nodes) {
        const typ = (el.getAttribute("type") || "").toLowerCase().trim();
        if (typ.startsWith("application/ld+json")) {
          out.push(el.textContent ?? "");
        }
      }
      if (out.length) return out;
    } catch {
      // fall through to regex
    }
  }
  const blocks: string[] = [];
  SCRIPT_RE.lastIndex = 0;
  let m: RegExpExecArray | null;
  while ((m = SCRIPT_RE.exec(html))) {
    const attrs = m[1] ?? "";
    const body = m[2] ?? "";
    if (TYPE_RE.test(attrs) || TYPE_UNQUOTED.test(attrs)) {
      blocks.push(body);
    }
    TYPE_RE.lastIndex = 0;
    TYPE_UNQUOTED.lastIndex = 0;
  }
  return blocks;
}

function stripWrappers(raw: string): string {
  let s = raw.trim().replace(/^\uFEFF/, "");
  s = s.replace(/^\/\/\s*<!\[CDATA\[/, "");
  s = s.replace(/\/\/\s*\]\]>\s*$/, "");
  if (s.startsWith("<![CDATA[") && s.trimEnd().endsWith("]]>")) {
    s = s.slice(9);
    if (s.endsWith("]]>")) s = s.slice(0, -3);
  }
  s = s.replace(/<!--[\s\S]*?-->/g, "");
  return s.trim().replace(/^\uFEFF/, "");
}

export function parseJsonLdText(raw: string): unknown {
  const s = stripWrappers(raw);
  if (!s) throw new SyntaxError("empty JSON-LD block");
  // Support concatenated top-level values the way json.JSONDecoder.raw_decode does.
  const objs: unknown[] = [];
  let idx = 0;
  while (idx < s.length) {
    while (idx < s.length && /\s/.test(s[idx] ?? "")) idx += 1;
    if (idx >= s.length) break;
    const slice = s.slice(idx);
    try {
      const parsed = JSON.parse(slice) as unknown;
      objs.push(parsed);
      // JSON.parse consumed the whole remainder — we're done.
      break;
    } catch {
      // Try to parse one value by walking braces/brackets.
      const one = decodeOne(s, idx);
      if (!one) {
        if (!objs.length) throw new SyntaxError("invalid JSON in ld+json script");
        break;
      }
      objs.push(one.value);
      idx = one.end;
    }
  }
  if (!objs.length) throw new SyntaxError("empty JSON-LD block");
  return objs.length === 1 ? objs[0] : objs;
}

function decodeOne(s: string, start: number): { value: unknown; end: number } | null {
  const ch = s[start];
  if (ch !== "{" && ch !== "[") {
    // primitive
    const prim = s.slice(start).match(/^(null|true|false|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)/);
    if (prim) {
      return { value: JSON.parse(prim[0]) as unknown, end: start + prim[0].length };
    }
    if (ch === '"') {
      const end = endOfString(s, start);
      if (end < 0) return null;
      return { value: JSON.parse(s.slice(start, end)) as unknown, end };
    }
    return null;
  }
  let depth = 0;
  let inStr = false;
  let esc = false;
  for (let i = start; i < s.length; i++) {
    const c = s[i] ?? "";
    if (inStr) {
      if (esc) {
        esc = false;
        continue;
      }
      if (c === "\\") {
        esc = true;
        continue;
      }
      if (c === '"') inStr = false;
      continue;
    }
    if (c === '"') {
      inStr = true;
      continue;
    }
    if (c === "{" || c === "[") depth += 1;
    else if (c === "}" || c === "]") {
      depth -= 1;
      if (depth === 0) {
        const chunk = s.slice(start, i + 1);
        try {
          return { value: JSON.parse(chunk) as unknown, end: i + 1 };
        } catch {
          return null;
        }
      }
    }
  }
  return null;
}

function endOfString(s: string, start: number): number {
  let esc = false;
  for (let i = start + 1; i < s.length; i++) {
    const c = s[i];
    if (esc) {
      esc = false;
      continue;
    }
    if (c === "\\") {
      esc = true;
      continue;
    }
    if (c === '"') return i + 1;
  }
  return -1;
}

function flattenEntities(parsed: unknown, blockIndex: number): Entity[] {
  const entities: Entity[] = [];

  function walk(node: unknown, ctx: unknown, path: string) {
    if (Array.isArray(node)) {
      node.forEach((item, i) => walk(item, ctx, `${path}[${i}]`));
      return;
    }
    if (!node || typeof node !== "object") return;
    const rec = node as Record<string, unknown>;
    const nextCtx = "@context" in rec ? rec["@context"] : ctx;
    const graph = rec["@graph"];
    const nodeTypes = typesOf(rec);
    if (nodeTypes.length) {
      entities.push({
        node: rec,
        types: nodeTypes,
        blockIndex,
        path,
        context: nextCtx,
      });
    }
    if (graph !== undefined) walk(graph, nextCtx, `${path}.@graph`);
  }

  walk(parsed, null, "$");
  return entities;
}

export function extractJsonLd(html: string): Extraction {
  const texts = extractScriptTexts(html);
  const blocks: LdBlock[] = [];
  const entities: Entity[] = [];
  const typeOrder: string[] = [];
  const seen = new Set<string>();

  texts.forEach((raw, i) => {
    const block: LdBlock = { raw, index: i, parsed: null, error: null };
    try {
      block.parsed = parseJsonLdText(raw);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "invalid JSON";
      block.error = msg.startsWith("invalid JSON") ? `invalid JSON in ld+json script: ${msg}` : `invalid JSON in ld+json script: ${msg}`;
    }
    blocks.push(block);
    if (block.error || block.parsed == null) return;
    const ents = flattenEntities(block.parsed, i);
    entities.push(...ents);
    for (const ent of ents) {
      for (const t of ent.types) {
        if (!seen.has(t)) {
          seen.add(t);
          typeOrder.push(t);
        }
      }
    }
  });

  return { blocks, entities, typesFound: typeOrder };
}
