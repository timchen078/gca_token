#!/usr/bin/env python3
"""Validate GCA public-site links, assets, fragments, and placeholders.

Local mode resolves every internal reference against the ``site`` directory.
Optional live mode also fetches each discovered same-origin target after deploy.
The checker never submits forms, runs page JavaScript, or follows external links.
"""

from __future__ import annotations

import argparse
import json
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SITE_ROOT = ROOT / "site"
DEFAULT_BASE_URL = "https://gcagochina.com/"
DEFAULT_TIMEOUT_SECONDS = 20.0
DEFAULT_MAX_WORKERS = 6
MAX_REMOTE_RESPONSE_BYTES = 4 * 1024 * 1024
VIDEO_TARGET_SUFFIXES = {".mov", ".mp4", ".webm"}
USER_AGENT = "GCA-Site-Link-Integrity/1.0"
PLACEHOLDER_HOSTS = {
    "example.com",
    "example.net",
    "example.org",
    "localhost",
    "127.0.0.1",
    "::1",
    "0.0.0.0",
}
REFERENCE_ATTRIBUTES = {
    "a": ("href",),
    "area": ("href",),
    "audio": ("src",),
    "button": ("formaction",),
    "form": ("action",),
    "iframe": ("src",),
    "img": ("src",),
    "input": ("src", "formaction"),
    "link": ("href",),
    "object": ("data",),
    "script": ("src",),
    "source": ("src",),
    "video": ("src", "poster"),
}
META_URL_KEYS = {"og:image", "og:url", "twitter:image"}


@dataclass(frozen=True)
class Reference:
    source: Path
    line: int
    tag: str
    attribute: str
    value: str
    target_blank: bool = False
    rel_tokens: frozenset[str] = frozenset()


@dataclass(frozen=True)
class ParsedDocument:
    path: Path
    ids: frozenset[str]
    duplicate_ids: tuple[str, ...]
    references: tuple[Reference, ...]


@dataclass(frozen=True)
class LinkIntegrityReport:
    page_count: int
    reference_count: int
    internal_reference_count: int
    external_reference_count: int
    fragment_reference_count: int
    internal_urls: tuple[str, ...]
    errors: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "pageCount": self.page_count,
            "referenceCount": self.reference_count,
            "internalReferenceCount": self.internal_reference_count,
            "externalReferenceCount": self.external_reference_count,
            "fragmentReferenceCount": self.fragment_reference_count,
            "uniqueInternalTargetCount": len(self.internal_urls),
            "internalUrls": list(self.internal_urls),
            "errors": list(self.errors),
        }


class SiteHTMLParser(HTMLParser):
    def __init__(self, source: Path) -> None:
        super().__init__(convert_charrefs=True)
        self.source = source
        self.ids: set[str] = set()
        self.duplicate_ids: list[str] = []
        self.references: list[Reference] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._handle_tag(tag, attrs)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._handle_tag(tag, attrs)

    def _handle_tag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attr_map = {name.lower(): value for name, value in attrs if name}
        identifier = attr_map.get("id")
        if identifier:
            if identifier in self.ids:
                self.duplicate_ids.append(identifier)
            self.ids.add(identifier)
        if tag == "a" and attr_map.get("name"):
            self.ids.add(attr_map["name"] or "")

        target_blank = (attr_map.get("target") or "").lower() == "_blank"
        rel_tokens = frozenset((attr_map.get("rel") or "").lower().split())
        line = self.getpos()[0]
        for attribute in REFERENCE_ATTRIBUTES.get(tag, ()):
            if attribute in attr_map:
                self.references.append(
                    Reference(
                        source=self.source,
                        line=line,
                        tag=tag,
                        attribute=attribute,
                        value=attr_map.get(attribute) or "",
                        target_blank=target_blank,
                        rel_tokens=rel_tokens,
                    )
                )

        if tag == "meta":
            key = (attr_map.get("property") or attr_map.get("name") or "").lower()
            if key in META_URL_KEYS and "content" in attr_map:
                self.references.append(
                    Reference(
                        source=self.source,
                        line=line,
                        tag=tag,
                        attribute="content",
                        value=attr_map.get("content") or "",
                    )
                )


def public_path(path: Path, site_root: Path) -> str:
    relative = path.relative_to(site_root).as_posix()
    return f"/{relative}"


def parse_documents(site_root: Path) -> dict[Path, ParsedDocument]:
    documents: dict[Path, ParsedDocument] = {}
    for path in sorted(site_root.rglob("*.html")):
        parser = SiteHTMLParser(path)
        parser.feed(path.read_text(encoding="utf-8"))
        parser.close()
        documents[path.resolve()] = ParsedDocument(
            path=path,
            ids=frozenset(parser.ids),
            duplicate_ids=tuple(parser.duplicate_ids),
            references=tuple(parser.references),
        )
    return documents


