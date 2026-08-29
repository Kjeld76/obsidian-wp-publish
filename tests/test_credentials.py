import pytest
import credentials


def test_load_config_liefert_site_und_user():
    cfg = credentials.load_config()
    assert cfg["site"].startswith("https://")
    assert cfg["username"]
    assert cfg["default_status"] == "draft"


def test_fehlende_ablage_nennt_den_setup_befehl(monkeypatch):
    monkeypatch.setattr(credentials.keyring, "get_password", lambda s, u: None)
    with pytest.raises(credentials.CredentialError) as exc:
        credentials.get_app_password("https://example.invalid", "wer")
    assert "set_credentials.py" in str(exc.value)


def test_leeres_passwort_wird_nicht_gespeichert():
    with pytest.raises(credentials.CredentialError):
        credentials.set_app_password("https://example.invalid", "wer", "   ")
