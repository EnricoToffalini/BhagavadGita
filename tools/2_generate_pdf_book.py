from pathlib import Path
import json
import csv
import re

ROOT = Path(__file__).resolve().parents[1]
VERSES_JSON = ROOT / "data" / "verses.json"
GLOSSARY_CSV = ROOT / "data" / "glossary.csv"
GLOSSARY_JSON = ROOT / "data" / "glossary.json"
CHAPTER_TITLES_JSON = ROOT / "data" / "chapter_titles.json"
OUT_QMD = ROOT / "pdf_book.qmd"

DEFAULT_CHAPTER_TITLES = {
    1: "Arjuna Vishada Yoga",
    2: "Sankhya Yoga",
    3: "Karma Yoga",
    4: "Jnana-Karma-Sannyasa Yoga",
    5: "Sannyasa Yoga",
    6: "Atma-Samyama Yoga",
    7: "Jnana-Vijnana Yoga",
    8: "Akshara-Brahma Yoga",
    9: "Raja-Vidya Raja-Guhya Yoga",
    10: "Vibhuti Yoga",
    11: "Vishvarupa-Darshana Yoga",
    12: "Bhakti Yoga",
    13: "Kshetra-Kshetrajna Vibhaga Yoga",
    14: "Guna-Traya Vibhaga Yoga",
    15: "Purushottama Yoga",
    16: "Daivasura-Sampad Vibhaga Yoga",
    17: "Shraddha-Traya Vibhaga Yoga",
    18: "Moksha-Sannyasa Yoga",
}

GLOSSARY_GROUPS = [
    "Concepts",
    "Social and ritual terms",
    "Names and epithets",
]

