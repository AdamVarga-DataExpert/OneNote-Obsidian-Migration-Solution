# Reconstruct OneNote structure from OneNote MD Exporter output and verify image embeds

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Rebuild the OneNote-derived Obsidian vault from OneNote MD Exporter output so the hierarchy, subpages, and embedded images match the exported source as closely as possible.

**Architecture:** Use OneNote MD Exporter as the canonical source of truth for page structure and asset paths, then reconcile the exported markdown into the vault with targeted repairs for misplaced pages, duplicate folder/note pairs, and broken image embeds. Validate by comparing exporter output, filesystem layout, and Obsidian rendering so we only preserve structures the exporter actually produced.

**Tech Stack:** OneNote MD Exporter, Obsidian vault files, local filesystem, markdown, image asset verification, Obsidian rendering checks.

---

## Current context / assumptions
- The working vault is `C:\Users\<user>\Documents\<vault>`.
- The source material should now be treated as OneNote MD Exporter output rather than a raw Microsoft Graph download.
- OneNote MD Exporter is the authoritative basis for page ordering, folder nesting, subpage handling, and asset placement.
- The vault already contains many migrated notes, folders, and local asset folders.
- Some pages may currently be represented in a way that looks correct in the filesystem but is wrong in Obsidian, especially where folders, empty pages, and same-named note/folder pairs are involved.
- Some recovered assets may still have raw OneNote names or ambiguous extensions, so image verification must be content-based rather than filename-based.
- The safest path is to inspect the exporter output first, then verify, and only then restructure or rename.

## Proposed approach
1. Rebuild the intended page model from OneNote MD Exporter output.
   - Treat the exporter-generated markdown as the canonical page where possible.
   - Preserve real subpages as nested structure only when they exist in the exporter hierarchy.
   - Avoid leaving a note that exists only as an empty page placeholder.

2. Identify structural outliers.
   - Look for pages that are broken, empty, duplicated, or split across a folder and a note.
   - Pay special attention to `Map A Globe` and similar cases where the visible vault layout may hide a bad reconstruction.
   - Separate genuine parent pages from accidental wrapper folders.

3. Verify image embed reality, not just file presence.
   - Scan exporter-generated markdown for local image embed syntax.
   - Confirm the referenced asset files exist on disk.
   - Verify the asset bytes match an image format by signature, not by extension alone.
   - Determine whether images are truly embedded in the note content or only present as loose files.

4. Validate display behavior in Obsidian.
   - Check notes in a way that approximates how Obsidian renders them.
   - Use screenshots or view inspection when needed to confirm the image is visible in the page, not merely referenced.
   - Spot-check notes with known images and notes that should have no images.

5. Repair image problems.
   - Fix broken embed paths.
   - Rename or normalize asset files if that is required for reliable rendering.
   - Update note references after any asset rename or move.
   - Re-scan after each fix to make sure the repair did not introduce new broken links.

## Step-by-step plan
### Phase 1: Inventory and diagnosis
- Enumerate the suspicious pages and folders in the vault.
- Identify pages with empty content, duplicate structures, or folder/file collisions.
- List notes with image embeds and notes that should contain images but do not.
- Record the current set of broken or ambiguous cases before making changes.
- Capture the corresponding OneNote MD Exporter output paths so each issue can be traced back to source export data.

### Phase 2: Structural reconstruction
- Reconstruct page hierarchy from the OneNote MD Exporter output.
- Restore real subpage relationships where they exist.
- Flatten or remove accidental wrapper folders only when they do not contain meaningful child notes or required assets.
- Ensure that page names, folder names, and note placement reflect the exporter structure as closely as possible.

### Phase 3: Image verification
- For each image-bearing note, verify three things:
  1. the embed exists in the markdown
  2. the referenced asset exists locally
  3. the asset is actually an image by file signature
- Create a small verification set of representative notes, including at least one known problem page such as `Map A Globe`.
- Distinguish between:
  - image file exists but not referenced
  - image referenced but file missing
  - image referenced correctly but rendering still fails
  - image embedded and rendering correctly

### Phase 4: Repair
- Fix broken embed targets.
- Normalize filenames or extensions only if needed for consistent rendering.
- Update note links after any rename/move.
- Preserve relative paths so Obsidian continues to resolve local embeds.
- If the exporter generates a more correct hierarchy than the current vault, prefer aligning the vault to the exporter rather than preserving legacy manual rearrangements.

### Phase 5: Re-validation
- Re-scan the vault after each repair pass.
- Confirm that previously broken pages now open with the expected structure.
- Confirm that embedded images render correctly in Obsidian view.
- Check that no unintended blank pages or orphaned folders were created.
- Reconcile the final vault state against the OneNote MD Exporter output one last time.

## Files likely to change
- `C:\Users\<user>\Documents\<vault>\**\*.md`
- `C:\Users\<user>\Documents\<vault>\**\.assets\*`
- possibly `C:\Users\<user>\Documents\<vault>\.obsidian\workspace.json` if a saved view is needed for validation

## Validation / success criteria
- `Map A Globe` and similar problem pages no longer appear as broken or empty shell pages.
- The page hierarchy matches the OneNote MD Exporter structure as closely as the export allows.
- Every intended local image embed resolves to an existing image file.
- The images render visibly in Obsidian, not just as source text or loose files.
- A post-fix scan shows no newly introduced broken local image links.

## Risks / tradeoffs
- Renaming assets can break links if embeds are not updated in the same pass.
- Removing wrapper folders too early can destroy genuine child-page structure.
- Some OneNote content may be incomplete, encrypted, or missing from the exporter and should be documented rather than guessed.
- Visual verification can miss edge cases if only one or two notes are checked, so multiple representative samples are needed.

## Open questions
- Should asset normalization be required everywhere, or only where it improves correctness and display reliability?
- Should empty page shells be preserved as placeholders, or removed when they contain no meaningful content?
- For ambiguous cases like `Map A Globe`, should source fidelity win over a cleaner simplified vault layout?
