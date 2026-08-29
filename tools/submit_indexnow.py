#!/usr/bin/env python3
"""Notify IndexNow participants after a verified GCA site deployment."""

from __future__ import annotations

import argparse
import json
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
HOST = "gcagochina.com"
BASE_URL = f"https://{HOST}"
ENDPOINT = "https://api.indexnow.org/indexnow"
KEY_FILE = SITE / "b72f6e37c84a4d659820a9137e4c1fd8.txt"
KEY_RE = re.compile(r"[A-Za-z0-9-]{8,128}")


def read_key(path: Path = KEY_FILE) -> str:
    key = path.read_text(encoding="utf-8").strip()
    if not KEY_RE.fullmatch(key):
        raise ValueError("IndexNow key must be 8-128 letters, numbers, or dashes")
    if path.name != f"{key}.txt":
        raise ValueError("IndexNow key filename must match the key")
    return key


def public_html_urls(site_root: Path = SITE) -> list[str]:
    urls: set[str] = set()
    for path in site_root.rglob("*.html"):
        relative = path.relative_to(site_root).as_posix()
        if relative == "404.html":
            continue
        if relative == "index.html":
            urls.add(f"{BASE_URL}/")
        elif relative.endswith("/index.html"):
            urls.add(f"{BASE_URL}/{relative[:-10]}")
        else:
            urls.add(f"{BASE_URL}/{relative}")
    urls.add(f"{BASE_URL}/sitemap.xml")
    return sorted(urls)


def build_payload(site_root: Path = SITE, key_file: Path = KEY_FILE) -> dict[str, Any]:
    key = read_key(key_file)
    return {
        "host": HOST,
        "key": key,
        "keyLocation": f"{BASE_URL}/{key}.txt",
        "urlList": public_html_urls(site_root),
    }


def submit(payload: dict[str, Any], timeout: float = 30.0) -> dict[str, Any]:
    request = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
            body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as error:
        status = error.code
        body = error.read().decode("utf-8", errors="replace")
    return {
        "accepted": status in {200, 202},
        "status": status,
        "response": body,
        "urlCount": len(payload["urlList"]),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare or submit the GCA IndexNow URL set.")
    parser.add_argument("--submit", action="store_true", help="Send the URL set to IndexNow.")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_payload()
    report: dict[str, Any] = {
        "mode": "submit" if args.submit else "dry-run",
        "host": payload["host"],
        "keyLocation": payload["keyLocation"],
        "urlCount": len(payload["urlList"]),
        "criticalUrls": [
            f"{BASE_URL}/about.html",
            f"{BASE_URL}/team.html",
            f"{BASE_URL}/community.html",
            f"{BASE_URL}/project-profile.html",
        ],
    }
    if args.submit:
        report.update(submit(payload, timeout=args.timeout))
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"GCA IndexNow {report['mode']}: {report['urlCount']} URLs")
        if args.submit:
            print(f"HTTP status: {report['status']}")
    return 0 if not args.submit or report.get("accepted", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())
