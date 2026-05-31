"""Graph-based OneNote Markdown exporter.

Word-free fallback exporter using Microsoft Graph page HTML plus image resources.
The output layout is inspired by Obsidian and OneNote MD Exporter conventions:
real page-title Markdown files, hierarchy folders, and visible per-folder assets/.
Safe sample staging destination defaults to OneNote-Migration-Staging-Sample.
"""
from __future__ import annotations

import asyncio
import html as htmllib
import json
import os
import re
import traceback
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse, unquote

from tools.onenote_tool import (
    list_onenote_notebooks,
    list_onenote_sections,
    OneNoteDelegatedTokenProvider,
)
from tools.microsoft_graph_client import MicrosoftGraphClient

MAX_NAME_LEN = 50
RESOURCE_FOLDER_NAME = 'assets'
RESOURCE_FOLDER_LOCATION = 'PageParentFolder'
PROCESSING_OF_PAGE_HIERARCHY = 'HierarchyAsFolderTree'
SAMPLE_MODE = True
SAMPLE_PAGE_LIMIT = 10
FORCE = False
DEST_ROOT = Path.home() / 'Documents' / 'OneNote-Migration-Staging-Sample'
FULL_DEST_ROOT = Path.home() / 'Documents' / 'OneNote-Migration-Staging-v2'
GRAPH_NOTEBOOK_PAUSE_SECONDS = 30
GRAPH_SECTION_PAUSE_SECONDS = 10
GRAPH_PAGE_PAUSE_SECONDS = 3
if SAMPLE_MODE:
    GRAPH_NOTEBOOK_PAUSE_SECONDS = 1
    GRAPH_SECTION_PAUSE_SECONDS = 0.5
    GRAPH_PAGE_PAUSE_SECONDS = 0.25
GRAPH_MAX_RETRY_ATTEMPTS = 8
GRAPH_MAX_RETRY_DELAY_SECONDS = 180
REDACT_QUERY_KEYS = {'token', 'access_token', 'code', 'sig', 'signature', 'auth', 'key', 'password', 'secret'}
REDACT_QUERY_KEY_PARTS = ('token', 'secret', 'password', 'passwd', 'auth', 'signature', 'sig', 'key', 'code', 'jwt')
IMG_TAG_RE = re.compile(r'<img\b(?P<attrs>[^>]*)>', re.I | re.S)
ATTR_RE = re.compile(r'([\w:-]+)\s*=\s*(["\'])(.*?)\2', re.S)


def clean_title_for_path(name, max_len=MAX_NAME_LEN):
    s = htmllib.unescape(str(name or '')).replace('\r', ' ').replace('\n', ' ')
    s = re.sub(r'[\\/:*?"<>|]+', '-', s)
    s = re.sub(r'\s+', ' ', s).strip().rstrip('.').strip()
    if len(s) > max_len:
        s = s[:max_len].rstrip(' .')
    return s or 'Untitled'

slug = clean_title_for_path


def page_md_path(section_root: Path, page_node: dict) -> Path:
    parts = [clean_title_for_path(p) for p in page_node.get('parent_path_parts') or []]
    return Path(section_root, *parts, clean_title_for_path(page_node.get('title')) + '.md')


def resource_folder_for_note(md_path: Path) -> Path:
    return md_path.parent / RESOURCE_FOLDER_NAME


def relative_asset_ref(md_path: Path, asset_path: Path) -> str:
    return os.path.relpath(asset_path, md_path.parent).replace(os.sep, '/')


def unique_path(candidate: Path, used: set[str]) -> Path:
    stem, suffix, parent = candidate.stem, candidate.suffix, candidate.parent
    n = 1
    p = candidate
    while p.exists() or str(p) in used:
        n += 1
        base = f'{stem} ({n})'
        if len(base) > MAX_NAME_LEN:
            base = f'{stem[:MAX_NAME_LEN - len(f" ({n})")].rstrip()} ({n})'
        p = parent / f'{base}{suffix}'
    used.add(str(p))
    return p


def _attrs(attr_text):
    return {m.group(1).lower(): htmllib.unescape(m.group(3)) for m in ATTR_RE.finditer(attr_text or '')}


def parse_img_tags(html):
    for m in IMG_TAG_RE.finditer(html or ''):
        attrs = _attrs(m.group('attrs'))
        if attrs.get('src'):
            yield m.group(0), attrs.get('src'), attrs.get('alt', '')