LATEX_REPLACEMENTS = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def read_json_file(path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def as_text(value):
    return "" if value is None else str(value).strip()


def first_nonempty(*values):
    for value in values:
        text = as_text(value)
        if text:
            return text
    return ""


def escape_latex(text):
    text = as_text(text)
    if not text:
        return ""
    return "".join(LATEX_REPLACEMENTS.get(ch, ch) for ch in text)


def normalize_paragraphs(text):
    text = as_text(text)
    if not text:
        return []
    parts = []
    for paragraph in re.split(r"\n\s*\n", text.strip()):
        lines = [line.strip() for line in paragraph.splitlines() if line.strip()]
        if lines:
            parts.append(" ".join(lines))
    return parts


def load_verses():
    data = read_json_file(VERSES_JSON)
    verses = []
    for item in data:
        chapter = item.get("chapter")
        verse = item.get("verse")
        if chapter is None or verse is None:
            continue
        verses.append(
            {
                "chapter": int(chapter),
                "verse": int(verse),
                "reference": f"{int(chapter)}.{int(verse)}",
                "speaker": as_text(item.get("speaker")),
                "translation": first_nonempty(
                    item.get("translation_en"),
                    item.get("ai_refined_en"),
                    item.get("english"),
                ),
            }
        )
    verses.sort(key=lambda item: (item["chapter"], item["verse"]))
    return verses


def load_chapter_titles():
    titles = dict(DEFAULT_CHAPTER_TITLES)
    if not CHAPTER_TITLES_JSON.exists():
        return titles

    try:
        data = read_json_file(CHAPTER_TITLES_JSON)
    except Exception:
        return titles

    if isinstance(data, dict):
        items = data.items()
    else:
        items = []
        for entry in data:
            if isinstance(entry, dict):
                items.append((entry.get("chapter"), entry))

    for chapter_key, entry in items:
        try:
            chapter = int(chapter_key)
        except (TypeError, ValueError):
            continue
        if isinstance(entry, dict):
            title = first_nonempty(entry.get("title_roman"), entry.get("title"), entry.get("name"))
        else:
            title = as_text(entry)
        if title:
            titles[chapter] = title
    return titles


def load_glossary_csv():
    entries = []
    with GLOSSARY_CSV.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"id", "term", "group", "definition", "variants"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing columns in glossary.csv: {sorted(missing)}")
        for row in reader:
            variants = [piece.strip() for piece in row["variants"].split("|") if piece.strip()]
            entries.append(
                {
                    "id": as_text(row["id"]),
                    "term": as_text(row["term"]),
                    "group": as_text(row["group"]),
                    "definition": as_text(row["definition"]),
                    "variants": variants,
                }
            )
    return entries


def normalize_variants(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [as_text(item) for item in value if as_text(item)]
    if isinstance(value, str):
        return [piece.strip() for piece in value.split("|") if piece.strip()]
    text = as_text(value)
    return [text] if text else []


def load_glossary_json():
    data = read_json_file(GLOSSARY_JSON)
    entries = []
    for item in data:
        if not isinstance(item, dict):
            continue
        entries.append(
            {
                "id": as_text(item.get("id")),
                "term": as_text(item.get("term")),
                "group": as_text(item.get("group")),
                "definition": as_text(item.get("definition")),
                "variants": normalize_variants(item.get("variants")),
            }
        )
    return entries


def load_glossary():
    if GLOSSARY_CSV.exists():
        return load_glossary_csv()
    if GLOSSARY_JSON.exists():
        return load_glossary_json()
    raise FileNotFoundError("Missing glossary source: data/glossary.csv or data/glossary.json")


def render_intro():
    return [
        "The Bhagavad Gita is part of the Mahabharata, Book 6, Bhishma Parva, chapters 23-40. This English draft was prepared from Google Translate output and revised with GPT-5.4 mini.",
        "",
        r"\clearpage",
        "",
    ]


def render_verse(verse):
    speaker = escape_latex(verse["speaker"])
    reference = escape_latex(verse["reference"])
    lines = [
        r"\begingroup",
        r"\setlength{\parindent}{0pt}",
    ]
    if speaker:
        lines.append(f"\\textbf{{{reference}}} \\textit{{{speaker}}}\\par")
    else:
        lines.append(f"\\textbf{{{reference}}}\\par")

    paragraphs = normalize_paragraphs(verse["translation"])
    for index, paragraph in enumerate(paragraphs):
        lines.append(escape_latex(paragraph))
        if index < len(paragraphs) - 1:
            lines.append(r"\par")

    lines.append(r"\par\endgroup")
    lines.append(r"\vspace{0.42em}")
    lines.append("")
    return lines


def render_chapters(verses, chapter_titles):
    chapters = {}
    for verse in verses:
        chapters.setdefault(verse["chapter"], []).append(verse)

    parts = []
    for chapter in sorted(chapters):
        title = escape_latex(chapter_titles.get(chapter, f"Chapter {chapter}"))
        parts.append(r"\clearpage")
        parts.append(f"# Chapter {chapter} - {title}")
        parts.append("")
        for verse in chapters[chapter]:
            parts.extend(render_verse(verse))
    return parts


def render_glossary(entries):
    grouped = {group: [] for group in GLOSSARY_GROUPS}
    extra_groups = {}
    for entry in entries:
        group = entry["group"] or "Concepts"
        if group in grouped:
            grouped[group].append(entry)
        else:
            extra_groups.setdefault(group, []).append(entry)

    parts = [r"\clearpage", "# Glossary", ""]
    ordered_groups = list(GLOSSARY_GROUPS) + sorted(extra_groups)
    for group in ordered_groups:
        items = grouped.get(group, []) or extra_groups.get(group, [])
        if not items:
            continue
        parts.append(f"## {group}")
        parts.append("")
        parts.append(r"\begin{description}")
        for item in sorted(items, key=lambda value: value["term"].casefold()):
            term = escape_latex(item["term"])
            definition = escape_latex(item["definition"])
            line = f"\\item[{term}] {definition}"
            variants = [escape_latex(value) for value in item.get("variants", []) if as_text(value)]
            if variants:
                line += f" \\textit{{Forms: {' | '.join(variants)}}}"
            parts.append(line)
        parts.append(r"\end{description}")
        parts.append("")
    return parts


def build_qmd():
    verses = load_verses()
    chapter_titles = load_chapter_titles()
    glossary = load_glossary()

    parts = [
        "<!--",
        "GENERATED FILE. DO NOT EDIT DIRECTLY.",
        "",
        "Edit instead:",
        "- data/bhagavadgita_ai_refined.xlsx for verse text",
        "- data/glossary.csv for glossary entries",
        "- tools/2_generate_pdf_book.py for PDF generation logic",
        "",
        "Then run:",
        "    python tools\\2_generate_pdf_book.py",
        "    quarto render pdf_book.qmd --to pdf",
        "-->",
        "",
        "---",
        'title: "Bhagavad Gita"',
        'subtitle: "English draft"',
        'output-file: "bhagavad-gita"',
        "format:",
        "  pdf:",
        "    documentclass: scrartcl",
        "    pdf-engine: xelatex",
        "    papersize: a5",
        "    fontsize: 10.5pt",
        "    toc: true",
        "    toc-depth: 1",
        "    number-sections: false",
        "    colorlinks: true",
        "    geometry:",
        "      - top=15mm",
        "      - bottom=17mm",
        "      - inner=16mm",
        "      - outer=14mm",
        "    include-in-header: pdf/pdf-preamble.tex",
        "---",
        "",
    ]
    parts.extend(render_intro())
    parts.extend(render_chapters(verses, chapter_titles))
    parts.extend(render_glossary(glossary))
    return "\n".join(parts).rstrip() + "\n"


def main():
    OUT_QMD.write_text(build_qmd(), encoding="utf-8")
    print(f"Wrote {OUT_QMD}")


if __name__ == "__main__":
    main()
