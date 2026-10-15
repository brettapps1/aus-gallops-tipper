#!/usr/bin/env python3
"""Build AU AI Compliance Playbook — PDF + EPUB + flipbook."""
import os, re, sys, glob, tempfile
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (Paragraph, Spacer, PageBreak, BaseDocTemplate,
                                PageTemplate, Frame, Preformatted, Table,
                                TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

PRIMARY = HexColor('#0E4D2E')
ACCENT = HexColor('#C88A00')
DARK = HexColor('#1e293b')
GRAY = HexColor('#64748b')
LIGHT = HexColor('#f8fafc')

BOOK = {
    'src': 'book/au-ai-compliance-playbook',
    'out': 'digital_product_workforce/outputs/prod-fairdinkum-compliance/build',
    'title': 'AU AI Compliance Playbook',
    'subtitle': 'Privacy Act 1988 for Australian Small Business',
    'prod': 'FDP-COMP-001',
}

_EPUB_CSS = """\
body { font-family: Georgia, "Times New Roman", serif; line-height: 1.5;
       margin: 0 5%; color: #1e293b; }
h1 { color: #0E4D2E; font-size: 1.5em; margin: 1.2em 0 0.6em; }
h2 { color: #0E4D2E; font-size: 1.2em; margin: 1.4em 0 0.5em;
     border-top: 2px solid #C88A00; padding-top: 0.5em; }
h3 { color: #475569; font-size: 1.05em; margin: 1.1em 0 0.4em; }
/* Google Play Books reflowable EPUBs reject justified text. */
p { margin: 0 0 0.85em; text-align: left; }
hr { border: none; border-top: 1px solid #cbd5e1; margin: 1.6em 0; }
ul, ol { margin: 0 0 0.9em; padding-left: 1.4em; }
li { margin-bottom: 0.35em; }
blockquote { border-left: 3px solid #C88A00; margin: 1em 0; padding: 0.5em 1em;
             color: #475569; font-style: italic; background: #f8fafc; }
code { font-family: "Courier New", monospace; font-size: 0.88em;
       background: #f1f5f9; padding: 0 0.15em; }
pre { background: #f8fafc; border: 1px solid #cbd5e1; border-left: 3px solid #0E4D2E;
      padding: 0.7em; margin: 1em 0; white-space: pre-wrap; word-wrap: break-word; }
pre code { background: none; padding: 0; font-size: 0.8em; }
table { border-collapse: collapse; width: 100%; margin: 1em 0; font-size: 0.92em; }
th, td { border: 1px solid #cbd5e1; padding: 0.4em 0.5em; text-align: left;
         vertical-align: top; }
th { background: #0E4D2E; color: #ffffff; }
tr:nth-child(even) td { background: #f8fafc; }
a { color: #0E4D2E; }
"""


def styles():
    base = getSampleStyleSheet()
    return {
        'cover_title': ParagraphStyle('CT', parent=base['Title'], fontSize=34, leading=40,
                                      textColor=PRIMARY, alignment=TA_CENTER, fontName='Helvetica-Bold', spaceAfter=12),
        'cover_sub': ParagraphStyle('CS', parent=base['Normal'], fontSize=14, leading=20,
                                    textColor=GRAY, alignment=TA_CENTER, spaceAfter=6),
        'brand': ParagraphStyle('BR', parent=base['Normal'], fontSize=11, leading=15,
                                textColor=ACCENT, alignment=TA_CENTER, fontName='Helvetica-Bold', spaceBefore=24),
        'h1': ParagraphStyle('H1', parent=base['Heading1'], fontSize=22, leading=28,
                             textColor=PRIMARY, fontName='Helvetica-Bold', spaceBefore=0, spaceAfter=10, keepWithNext=True),
        'h2': ParagraphStyle('H2', parent=base['Heading2'], fontSize=15, leading=21,
                             textColor=DARK, fontName='Helvetica-Bold', spaceBefore=16, spaceAfter=6, keepWithNext=True),
        'h3': ParagraphStyle('H3', parent=base['Heading3'], fontSize=12, leading=17,
                             textColor=GRAY, fontName='Helvetica-BoldOblique', spaceBefore=12, spaceAfter=4),
        'body': ParagraphStyle('BO', parent=base['Normal'], fontSize=10.5, leading=16,
                               textColor=DARK, alignment=TA_JUSTIFY, spaceAfter=7),
        'bullet': ParagraphStyle('BU', parent=base['Normal'], fontSize=10.5, leading=16,
                                 textColor=DARK, leftIndent=18, spaceAfter=4),
        'quote': ParagraphStyle('QU', parent=base['Normal'], fontSize=10.5, leading=16,
                                textColor=GRAY, leftIndent=16, spaceAfter=7, fontName='Helvetica-Oblique',
                                borderPadding=(6, 6, 6), backColor=LIGHT),
        'code': ParagraphStyle('CO', parent=base['Code'], fontSize=7.6, leading=10.2,
                               textColor=DARK, fontName='Courier', backColor=LIGHT,
                               borderPadding=(6, 5, 6, 5), borderColor=HexColor('#cbd5e1'),
                               borderWidth=0.5, spaceBefore=2, spaceAfter=2),
        'toc0': ParagraphStyle('T0', parent=base['Normal'], fontSize=12, leading=20,
                               textColor=DARK, fontName='Helvetica-Bold', leftIndent=0),
        'toc1': ParagraphStyle('T1', parent=base['Normal'], fontSize=10, leading=16,
                               textColor=GRAY, leftIndent=18),
    }

def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(GRAY)
    canvas.drawCentredString(A4[0] / 2, 15 * mm,
        f"Fair Dinkum Publishing · ABN 63 590 716 023 · {getattr(doc, 'fdp_title', '')} · p. {doc.page}")
    canvas.restoreState()

import html as _html
import re as _re

_CODE_SLOT = '\x00code%d\x00'


def _inline(text):
    """Escape HTML, then apply inline markdown (code, links, bold, italic)."""
    s = _html.escape(text, quote=False)
    # Stash code spans first so ** and * inside them are left alone.
    spans = []

    def _stash(m):
        spans.append(m.group(1))
        return _CODE_SLOT % (len(spans) - 1)

    s = _re.sub(r'`([^`]+)`', _stash, s)
    s = _re.sub(r'\[([^\]]+)\]\(([^)\s]+)\)', r'<a href="\2">\1</a>', s)
    s = _re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', s)
    s = _re.sub(r'(?<!\*)\*([^*\n]+)\*(?!\*)', r'<em>\1</em>', s)
    for idx, code in enumerate(spans):
        s = s.replace(_CODE_SLOT % idx, '<code>%s</code>' % code)
    return s


def _split_row(line):
    """Split a markdown table row into stripped cells."""
    return [c.strip() for c in line.strip().strip('|').split('|')]


def _is_table_delimiter(line):
    return bool(_re.match(r'^\s*\|[\s:\-|]+\|\s*$', line))


def md_to_html(text):
    """Markdown -> HTML for EPUB and the flipbook.

    Handles fenced code blocks, tables, headings, ordered/unordered lists,
    blockquotes and horizontal rules. Everything is HTML-escaped, which the
    previous line-based version did not do.
    """
    lines = text.split('\n')
    out = []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()

        # ── Fenced code block ────────────────────────────────────────────
        if stripped.startswith('```'):
            lang = stripped[3:].strip()
            i += 1
            buf = []
            while i < n and not lines[i].strip().startswith('```'):
                buf.append(lines[i])
                i += 1
            i += 1  # consume closing fence (or EOF)
            code = _html.escape('\n'.join(buf), quote=False)
            cls = ' class="language-%s"' % lang if lang else ''
            out.append('<pre><code%s>%s</code></pre>' % (cls, code))
            continue

        # ── Table (header row + delimiter row) ───────────────────────────
        if stripped.startswith('|') and i + 1 < n and _is_table_delimiter(lines[i + 1]):
            header = _split_row(stripped)
            i += 2
            rows = []
            while i < n and lines[i].strip().startswith('|'):
                rows.append(_split_row(lines[i]))
                i += 1
            out.append('<table><thead><tr>')
            out.extend('<th>%s</th>' % _inline(c) for c in header)
            out.append('</tr></thead><tbody>')
            for row in rows:
                out.append('<tr>')
                out.extend('<td>%s</td>' % _inline(c) for c in row)
                out.append('</tr>')
            out.append('</tbody></table>')
            continue

        if not stripped:
            i += 1
            continue

        # ── Horizontal rule (only when not a setext/table artefact) ──────
        if _re.match(r'^(-{3,}|\*{3,}|_{3,})$', stripped):
            out.append('<hr/>')
            i += 1
            continue

        # ── Headings ─────────────────────────────────────────────────────
        m = _re.match(r'^(#{1,6})\s+(.*)$', stripped)
        if m:
            lvl = min(len(m.group(1)), 6)
            out.append('<h%d>%s</h%d>' % (lvl, _inline(m.group(2)), lvl))
            i += 1
            continue

        # ── Blockquote ───────────────────────────────────────────────────
        if stripped.startswith('>'):
            buf = []
            while i < n and lines[i].strip().startswith('>'):
                buf.append(lines[i].strip().lstrip('>').strip())
                i += 1
            out.append('<blockquote><p>%s</p></blockquote>'
                       % _inline(' '.join(buf)))
            continue

        # ── Unordered list ───────────────────────────────────────────────
        if _re.match(r'^[-*+]\s+', stripped):
            out.append('<ul>')
            while i < n and _re.match(r'^[-*+]\s+', lines[i].strip()):
                out.append('<li>%s</li>'
                           % _inline(_re.sub(r'^[-*+]\s+', '', lines[i].strip())))
                i += 1
            out.append('</ul>')
            continue

        # ── Ordered list ─────────────────────────────────────────────────
        if _re.match(r'^\d+[.)]\s+', stripped):
            out.append('<ol>')
            while i < n and _re.match(r'^\d+[.)]\s+', lines[i].strip()):
                out.append('<li>%s</li>'
                           % _inline(_re.sub(r'^\d+[.)]\s+', '', lines[i].strip())))
                i += 1
            out.append('</ol>')
            continue

        # ── Paragraph ────────────────────────────────────────────────────
        out.append('<p>%s</p>' % _inline(stripped))
        i += 1

    return '\n'.join(out)


def iter_source_files(src_dir):
    """Yield (kind, path) for every markdown file, in book reading order.

    Previously each builder globbed only ``ch*.md`` and ``appendix-*.md``,
    which silently dropped the copyright page, disclaimer, transparency
    note, foreword, dedication and all back matter from the shipped files.
    """
    src = Path(src_dir)
    front = ['front-matter.md', 'dedication.md', 'foreword.md']
    for name in front:
        p = src / name
        if p.exists():
            yield ('front', p)
    for p in sorted(src.glob('ch*.md')):
        yield ('chapter', p)
    for p in sorted(src.glob('appendix-*.md')):
        yield ('appendix', p)
    back = ['about-the-author.md', 'further-resources.md']
    for name in back:
        p = src / name
        if p.exists():
            yield ('back', p)


def _pdf_inline(text):
    """Markdown inline -> reportlab Paragraph markup (XML-escaped)."""
    s = _html.escape(text, quote=False)
    spans = []

    def _stash(m):
        spans.append(m.group(1))
        return _CODE_SLOT % (len(spans) - 1)

    s = _re.sub(r'`([^`]+)`', _stash, s)
    s = _re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', s)
    s = _re.sub(r'(?<!\*)\*([^*\n]+)\*(?!\*)', r'<i>\1</i>', s)
    for idx, code in enumerate(spans):
        s = s.replace(
            _CODE_SLOT % idx,
            '<font face="Courier" size="9">%s</font>' % code,
        )
    return s


def _pdf_blocks(raw, s):
    """Convert markdown body lines into reportlab flowables.

    Handles fenced code (monospace, indentation preserved), tables (real
    Table objects), headings, lists, blockquotes and paragraphs. Previously
    code was flattened into justified prose and tables were dropped entirely.
    """
    lines = raw.split('\n')
    story = []
    i, n = 0, len(lines)

    # Skip the leading H1 -- the caller already emitted it as a page heading.
    for k, line in enumerate(lines):
        if line.strip():
            i = k + 1
            break

    usable = A4[0] - 36 * mm

    while i < n:
        stripped = lines[i].strip()

        # ── Fenced code ────────────────────────────────────────────────
        if stripped.startswith('```'):
            i += 1
            buf = []
            while i < n and not lines[i].strip().startswith('```'):
                buf.append(lines[i])
                i += 1
            i += 1
            if buf:
                story.append(Spacer(1, 2 * mm))
                story.append(Preformatted(
                    _html.escape('\n'.join(buf), quote=False), s['code'],
                ))
                story.append(Spacer(1, 2 * mm))
            continue

        # ── Table ──────────────────────────────────────────────────────
        if stripped.startswith('|') and i + 1 < n and _is_table_delimiter(lines[i + 1]):
            header = [_pdf_inline(c) for c in _split_row(stripped)]
            i += 2
            data = [header]
            while i < n and lines[i].strip().startswith('|'):
                data.append([_pdf_inline(c) for c in _split_row(lines[i])])
                i += 1
            ncols = max(len(r) for r in data)
            data = [r + [''] * (ncols - len(r)) for r in data]
            t = Table(data, colWidths=[usable / ncols] * ncols, repeatRows=1)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('GRID', (0, 0), (-1, -1), 0.4, HexColor('#cbd5e1')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTSIZE', (0, 0), (-1, -1), 8.5),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT]),
            ]))
            story.append(Spacer(1, 2 * mm))
            story.append(t)
            story.append(Spacer(1, 3 * mm))
            continue

        if not stripped:
            i += 1
            continue

        if _re.match(r'^(-{3,}|\*{3,}|_{3,})$', stripped):
            story.append(Spacer(1, 4 * mm))
            i += 1
            continue

        m = _re.match(r'^(#{2,6})\s+(.*)$', stripped)
        if m:
            lvl = min(len(m.group(1)), 3)
            story.append(Paragraph(
                _pdf_inline(m.group(2)),
                s['h2'] if lvl == 2 else s['h3'],
            ))
            i += 1
            continue

        if stripped.startswith('>'):
            buf = []
            while i < n and lines[i].strip().startswith('>'):
                buf.append(lines[i].strip().lstrip('>').strip())
                i += 1
            story.append(Paragraph(_pdf_inline(' '.join(buf)), s['quote']))
            continue

        if _re.match(r'^[-*+]\s+', stripped) or _re.match(r'^\d+[.)]\s+', stripped):
            while i < n:
                cur = lines[i].strip()
                if _re.match(r'^[-*+]\s+', cur):
                    txt = _re.sub(r'^[-*+]\s+', '', cur)
                elif _re.match(r'^\d+[.)]\s+', cur):
                    txt = _re.sub(r'^\d+[.)]\s+', '', cur)
                else:
                    break
                story.append(Paragraph(_pdf_inline(txt), s['bullet']))
                i += 1
            story.append(Spacer(1, 2 * mm))
            continue

        story.append(Paragraph(_pdf_inline(stripped), s['body']))
        i += 1

    return story