def _strip_html(html):
    s = (html or '').replace('\r', '')
    s = re.sub(r'(?is)<br\s*/?>', '\n', s)
    s = re.sub(r'(?is)</p\s*>', '\n\n', s)
    s = re.sub(r'(?is)</div\s*>', '\n', s)
    s = re.sub(r'(?is)</li\s*>', '\n- ', s)
    s = re.sub(r'(?is)<[^>]+>', '', s)
    s = htmllib.unescape(s)
    s = re.sub(r'(?m)^[\t ]+(!\[)', r'\1', s)
    s = re.sub(r'\n{3,}', '\n\n', s)
    return s.strip()


def markdown_image_alt_text(value):
    s = htmllib.unescape(str(value or 'image')).replace('\r', ' ').replace('\n', ' ')
    s = re.sub(r'\s+', ' ', s).strip() or 'image'
    return s.replace('[', '(').replace(']', ')')


def html_to_markdown_with_images(html, replacements):
    stats = {'assets_expected': 0}
    def repl(m):
        attrs = _attrs(m.group('attrs'))
        src = attrs.get('src', '')
        alt = markdown_image_alt_text(attrs.get('alt', ''))
        stats['assets_expected'] += 1
        local = replacements.get(src)
        if local:
            return f'![{alt}]({local})'
        return '[Image not exported: source asset download failed]'
    return _strip_html(IMG_TAG_RE.sub(repl, html or '')), stats


def detect_image_extension(data: bytes):
    if data.startswith(b'\x89PNG\r\n\x1a\n'): return '.png'
    if data.startswith(b'\xff\xd8\xff'): return '.jpg'
    if data.startswith((b'GIF87a', b'GIF89a')): return '.gif'
    if len(data) >= 12 and data[:4] == b'RIFF' and data[8:12] == b'WEBP': return '.webp'
    return None


def improved_asset_name(src, idx, page_title, data):
    ext = detect_image_extension(data) or Path(unquote(urlparse(src).path)).suffix.lower()
    if ext == '.jpeg': ext = '.jpg'
    if ext not in {'.png', '.jpg', '.gif', '.webp'}: ext = '.bin'
    base = Path(unquote(urlparse(src).path)).name
    if not base or base == '$value' or Path(base).suffix.lower() in {'', '.bin'}:
        return f'{clean_title_for_path(page_title).lower().replace(" ", "-")}-{idx:02d}{ext}'
    return clean_title_for_path(Path(base).stem) + ext


def is_sensitive_query_key(key: str) -> bool:
    lowered = (key or '').lower().replace('-', '_')
    return lowered in REDACT_QUERY_KEYS or any(part in lowered for part in REDACT_QUERY_KEY_PARTS)


def redact_url(url):
    if not url: return ''
    p = urlparse(url)
    q = [(k, 'REDACTED' if is_sensitive_query_key(k) else v) for k, v in parse_qsl(p.query, keep_blank_values=True)]
    return urlunparse((p.scheme, p.netloc, p.path, p.params, urlencode(q), p.fragment))


URL_LIKE_RE = re.compile(r'https?://[^\s<>"\']+')


def redact_error_message(message):
    def repl(match):
        url = match.group(0)
        trailing = ''
        while url and url[-1] in '.,;)]}':
            trailing = url[-1] + trailing
            url = url[:-1]
        return redact_url(url) + trailing
    return URL_LIKE_RE.sub(repl, str(message or ''))


def path_is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def yaml_quote(value):
    return json.dumps('' if value is None else str(value), ensure_ascii=False)


def build_frontmatter(page, notebook, section, has_assets, status):
    link = page.get('links', {}).get('oneNoteWebUrl', {}).get('href', '')
    rows = {
        'title': page.get('title', ''), 'created': page.get('createdDateTime', ''),
        'updated': page.get('lastModifiedDateTime', ''), 'type': 'source-note', 'source': 'onenote',
        'source_notebook': notebook, 'source_section': section, 'source_page_id': page.get('id', ''),
        'source_link': redact_url(link), 'exporter': 'hermes-graph-onenote-md', 'export_status': status,
    }
    lines = ['---'] + [f'{k}: {yaml_quote(v)}' for k, v in rows.items()]
    if has_assets: lines.append(f'asset_folder: {RESOURCE_FOLDER_NAME}')
    lines.append('---')
    return '\n'.join(lines)


async def with_graph_retries(call, *, sleep=asyncio.sleep, initial_delay=10):
    delay = initial_delay
    for attempt in range(GRAPH_MAX_RETRY_ATTEMPTS):
        try:
            return await call()
        except Exception as e:
            status = getattr(e, 'status_code', None)
            if status == 429 and attempt < GRAPH_MAX_RETRY_ATTEMPTS - 1:
                retry_after = getattr(e, 'retry_after_seconds', None)
                await sleep(min(float(retry_after or delay), GRAPH_MAX_RETRY_DELAY_SECONDS))
                delay = min(delay * 2, GRAPH_MAX_RETRY_DELAY_SECONDS)
                continue
            raise


