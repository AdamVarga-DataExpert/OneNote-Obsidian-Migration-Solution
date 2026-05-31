# Runbook

## 1. Prepare

Work from the Hermes Agent checkout because the exporter imports Hermes OneNote/Graph helper modules.

```bash
cd /c/Users/<user>/AppData/Local/hermes/hermes-agent
```

Use the Hermes venv Python when available:

```bash
PY=/c/Users/<user>/AppData/Local/hermes/hermes-agent/venv/Scripts/python
```

## 2. Sample export first

Keep `SAMPLE_MODE = True` and `SAMPLE_PAGE_LIMIT` small in `tmp_migrate_onenote_assets.py`.

```bash
"$PY" tmp_migrate_onenote_assets.py
"$PY" verify_onenote_graph_export.py /c/Users/<user>/Documents/OneNote-Migration-Staging-Sample
```

A sample is acceptable only if:

- no `index.md` wrappers are generated;
- hidden `.assets` folders are not generated;
- Markdown image embeds point to local assets;
- no broken local refs exist;
- no Graph image URLs remain in successful notes;
- failures are explicit in the manifest.

## 3. Full export

Only after sample verification passes, switch the exporter to full destination:

```python
SAMPLE_MODE = False
DEST_ROOT = FULL_DEST_ROOT  # C:/Users/<user>/Documents/OneNote-Migration-Staging-v2
```

Run as a tracked process because Graph can be slow and throttle:

```bash
"$PY" tmp_migrate_onenote_assets.py
```

Monitor `_manifest.json` rather than relying on chatty stdout.

## 4. Verify full output

```bash
"$PY" verify_onenote_graph_export.py /c/Users/<user>/Documents/OneNote-Migration-Staging-v2
```

Expected hard gates:

- `index_md_count == 0`
- `hidden_assets_dirs == 0`
- `broken_local_refs == []`
- `invalid_signatures_for_referenced_images == []`
- `render_blocking_image_refs_count == 0`

Remaining remote Graph URLs or failed manifest entries require review. Do not silently treat them as success.

## 5. Repair image rendering syntax if needed

Use `scripts/repair_markdown_image_rendering.py` from this repo or equivalent logic to remove leading OneNote indentation before Markdown image embeds and collapse multiline alt text.

```bash
python scripts/repair_markdown_image_rendering.py /c/Users/<user>/Documents/OneNote-Migration-Staging-v2
```

Then run the verifier again.

## 6. Audit source-link preservation

After image/layout verification passes, compare the migrated Markdown links with
live OneNote HTML anchors. This catches cases where the visible text migrated but
the actual URL was lost.

```bash
python scripts/audit_onenote_links.py /path/to/migrated-vault \
  --auth-json /path/to/private/microsoft-graph-token.json
```

The audit writes reports under `<vault>/_audit/` by default. Those reports can
contain private note titles, relative paths, OneNote page IDs, and source URLs;
do not commit them to a public repository.

Hard expectations:

- `fetch_errors == 0`, unless throttled/encrypted/inaccessible pages are explicitly documented;
- `notes_with_missing_external_links == 0` after repair;
- URL query strings are preserved because they can contain YouTube IDs, timestamps, and other meaningful source details.

## 7. Repair missing source links if needed

If the audit finds missing or partial external links, repair from the audit JSON:

```bash
python scripts/repair_missing_onenote_links.py /path/to/migrated-vault
python scripts/audit_onenote_links.py /path/to/migrated-vault \
  --auth-json /path/to/private/microsoft-graph-token.json \
  --report-stem onenote-link-verification-after-repair
```

The repair script backs up changed notes outside the vault by default, restores
links inline when the original anchor context is clear, and otherwise adds a
`## Source links` section.

## 8. Manual Obsidian check

Open representative notes in Obsidian Reading view, especially:

- one image-heavy note, e.g. `Map ideas.md`;
- one multi-image note;
- one text-only note;
- one page with restored source links;
- one failed-fetch placeholder note.

Acceptance requires the image to display inline after reload, not only the asset existing on disk. Source links must remain clickable in Reading view.

## 9. Promote or sync

Only promote into the final Obsidian vault or commit to a sync repo after automated verification, source-link audit, and representative Obsidian rendering checks pass.
