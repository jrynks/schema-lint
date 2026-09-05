"""Adversarial cases: never invent JSON-LD; do not treat missing fields as present."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from schema_lint.cli import main
from schema_lint.extract import extract_jsonld
from schema_lint.validate import check_html


def ld(obj: dict | list, *, script_type: str = "application/ld+json") -> str:
    return f'<html><head><script type="{script_type}">{json.dumps(obj)}</script></head><body></body></html>'


class AdversarialTests(unittest.TestCase):
    def test_type_as_schema_url(self) -> None:
        page = ld(
            {
                "@context": "https://schema.org",
                "@type": "https://schema.org/FAQPage",
                "mainEntity": [
                    {
                        "@type": "https://schema.org/Question",
                        "name": "Q",
                        "acceptedAnswer": {"@type": "Answer", "text": "A"},
                    }
                ],
            }
        )
        r = check_html(page, url="url-type")
        self.assertEqual(r.status, "OK")
        self.assertIn("FAQPage", r.types_found)

    def test_type_array_course_and_product(self) -> None:
        page = ld(
            {
                "@context": "https://schema.org",
                "@type": ["Course", "Product"],
                "name": "Lab",
                "description": "Hands-on",
                "provider": "Ledger",
            }
        )
        r = check_html(page, url="arr-type")
        self.assertIn("Course", r.types_found)
        self.assertIn("Product", r.types_found)
        self.assertEqual(r.error_count(), 0)

    def test_address_string_counts(self) -> None:
        page = ld(
            {
                "@context": "https://schema.org",
                "@type": "LocalBusiness",
                "name": "Shop",
                "telephone": "604-555-0100",
                "address": "2100 Shaughnessy St, Port Coquitlam",
            }
        )
        r = check_html(page, url="addr-str")
        self.assertEqual(r.error_count(), 0)

    def test_address_country_only_fails(self) -> None:
        page = ld(
            {
                "@context": "https://schema.org",
                "@type": "LocalBusiness",
                "name": "Shop",
                "url": "https://shop.example",
                "address": {"@type": "PostalAddress", "addressCountry": "CA"},
            }
        )
        r = check_html(page, url="addr-weak")
        self.assertEqual(r.status, "ERRORS")
        self.assertTrue(any(".address" in i.path for i in r.issues if i.level == "error"))

    def test_telephone_only_ok(self) -> None:
        page = ld(
            {
                "@context": "https://schema.org",
                "@type": "LocalBusiness",
                "name": "Shop",
                "telephone": "+1-604-555-0100",
                "address": {"streetAddress": "1 Main", "addressLocality": "Vancouver"},
            }
        )
        r = check_html(page, url="tel-only")
        self.assertFalse(any("telephone" in i.path and i.level == "error" for i in r.issues))

    def test_organizer_satisfies_course(self) -> None:
        page = ld(
            {
                "@context": "https://schema.org",
                "@type": "Course",
                "name": "GST",
                "description": "Tax",
                "organizer": {"name": "Ledger"},
            }
        )
        r = check_html(page, url="orgn")
        self.assertEqual(r.error_count(), 0)

    def test_empty_accepted_answer_object(self) -> None:
        page = ld(
            {
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": [{"@type": "Question", "name": "Q", "acceptedAnswer": {}}],
            }
        )
        r = check_html(page, url="empty-ans")
        self.assertEqual(r.status, "ERRORS")

    def test_accepted_answer_as_string(self) -> None:
        page = ld(
            {
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": [{"@type": "Question", "name": "Q", "acceptedAnswer": "Because."}],
            }
        )
        r = check_html(page, url="ans-str")
        self.assertEqual(r.error_count(), 0)

    def test_script_type_with_charset(self) -> None:
        body = json.dumps(
            {
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": [{"@type": "Question", "name": "Q", "acceptedAnswer": {"text": "A"}}],
            }
        )
        page = f'<script type="application/ld+json; charset=utf-8">{body}</script>'
        r = check_html(page, url="charset")
        self.assertEqual(r.status, "OK")
        self.assertEqual(r.jsonld_count, 1)

    def test_mixed_broken_and_valid(self) -> None:
        page = """
        <script type="application/ld+json">{not json</script>
        <script type="application/ld+json">
        {"@context":"https://schema.org","@type":"FAQPage",
         "mainEntity":[{"@type":"Question","name":"Q","acceptedAnswer":{"text":"A"}}]}
        </script>
        """
        r = check_html(page, url="mixed")
        self.assertEqual(r.status, "ERRORS")
        self.assertIn("FAQPage", r.types_found)
        self.assertEqual(r.jsonld_count, 2)
        self.assertTrue(any(i.type == "JSON-LD" for i in r.issues))

    def test_top_level_array(self) -> None:
        page = ld(
            [
                {
                    "@context": "https://schema.org",
                    "@type": "Organization",
                    "name": "Ledger",
                    "url": "https://ledger.example",
                },
                {
                    "@context": "https://schema.org",
                    "@type": "WebSite",
                    "name": "Ledger",
                    "url": "https://ledger.example",
                },
            ]
        )
        r = check_html(page, url="arr")
        self.assertIn("Organization", r.types_found)
        self.assertIn("WebSite", r.types_found)
        self.assertEqual(r.error_count(), 0)

    def test_microdata_is_ignored(self) -> None:
        page = """
        <div itemscope itemtype="https://schema.org/FAQPage">
          <div itemprop="mainEntity" itemscope itemtype="https://schema.org/Question">
            <span itemprop="name">Q</span>
          </div>
        </div>
        """
        r = check_html(page, url="microdata")
        self.assertEqual(r.types_found, [])
        self.assertEqual(r.jsonld_count, 0)

    def test_empty_script_is_error(self) -> None:
        page = '<script type="application/ld+json">   </script>'
        r = check_html(page, url="empty")
        self.assertEqual(r.status, "ERRORS")
        self.assertEqual(r.jsonld_count, 1)

    def test_context_vocab_object(self) -> None:
        page = ld(
            {
                "@context": {"@vocab": "https://schema.org/"},
                "@type": "FAQPage",
                "mainEntity": [{"@type": "Question", "name": "Q", "acceptedAnswer": {"text": "A"}}],
            }
        )
        r = check_html(page, url="vocab")
        self.assertFalse(any("schema.org @context" in i.message for i in r.issues))

    def test_courseinstance_missing_dates_is_warning(self) -> None:
        page = ld(
            {
                "@context": "https://schema.org",
                "@type": "Course",
                "name": "Lab",
                "description": "Hands-on",
                "provider": "Ledger",
                "hasCourseInstance": {"@type": "CourseInstance", "courseMode": "online"},
            }
        )
        r = check_html(page, url="inst")
        self.assertEqual(r.error_count(), 0)
        self.assertTrue(any("startDate" in i.path for i in r.issues if i.level == "warning"))

    def test_offers_array_price(self) -> None:
        page = ld(
            {
                "@context": "https://schema.org",
                "@type": "Course",
                "name": "Lab",
                "description": "Hands-on",
                "provider": "Ledger",
                "offers": [{"@type": "Offer", "price": "0", "priceCurrency": "CAD"}],
            }
        )
        r = check_html(page, url="offers")
        self.assertFalse(any("offers.price" in i.path for i in r.issues))

    def test_javascript_scheme_rejected(self) -> None:
        from schema_lint.fetch import fetch

        res = fetch("javascript:alert(1)")
        self.assertFalse(res.ok)

    def test_professional_service_family(self) -> None:
        page = ld(
            {
                "@context": "https://schema.org",
                "@type": "ProfessionalService",
                "name": "Ledger Advisory",
                "url": "https://ledger.example",
                "address": {"addressLocality": "Port Coquitlam"},
            }
        )
        r = check_html(page, url="pro", types="LocalBusiness")
        self.assertEqual(r.error_count(), 0)
        self.assertIn("ProfessionalService", r.types_found)

    def test_types_filter_does_not_score_unrequested(self) -> None:
        page = ld(
            {
                "@context": "https://schema.org",
                "@type": "LocalBusiness",
            }
        )
        r = check_html(page, url="nofilter", types="Course")
        self.assertEqual(r.error_count(), 0)

    def test_does_not_invent_on_dump(self) -> None:
        page = ld({"@context": "https://schema.org", "@type": "Course", "name": "Only a name"})
        ext = extract_jsonld(page)
        node = ext.entities[0].node
        self.assertNotIn("description", node)
        self.assertNotIn("provider", node)
        r = check_html(page, url="invent")
        self.assertGreater(r.error_count(), 0)

    def test_graph_context_inherited(self) -> None:
        page = ld(
            {
                "@context": "https://schema.org",
                "@graph": [
                    {
                        "@type": "FAQPage",
                        "mainEntity": [
                            {"@type": "Question", "name": "Q", "acceptedAnswer": {"text": "A"}}
                        ],
                    }
                ],
            }
        )
        r = check_html(page, url="inherit")
        self.assertEqual(r.status, "OK")
        self.assertFalse(any("schema.org @context" in i.message for i in r.issues))

    def test_bom_and_whitespace(self) -> None:
        payload = '\ufeff\n{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[{"@type":"Question","name":"Q","acceptedAnswer":{"text":"A"}}]}\n'
        page = f'<script type="application/ld+json">{payload}</script>'
        r = check_html(page, url="bom")
        self.assertEqual(r.status, "OK")

    def test_cli_writes_report_chip(self) -> None:
        page = ld(
            {
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": [{"@type": "Question", "name": "Q", "acceptedAnswer": {"text": "A"}}],
            }
        )
        with tempfile.TemporaryDirectory() as tmp:
            html_path = Path(tmp) / "p.html"
            html_path.write_text(page, encoding="utf-8")
            code = main(["--json", "--out", tmp, "check", str(html_path)])
            self.assertEqual(code, 0)
            chips = list(Path(tmp).glob("report-*.json"))
            self.assertTrue(chips)
            payload = json.loads(chips[0].read_text(encoding="utf-8"))
            self.assertEqual(payload["schema"], "schema-lint/v1")
            self.assertEqual(payload["error_count"], 0)

    def test_breadcrumb_warn_only(self) -> None:
        page = ld({"@context": "https://schema.org", "@type": "BreadcrumbList"})
        r = check_html(page, url="crumbs")
        self.assertEqual(r.error_count(), 0)
        self.assertGreater(r.warning_count(), 0)

    def test_faq_wrong_mainentity_type(self) -> None:
        page = ld(
            {
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": [{"@type": "Thing", "name": "Nope"}],
            }
        )
        r = check_html(page, url="wrong-q")
        self.assertEqual(r.status, "ERRORS")


if __name__ == "__main__":
    unittest.main()
