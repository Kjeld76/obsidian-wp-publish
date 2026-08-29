import pytest
import frontmatter as fm

NOTIZ = (
    "---\n"
    "title: Testpost\n"
    "tags:\n"
    "  - linux\n"
    "  - hpc\n"
    "categories:\n"
    "  - Allgemein\n"
    "---\n"
    "\n"
    "# Ueberschrift\n"
    "\n"
    "- eins\n"
    "- zwei\n"
)

# Genau der beim Plugin beobachtete Schaden: oeffnende --- fehlt.
KAPUTT = "categories:\n  - 1\n---\n\nDas ist ein Testpost.\n"


def test_split_liest_alle_felder():
    daten, roh, rumpf = fm.split_note(NOTIZ)
    assert daten["title"] == "Testpost"
    assert daten["tags"] == ["linux", "hpc"]
    assert daten["categories"] == ["Allgemein"]
    assert rumpf.startswith("\n# Ueberschrift")


def test_set_field_haengt_an_und_laesst_alles_andere_stehen():
    neu = fm.set_field(NOTIZ, "wp_id", 168)
    daten, _, rumpf = fm.split_note(neu)
    assert daten["wp_id"] == 168
    assert daten["title"] == "Testpost"
    assert daten["tags"] == ["linux", "hpc"]
    assert daten["categories"] == ["Allgemein"]
    assert rumpf == fm.split_note(NOTIZ)[2]
    assert neu.startswith("---\n") and "\n---\n" in neu


def test_set_field_aktualisiert_statt_zu_duplizieren():
    zweimal = fm.set_field(fm.set_field(NOTIZ, "wp_id", 168), "wp_id", 999)
    assert zweimal.count("wp_id:") == 1
    assert fm.split_note(zweimal)[0]["wp_id"] == 999


def test_kaputtes_frontmatter_wird_abgelehnt_statt_ueberschrieben():
    with pytest.raises(fm.FrontmatterError):
        fm.set_field(KAPUTT, "wp_id", 168)


def test_crlf_notiz_bleibt_lesbar():
    assert fm.split_note(NOTIZ.replace("\n", "\r\n"))[0]["title"] == "Testpost"


def test_eingerueckter_gleichnamiger_key_wird_nicht_getroffen():
    notiz = "---\nmeta:\n  wp_id: 1\ntitle: X\n---\n\nText\n"
    daten, _, _ = fm.split_note(fm.set_field(notiz, "wp_id", 168))
    assert daten["meta"]["wp_id"] == 1
    assert daten["wp_id"] == 168
