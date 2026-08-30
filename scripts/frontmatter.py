"""Read and write the YAML frontmatter of Obsidian notes.

Writing is surgical: only the line of the affected key is replaced or added.
Everything else - key order, quoting, indentation, body text - stays byte for
byte identical. Every write verifies itself before it is committed to disk.
"""
import os
import re
import shutil
import tempfile

import yaml

FM_RE = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*\r?\n", re.DOTALL)


class FrontmatterError(Exception):
    pass


def split_note(text):
    """Returns (data, raw_yaml, body). Without valid frontmatter: ({}, None, text)."""
    match = FM_RE.match(text)
    if not match:
        return {}, None, text
    raw = match.group(1)
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as err:
        raise FrontmatterError("Frontmatter is not valid YAML: %s" % err)
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise FrontmatterError("Frontmatter is not a YAML mapping")
    return data, raw, text[match.end():]


def set_field(text, key, value):
    """Set exactly one scalar field in the frontmatter and return the new text."""
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise FrontmatterError("Only numbers and strings are written, not %r" % type(value))

    old, raw, body = split_note(text)
    if raw is None:
        raise FrontmatterError(
            "This note has no valid frontmatter (missing or broken '---' delimiters). "
            "Nothing was written - please repair the note first."
        )

    line = "%s: %s" % (key, value)
    key_re = re.compile(r"^%s[ \t]*:.*$" % re.escape(key), re.MULTILINE)
    if key_re.search(raw):
        new_raw = key_re.sub(line, raw, count=1)
    else:
        new_raw = raw.rstrip("\r\n") + "\n" + line

    new_text = "---\n" + new_raw + "\n---\n" + body

    # Self-check - exactly the properties a careless writer gets wrong.
    new, new_raw_check, new_body = split_note(new_text)
    if new_raw_check is None:
        raise FrontmatterError("Result would have no valid frontmatter - aborted")
    lost = sorted(set(old) - set(new))
    if lost:
        raise FrontmatterError("Fields would be lost: %s - aborted" % ", ".join(lost))
    for field, val in old.items():
        if field != key and new.get(field) != val:
            raise FrontmatterError("Field '%s' would be modified - aborted" % field)
    if new.get(key) != value:
        raise FrontmatterError("Field '%s' was not set correctly - aborted" % key)
    if new_body != body:
        raise FrontmatterError("The note body would be modified - aborted")
    return new_text


def write_note(path, new_text):
    """Write atomically, keeping a .bak copy of the previous version."""
    if not new_text.strip():
        raise FrontmatterError("Refusing to write empty text")
    shutil.copy2(path, path + ".bak")
    folder = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=folder, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(new_text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
