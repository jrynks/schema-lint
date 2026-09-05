"""Validate extracted entities against documented required properties.

Missing required props = errors. Never invent fields as present.
"""

from __future__ import annotations

from typing import Any, Iterable

from schema_lint.const import (
    COURSE_FAMILY,
    DEFAULT_TYPES,
    LOCAL_BUSINESS_FAMILY,
    OPTIONAL_TYPES,
    family_for,
    is_course_family,
    is_local_business,
    matches_requested,
    types_of,
)
from schema_lint.extract import Entity, Extraction, extract_jsonld
from schema_lint.fetch import FetchResult, fetch
from schema_lint.models import Issue, UrlResult, issue_error, issue_warn
from schema_lint.props import as_list, has_text, nonempty, text_of


def parse_types_arg(types: str | list[str] | None) -> list[str] | None:
    """None means CLI/library default. Empty list means 'no type filter'."""
    if types is None:
        return None
    if isinstance(types, list):
        return [t.strip() for t in types if str(t).strip()]
    parts = [p.strip() for p in str(types).split(",") if p.strip()]
    return parts


def _schema_org_context(ctx: Any) -> bool:
    if ctx is None:
        return False
    if isinstance(ctx, str):
        return "schema.org" in ctx.lower()
    if isinstance(ctx, list):
        return any(_schema_org_context(x) for x in ctx)
    if isinstance(ctx, dict):
        if _schema_org_context(ctx.get("@vocab")):
            return True
        return any(_schema_org_context(v) for v in ctx.values())
    return False


def _primary_type(types: list[str]) -> str:
    for t in types:
        if t in LOCAL_BUSINESS_FAMILY:
            return t
        if t in COURSE_FAMILY:
            return t
        if t == "FAQPage":
            return t
        if t in OPTIONAL_TYPES:
            return t
    return types[0] if types else ""


def _in_filter(found: list[str], requested: list[str] | None) -> bool:
    if requested is None:
        # default: primary families
        return matches_requested(found, list(DEFAULT_TYPES))
    if not requested:
        return True
    return matches_requested(found, requested)


def _optional_enabled(requested: list[str] | None) -> bool:
    """Optional types are warn-only and on by default; filtered out if --types omits them."""
    if requested is None:
        return True
    if not requested:
        return True
    return any(_in_filter([opt], requested) for opt in OPTIONAL_TYPES)


def _validate_course(ent: Entity, issues: list[Issue]) -> None:
    node = ent.node
    label = _primary_type(ent.types) or "Course"
    base = ent.path

    if "Course" in ent.types or ("CourseInstance" not in ent.types and is_course_family(ent.types)):
        if not has_text(node, "name"):
            issues.append(issue_error(label, f"{base}.name", "missing required property name"))
        if not has_text(node, "description") and not nonempty(node.get("about")):
            issues.append(
                issue_error(
                    label,
                    f"{base}.description",
                    "missing required property description (or about)",
                )
            )
        if not any(nonempty(node.get(k)) for k in ("provider", "organizer", "author")):
            issues.append(
                issue_error(
                    label,
                    f"{base}.provider",
                    "missing required provider, organizer, or author",
                )
            )
        if not has_text(node, "url"):
            issues.append(issue_warn(label, f"{base}.url", "recommended property url is missing"))
        offers = node.get("offers")
        if not nonempty(offers):
            issues.append(issue_warn(label, f"{base}.offers", "recommended property offers is missing"))
        else:
            has_price = False
            for off in as_list(offers):
                if isinstance(off, dict) and (
                    has_text(off, "price") or has_text(off, "lowPrice") or has_text(off, "highPrice")
                ):
                    has_price = True
                    break
                if text_of(off):
                    has_price = True
            if not has_price:
                issues.append(
                    issue_warn(label, f"{base}.offers.price", "recommended offers.price is missing")
                )
        instances = as_list(node.get("hasCourseInstance"))
        if not instances:
            issues.append(
                issue_warn(
                    label,
                    f"{base}.hasCourseInstance",
                    "recommended property hasCourseInstance is missing",
                )
            )
        else:
            for i, inst in enumerate(instances):
                if isinstance(inst, dict):
                    _validate_course_instance(inst, issues, f"{base}.hasCourseInstance[{i}]")
                else:
                    issues.append(
                        issue_warn(
                            label,
                            f"{base}.hasCourseInstance[{i}]",
                            "CourseInstance is not an object; cannot check dates",
                        )
                    )

    if "CourseInstance" in ent.types:
        _validate_course_instance(node, issues, base, label="CourseInstance")


