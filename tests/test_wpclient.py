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
    assert c.term_ids("tags", ["Linux"]) == [7]
    assert len(c.session.aufrufe) == 1


def test_fehlender_term_wird_angelegt():
    c = _client([FakeAntwort(200, []), FakeAntwort(201, {"id": 12, "name": "HPC"})])
    assert c.term_ids("tags", ["HPC"]) == [12]
    assert c.session.aufrufe[1][0] == "POST"


def test_numerischer_term_wird_direkt_als_id_genommen():
    c = _client([])
    assert c.term_ids("categories", [1]) == [1]


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
