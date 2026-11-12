"""PDF -> clean text lines. Drops running headers, page numbers, footnotes and superscript markers."""

from collections import Counter
from dataclasses import dataclass

import pymupdf

HEADER_BAND = 0.1  # top fraction of each page (after the first) holding running headers
SMALL_FONT_RATIO = 0.9  # spans smaller than this x body size are footnotes or superscripts
SUPERSCRIPT_FLAG = 1
SCANNED_CHARS_PER_PAGE = 200


@dataclass(frozen=True)
class Line:
    text: str
    block: int  # global block number; a new block usually means a new paragraph


@dataclass(frozen=True)
class PdfText:
    lines: list[Line]
    page_count: int
    chars_per_page: float

    @property
    def looks_scanned(self) -> bool:
        return self.chars_per_page < SCANNED_CHARS_PER_PAGE


def _body_font_size(pages: list[dict]) -> float:
    sizes: Counter[float] = Counter()
    for page in pages:
        for block in page["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    sizes[round(span["size"], 1)] += len(span["text"].strip())
    return sizes.most_common(1)[0][0] if sizes else 0.0


def extract_pdf(data: bytes) -> PdfText:
    with pymupdf.open(stream=data, filetype="pdf") as doc:
        pages = [page.get_text("dict") for page in doc]
        heights = [page.rect.height for page in doc]

    body_size = _body_font_size(pages)
    lines: list[Line] = []
    total_chars = 0
    block_no = 0
    for page_no, (page, height) in enumerate(zip(pages, heights, strict=True)):
        for block in page["blocks"]:
            block_no += 1
            for line in block.get("lines", []):
                if page_no > 0 and line["bbox"][1] < height * HEADER_BAND:
                    continue
                text = "".join(
                    span["text"]
                    for span in line["spans"]
                    if span["size"] >= body_size * SMALL_FONT_RATIO and not span["flags"] & SUPERSCRIPT_FLAG
                )
                text = " ".join(text.replace("\x08", " ").split())
                if text:
                    total_chars += len(text)
                    lines.append(Line(text, block_no))
    page_count = len(pages)
    return PdfText(lines=lines, page_count=page_count, chars_per_page=total_chars / max(page_count, 1))
