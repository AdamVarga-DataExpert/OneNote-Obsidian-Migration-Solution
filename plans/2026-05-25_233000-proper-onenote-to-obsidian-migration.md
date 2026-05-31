# Proper OneNote-to-Obsidian Migration Plan

## Goal
Redo the OneNote migration properly so the Obsidian vault preserves the original OneNote hierarchy, including notebook/section/subpage organization, and includes local copies of images and other embedded assets.

## Current context / assumptions
- The existing `C:\Users\<user>\Documents\<vault>` vault contains an initial OneNote import, but it flattened hierarchy too aggressively and did not preserve images.
- The current vault should be treated as a draft/reference, not the final migrated structure.
- The user wants a faithful filesystem-native Obsidian migration, with local assets and preserved source metadata.
- The destination vault remains `C:\Users\<user>\Documents\<vault>` unless a better corrective layout is required during the repair pass.
- Source metadata already exists in imported notes and should continue to be preserved.
- The final output should be suitable for git-based sync.

## Proposed approach
Do a second, structural migration pass that is source-tree-first rather than title-first:
1. Reconstruct the OneNote tree from notebook -> section group -> section -> page -> subpage relationships.
2. Re-extract page bodies and all embeddable assets, especially images.
3. Write a hierarchy-preserving Obsidian layout that mirrors the OneNote tree where it matters, while still keeping PARA as the top-level organization.
4. Replace flat notes with parent/index notes plus child subpages where OneNote had nested pages.
5. Verify that every page with images has corresponding local assets and embeds.

## Step-by-step plan

### 1) Re-audit the OneNote source model
- Inspect the OneNote helper code and extraction logic currently used.
- Determine how to enumerate:
  - notebooks
  - section groups
  - sections
  - pages
  - subpages / child pages
  - images and attachments
- Identify whether the source API can directly provide page hierarchy or whether it must be reconstructed from page metadata and links.
- Produce a source manifest that records the full tree before any writing happens.

### 2) Build a staging representation of the real OneNote tree
- Create a staging folder separate from the final vault for raw exports and manifests.
- Store one manifest entry per page with:
  - notebook, section group, section
  - page id and title
  - parent page id if any
  - child page ids / subpage order if any
  - source link
  - image and attachment references
  - extraction status
- Keep raw HTML or source payloads alongside each page so the transformation can be rerun without redownloading.

### 3) Re-extract pages with local assets
- Download page content and image binaries for all pages.
- Save images into page-local asset folders, e.g. `note.assets/` or a sibling asset directory.
- Rewrite image references so the markdown points to local files only.
- Preserve alt text and image order when available.
- Record missing or inaccessible assets explicitly in the manifest.

### 4) Rebuild note structure with subpage preservation
- For pages that have subpages, preserve the nesting rather than flattening everything into one top-level note.
- Use a parent/index note for the main page when it has children, and place child pages beneath it or in a clearly linked subfolder.
- Keep PARA as the top-level organizing layer, but allow OneNote nesting inside the PARA destination.
- When one OneNote page is essentially an index with multiple child topics, keep it as an index note instead of merging its children into unrelated notes.
- Only split or merge notes when the source hierarchy and content support that decision.

### 5) Rewrite the vault carefully
- Replace or quarantine the current flattened output rather than piling a second conflicting import on top of it.
- Preserve all useful source metadata in frontmatter:
  - `type: source-note`
  - `source: onenote`
  - notebook / section / section group
  - page id
  - parent page id if applicable
  - source link
  - migration status
- Use sane filenames that reflect the actual page titles and avoid artifact filenames.
- Ensure subpages have either nested folders or explicit links from their parent note, depending on the source structure and what is most readable in Obsidian.

### 6) Validate completeness and fidelity
- Compare the final note tree against the OneNote manifest.
- Verify that:
  - all source pages are represented
  - child pages remain associated with their parents
  - images exist locally
  - image embeds resolve to real files
  - no major page groups were flattened incorrectly
- Read back a sample of rewritten notes to confirm structure and asset references.
- Track any pages that remain partial or need manual follow-up.

### 7) Git and cleanup
- Keep the repository ready for sync after the corrected migration.
- Review git status and ensure only intended files are present.
- Commit the repaired structure once validation passes.

## Files likely to change
- OneNote extraction / migration scripts under `C:\Users\<user>\AppData\Local\hermes\hermes-agent\` or `C:\Users\<user>\AppData\Local\hermes\scripts\`
- The Obsidian vault at `C:\Users\<user>\Documents\<vault>\...`
- Migration status notes inside the vault
- Staging manifest files and raw exports under a dedicated migration workspace
- `.gitignore` and git metadata if staging paths need to be excluded

## Tests / validation
- Verify the OneNote tree manifest matches the source hierarchy.
- Confirm a page with known images produces local image files and working Obsidian embeds.
- Confirm at least one page with subpages is represented as a parent/child structure rather than a flat list of unrelated notes.
- Check that no imported note is missing source metadata.
- Run a completeness pass comparing expected page count vs written page count.
- Confirm the final vault opens cleanly in Obsidian and the git repo is in a valid state.

## Risks, tradeoffs, and open questions
- OneNote subpage hierarchy may not be fully exposed by the existing extraction helper and may require a different Graph call pattern.
- Some images may be embedded in ways that require extra API handling or HTML parsing.
- There is a tradeoff between strict OneNote structural fidelity and long-term Obsidian usability.
- The best representation for subpages may differ by note family: nested folders for large trees, or parent index notes with links for lighter trees.
- The current vault already contains a partial import; the safest path may be to regenerate the corrected vault into a clean staging destination and then replace the final vault only after validation.

## Suggested execution order later
1. Inspect and understand the current OneNote helper and hierarchy exposure.
2. Generate a source manifest for notebooks, sections, pages, and subpages.
3. Re-extract a small sample that includes images and nested pages.
4. Validate the sample in Obsidian.
5. Scale the corrected migration to the full source tree.
6. Replace or reconcile the current vault contents.
7. Re-run validation and commit the corrected vault.

## Precise handoff summary
The repaired migration exists in the current `<vault>` vault and has been pushed to GitHub, but the source OneNote model still needs a final cleanup pass if perfect fidelity is required. Current state:
- The final vault is at `C:\Users\<user>\Documents\<vault>`.
- The corrected migration is committed and pushed on `main`.
- The export preserves the OneNote notebook/section/page hierarchy in nested folders.
- Embedded assets were recovered into per-page `.assets` folders.
- Asset filenames are still mostly raw OneNote resource names like `$value.bin`.
- Many of those `.bin` files are actually images; at least some are JPEGs or PNGs based on file signatures.
- The notes currently reference local asset folders, so Obsidian can access the images, but the filenames/extensions are not normalized yet.
- Encrypted OneNote sections were skipped because Microsoft Graph does not expose them.

What still needs to be done if continuing:
1. Normalize recovered asset filenames by sniffing signatures and renaming `.bin` to `.jpg`, `.png`, `.gif`, `.webp`, etc.
2. Update any note references if the asset filenames change.
3. Optionally re-scan the vault for notes whose page hierarchy still needs manual verification.
4. Decide whether encrypted sections should remain skipped or be documented separately as inaccessible.
5. If no further structural issues are found, the migration can be considered complete.
