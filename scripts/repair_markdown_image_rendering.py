#!/usr/bin/env python3
"""Repair Markdown image syntax that can block Obsidian rendering.

Fixes two common OneNote export artifacts:
1. Markdown image links indented with a tab or >=4 spaces, which Markdown treats as code.
2. Image alt text split across multiple lines, which makes render/parsing fragile.

Usage:
    python scripts/repair_markdown_image_rendering.py C:/path/to/staging-vault
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

IMAGE_RE = re.compile(r'(?ms)^(?P<prefix>[\t ]*)!\[(?P<alt>.*?)\]\((?P<dest>[^\n]+?)\)')


def scan(root: Path) -> dict:
    files_with_images = refs = indented = multiline_alt = 0
    for md in root.rglob('*.md'):
        text = md.read_text(encoding='utf-8', errors='replace')
        matches = list(IMAGE_RE.finditer(text))
        if matches:
            files_with_images += 1
        for m in matches:
            refs += 1
            prefix = m.group('prefix') or ''
            if '\t' in prefix or len(prefix.replace('\t', '    ')) >= 4:
                indented += 1
            if '\n' in m.group('alt') or '\r' in m.group('alt'):
                multiline_alt += 1
    return {
        'files_with_images': files_with_images,
        'refs': refs,
        'indented': indented,
        'multiline_alt': multiline_alt,
    }


def repair_text(text: str) -> tuple[str, int]:
    changed = 0

    def repl(match: re.Match) -> str:
        nonlocal changed
        prefix = match.group('prefix') or ''
        alt = re.sub(r'\s+', ' ', match.group('alt') or 'image').strip() or 'image'
        dest = (match.group('dest') or '').strip()
        replacement = f'![{alt}]({dest})'
        if prefix or alt != match.group('alt') or dest != match.group('dest'):
            changed += 1
        return replacement

    return IMAGE_RE.sub(repl, text), changed


def main(root: Path) -> int:
    if not root.exists():
        raise SystemExit(f'Root does not exist: {root}')
    before = scan(root)
    changed_files = []
    for md in root.rglob('*.md'):
        original = md.read_text(encoding='utf-8', errors='replace')
        repaired, count = repair_text(original)
        if repaired != original:
            md.write_text(repaired, encoding='utf-8')
            changed_files.append({'path': str(md.relative_to(root)), 'image_refs_rewritten': count})
    after = scan(root)
    manifest = {
        'created_utc': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'target': str(root),
        'reason': 'Repair Markdown image syntax that Obsidian can render as code blocks because of OneNote indentation; collapse multiline alt text.',
        'before': before,
        'after': after,
        'changed_file_count': len(changed_files),
        'changed_files': changed_files,
    }
    out = root / '_image_render_repair_manifest.json'
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: repair_markdown_image_rendering.py <vault-root>')
    raise SystemExit(main(Path(sys.argv[1])))
