from pathlib import Path

from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

OUT = Path(__file__).parent / "out"


def policy_pdf(client_id: str, policy_id: str, sections: dict[str, str], ugly: bool = False) -> Path:
    path = OUT / "policies" / client_id / f"{policy_id}.pdf"
    path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(path), pagesize=LETTER)
    y = 740
    for heading, body in sections.items():          # one section = one future chunk
        c.setFont("Helvetica-Bold", 11); c.drawString(54, y, heading); y -= 16
        c.setFont("Helvetica", 9)
        for line in body.splitlines():
            c.drawString(54, y, line); y -= 12
            if y < 60:
                c.showPage(); y = 740
        y -= 10
    c.save()
    if ugly:
        make_ugly(path, OUT / "policies" / client_id / f"{policy_id}_ugly.pdf")       

    return path




def make_ugly(src: Path, dst: Path) -> None:
    from pdf2image import convert_from_path   # needs poppler installed

    """Rotate pages and drop the text layer by rasterising: what a fax-to-PDF loss run looks like."""
    pages = convert_from_path(src, dpi=110)
    pages = [p.rotate(90 if i % 2 else -3, expand=True) for i, p in enumerate(pages)]
    pages[0].save(dst, save_all=True, append_images=pages[1:])
