import json

import pytest
import credentials


def _write_config(tmp_path, **overrides):
    cfg = {"site": "https://example.test/", "username": "someone"}
    cfg.update(overrides)
    path = tmp_path / "config.json"
    path.write_text(json.dumps(cfg), encoding="utf-8")
    return str(path)


def test_load_config_fills_in_the_optional_defaults(tmp_path):
    cfg = credentials.load_config(_write_config(tmp_path))
    assert cfg["site"] == "https://example.test"          # trailing slash removed
    assert cfg["username"] == "someone"
    assert cfg["default_status"] == "draft"
    assert cfg["default_category"] == "Uncategorized"
    assert cfg["vault_path"] == ""
    assert cfg["attachment_folders"] == []


def test_a_single_attachment_folder_may_be_a_plain_string(tmp_path):
    path = _write_config(tmp_path, attachment_folders="assets")
    assert credentials.load_config(path)["attachment_folders"] == ["assets"]


def test_missing_site_is_rejected(tmp_path):
    path = _write_config(tmp_path, site="")
    with pytest.raises(credentials.CredentialError):
        credentials.load_config(path)


def test_missing_config_names_the_example_file(tmp_path):
    with pytest.raises(credentials.CredentialError) as exc:
        credentials.load_config(str(tmp_path / "nothere.json"))
    assert "config.example.json" in str(exc.value)


def test_missing_password_names_the_setup_command(monkeypatch):
    monkeypatch.setattr(credentials.keyring, "get_password", lambda s, u: None)
    with pytest.raises(credentials.CredentialError) as exc:
        credentials.get_app_password("https://example.invalid", "someone")
    assert "set_credentials.py" in str(exc.value)


def test_empty_password_is_not_stored():
    with pytest.raises(credentials.CredentialError):
        credentials.set_app_password("https://example.invalid", "someone", "   ")
