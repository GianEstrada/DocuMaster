from html.parser import HTMLParser
import os
from pathlib import Path
import subprocess
from textwrap import wrap

from jinja2 import Environment, FileSystemLoader, select_autoescape

from documaster.models.orden_salida import OrdenSalidaSchema


class DocumentService:
    def __init__(self, root: Path):
        self.templates_root = root / "templates"
        self.environment = Environment(
            loader=FileSystemLoader(self.templates_root),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def render(self, order: OrdenSalidaSchema) -> str:
        html = self.environment.get_template("contrato_factura.html").render(orden=order)
        stylesheet = (self.templates_root / "styles.css").read_text(encoding="utf-8")
        return html.replace(
            '<link rel="stylesheet" href="styles.css">',
            f"<style>\n{stylesheet}\n</style>",
        )

    def create_pdf(self, html: str, output: Path) -> str:
        output.parent.mkdir(parents=True, exist_ok=True)
        try:
            browser = _find_edge()
            if browser:
                source = output.with_suffix(".render.html")
                source.write_text(html, encoding="utf-8")
                try:
                    subprocess.run(
                        [
                            browser,
                            "--headless",
                            "--disable-gpu",
                            "--no-sandbox",
                            "--no-pdf-header-footer",
                            f"--print-to-pdf={output}",
                            source.as_uri(),
                        ],
                        check=True,
                        capture_output=True,
                        text=True,
                        timeout=60,
                    )
                    if output.exists() and output.stat().st_size > 0:
                        return "Microsoft Edge (Chromium)"
                finally:
                    source.unlink(missing_ok=True)
        except (OSError, subprocess.SubprocessError) as browser_error:
            browser_error_message = str(browser_error)
        else:
            browser_error_message = "No se encontró Microsoft Edge"

        try:
            if os.name == "nt":
                gtk_bin = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Gtk-Runtime" / "bin"
                if gtk_bin.is_dir():
                    os.add_dll_directory(str(gtk_bin))
            from weasyprint import HTML

            HTML(string=html, base_url=str(self.templates_root)).write_pdf(str(output))
            return "WeasyPrint"
        except Exception as weasyprint_error:
            try:
                from reportlab.lib.pagesizes import letter
                from reportlab.pdfbase.pdfmetrics import stringWidth
                from reportlab.pdfgen.canvas import Canvas

                canvas = Canvas(str(output), pagesize=letter)
                width, height = letter
                y = height - 45
                canvas.setTitle("Contrato de Arrendamiento y Factura Proforma")
                parser = _PlainTextParser()
                parser.feed(html)
                parser.close()
                canvas.setFont("Helvetica", 9)
                for paragraph in parser.paragraphs:
                    for line in _wrap_pdf_text(paragraph, width - 80, "Helvetica", 9):
                        canvas.drawString(40, y, line)
                        y -= 13
                        if y < 45:
                            canvas.showPage()
                            canvas.setFont("Helvetica", 9)
                            y = height - 45
                    y -= 5
                canvas.save()
                return f"ReportLab (fallback; Edge: {browser_error_message}; WeasyPrint: {weasyprint_error})"
            except Exception as reportlab_error:
                raise RuntimeError(f"No fue posible generar el PDF: {reportlab_error}") from reportlab_error


def _find_edge() -> str | None:
    candidates = [
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(os.environ.get("ProgramFiles", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
    ]
    return next((str(path) for path in candidates if path.is_file()), None)


class _PlainTextParser(HTMLParser):
    """Converts the HTML fallback into readable paragraphs instead of raw markup."""

    BLOCK_TAGS = {"body", "div", "h1", "h2", "p", "tr", "table", "br"}

    def __init__(self):
        super().__init__()
        self.paragraphs: list[str] = []
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs):
        if tag in self.BLOCK_TAGS and self._parts:
            self._flush()

    def handle_endtag(self, tag: str):
        if tag in self.BLOCK_TAGS:
            self._flush()

    def handle_data(self, data: str):
        text = " ".join(data.split())
        if text:
            self._parts.append(text)

    def _flush(self):
        text = " ".join(self._parts).strip()
        if text:
            self.paragraphs.append(text)
        self._parts.clear()

    def close(self):
        super().close()
        self._flush()


def _wrap_pdf_text(text: str, max_width: float, font: str, size: int) -> list[str]:
    from reportlab.pdfbase.pdfmetrics import stringWidth

    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if stringWidth(candidate, font, size) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines
