# Adapt Python OneNote Graph Exporter with OneNote MD Exporter Layout Logic Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task, with verification after each task. Do not run the full migration until the small-sample export and local verification pass.

**Goal:** Upgrade the custom Python Graph-based OneNote exporter so it keeps the Word-free Graph extraction path but adopts the Obsidian-friendly layout and post-processing lessons from `alxnbl/onenote-md-exporter`.

**Architecture:** Keep `tmp_migrate_onenote_assets.py` as the base because it already avoids the blocked OneNote/Word `Publish(...)` path and downloads Graph image assets. Refactor it into testable pure helper functions plus a thin async Graph runner, then implement MD Exporter-inspired pathing: real page-title Markdown files, visible `assets/` folders beside each note, hierarchy-as-folder-tree when Graph page level/order data is available, stable attachment naming, local relative image references, source metadata frontmatter, manifest/checkpoint status, and deterministic verification.

**Tech Stack:** Python 3, Microsoft Graph delegated OneNote APIs, local filesystem, Markdown/Obsidian, existing Hermes OneNote Graph wrappers, stdlib `unittest` or direct script tests, existing vault scanner.

---

## Current source files and observed behavior

Primary custom exporter to adapt:
- `C:\Users\<user>\AppData\Local\hermes\hermes-agent\tmp_migrate_onenote_assets.py`

Relevant upstream exporter references:
- `C:\Users\<user>\onenote-md-exporter\src\OneNoteMdExporter\Services\Export\MdExportService.cs`
- `C:\Users\<user>\onenote-md-exporter\src\OneNoteMdExporter\Services\Export\ExportServiceBase.cs`
- `C:\Users\<user>\onenote-md-exporter\src\OneNoteMdExporter\Infrastructure\AppSettings.cs`
- `C:\Users\<user>\onenote-md-exporter\src\OneNoteMdExporter\appSettings.json`

Important current Python behavior to change:
- writes each page as `section/page-title/index.md`
- creates hidden `.assets` folders even when empty
- rewrites HTML image `src` values to `.assets/...`, but then `html_to_text()` strips the `<img>` tag entirely, so Markdown embeds are not guaranteed to appear
- manifest has no explicit success/failure/partial status
- page order/hierarchy is not source-order aware; current wrapper orders pages by `lastModifiedDateTime desc`

Important upstream logic to mimic:
- page Markdown path is a real title file: `section/Page title.md`
- child pages can become `section/Parent page/Child page.md`
- resource folder lives beside the Markdown file when `ResourceFolderLocation = PageParentFolder`
- visible resource folder name should be `assets`
- attachment/image references are relative from the note folder to the asset file
- avoid filename collisions deterministically
- frontmatter is added
- Obsidian-compatible link/image output must be verified by render/path semantics, not by file existence alone

---

## Non-goals

- Do not reintroduce the COM/Word `Publish(...)` path; it is blocked on this machine and defeats the purpose of the Python fallback.
- Do not mutate the existing staging vault destructively during the planning/first implementation pass.
- Do not delete failed-fetch notes; record them explicitly.
- Do not guess missing content from encrypted/unreadable pages.
- Do not expose or persist any token/secret/credential values in logs or manifests.

---

## Target output shape

For a normal page:

```text
C:\Users\<user>\Documents\OneNote-Migration-Staging\1 Projects\Shopping list.md
C:\Users\<user>\Documents\OneNote-Migration-Staging\1 Projects\assets\shopping-list-01.png
```

For a parent page with child/subpage if Graph hierarchy metadata is available:

```text
C:\Users\<user>\Documents\OneNote-Migration-Staging\1 Projects\Trip planning.md
C:\Users\<user>\Documents\OneNote-Migration-Staging\1 Projects\Trip planning\Flights.md
C:\Users\<user>\Documents\OneNote-Migration-Staging\1 Projects\Trip planning\assets\flights-01.jpg
```

Markdown image reference style:

```markdown
![image](assets/shopping-list-01.png)
```

This matches the upstream exporter’s normal Markdown image style and is Obsidian-compatible. If a later verification shows wiki embeds are more reliable in this vault, add a single config switch rather than hard-coding both styles.

---

## Task 1: Freeze the current exporter and create a testable copy

**Objective:** Preserve the working script before refactoring and create a canonical file path for the upgraded exporter.

