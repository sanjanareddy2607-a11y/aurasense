"""Build the AuraSense audit PDF and Markdown from content blocks.

This is a reporting-only script. It reads prepared content blocks (written from
an inspection of the running project) and produces:
  audit/AURASENSE_AUDIT.pdf
  audit/AURASENSE_AUDIT.md

No application source file is imported or modified.
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from fpdf import FPDF
from fpdf.fonts import FontFace
from fpdf.enums import TableCellFillMode

from report_blocks_a import BLOCKS as A
from report_blocks_b import BLOCKS as B
from report_blocks_c import BLOCKS as C
from report_blocks_d import BLOCKS as D

ROOT = Path(__file__).resolve().parent
FONT_DIR = Path("C:/Windows/Fonts")
FONT_REG = FONT_DIR / "arial.ttf"
FONT_BOLD = FONT_DIR / "arialbd.ttf"
FONT_ITALIC = FONT_DIR / "ariali.ttf"

FOREST = (24, 61, 50)
FOREST_DARK = (16, 42, 34)
SAGE = (145, 165, 142)
SAGE_LIGHT = (232, 237, 227)
AMBER = (212, 154, 69)
CORAL = (201, 121, 105)
CHARCOAL = (48, 56, 50)
GREY = (120, 128, 120)
LINE = (217, 216, 205)
IVORY = (247, 246, 240)
PAPER = (253, 252, 247)

BLOCKS = A + B + C + D
TITLE = "AURASENSE \u2014 COMPLETE PROJECT EXPLANATION, TECHNICAL ARCHITECTURE AND FUNCTIONALITY AUDIT"
SHORT_TITLE = "AuraSense \u2014 Project Explanation & Technical Audit"


class AuditPDF(FPDF):
    def __init__(self, toc: list[tuple[str, str, int]] | None = None):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.toc = toc
        self.chapters: list[tuple[str, str, int]] = []
        self.set_auto_page_break(auto=True, margin=21)
        self.set_margins(18, 20, 18)
        self.add_font("Arial", "", str(FONT_REG))
        self.add_font("Arial", "B", str(FONT_BOLD))
        self.add_font("Arial", "I", str(FONT_ITALIC))
        self.alias_nb_pages()
        self.set_title(TITLE)
        self.set_author("AuraSense technical audit")
        self.set_subject("Inspection, verification and explanation of the AuraSense research prototype")
        self.set_creator("AuraSense audit builder")

    # ------------------------------------------------------------------ chrome
    def header(self) -> None:
        if self.page_no() == 1:
            return
        self.set_y(9)
        self.set_font("Arial", "B", 7.5)
        self.set_text_color(*FOREST)
        self.cell(0, 5, SHORT_TITLE, align="L")
        self.set_font("Arial", "", 7.5)
        self.set_text_color(*GREY)
        self.cell(0, 5, "Independent inspection report  |  November 2026", align="R")
        self.set_draw_color(*LINE)
        self.set_line_width(0.25)
        self.line(18, 16, 192, 16)
        self.set_y(21)

    def footer(self) -> None:
        if self.page_no() == 1:
            return
        self.set_y(-15)
        self.set_font("Arial", "", 7)
        self.set_text_color(*GREY)
        self.cell(0, 5, "AuraSense research prototype  \u00b7  Not a medical device  \u00b7  No source files were modified", align="C")
        self.set_y(-11)
        self.cell(0, 5, f"Page {self.page_no()} of {{nb}}", align="C")

    # ------------------------------------------------------------------ atoms
    def cover(self) -> None:
        self.add_page()
        self.set_fill_color(*FOREST)
        self.rect(0, 0, 210, 297, style="F")
        self.set_fill_color(*AMBER)
        self.rect(18, 30, 34, 2.2, style="F")
        self.set_xy(18, 40)
        self.set_font("Arial", "B", 9)
        self.set_text_color(*SAGE)
        self.cell(0, 6, "PROJECT EXPLANATION  \u00b7  ARCHITECTURE  \u00b7  AUDIT", new_x="LMARGIN", new_y="NEXT")
        self.set_xy(18, 64)
        self.set_font("Arial", "B", 31)
        self.set_text_color(250, 249, 243)
        self.multi_cell(174, 12.4, "AuraSense", align="L", new_x="LMARGIN", new_y="NEXT")
        self.set_xy(18, 84)
        self.set_font("Arial", "", 15)
        self.set_text_color(*SAGE)
        self.multi_cell(
            168,
            7.6,
            "Complete project explanation,\ntechnical architecture and functionality audit",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        self.set_draw_color(80, 110, 96)
        self.set_line_width(0.3)
        self.line(18, 122, 192, 122)
        self.set_xy(18, 130)
        self.set_font("Arial", "", 10)
        self.set_text_color(225, 229, 217)
        self.multi_cell(
            150,
            6,
            "An evidence-based inspection of the existing build: what is real,\n"
            "what is simulated, how every part works, and what must improve.",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        self.set_xy(18, 166)
        self.set_font("Arial", "B", 9)
        self.set_text_color(250, 249, 243)
        self.cell(0, 6, "Prepared for faculty review and student demonstration", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Arial", "", 9)
        self.set_text_color(*SAGE)
        self.cell(0, 6, "Model version aura-wesad-20261107-444b41", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 6, f"Audit date: {date.today().strftime('%d %B %Y')}", new_x="LMARGIN", new_y="NEXT")

        self.set_xy(18, 218)
        self.set_fill_color(34, 76, 62)
        self.rect(18, 218, 174, 38, style="F", round_corners=True, corner_radius=3)
        self.set_xy(24, 223)
        self.set_font("Arial", "B", 8.5)
        self.set_text_color(*AMBER)
        self.cell(0, 5, "SCOPE NOTE", new_x="LMARGIN", new_y="NEXT")
        self.set_x(24)
        self.set_font("Arial", "", 8.6)
        self.set_text_color(231, 235, 224)
        self.multi_cell(
            160,
            4.8,
            "This report inspects the application that already exists. It does not propose a redesign, and no "
            "application file, database record or trained artifact was modified. Claims are separated into "
            "verified, simulated, hardcoded and not implemented. Where something could not be tested, it is "
            "marked NOT VERIFIED rather than assumed.",
            align="L",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        self.set_xy(18, 266)
        self.set_font("Arial", "", 7.5)
        self.set_text_color(160, 180, 166)
        self.cell(0, 4, "Research prototype  \u00b7  Not clinically validated  \u00b7  Not a diagnosis", align="C")

    def toc_page(self) -> None:
        self.add_page()
        self.set_font("Arial", "B", 22)
        self.set_text_color(*FOREST)
        self.cell(0, 12, "Contents", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Arial", "", 9)
        self.set_text_color(*GREY)
        self.cell(0, 5, "Every chapter below is based on the code, artifacts and live checks described in Chapter 15.", new_x="LMARGIN", new_y="NEXT")
        self.ln(6)
        assert self.toc is not None
        for num, title, page in self.toc:
            y = self.get_y()
            if y > 268:
                self.add_page()
                y = self.get_y()
            self.set_font("Arial", "B", 9)
            self.set_text_color(*AMBER)
            self.set_xy(18, y)
            self.cell(12, 7, num)
            self.set_font("Arial", "", 9.3)
            self.set_text_color(*CHARCOAL)
            self.cell(142, 7, title)
            self.set_font("Arial", "B", 9)
            self.set_text_color(*FOREST)
            self.cell(14, 7, str(page), align="R")
            self.ln(7)
        self.set_y(221)
        self.set_font("Arial", "I", 7.8)
        self.set_text_color(*GREY)
        self.multi_cell(
            0,
            4.4,
            "Reading tip: Chapters 1 and 19 are written for a reader new to the project. Chapters 2\u20135 cover the "
            "stack and machine learning; 6\u201312 walk through the modules; 15 is the test evidence; 18 is the verdict.",
        )

    def chapter(self, num: str, title: str, sub: str | None = None) -> None:
        self.add_page()
        self.chapters.append((num, title, self.page_no()))
        self.set_fill_color(*AMBER)
        self.rect(18, 27, 13, 1.6, style="F")
        self.set_xy(18, 32)
        self.set_font("Arial", "B", 8.5)
        self.set_text_color(*AMBER)
        if num in {"A", "B", "C", "D"}:
            label = f"APPENDIX {num}"
        elif num.isdigit():
            label = f"CHAPTER {num}"
        else:
            label = num.upper()
        self.cell(28, 5, label)
        self.set_xy(18, 40)
        self.set_font("Arial", "B", 20)
        self.set_text_color(*FOREST)
        self.multi_cell(174, 9.2, title, align="L", new_x="LMARGIN", new_y="NEXT")
        if sub:
            self.set_font("Arial", "I", 9.5)
            self.set_text_color(*GREY)
            self.multi_cell(170, 5, sub, align="L", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

    def h2(self, text: str) -> None:
        if self.get_y() > 250:
            self.add_page()
        self.ln(2)
        self.set_font("Arial", "B", 11.5)
        self.set_text_color(*FOREST)
        self.multi_cell(0, 6.2, text, align="L", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*LINE)
        self.line(18, self.get_y() + 0.8, 70, self.get_y() + 0.8)
        self.ln(3)

    def body(self, text: str, size: float = 9.4, color=CHARCOAL, lh: float = 5.05, after: float = 2.0) -> None:
        if self.get_y() > 273:
            self.add_page()
        self.set_font("Arial", "", size)
        self.set_text_color(*color)
        self.multi_cell(0, lh, text, align="L", new_x="LMARGIN", new_y="NEXT")
        self.ln(after)

    def bullets(self, items: list[str], size: float = 9.1) -> None:
        for item in items:
            if self.get_y() > 270:
                self.add_page()
            self.set_font("Arial", "", size)
            self.set_text_color(*CHARCOAL)
            self.set_x(21)
            self.cell(4, 4.9, "\u2022")
            self.multi_cell(0, 4.9, item, align="L", new_x="LMARGIN", new_y="NEXT")
            self.ln(0.9)
        self.ln(1.5)

    def callout(self, title: str, text: str, tone: str = "amber") -> None:
        color = {"amber": AMBER, "coral": CORAL, "forest": FOREST, "sage": SAGE}.get(tone, AMBER)
        fill = {"amber": (250, 244, 230), "coral": (249, 236, 233), "forest": (235, 241, 234), "sage": SAGE_LIGHT}.get(tone, (250, 244, 230))
        self.set_font("Arial", "", 8.6)
        text_h = self.multi_cell(162, 4.5, text, dry_run=True, output="HEIGHT")
        box_h = max(24, 12 + text_h)
        if self.get_y() + box_h > 272:
            self.add_page()
        y = self.get_y()
        self.set_fill_color(*fill)
        self.rect(18, y, 174, box_h, style="F", round_corners=True, corner_radius=2)
        self.set_fill_color(*color)
        self.rect(18, y, 2.4, box_h, style="F")
        self.set_xy(24, y + 3.2)
        self.set_font("Arial", "B", 8.7)
        self.set_text_color(*color)
        self.cell(0, 4.5, title.upper(), new_x="LMARGIN", new_y="NEXT")
        self.set_x(24)
        self.set_font("Arial", "", 8.6)
        self.set_text_color(*CHARCOAL)
        self.multi_cell(162, 4.5, text, align="L", new_x="LMARGIN", new_y="NEXT")
        self.set_y(y + box_h + 4)

    def table(self, head: list[str], rows: list[list[str]], widths: list[float] | None = None,
              size: float = 8.0, align: tuple[str, ...] | None = None) -> None:
        if self.get_y() > 235:
            self.add_page()
        self.set_font("Arial", "", size)
        self.set_text_color(*CHARCOAL)
        self.set_fill_color(251, 250, 244)
        kwargs = dict(
            line_height=size * 0.62,
            headings_style=FontFace(emphasis="BOLD", color=(255, 255, 255), fill_color=FOREST),
            text_align=align or ("LEFT",) * len(head),
            padding=(1.8, 1.6),
            cell_fill_mode=TableCellFillMode.EVEN_ROWS,
        )
        if widths:
            kwargs["col_widths"] = widths
        else:
            kwargs["width"] = 174
        with FPDF.table(self, **kwargs) as table:
            row = table.row()
            for item in head:
                row.cell(item)
            for values in rows:
                row = table.row()
                for value in values:
                    row.cell(str(value))
        self.ln(3)

    def kv(self, rows: list[list[str]], widths: list[float] | None = None) -> None:
        self.table(["Field", "Value"], rows, widths or [50, 124], size=8.5)

    def flow(self, title: str, steps: list[str], per_row: int = 4) -> None:
        self.ln(1)
        self.set_font("Arial", "B", 8.3)
        self.set_text_color(*FOREST)
        self.cell(0, 5, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(1.5)
        gap = 8
        box_w = (174 - gap * (per_row - 1)) / per_row
        box_h = 17
        row_y = self.get_y()
        for index, step in enumerate(steps):
            col = index % per_row
            if col == 0:
                row_y = self.get_y()
                if row_y + box_h > 272:
                    self.add_page()
                    row_y = self.get_y()
            x = 18 + col * (box_w + gap)
            self.set_fill_color(*(SAGE_LIGHT if (index // per_row) % 2 == 0 else (244, 242, 233)))
            self.set_draw_color(*SAGE)
            self.set_line_width(0.25)
            self.rect(x, row_y, box_w, box_h, style="DF", round_corners=True, corner_radius=2)
            self.set_xy(x + 2.5, row_y + 3)
            self.set_font("Arial", "B", 7.4)
            self.set_text_color(*FOREST)
            self.multi_cell(box_w - 5, 3.5, step, align="C")
            if col < per_row - 1 and index < len(steps) - 1:
                self.set_draw_color(*AMBER)
                self.set_line_width(0.5)
                ax = x + box_w + 1.2
                ay = row_y + box_h / 2
                self.line(ax, ay, ax + gap - 2.4, ay)
                self.line(ax + gap - 3.8, ay - 1.4, ax + gap - 2.4, ay)
                self.line(ax + gap - 3.8, ay + 1.4, ax + gap - 2.4, ay)
            if col == per_row - 1 or index == len(steps) - 1:
                self.set_y(row_y + box_h + 4)
        self.ln(1)

    def arch(self) -> None:
        if self.get_y() > 170:
            self.add_page()
        self.ln(2)
        self.set_font("Arial", "B", 8.3)
        self.set_text_color(*FOREST)
        self.cell(0, 5, "AuraSense architecture (actual components)", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)
        layers = [
            ("BROWSER", "React 19 + TypeScript + Vite + Tailwind + Recharts  \u00b7  src/pages, components, context", SAGE_LIGHT, FOREST),
            ("HTTP / JSON + JWT", "fetch('/api/...') through the Vite proxy (dev) or VITE_API_URL  \u00b7  Authorization: Bearer", (244, 242, 233), CHARCOAL),
            ("FASTAPI (Python 3.14)", "routers/ \u2192 services/ \u2192 SQLAlchemy  \u00b7  validation, roles, ownership checks", (235, 241, 234), FOREST),
            ("ML LAYER", "ml/features.py \u2192 median imputer \u2192 model.joblib (Gradient Boosting) \u2192 probabilities", (250, 244, 230), FOREST),
            ("SQLITE + FILES", "9 tables  \u00b7  storage/uploads, storage/sessions, storage/reports  \u00b7  ml/artifacts", SAGE_LIGHT, FOREST),
        ]
        box_h = 14
        for index, (label, detail, fill, color) in enumerate(layers):
            y = self.get_y()
            self.set_fill_color(*fill)
            self.set_draw_color(*LINE)
            self.rect(18, y, 174, box_h, style="DF", round_corners=True, corner_radius=2)
            self.set_xy(22, y + 2.3)
            self.set_font("Arial", "B", 7.2)
            self.set_text_color(*color)
            self.cell(38, 4, label)
            self.set_xy(60, y + 2.3)
            self.set_font("Arial", "", 7.2)
            self.set_text_color(*CHARCOAL)
            self.multi_cell(128, 4, detail, new_x="LMARGIN", new_y="NEXT")
            if index < len(layers) - 1:
                ax = 105
                self.set_draw_color(*AMBER)
                self.set_line_width(0.5)
                self.line(ax, y + box_h + 0.6, ax, y + box_h + 3.2)
                self.line(ax - 1.4, y + box_h + 2.0, ax, y + box_h + 3.4)
                self.line(ax + 1.4, y + box_h + 2.0, ax, y + box_h + 3.4)
            self.set_y(y + box_h + 4)
        self.ln(2)

    def bars(self, title: str, labels: list[str], series: list[tuple[str, list[float], tuple[int, int, int]]]) -> None:
        if self.get_y() > 205:
            self.add_page()
        self.ln(1)
        self.set_font("Arial", "B", 8.3)
        self.set_text_color(*FOREST)
        self.cell(0, 5, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)
        x0, y0 = 30, self.get_y() + 4
        height, width = 46, 150
        self.set_draw_color(*LINE)
        for tick in range(0, 101, 25):
            y = y0 + height - height * tick / 100
            self.set_line_width(0.2)
            self.line(x0, y, x0 + width, y)
            self.set_font("Arial", "", 6.3)
            self.set_text_color(*GREY)
            self.set_xy(x0 - 10, y - 1.7)
            self.cell(8, 3.4, str(tick), align="R")
        self.set_draw_color(*CHARCOAL)
        self.line(x0, y0, x0, y0 + height)
        group_w = width / len(labels)
        bar_w = min(9.0, (group_w - 10) / max(1, len(series)))
        for gi, label in enumerate(labels):
            gx = x0 + gi * group_w + 5
            for si, (_, values, color) in enumerate(series):
                value = max(0.0, min(100.0, values[gi]))
                h = height * value / 100
                self.set_fill_color(*color)
                self.rect(gx + si * (bar_w + 1.4), y0 + height - h, bar_w, h, style="F")
                self.set_font("Arial", "", 5.6)
                self.set_text_color(*CHARCOAL)
                self.set_xy(gx + si * (bar_w + 1.4) - 1.5, y0 + height - h - 3.6)
                self.cell(bar_w + 3, 3, f"{value:.1f}", align="C")
            self.set_font("Arial", "", 6.6)
            self.set_text_color(*CHARCOAL)
            self.set_xy(x0 + gi * group_w, y0 + height + 2)
            self.cell(group_w, 4, label, align="C")
        legend_y = y0 + height + 10
        lx = x0
        for name, _, color in series:
            self.set_fill_color(*color)
            self.rect(lx, legend_y, 3.4, 3.4, style="F")
            self.set_font("Arial", "", 6.8)
            self.set_text_color(*CHARCOAL)
            self.set_xy(lx + 4.6, legend_y - 0.8)
            self.cell(30, 4, name)
            lx += 44
        self.set_y(legend_y + 7)

    def pagebreak(self) -> None:
        self.add_page()

    def render(self, blocks: list[dict], with_toc: bool) -> None:
        self.cover()
        if with_toc:
            self.toc_page()
        for block in blocks:
            kind = block["t"]
            if kind == "chapter":
                self.chapter(block["num"], block["title"], block.get("sub"))
            elif kind == "h2":
                self.h2(block["text"])
            elif kind == "p":
                self.body(block["text"])
            elif kind == "small":
                self.body(block["text"], size=8.2, color=GREY, lh=4.4)
            elif kind == "b":
                self.bullets(block["items"])
            elif kind == "kv":
                self.kv(block["rows"], block.get("widths"))
            elif kind == "table":
                self.table(block["head"], block["rows"], block.get("widths"), block.get("size", 8.0), block.get("align"))
            elif kind == "callout":
                self.callout(block["title"], block["text"], block.get("tone", "amber"))
            elif kind == "flow":
                self.flow(block["title"], block["steps"], block.get("per_row", 4))
            elif kind == "arch":
                self.arch()
            elif kind == "bars":
                self.bars(block["title"], block["labels"], block["series"])
            elif kind == "pagebreak":
                self.pagebreak()
            else:
                raise ValueError(f"Unknown block type {kind}")


def build_markdown(blocks: list[dict]) -> str:
    lines = [
        f"# {TITLE}",
        "",
        f"_Audit date: {date.today().strftime('%d %B %Y')} \u00b7 Model version aura-wesad-20261107-444b41_",
        "",
        "> This report inspects the existing AuraSense build. No application source file, database record or trained artifact was modified.",
        "",
        "## Table of contents",
        "",
    ]
    for block in blocks:
        if block["t"] == "chapter":
            anchor = re.sub(r"[^a-z0-9]+", "-", block["title"].lower()).strip("-")
            lines.append(f"- **{block['num']}** [{block['title']}](#{anchor})")
    lines.append("")
    for block in blocks:
        kind = block["t"]
        if kind == "chapter":
            lines += ["", f"## {block['num']}. {block['title']}", ""]
            if block.get("sub"):
                lines += [f"_{block['sub']}_", ""]
        elif kind == "h2":
            lines += ["", f"### {block['text']}", ""]
        elif kind == "p":
            lines += [block["text"], ""]
        elif kind == "small":
            lines += [f"_{block['text']}_", ""]
        elif kind == "b":
            lines += [f"- {item}" for item in block["items"]] + [""]
        elif kind == "callout":
            lines += [f"> **{block['title']}** \u2014 {block['text']}", ""]
        elif kind == "kv":
            lines += ["| Field | Value |", "| --- | --- |"]
            lines += [f"| {row[0]} | {row[1]} |" for row in block["rows"]]
            lines.append("")
        elif kind == "table":
            head = block["head"]
            lines += ["| " + " | ".join(head) + " |", "| " + " | ".join(["---"] * len(head)) + " |"]
            for row in block["rows"]:
                cells = [str(c).replace("|", "\\|").replace("\n", "<br>") for c in row]
                lines.append("| " + " | ".join(cells) + " |")
            lines.append("")
        elif kind == "flow":
            lines += [f"**{block['title']}**", "", "```mermaid", "flowchart LR"]
            for i, step in enumerate(block["steps"]):
                lines.append(f'  N{i}["{step}"]')
            for i in range(len(block["steps"]) - 1):
                lines.append(f"  N{i} --> N{i+1}")
            lines += ["```", ""]
        elif kind == "arch":
            lines += ["**Architecture**", "", "```mermaid", "flowchart TD",
                      '  UI["React frontend"] --> API["FastAPI /api"]',
                      '  API --> SVC["Services + role/ownership checks"]',
                      '  SVC --> ML["ml/features.py + model.joblib"]',
                      '  SVC --> DB[("SQLite")]',
                      '  SVC --> FS[("uploads / sessions / reports")]', "```", ""]
        elif kind == "bars":
            names = [s[0] for s in block["series"]]
            lines += [f"**{block['title']}**", "",
                      "| Class/model | " + " | ".join(names) + " |",
                      "| --- | " + " | ".join(["---"] * len(names)) + " |"]
            for i, label in enumerate(block["labels"]):
                lines.append("| " + label + " | " + " | ".join(f"{s[1][i]:.1f}" for s in block["series"]) + " |")
            lines.append("")
        elif kind == "pagebreak":
            lines += ["", "---", ""]
    return "\n".join(lines).strip() + "\n"


def main() -> None:
    # Pass 1: no TOC, collect chapter pages.
    first = AuditPDF()
    first.render(BLOCKS, with_toc=False)
    chapters = first.chapters
    toc = [(num, title, page + 1) for num, title, page in chapters]

    # Pass 2: insert one TOC page and shift recorded pages by one.
    final = AuditPDF(toc=toc)
    final.render(BLOCKS, with_toc=True)
    if len(final.chapters) != len(toc) or final.page_no() < 10:
        raise SystemExit("Unexpected chapter count or page count")

    pdf_path = ROOT / "AURASENSE_AUDIT.pdf"
    final.output(str(pdf_path))

    md_path = ROOT / "AURASENSE_AUDIT.md"
    md_path.write_text(build_markdown(BLOCKS), encoding="utf-8")

    print(f"PDF: {pdf_path} ({pdf_path.stat().st_size} bytes, {final.page_no()} pages)")
    print(f"Markdown: {md_path} ({md_path.stat().st_size} bytes)")
    print("Chapters:")
    for num, title, page in final.chapters:
        print(f"  {num:>3}  p{page:>3}  {title}")


if __name__ == "__main__":
    main()
