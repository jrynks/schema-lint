from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from schema_lint.cli import main

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.out = self.tmp.name

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_doctor(self) -> None:
        code = main(["--out", self.out, "doctor"])
        self.assertEqual(code, 0)

    def test_faq_valid_ok(self) -> None:
        code = main(["--out", self.out, "check", str(FIXTURES / "faq_valid.html")])
        self.assertEqual(code, 0)
        reports = list(Path(self.out).glob("report-*.json"))
        self.assertTrue(reports)

    def test_faq_missing_answer_exit_2(self) -> None:
        code = main(["--out", self.out, "check", str(FIXTURES / "faq_missing_answer.html")])
        self.assertEqual(code, 2)

    def test_broken_jsonld_exit_2(self) -> None:
        code = main(["--out", self.out, "check", str(FIXTURES / "jsonld_broken.html")])
        self.assertEqual(code, 2)

    def test_localbusiness_missing_exit_2(self) -> None:
        code = main(["--out", self.out, "check", str(FIXTURES / "localbusiness_missing.html")])
        self.assertEqual(code, 2)

    def test_course_minimal_pass(self) -> None:
        code = main(["--out", self.out, "check", str(FIXTURES / "course_minimal.html")])
        self.assertEqual(code, 0)

    def test_json_stdout_schema(self) -> None:
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["--json", "--out", self.out, "check", str(FIXTURES / "faq_valid.html")])
        self.assertEqual(code, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["schema"], "schema-lint/v1")
        self.assertIn("generated_at", payload)
        self.assertEqual(payload["error_count"], 0)
        self.assertEqual(payload["results"][0]["status"], "OK")
        self.assertIn("FAQPage", payload["results"][0]["types_found"])

    def test_urls_file(self) -> None:
        listing = Path(self.out) / "urls.txt"
        listing.write_text(
            f"# comment\n{FIXTURES / 'faq_valid.html'}\n{FIXTURES / 'course_minimal.html'}\n",
            encoding="utf-8",
        )
        code = main(["--out", self.out, "check", "--urls", str(listing)])
        self.assertEqual(code, 0)

    def test_strict_types_no_match(self) -> None:
        code = main(
            [
                "--out",
                self.out,
                "check",
                str(FIXTURES / "faq_valid.html"),
                "--types",
                "Course",
                "--strict-types",
            ]
        )
        self.assertEqual(code, 2)

    def test_dump_ld_never_invents(self) -> None:
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["--json", "dump-ld", str(FIXTURES / "no_jsonld.html")])
        self.assertEqual(code, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload[0]["blocks"], [])

    def test_fetch_failed_exit_2(self) -> None:
        code = main(["--out", self.out, "--timeout-sec", "2", "check", "https://127.0.0.1:1/nope"])
        self.assertEqual(code, 2)

    def test_no_fail_on_fetch_allows_zero(self) -> None:
        code = main(
            [
                "--out",
                self.out,
                "--no-fail-on-fetch",
                "--timeout-sec",
                "2",
                "check",
                "https://127.0.0.1:1/nope",
            ]
        )
        self.assertEqual(code, 0)

    def test_check_no_urls(self) -> None:
        code = main(["--out", self.out, "check"])
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