**Files:**
- Read: `C:\Users\<user>\AppData\Local\hermes\hermes-agent\tmp_migrate_onenote_assets.py`
- Create: `C:\Users\<user>\AppData\Local\hermes\hermes-agent\tmp_migrate_onenote_assets_legacy.py`
- Create/Modify: `C:\Users\<user>\AppData\Local\hermes\hermes-agent\tmp_migrate_onenote_assets.py`

**Steps:**
1. Copy the current script to `tmp_migrate_onenote_assets_legacy.py` if the backup does not already exist.
2. Keep the active filename as `tmp_migrate_onenote_assets.py` so existing references still work.
3. Add a top-level docstring to the active script explaining:
   - Graph-based exporter
   - Word-free fallback
   - Obsidian/OneNote MD Exporter-inspired layout
   - staging destination

**Verification:**
Run:

```bash
python -m py_compile C:/Users/<user>/AppData/Local/hermes/hermes-agent/tmp_migrate_onenote_assets.py
```

Expected:
- exit code 0
- no syntax errors
- backup file exists

---

## Task 2: Add pure layout helpers before touching Graph logic

**Objective:** Make MD Exporter-style path decisions testable without calling Microsoft Graph.

**Files:**
- Modify: `C:\Users\<user>\AppData\Local\hermes\hermes-agent\tmp_migrate_onenote_assets.py`
- Create: `C:\Users\<user>\AppData\Local\hermes\hermes-agent\tests\test_onenote_graph_exporter_layout.py`

**Implementation requirements:**
Add small pure functions:

```python
MAX_NAME_LEN = 50
RESOURCE_FOLDER_NAME = "assets"
RESOURCE_FOLDER_LOCATION = "PageParentFolder"
PROCESSING_OF_PAGE_HIERARCHY = "HierarchyAsFolderTree"

INVALID_FILENAME_RE = re.compile(r'[\\/:*?"<>|]+')

def clean_title_for_path(name: str, max_len: int = MAX_NAME_LEN) -> str:
    value = INVALID_FILENAME_RE.sub('-', name or 'Untitled')
    value = re.sub(r'\s+', ' ', value).strip().rstrip('.')
    return (value[:max_len].rstrip().rstrip('.') or 'Untitled')
```

Add path helpers with upstream-inspired behavior:

```python
def page_md_path(section_root: Path, page_node: dict) -> Path:
    """Return section/Page.md or section/Parent/Child.md based on resolved parent_path_parts."""
```

```python
def resource_folder_for_note(md_path: Path) -> Path:
    return md_path.parent / RESOURCE_FOLDER_NAME
```

```python
def relative_asset_ref(md_path: Path, asset_path: Path) -> str:
    return asset_path.relative_to(md_path.parent).as_posix()
```

**Test cases:**
- invalid filename chars are replaced
- trailing dots/spaces are removed
- title length is capped
- normal page path is `Section/Page.md`, not `Section/Page/index.md`
- child page path is `Section/Parent/Child.md`
- resource folder is `Section/assets` for a section-level page
- resource folder is `Section/Parent/assets` for a child page
- relative asset ref is `assets/image.png`

**Verification:**
Run:

```bash
python -m unittest C:/Users/<user>/AppData/Local/hermes/hermes-agent/tests/test_onenote_graph_exporter_layout.py
```

Expected:
- tests pass
- no Graph calls are made

---

## Task 3: Implement deterministic filename collision handling

**Objective:** Mirror the upstream exporter’s uniqueness behavior so same-title pages or attachments do not overwrite each other.

**Files:**
- Modify: `tmp_migrate_onenote_assets.py`
- Modify: `tests/test_onenote_graph_exporter_layout.py`

**Implementation requirements:**
Add helper:

```python
def unique_path(candidate: Path, used: set[Path]) -> Path:
    if candidate not in used and not candidate.exists():
        used.add(candidate)
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix
    parent = candidate.parent
    i = 2
    while True:
        next_candidate = parent / f"{stem} ({i}){suffix}"
        if next_candidate not in used and not next_candidate.exists():
            used.add(next_candidate)
            return next_candidate
        i += 1
```

Apply this to:
- Markdown page file paths
- asset file paths

**Test cases:**
- two pages titled `Plan` become `Plan.md` and `Plan (2).md`
- two images named `image.png` become `image.png` and `image (2).png`
- existing files on disk are respected

**Verification:**
Run:

```bash
python -m unittest C:/Users/<user>/AppData/Local/hermes/hermes-agent/tests/test_onenote_graph_exporter_layout.py
```

