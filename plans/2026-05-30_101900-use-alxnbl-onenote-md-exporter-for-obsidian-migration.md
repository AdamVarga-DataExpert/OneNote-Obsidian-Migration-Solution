# Use alxnbl/onenote-md-exporter for Obsidian migration

> **For Hermes:** Use subagent-driven-development to implement this plan task-by-task, with verification after each step.

**Goal:** Migrate the OneNote content using the alxnbl/onenote-md-exporter repo as the export base, so notes land in an Obsidian-friendly Markdown layout with all images exported and rendered inline correctly.

**Architecture:**
Use the upstream exporter as the primary OneNote → Markdown pipeline instead of the current custom script. Keep the export structure aligned with Obsidian expectations: page files should use real page filenames, attachments should be stored in visible resource folders, and embeds must be rewritten with correct relative paths from each note’s actual folder. Preserve the existing vault as a staging target and validate a small sample before any full export. If the upstream exporter’s defaults are not sufficient, patch the local fork minimally rather than re-inventing the export pipeline.

**Tech Stack:**
- C# / .NET / OneNote COM + Word / Pandoc
- Obsidian Markdown vault layout
- Local fork of `C:\Users\<user>\onenote-md-exporter`
- Regression verification in Obsidian Reading view

---

### Task 1: Confirm the upstream exporter’s layout and settings for Obsidian

**Objective:** Identify the exact export settings that produce Obsidian-friendly page filenames, attachment folders, and image embeds.

**Files:**
- Read: `C:\Users\<user>\onenote-md-exporter\README.md`
- Read: `C:\Users\<user>\onenote-md-exporter\src\OneNoteMdExporter\Services\Export\MdExportService.cs`
- Read: `C:\Users\<user>\onenote-md-exporter\src\OneNoteMdExporter\Models\Attachement.cs`
- Read: `C:\Users\<user>\onenote-md-exporter\src\OneNoteMdExporter\Models\Page.cs`

**Step 1: Inspect the export path logic**
- Verify how page markdown paths are built.
- Verify how attachment paths are built.
- Verify how relative markdown references are generated.

**Step 2: Map the settings to our vault needs**
- Determine the best values for:
  - `ProcessingOfPageHierarchy`
  - `ResourceFolderLocation`
  - `AddFrontMatterHeader`
  - `OneNoteLinksHandling`
  - `UseHtmlStyling`

**Step 3: Record the expected output layout**
- Notes should use page-title filenames instead of `index.md`.
- Images should live in visible resource folders, not hidden `.assets` folders.
- Image embeds should resolve from the note’s actual folder context.

**Verification:**
- A short written mapping of “setting → expected export behavior”.
- No code changes yet.

---

### Task 2: Create a tiny sample export and inspect the output layout

**Objective:** Export a small notebook/section sample with the upstream tool and check whether the output is already Obsidian-ready.

**Files:**
- Use the cloned repo under `C:\Users\<user>\onenote-md-exporter`
- Export into a disposable staging folder outside the current vault

**Step 1: Choose a minimal sample**
- Pick one notebook/section/page set that contains at least one image and one text-heavy page.

**Step 2: Run the exporter on the sample**
- Use the exporter’s documented CLI or app flow.
- Keep the sample small enough to inspect manually.

**Step 3: Inspect the generated structure**
- Confirm whether pages are written as `PageTitle.md`.
- Confirm where images are stored.
- Confirm whether image embeds are relative and valid.

**Step 4: Check for obvious Obsidian issues**
- Hidden attachment folders.
- Generic attachment naming.
- Broken paths from note location to asset location.

**Verification:**
- A generated sample tree with at least one note and one image.
- A note file whose embed target exists on disk.

---

### Task 3: Add or adjust the exporter defaults for Obsidian-friendly output

**Objective:** Patch the exporter only if the sample output is not already suitable for Obsidian.

**Files:**
- Modify: `C:\Users\<user>\onenote-md-exporter\src\OneNoteMdExporter\Services\Export\MdExportService.cs`
- Possibly modify: exporter settings or config models if needed
- Possibly add or adjust tests in `C:\Users\<user>\onenote-md-exporter\src\OneNoteMdExporter.IntTests\MarkdownExportTests.cs`

