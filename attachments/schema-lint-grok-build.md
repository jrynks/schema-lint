# schema-lint — Grok Build prompt

Local Linux CLI for agent **Site Audit**. Fetch pages, extract JSON-LD, validate Course / LocalBusiness / FAQPage (and related). Exit non-zero on validation errors.

## Context (for humans)

**Token-burn goal:** Prefer this fast local CLI + compact `--json` chips over browserUse/computerUse loops, giant chat dumps, or re-scraping the same URLs in-agent. The agent should invoke `schema-lint` once, read the small structured output under `/tmp/schema-lint/`, and move on — not re-drive a browser for scores/prices/variants.

- Used after lighthouse/axe to check structured data quality for SEO / rich results eligibility signals.
- Validates against documented required properties — does not invent missing fields as present.
- Exit non-zero when errors found so agents can gate workflows.

---

## Prompt (paste into Grok Build)

```text
Build a local Linux CLI `schema-lint` (Python 3.11+, stdlib + urllib; optional beautifulsoup4/lxml) for agent Site Audit.

## Purpose
TOKEN BURN: Designed so the agent shells this CLI once and consumes a small JSON/CSV chip — not browserUse loops, not pasting full HTML into chat, not re-fetching in the LLM.
Fetch one or more URLs, extract JSON-LD (`application/ld+json`), and validate common Schema.org types used by Jason’s clients:
- Course / CourseInstance
- LocalBusiness (and subtypes: ProfessionalService, MedicalBusiness, etc. treated as LocalBusiness family)
- FAQPage (mainEntity Question/Answer)
Optional: Organization, WebSite, BreadcrumbList (warn-only by default).

NEVER invent JSON-LD that was not on the page. Missing required props = errors. Exit non-zero when any error-level issue exists.

## Commands

### `schema-lint check URL [URL...] [--types Course,LocalBusiness,FAQPage] [--strict-types] [--out /tmp/schema-lint]`
OR `schema-lint check --urls urls.txt …`
For each URL:
1) HTTP GET (follow redirects; timeout configurable)
2) Parse all ld+json blocks (handle @graph arrays and single objects; expand @type lists)
3) Validate per type rules below
4) Emit per-url + batch report

### Validation rules (error vs warning)

Course (error if type requested/found):
- required: name, description (or about), provider OR organizer OR author (at least one)
- recommended (warn): url, offers / offers.price, hasCourseInstance
- CourseInstance: startDate, endDate or courseMode when instance present — warn if instance missing dates

LocalBusiness family:
- required: name, address (PostalAddress with streetAddress or addressLocality at min) OR hasMap
- required-ish: telephone OR url (error if both missing)
- recommended (warn): openingHoursSpecification / openingHours, geo, image, priceRange

FAQPage:
- required: mainEntity as list of Question
- each Question: name/text + acceptedAnswer with text
- error if FAQPage present with empty mainEntity

@context: warn if missing schema.org context
Invalid JSON in ld+json script: error

### Output schema "schema-lint/v1"
{
  "schema": "schema-lint/v1",
  "generated_at": "ISO8601",
  "results": [
    {
      "url": "…",
      "status": "OK"|"ERRORS"|"FETCH_FAILED",
      "types_found": ["FAQPage", "Organization"],
      "issues": [
        {"level": "error"|"warning", "type": "FAQPage", "path": "mainEntity[0].acceptedAnswer", "message": "…"}
      ],
      "jsonld_count": 2
    }
  ],
  "error_count": 3,
  "warning_count": 1
}

Exit 0 if error_count == 0 (warnings allowed).
Exit 2 if error_count > 0 OR any FETCH_FAILED when --fail-on-fetch (default: fetch fail counts as error).

### `schema-lint doctor`
Print parser deps, output_dir, default types.

### `schema-lint dump-ld URL`
Extract and pretty-print JSON-LD only (debug) — still never invent.

## Flags
- `--types` filter which found types to validate; if --strict-types, also error when none of the requested types are present on the page
- `--json` global stdout JSON
- `--timeout-sec` default 30
- `--user-agent` configurable

## Constraints / non-goals
- No invented structured data
- No auto-fix / writing corrected JSON-LD back to the site
- No Microdata/RDFa required in v1 (JSON-LD only; optional future)
- Do not call Google Rich Results Test API unless optionally documented behind a flag (default off — local validation only)

## Packaging
pyproject.toml → schema-lint = schema_lint.cli:main
pip install -e .
Unit tests with fixture HTML: valid FAQPage OK; missing Question answer → error exit 2; broken JSON-LD → error; LocalBusiness missing name+address → error; Course minimal pass

## Output contract
Always write /tmp/schema-lint/report-*.json
Stdout human issue list unless --json
```

## After install (Site Audit)

```bash
pip install -e .
schema-lint doctor
schema-lint --json check https://example.com/courses --types Course,FAQPage --strict-types
schema-lint check --urls ./pages.txt
```
