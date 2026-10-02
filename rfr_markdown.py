"""Small Markdown prose reader and source mapping, using only the stdlib."""

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class Paragraph:
    id: str
    heading: str
    text: str
    start_line: int
    end_line: int


def read_paragraphs(text: str) -> list[Paragraph]:
    """Group prose under headings, excluding fenced code (not a full AST)."""
    lines = text.splitlines()
    paragraphs = []
    headings = []
    start = None
    fence = None

    def flush(end):
        nonlocal start
        if start is not None:
            paragraphs.append(Paragraph(
                f"p{len(paragraphs) + 1}", " / ".join(h[1] for h in headings),
                "\n".join(lines[start:end]), start, end - 1,
            ))
            start = None

    def heading(level, label):
        while headings and headings[-1][0] >= level:
            headings.pop()
        headings.append((level, label))

    i = 0
    while i < len(lines):
        line = lines[i]
        if fence:
            char, length = fence
            if re.fullmatch(r" {0,3}" + re.escape(char) + "{" + str(length) + r",}[ \t]*", line):
                fence = None
            i += 1
            continue
        opening = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if opening and not (opening[1][0] == "`" and "`" in opening[2]):
            flush(i)
            fence = (opening[1][0], len(opening[1]))
            i += 1
            continue
        atx = re.match(r"^ {0,3}(#{1,6})(?:[ \t]+(.*?)|[ \t]*)$", line)
        if atx:
            flush(i)
            label = re.sub(r"[ \t]+#+[ \t]*$", "", atx[2] or "").strip()
            heading(len(atx[1]), label)
            i += 1
            continue
        underline = re.fullmatch(r" {0,3}(=+|-+)[ \t]*", lines[i + 1]) if i + 1 < len(lines) else None
        if line.strip() and underline:
            label_start = start if start is not None else i
            label = " ".join(l.strip() for l in lines[label_start:i + 1])
            start = None
            heading(1 if underline[1][0] == "=" else 2, label)
            i += 2
            continue
        if not line.strip():
            flush(i)
        elif start is None:
            start = i
        i += 1
    flush(len(lines))
    return paragraphs


def paragraph_range(text: str, paragraph: Paragraph) -> dict:
    last_line = text.splitlines()[paragraph.end_line]
    return {
        "start": {"line": paragraph.start_line, "character": 0},
        "end": {"line": paragraph.end_line, "character": len(last_line.encode("utf-16-le")) // 2},
    }
