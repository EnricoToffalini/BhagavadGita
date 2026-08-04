"""Validate rendered HTML and write a canonical-only sitemap.

Quarto creates the first version of ``docs/sitemap.xml``.  Its sitemap URLs for
index pages include ``index.html``, while the canonical links use directory URLs.
This post-render step makes the two signals agree and fails the website build if
an indexable HTML page is missing essential metadata or contains a broken local
link.  It uses only the Python standard library.
"""

from collections import defaultdict
from html.parser import HTMLParser
import os
from pathlib import Path
import posixpath
import re
from urllib.parse import unquote, urljoin, urlsplit
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SITE_URL = 'https://enricotoffalini.github.io/BhagavadGita/'
SITEMAP_NS = 'http://www.sitemaps.org/schemas/sitemap/0.9'


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.canonicals = []
        self.description = ''
        self.robots = []
        self.links = []
        self._in_title = False
        self._title_parts = []

    @property
    def title(self):
        return ''.join(self._title_parts).strip()

    def handle_starttag(self, tag, attrs):
        values = {name.lower(): (value or '') for name, value in attrs}
        tag = tag.lower()
        if tag == 'title':
            self._in_title = True
        elif tag == 'link':
            rel = {part.lower() for part in values.get('rel', '').split()}
            if 'canonical' in rel and values.get('href'):
                self.canonicals.append(values['href'].strip())
        elif tag == 'meta':
            name = values.get('name', '').lower()
            if name == 'description':
                self.description = values.get('content', '').strip()
            elif name in {'robots', 'googlebot'}:
                self.robots.append(values.get('content', ''))
        elif tag == 'a' and values.get('href'):
            self.links.append(values['href'].strip())

    def handle_endtag(self, tag):
        if tag.lower() == 'title':
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self._title_parts.append(data)


def expected_canonical(relative_path):
    page = relative_path.as_posix()
    if page == 'index.html':
        public_path = ''
    elif page.endswith('/index.html'):
        public_path = page[:-len('index.html')]
    else:
        public_path = page
    return urljoin(SITE_URL, public_path)


def parse_page(path):
    parser = PageParser()
    parser.feed(path.read_text(encoding='utf-8'))
    parser.close()
    return parser


def local_link_target(source_relative, href):
    """Return a site-relative target for an internal link, or None if external."""
    parsed = urlsplit(href)
    site = urlsplit(SITE_URL)

    if parsed.scheme or parsed.netloc:
        if parsed.scheme not in {'http', 'https'} or parsed.netloc != site.netloc:
            return None
        if not parsed.path.startswith(site.path):
            return None
        target = unquote(parsed.path[len(site.path):])
    elif parsed.path.startswith('/'):
        if not parsed.path.startswith(site.path):
            raise ValueError(f'root-absolute URL omits the project path: {href}')
        target = unquote(parsed.path[len(site.path):])
    else:
        if not parsed.path:
            return None
        target = posixpath.normpath(
            posixpath.join(source_relative.parent.as_posix(), unquote(parsed.path))
        )

    if target.endswith('/'):
        target += 'index.html'
    if target in {'', '.'}:
        target = 'index.html'
    if target == '..' or target.startswith('../'):
        raise ValueError(f'local link escapes the published site: {href}')
    return target


def main():
    # Quarto also invokes project hooks for the two later single-file PDF
    # renders in run.bat.  Only finalize after a complete website render; allow
    # direct invocation (where the variable is absent) for maintenance/testing.
    render_all = os.getenv('QUARTO_PROJECT_RENDER_ALL')
    if render_all is not None and render_all != '1':
        print('SEO finalization skipped for an incremental/single-file render.')
        return

    output_setting = os.getenv('QUARTO_PROJECT_OUTPUT_DIR', 'docs')
    output_dir = Path(output_setting)
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    if not output_dir.is_dir():
        raise SystemExit(f'SEO finalization failed: output directory not found: {output_dir}')

    all_files = {
        path.relative_to(output_dir).as_posix()
        for path in output_dir.rglob('*')
        if path.is_file()
    }
    html_files = [
        path for path in output_dir.rglob('*.html')
        if 'site_libs' not in path.relative_to(output_dir).parts
        and path.name != '404.html'
    ]

    pages = []
    errors = []
    seen_canonical = {}
    titles = defaultdict(list)
    descriptions = defaultdict(list)

    for path in sorted(html_files):
        relative = path.relative_to(output_dir)
        page = parse_page(path)
        robots_tokens = {
            token for value in page.robots
            for token in re.split(r'[\s,]+', value.lower()) if token
        }
        if 'noindex' in robots_tokens:
            continue

        label = relative.as_posix()
        if len(page.canonicals) != 1:
            errors.append(f'{label}: expected exactly one canonical, found {len(page.canonicals)}')
            continue
        canonical = page.canonicals[0]
        expected = expected_canonical(relative)
        if canonical != expected:
            errors.append(f'{label}: canonical {canonical!r}, expected {expected!r}')
        if canonical in seen_canonical:
            errors.append(
                f'{label}: canonical duplicates {seen_canonical[canonical]}: {canonical}'
            )
        else:
            seen_canonical[canonical] = label
        if not page.title:
            errors.append(f'{label}: missing <title>')
        else:
            titles[page.title].append(label)
        if not page.description:
            errors.append(f'{label}: missing meta description')
        else:
            descriptions[page.description].append(label)

        for href in page.links:
            try:
                target = local_link_target(relative, href)
            except ValueError as exc:
                errors.append(f'{label}: {exc}')
                continue
            if target is not None and target not in all_files:
                errors.append(f'{label}: broken local link {href!r} -> {target!r}')

        pages.append((relative, canonical))

    for title, labels in titles.items():
        if len(labels) > 1:
            errors.append(f'duplicate title {title!r}: {", ".join(labels)}')
    for description, labels in descriptions.items():
        if len(labels) > 1:
            errors.append(
                f'duplicate meta description {description!r}: {", ".join(labels)}'
            )

    if errors:
        details = '\n'.join(f'  - {error}' for error in errors)
        raise SystemExit(f'SEO finalization failed:\n{details}')
    if not pages:
        raise SystemExit('SEO finalization failed: no indexable HTML pages found.')

    ET.register_namespace('', SITEMAP_NS)
    urlset = ET.Element(ET.QName(SITEMAP_NS, 'urlset'))
    for _, canonical in sorted(pages, key=lambda item: item[0].as_posix()):
        url = ET.SubElement(urlset, ET.QName(SITEMAP_NS, 'url'))
        ET.SubElement(url, ET.QName(SITEMAP_NS, 'loc')).text = canonical
    tree = ET.ElementTree(urlset)
    ET.indent(tree, space='  ')
    tree.write(
        output_dir / 'sitemap.xml', encoding='utf-8', xml_declaration=True
    )
    print(f'SEO finalization: validated {len(pages)} pages and wrote sitemap.xml.')


if __name__ == '__main__':
    main()
