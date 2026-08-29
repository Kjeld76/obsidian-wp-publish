# obsidian-wp-publish

Veroeffentlicht eine Obsidian-Notiz als Entwurf auf devnull.koenig-mario.de und
aktualisiert bei erneutem Lauf denselben Post, statt ihn zu duplizieren.

Ersetzt das Obsidian-Plugin `obsidian-wordpress`, dessen Rueckschreiben der
Metadaten das YAML-Frontmatter der Notiz reproduzierbar zerstoert hat. Der Kern
dieses Werkzeugs ist deshalb eine kontrollierte Frontmatter-Schreiblogik:
chirurgische Zeilen-Edits statt YAML-Round-trip, mit Selbstkontrolle vor jedem
Schreibvorgang.

## Einrichtung

```
python -m pip install requests markdown keyring pytest
python scripts/set_credentials.py
```

Das Application Password liegt ausschliesslich im Windows Credential Manager.
`config.json` enthaelt nur Site-URL und Benutzername, nie ein Secret.

## Benutzung

```
python scripts/wp_publish.py "<pfad/zur/notiz.md>" [--status draft|publish] [--dry-run]
```

Standard ist immer `draft`.

## Frontmatter

```yaml
---
title: Titel des Posts
tags:
  - linux
categories:
  - Allgemein
wp_status: draft
wp_id: 168
---
```

`wp_id` setzt das Werkzeug selbst und ist das einzige Feld, das es je schreibt.

## Tests

```
python -m pytest tests/ -v
```
