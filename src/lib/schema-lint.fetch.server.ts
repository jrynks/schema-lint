import { isIP } from "node:net";
import { lookup } from "node:dns/promises";

const MAX_BYTES = 1_500_000;
const MAX_REDIRECTS = 5;

function isPrivateAddress(ip: string): boolean {
  if (ip === "::1" || ip === "0.0.0.0") return true;
  if (ip.startsWith("fe80:") || ip.startsWith("fc") || ip.startsWith("fd") || ip.startsWith("::ffff:127.")) {
    return true;
  }
  const v4 = ip.includes(":") && ip.includes(".") ? ip.split(":").pop() ?? ip : ip;
  const parts = v4.split(".").map((n) => Number(n));
  if (parts.length === 4 && parts.every((n) => Number.isInteger(n))) {
    const [a, b] = parts;
    if (a === 10 || a === 127 || a === 0) return true;
    if (a === 169 && b === 254) return true;
    if (a === 172 && b !== undefined && b >= 16 && b <= 31) return true;
    if (a === 192 && b === 168) return true;
    if (a === 100 && b !== undefined && b >= 64 && b <= 127) return true;
    if (a === 198 && (b === 18 || b === 19)) return true;
  }
  return false;
}

function assertSafeUrl(raw: string): URL {
  let url: URL;
  try {
    url = new URL(raw);
  } catch {
    throw new Error("invalid URL");
  }
  if (url.protocol !== "http:" && url.protocol !== "https:") {
    throw new Error(`unsupported scheme: ${url.protocol.replace(":", "")}`);
  }
  if (url.username || url.password) {
    throw new Error("URLs with credentials are not allowed");
  }
  const host = url.hostname.replace(/^\[|\]$/g, "").toLowerCase();
  if (
    host === "localhost" ||
    host.endsWith(".localhost") ||
    host.endsWith(".local") ||
    host.endsWith(".internal") ||
    host === "0.0.0.0" ||
    host === "::1"
  ) {
    throw new Error("private host is not allowed");
  }
  if (isIP(host) && isPrivateAddress(host)) {
    throw new Error("private address is not allowed");
  }
  return url;
}

async function assertPublicHost(hostname: string) {
  if (isIP(hostname)) {
    if (isPrivateAddress(hostname)) throw new Error("private address is not allowed");
    return;
  }
  const records = await lookup(hostname, { all: true });
  if (!records.length) throw new Error("host did not resolve");
  for (const rec of records) {
    if (isPrivateAddress(rec.address)) {
      throw new Error("host resolves to a private address");
    }
  }
}

export type FetchedPage = {
  url: string;
  ok: boolean;
  html: string;
  error: string;
  status: number | null;
};

export async function fetchPage(target: string, timeoutSec = 20, userAgent = "schema-lint/1.0"): Promise<FetchedPage> {
  try {
    let current = assertSafeUrl(target);
    await assertPublicHost(current.hostname);
    const ctrl = AbortSignal.timeout(Math.max(3, timeoutSec) * 1000);
    for (let hop = 0; hop <= MAX_REDIRECTS; hop++) {
      const res = await fetch(current.href, {
        method: "GET",
        redirect: "manual",
        signal: ctrl,
        headers: {
          "User-Agent": userAgent,
          Accept: "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        },
      });
      if (res.status >= 300 && res.status < 400) {
        const loc = res.headers.get("location");
        if (!loc) return { url: target, ok: false, html: "", error: `HTTP ${res.status} with no Location`, status: res.status };
        const next = new URL(loc, current);
        assertSafeUrl(next.href);
        await assertPublicHost(next.hostname);
        current = next;
        continue;
      }
      if (!res.ok) {
        return { url: target, ok: false, html: "", error: `HTTP ${res.status} ${res.statusText}`.trim(), status: res.status };
      }
      const len = Number(res.headers.get("content-length") || "0");
      if (len > MAX_BYTES) {
        return { url: target, ok: false, html: "", error: "response exceeded size limit", status: res.status };
      }
      const buf = new Uint8Array(await res.arrayBuffer());
      if (buf.byteLength > MAX_BYTES) {
        return { url: target, ok: false, html: "", error: "response exceeded size limit", status: res.status };
      }
      const html = new TextDecoder("utf-8").decode(buf);
      return { url: target, ok: true, html, error: "", status: res.status };
    }
    return { url: target, ok: false, html: "", error: "too many redirects", status: null };
  } catch (e) {
    const message = e instanceof Error ? e.message : "fetch failed";
    return { url: target, ok: false, html: "", error: `fetch failed: ${message}`, status: null };
  }
}
