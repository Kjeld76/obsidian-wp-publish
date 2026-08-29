---
name: blog-publish
description: >-
  Veroeffentlicht eine Obsidian-Notiz als Entwurf auf Marios Blog
  devnull.koenig-mario.de (WordPress REST API + Application Password) und
  aktualisiert bei erneutem Lauf denselben Post ueber die wp_id, statt zu
  duplizieren. Wandelt Obsidian-Markdown nach HTML (Code-Bloecke, Listen,
  Links, Ueberschriften), laedt eingebettete Bilder in die Mediathek hoch und
  mappt Kategorien/Tags auf Term-IDs. Nutze diesen Skill, wenn Mario einen
  Blogpost veroeffentlichen, hochladen oder aktualisieren will - z. B. "Post
  auf den Blog", "veroeffentliche die Notiz als Entwurf", "Blogpost
  aktualisieren", "/blog-publish". NICHT fuer das Erfassen von Blog-Ideen
  (Trigger "Blog:" laeuft nach 04 Ressourcen/Blog/Blog-Ideen), nicht fuer das
  Schreiben des Textes selbst, und nicht fuer andere Seiten als
  devnull.koenig-mario.de.
---

# Blog-Publish

Bringt eine Notiz aus dem Vault als Entwurf auf devnull.koenig-mario.de — und
beim naechsten Lauf dieselbe Notiz auf denselben Post, ohne zu duplizieren und
ohne das Frontmatter zu beschaedigen.

Ersetzt das Obsidian-Plugin `obsidian-wordpress`, dessen Metadaten-Rueckschreiben
am 28./29.08.2026 zweimal reproduzierbar das YAML-Frontmatter zerstoert hat
(→ [[04 Ressourcen/Blog/Blog]]).

## Ablauf

1. **Notiz pruefen.** Frontmatter muss gueltig sein (siehe Schema). Ist es das
   nicht, bricht das Werkzeug ab und schickt nichts — das ist gewollt, nicht
   umgehen.
2. **Dry-Run zeigen.** Immer zuerst:
   ```
   python "C:\SecondBrain\.claude\skills\blog-publish\scripts\wp_publish.py" "<notiz.md>" --dry-run
   ```
   Ziel (Update vs. Neuanlage), Titel, Status, Term-IDs und der HTML-Anfang
   werden ausgegeben. Diese Ausgabe Mario vorlegen.
3. **Freigabe abwarten.** Erst nach Marios OK der Echtlauf.
4. **Echtlauf** — derselbe Befehl ohne `--dry-run`.
5. **Beide Seiten gegenpruefen.** Frontmatter der Notiz muss weiterhin gueltig
   sein und alle Felder tragen; in der WordPress-Redaktion Formatierung,
   Kategorie und Tags sichten.

## Frontmatter-Schema

```yaml
---
title: Titel des Posts
tags:
  - linux
categories:
  - Allgemein        # Namen, nicht IDs - der Skill mappt auf Term-IDs
wp_status: draft     # optional, sonst draft
wp_id: 168           # setzt der Skill, nie von Hand
---
```

Fehlt `title`, wird der Dateiname genommen. Fehlt `categories`, greift
`default_category` aus `config.json`. Zahlen in `categories`/`tags` gelten als
bereits bekannte Term-ID.

## Grenzen

- **Nie `--status publish` ohne ausdrueckliche Ansage von Mario.** Standard ist
  `draft`, damit nichts ungeprueft live geht.
- **Nie ein anderes Frontmatter-Feld als `wp_id` schreiben.** Alles andere
  gehoert Mario.
- Kein Auto-Publish ohne vorherigen Dry-Run.
- Wikilinks werden zu Klartext (im Blog gibt es die Zielnotizen nicht) — der
  Lauf warnt fuer jeden. Bei vielen Wikilinks vorher fragen, ob der Text so
  raus soll.

## Fehlerbilder

| Meldung | Ursache und Abhilfe |
|---|---|
| `Kein Application Password im Credential Manager` | Einmalig `python scripts/set_credentials.py` — Mario muss das selbst im Terminal starten (`!`-Prefix). |
| `HTTP 401` | Application Password falsch oder widerrufen. Neues in WordPress erzeugen, erneut hinterlegen. |
| `Notiz hat kein gueltiges Frontmatter` | Kein Fehler des Werkzeugs, sondern der Schutz. Notiz reparieren, dann erneut. |
| `Bild ... nicht gefunden` | Datei liegt weder neben der Notiz noch in `07 Anhänge/`. Platzhalter bleibt im HTML stehen. |

## Technik

Repo: https://github.com/Kjeld76/obsidian-wp-publish · Tests: `python -m pytest tests/ -v`
Das Application Password liegt im Windows Credential Manager, nie im Vault.
