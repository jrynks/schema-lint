import { useEffect, useMemo, useState } from "react";
import {
  Check,
  ClipboardCopy,
  LoaderCircle,
  ScanSearch,
  TriangleAlert,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { FIXTURES } from "@/lib/schema-lint/fixtures";
import {
  DEFAULT_TYPES,
  OPTIONAL_TYPES,
  type SchemaLintReport,
  type UrlResult,
} from "@/lib/schema-lint/types";
import { buildReport, checkHtml } from "@/lib/schema-lint/validate";
import { extractJsonLd } from "@/lib/schema-lint/extract";
import { checkUrls, dumpLd } from "@/lib/schema-lint.functions";

const TYPE_OPTIONS = [...DEFAULT_TYPES, ...OPTIONAL_TYPES];

type Mode = "urls" | "html";

function statusTone(status: UrlResult["status"]): "ok" | "error" | "warn" | "fetch" {
  if (status === "OK") return "ok";
  if (status === "FETCH_FAILED") return "fetch";
  return "error";
}

function cliFor(urls: string[], types: string[], strict: boolean): string {
  const u = urls.filter(Boolean);
  const urlPart = u.length ? u.map((x) => JSON.stringify(x)).join(" ") : "URL";
  const typePart = types.length ? ` --types ${types.join(",")}` : "";
  const strictPart = strict ? " --strict-types" : "";
  return `schema-lint --json check ${urlPart}${typePart}${strictPart}`;
}

export function AuditApp() {
  const [mode, setMode] = useState<Mode>("html");
  const [urlText, setUrlText] = useState("https://schema.org/FAQPage");
  const [htmlText, setHtmlText] = useState(FIXTURES[0]?.html ?? "");
  const [types, setTypes] = useState<string[]>([...DEFAULT_TYPES]);
  const [strict, setStrict] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<SchemaLintReport | null>(() => {
    const fx = FIXTURES[0];
    if (!fx) return null;
    return buildReport([checkHtml(fx.html, fx.label, { types: [...DEFAULT_TYPES] })]);
  });
  const [sourceHtml, setSourceHtml] = useState<string>(FIXTURES[0]?.html ?? "");
  const [activeFixture, setActiveFixture] = useState<string | null>(FIXTURES[0]?.id ?? null);
  const [copied, setCopied] = useState<"cli" | "json" | null>(null);
  const [dumpOpen, setDumpOpen] = useState<string | null>(null);

  const urls = useMemo(
    () =>
      urlText
        .split(/\n/)
        .map((s) => s.trim())
        .filter((s) => s && !s.startsWith("#")),
    [urlText],
  );

  const command = cliFor(mode === "urls" ? urls : ["page.html"], types, strict);

  function toggleType(t: string) {
    setTypes((prev) => (prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]));
  }

  function flash(which: "cli" | "json") {
    setCopied(which);
    window.setTimeout(() => setCopied(null), 1400);
  }

  async function copy(text: string, which: "cli" | "json") {
    try {
      await navigator.clipboard.writeText(text);
      flash(which);
    } catch {
      /* ignore */
    }
  }

  function applyFixture(id: string) {
    const fx = FIXTURES.find((f) => f.id === id);
    if (!fx) return;
    setActiveFixture(id);
    setMode("html");
    setHtmlText(fx.html);
    setSourceHtml(fx.html);
    setError(null);
    const result = checkHtml(fx.html, fx.label, { types, strictTypes: strict });
    setReport(buildReport([result]));
  }

  async function runCheck() {
    setBusy(true);
    setError(null);
    setActiveFixture(null);
    try {
      if (mode === "html") {
        if (!htmlText.trim()) {
          setError("Paste HTML that contains a JSON-LD script tag.");
          setReport(null);
          return;
        }
        setSourceHtml(htmlText);
        const result = checkHtml(htmlText, "(pasted HTML)", { types, strictTypes: strict });
        setReport(buildReport([result]));
        return;
      }
      if (!urls.length) {
        setError("Add at least one URL.");
        setReport(null);
        return;
      }
      setSourceHtml("");
      const next = await checkUrls({
        data: { urls: urls.slice(0, 8), types, strictTypes: strict, timeoutSec: 20 },
      });
      setReport(next);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Check failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-dvh bg-background text-foreground">
      <header className="border-b border-border">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-6 sm:flex-row sm:items-end sm:justify-between sm:px-6">
          <div className="stagger-in">
            <p className="font-mono text-xs tracking-[0.28em] text-accent">SITE AUDIT</p>
            <h1 className="mt-2 font-sans text-3xl font-semibold tracking-[-0.03em] text-foreground sm:text-4xl">
              Schema Lint
            </h1>
            <p className="mt-2 max-w-xl text-sm text-muted">
              Fetch pages. Extract JSON-LD. Validate Course, LocalBusiness, and FAQPage. Missing required
              properties are errors. Nothing is invented.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="accent">schema-lint/v1</Badge>
            <Badge>JSON-LD only</Badge>
          </div>
        </div>
      </header>

      <main className="mx-auto grid max-w-6xl gap-6 px-4 py-6 sm:px-6 lg:grid-cols-[minmax(0,22rem)_minmax(0,1fr)] lg:items-start">
        <section className="rounded-xl bg-surface p-4 shadow-[var(--shadow-border)] sm:p-5">
          <div className="flex rounded-lg bg-background p-1">
            {(
              [
                ["urls", "URLs"],
                ["html", "Paste HTML"],
              ] as const
            ).map(([id, label]) => (
              <button
                key={id}
                type="button"
                onClick={() => setMode(id)}
                className={cn(
                  "h-11 flex-1 rounded-md text-sm font-medium transition-colors duration-[var(--motion-quick)]",
                  mode === id ? "bg-surface-2 text-foreground" : "text-muted hover:text-foreground",
                )}
              >
                {label}
              </button>
            ))}
          </div>

          {mode === "urls" ? (
            <label className="mt-4 block">
              <span className="font-mono text-xs uppercase tracking-wide text-subtle">Pages</span>
              <textarea
                value={urlText}
                onChange={(e) => setUrlText(e.target.value)}
                rows={6}
                spellCheck={false}
                className="mt-2 w-full resize-y rounded-md bg-background px-3 py-3 font-mono text-sm text-foreground shadow-[var(--shadow-border)] outline-none placeholder:text-subtle focus:shadow-[var(--shadow-border-hover)]"
                placeholder={"https://example.com/courses\nhttps://example.com/faq"}
              />
            </label>
          ) : (
            <label className="mt-4 block">
              <span className="font-mono text-xs uppercase tracking-wide text-subtle">HTML</span>
              <textarea
                value={htmlText}
                onChange={(e) => setHtmlText(e.target.value)}
                rows={8}
                spellCheck={false}
                className="mt-2 w-full resize-y rounded-md bg-background px-3 py-3 font-mono text-xs leading-relaxed text-foreground shadow-[var(--shadow-border)] outline-none placeholder:text-subtle focus:shadow-[var(--shadow-border-hover)]"
                placeholder={'<script type="application/ld+json">{"@type":"FAQPage"}</script>'}
              />
            </label>
          )}

          <fieldset className="mt-5">
            <legend className="font-mono text-xs uppercase tracking-wide text-subtle">Types</legend>
            <div className="mt-2 flex flex-wrap gap-2">
              {TYPE_OPTIONS.map((t) => {
                const on = types.includes(t);
                const optional = (OPTIONAL_TYPES as readonly string[]).includes(t);
                return (
                  <button
                    key={t}
                    type="button"
                    onClick={() => toggleType(t)}
                    className={cn(
                      "h-11 rounded-sm px-3 font-mono text-xs transition-colors duration-[var(--motion-quick)]",
                      on
                        ? "bg-accent text-accent-fg"
                        : "bg-background text-muted shadow-[var(--shadow-border)] hover:text-foreground",
                    )}
                    aria-label={optional ? `${t} (warn-only)` : t}
                  >
                    {t}
                    {optional ? (
                      <span className="ml-1 opacity-70" aria-hidden="true">
                        w
                      </span>
                    ) : null}
                  </button>
                );
              })}
            </div>
          </fieldset>

          <label className="mt-4 flex min-h-11 items-center gap-3">
            <input
              type="checkbox"
              checked={strict}
              onChange={(e) => setStrict(e.target.checked)}
              className="size-4 accent-accent"
            />
            <span className="text-sm text-foreground">
              Strict types
              <span className="block text-xs text-muted">Error when none of the requested types are present</span>
            </span>
          </label>

          <Button className="mt-4 w-full" onClick={() => void runCheck()} disabled={busy}>
            {busy ? <LoaderCircle className="animate-spin" /> : <ScanSearch />}
            {busy ? "Checking" : "Check structured data"}
          </Button>

          {error ? (
            <p className="mt-3 flex items-start gap-2 text-sm text-error">
              <TriangleAlert className="mt-0.5 size-4 shrink-0" />
              {error}
            </p>
          ) : null}

          <div className="mt-6">
            <p className="font-mono text-xs uppercase tracking-wide text-subtle">Fixtures</p>
            <div className="mt-2 flex flex-col gap-1">
              {FIXTURES.map((fx) => (
                <button
                  key={fx.id}
                  type="button"
                  onClick={() => applyFixture(fx.id)}
                  className={cn(
                    "flex min-h-11 items-center justify-between rounded-md px-3 text-left transition-colors duration-[var(--motion-quick)]",
                    activeFixture === fx.id ? "bg-surface-2" : "hover:bg-background",
                  )}
                >
                  <span>
                    <span className="block text-sm text-foreground">{fx.label}</span>
                    <span className="block text-xs text-muted">{fx.hint}</span>
                  </span>
                  <Badge tone={fx.expect === "OK" ? "ok" : "error"}>{fx.expect}</Badge>
                </button>
              ))}
            </div>
          </div>

          <div className="mt-6 rounded-md bg-background p-3">
            <div className="flex items-center justify-between gap-2">
              <p className="font-mono text-xs uppercase tracking-wide text-subtle">CLI chip</p>
              <button
                type="button"
                onClick={() => void copy(command, "cli")}
                className="inline-flex h-11 items-center gap-1 text-xs text-muted hover:text-foreground"
              >
                {copied === "cli" ? <Check className="size-3.5" /> : <ClipboardCopy className="size-3.5" />}
                Copy
              </button>
            </div>
            <pre className="mt-2 overflow-x-auto whitespace-pre-wrap break-all font-mono text-xs leading-relaxed text-accent">
              {command}
            </pre>
          </div>
        </section>

        <section className="min-w-0">
          {!report ? (
            <EmptyProof />
          ) : (
            <Proof
              report={report}
              sourceHtml={sourceHtml}
              dumpOpen={dumpOpen}
              setDumpOpen={setDumpOpen}
              onCopyJson={() => void copy(JSON.stringify(report, null, 2), "json")}
              copied={copied === "json"}
            />
          )}
        </section>
      </main>
    </div>
  );
}

function EmptyProof() {
  return (
    <div className="rounded-xl bg-surface px-5 py-16 text-center shadow-[var(--shadow-border)]">
      <p className="font-mono text-xs tracking-[0.24em] text-accent">PROOF SHEET</p>
      <h2 className="mt-3 text-xl font-semibold tracking-[-0.02em]">No report yet</h2>
      <p className="mx-auto mt-2 max-w-sm text-sm text-muted">
        Run a fixture to see the schema-lint/v1 chip, or paste a live URL. Microdata and RDFa are ignored.
      </p>
    </div>
  );
}

function Proof({
  report,
  sourceHtml,
  dumpOpen,
  setDumpOpen,
  onCopyJson,
  copied,
}: {
  report: SchemaLintReport;
  sourceHtml: string;
  dumpOpen: string | null;
  setDumpOpen: (v: string | null) => void;
  onCopyJson: () => void;
  copied: boolean;
}) {
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2 rounded-xl bg-surface p-4 shadow-[var(--shadow-border)]">
        <Stat label="Errors" value={report.error_count} tone={report.error_count ? "error" : "ok"} />
        <Stat label="Warnings" value={report.warning_count} tone={report.warning_count ? "warn" : "ok"} />
        <Stat label="Pages" value={report.results.length} tone="accent" />
        <div className="ml-auto">
          <Button variant="secondary" size="sm" onClick={onCopyJson}>
            {copied ? <Check /> : <ClipboardCopy />}
            Copy JSON
          </Button>
        </div>
      </div>

      {report.results.map((r) => (
        <article key={r.url} className="overflow-hidden rounded-xl bg-surface shadow-[var(--shadow-border)]">
          <header className="flex flex-wrap items-start justify-between gap-3 border-b border-border px-4 py-3 sm:px-5">
            <div className="min-w-0">
              <p className="truncate font-mono text-sm text-foreground">{r.url}</p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                <Badge tone={statusTone(r.status)}>{r.status}</Badge>
                <Badge>{r.jsonld_count} JSON-LD</Badge>
                {r.types_found.length ? (
                  r.types_found.map((t) => (
                    <Badge key={t} tone="accent">
                      {t}
                    </Badge>
                  ))
                ) : (
                  <Badge>no types</Badge>
                )}
              </div>
            </div>
            <button
              type="button"
              className="h-11 rounded-sm px-3 font-mono text-xs uppercase tracking-wide text-muted hover:text-foreground"
              onClick={() => setDumpOpen(dumpOpen === r.url ? null : r.url)}
            >
              {dumpOpen === r.url ? "Hide dump" : "Dump JSON-LD"}
            </button>
          </header>

          {dumpOpen === r.url ? <DumpBlock result={r} sourceHtml={sourceHtml} /> : null}

          <ul className="divide-y divide-border">
            {r.issues.length === 0 ? (
              <li className="px-4 py-4 text-sm text-ok sm:px-5">
                No issues. Required properties are present as published.
              </li>
            ) : (
              r.issues.map((issue, i) => (
                <li key={`${issue.path}-${i}`} className="grid grid-cols-[2.25rem_minmax(0,1fr)] gap-3 px-4 py-3 sm:px-5">
                  <span
                    className={cn(
                      "font-mono text-xs font-medium",
                      issue.level === "error" ? "text-error" : "text-warn",
                    )}
                  >
                    {issue.level === "error" ? "E" : "W"}
                  </span>
                  <div className="min-w-0">
                    <p className="text-sm text-foreground">{issue.message}</p>
                    <p className="mt-1 font-mono text-xs text-muted">
                      {issue.type || "—"} · {issue.path || "—"}
                    </p>
                  </div>
                </li>
              ))
            )}
          </ul>
        </article>
      ))}
    </div>
  );
}

