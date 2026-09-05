from __future__ import annotations

import unittest
from pathlib import Path

from schema_lint.extract import extract_jsonld, parse_jsonld_text

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class ExtractTests(unittest.TestCase):
    def test_faq_valid_types(self) -> None:
        html = (FIXTURES / "faq_valid.html").read_text(encoding="utf-8")
        ext = extract_jsonld(html)
        self.assertEqual(ext.types_found, ["FAQPage"])
        self.assertEqual(len(ext.blocks), 1)
        self.assertIsNone(ext.blocks[0].error)

    def test_graph_expands_types(self) -> None:
        html = (FIXTURES / "graph_mixed.html").read_text(encoding="utf-8")
        ext = extract_jsonld(html)
        self.assertIn("WebSite", ext.types_found)
        self.assertIn("Course", ext.types_found)
        self.assertIn("Product", ext.types_found)
        self.assertIn("BreadcrumbList", ext.types_found)

    def test_two_blocks(self) -> None:
        html = (FIXTURES / "two_blocks.html").read_text(encoding="utf-8")
        ext = extract_jsonld(html)
        self.assertEqual(ext.jsonld_count if hasattr(ext, "jsonld_count") else len(ext.blocks), 2)
        self.assertEqual(ext.types_found, ["Organization", "FAQPage"])

    def test_broken_json_records_error(self) -> None:
        html = (FIXTURES / "jsonld_broken.html").read_text(encoding="utf-8")
        ext = extract_jsonld(html)
        self.assertEqual(len(ext.blocks), 1)
        self.assertIsNotNone(ext.blocks[0].error)
        self.assertEqual(ext.entities, [])

    def test_cdata_and_comment(self) -> None:
        html = (FIXTURES / "cdata_and_comment.html").read_text(encoding="utf-8")
        ext = extract_jsonld(html)
        self.assertIsNone(ext.blocks[0].error)
        self.assertEqual(ext.types_found, ["FAQPage"])

    def test_no_jsonld(self) -> None:
        html = (FIXTURES / "no_jsonld.html").read_text(encoding="utf-8")
        ext = extract_jsonld(html)
        self.assertEqual(ext.blocks, [])
        self.assertEqual(ext.types_found, [])

    def test_concatenated_objects(self) -> None:
        raw = '{"@type":"WebSite","name":"A"}\n{"@type":"Organization","name":"B"}'
        parsed = parse_jsonld_text(raw)
        self.assertIsInstance(parsed, list)
        self.assertEqual(len(parsed), 2)

    def test_never_invents_on_empty(self) -> None:
        ext = extract_jsonld("<html><head></head><body></body></html>")
        self.assertEqual(ext.entities, [])
        self.assertEqual(ext.types_found, [])


if __name__ == "__main__":
    unittest.main()
