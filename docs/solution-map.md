# Solution map

## Goal

Import OneNote notes into an Obsidian-friendly filesystem vault while preserving hierarchy, images, source metadata, and explicit failure records.

## Chosen architecture

```text
OneNote notebooks
  -> Microsoft Graph delegated API
  -> Graph page metadata: notebook, section, page id, title, level, order, timestamps, links
  -> Graph page HTML
  -> Graph image/resource downloads
  -> Markdown transform
  -> Obsidian staging tree
  -> verifier + manual Obsidian Reading view checks
```

## Why this path was chosen

The upstream desktop `onenote-md-exporter` was useful as a layout reference, but the local OneNote/Word publish path was unreliable. Multiple publish targets failed before Markdown conversion. The working path therefore uses Microsoft Graph directly and borrows the upstream exporter’s Obsidian-friendly output conventions.

## Output mapping

### Notebook and section mapping

```text
OneNote notebook name -> top-level folder
OneNote section name  -> folder under notebook
OneNote page title    -> real Markdown filename, e.g. Page title.md
OneNote subpage       -> nested folder structure when Graph level/order supports it
Images/resources      -> visible sibling assets/ folder beside the note
```

Example:

```text
OneNote:
  1 Projects / Maps A Globe Co / Map ideas

Obsidian staging:
  1 Projects/Maps A Globe Co/Map ideas.md
  1 Projects/Maps A Globe Co/assets/map-ideas-01.jpg
```

## Markdown conventions

- Real page-title Markdown files, not `index.md` wrappers.
- Visible `assets/` folders, not hidden `.assets/` folders.
- Local relative Markdown embeds:

```markdown
![image](assets/example-01.jpg)
```

- YAML frontmatter preserves source traceability:

```yaml
---
title: "Page title"
created: "..."
updated: "..."
type: "source-note"
source: "onenote"
source_notebook: "1 Projects"
source_section: "Maps A Globe Co"
source_page_id: "..."
source_link: "..."
exporter: "hermes-graph-onenote-md"
export_status: "success"
asset_folder: "assets"
---
```

## Manifest model

Each page gets an entry in `_manifest.json` with at least:

- notebook
- section
- page_id
- title
- path
- status: `success`, `partial`, `failed_fetch`, `failed_section_pages`, or `failed`
- warnings
- assets_expected
- assets_downloaded
- asset_failures

The manifest is also the resume/checkpoint file. Successful pages with existing output can be skipped; failed or missing pages can be retried.

## Verification model

A page with images is not accepted until all layers pass:

1. Markdown image reference exists.
2. The image reference is syntactically renderable; it is not code-blocked by indentation and the alt text is not split across lines.
3. The referenced local file exists from the note’s real folder.
4. The bytes match a real image signature.
5. Obsidian Reading view shows the image inline after reload for representative samples.

## Current known output scope

The latest verified staging folder is PARA-shaped at the filesystem level:

- `1 Projects`
- `2 Areas`
- `3 Resources`
- `4 Archive`

The manifest also records other notebooks discovered during Graph enumeration. Some manifest paths for non-PARA notebooks currently do not exist in the visible staging tree; treat that as a reconciliation issue before declaring total completeness.
