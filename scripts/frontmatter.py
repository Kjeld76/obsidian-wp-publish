"""Liest und schreibt YAML-Frontmatter von Obsidian-Notizen.

Geschrieben wird chirurgisch: nur die Zeile des betroffenen Keys wird ersetzt
oder ergaenzt. Alles andere - Reihenfolge, Quoting, Einrueckung, Rumpftext -
bleibt byteweise unveraendert. Jeder Schreibvorgang prueft sich selbst.
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
    """(daten, roh_yaml, rumpf). Ohne gueltiges Frontmatter: ({}, None, text)."""
    match = FM_RE.match(text)
    if not match:
        return {}, None, text
    roh = match.group(1)
    try:
        daten = yaml.safe_load(roh)
    except yaml.YAMLError as err:
        raise FrontmatterError("Frontmatter ist kein gueltiges YAML: %s" % err)
    if daten is None:
        daten = {}
    if not isinstance(daten, dict):
        raise FrontmatterError("Frontmatter ist kein YAML-Mapping")
    return daten, roh, text[match.end():]


def set_field(text, key, value):
    """Setzt genau ein Skalarfeld im Frontmatter und gibt den neuen Text zurueck."""
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise FrontmatterError("Nur Zahlen und Strings werden geschrieben, nicht %r" % type(value))

    alt, roh, rumpf = split_note(text)
    if roh is None:
        raise FrontmatterError(
            "Notiz hat kein gueltiges Frontmatter (fehlende oder defekte '---'-Trenner). "
            "Es wird nichts geschrieben - bitte die Notiz zuerst reparieren."
        )

    zeile = "%s: %s" % (key, value)
    key_re = re.compile(r"^%s[ \t]*:.*$" % re.escape(key), re.MULTILINE)
    if key_re.search(roh):
        neu_roh = key_re.sub(zeile, roh, count=1)
    else:
        neu_roh = roh.rstrip("\r\n") + "\n" + zeile

    neu_text = "---\n" + neu_roh + "\n---\n" + rumpf

    # Selbstkontrolle - genau die Pruefungen, an denen das Plugin gescheitert ist.
    neu, neu_roh_check, neu_rumpf = split_note(neu_text)
    if neu_roh_check is None:
        raise FrontmatterError("Ergebnis haette kein gueltiges Frontmatter - abgebrochen")
    verloren = sorted(set(alt) - set(neu))
    if verloren:
        raise FrontmatterError("Felder gingen verloren: %s - abgebrochen" % ", ".join(verloren))
    for feld, wert in alt.items():
        if feld != key and neu.get(feld) != wert:
            raise FrontmatterError("Feld '%s' wurde veraendert - abgebrochen" % feld)
    if neu.get(key) != value:
        raise FrontmatterError("Feld '%s' wurde nicht korrekt gesetzt - abgebrochen" % key)
    if neu_rumpf != rumpf:
        raise FrontmatterError("Notiztext wurde veraendert - abgebrochen")
    return neu_text


def write_note(path, neu_text):
    """Schreibt atomar und legt vorher eine .bak-Kopie an."""
    if not neu_text.strip():
        raise FrontmatterError("Leerer Text wird nicht geschrieben")
    shutil.copy2(path, path + ".bak")
    ordner = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=ordner, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(neu_text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
