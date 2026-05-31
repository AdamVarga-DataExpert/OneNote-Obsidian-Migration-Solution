# Progress log

## Completed

- Microsoft Graph delegated OneNote access is available on the machine.
- Earlier flattened/imported vault attempts were analyzed and treated as drafts/reference material.
- The upstream `alxnbl/onenote-md-exporter` approach was investigated for Obsidian-friendly conventions.
- The desktop OneNote/Word publish path was rejected as the primary runtime path after publish failures.
- A Word-free Graph-based Python exporter was adapted to use OneNote MD Exporter-style layout logic.
- The exporter now uses:
  - page-title `.md` files rather than `index.md` wrappers;
  - visible `assets/` folders;
  - local relative Markdown image embeds;
  - Graph `level` / `order` metadata for hierarchy when available;
  - manifest checkpoint/resume status;
  - throttling/backoff for Graph requests;
  - token-like URL query redaction in links/errors.
- A verifier script was created for Obsidian-relevant checks.
- A full v2 staging export was created at `C:/Users/<user>/Documents/OneNote-Migration-Staging-v2`.
- A rendering issue was found and repaired: OneNote indentation tabs before Markdown image lines made images render as code blocks in Obsidian.
- The exporter was patched to avoid recreating the image indentation/multiline-alt problem in future runs.
- The verifier was patched to catch render-blocking Markdown image refs.

## Latest measured state at project creation

From `reports/current-state-2026-05-30.json`:

- Manifest records: 367
- Manifest status counts:
  - success: 363
  - failed_fetch: 3
  - failed_section_pages: 1
- Pages with asset metadata: 133
- Manifest asset failure count: 0
- Filesystem scan in visible staging tree:
  - markdown files: 315
  - image files by extension: 596
  - top-level Markdown folders: `1 Projects`, `2 Areas`, `3 Resources`, `4 Archive`
- Latest verifier summary:
  - markdown_count: 315
  - index_md_count: 0
  - visible_assets_dirs: 25
  - hidden_assets_dirs: 0
  - markdown_image_embeds: 591
  - render_blocking_image_refs_count: 0
  - broken_local_refs: 0
  - invalid_signatures_for_referenced_images: 0
  - manifest_failed_or_partial_count: 4

## Image-render repair result

From `_image_render_repair_manifest.json`:

- Changed files: 133
- Before:
  - files_with_images: 133
  - refs: 645
  - indented: 643
  - multiline_alt: 129
- After:
  - files_with_images: 133
  - refs: 645
  - indented: 0
  - multiline_alt: 0

Note: the latest verifier currently sees 591 Markdown image embeds in the visible staging tree. The repair manifest counted 645 refs when it was generated. Treat this difference as something to reconcile before final completeness claims.