def _validate_course_instance(
    node: dict[str, Any],
    issues: list[Issue],
    path: str,
    *,
    label: str = "CourseInstance",
) -> None:
    if not has_text(node, "startDate"):
        issues.append(issue_warn(label, f"{path}.startDate", "CourseInstance missing startDate"))
    if not has_text(node, "endDate") and not has_text(node, "courseMode"):
        issues.append(
            issue_warn(label, f"{path}.endDate", "CourseInstance missing endDate or courseMode")
        )


def _address_ok(node: dict[str, Any]) -> bool:
    addr = node.get("address")
    if addr is None:
        return False
    if isinstance(addr, str) and addr.strip():
        return True
    for item in as_list(addr):
        if isinstance(item, str) and item.strip():
            return True
        if isinstance(item, dict):
            if text_of(item.get("streetAddress")) or text_of(item.get("addressLocality")):
                return True
    return False


def _has_map(node: dict[str, Any]) -> bool:
    return nonempty(node.get("hasMap"))


def _validate_local_business(ent: Entity, issues: list[Issue]) -> None:
    node = ent.node
    label = _primary_type(ent.types) or "LocalBusiness"
    base = ent.path

    if not has_text(node, "name"):
        issues.append(issue_error(label, f"{base}.name", "missing required property name"))

    if not _address_ok(node) and not _has_map(node):
        issues.append(
            issue_error(
                label,
                f"{base}.address",
                "missing required address (PostalAddress with streetAddress or addressLocality) or hasMap",
            )
        )
    elif not _address_ok(node) and _has_map(node):
        issues.append(
            issue_warn(
                label,
                f"{base}.address",
                "address missing; hasMap is present so location requirement is met",
            )
        )

    if not has_text(node, "telephone") and not has_text(node, "url"):
        issues.append(
            issue_error(
                label,
                f"{base}.telephone",
                "missing telephone and url (at least one is required)",
            )
        )

    if not nonempty(node.get("openingHoursSpecification")) and not has_text(node, "openingHours"):
        issues.append(
            issue_warn(
                label,
                f"{base}.openingHours",
                "recommended openingHours or openingHoursSpecification is missing",
            )
        )
    if not nonempty(node.get("geo")):
        issues.append(issue_warn(label, f"{base}.geo", "recommended property geo is missing"))
    if not nonempty(node.get("image")):
        issues.append(issue_warn(label, f"{base}.image", "recommended property image is missing"))
    if not has_text(node, "priceRange"):
        issues.append(issue_warn(label, f"{base}.priceRange", "recommended property priceRange is missing"))


def _answer_text(q: dict[str, Any]) -> bool:
    ans = q.get("acceptedAnswer")
    if not nonempty(ans):
        return False
    for item in as_list(ans):
        if isinstance(item, str) and item.strip():
            return True
        if isinstance(item, dict) and has_text(item, "text", "name"):
            return True
    return False


