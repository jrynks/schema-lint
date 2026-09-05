from __future__ import annotations

import unittest
from pathlib import Path

from schema_lint.validate import check_html

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def html(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class ValidateTests(unittest.TestCase):
    def test_faq_valid_ok(self) -> None:
        r = check_html(html("faq_valid.html"), url="faq_valid")
        self.assertEqual(r.status, "OK")
        self.assertEqual(r.error_count(), 0)
        self.assertIn("FAQPage", r.types_found)

    def test_faq_missing_answer(self) -> None:
        r = check_html(html("faq_missing_answer.html"), url="faq_missing")
        self.assertEqual(r.status, "ERRORS")
        self.assertGreater(r.error_count(), 0)
        self.assertTrue(any("acceptedAnswer" in i.path or "acceptedAnswer" in i.message for i in r.issues))

    def test_faq_empty_main(self) -> None:
        r = check_html(html("faq_empty_main.html"), url="faq_empty")
        self.assertEqual(r.status, "ERRORS")
        self.assertTrue(any("empty mainEntity" in i.message for i in r.issues))

    def test_broken_jsonld(self) -> None:
        r = check_html(html("jsonld_broken.html"), url="broken")
        self.assertEqual(r.status, "ERRORS")
        self.assertTrue(any(i.type == "JSON-LD" for i in r.issues))

    def test_localbusiness_missing_name_address(self) -> None:
        r = check_html(html("localbusiness_missing.html"), url="lb_missing")
        self.assertEqual(r.status, "ERRORS")
        paths = {i.path for i in r.issues if i.level == "error"}
        self.assertTrue(any(p.endswith(".name") for p in paths))
        self.assertTrue(any(".address" in p for p in paths))

    def test_course_minimal_pass(self) -> None:
        r = check_html(html("course_minimal.html"), url="course")
        self.assertEqual(r.status, "OK")
        self.assertEqual(r.error_count(), 0)
        # recommended fields warn
        self.assertGreater(r.warning_count(), 0)

    def test_course_about_and_author(self) -> None:
        r = check_html(html("course_about_author.html"), url="course_about")
        self.assertEqual(r.status, "OK")
        self.assertEqual(r.error_count(), 0)

    def test_dentist_counts_as_localbusiness(self) -> None:
        r = check_html(html("localbusiness_valid.html"), url="dentist")
        self.assertEqual(r.status, "OK")
        self.assertEqual(r.error_count(), 0)
        self.assertIn("Dentist", r.types_found)

    def test_hasmap_satisfies_location(self) -> None:
        r = check_html(html("local_hasmap_only.html"), url="hasmap")
        self.assertEqual(r.error_count(), 0)
        self.assertEqual(r.status, "OK")

    def test_missing_context_is_warning(self) -> None:
        r = check_html(html("missing_context.html"), url="nocontext")
        self.assertEqual(r.status, "OK")
        self.assertTrue(any("schema.org" in i.message and i.level == "warning" for i in r.issues))

    def test_types_filter_ignores_other_errors(self) -> None:
        r = check_html(html("localbusiness_missing.html"), url="lb", types="FAQPage")
        self.assertEqual(r.status, "OK")
        self.assertEqual(r.error_count(), 0)

    def test_strict_types(self) -> None:
        r = check_html(html("faq_valid.html"), url="faq", types="Course", strict_types=True)
        self.assertEqual(r.status, "ERRORS")
        self.assertTrue(any("none of the requested types" in i.message for i in r.issues))

    def test_graph_course_complete_no_error(self) -> None:
        r = check_html(html("graph_mixed.html"), url="graph")
        self.assertEqual(r.error_count(), 0)

    def test_single_question_not_array(self) -> None:
        page = """<script type="application/ld+json">
        {"@context":"https://schema.org","@type":"FAQPage",
         "mainEntity":{"@type":"Question","name":"Q","acceptedAnswer":{"text":"A"}}}
        </script>"""
        r = check_html(page, url="single-q")
        self.assertEqual(r.status, "OK")
        self.assertEqual(r.error_count(), 0)

    def test_question_text_alias(self) -> None:
        r = check_html(html("two_blocks.html"), url="two")
        self.assertEqual(r.error_count(), 0)
        self.assertIn("FAQPage", r.types_found)
        self.assertIn("Organization", r.types_found)

    def test_does_not_invent_missing_fields(self) -> None:
        r = check_html(html("course_minimal.html"), url="c")
        # url / offers / hasCourseInstance were not on the page — warnings, not silently present
        msgs = " ".join(i.message for i in r.issues)
        self.assertIn("url is missing", msgs)
        self.assertIn("offers is missing", msgs)
        self.assertIn("hasCourseInstance is missing", msgs)


if __name__ == "__main__":
    unittest.main()
