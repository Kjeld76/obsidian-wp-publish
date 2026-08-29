"""Einmalige Ablage des Application Passwords im Windows Credential Manager."""
import getpass

import credentials

cfg = credentials.load_config()
pw = getpass.getpass("Application Password fuer %s (%s): " % (cfg["site"], cfg["username"]))
credentials.set_app_password(cfg["site"], cfg["username"], pw)
print("Gespeichert. Die Eingabe wurde nirgends protokolliert.")
