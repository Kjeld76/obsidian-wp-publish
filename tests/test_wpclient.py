import pytest
import wpclient


class FakeResponse:
    def __init__(self, status, data):
        self.status_code = status
        self._data = data
        self.text = str(data)

    def json(self):
        return self._data


class FakeSession:
    def __init__(self, plan):
        self.plan = plan
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.plan.pop(0)


def _client(plan):
    c = wpclient.WPClient("https://example.test", "someone", "s3cret")
    c.session = FakeSession(plan)
    return c


def test_existing_term_is_reused():
    c = _client([FakeResponse(200, [{"id": 7, "name": "Linux"}])])
    assert c.term_ids("tags", ["Linux"]) == ([7], [])
    assert len(c.session.calls) == 1


def test_missing_term_is_created():
    c = _client([FakeResponse(200, []), FakeResponse(201, {"id": 12, "name": "HPC"})])
    assert c.term_ids("tags", ["HPC"]) == ([12], [])
    assert c.session.calls[1][0] == "POST"


def test_numeric_term_is_taken_as_an_id():
    c = _client([])
    assert c.term_ids("categories", [1]) == ([1], [])


def test_error_message_does_not_contain_the_password():
    c = _client([FakeResponse(401, {"code": "unauthorized"})])
    with pytest.raises(wpclient.WPError) as exc:
        c.get_post(168)
    assert "s3cret" not in str(exc.value)


def test_update_post_puts_the_id_in_the_path():
    c = _client([FakeResponse(200, {"id": 168, "status": "draft"})])
    c.update_post(168, {"title": "X"})
    method, url, _ = c.session.calls[0]
    assert method == "POST" and url.endswith("/wp/v2/posts/168")


def test_without_create_no_term_is_written():
    """The dry run must not write - missing terms are only reported."""
    c = _client([FakeResponse(200, [])])
    ids, missing = c.term_ids("tags", ["HPC"], create=False)
    assert ids == []
    assert missing == ["HPC"]
    assert [call[0] for call in c.session.calls] == ["GET"]      # no POST


def test_term_with_html_entity_is_found_without_the_search_parameter():
    """The name is stored as an entity in the database ('Code &amp; Technik').

    A WordPress search for 'Code & Technik' therefore returns zero results -
    measured against a live blog. The client has to load the list and compare
    locally, otherwise it creates a duplicate on every run.
    """
    c = _client([FakeResponse(200, [{"id": 31, "name": "Code &amp; Technik"}])])
    assert c.term_ids("categories", ["Code & Technik"]) == ([31], [])
    assert [call[0] for call in c.session.calls] == ["GET"]      # no POST
    assert "search" not in c.session.calls[0][2].get("params", {})


def test_term_list_is_fetched_only_once():
    """Two names, one GET - otherwise runtime grows with every tag."""
    c = _client([FakeResponse(200, [{"id": 7, "name": "Linux"}, {"id": 8, "name": "HPC"}])])
    assert c.term_ids("tags", ["Linux", "HPC"]) == ([7, 8], [])
    assert len(c.session.calls) == 1


# --- media -----------------------------------------------------------------
# Measured live: two runs of the same note produced both
# 'pasted-image-20260829.png' AND 'pasted-image-20260829-1.png'. Idempotency
# had only ever been considered for the post, not for the media library.

def test_filename_is_normalised_deterministically():
    f = wpclient.WPClient.media_filename
    assert f(r"C:\x\Pasted image 20260829.png") == "pasted-image-20260829.png"
    assert f("/x/My Image (2).JPG") == "my-image-2.jpg"
    assert f("/x/Über alles.png") == "uber-alles.png"


def test_characters_without_an_ascii_decomposition_are_dropped():
    """Known limitation, documented rather than silently surprising.

    NFKD splits accented letters into base plus combining mark, so 'ü' becomes
    'u'. Characters with no such decomposition - 'ß', CJK, emoji - have no
    ASCII equivalent and are dropped. The result stays deterministic, which is
    what the reuse logic depends on, but it is not a transliteration.
    """
    f = wpclient.WPClient.media_filename
    assert f("/x/Größe.png") == "groe.png"
    assert f("/x/日本語.png") == "image.png"          # nothing left, fallback name


def test_existing_medium_is_reused(tmp_path):
    path = tmp_path / "Pasted image 20260829.png"
    path.write_bytes(b"x")
    c = _client([FakeResponse(200, [{"id": 175,
                                     "source_url": "https://e.test/pasted-image-20260829.png"}])])
    url = c.upload_media(str(path))
    assert url == "https://e.test/pasted-image-20260829.png"
    assert [call[0] for call in c.session.calls] == ["GET"]      # no second upload


def test_unknown_medium_is_uploaded(tmp_path):
    path = tmp_path / "new.png"
    path.write_bytes(b"x")
    c = _client([FakeResponse(200, []),
                 FakeResponse(201, {"id": 9, "source_url": "https://e.test/new.png"})])
    assert c.upload_media(str(path)) == "https://e.test/new.png"
    assert [call[0] for call in c.session.calls] == ["GET", "POST"]
    header = c.session.calls[1][2]["headers"]["Content-Disposition"]
    assert 'filename="new.png"' in header
