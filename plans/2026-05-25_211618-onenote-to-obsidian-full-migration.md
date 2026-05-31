# Goal
Plan a full OneNote-to-Obsidian migration workflow that:
- downloads all OneNote content into a local staging folder
- preserves page structure, source metadata, and images
- transforms content into logical PARA-aligned Obsidian markdown notes
- stores images locally in vault asset folders
- initializes/prepares the resulting vault as a git repository for later sync

# Current context / assumptions
- A working OneNote Graph auth setup already exists on this machine.
- There is already an extraction script used for OneNote content recovery:
  - `C:\Users\<user>\AppData\Local\hermes\hermes-agent\tmp_migrate_onenote.py`
- The user wants a durable, filesystem-first result in Obsidian, not a mirrored OneNote dump.
- The migration should preserve source metadata and avoid guessing content that cannot be recovered.
- Images should be stored locally, not left as remote Graph links.
- The final state should be a git repo ready for sync.

# Proposed approach
Use a staged pipeline with four layers:
1. raw extraction from OneNote Graph into a local staging tree
2. parsing and normalization into structured intermediate records
3. PARA-aware content shaping into Obsidian markdown notes
4. verification and git repo setup

This keeps extraction reproducible and makes it easier to re-run transformations without re-downloading everything.

# Step-by-step plan

## 1) Inventory the source and define the staging layout
- Enumerate notebooks, sections, pages, and page resources via Microsoft Graph.
- Create a local staging root such as:
  - `C:\Users\<user>\Documents\OneNote-Migration\raw\`
  - `C:\Users\<user>\Documents\OneNote-Migration\normalized\`
  - `C:\Users\<user>\Documents\OneNote-Migration\logs\`
- Decide a stable ID scheme for each page and asset, based on OneNote page id plus a sanitized title slug.
- Define a manifest format (JSON or YAML) for each page with:
  - notebook, section, page id, title, web link
  - extraction timestamp
  - asset list
  - transform status
  - destination note path

## 2) Build or adapt the OneNote downloader
- Use the existing Graph auth and OneNote helper code as the source of truth.
- Download each page as HTML plus metadata.
- Download referenced images and attachments into page-local asset folders.
- Save raw artifacts separately from transformed markdown so the pipeline can be re-run safely.
- Record failures explicitly rather than skipping them silently.
- Add throttling/backoff around Graph calls to avoid 429s.

Likely source files:
- `C:\Users\<user>\AppData\Local\hermes\hermes-agent\tmp_migrate_onenote.py`
- `C:\Users\<user>\AppData\Local\hermes\hermes-agent\tools\onenote_tool.py`
- any Graph helper modules those scripts import

## 3) Parse OneNote HTML into structured intermediate data
- Convert HTML into a normalized internal representation rather than directly into final markdown.
- Capture:
  - headings
  - paragraphs
  - lists and nesting
  - tables
  - links
  - images and their alt text / source refs
  - embedded file references when available
- Preserve source ordering and section boundaries.
- Keep a “raw text fallback” for pages that do not parse cleanly.

## 4) Map content into PARA and Obsidian note structure
- Use existing PARA folders as the destination base.
- Route notes by semantics:
  - Projects → active outcomes and deliverables
  - Areas → ongoing responsibilities and life domains
  - Resources → reference material and evergreen knowledge
  - Archive → closed/completed items
- Prefer existing notes when a matching home already exists.
- Split mixed pages when a single OneNote page contains multiple distinct topics.
- Merge duplicate pages where the recovered content clearly overlaps.
- Preserve or add source metadata in frontmatter:
  - `type: source-note`
  - `source: onenote`
  - source notebook/section/page id/link
  - transform status
  - original title
- Mark incomplete recoveries explicitly as partial rather than pretending completeness.

## 5) Write Obsidian markdown files with local assets
- Write one markdown file per final note.
- Use frontmatter for traceability and status.
- Use relative embeds to local assets, for example:
  - `![[note.assets/image-1.png]]` or a sibling asset folder convention
- Copy images into a durable local path under the note’s asset folder.
- Ensure filenames are sanitized for Windows and Obsidian compatibility.
- Keep links between notes as wikilinks where appropriate.

## 6) Validation and completeness checks
- Verify every written note by reading it back after creation.
- Confirm that:
  - markdown is syntactically valid
  - titles are sane and do not contain artifact filenames
  - source metadata is present
  - images exist locally and embeds point to existing files
  - no notes were accidentally flattened into generic summaries
- Produce audit reports for:
  - pages downloaded
  - pages transformed successfully
  - pages partially recovered
  - pages that failed and need manual review

## 7) Git repository preparation
- Initialize the destination vault as a git repository if it is not already one.
- Add a sensible `.gitignore` for cache, logs, and transient staging folders.
- Confirm the repo status is clean after the migration pass.
- If the vault is already a git repo, verify remotes and branch state before committing any changes.
- Decide whether to keep staging folders inside or outside the repo; likely outside the repo for large raw downloads.

## 8) Sync-ready cleanup
- Normalize filenames and folder names for stable sync.
- Remove or quarantine broken artifacts separately from the final vault.
- Leave the vault in a state where future sync can happen without needing additional cleanup.

# Files likely to change
Likely new or changed files include:
- OneNote extraction / migration script(s) under `C:\Users\<user>\AppData\Local\hermes\hermes-agent\` or `C:\Users\<user>\AppData\Local\hermes\scripts\`
- OneNote auth or helper modules if asset download support is missing
- the Obsidian vault contents under `C:\Users\<user>\Documents\PARA_PERSONAL\...`
- migration status notes in the vault
- `.gitignore` and git metadata in the vault root if needed
- staging manifests and logs under a dedicated migration workspace

# Tests / validation
- Re-run the downloader against a small notebook/section first.
- Compare a sample page in OneNote against the generated markdown.
- Verify a page with images downloads local assets and embeds them correctly.
- Check that a mixed-content page is split into sensible PARA destinations.
- Re-scan the vault for partial-import markers and broken filename artifacts.
- Confirm `git status` is clean or only contains intended migration changes.

# Risks, tradeoffs, and open questions
- Graph throttling may slow the migration substantially.
- Some OneNote pages may contain content that cannot be fully recovered from Graph.
- Images or attachments may require additional API calls or special handling.
- Mixed-topic pages require judgment for split vs merge vs preserve-as-is.
- There is a tradeoff between preserving the exact OneNote structure and making the Obsidian vault more useful long-term.
- Need to decide whether the “download whole OneNote content” stage should include every notebook/page or only the notebooks in scope for the PARA vault.
- Need to decide whether git repo setup should happen inside the vault root or in a parent workspace repo.

# Suggested execution order later
1. Confirm the vault root and a separate staging root.
2. Audit the current OneNote helper scripts for page HTML and image download support.
3. Implement/download a small pilot notebook/section.
4. Transform the pilot into Obsidian markdown with local assets.
5. Validate the result manually.
6. Scale to the full OneNote set.
7. Normalize the vault and initialize/check git sync readiness.
