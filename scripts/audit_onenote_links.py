"""Audit whether OneNote source links survived in a migrated Obsidian vault.

The script compares external links currently present in Markdown notes with the
live ``<a href=...>`` anchors from Microsoft Graph OneNote page HTML. It is
intended for private/local runs only; generated reports can contain note titles,
relative paths, URLs, and OneNote page IDs from the source vault, so keep the
reports out of public repositories.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import html as htmlmod
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

URL_RE = re.compile(r"https?://[^\s<>\]\}\"']+", re.I)
SOURCE_PAGE_RE = re.compile(r'^source_page_id:\s*"?([^"\n]+)"?\s*$', re.M)
TITLE_RE = re.compile(r'^title:\s*"?([^"\n]+)"?\s*$', re.M)
MICROSOFT_LINK_HOST_PARTS = (
    "onenote.com",
    "1drv.ms",
    "onedrive.live.com",
    "graph.microsoft.com",
)


class LinkParser(HTMLParser):
    """Collect anchors from OneNote HTML while preserving visible link text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.anchors: list[dict[str, str]] = []
        self._current: dict[str, str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        attr_map = {key: value or "" for key, value in attrs}
        self._current = {
            "href": attr_map.get("href", ""),
            "text": "",
            "title": attr_map.get("title", ""),
        }

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._current is not None:
            self._current["text"] = re.sub(r"\s+", " ", self._current.get("text", "")).strip()
            self.anchors.append(self._current)
            self._current = None

    def handle_data(self, data: str) -> None:
        if self._current is not None:
            self._current["text"] += data


def normalize_url(url: str) -> str:
    """Normalize enough for comparison without dropping meaningful query values."""
    if not url:
        return ""
    url = htmlmod.unescape(url).strip().strip("<>\"'")
    try:
        parsed = urllib.parse.urlsplit(url)
        query_pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        query = urllib.parse.urlencode(sorted(query_pairs), doseq=True)
        path = urllib.parse.unquote(parsed.path)
        if path != "/":
            path = path.rstrip("/")
        return urllib.parse.urlunsplit(
            (
                parsed.scheme.lower(),
                parsed.netloc.lower(),
                path,
                query,
                urllib.parse.unquote(parsed.fragment),
            )
        )
    except Exception:
        return url


def bare_url(url: str) -> str:
    """Return URL without query parameters for partial/same-base matching."""
    try:
        parsed = urllib.parse.urlsplit(normalize_url(url))
        return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", parsed.fragment))
    except Exception:
        return normalize_url(url)


def parse_markdown_link_targets(text: str) -> list[str]:
    """Parse Markdown link targets, including targets with balanced parentheses."""
    targets: list[str] = []
    i = 0
    while True:
        start = text.find("](", i)
        if start == -1:
            break
        j = start + 2
        if j < len(text) and text[j] == "<":
            k = text.find(">", j + 1)
            if k != -1:
                targets.append(text[j + 1 : k])
                i = k + 1
                continue
        depth = 0
        k = j
        while k < len(text):
            ch = text[k]
            if ch == "\\":
                k += 2
                continue
            if ch == "(":
                depth += 1
            elif ch == ")":
                if depth == 0:
                    targets.append(text[j:k])
                    break
                depth -= 1
            k += 1
        i = max(k + 1, j + 1)
    return targets


def extract_current_links(text: str) -> list[str]:
    """Extract external links from Markdown links/images and bare URLs."""
    links: list[str] = []
    for target in parse_markdown_link_targets(text):
        target = target.strip().strip("<>")
        if target.lower().startswith(("http://", "https://")):
            links.append(target)
    for match in URL_RE.finditer(text):
        links.append(match.group(0).rstrip(".,;"))
    return sorted({normalized for link in links if (normalized := normalize_url(link))})


def title_for(text: str, path: Path) -> str:
    match = TITLE_RE.search(text)
    if match:
        return match.group(1).strip()
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem


def is_external_web(url: str) -> bool:
    normalized = normalize_url(url)
    if not normalized.startswith(("http://", "https://")):
        return False
    host = urllib.parse.urlsplit(normalized).netloc.lower()
    return not any(part in host for part in MICROSOFT_LINK_HOST_PARTS)


def load_access_token(auth_json: Path | None, explicit_token: str | None) -> str:
    if explicit_token:
        return explicit_token
    env_token = os.getenv("MSGRAPH_ACCESS_TOKEN")
    if env_token:
        return env_token
    env_json = os.getenv("MSGRAPH_ONENOTE_AUTH_JSON")
    token_path = auth_json or (Path(env_json) if env_json else None)
    if not token_path:
        raise SystemExit(
            "No access token found. Pass --auth-json, set MSGRAPH_ONENOTE_AUTH_JSON, "
            "or set MSGRAPH_ACCESS_TOKEN."
        )
    data = json.loads(token_path.read_text(encoding="utf-8"))
    token = data.get("access_token") or data.get("token")
    if not token:
        raise SystemExit(f"No access_token key found in {token_path}")
    return token


def fetch_page_content(page_id: str, token: str, retries: int) -> tuple[str | None, str | None]:
    url = "https://graph.microsoft.com/v1.0/me/onenote/pages/" + urllib.parse.quote(page_id, safe="") + "/content"
    last_error: str | None = None
    for attempt in range(retries + 1):
        request = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                return response.read().decode("utf-8", "replace"), None
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", "replace")[:300]
            except Exception:
                pass
            last_error = f"HTTP {exc.code}: {body}"
            if exc.code in {429, 500, 502, 503, 504} and attempt < retries:
                retry_after = exc.headers.get("Retry-After")
                delay = float(retry_after) if retry_after and retry_after.isdigit() else 2**attempt
                time.sleep(min(delay, 30))
                continue
            return None, last_error
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < retries:
                time.sleep(2**attempt)
    return None, last_error


def load_notes(vault_root: Path, output_dir: Path) -> list[dict[str, Any]]:
    notes: list[dict[str, Any]] = []
    for path in vault_root.rglob("*.md"):
        if ".git" in path.parts or output_dir in path.parents or path == output_dir:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        match = SOURCE_PAGE_RE.search(text)
        if not match:
            continue
        notes.append(
            {
                "path": str(path.relative_to(vault_root)).replace("\\", "/"),
                "title": title_for(text, path),
                "page_id": match.group(1).strip(),
                "current_links": extract_current_links(text),
            }
        )
    return notes


def audit_one(note: dict[str, Any], token: str, retries: int) -> dict[str, Any]:
    html, error = fetch_page_content(note["page_id"], token, retries)
    result = dict(note)
    if error:
        result.update(
            {
                "fetch_error": error,
                "source_links": [],
                "source_external_links": [],
                "missing_links": [],
                "missing_external_links": [],
                "partial_links": [],
                "partial_external_links": [],
            }
        )
        return result

    parser = LinkParser()
    parser.feed(html or "")
    seen: dict[str, dict[str, str]] = {}
    for anchor in parser.anchors:
        href = normalize_url(anchor.get("href", ""))
        if not href:
            continue
        label = anchor.get("text") or anchor.get("title") or ""
        if href not in seen:
            seen[href] = {"href": href, "text": label}
        elif label and label not in seen[href].get("text", ""):
            seen[href]["text"] = (seen[href].get("text", "") + " | " + label).strip(" |")

    source_links = list(seen.values())
    current_links = set(note["current_links"])
    current_bare_links = {bare_url(link) for link in current_links}
    missing: list[dict[str, str]] = []
    partial: list[dict[str, str]] = []
    for item in source_links:
        href = item["href"]
        if href in current_links:
            continue
        if bare_url(href) in current_bare_links:
            partial.append(item)
        else:
            missing.append(item)

    result.update(
        {
            "fetch_error": None,
            "source_links": source_links,
            "source_external_links": [item for item in source_links if is_external_web(item["href"])],
            "missing_links": missing,
            "missing_external_links": [item for item in missing if is_external_web(item["href"])],
            "partial_links": partial,
            "partial_external_links": [item for item in partial if is_external_web(item["href"])],
        }
    )
    return result


def write_reports(results: list[dict[str, Any]], output_dir: Path, report_stem: str) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "notes_with_source_page_id": len(results),
        "fetched_ok": sum(1 for result in results if not result.get("fetch_error")),
        "fetch_errors": sum(1 for result in results if result.get("fetch_error")),
        "source_links_total": sum(len(result.get("source_links", [])) for result in results),
        "source_external_links_total": sum(len(result.get("source_external_links", [])) for result in results),
        "notes_with_missing_any_links": sum(1 for result in results if result.get("missing_links") or result.get("partial_links")),
        "notes_with_missing_external_links": sum(
            1 for result in results if result.get("missing_external_links") or result.get("partial_external_links")
        ),
        "missing_links_total": sum(len(result.get("missing_links", [])) for result in results),
        "missing_external_links_total": sum(len(result.get("missing_external_links", [])) for result in results),
        "partial_external_links_total": sum(len(result.get("partial_external_links", [])) for result in results),
    }
    payload = {"summary": summary, "results": results}
    json_path = output_dir / f"{report_stem}.json"
    md_path = output_dir / f"{report_stem}.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["# OneNote link preservation audit", ""]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## Pages with missing/partial external source links")
    missing_external_pages = [
        result for result in results if result.get("missing_external_links") or result.get("partial_external_links")
    ]
    if not missing_external_pages:
        lines.append("None found.")
    else:
        for result in missing_external_pages:
            lines.append(f"\n### {result['path']}")
            if result.get("missing_external_links"):
                lines.append("Missing:")
                for item in result["missing_external_links"]:
                    label = item.get("text") or item["href"]
                    lines.append(f"- [{label}](<{item['href']}>)")
            if result.get("partial_external_links"):
                lines.append("Partial / same base URL but query differs:")
                for item in result["partial_external_links"]:
                    label = item.get("text") or item["href"]
                    lines.append(f"- [{label}](<{item['href']}>)")
    if summary["fetch_errors"]:
        lines.append("\n## Fetch errors")
        for result in results:
            if result.get("fetch_error"):
                lines.append(f"- `{result['path']}`: {result['fetch_error']}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"summary": summary, "json": str(json_path), "markdown": str(md_path)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vault", type=Path, help="Path to the migrated Obsidian vault")
    parser.add_argument("--auth-json", type=Path, help="JSON file containing a Microsoft Graph access_token")
    parser.add_argument("--access-token", help="Microsoft Graph access token; overrides --auth-json")
    parser.add_argument("--out-dir", type=Path, help="Output directory; defaults to <vault>/_audit")
    parser.add_argument("--report-stem", default="onenote-link-audit", help="Report filename stem")
    parser.add_argument("--workers", type=int, default=2, help="Concurrent page fetches")
    parser.add_argument("--retries", type=int, default=3, help="Retries per Graph request")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    vault = args.vault.resolve()
    output_dir = (args.out_dir or (vault / "_audit")).resolve()
    token = load_access_token(args.auth_json, args.access_token)
    notes = load_notes(vault, output_dir)
    results: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = [executor.submit(audit_one, note, token, args.retries) for note in notes]
        for index, future in enumerate(concurrent.futures.as_completed(futures), 1):
            results.append(future.result())
            if index % 25 == 0:
                print(f"audited {index}/{len(notes)}")
    results.sort(key=lambda result: result["path"].lower())
    print(json.dumps(write_reports(results, output_dir, args.report_stem), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
