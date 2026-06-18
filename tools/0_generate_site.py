from pathlib import Path
from openpyxl import load_workbook
from collections import defaultdict
import html
import json
import re
import csv

ROOT = Path(__file__).resolve().parents[1]
SRC_XLSX = ROOT / 'data' / 'bhagavadgita_ai_refined.xlsx'
OUT = ROOT

GENERATED_FILE_NOTE = '''<!--
GENERATED FILE. DO NOT EDIT DIRECTLY.

Edit instead:
- data/glossary.csv for glossary content
- data/bhagavadgita_ai_refined.xlsx for verses/translations
- tools/0_generate_site.py for generation logic
- styles.css for visual style

Then run:
    run_all.bat
-->
'''

GLOSSARY_CSV = ROOT / 'data' / 'glossary.csv'


def load_glossary(path=GLOSSARY_CSV):
    entries = []
    if not path.exists():
        raise FileNotFoundError(
            f'Missing glossary file: {path}. '
            'Create data/glossary.csv or restore it from the patch.'
        )
    with open(path, encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        required = {'id', 'term', 'group', 'definition', 'variants'}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f'Missing columns in glossary.csv: {sorted(missing)}')
        for row in reader:
            entries.append({
                'id': row['id'].strip(),
                'term': row['term'].strip(),
                'group': row['group'].strip(),
                'definition': row['definition'].strip(),
                'variants': [
                    v.strip()
                    for v in row['variants'].split('|')
                    if v.strip()
                ],
            })
    return entries


GLOSSARY = load_glossary()

SPEAKER_MAP = {
    'धृतराष्ट्र': '(Dhritarashtra)',
    'सञ्जय': '(Sanjaya)',
    'अर्जुन': '(Arjuna)',
    'श्रीभगवान्': '(Shri Bhagavan Krishna)',
}


LETTER = "A-Za-z0-9ĀāĪīŪūṚṛṜṝḶḷṂṃḤḥÑñṄṅṆṇṬṭḌḍŚśṢṣÇçḸḹẎẏ"


def as_text(v):
    return '' if v is None else str(v).strip()


def esc(v):
    return html.escape(as_text(v), quote=True)


def speaker_display(v):
    text = as_text(v)
    return SPEAKER_MAP.get(text, text)


def glossary_payload():
    payload = []
    for item in GLOSSARY:
        clean = dict(item)
        clean['variants'] = sorted(set(clean['variants']))
        payload.append(clean)
    return payload


def build_glossary_regex():
    variant_map = []
    for item in GLOSSARY:
        for variant in item['variants']:
            variant_map.append((variant, item))
    variant_map.sort(key=lambda x: len(x[0]), reverse=True)
    pattern = '|'.join(re.escape(v) for v, _ in variant_map)
    regex = re.compile(rf'(?<![{LETTER}])({pattern})(?![{LETTER}])', flags=re.IGNORECASE)
    lookup = {v.casefold(): item for v, item in variant_map}
    return regex, lookup


GLOSSARY_RE, GLOSSARY_LOOKUP = build_glossary_regex()