Expected:
- all previous tests plus collision tests pass

---

## Task 4: Replace index.md writing with upstream-style real page filenames

**Objective:** Stop generating `index.md` per page and write real page-title Markdown files.

**Files:**
- Modify: `tmp_migrate_onenote_assets.py`

**Current code to replace:**

```python
page_dir = sec_root / slug(title)
page_dir.mkdir(parents=True, exist_ok=True)
...
rel = page_dir / 'index.md'
```

**New behavior:**
- compute `md_path = page_md_path(sec_root, page_node)`
- create `md_path.parent`
- write Markdown to `md_path`
- store `path: str(md_path)` in manifest
- do not create a per-page directory unless needed by hierarchy or assets

**Verification:**
Use a dry-run/fake data helper first, not live Graph:
- feed two fake pages into the writer
- confirm output uses `Page.md`, not `Page/index.md`

Run syntax check:

```bash
python -m py_compile C:/Users/<user>/AppData/Local/hermes/hermes-agent/tmp_migrate_onenote_assets.py
```

Expected:
- no syntax errors
- no reference to `index.md` remains in write logic except legacy comments/tests

---

## Task 5: Add Graph page metadata discovery for source order and hierarchy

**Objective:** Use Graph page `level` / `order` metadata if available, so Python can mimic MD Exporter’s `HierarchyAsFolderTree` behavior.

**Files:**
- Modify: `tmp_migrate_onenote_assets.py`
- Possibly leave `tools\onenote_tool.py` untouched unless the wrapper cannot expose needed fields

**Implementation requirements:**
Do not rely only on `list_onenote_pages()`, because the current wrapper selects:

```text
id,title,createdDateTime,lastModifiedDateTime,links,parentSection
```

and orders by:

```text
lastModifiedDateTime desc
```

Add a script-local function using `MicrosoftGraphClient` directly:

```python
async def list_pages_for_export(graph: MicrosoftGraphClient, section_id: str) -> list[dict]:
    path = f"/me/onenote/sections/{section_id}/pages"
    params = {
        "$select": "id,title,createdDateTime,lastModifiedDateTime,links,parentSection,level,order",
        "$top": 500,
    }
    pages = await graph.collect_paginated(path, params=params)
    return sort_pages_for_export(pages)
```

Add sort fallback:
- primary: numeric `order` when present
- secondary: original API order if no order
- final fallback: title, then id for deterministic output

Add hierarchy builder:

```python
def build_page_nodes(pages: list[dict]) -> list[dict]:
    """Attach parent_path_parts based on OneNote page level/order.
    If level is missing for all pages, return flat nodes with parent_path_parts=[] and manifest warning.
    """
```

Rules:
- level 0 or 1 is section-root page depending on Graph shape; normalize using the minimum observed level
- a page with higher level becomes child of the nearest preceding page with lower level
- if a level jump is invalid, flatten that page and record a warning

**Test cases:**
- flat pages produce no parent path
- parent level 0 + child level 1 yields `Parent/Child.md`
- grandchild works
- invalid level jump records warning and does not crash
- missing level data produces flat output plus manifest warning

**Verification:**
Run unit tests first.
Then run a metadata-only probe against one small section and print sanitized page keys/counts, without fetching page content.

Expected:
- page metadata can be retrieved or a safe fallback is recorded
- no full migration is started

---

## Task 6: Change asset folder logic from hidden `.assets` to visible `assets`

**Objective:** Match the upstream Obsidian-friendly setting `ResourceFolderName = assets` and avoid creating empty asset folders.

**Files:**
- Modify: `tmp_migrate_onenote_assets.py`
- Modify: layout tests

**Current code to replace:**

```python
assets_dir = page_dir / '.assets'
assets_dir.mkdir(parents=True, exist_ok=True)
...
replacements[src] = f'.assets/{asset_name}'
```

**New behavior:**
- compute assets directory from Markdown path:

```python
assets_dir = resource_folder_for_note(md_path)
```

- create `assets_dir` only when at least one image is actually going to be downloaded or written
- manifest should distinguish:
  - `assets_expected`
  - `assets_downloaded`
  - `asset_failures`
- frontmatter should say `asset_folder: assets` only when assets exist, or omit it for image-free pages

**Verification:**
- unit test: image-free page does not create `assets/`
- unit test: image page creates visible `assets/`
- search after sample export should show no new `.assets` folders in the sample output

