"""Generate a small dummy PDF so you can try the toolkit: python samples/make_sample.py"""
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

out = Path(__file__).with_name("sample.pdf")
c = canvas.Canvas(str(out), pagesize=letter)
w, h = letter
c.setFont("Helvetica", 20)
c.drawString(72, h - 90, "Quarterly Report")
c.setFont("Helvetica", 11)
c.drawString(72, h - 120, "Prepared for ACME Corp by the analytics team.")
c.drawString(72, h - 140, "Contact:")
c.setFont("Helvetica", 20)
c.drawString(72, h - 200, "Highlights")
c.setFont("Helvetica", 11)
c.drawString(72, h - 220, "Revenue grew steadily. ACME Corp expects further growth.")
c.save()
print(f"Wrote {out}")
