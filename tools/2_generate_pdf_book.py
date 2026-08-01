from pathlib import Path
import argparse
import json
import csv
import re

ROOT = Path(__file__).resolve().parents[1]
VERSES_JSON = ROOT / "data" / "verses.json"
CHAPTER_TITLES_JSON = ROOT / "data" / "chapter_titles.json"

LANGUAGES = {
    "en": {
        "output_qmd": ROOT / "pdf_book.qmd",
        "output_pdf": "bhagavad-gita-en",
        "cover_tex": "pdf/cover-en.tex",
        "subtitle": "English draft",
        "intro": (
            "The Bhagavad Gita is part of the Mahabharata, Book 6, the Bhishma Parva, "
            "chapters 23–40. This English version was prepared from Google Translate "
            "output and revised using GPT-5.4/5.5/5.6 and Claude Opus 4.8/5.0, along "
            "with some manual editing. The aim was to produce an English translation "
            "that is readable, unbiased, and as literal as possible."
        ),
        "chapter": "Chapter",
        "glossary": "Glossary",
        "forms": "Forms",
        "glossary_csv": ROOT / "data" / "glossary.en.csv",
        "glossary_json": ROOT / "data" / "glossary.json",
        "glossary_groups": ["Concepts", "Social and ritual terms", "Names and epithets"],
        "translation_keys": ["translation_en", "ai_refined_en", "english"],
    },
    "it": {
        "output_qmd": ROOT / "pdf_book_it.qmd",
        "output_pdf": "bhagavad-gita-it",
        "cover_tex": "pdf/cover-it.tex",
        "subtitle": "Traduzione italiana",
        "intro": (
            "La Bhagavad Gita fa parte del Mahabharata, Libro 6, il Bhishma Parva, "
            "capitoli 23-40. Questa versione italiana è stata preparata a partire "
            "dall'output di Google Translate, rivista con GPT-5.4/5.5/5.6 e "
            "Claude-Opus-4.8/5.0, oltre a qualche revisione manuale. L’obiettivo era "
            "produrre una traduzione italiana leggibile, imparziale e il più possibile "
            "letterale."
        ),
        "chapter": "Capitolo",
        "glossary": "Glossario",
        "forms": "Forme",
        "glossary_csv": ROOT / "data" / "glossary.it.csv",
        "glossary_json": ROOT / "data" / "glossary.it.json",
        "glossary_groups": ["Concetti", "Termini sociali e rituali", "Nomi ed epiteti"],
        "translation_keys": ["translation_it", "ai_refined_it", "italian_translation", "it_translation", "traduzione_italiana"],
    },
}

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


def load_verses(language):
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
                "translation": first_nonempty(*(item.get(key) for key in LANGUAGES[language]["translation_keys"])),
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


def load_glossary_csv(path):
    entries = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"id", "term", "group", "definition", "variants"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing columns in {path.name}: {sorted(missing)}")
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


def load_glossary_json(path):
    data = read_json_file(path)
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


def load_glossary(language):
    config = LANGUAGES[language]
    if config["glossary_csv"].exists():
        return load_glossary_csv(config["glossary_csv"])
    if config["glossary_json"].exists():
        return load_glossary_json(config["glossary_json"])
    raise FileNotFoundError(
        f"Missing glossary source for {language}: "
        f"{config['glossary_csv'].name} or {config['glossary_json'].name}"
    )


def render_intro(language):
    return [
        LANGUAGES[language]["intro"],
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


def render_chapters(verses, chapter_titles, language):
    chapters = {}
    for verse in verses:
        chapters.setdefault(verse["chapter"], []).append(verse)

    parts = []
    for chapter in sorted(chapters):
        chapter_label = LANGUAGES[language]["chapter"]
        title = escape_latex(chapter_titles.get(chapter, f"{chapter_label} {chapter}"))
        parts.append(r"\clearpage")
        parts.append(f"# {chapter_label} {chapter} - {title}")
        parts.append("")
        for verse in chapters[chapter]:
            parts.extend(render_verse(verse))
    return parts


def render_glossary(entries, language):
    config = LANGUAGES[language]
    grouped = {group: [] for group in config["glossary_groups"]}
    extra_groups = {}
    for entry in entries:
        group = entry["group"] or config["glossary_groups"][0]
        if group in grouped:
            grouped[group].append(entry)
        else:
            extra_groups.setdefault(group, []).append(entry)

    parts = [r"\clearpage", f"# {config['glossary']}", ""]
    ordered_groups = list(config["glossary_groups"]) + sorted(extra_groups)
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
                line += f" \\textit{{{config['forms']}: {' | '.join(variants)}}}"
            parts.append(line)
        parts.append(r"\end{description}")
        parts.append("")
    return parts


def build_qmd(language):
    config = LANGUAGES[language]
    verses = load_verses(language)
    chapter_titles = load_chapter_titles()
    glossary = load_glossary(language)

    parts = [
        "<!--",
        "GENERATED FILE. DO NOT EDIT DIRECTLY.",
        "",
        "Edit instead:",
        "- data/bhagavadgita_ai_refined.xlsx for verse text",
        f"- {config['glossary_csv'].relative_to(ROOT).as_posix()} for glossary entries",
        "- tools/2_generate_pdf_book.py for PDF generation logic",
        "",
        "Then run:",
        "    python tools\\2_generate_pdf_book.py",
        f"    quarto render {config['output_qmd'].name} --to pdf",
        "-->",
        "",
        "---",
        f'output-file: "{config["output_pdf"]}"',
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
        "      - top=17mm",
        "      - bottom=22mm",
        "      - inner=18mm",
        "      - outer=16mm",
        "      - footskip=9mm",
        "    include-in-header: pdf/pdf-preamble.tex",
        f'    include-before-body: {config["cover_tex"]}',
        "---",
        "",
    ]
    parts.extend(render_intro(language))
    parts.extend(render_chapters(verses, chapter_titles, language))
    parts.extend(render_glossary(glossary, language))
    return "\n".join(parts).rstrip() + "\n"


def main():
    parser = argparse.ArgumentParser(description="Generate the PDF source files.")
    parser.add_argument("--lang", choices=LANGUAGES, help="Generate only one language.")
    args = parser.parse_args()
    languages = [args.lang] if args.lang else LANGUAGES
    for language in languages:
        output = LANGUAGES[language]["output_qmd"]
        output.write_text(build_qmd(language), encoding="utf-8")
        print(f"Wrote {output}")


if __name__ == "__main__":
    main()