async def safe_list_notebooks():
    return await with_graph_retries(lambda: list_onenote_notebooks())


async def safe_list_sections(notebook_id):
    return await with_graph_retries(lambda: list_onenote_sections(notebook_id=notebook_id))


async def list_pages_for_export(graph: MicrosoftGraphClient, section_id):
    params = {'$select': 'id,title,createdDateTime,lastModifiedDateTime,links,parentSection,level,order', '$top': 100}
    pages = await with_graph_retries(lambda: graph.collect_paginated(f'/me/onenote/sections/{section_id}/pages', params=params))
    return sort_pages_for_export(pages)


async def get_page_content_for_export(graph: MicrosoftGraphClient, page_id):
    response = await graph._request(
        'GET',
        f'/me/onenote/pages/{page_id}/content',
        headers={'Accept': 'text/html'},
    )
    return response.text


def sort_pages_for_export(pages):
    decorated = list(enumerate(pages or []))
    def key(item):
        i, p = item
        order = p.get('order')
        try: return (0, float(order), str(p.get('title','')).lower(), str(p.get('id','')))
        except (TypeError, ValueError): return (1, i, str(p.get('title','')).lower(), str(p.get('id','')))
    return [p for _, p in sorted(decorated, key=key)]


def build_page_nodes(pages):
    if not any(isinstance(p.get('level'), int) for p in pages or []):
        return [dict(p, parent_path_parts=[]) for p in pages or []], ['missing levels; flattened']
    min_level = min(int(p.get('level', 0)) for p in pages if isinstance(p.get('level'), int))
    stack, nodes, warnings = [], [], []
    for p in pages or []:
        if not isinstance(p.get('level'), int):
            warnings.append(f"missing level for page {p.get('id')}; flattened")
            parent_parts = []
        else:
            level = int(p['level']) - min_level
            if level > len(stack):
                warnings.append(f"level gap for page {p.get('id')}; flattened")
                parent_parts = []
            else:
                stack = stack[:level]
                parent_parts = [x.get('title', 'Untitled') for x in stack]
                stack.append(p)
        nodes.append(dict(p, parent_path_parts=parent_parts))
    return nodes, warnings


async def download_assets(graph, md_path: Path, page_html: str, page_title: str):
    replacements, failures = {}, []
    img_tags = list(parse_img_tags(page_html))
    if not img_tags: return replacements, {'assets_expected': 0, 'assets_downloaded': 0, 'asset_failures': []}
    assets_dir = resource_folder_for_note(md_path)
    used_asset_paths: set[str] = set()
    seq = 0
    for _, src, _alt in img_tags:
        seq += 1
        tmp = assets_dir / f'.download-{seq}.part'
        try:
            await with_graph_retries(lambda s=src, t=tmp: graph.download_to_file(s, t, headers={'Accept': 'application/octet-stream'}))
            data = tmp.read_bytes()
            if detect_image_extension(data) is None:
                failures.append({'src': redact_url(src), 'error': 'unknown image signature'})
                tmp.unlink(missing_ok=True)
                continue
            name = improved_asset_name(src, seq, page_title, data)
            assets_dir.mkdir(parents=True, exist_ok=True)
            final = unique_path(assets_dir / name, used_asset_paths)
            tmp.replace(final)
            replacements[src] = relative_asset_ref(md_path, final)
        except Exception as e:
            tmp.unlink(missing_ok=True)
            failures.append({'src': redact_url(src), 'error': redact_error_message(e)})
    try:
        if assets_dir.exists() and not any(assets_dir.iterdir()):
            assets_dir.rmdir()
    except OSError:
        pass
    return replacements, {'assets_expected': len(img_tags), 'assets_downloaded': len(replacements), 'asset_failures': failures}


def load_manifest(path):
    if not path.exists(): return []
    data = json.loads(path.read_text(encoding='utf-8'))
    return data if isinstance(data, list) else list(data.get('entries', []))


def write_manifest(path, entries):
    path.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding='utf-8')


def previous_success(entries, page_id, dest_root: Path | None = None):
    for e in reversed(entries):
        path = Path(e['path']) if e.get('path') else None
        if (
            e.get('page_id') == page_id
            and e.get('status') == 'success'
            and path
            and path.exists()
            and (dest_root is None or path_is_under(path, dest_root))
        ):
            return True
    return False


