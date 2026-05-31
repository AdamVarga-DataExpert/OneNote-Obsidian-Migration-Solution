"""Repair missing OneNote source links in migrated Obsidian notes.

Input is the JSON report from ``audit_onenote_links.py``. The repair is
conservative: it only wraps preserved anchor text inline when the match is clear;
otherwise it appends the exact URL to a ``## Source links`` section. Generated
backup and repair reports can contain private note paths/titles/URLs, so keep
them out of public repositories.
"""
from __future__ import annotations

import argparse
import html as htmlmod
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, unquote, urlsplit, urlunsplit

GENERIC_LABELS = {
    "link",
    "url",
    "source",
    "here",
    "website",
    "video",
    "article",
    "google amp result",
}
URL_RE = re.compile(r"https?://[^\s<>\]\}\"']+", re.I)


def normalize_url(url: str) -> str:
    if not url:
        return ""
    url = htmlmod.unescape(url).strip().strip("<>\"'")
    try:
        parsed = urlsplit(url)
        query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
        query = urlencode(sorted(query_pairs), doseq=True)
        path = unquote(parsed.path)
        if path != "/":
            path = path.rstrip("/")
        return urlunsplit(
            (parsed.scheme.lower(), parsed.netloc.lower(), path, query, unquote(parsed.fragment))
        )
    except Exception:
        return url


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


def extract_links(text: str) -> set[str]:
    links: list[str] = []
    for target in parse_markdown_link_targets(text):
        target = target.strip().strip("<>")
        if target.lower().startswith(("http://", "https://")):
            links.append(target)
    for match in URL_RE.finditer(text):
        links.append(match.group(0).rstrip(".,;"))
    return {normalized for link in links if (normalized := normalize_url(link))}


def markdown_link(label: str, href: str) -> str:
    label = (label or href).strip()
    label = label.replace("[", "\\[").replace("]", "\\]")
    return f"[{label}](<{href}>)"


def is_probably_generic(label: str) -> bool:
    label = re.sub(r"\s+", " ", (label or "").strip()).lower()
    if not label or label in GENERIC_LABELS:
        return True
    return len(label) <= 3 and all(ord(char) < 128 for char in label)


def frontmatter_end_line_index(lines: list[str]) -> int:
    if not lines or lines[0].strip() != "---":
        return 0
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return index + 1
    return 0


def line_already_has_url(line: str) -> bool:
    lower = line.lower()
    return "http://" in lower or "https://" in lower


def replace_label_inline(text: str, label: str, href: str) -> tuple[str, bool, str | None]:
    """Wrap clear preserved anchor text in a Markdown link."""
    if not label or is_probably_generic(label):
        return text, False, None
    lines = text.splitlines(True)
    start_index = frontmatter_end_line_index(lines)
    symbolish = len(label.strip()) <= 3 and any(ord(char) > 127 for char in label.strip())
    for index in range(start_index, len(lines)):
        line = lines[index]
        if label not in line or line_already_has_url(line):
            continue
        raw_line = line.rstrip("\r\n")
        newline = line[len(raw_line) :]
        stripped = raw_line.strip()
        leading = raw_line[: len(raw_line) - len(raw_line.lstrip())]
        if symbolish and stripped.startswith(label.strip()) and len(stripped) > len(label.strip()) + 4:
            lines[index] = leading + markdown_link(stripped, href) + newline
            return "".join(lines), True, "wrapped_line"
        position = raw_line.find(label)
        if position >= 0:
            before = raw_line[:position]
            # Avoid replacing inside an existing Markdown link label.
            if before.rfind("[") > before.rfind("]"):
                continue
            new_raw = raw_line[:position] + markdown_link(label, href) + raw_line[position + len(label) :]
            lines[index] = new_raw + newline
            return "".join(lines), True, "inline_label"
    return text, False, None


def append_source_links(text: str, items: list[dict[str, Any]]) -> str:
    if not items:
        return text
    lines = []
    for item in items:
        label = item.get("text") or item.get("href") or "Source"
        href = item["href"]
        lines.append(f"- {markdown_link(label, href)}")
    if "\n## Source links\n" not in text:
        return text.rstrip() + "\n\n## Source links\n" + "\n".join(lines) + "\n"
    return text.rstrip() + "\n" + "\n".join(lines) + "\n"