def format_error(reference: Reference, site_root: Path, message: str) -> str:
    source = reference.source.relative_to(site_root).as_posix()
    return f"{source}:{reference.line}: {message}: {reference.value!r}"


def resolve_internal_path(site_root: Path, url_path: str) -> Path | None:
    decoded = unquote(url_path)
    if "\\" in decoded or "\x00" in decoded:
        return None
    relative = decoded.lstrip("/")
    if not relative or decoded.endswith("/"):
        relative = f"{relative}index.html"
    candidate = (site_root / relative).resolve()
    try:
        candidate.relative_to(site_root.resolve())
    except ValueError:
        return None
    if candidate.is_dir():
        candidate = candidate / "index.html"
    return candidate


def is_client_state_fragment(fragment: str) -> bool:
    return "=" in fragment or "&" in fragment


def is_placeholder_or_local_host(host: str) -> bool:
    return host.endswith(".invalid") or any(
        host == placeholder or host.endswith(f".{placeholder}")
        for placeholder in PLACEHOLDER_HOSTS
    )


def scan_site(
    site_root: Path = DEFAULT_SITE_ROOT,
    *,
    base_url: str = DEFAULT_BASE_URL,
) -> LinkIntegrityReport:
    site_root = site_root.resolve()
    if not site_root.is_dir():
        return LinkIntegrityReport(0, 0, 0, 0, 0, (), (f"site root does not exist: {site_root}",))

    base_parts = urlsplit(base_url)
    if base_parts.scheme != "https" or not base_parts.hostname:
        return LinkIntegrityReport(0, 0, 0, 0, 0, (), ("base URL must be an absolute HTTPS URL",))
    official_host = base_parts.hostname.lower()
    documents = parse_documents(site_root)
    errors: list[str] = []
    internal_urls: set[str] = set()
    reference_count = 0
    internal_count = 0
    external_count = 0
    fragment_count = 0

    if not documents:
        errors.append("site root contains no HTML pages")

    for document in documents.values():
        for identifier in sorted(set(document.duplicate_ids)):
            source = document.path.relative_to(site_root).as_posix()
            errors.append(f"{source}: duplicate id {identifier!r}")

        source_url = urljoin(base_url, public_path(document.path, site_root).lstrip("/"))
        for reference in document.references:
            reference_count += 1
            raw = reference.value.strip()
            if not raw:
                errors.append(format_error(reference, site_root, "empty URL attribute"))
                continue
            if raw == "#":
                errors.append(format_error(reference, site_root, "placeholder fragment"))
                continue
            if any(ord(character) < 32 for character in raw):
                errors.append(format_error(reference, site_root, "URL contains a control character"))
                continue
            if raw.startswith("//"):
                errors.append(format_error(reference, site_root, "protocol-relative URL is not allowed"))
                continue

            raw_parts = urlsplit(raw)
            scheme = raw_parts.scheme.lower()
            if scheme in {"mailto", "tel"}:
                external_count += 1
                if not raw_parts.path or (scheme == "mailto" and "@" not in raw_parts.path):
                    errors.append(format_error(reference, site_root, f"invalid {scheme} URL"))
                continue
            if scheme == "data":
                external_count += 1
                if reference.tag not in {"img", "source"}:
                    errors.append(format_error(reference, site_root, "data URL is only allowed for image media"))
                continue
            if scheme and scheme not in {"http", "https"}:
                errors.append(format_error(reference, site_root, f"unsupported URL scheme {scheme!r}"))
                continue

            resolved = urlsplit(urljoin(source_url, raw))
            host = (resolved.hostname or "").lower()
            if host and host != official_host:
                external_count += 1
                if scheme != "https":
                    errors.append(format_error(reference, site_root, "external URL must use HTTPS"))
                if is_placeholder_or_local_host(host):
                    errors.append(format_error(reference, site_root, "placeholder or local-only host is not allowed"))
                if reference.target_blank and not ({"noopener", "noreferrer"} & reference.rel_tokens):
                    errors.append(format_error(reference, site_root, "target=_blank requires rel=noopener or noreferrer"))
                continue

            internal_count += 1
            if resolved.scheme != "https" or host != official_host:
                errors.append(format_error(reference, site_root, "internal URL did not resolve to the official HTTPS origin"))
                continue
            target = resolve_internal_path(site_root, resolved.path)
            if target is None:
                errors.append(format_error(reference, site_root, "internal URL escapes or cannot map to the site root"))
                continue
            if not target.is_file():
                errors.append(format_error(reference, site_root, f"missing internal target {resolved.path}"))
                continue

            remote_target = urlunsplit(("", "", resolved.path or "/", resolved.query, ""))
            internal_urls.add(remote_target)
            if resolved.fragment:
                fragment_count += 1
                fragment = unquote(resolved.fragment)
                if target.suffix.lower() == ".html" and not is_client_state_fragment(fragment):
                    target_document = documents.get(target.resolve())
                    if target_document is None or fragment not in target_document.ids:
                        errors.append(format_error(reference, site_root, f"missing fragment target #{fragment}"))

    return LinkIntegrityReport(
        page_count=len(documents),
        reference_count=reference_count,
        internal_reference_count=internal_count,
        external_reference_count=external_count,
        fragment_reference_count=fragment_count,
        internal_urls=tuple(sorted(internal_urls)),
        errors=tuple(sorted(errors)),
    )