---

## Task 7: Preserve image embeds instead of stripping image tags

**Objective:** Ensure images downloaded from OneNote appear in the Markdown body as local embeds.

**Files:**
- Modify: `tmp_migrate_onenote_assets.py`
- Add/modify tests for HTML conversion

**Problem to fix:**
The current flow rewrites HTML image src values, then `html_to_text()` removes all HTML tags. This can remove the image from the Markdown completely.

**Implementation requirements:**
Change conversion order so local replacements generate Markdown image syntax before generic tag stripping.

Add function:

```python
def replace_img_tags_with_markdown(html: str, replacements: dict[str, str]) -> str:
    """Replace <img ... src="remote" ...> with ![alt](local-relative-path)."""
```

Rules:
- preserve `alt` text when present
- default alt: `image`
- use relative refs such as `assets/image-01.png`
- if download failed and no local replacement exists, remove the remote URL from output and insert a visible placeholder:

```markdown
[Image not exported: source asset download failed]
```

Do not leave Graph URLs in final Markdown.

**Test cases:**
- `<img src="remote" alt="Diagram">` becomes `![Diagram](assets/diagram.png)`
- image without alt becomes `![image](assets/image.png)`
- failed image does not leave `https://graph.microsoft.com/...` in Markdown
- ordinary paragraphs and lists still convert to readable Markdown/plain text

**Verification:**
Run conversion tests.
Then run a sample export containing at least one image and verify:
- Markdown contains `![](...)` or `![alt](...)`
- referenced asset exists
- no remote Graph image URL remains

---

## Task 8: Improve asset filenames with extension detection and stable numbering

**Objective:** Avoid ambiguous `.bin` / `$value` assets and make Obsidian image rendering reliable.

**Files:**
- Modify: `tmp_migrate_onenote_assets.py`
- Add/modify tests for asset naming/signature detection

**Implementation requirements:**
Add image signature detection:

```python
IMAGE_SIGNATURES = [
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"\xff\xd8\xff", ".jpg"),
    (b"GIF87a", ".gif"),
    (b"GIF89a", ".gif"),
]

def detect_image_extension(path: Path) -> str | None:
    data = path.read_bytes()[:16]
    ...
```

After download:
- if asset name has `.bin`, no extension, or `$value`, rename based on signature
- use page slug and sequence number when the source filename is useless:
  - `shopping-list-01.png`
  - `shopping-list-02.jpg`
- if signature is unknown, keep file but mark `asset_status: unknown_signature` in manifest and do not count it as verified image

**Test cases:**
- PNG bytes get `.png`
- JPEG bytes get `.jpg`
- `$value` URL becomes page-based filename after download
- unknown bytes are recorded, not silently treated as image

**Verification:**
Run tests.
Run sample export and then scanner/signature check.

---

## Task 9: Add upstream-style frontmatter plus source traceability

**Objective:** Keep useful MD Exporter frontmatter while preserving Graph source provenance.

**Files:**
- Modify: `tmp_migrate_onenote_assets.py`

**Implementation requirements:**
Use YAML-safe frontmatter generation, not raw string interpolation for arbitrary titles/URLs.
If PyYAML is not available, implement minimal safe scalar quoting.

Target frontmatter:

```yaml
---
title: "Page title"
created: "2026-05-30T10:00:00"
updated: "2026-05-30T11:00:00"
type: source-note
source: onenote
source_notebook: "1 Projects"
source_section: "Shopping"
source_page_id: "..."
source_link: "..."
exporter: hermes-graph-onenote-md
export_status: success
asset_folder: assets
---
```

Rules:
- never include token/query auth values if encountered; redact suspicious token-like query parameters
- if fetch failed, set `export_status: failed_fetch`
- if content fetched but some assets failed, set `export_status: partial`

**Verification:**
- unit test frontmatter escapes quotes/colons/newlines safely
- sample Markdown frontmatter parses visually and does not expose secrets

---

## Task 10: Add manifest/checkpoint/resume semantics

**Objective:** Make the migration safe for long runs with Graph throttling and recoverable failures.

**Files:**
- Modify: `tmp_migrate_onenote_assets.py`

**Implementation requirements:**
Manifest entry per page:

