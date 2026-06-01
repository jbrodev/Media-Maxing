from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


RISKY_PATTERNS = (
    "access_token",
    "refresh_token",
    "client_secret",
    "Authorization",
    "Bearer",
    "id_token",
    "appsecret_proof",
    "signed_request",
    "META_CLIENT_SECRET",
    "GOOGLE_CLIENT_SECRET",
    "TIKTOK_CLIENT_SECRET",
    "LINKEDIN_CLIENT_SECRET",
    "X_CLIENT_SECRET",
)

SCAN_SUFFIXES = {".md", ".example", ".py", ".js", ".html", ".css", ".sql"}
IGNORED_DIRS = {"__pycache__", ".git", "node_modules", ".pytest_cache", ".mypy_cache"}

SECRET_VALUE_RE = re.compile(
    r"(?i)(?:access_token|refresh_token|client_secret|authorization|bearer|id_token)"
    r"['\" ]*[:=]['\" ]+([A-Za-z0-9_\-\.]{24,})"
)


@dataclass
class ScanFileFinding:
    path: str
    category: str
    risky_pattern_count: int
    secret_like_value_count: int


@dataclass
class SecurityScanResult:
    files_scanned: int = 0
    files_with_risky_patterns: int = 0
    code_schema_test_files: int = 0
    docs_example_files: int = 0
    actual_secret_like_values: int = 0
    findings: list[ScanFileFinding] = field(default_factory=list)

    def to_report(self) -> str:
        return "\n".join(
            (
                f"files_scanned={self.files_scanned}",
                f"risky_pattern_files={self.files_with_risky_patterns}",
                f"code/schema/test_files={self.code_schema_test_files}",
                f"docs/example_files={self.docs_example_files}",
                f"actual_secret_like_values={self.actual_secret_like_values}",
                "No secret values printed. Review flagged files locally if actual_secret_like_values is nonzero.",
            )
        )


def scan_paths(paths: Iterable[str | Path]) -> SecurityScanResult:
    result = SecurityScanResult()
    for root in paths:
        path = Path(root)
        candidates = [path] if path.is_file() else path.rglob("*")
        for candidate in candidates:
            if _should_skip(candidate):
                continue
            result.files_scanned += 1
            text = _read_text(candidate)
            if text is None:
                continue
            risky_count = sum(text.count(pattern) for pattern in RISKY_PATTERNS)
            secret_like_count = sum(1 for value in SECRET_VALUE_RE.findall(text) if _looks_real_secret(value))
            if risky_count or secret_like_count:
                category = _category(candidate)
                result.files_with_risky_patterns += 1
                if category == "docs/example":
                    result.docs_example_files += 1
                else:
                    result.code_schema_test_files += 1
                result.actual_secret_like_values += secret_like_count
                result.findings.append(
                    ScanFileFinding(
                        path=str(candidate),
                        category=category,
                        risky_pattern_count=risky_count,
                        secret_like_value_count=secret_like_count,
                    )
                )
    return result


def _should_skip(path: Path) -> bool:
    if any(part in IGNORED_DIRS for part in path.parts):
        return True
    return not path.is_file() or path.suffix not in SCAN_SUFFIXES


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None


def _category(path: Path) -> str:
    if path.suffix in {".md", ".example"} or path.name.endswith(".env.example"):
        return "docs/example"
    return "code/schema/test"


def _looks_real_secret(value: str) -> bool:
    lowered = value.lower()
    if any(marker in lowered for marker in ("fake", "mock", "demo", "test", "hidden", "must-not-leak")):
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a redacted integration security scan.")
    parser.add_argument("paths", nargs="*", default=["."], help="Files or folders to scan.")
    args = parser.parse_args()
    result = scan_paths(args.paths)
    print(result.to_report())
    return 1 if result.actual_secret_like_values else 0


if __name__ == "__main__":
    raise SystemExit(main())
