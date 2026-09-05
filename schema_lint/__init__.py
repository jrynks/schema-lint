"""schema-lint — fetch pages, extract JSON-LD, validate Schema.org types.

Never invent structured data. Missing required properties are errors.
"""

from __future__ import annotations

__version__ = "1.0.0"
SCHEMA_VERSION = "schema-lint/v1"
DEFAULT_OUTPUT_DIR = "/tmp/schema-lint"
DEFAULT_TIMEOUT_SEC = 30
DEFAULT_USER_AGENT = "schema-lint/1.0 (+https://schema.org; Site Audit)"

from schema_lint.models import Issue, Report, UrlResult  # noqa: E402
from schema_lint.validate import check_html, check_url, validate_entities  # noqa: E402

__all__ = [
    "SCHEMA_VERSION",
    "Issue",
    "Report",
    "UrlResult",
    "__version__",
    "check_html",
    "check_url",
    "validate_entities",
]