def repair_note(vault_root: Path, backup_root: Path, relative_path: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    path = vault_root / relative_path
    original = path.read_text(encoding="utf-8", errors="replace")
    current_links = extract_links(original)
    text = original
    placed: list[dict[str, Any]] = []
    appended: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for item in items:
        href = item["href"]
        normalized = normalize_url(href)
        if normalized in current_links or href in text:
            skipped.append({**item, "reason": "already_present"})
            continue
        label = item.get("text") or href
        updated_text, ok, method = replace_label_inline(text, label, href)
        if ok:
            text = updated_text
            current_links = extract_links(text)
            placed.append({**item, "method": method})
        else:
            appended.append(item)

    if appended:
        text = append_source_links(text, appended)

    changed = text != original
    if changed:
        backup_path = backup_root / relative_path
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup_path)
        path.write_text(text, encoding="utf-8", newline="")

    return {
        "path": relative_path.replace("\\", "/"),
        "changed": changed,
        "inline_restored": len(placed),
        "appended": len(appended),
        "skipped": len(skipped),
        "placed": placed,
        "appended_items": appended,
        "skipped_items": skipped,
    }


def collect_affected_notes(audit_payload: dict[str, Any]) -> list[tuple[str, list[dict[str, Any]]]]:
    affected: list[tuple[str, list[dict[str, Any]]]] = []
    for result in audit_payload.get("results", []):
        items: list[dict[str, Any]] = []
        items.extend(result.get("missing_external_links", []))
        items.extend(result.get("partial_external_links", []))
        if items:
            affected.append((result["path"], items))
    return affected


def write_reports(reports: list[dict[str, Any]], report_json: Path, report_md: Path) -> dict[str, Any]:
    report_json.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "affected_notes": len(reports),
        "changed_notes": sum(1 for report in reports if report["changed"]),
        "links_restored_inline": sum(report["inline_restored"] for report in reports),
        "links_appended_to_source_links": sum(report["appended"] for report in reports),
        "links_skipped_already_present": sum(report["skipped"] for report in reports),
    }
    report_json.write_text(
        json.dumps({"summary": summary, "notes": reports}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = ["# OneNote missing-link repair report", ""]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## Changed notes")
    changed = [report for report in reports if report["changed"]]
    if not changed:
        lines.append("None.")
    else:
        for report in changed:
            lines.append(f"- `{report['path']}`: inline={report['inline_restored']}, appended={report['appended']}")
    report_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"summary": summary, "report_json": str(report_json), "report_md": str(report_md)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vault", type=Path, help="Path to the migrated Obsidian vault")
    parser.add_argument(
        "--audit-json",
        type=Path,
        help="Audit JSON from audit_onenote_links.py; defaults to <vault>/_audit/onenote-link-audit.json",
    )
    parser.add_argument("--backup-root", type=Path, help="Backup directory; defaults next to the vault with a timestamp")
    parser.add_argument("--report-json", type=Path, help="Repair JSON path; defaults to <vault>/_audit/onenote-link-repair-report.json")
    parser.add_argument("--report-md", type=Path, help="Repair Markdown path; defaults to <vault>/_audit/onenote-link-repair-report.md")
    parser.add_argument("--dry-run", action="store_true", help="Write reports without changing notes or creating backups")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    vault = args.vault.resolve()
    audit_json = (args.audit_json or (vault / "_audit" / "onenote-link-audit.json")).resolve()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_root = (args.backup_root or (vault.parent / f"{vault.name}_link_repair_backup_{timestamp}")).resolve()
    report_json = (args.report_json or (vault / "_audit" / "onenote-link-repair-report.json")).resolve()
    report_md = (args.report_md or (vault / "_audit" / "onenote-link-repair-report.md")).resolve()

    payload = json.loads(audit_json.read_text(encoding="utf-8"))
    affected = collect_affected_notes(payload)
    reports: list[dict[str, Any]] = []
    if args.dry_run:
        for relative_path, items in affected:
            reports.append(
                {
                    "path": relative_path,
                    "changed": False,
                    "inline_restored": 0,
                    "appended": len(items),
                    "skipped": 0,
                    "placed": [],
                    "appended_items": items,
                    "skipped_items": [],
                    "dry_run": True,
                }
            )
    else:
        backup_root.mkdir(parents=True, exist_ok=True)
        for relative_path, items in affected:
            reports.append(repair_note(vault, backup_root, relative_path, items))

    print(json.dumps(write_reports(reports, report_json, report_md), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
