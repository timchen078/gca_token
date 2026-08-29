#!/usr/bin/env python3
"""Reject personal identity markers from the public GCA website tree."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SITE_ROOT = ROOT / "site"
TEXT_SUFFIXES = {
    ".css",
    ".html",
    ".js",
    ".json",
    ".md",
    ".txt",
    ".webmanifest",
    ".xml",
}
EMAIL_RE = re.compile(r"(?i)(?<![\w.+-])([\w.+-]+)@([a-z0-9.-]+\.[a-z]{2,})(?![\w.-])")
ALLOWED_EMAIL_DOMAINS = frozenset({"gcagochina.com", "example.com"})
FORBIDDEN_PATTERNS = (
    ("macOS user path", re.compile(r"/Users/[^/\s<'\"]+")),
    ("Linux home path", re.compile(r"/home/[^/\s<'\"]+")),
    ("Windows user path", re.compile(r"(?i)[A-Z]:\\Users\\[^\\\s<'\"]+")),
    ("personal GitHub profile", re.compile(r"(?i)https?://(?:www\.)?github\.com/(?!organizations(?:/|$)|features(?:/|$)|topics(?:/|$))[^/\s<'\"]+")),
    ("LinkedIn profile", re.compile(r"(?i)https?://(?:[a-z]{2,3}\.)?linkedin\.com/")),
    ("HTML author metadata", re.compile(r"(?i)<meta\s+[^>]*name=[\"'](?:author|creator)[\"']")),
    ("personal identity JSON field", re.compile(r'(?i)"(?:author|creator|founder|ceo|projectLead|ownerName)"\s*:')),
)


def iter_public_text_files(site_root: Path):
    for path in sorted(site_root.rglob("*")):
        if path.is_file() and (path.suffix.lower() in TEXT_SUFFIXES or path.name in {"CNAME", "robots.txt"}):
            yield path


def check_public_privacy(site_root: Path = DEFAULT_SITE_ROOT) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    files_checked = 0
    for path in iter_public_text_files(site_root):
        files_checked += 1
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(site_root).as_posix()
        for line_number, line in enumerate(text.splitlines(), start=1):
            for match in EMAIL_RE.finditer(line):
                domain = match.group(2).lower()
                if domain not in ALLOWED_EMAIL_DOMAINS:
                    findings.append({
                        "path": relative,
                        "line": line_number,
                        "kind": "non-project email",
                        "value": match.group(0),
                    })
            for kind, pattern in FORBIDDEN_PATTERNS:
                match = pattern.search(line)
                if match:
                    findings.append({
                        "path": relative,
                        "line": line_number,
                        "kind": kind,
                        "value": match.group(0),
                    })
    return {
        "ok": not findings,
        "siteRoot": str(site_root),
        "filesChecked": files_checked,
        "findings": findings,
        "policy": {
            "allowedEmailDomains": sorted(ALLOWED_EMAIL_DOMAINS),
            "rejectsLocalUserPaths": True,
            "rejectsPersonalProfileLinks": True,
            "rejectsAuthorMetadata": True,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check the public GCA site for personal identity markers.")
    parser.add_argument("--site-root", type=Path, default=DEFAULT_SITE_ROOT)
    parser.add_argument("--json", action="store_true", help="Print the complete JSON report.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = check_public_privacy(args.site_root)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"GCA public privacy check: {'passed' if report['ok'] else 'failed'}")
        print(f"files checked: {report['filesChecked']}")
        for finding in report["findings"]:
            print(f"{finding['path']}:{finding['line']}: {finding['kind']}: {finding['value']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
