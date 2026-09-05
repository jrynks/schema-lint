# schema-lint

Local Linux CLI for agent **Site Audit**. Fetch pages, extract JSON-LD, validate Course / LocalBusiness / FAQPage (and related). Exit non-zero on validation errors.

Never invents JSON-LD that was not on the page. Missing required properties are errors.

## Install

```bash
pip install -e .
schema-lint doctor
```

Optional HTML parser: `pip install -e '.[html]'` (beautifulsoup4 + lxml). Stdlib `html.parser` is enough.

## Commands

```bash
schema-lint doctor
schema-lint --json check https://example.com/courses --types Course,FAQPage --strict-types
schema-lint check --urls ./pages.txt
schema-lint dump-ld https://example.com/faq
schema-lint check ./tests/fixtures/faq_valid.html
```

Always writes `/tmp/schema-lint/report-*.json` (override with `--out`).

Stdout is a human issue list unless `--json`.

### Exit codes

| Code | Meaning |
| --- | --- |
| 0 | `error_count == 0` (warnings allowed) |
| 1 | usage error |
| 2 | validation errors, or `FETCH_FAILED` when `--fail-on-fetch` (default) |

## schema-lint/v1 chip

```json
{
  "schema": "schema-lint/v1",
  "generated_at": "ISO8601",
  "results": [
    {
      "url": "…",
      "status": "OK",
      "types_found": ["FAQPage"],
      "issues": [
        {"level": "error", "type": "FAQPage", "path": "mainEntity[0].acceptedAnswer", "message": "…"}
      ],
      "jsonld_count": 1
    }
  ],
  "error_count": 0,
  "warning_count": 0
}
```

## Validation (error vs warning)

**Course** — required: `name`, `description` (or `about`), `provider` **or** `organizer` **or** `author`. Recommended (warn): `url`, `offers` / `offers.price`, `hasCourseInstance`. CourseInstance dates are warnings.

**LocalBusiness family** (Dentist, ProfessionalService, MedicalBusiness, …) — required: `name`, `address` (PostalAddress with `streetAddress` or `addressLocality`) **or** `hasMap`; `telephone` **or** `url`. Recommended (warn): hours, `geo`, `image`, `priceRange`.

**FAQPage** — `mainEntity` as Question list; each Question needs `name`/`text` and `acceptedAnswer.text`. Empty `mainEntity` is an error.

**Optional (warn-only):** Organization, WebSite, BreadcrumbList.

Invalid JSON in an `application/ld+json` script is an error. Missing schema.org `@context` is a warning. Microdata / RDFa are out of scope (JSON-LD only).

## Tests

```bash
python -m unittest discover -s tests -v
```