def _validate_faq(ent: Entity, issues: list[Issue]) -> None:
    node = ent.node
    label = "FAQPage"
    base = ent.path
    main = node.get("mainEntity")
    if main is None:
        issues.append(issue_error(label, f"{base}.mainEntity", "missing required property mainEntity"))
        return
    questions = as_list(main)
    if len(questions) == 0:
        issues.append(issue_error(label, f"{base}.mainEntity", "FAQPage present with empty mainEntity"))
        return

    expanded: list[tuple[str, Any]] = []
    for i, q in enumerate(questions):
        if isinstance(q, dict) and "Question" not in types_of(q) and types_of(q) == ["ItemList"]:
            for j, el in enumerate(as_list(q.get("itemListElement"))):
                item = el.get("item") if isinstance(el, dict) and "item" in el else el
                expanded.append((f"{base}.mainEntity[{i}].itemListElement[{j}]", item))
        else:
            expanded.append((f"{base}.mainEntity[{i}]", q))

    if not expanded:
        issues.append(issue_error(label, f"{base}.mainEntity", "FAQPage present with empty mainEntity"))
        return

    for path, q in expanded:
        if not isinstance(q, dict):
            issues.append(issue_error(label, path, "mainEntity item is not a Question object"))
            continue
        qtypes = types_of(q)
        if qtypes and "Question" not in qtypes:
            issues.append(
                issue_error(label, f"{path}.@type", f"mainEntity item @type is {qtypes[0]}, expected Question")
            )
        if not has_text(q, "name", "text"):
            issues.append(issue_error(label, f"{path}.name", "Question missing name or text"))
        if not nonempty(q.get("acceptedAnswer")):
            issues.append(issue_error(label, f"{path}.acceptedAnswer", "Question missing acceptedAnswer"))
        elif not _answer_text(q):
            issues.append(
                issue_error(label, f"{path}.acceptedAnswer.text", "acceptedAnswer missing text")
            )


def _validate_organization(ent: Entity, issues: list[Issue]) -> None:
    node = ent.node
    label = _primary_type(ent.types) or "Organization"
    base = ent.path
    if not has_text(node, "name"):
        issues.append(issue_warn(label, f"{base}.name", "Organization missing name"))
    if not has_text(node, "url"):
        issues.append(issue_warn(label, f"{base}.url", "Organization missing url"))


def _validate_website(ent: Entity, issues: list[Issue]) -> None:
    node = ent.node
    base = ent.path
    if not has_text(node, "name"):
        issues.append(issue_warn("WebSite", f"{base}.name", "WebSite missing name"))
    if not has_text(node, "url"):
        issues.append(issue_warn("WebSite", f"{base}.url", "WebSite missing url"))


def _validate_breadcrumb(ent: Entity, issues: list[Issue]) -> None:
    node = ent.node
    base = ent.path
    elements = as_list(node.get("itemListElement"))
    if not elements:
        issues.append(
            issue_warn("BreadcrumbList", f"{base}.itemListElement", "BreadcrumbList missing itemListElement")
        )
        return
    for i, el in enumerate(elements):
        path = f"{base}.itemListElement[{i}]"
        if isinstance(el, dict) and ("item" in el or "position" in el or "name" in el):
            has_name = has_text(el, "name") or (
                isinstance(el.get("item"), dict) and has_text(el["item"], "name")
            ) or (isinstance(el.get("item"), str) and bool(el["item"].strip()))
            if not has_name:
                issues.append(issue_warn("BreadcrumbList", f"{path}.name", "ListItem missing name"))
            if not has_text(el, "position"):
                issues.append(issue_warn("BreadcrumbList", f"{path}.position", "ListItem missing position"))
        elif isinstance(el, dict):
            if not has_text(el, "name"):
                issues.append(issue_warn("BreadcrumbList", f"{path}.name", "breadcrumb entry missing name"))
        else:
            issues.append(issue_warn("BreadcrumbList", path, "breadcrumb entry is not an object"))