```json
{
  "notebook": "1 Projects",
  "section": "Shopping",
  "page_id": "...",
  "title": "Shopping list",
  "level": 0,
  "order": 12,
  "path": "C:/.../Shopping list.md",
  "status": "success|partial|failed_fetch|skipped_encrypted|failed",
  "assets_expected": 2,
  "assets_downloaded": 2,
  "assets": ["C:/.../assets/shopping-list-01.png"],
  "asset_failures": [],
  "warnings": []
}
```

Resume behavior:
- load existing `_manifest.json`
- skip a page if page id has `status == success` and output file still exists, unless `FORCE = True`
- retry pages with `partial`, `failed_fetch`, or missing files
- write manifest after each page, not only at the end

**Verification:**
- fake-run test: successful page is skipped on second run
- partial page is retried
- corrupt/missing output is retried
- manifest write is valid JSON after each update

---

## Task 11: Add conservative Graph throttling settings and clearer retries

**Objective:** Keep Graph extraction reliable for large notebooks.

**Files:**
- Modify: `tmp_migrate_onenote_assets.py`

**Implementation requirements:**
Replace aggressive pauses:

```python
GRAPH_NOTEBOOK_PAUSE_SECONDS = 2
GRAPH_SECTION_PAUSE_SECONDS = 1
GRAPH_PAGE_PAUSE_SECONDS = 0.5
```

with the safer session-proven defaults, unless running explicit sample mode:

```python
GRAPH_NOTEBOOK_PAUSE_SECONDS = 30
GRAPH_SECTION_PAUSE_SECONDS = 10
GRAPH_PAGE_PAUSE_SECONDS = 3
```

Add config:

```python
SAMPLE_MODE = True
SAMPLE_PAGE_LIMIT = 10
FORCE = False
```

In sample mode, lower pauses are acceptable, but the full run must use conservative values.

Retry behavior:
- 8 attempts
- exponential backoff for 429
- max delay 180s for page/content calls
- log sanitized error type/status, not auth data

**Verification:**
- unit test retry wrapper with fake 429 then success
- sample mode is visibly limited
- full mode cannot be accidentally started without changing one explicit config value

---

## Task 12: Add verification script for the new layout

**Objective:** Verify the upgraded output in terms that matter for Obsidian.

**Files:**
- Create: `C:\Users\<user>\AppData\Local\hermes\hermes-agent\verify_onenote_graph_export.py`
- Or update existing scanner only if that is cleaner:
  `C:\Users\<user>\AppData\Local\hermes\skills\note-taking\onenote-export-verification\scripts\scan_onenote_vault.py`

Prefer creating `verify_onenote_graph_export.py` first to avoid breaking the existing scanner.

**Checks:**
- count `.md` files
- count `index.md`; target for new sample should be zero unless there is a deliberate legacy folder
- count visible `assets/` dirs
- count hidden `.assets/` dirs; target for new sample should be zero
- find Markdown image embeds
- verify every local image ref exists from the note’s folder
- verify image signature
- report remote Graph URLs still present in Markdown
- report failed/partial manifest entries

**Command:**

```bash
python C:/Users/<user>/AppData/Local/hermes/hermes-agent/verify_onenote_graph_export.py C:/Users/<user>/Documents/OneNote-Migration-Staging-Sample
```

**Expected sample pass criteria:**
- no broken local image refs
- no remote Graph image URLs
- no hidden `.assets` dirs in new sample output
- `index.md` count is 0 for new output
- image assets referenced in Markdown are real images by signature

---

## Task 13: Run a small isolated sample export

**Objective:** Prove the new exporter behavior before touching the existing staging vault.

**Files/paths:**
- New sample output root:
  `C:\Users\<user>\Documents\OneNote-Migration-Staging-Sample`
- Active script:
  `C:\Users\<user>\AppData\Local\hermes\hermes-agent\tmp_migrate_onenote_assets.py`

**Steps:**
1. Set sample destination to `OneNote-Migration-Staging-Sample`.
2. Set `SAMPLE_MODE = True` and `SAMPLE_PAGE_LIMIT = 10`.
3. Prefer a notebook/section known to contain at least one image if discoverable.
4. Run export.
5. Run verification script.
6. Inspect at least one Markdown file with an image.

**Commands:**

```bash
python C:/Users/<user>/AppData/Local/hermes/hermes-agent/tmp_migrate_onenote_assets.py
python C:/Users/<user>/AppData/Local/hermes/hermes-agent/verify_onenote_graph_export.py C:/Users/<user>/Documents/OneNote-Migration-Staging-Sample
```

