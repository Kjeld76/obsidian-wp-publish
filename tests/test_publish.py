import wp_publish as wp

NOTIZ = (
    "---\ntitle: Mein Post\ntags:\n  - linux\ncategories:\n  - Allgemein\n---\n"
    "\nText mit Codeblock:\n\n```bash\nuname -a\n```\n"
)

CFG = {"site": "https://beispiel.test", "username": "wer",
       "default_status": "draft", "default_category": "Allgemein"}


class FakeClient:
    def term_ids(self, taxonomy, namen):
        basis = {"tags": 10, "categories": 20}[taxonomy]
        return [basis + i for i, _ in enumerate(namen or [])]

    def upload_media(self, pfad):
        return "https://beispiel.test/wp-content/uploads/bild.png"


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
