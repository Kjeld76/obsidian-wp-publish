import pytest
import wpclient


class FakeAntwort:
    def __init__(self, status, daten):
        self.status_code = status
        self._daten = daten
        self.text = str(daten)

    def json(self):
        return self._daten


class FakeSession:
    def __init__(self, plan):
        self.plan = plan
        self.aufrufe = []

    def request(self, methode, url, **kwargs):
        self.aufrufe.append((methode, url, kwargs))
        return self.plan.pop(0)


def _client(plan):
    c = wpclient.WPClient("https://beispiel.test", "wer", "geheim")
    c.session = FakeSession(plan)
    return c


def test_vorhandener_term_wird_wiederverwendet():
    c = _client([FakeAntwort(200, [{"id": 7, "name": "Linux"}])])
    assert c.term_ids("tags", ["Linux"]) == ([7], [])
    assert len(c.session.aufrufe) == 1


def test_fehlender_term_wird_angelegt():
    c = _client([FakeAntwort(200, []), FakeAntwort(201, {"id": 12, "name": "HPC"})])
    assert c.term_ids("tags", ["HPC"]) == ([12], [])
    assert c.session.aufrufe[1][0] == "POST"


def test_numerischer_term_wird_direkt_als_id_genommen():
    c = _client([])
    assert c.term_ids("categories", [1]) == ([1], [])


def test_fehlermeldung_enthaelt_kein_passwort():
    c = _client([FakeAntwort(401, {"code": "unauthorized"})])
    with pytest.raises(wpclient.WPError) as exc:
        c.get_post(168)
    assert "geheim" not in str(exc.value)


def test_update_post_nutzt_id_im_pfad():
    c = _client([FakeAntwort(200, {"id": 168, "status": "draft"})])
    c.update_post(168, {"title": "X"})
    methode, url, _ = c.session.aufrufe[0]
    assert methode == "POST" and url.endswith("/wp/v2/posts/168")


def test_ohne_anlegen_wird_kein_term_erzeugt():
    """Der Dry-Run darf nichts schreiben - fehlende Terms werden nur gemeldet."""
    c = _client([FakeAntwort(200, [])])
    ids, fehlend = c.term_ids("tags", ["HPC"], anlegen=False)
    assert ids == []
    assert fehlend == ["HPC"]
    assert [a[0] for a in c.session.aufrufe] == ["GET"]      # kein POST


def test_term_mit_html_entity_wird_gefunden_ohne_suchparameter():
    """Der Name steht als Entity in der DB ('Code &amp; Technik').

    Die WP-Suche nach 'Code & Technik' liefert deshalb null Treffer - am echten
    Blog am 29.08.2026 gemessen. Der Client muss die Liste laden und lokal
    vergleichen, sonst legt er ein Duplikat an.
    """
    c = _client([FakeAntwort(200, [{"id": 31, "name": "Code &amp; Technik"}])])
    assert c.term_ids("categories", ["Code & Technik"]) == ([31], [])
    assert [a[0] for a in c.session.aufrufe] == ["GET"]      # kein POST
    assert "search" not in c.session.aufrufe[0][2].get("params", {})


def test_termliste_wird_nur_einmal_geladen():
    """Zwei Namen, ein GET - sonst waechst die Laufzeit mit jedem Tag."""
    c = _client([FakeAntwort(200, [{"id": 7, "name": "Linux"}, {"id": 8, "name": "HPC"}])])
    assert c.term_ids("tags", ["Linux", "HPC"]) == ([7, 8], [])
    assert len(c.session.aufrufe) == 1