def build_pdf(src_dir, out_dir, title, subtitle):
    """Build paginated PDF."""
    s = styles()
    os.makedirs(out_dir, exist_ok=True)
    
    chapters = sorted(Path(src_dir).glob('ch*.md'))
    if not chapters:
        print("No chapters found!")
        return None
    
    pdf_path = os.path.join(out_dir, '02-ebook.pdf')
    
    doc = BaseDocTemplate(pdf_path, pagesize=A4,
                          leftMargin=18*mm, rightMargin=18*mm,
                          topMargin=22*mm, bottomMargin=18*mm,
                          title=title, author='Fair Dinkum Publishing')
    doc.fdp_title = title
    
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='main')
    template = PageTemplate(id='main', frames=[frame], onPage=footer)
    doc.addPageTemplates([template])
    
    story = []
    
    # Cover
    story.append(Spacer(1, 80*mm))
    story.append(Paragraph(title, s['cover_title']))
    story.append(Spacer(1, 10*mm))
    story.append(Paragraph(subtitle, s['cover_sub']))
    story.append(Spacer(1, 30*mm))
    story.append(Paragraph('Fair Dinkum Publishing', s['brand']))
    story.append(Paragraph('ABN 63 590 716 023', s['brand']))
    story.append(PageBreak())
    
    # TOC placeholder
    story.append(Paragraph('Contents', s['h1']))
    story.append(Spacer(1, 10*mm))

    # Front matter, chapters, appendices, back matter -- in reading order.
    for kind, path in iter_source_files(src_dir):
        with open(path, 'r', encoding='utf-8') as f:
            raw = f.read()
        h1_match = re.search(r'^#\s+(.+)', raw, re.MULTILINE)
        ch_title = h1_match.group(1).strip() if h1_match else path.stem

        story.append(Paragraph(_pdf_inline(ch_title), s['toc1']))

        story.append(PageBreak())
        story.append(Paragraph(_pdf_inline(ch_title), s['h1']))
        story.extend(_pdf_blocks(raw, s))

    doc.build(story)
    return pdf_path

