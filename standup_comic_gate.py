#!/usr/bin/env python3
"""Atomix standup comic pre-download gate.

Fails if submitted-person comics in a packaged standup HTML are SVG/card fallbacks
instead of real raster production comic assets.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import re
import sys
from pathlib import Path

from PIL import Image

SCRIPT_RE = re.compile(r"<script id=['\"]deck-data['\"] type=['\"]application/json['\"]>(.*?)</script>", re.S)


def load_deck(path: Path) -> dict:
    html = path.read_text(errors="ignore")
    match = SCRIPT_RE.search(html)
    if not match:
        raise SystemExit(f"FAIL: deck-data script not found in {path}")
    return json.loads(match.group(1))


def image_from_data_url(data_url: str) -> tuple[str, Image.Image, int]:
    if not data_url.startswith("data:image/"):
        raise ValueError("comic is not a data:image URL")
    header, b64 = data_url.split(",", 1)
    mime = header.split(";", 1)[0].replace("data:", "")
    if mime in {"image/svg+xml", "image/svg"}:
        raise ValueError("SVG fallback detected")
    raw = base64.b64decode(b64)
    im = Image.open(io.BytesIO(raw))
    im.load()
    return mime, im, len(raw)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("html", type=Path)
    ap.add_argument("--min-width", type=int, default=900)
    ap.add_argument("--min-height", type=int, default=550)
    args = ap.parse_args()

    deck = load_deck(args.html)
    failures: list[str] = []
    checked = 0
    for slide in deck.get("slides", []):
        if slide.get("type") != "person" or not slide.get("submitted"):
            continue
        pid = slide.get("pid") or slide.get("title") or "unknown"
        comic = slide.get("comic") or ""
        try:
            mime, im, raw_size = image_from_data_url(comic)
        except Exception as exc:  # noqa: BLE001 - gate should report any decode failure
            failures.append(f"{pid}: {exc}")
            continue
        checked += 1
        w, h = im.size
        ratio = w / h if h else 0
        if w < args.min_width or h < args.min_height:
            failures.append(f"{pid}: image too small {w}x{h}")
        # Accept generated 3-panel horizontal strips and the current Atomix
        # production comic canvas (1800x980, ~1.84). Fail only square/tall cards
        # or extreme banners that are likely placeholders.
        if not (1.35 <= ratio <= 1.95):
            failures.append(f"{pid}: not an accepted wide comic-strip image ratio {w}x{h}")
        if raw_size < 50_000:
            failures.append(f"{pid}: raster asset too small ({raw_size} bytes), likely fallback/placeholder")
        if "svg" in mime:
            failures.append(f"{pid}: SVG fallback detected")
        print(f"OK_CHECK {pid}: {mime} {w}x{h} {raw_size} bytes")

    if checked == 0:
        failures.append("No submitted-person comics found to check")

    if failures:
        print("\nFAILURES:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(f"\nPASS: {checked} submitted-person comics are raster production assets; no SVG/card fallback detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
