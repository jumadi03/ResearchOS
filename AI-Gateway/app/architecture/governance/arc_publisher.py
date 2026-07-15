"""Render canonical ARC Markdown to HTML and PDF publication artifacts."""

from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
from html import escape
from io import BytesIO
import re

from ..models import ARCPackage


@dataclass(frozen=True, slots=True)
class ARCPublisher:
    """Create sibling HTML/PDF renders and issue a new finalized manifest."""

    def publish(self, package: ARCPackage) -> ARCPackage:
        if not package.verify():
            raise ValueError("ARC publication requires a verified source package")
        markdown = package.artifacts.get("report.md")
        if not isinstance(markdown, str):
            raise ValueError("ARC publication requires a canonical report.md")

        artifacts = {
            **package.artifacts,
            "report.html": self.render_html(markdown),
            "report.pdf": self.render_pdf(markdown),
        }
        checksums = {
            name: sha256(ARCPackage._bytes(content)).hexdigest()
            for name, content in sorted(artifacts.items())
        }
        manifest = replace(
            package.manifest,
            arc_id="",
            manifest_hash="",
            artifact_checksums=checksums,
        ).finalized()
        published = ARCPackage(manifest=manifest, artifacts=artifacts)
        if not published.verify():
            raise ValueError("Published ARC package failed its integrity check")
        return published

    @staticmethod
    def _inline(value: str) -> str:
        value = escape(value)
        value = re.sub(r"`([^`]+)`", r"<code>\1</code>", value)
        value = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", value)
        return value

    def render_html(self, markdown: str) -> str:
        """Render the constrained canonical ARC Markdown dialect safely."""
        lines = markdown.splitlines()
        body: list[str] = []
        index = 0
        in_list = False
        while index < len(lines):
            line = lines[index]
            if line.startswith("| "):
                if in_list:
                    body.append("</ul>")
                    in_list = False
                rows: list[list[str]] = []
                while index < len(lines) and lines[index].startswith("|"):
                    cells = [cell.strip() for cell in lines[index].strip("|").split("|")]
                    rows.append(cells)
                    index += 1
                header = rows[0]
                data = rows[2:] if len(rows) > 1 else []
                body.append("<div class=\"table-wrap\"><table><thead><tr>")
                body.extend(f"<th>{self._inline(cell)}</th>" for cell in header)
                body.append("</tr></thead><tbody>")
                for row in data:
                    body.append("<tr>")
                    body.extend(f"<td>{self._inline(cell)}</td>" for cell in row)
                    body.append("</tr>")
                body.append("</tbody></table></div>")
                continue
            if line.startswith("- "):
                if not in_list:
                    body.append("<ul>")
                    in_list = True
                body.append(f"<li>{self._inline(line[2:])}</li>")
            else:
                if in_list:
                    body.append("</ul>")
                    in_list = False
                if line.startswith("# "):
                    body.append(f"<h1>{self._inline(line[2:])}</h1>")
                elif line.startswith("## "):
                    body.append(f"<h2>{self._inline(line[3:])}</h2>")
                elif line.strip():
                    body.append(f"<p>{self._inline(line)}</p>")
            index += 1
        if in_list:
            body.append("</ul>")

        return "\n".join(
            [
                "<!doctype html>",
                '<html lang="en">',
                "<head>",
                '<meta charset="utf-8">',
                '<meta name="viewport" content="width=device-width, initial-scale=1">',
                "<title>Architecture Review &amp; Compliance Report</title>",
                "<style>",
                ":root{color-scheme:light;--ink:#172033;--muted:#5e687b;--line:#d9dee8;--accent:#2457d6;--panel:#f6f8fc}",
                "*{box-sizing:border-box}body{margin:0;background:#eef2f8;color:var(--ink);font:15px/1.6 Inter,Segoe UI,Arial,sans-serif}",
                "main{max-width:1080px;margin:40px auto;padding:48px 56px;background:white;border:1px solid var(--line);border-radius:14px;box-shadow:0 12px 35px #17203314}",
                "h1{font-size:30px;line-height:1.2;margin:0 0 28px;border-bottom:3px solid var(--accent);padding-bottom:16px}",
                "h2{font-size:20px;margin:34px 0 14px}ul{padding-left:22px}code{font:12px/1.5 Consolas,monospace;background:var(--panel);padding:2px 5px;border-radius:4px;overflow-wrap:anywhere}",
                ".table-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:8px}table{border-collapse:collapse;width:100%;font-size:13px}th{background:var(--panel);text-align:left}th,td{padding:10px 12px;border-bottom:1px solid var(--line);vertical-align:top}tr:last-child td{border-bottom:0}",
                "@media(max-width:720px){main{margin:0;padding:28px 20px;border:0;border-radius:0}h1{font-size:25px}}",
                "@media print{body{background:white}main{margin:0;max-width:none;padding:0;border:0;box-shadow:none}}",
                "</style>",
                "</head>",
                "<body><main>",
                *body,
                "</main></body>",
                "</html>",
                "",
            ]
        )

    @staticmethod
    def _pdf_inline(value: str) -> str:
        value = escape(value)
        value = re.sub(r"`([^`]+)`", r'<font name="Courier" size="7">\1</font>', value)
        value = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", value)
        return value

    def render_pdf(self, markdown: str) -> bytes:
        """Render canonical ARC Markdown to a polished paginated PDF."""
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_LEFT
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.pdfgen.canvas import Canvas
        from reportlab.platypus import (
            KeepTogether,
            ListFlowable,
            ListItem,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )

        buffer = BytesIO()
        page_size = landscape(A4)
        document = SimpleDocTemplate(
            buffer,
            pagesize=page_size,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=14 * mm,
            bottomMargin=16 * mm,
            title="Architecture Review & Compliance Report",
            author="ResearchOS",
        )
        styles = getSampleStyleSheet()
        styles.add(
            ParagraphStyle(
                "ARC-H1",
                parent=styles["Title"],
                fontName="Helvetica-Bold",
                fontSize=20,
                leading=24,
                textColor=colors.HexColor("#172033"),
                spaceAfter=10,
                borderColor=colors.HexColor("#2457D6"),
                borderWidth=0,
                borderPadding=(0, 0, 8, 0),
            )
        )
        styles.add(
            ParagraphStyle(
                "ARC-H2",
                parent=styles["Heading2"],
                fontName="Helvetica-Bold",
                fontSize=13,
                leading=16,
                textColor=colors.HexColor("#2457D6"),
                spaceBefore=8,
                spaceAfter=5,
            )
        )
        styles.add(
            ParagraphStyle(
                "ARC-Body",
                parent=styles["BodyText"],
                fontName="Helvetica",
                fontSize=8.2,
                leading=10.5,
                textColor=colors.HexColor("#263044"),
                splitLongWords=1,
                alignment=TA_LEFT,
            )
        )
        styles.add(
            ParagraphStyle(
                "ARC-Cell",
                parent=styles["ARC-Body"],
                fontSize=7.3,
                leading=9.5,
            )
        )

        story: list[object] = []
        lines = markdown.splitlines()
        index = 0
        bullets: list[object] = []

        def flush_bullets() -> None:
            if bullets:
                story.append(
                    ListFlowable(
                        list(bullets),
                        bulletType="bullet",
                        leftIndent=14,
                        bulletFontSize=6,
                        spaceAfter=4,
                    )
                )
                bullets.clear()

        while index < len(lines):
            line = lines[index]
            if line.startswith("| "):
                flush_bullets()
                rows: list[list[str]] = []
                while index < len(lines) and lines[index].startswith("|"):
                    rows.append(
                        [cell.strip() for cell in lines[index].strip("|").split("|")]
                    )
                    index += 1
                rows = [rows[0], *rows[2:]]
                table_data = [
                    [Paragraph(self._pdf_inline(cell), styles["ARC-Cell"]) for cell in row]
                    for row in rows
                ]
                width = document.width / max(len(rows[0]), 1)
                table = Table(
                    table_data,
                    colWidths=[width] * len(rows[0]),
                    repeatRows=1,
                    hAlign="LEFT",
                )
                table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF0FF")),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#172033")),
                            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CCD4E2")),
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 5),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                            ("TOPPADDING", (0, 0), (-1, -1), 5),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                        ]
                    )
                )
                story.extend([table, Spacer(1, 7)])
                continue
            if line.startswith("- "):
                bullets.append(
                    ListItem(
                        Paragraph(self._pdf_inline(line[2:]), styles["ARC-Body"]),
                        leftIndent=8,
                    )
                )
            else:
                flush_bullets()
                if line.startswith("# "):
                    story.append(Paragraph(self._pdf_inline(line[2:]), styles["ARC-H1"]))
                elif line.startswith("## "):
                    story.append(Paragraph(self._pdf_inline(line[3:]), styles["ARC-H2"]))
                elif line.strip():
                    story.append(
                        KeepTogether(
                            [Paragraph(self._pdf_inline(line), styles["ARC-Body"]), Spacer(1, 3)]
                        )
                    )
            index += 1
        flush_bullets()

        def decorate(canvas, doc) -> None:
            canvas.saveState()
            canvas.setStrokeColor(colors.HexColor("#D9DEE8"))
            canvas.setLineWidth(0.5)
            canvas.line(18 * mm, 13 * mm, page_size[0] - 18 * mm, 13 * mm)
            canvas.setFont("Helvetica", 7)
            canvas.setFillColor(colors.HexColor("#667085"))
            canvas.drawString(18 * mm, 8 * mm, "ResearchOS - Architecture Review & Compliance")
            canvas.drawRightString(
                page_size[0] - 18 * mm, 8 * mm, f"Page {doc.page}"
            )
            canvas.restoreState()

        def invariant_canvas(*args, **kwargs):
            kwargs["invariant"] = 1
            return Canvas(*args, **kwargs)

        document.build(
            story,
            onFirstPage=decorate,
            onLaterPages=decorate,
            canvasmaker=invariant_canvas,
        )
        return buffer.getvalue()
