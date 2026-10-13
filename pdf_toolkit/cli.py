"""Command-line interface: ``python -m pdf_toolkit <command> INPUT [options]``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from . import __version__, editor


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("input", help="A PDF file, or a folder (searched recursively)")
    common.add_argument("-o", "--output", default="output", help="Output folder (default: ./output)")
    common.add_argument("-c", "--config", help="YAML config file; CLI options override it")

    parser = argparse.ArgumentParser(prog="pdf_toolkit", description="Batch-edit text in PDF files.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("replace", parents=[common], help="Find and replace text")
    p.add_argument("--find", help="Text to find")
    p.add_argument("--replace", help="Replacement text")

    p = sub.add_parser("insert-after", parents=[common], help="Insert text after an anchor phrase")
    p.add_argument("--anchor", help="Phrase to insert after")
    p.add_argument("--text", help="Text to insert")

    p = sub.add_parser("headings", parents=[common], help="Restyle headings (bold, resize, suffix)")
    p.add_argument("--min-size", type=float, help="Lines with font size >= this are headings (default 16)")
    p.add_argument("--bold", action="store_true", default=None, help="Make headings bold")
    p.add_argument("--scale", type=float, help="Multiply heading font size (default 1.0)")
    p.add_argument("--suffix", action="append", dest="suffixes",
                   help="Text appended to headings; repeat the flag for a pool to pick from")
    p.add_argument("--seed", type=int, help="Seed for reproducible suffix picking")
    return parser


def _load_config(path: str | None, command: str) -> dict:
    if not path:
        return {}
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return data.get(command, {}) or {}


def _make_edit(args: argparse.Namespace):
    """Return a function that edits one open document, or raise ValueError."""
    if args.command == "replace":
        if not args.find or args.replace is None:
            raise ValueError("replace needs --find and --replace (or set them in the config)")
        return lambda doc: editor.replace_text(doc, args.find, args.replace)
    if args.command == "insert-after":
        if not args.anchor or not args.text:
            raise ValueError("insert-after needs --anchor and --text (or set them in the config)")
        return lambda doc: editor.insert_after(doc, args.anchor, args.text)
    return lambda doc: editor.style_headings(
        doc,
        min_size=args.min_size if args.min_size is not None else 16.0,
        bold=bool(args.bold) if args.bold is not None else True,
        scale=args.scale if args.scale is not None else 1.0,
        suffixes=args.suffixes or (),
        seed=args.seed,
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    # Config values fill in anything not given on the command line.
    for key, value in _load_config(args.config, args.command.replace("-", "_")).items():
        if getattr(args, key, None) in (None, False):
            setattr(args, key, value)

    try:
        edit = _make_edit(args)
        sources = list(editor.iter_pdfs(args.input))
    except (ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if not sources:
        print("No PDF files found.", file=sys.stderr)
        return 1

    results = editor.process_many(sources, Path(args.output), edit, root=Path(args.input))
    failures = 0
    for src, outcome in results:
        if isinstance(outcome, str):
            failures += 1
            print(f"FAIL  {src}  ({outcome})")
        else:
            print(f"OK    {src}  ({outcome} change{'s' if outcome != 1 else ''})")
    print(f"\nDone: {len(results) - failures}/{len(results)} files written to {args.output}/")
    return 1 if failures else 0
