import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";
import { buildReport, checkExtraction, checkHtml } from "@/lib/schema-lint/validate";
import { extractJsonLd } from "@/lib/schema-lint/extract";
import { DEFAULT_TYPES } from "@/lib/schema-lint/types";
import type { SchemaLintReport, UrlResult } from "@/lib/schema-lint/types";

const CheckInput = z.object({
  urls: z.array(z.string().min(1).max(2048)).max(8),
  types: z.array(z.string().min(1).max(64)).max(16).optional(),
  strictTypes: z.boolean().optional(),
  timeoutSec: z.number().int().min(3).max(30).optional(),
});

export const checkUrls = createServerFn({ method: "POST" })
  .validator(CheckInput)
  .handler(async ({ data }): Promise<SchemaLintReport> => {
    const { fetchPage } = await import("@/lib/schema-lint.fetch.server");
    const types = data.types?.length ? data.types : [...DEFAULT_TYPES];
    const results: UrlResult[] = [];
    for (const url of data.urls) {
      const fetched = await fetchPage(url.trim(), data.timeoutSec ?? 20);
      if (!fetched.ok) {
        results.push(
          checkExtraction(
            { blocks: [], entities: [], typesFound: [] },
            {
              url,
              requestedTypes: types,
              strictTypes: data.strictTypes ?? false,
              failOnFetch: true,
              fetchError: fetched.error,
            },
          ),
        );
        continue;
      }
      results.push(
        checkHtml(fetched.html, url, {
          types,
          strictTypes: data.strictTypes ?? false,
        }),
      );
    }
    return buildReport(results);
  });

export type DumpLdResult = {
  url: string;
  error: string | null;
  typesFound: string[];
  jsonText: string;
};

export const dumpLd = createServerFn({ method: "POST" })
  .validator(z.object({ url: z.string().min(1).max(2048) }))
  .handler(async ({ data }): Promise<DumpLdResult> => {
    const { fetchPage } = await import("@/lib/schema-lint.fetch.server");
    const fetched = await fetchPage(data.url.trim(), 20);
    if (!fetched.ok) {
      return { url: data.url, error: fetched.error, typesFound: [], jsonText: "[]" };
    }
    const extraction = extractJsonLd(fetched.html);
    const blocks = extraction.blocks.map((b) =>
      b.error ? { index: b.index, error: b.error } : { index: b.index, jsonld: b.parsed },
    );
    return {
      url: data.url,
      error: null,
      typesFound: extraction.typesFound,
      jsonText: JSON.stringify(blocks, null, 2),
    };
  });
