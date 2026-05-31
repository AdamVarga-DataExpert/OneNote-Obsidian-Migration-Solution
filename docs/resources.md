# Resources and source artifacts

## Environment

- Host user home: `C:/Users/<user>`
- Hermes checkout: `C:/Users/<user>/AppData/Local/hermes/hermes-agent`
- Hermes Python used for verification: `C:/Users/<user>/AppData/Local/hermes/hermes-agent/venv/Scripts/python`
- OneNote auth: delegated Microsoft Graph auth is already configured on this machine.
- Graph limitation: encrypted OneNote sections are not accessible through Microsoft Graph.

## Current source/staging paths

- Current v2 staging vault: `C:/Users/<user>/Documents/OneNote-Migration-Staging-v2`
- Main manifest: `C:/Users/<user>/Documents/OneNote-Migration-Staging-v2/_manifest.json`
- Image rendering repair manifest: `C:/Users/<user>/Documents/OneNote-Migration-Staging-v2/_image_render_repair_manifest.json`
- Exporter source: `C:/Users/<user>/AppData/Local/hermes/hermes-agent/tmp_migrate_onenote_assets.py`
- Verifier source: `C:/Users/<user>/AppData/Local/hermes/hermes-agent/verify_onenote_graph_export.py`

## Historical plans copied into this repo

The `plans/` folder contains the progression of the migration design:

1. `2026-05-25_211618-onenote-to-obsidian-full-migration.md` — initial staged Graph/Obsidian/git workflow.
2. `2026-05-25_233000-proper-onenote-to-obsidian-migration.md` — stronger hierarchy and local-asset preservation plan.
3. `2026-05-27_000000-reconstruct-onenote-structure-and-verify-images.md` — repair of early Graph-derived vault structure.
4. `2026-05-27_075535-reconstruct-onenote-structure-and-verify-images.md` — OneNote MD Exporter-output reconstruction and rendering validation.
5. `2026-05-30_101900-use-alxnbl-onenote-md-exporter-for-obsidian-migration.md` — upstream exporter evaluation plan.
6. `2026-05-30_184536-adapt-python-onenote-exporter-with-md-exporter-logic.md` — final chosen plan: keep Graph extraction and adopt Obsidian-friendly OneNote MD Exporter layout logic.

## External/upstream reference

- Upstream reference considered: `alxnbl/onenote-md-exporter`.
- Useful layout settings from that tool:
  - `ProcessingOfPageHierarchy = HierarchyAsFolderTree`
  - `ResourceFolderLocation = PageParentFolder`
  - `ResourceFolderName = assets`
  - `OneNoteLinksHandling = ConvertToWikilink`
  - `AddFrontMatterHeader = true`
  - `PostProcessingMdImgRef = true`
  - `UseHtmlStyling = true`

## What is intentionally not stored here

- Raw OneNote note contents.
- OAuth tokens or client secrets.
- Full unsanitized manifests containing all page IDs and source links.
- The Obsidian staging vault itself.
