# pdf-batch-toolkit

A small, scriptable CLI for batch-editing text in PDF files. Point it at one PDF or a whole folder, pick a command, and it writes edited copies to an output folder. Your originals are never modified.

Built with Python and [PyMuPDF](https://pymupdf.readthedocs.io/).

## Features

| Command | What it does |
|---|---|
| `replace` | Find and replace text across every page |
| `insert-after` | Insert text right after an anchor phrase (e.g. add a phone number after `Contact:`) |
| `headings` | Restyle headings: make them bold, resize them, optionally append text |

- Works on a single file or a folder (recursive)
- Settings can live in a YAML config file, CLI flags override it
- One bad file never stops the batch; errors are reported per file
- Reproducible runs via `--seed`

## Install

```bash
git clone https://github.com/Moeez-03/pdf-batch-toolkit.git
cd pdf-batch-toolkit
pip install -r requirements.txt
```

## Quick start

```bash
# Create a dummy PDF to experiment with
python samples/make_sample.py

# Replace text
python -m pdf_toolkit replace samples/sample.pdf -o output --find "ACME Corp" --replace "Example Inc"

# Insert text after a phrase
python -m pdf_toolkit insert-after samples/sample.pdf -o output --anchor "Contact:" --text "+1-555-0100"

# Make headings (16pt and larger) bold and 10% bigger
python -m pdf_toolkit headings samples/sample.pdf -o output --min-size 16 --bold --scale 1.1

# Process a whole folder
python -m pdf_toolkit replace ./my_pdfs -o ./edited --find "2025" --replace "2026"
```

## Config file

Copy `config.example.yaml` to `config.yaml` and run:

```bash
python -m pdf_toolkit headings ./my_pdfs -c config.yaml
```

Each command has its own section; flags given on the command line win over the file.

## Limitations

Please read these before using it on important documents:

- **Text-based PDFs only.** Scanned PDFs (images of pages) need OCR first.
- **Font is not preserved.** Edited text is drawn in Helvetica, and only Latin characters are supported.
- **Replacement length matters.** Surrounding text is not reflowed, so a replacement much longer than the original can touch the next word. Same-length or shorter replacements look best.
- Always review the output PDFs before sending them to anyone.

## Development

```bash
pip install pytest
pytest
```

## License

MIT, see [LICENSE](LICENSE).
