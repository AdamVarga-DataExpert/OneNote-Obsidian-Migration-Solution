# Verification

## Automated command

From the Hermes checkout:

```bash
cd /c/Users/<user>/AppData/Local/hermes/hermes-agent
PY=/c/Users/<user>/AppData/Local/hermes/hermes-agent/venv/Scripts/python
"$PY" verify_onenote_graph_export.py /c/Users/<user>/Documents/OneNote-Migration-Staging-v2
```

## Hard pass criteria

The following must be true before promotion:

- `index_md_count == 0`
- `hidden_assets_dirs == 0`
- `broken_local_refs == []`
- `invalid_signatures_for_referenced_images == []`
- `render_blocking_image_refs_count == 0`

## Review-required criteria

These can be non-zero only if explicitly documented:

- `manifest_failed_or_partial_count`
- `remote_graph_urls`
- manifest entries for encrypted sections
- manifest paths that do not exist on disk

## Manual Obsidian Reading view checklist

For each representative note:

1. Open the note in Obsidian.
2. Switch to Reading view.
3. Reload or reopen the note.
4. Confirm images render inline, not as source text.
5. Confirm the note title and hierarchy make sense.
6. Confirm source metadata is present but not disruptive.
7. Confirm failed/inaccessible pages are visibly marked as failed, not silently blank.

## Representative notes to keep checking

- `1 Projects/Maps A Globe Co/Map ideas.md` — known image-rendering case.
- One image-heavy page from `Decoration P2`.
- One text-only page.
- One failed-fetch placeholder.
- One page with nested/subpage structure, if present.
