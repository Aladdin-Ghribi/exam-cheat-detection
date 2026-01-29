"""Export login presentation slides to a single PDF (or individual PNGs) using Playwright.

Usage:
    python tools/export_presentation.py --url http://localhost:5000 --output presentation_exports --format pdf
    python tools/export_presentation.py --url http://localhost:5000 --output presentation_exports --format png

Prereqs:
    pip install playwright
    python -m playwright install chromium
    (Pillow already present in this env for PNG->PDF combine)
"""
from __future__ import annotations

import argparse
from pathlib import Path
from io import BytesIO
from typing import List
from playwright.sync_api import sync_playwright
from PIL import Image


def export_slides(
    base_url: str,
    output_dir: Path,
    fmt: str = "pdf",
    width: int = 1920,
    height: int = 1080,
    settle_ms: int = 800,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": width, "height": height})

        page.goto(f"{base_url}/", wait_until="networkidle")

        # Open presentation overlay
        page.click("#presentationLaunchBtn")
        page.wait_for_selector("#presentationOverlay", state="visible")

        slides = page.query_selector_all(".presentation-slide")
        total = len(slides)
        if total == 0:
            browser.close()
            raise RuntimeError(
                "No presentation slides found. Check selectors or page load.")

        # Let initial overlay animations finish
        page.wait_for_timeout(settle_ms)

        png_bytes: List[bytes] = []

        for i in range(total):
            # ensure layout/transition settled
            page.wait_for_timeout(settle_ms)
            # capture PNG bytes (full page to include slide)
            shot = page.screenshot(full_page=True)
            png_bytes.append(shot)

            if fmt == "png":
                (output_dir / f"slide-{i + 1}.png").write_bytes(shot)

            if i < total - 1:
                page.click("#presentationNextBtn")

        browser.close()

        if fmt == "pdf":
            images = [Image.open(BytesIO(b)).convert("RGB") for b in png_bytes]
            first, *rest = images
            output_path = output_dir / "presentation.pdf"
            first.save(output_path, save_all=True, append_images=rest)
            print(f"Exported {total} slides to single PDF: {output_path}")
        else:
            print(f"Exported {total} slides as PNGs to {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export login presentation slides to PDF/PNG")
    parser.add_argument("--url", default="http://localhost:5000",
                        help="Base URL where the app is running")
    parser.add_argument(
        "--output", default="presentation_exports", help="Output folder")
    parser.add_argument(
        "--format", choices=["pdf", "png"], default="pdf", help="Output format")
    parser.add_argument("--width", type=int, default=1920,
                        help="Viewport/PDF width")
    parser.add_argument("--height", type=int, default=1080,
                        help="Viewport/PDF height")
    parser.add_argument("--settle-ms", type=int, default=800,
                        help="Delay after each slide transition before capture (ms)")
    args = parser.parse_args()

    export_slides(
        base_url=args.url,
        output_dir=Path(args.output),
        fmt=args.format,
        width=args.width,
        height=args.height,
        settle_ms=args.settle_ms,
    )


if __name__ == "__main__":
    main()
