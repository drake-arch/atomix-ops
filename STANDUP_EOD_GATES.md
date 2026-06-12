# Atomix EOD → Standup Hard Gates

These gates exist because two failures happened:

1. 4 PM custom questions were saved to archive but not published to the live EOD intake site.
2. Standup comics passed data/ZIP checks while using rejected card/icon fallback art.

## Gate A — 4 PM custom questions are not done until live

A dated file is only the draft source. The team-facing EOD intake site is the operational truth.

Required sequence after final person is captured:

1. Confirm the dated file exists:
   `/home/fabric041/work/atomix-ops/standup_archive/YYYY-MM-DD/eod_questions_YYYY-MM-DD.md`
2. Publish questions into the EOD intake site:
   ```bash
   python3 /home/fabric041/work/atomix-ops/publish_eod_questions_to_site.py \
     /home/fabric041/work/atomix-ops/standup_archive/YYYY-MM-DD/eod_questions_YYYY-MM-DD.md
   ```
3. Run JS syntax check on the EOD intake HTML.
4. Browser-test locally: start report → enter test name/date → open at least one custom EOD person → confirm exact question text appears.
5. Commit/push the EOD intake site update.
6. Open live GitHub Pages URL with cache busting and verify the exact question text appears.
7. Only then say: “questions are live for the team.”

## Gate B — morning standup deck question integrity

Before building the morning deck:

1. Read prior-day `eod_questions_YYYY-MM-DD.md`.
2. Pull Sheet answers for that same date.
3. Compare expected custom question text against submitted answer question text.
4. If the custom questions are missing from Sheet answers, report the mismatch plainly instead of building a misleading recap.

## Gate C — comic quality

Before delivering any downloadable standup ZIP:

1. Load `atomix-comic`, `atomix-design-system`, and `comic-quality-gates`.
2. Inspect the actual packaged HTML/ZIP, not just source files.
3. For every submitted person, comics must be real generated raster comic art — not SVG/card/icon/person placeholders.
4. Complex EODs may expand beyond one 3-panel strip. Use multiple comic pages/slides inside the same person section when needed.
5. Run:
   ```bash
   python3 /home/fabric041/work/atomix-ops/standup_comic_gate.py /path/to/CLICK_TO_OPEN_*.html
   ```
6. Browser-check at least one submitted-person comic after scrolling it into view.
7. Verify ZIP is small enough to attach/download.

## Final handoff wording requirement

When handing off, explicitly state:

- EOD questions live-verified: yes/no
- JS syntax check: pass/fail
- Comic gate: pass/fail
- Browser visual check: which person checked
- ZIP size

No vague “done.”
