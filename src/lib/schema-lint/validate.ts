import {
  COURSE_FAMILY,
  LOCAL_BUSINESS_FAMILY,
  familyFor,
  matchesRequested,
  typesOf,
} from "./const";
import { extractJsonLd } from "./extract";
import { asList, hasText, nonempty, textOf } from "./props";
import {
  DEFAULT_TYPES,
  OPTIONAL_TYPES,
  type CheckOptions,
  type Entity,
  type Extraction,
  type Issue,
  type UrlResult,
} from "./types";

function err(type: string, path: string, message: string): Issue {
  return { level: "error", type, path, message };
}
function warn(type: string, path: string, message: string): Issue {
  return { level: "warning", type, path, message };
}

function schemaOrgContext(ctx: unknown): boolean {
  if (ctx == null) return false;
  if (typeof ctx === "string") return ctx.toLowerCase().includes("schema.org");
  if (Array.isArray(ctx)) return ctx.some(schemaOrgContext);
  if (typeof ctx === "object") {
    const rec = ctx as Record<string, unknown>;
    if (schemaOrgContext(rec["@vocab"])) return true;
    return Object.values(rec).some(schemaOrgContext);
  }
  return false;
}

function primaryType(types: string[]): string {
  for (const t of types) {
    if (LOCAL_BUSINESS_FAMILY.has(t) || COURSE_FAMILY.has(t) || t === "FAQPage" || OPTIONAL_TYPES.includes(t as (typeof OPTIONAL_TYPES)[number])) {
      return t;
    }
  }
  return types[0] ?? "";
}

function inFilter(found: string[], requested: string[] | null | undefined): boolean {
  if (requested == null) return matchesRequested(found, [...DEFAULT_TYPES]);
  if (!requested.length) return true;
  return matchesRequested(found, requested);
}

function optionalOn(requested: string[] | null | undefined): boolean {
  if (requested == null || !requested.length) return true;
  return OPTIONAL_TYPES.some((opt) => inFilter([opt], requested));
}

function isLocal(types: string[]): boolean {
  return types.some((t) => LOCAL_BUSINESS_FAMILY.has(t));
}
function isCourse(types: string[]): boolean {
  return types.some((t) => COURSE_FAMILY.has(t));
}

function validateCourseInstance(node: Record<string, unknown>, issues: Issue[], path: string, label = "CourseInstance") {
  if (!hasText(node, "startDate")) {
    issues.push(warn(label, `${path}.startDate`, "CourseInstance missing startDate"));
  }
  if (!hasText(node, "endDate") && !hasText(node, "courseMode")) {
    issues.push(warn(label, `${path}.endDate`, "CourseInstance missing endDate or courseMode"));
  }
}

function validateCourse(ent: Entity, issues: Issue[]) {
  const node = ent.node;
  const label = primaryType(ent.types) || "Course";
  const base = ent.path;
  if (ent.types.includes("Course") || (!ent.types.includes("CourseInstance") && isCourse(ent.types))) {
    if (!hasText(node, "name")) issues.push(err(label, `${base}.name`, "missing required property name"));
    if (!hasText(node, "description") && !nonempty(node.about)) {
      issues.push(err(label, `${base}.description`, "missing required property description (or about)"));
    }
    if (!["provider", "organizer", "author"].some((k) => nonempty(node[k]))) {
      issues.push(err(label, `${base}.provider`, "missing required provider, organizer, or author"));
    }
    if (!hasText(node, "url")) issues.push(warn(label, `${base}.url`, "recommended property url is missing"));
    const offers = node.offers;
    if (!nonempty(offers)) {
      issues.push(warn(label, `${base}.offers`, "recommended property offers is missing"));
    } else {
      let hasPrice = false;
      for (const off of asList(offers)) {
        if (off && typeof off === "object" && !Array.isArray(off)) {
          const rec = off as Record<string, unknown>;
          if (hasText(rec, "price") || hasText(rec, "lowPrice") || hasText(rec, "highPrice")) {
            hasPrice = true;
            break;
          }
        }
        if (textOf(off)) {
          hasPrice = true;
          break;
        }
      }
      if (!hasPrice) issues.push(warn(label, `${base}.offers.price`, "recommended offers.price is missing"));
    }
    const instances = asList(node.hasCourseInstance);
    if (!instances.length) {
      issues.push(warn(label, `${base}.hasCourseInstance`, "recommended property hasCourseInstance is missing"));
    } else {
      instances.forEach((inst, i) => {
        if (inst && typeof inst === "object" && !Array.isArray(inst)) {
          validateCourseInstance(inst as Record<string, unknown>, issues, `${base}.hasCourseInstance[${i}]`);
        } else {
          issues.push(warn(label, `${base}.hasCourseInstance[${i}]`, "CourseInstance is not an object; cannot check dates"));
        }
      });
    }
  }
  if (ent.types.includes("CourseInstance")) {
    validateCourseInstance(node, issues, base, "CourseInstance");
  }
}

