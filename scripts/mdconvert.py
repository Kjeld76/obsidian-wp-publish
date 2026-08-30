"""Prepare Obsidian flavoured Markdown for WordPress and convert it to HTML."""
import re

import markdown

EXTENSIONS = ["fenced_code", "tables", "sane_lists", "attr_list"]

EMBED_RE = re.compile(r"!\[\[([^\]|]+?)(?:\|[^\]]*)?\]\]")
WIKILINK_RE = re.compile(r"(?<!!)\[\[([^\]|]+?)(?:\|([^\]]*))?\]\]")
CALLOUT_RE = re.compile(r"^>[ \t]*\[![a-zA-Z-]+\][+-]?[ \t]*(.*)$", re.MULTILINE)
CODE_CLASS_RE = re.compile(r'<code class="([a-z0-9+#-]+)">')


def preprocess(body):
    """Returns (markdown_text, image_files, warnings)."""
    images = []
    warnings = []

    def _embed(match):
        filename = match.group(1).strip()
        if filename not in images:
            images.append(filename)
        return "![](WPMEDIA::%s)" % filename

    def _wikilink(match):
        target = match.group(1).strip()
        alias = (match.group(2) or "").strip()
        warnings.append(
            "Wikilink '%s' became plain text - the target note does not exist on the blog"
            % target)
        return alias or target.split("/")[-1]

    def _callout(match):
        title = match.group(1).strip()
        return "> **%s**" % title if title else ">"

    text = EMBED_RE.sub(_embed, body)
    text = WIKILINK_RE.sub(_wikilink, text)
    text = CALLOUT_RE.sub(_callout, text)
    return text, images, warnings


def _language_class(match):
    name = match.group(1)
    if not name.startswith("language-"):
        name = "language-" + name
    return '<code class="%s">' % name


def to_html(body):
    html = markdown.markdown(body, extensions=EXTENSIONS, output_format="html5")
    # Normalise the language class: <code class="bash"> -> <code class="language-bash">
    return CODE_CLASS_RE.sub(_language_class, html)


def replace_media(html, url_map):
    """Replace the WPMEDIA:: placeholders with the uploaded WordPress URLs."""
    for filename, url in url_map.items():
        html = html.replace("WPMEDIA::%s" % filename, url)
    return html