def fetch_internal_target(base_url: str, target: str, timeout: float, context: ssl.SSLContext) -> str | None:
    url = urljoin(base_url, target.lstrip("/"))
    is_video = Path(urlsplit(target).path).suffix.lower() in VIDEO_TARGET_SUFFIXES
    request = Request(
        url,
        method="HEAD" if is_video else "GET",
        headers={"Accept": "video/*" if is_video else "*/*", "User-Agent": USER_AGENT},
    )
    try:
        with urlopen(request, timeout=timeout, context=context) as response:
            status = getattr(response, "status", 200)
            final = urlsplit(response.geturl())
            expected_host = urlsplit(base_url).hostname
            if status < 200 or status >= 300:
                return f"{target}: HTTP {status}"
            if final.scheme != "https" or final.hostname != expected_host:
                return f"{target}: redirected outside the official HTTPS origin to {response.geturl()}"
            if is_video:
                content_type = response.headers.get("Content-Type", "").partition(";")[0].strip().lower()
                if not content_type.startswith("video/"):
                    return f"{target}: unexpected video content type {content_type or 'missing'}"
            elif len(response.read(MAX_REMOTE_RESPONSE_BYTES + 1)) > MAX_REMOTE_RESPONSE_BYTES:
                return f"{target}: response exceeds {MAX_REMOTE_RESPONSE_BYTES} bytes"
    except HTTPError as error:
        return f"{target}: HTTP {error.code}"
    except (URLError, TimeoutError, OSError) as error:
        return f"{target}: {error}"
    return None


def build_ssl_context() -> ssl.SSLContext:
    try:
        import certifi
    except ImportError:
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())


def check_live_targets(
    targets: Iterable[str],
    *,
    base_url: str = DEFAULT_BASE_URL,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_workers: int = DEFAULT_MAX_WORKERS,
) -> tuple[str, ...]:
    base_parts = urlsplit(base_url)
    if base_parts.scheme != "https" or not base_parts.hostname:
        return ("base URL must be an absolute HTTPS URL",)
    context = build_ssl_context()
    errors: list[str] = []
    unique_targets = tuple(sorted(set(targets)))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(fetch_internal_target, base_url, target, timeout, context): target
            for target in unique_targets
        }
        for future in as_completed(futures):
            error = future.result()
            if error:
                errors.append(error)
    return tuple(sorted(errors))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate all GCA public-site links and assets.")
    parser.add_argument("--site-root", type=Path, default=DEFAULT_SITE_ROOT)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--check-live", action="store_true", help="Fetch every discovered same-origin target.")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--max-workers", type=int, default=DEFAULT_MAX_WORKERS)
    parser.add_argument("--json", action="store_true", help="Print a machine-readable report.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.timeout <= 0:
        raise SystemExit("--timeout must be positive")
    if args.max_workers < 1 or args.max_workers > 16:
        raise SystemExit("--max-workers must be between 1 and 16")

    report = scan_site(args.site_root, base_url=args.base_url)
    live_errors: tuple[str, ...] = ()
    if report.ok and args.check_live:
        live_errors = check_live_targets(
            report.internal_urls,
            base_url=args.base_url,
            timeout=args.timeout,
            max_workers=args.max_workers,
        )

    payload = report.as_dict()
    payload["liveTargetCheckEnabled"] = args.check_live
    payload["liveTargetErrors"] = list(live_errors)
    payload["ok"] = report.ok and not live_errors
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif payload["ok"]:
        suffix = f"; {len(report.internal_urls)} live targets reachable" if args.check_live else ""
        print(
            f"[ok] {report.page_count} HTML pages, {report.reference_count} references, "
            f"{len(report.internal_urls)} unique internal targets{suffix}."
        )
    else:
        for error in (*report.errors, *live_errors):
            print(f"[fail] {error}")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