def validate_entities(
    entities: Iterable[Entity],
    *,
    requested_types: list[str] | None = None,
) -> list[Issue]:
    issues: list[Issue] = []
    optional_on = _optional_enabled(requested_types)

    for ent in entities:
        types = ent.types
        if not types:
            continue

        run_course = is_course_family(types) and _in_filter(["Course"], requested_types)
        run_local = is_local_business(types) and _in_filter(["LocalBusiness"], requested_types)
        run_faq = "FAQPage" in types and _in_filter(["FAQPage"], requested_types)
        run_org = (
            optional_on
            and not is_local_business(types)
            and (any(t == "Organization" for t in types) or any(t in family_for("Organization") for t in types))
            and _in_filter(["Organization"], requested_types if requested_types is not None else ["Organization"])
        )
        run_site = optional_on and "WebSite" in types and (
            requested_types is None or _in_filter(["WebSite"], requested_types)
        )
        run_crumbs = optional_on and "BreadcrumbList" in types and (
            requested_types is None or _in_filter(["BreadcrumbList"], requested_types)
        )

        active = run_course or run_local or run_faq or run_org or run_site or run_crumbs
        if active and not _schema_org_context(ent.context):
            issues.append(
                issue_warn(
                    _primary_type(types) or "JSON-LD",
                    f"{ent.path}.@context",
                    "missing schema.org @context",
                )
            )

        if run_course:
            _validate_course(ent, issues)
        if run_local:
            _validate_local_business(ent, issues)
        if run_faq:
            _validate_faq(ent, issues)
        if run_org:
            _validate_organization(ent, issues)
        if run_site:
            _validate_website(ent, issues)
        if run_crumbs:
            _validate_breadcrumb(ent, issues)

    return issues


def check_extraction(
    extraction: Extraction,
    *,
    url: str,
    requested_types: list[str] | None = None,
    strict_types: bool = False,
    fail_on_fetch: bool = True,
    fetch_error: str | None = None,
) -> UrlResult:
    if fetch_error:
        level = "error" if fail_on_fetch else "warning"
        return UrlResult(
            url=url,
            status="FETCH_FAILED",
            types_found=[],
            issues=[Issue(level=level, type="", path="", message=fetch_error)],
            jsonld_count=0,
        )

    issues: list[Issue] = []
    for block in extraction.blocks:
        if block.error:
            issues.append(issue_error("JSON-LD", f"$blocks[{block.index}]", block.error))

    issues.extend(validate_entities(extraction.entities, requested_types=requested_types))

    strict_against = list(DEFAULT_TYPES) if requested_types is None else list(requested_types)
    if strict_types:
        if not matches_requested(extraction.types_found, strict_against):
            found = ", ".join(extraction.types_found) if extraction.types_found else "(none)"
            want = ", ".join(strict_against) if strict_against else "(any)"
            issues.append(
                issue_error(
                    "",
                    "$",
                    f"none of the requested types present: {want} (found: {found})",
                )
            )

    errors = [i for i in issues if i.level == "error"]
    status = "ERRORS" if errors else "OK"
    return UrlResult(
        url=url,
        status=status,
        types_found=list(extraction.types_found),
        issues=issues,
        jsonld_count=len(extraction.blocks),
    )


def check_html(
    html: str,
    *,
    url: str = "(html)",
    types: str | list[str] | None = None,
    strict_types: bool = False,
    fail_on_fetch: bool = True,
) -> UrlResult:
    requested = parse_types_arg(types)
    extraction = extract_jsonld(html)
    return check_extraction(
        extraction,
        url=url,
        requested_types=requested,
        strict_types=strict_types,
        fail_on_fetch=fail_on_fetch,
    )


def check_url(
    target: str,
    *,
    types: str | list[str] | None = None,
    strict_types: bool = False,
    timeout_sec: int = 30,
    user_agent: str | None = None,
    fail_on_fetch: bool = True,
) -> tuple[UrlResult, FetchResult]:
    from schema_lint import DEFAULT_USER_AGENT

    fetched = fetch(target, timeout_sec=timeout_sec, user_agent=user_agent or DEFAULT_USER_AGENT)
    requested = parse_types_arg(types)
    if not fetched.ok:
        result = check_extraction(
            Extraction(),
            url=target,
            requested_types=requested,
            strict_types=strict_types,
            fail_on_fetch=fail_on_fetch,
            fetch_error=fetched.error or "fetch failed",
        )
        return result, fetched
    result = check_html(
        fetched.html,
        url=target,
        types=requested,
        strict_types=strict_types,
        fail_on_fetch=fail_on_fetch,
    )
    return result, fetched
