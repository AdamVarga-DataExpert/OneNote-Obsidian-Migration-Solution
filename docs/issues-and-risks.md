# Issues, blockers, and risks

## Current blockers / open issues

### 1. Graph fetch failures

Three pages are represented as failed-fetch placeholders due to Graph 504 errors:

- one project note
- two resource notes

These should be retried from the manifest. Do not reconstruct or summarize their content by guessing.

### 2. Encrypted section inaccessible through Graph

One section failed at page enumeration:

- `3 Resources / Encrypted private section`
- Error class: encrypted OneNote section is not accessible through Microsoft Graph.

This is a source/API limitation, not an exporter bug. It requires either manual OneNote export/unlock or explicit documentation as inaccessible.

### 3. Remote Graph URLs still appear in some Markdown

The latest verifier reported remote Graph URL occurrences in 10 Markdown files. Some may be source links or failed-fetch diagnostics; image URLs in successful note bodies should not remain. Review each occurrence before final acceptance.

### 4. Manifest/file reconciliation mismatch

The manifest contains 367 records and 366 path-bearing page entries, but only 315 Markdown files currently exist in the visible staging tree. Missing manifest paths are concentrated in non-PARA notebooks:

- `Primary legacy notebook`: 8
- `Additional private notebook A`: 1
- `Additional private notebook B`: 1
- `Private legacy notebook`: 41

The visible staging folder currently contains only PARA top-level folders. Decide whether non-PARA notebooks are intentionally out of final scope, need a separate vault area, or were written elsewhere/deleted. Do not call the migration globally complete until this is resolved.

### 5. Repair-count / verifier-count mismatch

The image repair manifest recorded 645 image refs, while the latest verifier sees 591 image embeds in the visible staging tree. This may be explained by manifest/path scope differences, but it should be reconciled before final acceptance.

## Known design risks

- Microsoft Graph throttling can make full runs slow; use checkpoint/resume instead of restarting from scratch.
- OneNote HTML is not full-fidelity Markdown; complex tables, drawings, ink, and attachments may need manual checks.
- Page hierarchy depends on Graph `level` and `order` metadata. Missing or odd levels are flattened with warnings.
- Image presence on disk is not enough; Obsidian rendering can still fail because of Markdown syntax or indentation.
- Do not commit token files, client secrets, raw note dumps, or sensitive notebook content to this documentation repo.

## Next recommended decisions

1. Decide whether non-PARA notebooks are in or out of migration scope.
2. Retry the three Graph 504 failed pages.
3. Review the 10 Markdown files containing Graph URLs and classify as safe metadata vs unresolved remote resource.
4. Re-run verifier after any retry/repair.
5. Manually verify several representative notes in Obsidian Reading view.
