"""Zugangsdaten fuer den WordPress-Publish-Skill.

Das Application Password liegt ausschliesslich im Windows Credential Manager
(ueber keyring). Weder Vault noch config.json enthalten je ein Secret.
"""
import json
import os

import keyring

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(SKILL_DIR, "config.json")


class CredentialError(Exception):
    pass


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
        cfg = json.load(fh)
    for key in ("site", "username", "default_status"):
        if not cfg.get(key):
            raise CredentialError("config.json: Feld '%s' fehlt oder ist leer" % key)
    cfg["site"] = cfg["site"].rstrip("/")
    return cfg


def _service(site):
    return "blog-publish:%s" % site.rstrip("/")


def set_app_password(site, user, password):
    if not password or not password.strip():
        raise CredentialError("Leeres Passwort wird nicht gespeichert")
    keyring.set_password(_service(site), user, password.strip())


def get_app_password(site, user):
    pw = keyring.get_password(_service(site), user)
    if not pw or not pw.strip():
        raise CredentialError(
            "Kein Application Password im Credential Manager fuer '%s' / '%s'. "
            "Einmalig hinterlegen mit: python scripts/set_credentials.py" % (site, user)
        )
    return pw.strip()