function addressOk(node: Record<string, unknown>): boolean {
  const addr = node.address;
  if (addr == null) return false;
  if (typeof addr === "string" && addr.trim()) return true;
  for (const item of asList(addr)) {
    if (typeof item === "string" && item.trim()) return true;
    if (item && typeof item === "object" && !Array.isArray(item)) {
      const rec = item as Record<string, unknown>;
      if (textOf(rec.streetAddress) || textOf(rec.addressLocality)) return true;
    }
  }
  return false;
}

function validateLocal(ent: Entity, issues: Issue[]) {
  const node = ent.node;
  const label = primaryType(ent.types) || "LocalBusiness";
  const base = ent.path;
  if (!hasText(node, "name")) issues.push(err(label, `${base}.name`, "missing required property name"));
  const hasMap = nonempty(node.hasMap);
  if (!addressOk(node) && !hasMap) {
    issues.push(
      err(
        label,
        `${base}.address`,
        "missing required address (PostalAddress with streetAddress or addressLocality) or hasMap",
      ),
    );
  } else if (!addressOk(node) && hasMap) {
    issues.push(warn(label, `${base}.address`, "address missing; hasMap is present so location requirement is met"));
  }
  if (!hasText(node, "telephone") && !hasText(node, "url")) {
    issues.push(err(label, `${base}.telephone`, "missing telephone and url (at least one is required)"));
  }
  if (!nonempty(node.openingHoursSpecification) && !hasText(node, "openingHours")) {
    issues.push(warn(label, `${base}.openingHours`, "recommended openingHours or openingHoursSpecification is missing"));
  }
  if (!nonempty(node.geo)) issues.push(warn(label, `${base}.geo`, "recommended property geo is missing"));
  if (!nonempty(node.image)) issues.push(warn(label, `${base}.image`, "recommended property image is missing"));
  if (!hasText(node, "priceRange")) issues.push(warn(label, `${base}.priceRange`, "recommended property priceRange is missing"));
}

function answerText(q: Record<string, unknown>): boolean {
  const ans = q.acceptedAnswer;
  if (!nonempty(ans)) return false;
  for (const item of asList(ans)) {
    if (typeof item === "string" && item.trim()) return true;
    if (item && typeof item === "object" && !Array.isArray(item) && hasText(item as Record<string, unknown>, "text", "name")) {
      return true;
    }
  }
  return false;
}