def build_flipbook(src_dir, out_dir, title, subtitle):
    """Build pageless HTML flipbook."""

    html_parts = [f'''<!DOCTYPE html>
<html lang="en-AU">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_html.escape(title)} — Fair Dinkum Publishing</title>
<style>
body {{ font-family: Georgia, serif; max-width: 720px; margin: 0 auto; padding: 24px; color: #1e293b; line-height: 1.6; }}
.cover {{ text-align: center; padding: 48px 0; border-bottom: 3px solid #C88A00; }}
h1 {{ color: #0E4D2E; }}
h2 {{ color: #0E4D2E; border-top: 2px solid #C88A00; padding-top: 16px; margin-top: 32px; }}
h3 {{ color: #64748b; }}
blockquote {{ border-left: 3px solid #C88A00; margin: 16px 0; padding: 8px 16px; color: #64748b; font-style: italic; background: #f8fafc; }}
nav {{ position: sticky; top: 0; background: #fff; padding: 12px; border-bottom: 1px solid #eee; margin-bottom: 24px; }}
nav a {{ margin-right: 16px; color: #0E4D2E; text-decoration: none; }}
code {{ font-family: "Courier New", monospace; font-size: 0.88em; background: #f1f5f9; padding: 0 3px; border-radius: 3px; }}
pre {{ background: #f8fafc; border: 1px solid #cbd5e1; border-left: 3px solid #0E4D2E; padding: 14px; margin: 16px 0; overflow-x: auto; }}
pre code {{ background: none; padding: 0; font-size: 0.82em; line-height: 1.45; }}
table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
th {{ background: #0E4D2E; color: white; }}
tr:nth-child(even) td {{ background: #f8fafc; }}
footer {{ margin-top: 48px; padding-top: 16px; border-top: 1px solid #eee; text-align: center; color: #64748b; font-size: 0.9em; }}
</style>
</head>
<body>
<div class="cover">
<h1>{_html.escape(title)}</h1>
<p>{_html.escape(subtitle)}</p>
<p><small>Fair Dinkum Publishing &middot; 2026 &middot; ABN 63 590 716 023</small></p>
</div>
''']
    
    for _kind, path in iter_source_files(src_dir):
        with open(path, 'r', encoding='utf-8') as f:
            raw = f.read()
        h1_match = re.search(r'^#\s+(.+)', raw, re.MULTILINE)
        ch_title = h1_match.group(1).strip() if h1_match else path.stem
        html_parts.append(f'<h1>{_html.escape(ch_title)}</h1>\n')
        body = re.sub(r'^#\s+.+\n+', '', raw, count=1)
        html_parts.append(md_to_html(body))

    html_parts.append('<footer><p>&copy; 2026 Fair Dinkum Publishing &middot; ABN 63 590 716 023</p></footer>\n</body>\n</html>')
    
    out_path = os.path.join(out_dir, '01-flipbook.html')
    os.makedirs(out_dir, exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(html_parts))
    return out_path