**Step 1: Write a failing test or capture the failing behavior**
- Add a regression test for the desired output layout if the repo’s test harness supports it.
- If the test harness is cumbersome, document the exact failing sample output and path issue first.

**Step 2: Implement the minimal fix**
- Prefer changes that preserve upstream behavior except for the export layout we need.
- Goals for the patch:
  - real page filenames instead of `index.md`
  - visible attachment/resource folder
  - correct relative image embeds
  - preserve all image attachments

**Step 3: Re-run the sample export**
- Confirm the new export structure matches the intended vault layout.

**Verification:**
- Sample export no longer uses the broken layout.
- At least one image embed resolves to an actual file.

---

### Task 4: Validate the exported notes in Obsidian Reading view

**Objective:** Prove that images render inline in Obsidian, not just on disk.

**Files:**
- Exported sample vault in `C:\Users\<user>\Documents\OneNote-Migration-Staging` or a fresh staging vault

**Step 1: Open representative notes in Obsidian**
- Use notes with one image and notes with multiple images.
- Check the page after reload, not only immediately after export.

**Step 2: Apply the image-render checklist**
- Confirm the embed syntax is real.
- Confirm the target exists.
- Confirm the file signature is a real image.
- Confirm Reading view shows the image inline.

**Step 3: Diagnose any failure**
- If a note fails to render, trace the relative path from the note’s real folder.
- If needed, patch the exporter and rerun the sample.

**Verification:**
- At least one representative note visibly renders its images inline in Obsidian.
- The result still holds after reopening the note.

---

### Task 5: Migrate the full OneNote export only after the sample passes

**Objective:** Run the chosen exporter on the full notebook set and replace the current custom migration output only when the sample has passed validation.

**Files:**
- Export target: `C:\Users\<user>\Documents\OneNote-Migration-Staging`
- Preserve the old export as a backup until verification completes

**Step 1: Run the full export**
- Use the validated exporter settings from earlier tasks.
- Do not overwrite the previous output until the new run is confirmed.

**Step 2: Run automated consistency checks**
- Count notes and image embeds.
- Check for missing asset targets.
- Check for obvious duplicate or generic attachment naming problems.

**Step 3: Manually spot-check representative notes**
- Include notes with one image, multiple images, and previously problematic notes.

**Step 4: Only then replace the previous migration output**
- Keep a backup copy until the new vault passes verification.

**Verification:**
- Full export succeeds.
- Representative notes render inline in Obsidian.
- No obvious broken image-path regressions remain.

---

### Task 6: Document the chosen export settings and fallback plan

**Objective:** Record the exact exporter settings and the reason we chose this path so future reruns are repeatable.

**Files:**
- Update this plan if new failure modes are discovered.
- Optionally add a short note in the migration docs or a local README.

**Step 1: Summarize the final settings**
- Which export mode to use.
- Which resource-folder layout to use.
- Which page hierarchy setting to use.

**Step 2: Document the verification method**
- Include the Obsidian Reading view check.
- Include the reload check.
- Include the image-signature check.

**Step 3: Document the fallback**
- If the exporter still misses images, patch the local fork rather than switching back to the ad hoc script.

**Verification:**
- The migration approach is repeatable without re-discovering the same issues.

---

## Acceptance Criteria
- The exporter is chosen based on an actual sample export, not just repo inspection.
- Page files use real page names rather than `index.md`.
- Images are exported into visible resource folders.
- Embeds point to the correct relative paths from each note.
- Representative notes render images inline in Obsidian Reading view.
- Rendering still works after reopening the note.
- If any image fails, the root cause is identified and the exporter is patched before acceptance.

## Non-goals
- Rewriting the exporter from scratch.
- Cleaning up unrelated note content.
- Perfect fidelity for every OneNote feature on the first pass.

## Notes
- Treat hidden `.assets` conventions as a potential failure mode, not a success signal.
- Keep a backup of the current migration output until the new pipeline is verified.
- If the upstream repo already satisfies the requirements, prefer configuration over code changes.