function validateFaq(ent: Entity, issues: Issue[]) {
  const node = ent.node;
  const label = "FAQPage";
  const base = ent.path;
  const main = node.mainEntity;
  if (main == null) {
    issues.push(err(label, `${base}.mainEntity`, "missing required property mainEntity"));
    return;
  }
  const questions = asList(main);
  if (!questions.length) {
    issues.push(err(label, `${base}.mainEntity`, "FAQPage present with empty mainEntity"));
    return;
  }
  const expanded: Array<[string, unknown]> = [];
  questions.forEach((q, i) => {
    if (q && typeof q === "object" && !Array.isArray(q) && typesOf(q).join() === "ItemList") {
      asList((q as Record<string, unknown>).itemListElement).forEach((el, j) => {
        const item =
          el && typeof el === "object" && !Array.isArray(el) && "item" in el
            ? (el as Record<string, unknown>).item
            : el;
        expanded.push([`${base}.mainEntity[${i}].itemListElement[${j}]`, item]);
      });
    } else {
      expanded.push([`${base}.mainEntity[${i}]`, q]);
    }
  });
  if (!expanded.length) {
    issues.push(err(label, `${base}.mainEntity`, "FAQPage present with empty mainEntity"));
    return;
  }
  for (const [path, q] of expanded) {
    if (!q || typeof q !== "object" || Array.isArray(q)) {
      issues.push(err(label, path, "mainEntity item is not a Question object"));
      continue;
    }
    const rec = q as Record<string, unknown>;
    const qtypes = typesOf(rec);
    if (qtypes.length && !qtypes.includes("Question")) {
      issues.push(err(label, `${path}.@type`, `mainEntity item @type is ${qtypes[0]}, expected Question`));
    }
    if (!hasText(rec, "name", "text")) issues.push(err(label, `${path}.name`, "Question missing name or text"));
    if (!nonempty(rec.acceptedAnswer)) {
      issues.push(err(label, `${path}.acceptedAnswer`, "Question missing acceptedAnswer"));
    } else if (!answerText(rec)) {
      issues.push(err(label, `${path}.acceptedAnswer.text`, "acceptedAnswer missing text"));
    }
  }
}

function validateOrg(ent: Entity, issues: Issue[]) {
  const node = ent.node;
  const label = primaryType(ent.types) || "Organization";
  if (!hasText(node, "name")) issues.push(warn(label, `${ent.path}.name`, "Organization missing name"));
  if (!hasText(node, "url")) issues.push(warn(label, `${ent.path}.url`, "Organization missing url"));
}

function validateWebsite(ent: Entity, issues: Issue[]) {
  if (!hasText(ent.node, "name")) issues.push(warn("WebSite", `${ent.path}.name`, "WebSite missing name"));
  if (!hasText(ent.node, "url")) issues.push(warn("WebSite", `${ent.path}.url`, "WebSite missing url"));
}

function validateBreadcrumb(ent: Entity, issues: Issue[]) {
  const elements = asList(ent.node.itemListElement);
  if (!elements.length) {
    issues.push(warn("BreadcrumbList", `${ent.path}.itemListElement`, "BreadcrumbList missing itemListElement"));
    return;
  }
  elements.forEach((el, i) => {
    const path = `${ent.path}.itemListElement[${i}]`;
    if (el && typeof el === "object" && !Array.isArray(el)) {
      const rec = el as Record<string, unknown>;
      const hasName =
        hasText(rec, "name") ||
        (rec.item && typeof rec.item === "object" && !Array.isArray(rec.item) && hasText(rec.item as Record<string, unknown>, "name")) ||
        (typeof rec.item === "string" && rec.item.trim().length > 0);
      if (!hasName) issues.push(warn("BreadcrumbList", `${path}.name`, "ListItem missing name"));
      if ("item" in rec || "position" in rec || "name" in rec) {
        if (!hasText(rec, "position")) issues.push(warn("BreadcrumbList", `${path}.position`, "ListItem missing position"));
      }
    } else {
      issues.push(warn("BreadcrumbList", path, "breadcrumb entry is not an object"));
    }
  });
}

