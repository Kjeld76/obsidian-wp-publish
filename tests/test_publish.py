import wp_publish as wp

NOTIZ = (
    "---\ntitle: Mein Post\ntags:\n  - linux\ncategories:\n  - Allgemein\n---\n"
    "\nText mit Codeblock:\n\n```bash\nuname -a\n```\n"
)

CFG = {"site": "https://beispiel.test", "username": "wer",
       "default_status": "draft", "default_category": "Allgemein"}


class FakeClient:
    """Kennt jeden Term. Protokolliert, ob er anlegen bzw. hochladen duerfte."""

    def __init__(self):
        self.anlegen_flags = []
        self.uploads = []

    def term_ids(self, taxonomy, namen, anlegen=True):
        self.anlegen_flags.append(anlegen)
        basis = {"tags": 10, "categories": 20}[taxonomy]
        return [basis + i for i, _ in enumerate(namen or [])], []

    def upload_media(self, pfad):
        self.uploads.append(pfad)
        return "https://beispiel.test/wp-content/uploads/bild.png"


class FakeClientOhneTerms(FakeClient):
    """Kennt keinen Term - so verhaelt sich ein frischer Blog."""

    def term_ids(self, taxonomy, namen, anlegen=True):
        self.anlegen_flags.append(anlegen)
        if anlegen:
            return [99 for _ in namen or []], []
        return [], [str(n) for n in namen or []]


def test_payload_traegt_titel_status_und_terms():
    payload, _ = wp.baue_payload(NOTIZ, CFG, FakeClient(), "C:/egal/Notiz.md")
    assert payload["title"] == "Mein Post"
    assert payload["status"] == "draft"
    assert payload["tags"] == [10] and payload["categories"] == [20]
    assert "<code" in payload["content"] and "uname -a" in payload["content"]


def test_ohne_title_wird_der_dateiname_genommen():
    ohne = NOTIZ.replace("title: Mein Post\n", "")
    payload, _ = wp.baue_payload(ohne, CFG, FakeClient(), "C:/egal/Spack bauen.md")
    assert payload["title"] == "Spack bauen"


def test_frontmatter_erscheint_nicht_im_inhalt():
    payload, _ = wp.baue_payload(NOTIZ, CFG, FakeClient(), "C:/egal/Notiz.md")
    assert "categories" not in payload["content"] and "---" not in payload["content"]


def test_dry_run_darf_keine_terms_anlegen():
    """Regression: der Dry-Run hat am 29.08.2026 Kategorie und Tag erzeugt."""
    client = FakeClientOhneTerms()
    payload, warnungen = wp.baue_payload(NOTIZ, CFG, client, "C:/egal/Notiz.md", schreiben=False)
    assert client.anlegen_flags == [False, False]
    assert payload["categories"] == [] and payload["tags"] == []
    assert any("wuerde neu angelegt" in w for w in warnungen)


def test_dry_run_darf_kein_bild_hochladen():
    notiz = NOTIZ.replace("Text mit Codeblock:", "![[diagramm.png]]")
    client = FakeClient()
    _, warnungen = wp.baue_payload(notiz, CFG, client, "C:/egal/Notiz.md", schreiben=False)
    assert client.uploads == []
    assert any("diagramm.png" in w for w in warnungen)


def test_echtlauf_legt_terms_an():
    client = FakeClientOhneTerms()
    payload, _ = wp.baue_payload(NOTIZ, CFG, client, "C:/egal/Notiz.md", schreiben=True)
    assert client.anlegen_flags == [True, True]
    assert payload["categories"] == [99]
