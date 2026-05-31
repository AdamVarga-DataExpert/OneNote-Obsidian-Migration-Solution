# OneNote → Obsidian Migration Solution

This repository documents the current working solution for extracting OneNote notes into an Obsidian-friendly vault, including the reasoning, plans, scripts, status, and known blockers.

It is intentionally a documentation and handoff project, not a dump of the notes themselves. Raw note content, Microsoft auth files, client secrets, and full manifests with page IDs should stay outside this repo unless explicitly needed and reviewed.

## Current canonical staging output

- Staging vault: `C:/Users/<user>/Documents/OneNote-Migration-Staging-v2`
- Exporter reference script: `scripts/reference_hermes_graph_exporter.py`
- Verifier script: `scripts/verify_onenote_graph_export.py`
- Status report: `reports/current-state-2026-05-30.json`

## Solution in one paragraph

The reliable path is a Word-free Microsoft Graph exporter run from the Hermes Agent checkout. It enumerates OneNote notebooks and sections, fetches page HTML through Graph, reconstructs page order and subpage hierarchy from Graph `level` / `order` metadata, writes real page-title Markdown files into a PARA-style Obsidian staging tree, downloads OneNote image resources into visible sibling `assets/` folders, rewrites image tags to local relative Markdown embeds, records per-page status in `_manifest.json`, and verifies the result with local path, image-signature, and render-blocking Markdown checks.

## Repository map

- `docs/resources.md` — tools, paths, credentials assumptions, source artifacts.
- `docs/solution-map.md` — architecture and data flow from OneNote to Obsidian.
- `docs/runbook.md` — repeatable operating procedure.
- `docs/progress.md` — current progress and verification numbers.
- `docs/issues-and-risks.md` — known failures, limitations, and next decisions.
- `docs/verification.md` — acceptance checks and commands.
- `plans/` — copied historical implementation plans in chronological order.
- `scripts/` — reference exporter/verifier/repair scripts.
- `reports/` — sanitized generated state summaries.

## Important safety rule

Do not treat a file existing on disk as proof of a successful migration. A note is only considered acceptable when:

1. the Markdown note exists;
2. frontmatter preserves OneNote source metadata;
3. every intended image has a local Markdown reference;
4. every local image reference resolves from the note folder;
5. the target bytes are a real image format;
6. the image Markdown is renderable in Obsidian, not indented as a code block;
7. missing, encrypted, throttled, or failed pages are documented rather than guessed.

## Latest known status

At project creation, the v2 staging export has a mostly successful Graph export with local assets and a repaired image-rendering issue. Remaining blockers are documented in `docs/issues-and-risks.md` and summarized in `reports/current-state-2026-05-30.json`.
