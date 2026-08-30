"""Credentials and configuration for the WordPress publisher.

The application password lives in the operating system's credential store
(via keyring) and nowhere else. Neither the vault nor config.json ever holds
a secret.
"""
import json
import os

import keyring

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(SKILL_DIR, "config.json")

DEFAULTS = {
    "vault_path": "",
    "attachment_folders": [],
    "default_category": "Uncategorized",
    "default_status": "draft",
}


class CredentialError(Exception):
    pass


def load_config(path=None):
    """Read config.json and fill in defaults for the optional keys."""
    path = path or CONFIG_PATH
    if not os.path.isfile(path):
        raise CredentialError(
            "No config.json found at %s. Copy config.example.json to "
            "config.json and fill in your site and username." % path
        )
    with open(path, "r", encoding="utf-8") as fh:
        cfg = json.load(fh)
    for key in ("site", "username"):
        if not cfg.get(key):
            raise CredentialError("config.json: '%s' is missing or empty" % key)
    for key, fallback in DEFAULTS.items():
        cfg.setdefault(key, fallback)
    cfg["site"] = cfg["site"].rstrip("/")
    if isinstance(cfg["attachment_folders"], str):
        cfg["attachment_folders"] = [cfg["attachment_folders"]]
    return cfg


def _service(site):
    return "blog-publish:%s" % site.rstrip("/")


def set_app_password(site, user, password):
    if not password or not password.strip():
        raise CredentialError("Refusing to store an empty password")
    keyring.set_password(_service(site), user, password.strip())


def get_app_password(site, user):
    pw = keyring.get_password(_service(site), user)
    if not pw or not pw.strip():
        raise CredentialError(
            "No application password in the credential store for '%s' / '%s'. "
            "Store it once with: python scripts/set_credentials.py" % (site, user)
        )
    return pw.strip()
