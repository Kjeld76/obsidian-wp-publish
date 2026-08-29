"""Obsidian-Markdown fuer WordPress aufbereiten und nach HTML wandeln."""
import re

import markdown

EXTENSIONS = ["fenced_code", "tables", "sane_lists", "attr_list"]

EMBED_RE = re.compile(r"!\[\[([^\]|]+?)(?:\|[^\]]*)?\]\]")
WIKILINK_RE = re.compile(r"(?<!!)\[\[([^\]|]+?)(?:\|([^\]]*))?\]\]")
CALLOUT_RE = re.compile(r"^>[ \t]*\[![a-zA-Z-]+\][+-]?[ \t]*(.*)$", re.MULTILINE)
CODE_CLASS_RE = re.compile(r'<code class="([a-z0-9+#-]+)">')


def preprocess(body):
    """(markdown_text, bilddateien, warnungen)."""
    bilder = []
    warnungen = []

    def _embed(match):
        datei = match.group(1).strip()
        if datei not in bilder:
            bilder.append(datei)
        return "![](WPMEDIA::%s)" % datei

    def _wikilink(match):
        ziel = match.group(1).strip()
        alias = (match.group(2) or "").strip()
        warnungen.append("Wikilink '%s' wurde zu Klartext - im Blog gibt es die Notiz nicht" % ziel)
        return alias or ziel.split("/")[-1]

    def _callout(match):
        titel = match.group(1).strip()
        return "> **%s**" % titel if titel else ">"

    text = EMBED_RE.sub(_embed, body)
    text = WIKILINK_RE.sub(_wikilink, text)
    text = CALLOUT_RE.sub(_callout, text)
    return text, bilder, warnungen


def _sprachklasse(match):
    klasse = match.group(1)
    if not klasse.startswith("language-"):
        klasse = "language-" + klasse
    return '<code class="%s">' % klasse


def to_html(body):
    html = markdown.markdown(body, extensions=EXTENSIONS, output_format="html5")
    # Sprachklasse vereinheitlichen: <code class="bash"> -> <code class="language-bash">
    return CODE_CLASS_RE.sub(_sprachklasse, html)


def ersetze_medien(html, url_map):
    """Ersetzt die WPMEDIA::-Platzhalter durch die hochgeladenen WordPress-URLs."""
    for datei, url in url_map.items():
        html = html.replace("WPMEDIA::%s" % datei, url)
    return html