export function validateEntities(entities: Entity[], requestedTypes: string[] | null = null): Issue[] {
  const issues: Issue[] = [];
  const opt = optionalOn(requestedTypes);
  for (const ent of entities) {
    const types = ent.types;
    if (!types.length) continue;
    const runCourse = isCourse(types) && inFilter(["Course"], requestedTypes);
    const runLocal = isLocal(types) && inFilter(["LocalBusiness"], requestedTypes);
    const runFaq = types.includes("FAQPage") && inFilter(["FAQPage"], requestedTypes);
    const runOrg =
      opt &&
      !isLocal(types) &&
      (types.includes("Organization") || types.some((t) => familyFor("Organization").has(t))) &&
      inFilter(["Organization"], requestedTypes ?? ["Organization"]);
    const runSite = opt && types.includes("WebSite") && (requestedTypes == null || inFilter(["WebSite"], requestedTypes));
    const runCrumbs =
      opt && types.includes("BreadcrumbList") && (requestedTypes == null || inFilter(["BreadcrumbList"], requestedTypes));
    const active = runCourse || runLocal || runFaq || runOrg || runSite || runCrumbs;
    if (active && !schemaOrgContext(ent.context)) {
      issues.push(warn(primaryType(types) || "JSON-LD", `${ent.path}.@context`, "missing schema.org @context"));
    }
    if (runCourse) validateCourse(ent, issues);
    if (runLocal) validateLocal(ent, issues);
    if (runFaq) validateFaq(ent, issues);
    if (runOrg) validateOrg(ent, issues);
    if (runSite) validateWebsite(ent, issues);
    if (runCrumbs) validateBreadcrumb(ent, issues);
  }
  return issues;
}

export function checkExtraction(
  extraction: Extraction,
  opts: { url: string; requestedTypes?: string[] | null; strictTypes?: boolean; failOnFetch?: boolean; fetchError?: string | null },
): UrlResult {
  if (opts.fetchError) {
    return {
      url: opts.url,
      status: "FETCH_FAILED",
      types_found: [],
      issues: [
        {
          level: opts.failOnFetch === false ? "warning" : "error",
          type: "",
          path: "",
          message: opts.fetchError,
        },
      ],
      jsonld_count: 0,
    };
  }
  const issues: Issue[] = [];
  for (const block of extraction.blocks) {
    if (block.error) issues.push(err("JSON-LD", `$blocks[${block.index}]`, block.error));
  }
  issues.push(...validateEntities(extraction.entities, opts.requestedTypes ?? null));
  const strictAgainst = opts.requestedTypes == null ? [...DEFAULT_TYPES] : opts.requestedTypes;
  if (opts.strictTypes && !matchesRequested(extraction.typesFound, strictAgainst)) {
    const found = extraction.typesFound.length ? extraction.typesFound.join(", ") : "(none)";
    const want = strictAgainst.length ? strictAgainst.join(", ") : "(any)";
    issues.push(err("", "$", `none of the requested types present: ${want} (found: ${found})`));
  }
  const errors = issues.filter((i) => i.level === "error");
  return {
    url: opts.url,
    status: errors.length ? "ERRORS" : "OK",
    types_found: [...extraction.typesFound],
    issues,
    jsonld_count: extraction.blocks.length,
  };
}

export function checkHtml(html: string, url = "(html)", options: CheckOptions = {}): UrlResult {
  const extraction = extractJsonLd(html);
  return checkExtraction(extraction, {
    url,
    requestedTypes: options.types ?? null,
    strictTypes: options.strictTypes ?? false,
    failOnFetch: options.failOnFetch ?? true,
  });
}

export function buildReport(results: UrlResult[]): {
  schema: "schema-lint/v1";
  generated_at: string;
  results: UrlResult[];
  error_count: number;
  warning_count: number;
} {
  const error_count = results.reduce((n, r) => n + r.issues.filter((i) => i.level === "error").length, 0);
  const warning_count = results.reduce((n, r) => n + r.issues.filter((i) => i.level === "warning").length, 0);
  return {
    schema: "schema-lint/v1",
    generated_at: new Date().toISOString().replace(/\.\d{3}Z$/, "Z"),
    results,
    error_count,
    warning_count,
  };
}
