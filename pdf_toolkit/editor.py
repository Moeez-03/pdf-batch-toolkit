"""Core PDF editing functions built on PyMuPDF.

Every edit function takes an open ``pymupdf.Document`` and returns the number
of changes made, so callers can report results per file.

Limitations (by design, to keep the toolkit simple and predictable):
- Replacement text is drawn with the built-in Helvetica fonts, so the original
  font face is not preserved and only Latin characters are supported.
- Edits work on text-based PDFs. Scanned PDFs (images) need OCR first.
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Callable, Iterable, Iterator, Sequence

import pymupdf

WHITE = (1, 1, 1)


def iter_pdfs(path: str | Path) -> Iterator[Path]:
    """Yield a single PDF, or every PDF under a directory (recursive)."""
    path = Path(path)
    if path.is_file():
        yield path
    elif path.is_dir():
        yield from sorted(p for p in path.rglob("*.pdf") if p.is_file())
    else:
        raise FileNotFoundError(f"No such file or directory: {path}")


def _span_at(page: pymupdf.Page, rect: pymupdf.Rect) -> dict | None:
    """Return the text span that overlaps ``rect`` the most (size, color, origin)."""
    best, best_area = None, 0.0
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                overlap = pymupdf.Rect(span["bbox"]) & rect
                if overlap.is_valid and not overlap.is_empty and overlap.get_area() > best_area:
                    best, best_area = span, overlap.get_area()
    return best


def _int_to_rgb(color: int) -> tuple[float, float, float]:
    return ((color >> 16 & 255) / 255, (color >> 8 & 255) / 255, (color & 255) / 255)


def replace_text(doc: pymupdf.Document, find: str, replace: str) -> int:
    """Replace every occurrence of ``find`` with ``replace``."""
    changes = 0
    for page in doc:
        pending = []
        for rect in page.search_for(find):
            span = _span_at(page, rect)
            size = span["size"] if span else 11
            color = _int_to_rgb(span["color"]) if span else (0, 0, 0)
            y = span["origin"][1] if span else rect.y1 - size * 0.2
            pending.append((rect, pymupdf.Point(rect.x0, y), size, color))
        for rect, *_ in pending:
            page.add_redact_annot(rect, fill=WHITE)
        if pending:
            page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE)
        for _, point, size, color in pending:
            page.insert_text(point, replace, fontsize=size, fontname="helv", color=color)
            changes += 1
    return changes


def insert_after(doc: pymupdf.Document, anchor: str, text: str, gap: float = 3.0) -> int:
    """Insert ``text`` right after every occurrence of ``anchor`` (same line, same size)."""
    changes = 0
    for page in doc:
        for rect in page.search_for(anchor):
            span = _span_at(page, rect)
            size = span["size"] if span else 11
            color = _int_to_rgb(span["color"]) if span else (0, 0, 0)
            y = span["origin"][1] if span else rect.y1 - size * 0.2
            page.insert_text(
                pymupdf.Point(rect.x1 + gap, y), text, fontsize=size, fontname="helv", color=color
            )
            changes += 1
    return changes


def style_headings(
    doc: pymupdf.Document,
    min_size: float = 16.0,
    bold: bool = True,
    scale: float = 1.0,
    suffixes: Sequence[str] = (),
    seed: int | None = None,
    margin: float = 36.0,
) -> int:
    """Restyle headings: any text line whose largest font size is >= ``min_size``.

    - ``bold``: redraw the heading in Helvetica-Bold
    - ``scale``: multiply the heading font size (1.2 = 20% larger)
    - ``suffixes``: optional list of strings; one is appended to each heading
      (picked with a seeded random generator so runs are reproducible)
    The font size is reduced automatically if a heading would run off the page.
    """
    rng = random.Random(seed)
    changes = 0
    for page in doc:
        pending = []
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                spans = [s for s in line["spans"] if s["text"].strip()]
                if not spans:
                    continue
                size = max(s["size"] for s in spans)
                if size < min_size:
                    continue
                text = "".join(s["text"] for s in line["spans"]).strip()
                if suffixes:
                    text = f"{text} {rng.choice(list(suffixes))}"
                pending.append(
                    (pymupdf.Rect(line["bbox"]), pymupdf.Point(spans[0]["origin"]), text, size,
                     _int_to_rgb(spans[0]["color"]))
                )
        for rect, *_ in pending:
            page.add_redact_annot(rect, fill=WHITE)
        if pending:
            page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE)
        font = "hebo" if bold else "helv"
        for _, origin, text, size, color in pending:
            new_size = size * scale
            while new_size > 6 and origin.x + pymupdf.get_text_length(text, font, new_size) > page.rect.x1 - margin:
                new_size -= 0.5
            page.insert_text(origin, text, fontsize=new_size, fontname=font, color=color)
            changes += 1
    return changes


def process_file(src: Path, dst: Path, edit: Callable[[pymupdf.Document], int]) -> int:
    """Open ``src``, apply ``edit``, save to ``dst``. Returns the change count."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    with pymupdf.open(src) as doc:
        changes = edit(doc)
        doc.save(dst, garbage=3, deflate=True)
    return changes


def process_many(
    sources: Iterable[Path], out_dir: Path, edit: Callable[[pymupdf.Document], int], root: Path | None = None
) -> list[tuple[Path, int | str]]:
    """Apply ``edit`` to many PDFs. Errors are captured per file, not raised."""
    results: list[tuple[Path, int | str]] = []
    for src in sources:
        rel = src.relative_to(root) if root and root.is_dir() else Path(src.name)
        try:
            results.append((src, process_file(src, out_dir / rel, edit)))
        except Exception as exc:  # keep going on bad files
            results.append((src, f"error: {exc}"))
    return results