def build_epub(src_dir, out_dir, title, subtitle):
    """Build EPUB."""
    from ebooklib import epub
    
    book = epub.EpubBook()
    book.set_identifier('fair-dum-ai-compliance-playbook')
    book.set_title(title)
    book.set_language('en-AU')
    book.add_author('Fair Dinkum Publishing')
    # ebooklib 0.20 has no set_description(); OPF metadata goes via add_metadata.
    book.add_metadata(
        'DC', 'description',
        'Privacy Act 1988 and the Australian Privacy Principles as they '
        'apply to AI tools, agents and automation in the Australian small '
        'business. Fair Dinkum Publishing, ABN 63 590 716 023.',
    )
    book.add_metadata('DC', 'publisher', 'Fair Dinkum Publishing')
    book.add_metadata('DC', 'rights', 'Copyright 2026 Brett Sjoberg')

    # Stylesheet so code blocks and tables stay readable in e-readers.
    css = epub.EpubItem(
        uid='style', file_name='style/main.css', media_type='text/css',
    )
    css.content = _EPUB_CSS
    book.add_item(css)

    chapter_list = []
    for _kind, path in iter_source_files(src_dir):
        with open(path, 'r', encoding='utf-8') as f:
            raw = f.read()
        h1_match = re.search(r'^#\s+(.+)', raw, re.MULTILINE)
        ch_title = h1_match.group(1).strip() if h1_match else path.stem
        body = re.sub(r'^#\s+.+\n+', '', raw, count=1)

        ch = epub.EpubHtml(
            file_name=f'{path.stem}.xhtml', title=ch_title, lang='en-AU',
        )
        ch.content = (
            '<!DOCTYPE html><html xmlns:epub="http://www.idpf.org/2007/ops">'
            '<head><meta charset="utf-8"/>'
            '<link rel="stylesheet" type="text/css" href="../style/main.css"/>'
            f'<title>{_html.escape(ch_title)}</title></head><body>'
            f'<h1>{_html.escape(ch_title)}</h1>\n{md_to_html(body)}'
            '</body></html>'
        )
        ch.add_item(css)
        book.add_item(ch)
        chapter_list.append(ch)

    book.toc = tuple(chapter_list)
    book.spine = ['nav'] + chapter_list
    book.add_item(epub.EpubNcx())
    # Hold the nav instance: ebooklib 0.20 exposes no EPUB_NAV lookup helper.
    nav = epub.EpubNav()
    book.add_item(nav)
    for ch in chapter_list:
        nav.add_item(ch)

    out_path = os.path.join(out_dir, 'compliance-playbook.epub')
    os.makedirs(out_dir, exist_ok=True)
    epub.write_epub(out_path, book)
    return out_path