function DumpBlock({ result, sourceHtml }: { result: UrlResult; sourceHtml: string }) {
  const isRemote = result.url.startsWith("http://") || result.url.startsWith("https://");
  const local = useMemo(() => {
    if (isRemote) return null;
    const fx = FIXTURES.find((f) => f.label === result.url);
    const html = fx?.html ?? sourceHtml;
    if (!html) return null;
    return extractJsonLd(html);
  }, [isRemote, result.url, sourceHtml]);

  const [remote, setRemote] = useState<string | null>(null);
  const [remoteErr, setRemoteErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isRemote) return;
    let cancelled = false;
    setLoading(true);
    setRemote(null);
    setRemoteErr(null);
    void dumpLd({ data: { url: result.url } })
      .then((dumped) => {
        if (cancelled) return;
        if (dumped.error) setRemoteErr(dumped.error);
        else setRemote(dumped.jsonText);
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        setRemoteErr(e instanceof Error ? e.message : "dump failed");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [isRemote, result.url]);

  if (local) {
    return (
      <pre className="max-h-72 overflow-auto border-b border-border bg-background px-4 py-3 font-mono text-xs leading-relaxed text-accent sm:px-5">
        {JSON.stringify(
          local.blocks.map((b) => (b.error ? { index: b.index, error: b.error } : { index: b.index, jsonld: b.parsed })),
          null,
          2,
        )}
      </pre>
    );
  }

  if (isRemote) {
    return (
      <pre className="max-h-72 overflow-auto border-b border-border bg-background px-4 py-3 font-mono text-xs leading-relaxed text-accent sm:px-5">
        {loading ? "Extracting JSON-LD…" : remoteErr ? remoteErr : remote || "(no JSON-LD blocks)"}
      </pre>
    );
  }

  return (
    <div className="border-b border-border bg-background px-4 py-3 font-mono text-xs text-muted sm:px-5">
      No JSON-LD dump for this result.
    </div>
  );
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "ok" | "error" | "warn" | "accent";
}) {
  const color =
    tone === "error" ? "text-error" : tone === "warn" ? "text-warn" : tone === "ok" ? "text-ok" : "text-accent";
  return (
    <div className="min-w-20">
      <p className="font-mono text-xs uppercase tracking-wide text-subtle">{label}</p>
      <p className={cn("font-mono text-2xl tabular-nums", color)}>{value}</p>
    </div>
  );
}
