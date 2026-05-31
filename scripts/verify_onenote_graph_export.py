"""Verify OneNote Graph Markdown export layout without running migration."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

DEFAULT_TARGET = Path.home() / 'Documents' / 'OneNote-Migration-Staging-Sample'
REMOTE_GRAPH_RE = re.compile(r'https://graph\.microsoft\.com', re.I)


def iter_markdown_images(text: str):
    """Yield inline Markdown image info, including balanced parentheses in destinations."""
    i = 0
    marker = '!['
    while True:
        start = text.find(marker, i)
        if start == -1:
            return
        alt_start = start + len(marker)
        alt_end = text.find(']', alt_start)
        if alt_end == -1 or alt_end + 1 >= len(text) or text[alt_end + 1] != '(':
            i = start + len(marker)
            continue
        dest_start = alt_end + 2
        depth = 0
        j = dest_start
        while j < len(text):
            ch = text[j]
            if ch == '\\':
                j += 2
                continue
            if ch == '(':
                depth += 1
            elif ch == ')':
                if depth == 0:
                    line_start = text.rfind('\n', 0, start) + 1
                    yield {
                        'ref': text[dest_start:j],
                        'alt': text[alt_start:alt_end],
                        'line_prefix': text[line_start:start],
                    }
                    i = j + 1
                    break
                depth -= 1
            j += 1
        else:
            i = dest_start


def iter_markdown_image_refs(text: str):
    for image in iter_markdown_images(text):
        yield image['ref']


def detect_image_extension(data: bytes):
    if data.startswith(b'\x89PNG\r\n\x1a\n'): return '.png'
    if data.startswith(b'\xff\xd8\xff'): return '.jpg'
    if data.startswith((b'GIF87a', b'GIF89a')): return '.gif'
    if len(data) >= 12 and data[:4] == b'RIFF' and data[8:12] == b'WEBP': return '.webp'
    return None


def main(root: Path) -> int:
    md_files = list(root.rglob('*.md')) if root.exists() else []
    index_files = [p for p in md_files if p.name.lower() == 'index.md']
    visible_assets = [p for p in root.rglob('assets') if p.is_dir()] if root.exists() else []
    hidden_assets = [p for p in root.rglob('.assets') if p.is_dir()] if root.exists() else []
    broken_refs, remote_graph_urls, invalid_signatures = [], [], []
    render_blocking_refs = []
    image_embeds = 0
    for md in md_files:
        text = md.read_text(encoding='utf-8', errors='replace')
        if REMOTE_GRAPH_RE.search(text):
            remote_graph_urls.append(str(md))
        for image in iter_markdown_images(text):
            ref = image['ref']
            image_embeds += 1
            prefix = image['line_prefix']
            indented_as_code = '\t' in prefix or len(prefix.replace('\t', '    ')) >= 4
            multiline_alt = '\n' in image['alt'] or '\r' in image['alt']
            if indented_as_code or multiline_alt:
                reasons = []
                if indented_as_code: reasons.append('indented-as-code')
                if multiline_alt: reasons.append('multiline-alt')
                render_blocking_refs.append(f'{md}: {ref} ({", ".join(reasons)})')
            if re.match(r'^[a-z]+://', ref, re.I):
                if REMOTE_GRAPH_RE.search(ref): remote_graph_urls.append(f'{md}: {ref}')
                continue
            target = (md.parent / ref).resolve()
            if not target.exists():
                broken_refs.append(f'{md}: {ref}')
                continue
            ext = detect_image_extension(target.read_bytes())
            if ext is None:
                invalid_signatures.append(str(target))
    manifest_failed_or_partial = []
    manifest = root / '_manifest.json'
    if manifest.exists():
        data = json.loads(manifest.read_text(encoding='utf-8'))
        entries = data if isinstance(data, list) else data.get('entries', [])
        latest_entries = {}
        non_page_entries = []
        for entry in entries:
            page_id = entry.get('page_id')
            if page_id:
                latest_entries[page_id] = entry
            else:
                non_page_entries.append(entry)
        current_entries = list(latest_entries.values()) + non_page_entries
        manifest_failed_or_partial = [e for e in current_entries if e.get('status') in {'failed', 'partial', 'failed_fetch', 'failed_section_pages'}]
    summary = {
        'target': str(root),
        'markdown_count': len(md_files),
        'index_md_count': len(index_files),
        'visible_assets_dirs': len(visible_assets),
        'hidden_assets_dirs': len(hidden_assets),
        'markdown_image_embeds': image_embeds,
        'render_blocking_image_refs_count': len(render_blocking_refs),
        'render_blocking_image_ref_samples': render_blocking_refs[:50],
        'broken_local_refs': broken_refs,
        'remote_graph_urls': remote_graph_urls,
        'invalid_signatures_for_referenced_images': invalid_signatures,
        'manifest_failed_or_partial_count': len(manifest_failed_or_partial),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    hard_errors = broken_refs or remote_graph_urls or invalid_signatures or hidden_assets or render_blocking_refs
    return 1 if hard_errors else 0


if __name__ == '__main__':
    sys.exit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_TARGET))