def build_gpb_epub(src_dir, out_dir, title, subtitle, ggkey,
                   cover_path=None, cover_src_dir=None):
    """Build a Google Play Books-ready EPUB.

    Differences from build_epub():
      * <dc:identifier> is the Partner Center GGKEY, so the file is bound to
        the volume Google already created.
      * The cover JPEG is embedded with properties="cover-image" and a
        cover.xhtml wrapper carries epub:type="cover" (GPB requires this).
      * nav.xhtml lists the cover first in the spine.
      * Fixed layout is not used; reflowable only.
    """
    from ebooklib import epub
    from PIL import Image

    os.makedirs(out_dir, exist_ok=True)
    book = epub.EpubBook()
    book.set_identifier(ggkey)
    book.set_title(title)
    book.set_language('en-AU')
    book.add_author('Fair Dinkum Publishing')
    book.add_metadata('DC', 'creator', 'Fair Dinkum Publishing',
                      {'id': 'creator'})
    book.add_metadata('DC', 'publisher', 'Fair Dinkum Publishing')
    book.add_metadata('DC', 'rights', 'Copyright 2026 Brett Sjoberg')
    book.add_metadata('DC', 'description',
                      'Privacy Act 1988 and the Australian Privacy Principles '
                      'as they apply to AI tools, agents and automation in '
                      'the Australian small business.')
    book.set_direction('ltr')
    book.add_metadata('DC', 'subject', 'Privacy Act 1988 (Australia)')
    book.add_metadata('DC', 'subject', 'Artificial intelligence -- Law and '
                                       'legislation -- Australia')

    css = epub.EpubItem(uid='style', file_name='style/main.css',
                        media_type='text/css')
    css.content = _EPUB_CSS
    book.add_item(css)

    # ── Cover image ───────────────────────────────────────────────────
    cover_item = None
    if cover_path and os.path.exists(cover_path):
        img = Image.open(cover_path).convert('RGB')
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tf:
            tmp_jpg = tf.name
        img.save(tmp_jpg, 'JPEG', quality=92, optimize=True)
        # ebooklib 0.20's EpubCover takes only uid/file_name; media type is
        # derived from the extension and the cover-image manifest property
        # must be set by hand.
        cover_item = epub.EpubCover(uid='cover-image',
                                    file_name='images/cover.jpg')
        cover_item.media_type = 'image/jpeg'
        cover_item.content = Path(tmp_jpg).read_bytes()
        cover_item.properties = ['cover-image']
        book.add_item(cover_item)
        os.unlink(tmp_jpg)

        cover_doc = epub.EpubHtml(uid='cover', file_name='cover.xhtml',
                                  lang='en-AU')
        cover_doc.content = (
            # No <?xml?> declaration: ebooklib 0.20's get_body_content() uses a
            # regex that returns b'' when one is present, which breaks nav
            # page-count generation with "Document is empty".
            '<!DOCTYPE html>'
            '<html xmlns="http://www.w3.org/1999/xhtml" '
            'xmlns:epub="http://www.idpf.org/2007/ops" lang="en-AU">'
            '<head><title>Cover</title>'
            '<meta charset="utf-8"/>'
            '<link rel="stylesheet" type="text/css" href="style/main.css"/>'
            '</head><body style="margin:0;padding:0;text-align:center;">'
            '<section epub:type="cover" role="doc-cover">'
            '<img src="images/cover.jpg" alt="Cover" '
            'style="max-width:100%;height:auto;"/>'
            '</section></body></html>'
        )
        book.add_item(cover_doc)

    chapter_list = []
    for _kind, path in iter_source_files(src_dir):
        with open(path, 'r', encoding='utf-8') as f:
            raw = f.read()
        h1_match = re.search(r'^#\s+(.+)', raw, re.MULTILINE)
        ch_title = h1_match.group(1).strip() if h1_match else path.stem
        body = re.sub(r'^#\s+.+\n+', '', raw, count=1)

        ch = epub.EpubHtml(file_name=f'{path.stem}.xhtml', title=ch_title,
                           lang='en-AU')
        ch.content = (
            # Same reason as the cover doc: no <?xml?> declaration, otherwise
            # ebooklib's nav page-count pass sees an empty document.
            '<!DOCTYPE html>'
            '<html xmlns="http://www.w3.org/1999/xhtml" '
            'xmlns:epub="http://www.idpf.org/2007/ops" lang="en-AU">'
            '<head><meta charset="utf-8"/>'
            '<title>%s</title>'
            '<link rel="stylesheet" type="text/css" href="style/main.css"/>'
            '</head><body>'
            '<section epub:type="chapter" role="doc-chapter">'
            '<h1>%s</h1>\n%s'
            '</section></body></html>'
        ) % (_html.escape(ch_title), _html.escape(ch_title), md_to_html(body))
        ch.add_item(css)
        book.add_item(ch)
        chapter_list.append(ch)

    # toc/nav: cover first, then every chapter, so the nav list matches the
    # spine. GPB renders the cover page from this list.
    ordered = ([cover_doc] if cover_item else []) + chapter_list
    book.toc = tuple(ordered)
    book.add_item(epub.EpubNcx())
    nav = epub.EpubNav()
    book.add_item(nav)
    for ch in ordered:
        nav.add_item(ch)

    # Spine must reference document items by id only. Using the cover
    # itemref id ('cover-image' is the JPEG's id) or the literal string
    # 'cover_doc' produces dangling/duplicate itemrefs.
    book.spine = (['cover'] if cover_item else []) + ['nav'] + chapter_list

    out_path = os.path.join(out_dir, 'compliance-playbook-gpb.epub')
    epub.write_epub(out_path, book)
    return out_path


if __name__ == '__main__':
    src = BOOK['src']
    out = BOOK['out']
    title = BOOK['title']
    subtitle = BOOK['subtitle']
    
    print(f"Building: {title}")
    print(f"Source: {src}")
    print(f"Output: {out}")
    print()
    
    print("Building flipbook...")
    flip = build_flipbook(src, out, title, subtitle)
    print(f"  ✓ {flip}")
    
    print("Building PDF...")
    pdf = build_pdf(src, out, title, subtitle)
    if pdf:
        print(f"  ✓ {pdf}")
    
    print("Building EPUB...")
    epub_path = build_epub(src, out, title, subtitle)
    print(f"  ✓ {epub_path}")
    
    print()
    print("Done.")
