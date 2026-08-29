import mdconvert as mc


def test_bildeinbettung_wird_zu_platzhalter():
    text, bilder, _ = mc.preprocess("Vorher\n\n![[diagramm.png]]\n\nNachher\n")
    assert bilder == ["diagramm.png"]
    assert "WPMEDIA::diagramm.png" in text and "![[" not in text


def test_wikilink_wird_zu_klartext_und_warnt():
    text, _, warnungen = mc.preprocess("Siehe [[HPC-Cluster|den Cluster]] und [[Blog]].\n")
    assert "den Cluster" in text and "Blog" in text and "[[" not in text
    assert len(warnungen) == 2


def test_callout_wird_zu_blockquote_mit_fetter_zeile():
    text, _, _ = mc.preprocess("> [!warning] Achtung\n> Zeile zwei\n")
    assert "> **Achtung**" in text and "[!warning]" not in text


def test_codeblock_behaelt_sprache():
    html = mc.to_html("```bash\nls -la\n```\n")
    assert "<pre>" in html and 'class="language-bash"' in html and "ls -la" in html


def test_ueberschrift_liste_link():
    html = mc.to_html("## Titel\n\n- eins\n- zwei\n\n[RUB](https://www.rub.de)\n")
    assert "<h2>Titel</h2>" in html
    assert "<li>eins</li>" in html
    assert '<a href="https://www.rub.de">RUB</a>' in html