def previous_entry_path(entries, page_id, dest_root: Path | None = None):
    for e in reversed(entries):
        if e.get('page_id') == page_id and e.get('path'):
            path = Path(e['path'])
            if dest_root is not None and not path_is_under(path, dest_root):
                return None
            return path
    return None


async def main():
    DEST_ROOT.mkdir(parents=True, exist_ok=True)
    manifest_path = DEST_ROOT / '_manifest.json'
    manifests = load_manifest(manifest_path)
    graph = MicrosoftGraphClient(OneNoteDelegatedTokenProvider(), max_retries=0)
    notebooks = await safe_list_notebooks()
    pages_written = 0
    pages_seen = 0
    used_paths = set()
    sample_limit_reached = False
    for nb_idx, nb in enumerate(notebooks):
        if sample_limit_reached:
            break
        if nb_idx: await asyncio.sleep(GRAPH_NOTEBOOK_PAUSE_SECONDS)
        nb_name = nb.get('displayName', 'Untitled')
        nb_root = DEST_ROOT / clean_title_for_path(nb_name)
        sections = await safe_list_sections(nb['id'])
        for sec in sections:
            if sample_limit_reached:
                break
            await asyncio.sleep(GRAPH_SECTION_PAUSE_SECONDS)
            sec_name = sec.get('displayName', 'Untitled')
            sec_root = nb_root / clean_title_for_path(sec_name)
            try:
                pages = await list_pages_for_export(graph, sec['id'])
            except Exception as section_error:
                manifests.append({
                    'notebook': nb_name,
                    'section': sec_name,
                    'page_id': None,
                    'title': None,
                    'path': None,
                    'status': 'failed_section_pages',
                    'error': redact_error_message(section_error),
                    'assets_expected': 0,
                    'assets_downloaded': 0,
                    'asset_failures': [],
                    'warnings': [],
                })
                write_manifest(manifest_path, manifests)
                continue
            nodes, hierarchy_warnings = build_page_nodes(pages)
            for node in nodes:
                if SAMPLE_MODE and pages_seen >= SAMPLE_PAGE_LIMIT:
                    sample_limit_reached = True
                    break
                pages_seen += 1
                page_id = node.get('id')
                if not FORCE and previous_success(manifests, page_id, DEST_ROOT):
                    continue
                prior_path = previous_entry_path(manifests, page_id, DEST_ROOT)
                md_path = prior_path if prior_path and not FORCE else unique_path(page_md_path(sec_root, node), used_paths)
                entry = {'notebook': nb_name, 'section': sec_name, 'page_id': page_id, 'title': node.get('title'), 'path': str(md_path)}
                try:
                    try:
                        content = await with_graph_retries(lambda pid=page_id: get_page_content_for_export(graph, pid))
                    except Exception as fetch_error:
                        status = 'failed_fetch'
                        md_path.parent.mkdir(parents=True, exist_ok=True)
                        fm = build_frontmatter(node, nb_name, sec_name, False, status)
                        safe_error = redact_error_message(fetch_error)
                        md_path.write_text(f'{fm}\n\n# {node.get("title", "Untitled")}\n\n[Failed to fetch page content: {safe_error}]\n', encoding='utf-8')
                        entry.update(status=status, error=safe_error, warnings=hierarchy_warnings, assets_expected=0, assets_downloaded=0, asset_failures=[])
                        pages_written += 1
                        manifests.append(entry)
                        write_manifest(manifest_path, manifests)
                        await asyncio.sleep(GRAPH_PAGE_PAUSE_SECONDS)
                        continue
                    replacements, asset_stats = await download_assets(graph, md_path, content, node.get('title', 'Untitled'))
                    body, img_stats = html_to_markdown_with_images(content, replacements)
                    status = 'partial' if asset_stats['asset_failures'] else 'success'
                    md_path.parent.mkdir(parents=True, exist_ok=True)
                    fm = build_frontmatter(node, nb_name, sec_name, bool(replacements), status)
                    md_path.write_text(f'{fm}\n\n# {node.get("title", "Untitled")}\n\n{body}\n', encoding='utf-8')
                    entry.update(status=status, warnings=hierarchy_warnings, **asset_stats)
                    pages_written += 1
                except Exception as e:
                    entry.update(status='failed', error=redact_error_message(e), warnings=hierarchy_warnings, assets_expected=0, assets_downloaded=0, asset_failures=[])
                manifests.append(entry)
                write_manifest(manifest_path, manifests)
                await asyncio.sleep(GRAPH_PAGE_PAUSE_SECONDS)
    print({'pages_written': pages_written, 'pages_seen': pages_seen, 'dest_root': str(DEST_ROOT), 'sample_mode': SAMPLE_MODE})

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception:
        traceback.print_exc()
        raise
