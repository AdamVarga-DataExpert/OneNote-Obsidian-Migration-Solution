# Reconstruct OneNote structure from Graph export and verify image embeds

## Goal

Restore the OneNote-derived Obsidian vault structure from the downloaded Graph export so that:

- each OneNote page is represented cleanly in the vault
- the intended OneNote hierarchy is preserved as much as possible
- image assets are stored locally and verified to render correctly in Obsidian
- no duplicate folder/file naming pattern remains unless it is explicitly needed for a subpage structure

## Current context / assumptions

- The vault lives at `C:\Users\<user>\Documents\<vault>`.
- The OneNote export was previously downloaded from Microsoft Graph and partially transformed.
- Some pages were renamed to title-based `.md` files.
- Some page folders still exist alongside same-named markdown notes, which can create unnecessary duplication.
- Assets exist locally in `.assets` folders, but image handling still needs a final decision and validation pass.
- A few notes may be malformed or incomplete because of earlier restructuring; the safest approach is to verify by inspection before changing anything else.

## Proposed approach

1. Re-establish the intended page model.
   - Treat the markdown file as the primary page note.
   - Keep folders only when they are needed to represent real child pages/subpages or to hold local assets.
   - Avoid keeping a redundant same-named folder + same-named file for a single page unless that folder is doing real work.

2. Reconstruct hierarchy from the downloaded Graph export.
   - Use the downloaded OneNote/Graph-derived files as the source of truth.
   - Identify sections, pages, and genuine subpages.
   - Ensure that subpages remain nested or linked in a way that mirrors the source structure.

3. Resolve the duplicate naming pattern.
   - For pages that are currently represented by both a folder and a same-named note, choose one canonical representation.
   - Prefer the note file as the canonical page representation.
   - Remove the redundant folder only after confirming whether it contains:
     - child page notes
     - assets that need to stay local
     - other non-page content

4. Decide and standardize image handling.
   - Confirm whether recovered images should stay in sibling `.assets` folders next to the note.
   - Normalize filenames where needed so that local embeds point to real files.
   - Keep note links consistent with the chosen asset layout.

5. Verify rendering in Obsidian.
   - Check that the note body contains valid local image embeds.
   - Confirm that the target asset files exist on disk.
   - If possible, verify in Obsidian Reading view or Live Preview rather than only source mode.
   - Spot-check pages with known images and pages with no images.

## Step-by-step plan

### Phase 1: Inventory and safety check
- Inspect the current vault tree for:
  - duplicate page-folder + same-named file patterns
  - folders that still contain child notes
  - folders that only contain assets
  - notes that are missing or appear broken
- Identify a small set of representative problem areas, especially `Maps A Globe Co`, before changing anything else.
- Record the number of pages/folders/assets that need cleanup.

### Phase 2: Restore the intended structure
- For each page folder:
  - determine whether it is a true parent folder for subpages or only a redundant wrapper
  - keep the folder only if it has real child notes or other necessary structure
  - otherwise flatten the page note up one level and remove the redundant folder if empty
- Preserve actual subpage structure where it exists.
- Do not flatten genuine child pages into unrelated notes.

### Phase 3: Image asset strategy
- Inspect `.assets` folders and collect all asset filenames.
- Determine whether any recovered assets still use raw OneNote-style names such as `$value.bin`.
- Decide whether to:
  - keep asset filenames as-is and only fix links, or
  - normalize file extensions by content sniffing and then update note references.
- Apply one consistent convention vault-wide.

### Phase 4: Link and embed repair
- Update note embeds only when file names or locations change.
- Ensure local image embeds point to the correct relative `.assets` path.
- Re-scan notes for broken image paths after any move/rename.

### Phase 5: Validation
- Verify there are no unintended missing notes after the structure pass.
- Verify key notes open correctly in Obsidian.
- Verify that image files exist and render inline where expected.
- Check for leftover duplicate naming patterns.
- Spot-check a few sections across the vault, not just one example.

## Files likely to change

- `C:\Users\<user>\Documents\<vault>\...` vault markdown notes
- `C:\Users\<user>\Documents\<vault>\...\.assets\...` image assets
- possibly `.obsidian/workspace.json` only if view-state changes are needed for validation

## Tests / validation

- Count remaining same-named page-folder + file patterns.
- Count remaining broken image links.
- Confirm target files exist for every local embed.
- Open sample notes in Obsidian and verify images display.
- Check representative sections for preserved hierarchy.
- Confirm no note disappeared during folder cleanup.

## Risks / tradeoffs

- Moving files too aggressively can make notes appear missing if links or view state still point at old paths.
- Deleting folders before checking for child notes can destroy hierarchy.
- Renaming assets without updating embeds can break image display.
- Some Graph-exported content may be incomplete or encrypted and should remain documented as unavailable rather than guessed.

## Open questions

- Should the final asset policy be:
  - local sibling `.assets` folders with normalized filenames, or
  - a more centralized asset layout?
- Should empty parent folders remain in place if they are useful for visual grouping, or should they be removed whenever possible?
- For pages like `Maps A Globe Co`, should the structure be reconstructed strictly from the export, or should it be simplified where the export is too noisy?