CHAPTER_TITLES_ROMAN = {
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


def annotate_text(text):
    text = as_text(text)
    if not text:
        return ''
    out = []
    pos = 0
    for match in GLOSSARY_RE.finditer(text):
        out.append(html.escape(text[pos:match.start()], quote=True))
        token = match.group(0)
        item = GLOSSARY_LOOKUP.get(token.casefold())
        if item is None:
            out.append(html.escape(token, quote=True))
        else:
            label = f"{item['term']}: {item['definition']}"
            out.append(
                '<span class="glossary-term" tabindex="0" '
                f'data-gloss="{html.escape(label, quote=True)}" '
                f'aria-label="{html.escape(label, quote=True)}" '
                f'title="{html.escape(label, quote=True)}" '
                f'data-glossary-id="{html.escape(item["id"], quote=True)}">'
                f'{html.escape(token, quote=True)}</span>'
            )
        pos = match.end()
    out.append(html.escape(text[pos:], quote=True))
    return ''.join(out)


def html_lines(v, annotate=False):
    if annotate:
        return '<br>\n'.join(annotate_text(line) for line in as_text(v).splitlines())
    return '<br>\n'.join(esc(v).splitlines())


def read_verses(path):
    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb['Sheet1']
    headers = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    idx = {h: i for i, h in enumerate(headers)}
    required = ['chapter', 'chapter_title_sanskrit', 'verse', 'reference', 'speaker', 'sanskrit_sloka', 'ai_refined_en']
    missing = [c for c in required if c not in idx]
    if missing:
        raise ValueError(f'Missing required columns: {missing}')
    it_candidates = ['ai_refined_it', 'italian_translation', 'it_translation', 'traduzione_italiana']
    it_col = next((c for c in it_candidates if c in idx), None)
    verses = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        ch = row[idx['chapter']]
        verse = row[idx['verse']]
        if ch is None or verse is None:
            continue
        item = {
            'chapter': int(ch),
            'chapter_title_sanskrit': as_text(row[idx['chapter_title_sanskrit']]),
            'verse': int(verse),
            'reference': f"{int(ch)}.{int(verse)}",
            'speaker': speaker_display(row[idx['speaker']]),
            'sanskrit_sloka': as_text(row[idx['sanskrit_sloka']]),
            'translation_en': as_text(row[idx['ai_refined_en']]),
        }
        if it_col:
            item['translation_it'] = as_text(row[idx[it_col]])
        verses.append(item)
    return verses


def write_quarto_yml(chapters):
    chapter_menu = '\n'.join(
        f'          - text: "Chapter {ch}"\n            href: chapters/chapter-{ch:02d}.qmd'
        for ch in sorted(chapters)
    )
    sidebar_chapters = '\n'.join(
        f'          - text: "Chapter {ch}"\n            href: chapters/chapter-{ch:02d}.qmd'
        for ch in sorted(chapters)
    )
    quarto_yml = f'''project:
  type: website
  output-dir: docs
  resources:
    - .nojekyll

website:
  title: "Bhagavad Gita"
  search: false
  page-navigation: true
  navbar:
    left:
      - text: "Chapters"
        menu:
{chapter_menu}
      - text: "Glossary"
        href: glossary.qmd
  sidebar:
    style: docked
    collapse-level: 1
    contents:
      - text: "Home"
        href: index.qmd
      - section: "English translation"
        contents:
{sidebar_chapters}
      - text: "Glossary"
        href: glossary.qmd

format:
  html:
    theme: cosmo
    css: styles.css
    toc: false
    smooth-scroll: true
    anchor-sections: false
    link-external-newwindow: true
'''
    (OUT / '_quarto.yml').write_text(quarto_yml, encoding='utf-8')


def write_index(chapters):
    cards = []
    for ch in sorted(chapters):
        count = len(chapters[ch])
        verse_word = 'verse' if count == 1 else 'verses'
        cards.append(
            f'<a class="chapter-card" href="chapters/chapter-{ch:02d}.html">'
            f'<span class="chapter-number">Chapter {ch}</span>'
            f'<span class="chapter-count">{count} {verse_word}</span></a>'
        )
    index_qmd = '''---
title: "Bhagavad Gita"
---

<div class="site-note">
The Bhagavad Gita is part of the Mahabharata, Book 6, Bhishma Parva, chapters 23-40. This English draft was prepared from Google Translate output and revised with GPT-5.4 mini.
</div>

<div class="site-usage">
Lightly marked Sanskrit terms show a short gloss on hover or tap.
</div>

<div class="site-download">
<a href="bhagavad-gita.pdf">Download PDF</a>
</div>

<div class="chapter-grid">
''' + '\n'.join(cards) + '''
</div>
'''
    (OUT / 'index.qmd').write_text(index_qmd, encoding='utf-8')


def write_glossary():
    groups = defaultdict(list)
    for item in GLOSSARY:
        groups[item['group']].append(item)
    parts = [
        '---',
        'title: "Glossary"',
        '---',
        '',
        GENERATED_FILE_NOTE,
        '',
        '<div class="site-note glossary-note">',
        'A compact guide to transliterated Sanskrit terms and recurring names used in the English rendering.',
        '</div>',
        '',
    ]
    for group in ['Concepts', 'Social and ritual terms', 'Names and epithets']:
        if group not in groups:
            continue
        parts += [f'## {group}', '', '<div class="glossary-list">']
        for item in sorted(groups[group], key=lambda x: x['term'].casefold()):
            variants = ', '.join(sorted(set(item['variants']), key=lambda v: v.casefold()))
            parts += [
                f'<section class="glossary-entry" id="glossary-{esc(item["id"])}">',
                f'<h3>{esc(item["term"])}</h3>',
                f'<p>{esc(item["definition"])}</p>',
                f'<p class="glossary-variants">Forms in the text: {esc(variants)}</p>',
                '</section>',
            ]
        parts += ['</div>', '']
    (OUT / 'glossary.qmd').write_text('\n'.join(parts), encoding='utf-8')


def write_chapters(chapters):
    chapter_dir = OUT / 'chapters'
    chapter_dir.mkdir(exist_ok=True)
    for old in chapter_dir.glob('chapter-*.qmd'):
        old.unlink()

    sorted_ch = sorted(chapters)
    for pos, ch in enumerate(sorted_ch):
        prev_ch = sorted_ch[pos - 1] if pos > 0 else None
        next_ch = sorted_ch[pos + 1] if pos < len(sorted_ch) - 1 else None
        items = chapters[ch]
        title_roman = CHAPTER_TITLES_ROMAN.get(ch, f'Chapter {ch}')
        title_sanskrit = items[0]['chapter_title_sanskrit'] if items else ''
        prev_link = f'<a href="chapter-{prev_ch:02d}.html">Previous chapter</a>' if prev_ch else '<span></span>'
        next_link = f'<a href="chapter-{next_ch:02d}.html">Next chapter</a>' if next_ch else '<span></span>'
        parts = [
            '---',
            f'title: "Chapter {ch} - {title_roman}"',
            '---',
            '',
        ]
        if title_sanskrit:
            parts += [
                f'<div class="chapter-title-sanskrit">{html_lines(title_sanskrit)}</div>',
                '',
            ]
        parts += [
            f'<nav class="chapter-nav">{prev_link}{next_link}</nav>',
            '',
            '<div class="verse-list">',
        ]
        for v in items:
            ref = esc(v['reference'])
            anchor = f'v-{v["chapter"]}-{v["verse"]}'
            parts += [
                f'<article class="verse" id="{anchor}" data-reference="{ref}">',
                '<header class="verse-head">',
                f'<a class="ref" href="#{anchor}">{ref}</a>',
                f'<span class="speaker">{esc(v["speaker"])}</span>' if v['speaker'] else '',
                '</header>',
                f'<p class="translation translation-en" data-lang="en">{html_lines(v["translation_en"], annotate=True)}</p>',
            ]
            if v.get('translation_it'):
                parts += [
                    '<details class="translation-it-block">',
                    '<summary>Italiano</summary>',
                    f'<p class="translation translation-it" data-lang="it">{html_lines(v["translation_it"], annotate=True)}</p>',
                    '</details>',
                ]
            if v['sanskrit_sloka']:
                parts += [
                    '<details class="sanskrit">',
                    '<summary>Sanskrit</summary>',
                    f'<div class="sanskrit-text">{html_lines(v["sanskrit_sloka"])}</div>',
                    '</details>',
                ]
            parts += ['</article>', '']
        parts += ['</div>', '']
        (chapter_dir / f'chapter-{ch:02d}.qmd').write_text('\n'.join(parts), encoding='utf-8')


def main():
    verses = read_verses(SRC_XLSX)
    chapters = defaultdict(list)
    for v in verses:
        chapters[v['chapter']].append(v)
    for ch in chapters:
        chapters[ch].sort(key=lambda x: x['verse'])

    (OUT / 'data').mkdir(exist_ok=True)
    with open(OUT / 'data' / 'verses.json', 'w', encoding='utf-8') as f:
        json.dump(verses, f, ensure_ascii=False, indent=2)
    with open(OUT / 'data' / 'glossary.json', 'w', encoding='utf-8') as f:
        json.dump(glossary_payload(), f, ensure_ascii=False, indent=2)

    write_quarto_yml(chapters)
    write_index(chapters)
    write_glossary()
    write_chapters(chapters)

    print(f'Generated {len(verses)} verses in {len(chapters)} chapters.')
    print(f'Glossary entries: {len(GLOSSARY)}')


if __name__ == '__main__':
    main()