**Expected:**
- sample writes real page-title `.md` files
- sample uses visible `assets/` folders only when needed
- manifest records statuses
- images in notes reference local files
- verification reports no broken local embeds

---

## Task 14: Compare the sample against current staging and decide promotion path

**Objective:** Avoid mixing old and new layouts without an explicit decision.

**Files/paths:**
- Old/current staging:
  `C:\Users\<user>\Documents\OneNote-Migration-Staging`
- New sample:
  `C:\Users\<user>\Documents\OneNote-Migration-Staging-Sample`

**Steps:**
1. Run old scanner on current staging and record counts:
   - current known baseline: `index_md_dirs: 364`, `failed_fetch_notes: 27`, `notes_with_assets: 0`, `notes_with_empty_assets: 232`
2. Run new verifier on sample.
3. Compare:
   - page path style
   - image embed style
   - asset dir style
   - manifest status quality
4. Decide one of:
   - rerun full migration into a fresh new staging folder
   - transform old staging in place only after git init/backup
   - keep old staging as reference and use new full output as canonical

**Recommendation:**
Use a fresh new full output folder after sample passes, e.g.:

```text
C:\Users\<user>\Documents\OneNote-Migration-Staging-v2
```

Do not overwrite the current staging folder during the first full run.

---

## Task 15: Initialize git only after sample output is sane

**Objective:** Make the full migration reviewable and reversible.

**Files/paths:**
- Recommended fresh full output:
  `C:\Users\<user>\Documents\OneNote-Migration-Staging-v2`

**Steps:**
1. Create fresh full output folder.
2. Initialize git there.
3. Add `.gitignore` for Obsidian workspace files and transient logs.
4. Commit initial generated migration only after verification has run.

**Commands:**

```bash
cd C:/Users/<user>/Documents/OneNote-Migration-Staging-v2
git init
printf '.obsidian/workspace*\n*.tmp\n_export.log\n' > .gitignore
git add .gitignore
git commit -m 'chore: initialize OneNote migration staging vault'
```

Then after full export and verification:

```bash
git add .
git commit -m 'import: export OneNote notes with local assets'
```

**Verification:**
- `git status --short` shows tracked generated files after add
- no credentials or token files are tracked

---

## Task 16: Full run acceptance criteria

**Objective:** Define what “done” means before execution begins.

The upgraded Python exporter is acceptable when:

1. It runs without the Word/COM publish path.
2. It writes real page-title Markdown files, not `index.md` wrappers.
3. It uses visible `assets/` folders adjacent to notes when images exist.
4. It does not create empty asset folders for image-free pages.
5. It preserves OneNote notebook/section/page metadata in frontmatter.
6. It records success/partial/failure status in `_manifest.json`.
7. It retries 429 throttling and can resume from manifest.
8. It records encrypted/unreadable/fetch-failed pages without guessing content.
9. It converts local images to Markdown embeds that point to real local files.
10. Verification reports:
    - no broken local image refs
    - no remote Graph image URLs in final Markdown
    - image files have valid signatures
    - failed pages are counted and listed
11. A manual Obsidian Reading view check confirms at least one image-heavy sample note renders inline after reload.

---

## Implementation order summary

1. Backup current script.
2. Add pure path/layout tests.
3. Implement MD Exporter-style path helpers.
4. Add collision handling.
5. Replace `index.md` output with page-title `.md` output.
6. Add Graph level/order metadata discovery and hierarchy builder.
7. Switch `.assets` to visible `assets` and avoid empty folders.
8. Preserve image embeds in Markdown.
9. Improve asset extension/signature handling.
10. Add source/frontmatter/status metadata.
11. Add manifest checkpoint/resume.
12. Add new verifier for the new layout.
13. Run isolated sample export.
14. Compare sample against current staging.
15. Only then run full migration into a fresh v2 staging vault.

---

## Notes for the implementer

- Treat `tmp_migrate_onenote_assets.py` as a migration script, not a polished package. Small internal helpers and tests are enough; do not over-engineer.
- Keep the implementation Word-free.
- Use the upstream exporter as a layout/reference model, not as a runtime dependency.
- Prefer visible `assets/` over hidden `.assets` because the user’s Obsidian verification cares about real rendering.
- Do not claim image success until Markdown reference + file existence + image signature + Obsidian Reading view have been checked.
- Do not start the full migration until the sample export passes local verification.
