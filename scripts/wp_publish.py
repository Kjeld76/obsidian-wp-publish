"""Obsidian-Notiz als WordPress-Entwurf anlegen oder aktualisieren."""
import argparse
import os
import sys

import credentials
import frontmatter as fm
import mdconvert
import wpclient

VAULT = r"C:\SecondBrain"
ANHANG_ORDNER = [os.path.join(VAULT, "07 Anhänge")]


def _finde_bild(name, notiz_pfad):
    """Sucht die Bilddatei zu einem ![[...]]-Embed.

    Obsidian schreibt Embeds mal als blossen Dateinamen, mal mit vollem
    Vault-Pfad. Die Blog-Bilder liegen laut gemeinsamem Frontmatter-Schema
    unter "07 Anhaenge/Blog/<slug>/", also in einem Unterordner - deshalb
    reicht ein Blick in die Anhang-Wurzel nicht.
    """
    name = name.replace("\\", "/").strip()
    kandidaten = [
        os.path.join(os.path.dirname(notiz_pfad), name),   # neben der Notiz
        os.path.join(VAULT, name),                         # vault-relativer Embed-Pfad
    ]
    kandidaten += [os.path.join(o, name) for o in ANHANG_ORDNER]
    for pfad in kandidaten:
        if os.path.isfile(pfad):
            return os.path.normpath(pfad)

    # Zuletzt rekursiv unter den Anhang-Ordnern nach dem reinen Dateinamen.
    basis = os.path.basename(name)
    for ordner in ANHANG_ORDNER:
        for wurzel, _, dateien in os.walk(ordner):
            if basis in dateien:
                return os.path.normpath(os.path.join(wurzel, basis))
    return None


def baue_payload(notiz_text, cfg, client, notiz_pfad, schreiben=True):
    """Baut den WordPress-Payload. Gibt (payload, warnungen) zurueck.

    Mit schreiben=False wird nichts an WordPress geschrieben - weder werden
    fehlende Terms angelegt noch Bilder hochgeladen. Beides wird stattdessen
    als Warnung gemeldet. Das ist der Modus des Dry-Runs, der nach eigener
    Zusage nichts sendet.
    """
    daten, roh, rumpf = fm.split_note(notiz_text)
    if roh is None:
        raise fm.FrontmatterError(
            "Notiz hat kein gueltiges Frontmatter - bitte zuerst reparieren. "
            "Es wird nichts an WordPress geschickt."
        )

    md_text, bilder, warnungen = mdconvert.preprocess(rumpf)

    url_map = {}
    for name in bilder:
        pfad = _finde_bild(name, notiz_pfad)
        if pfad is None:
            warnungen.append("Bild '%s' nicht gefunden - Platzhalter bleibt stehen" % name)
            continue
        if not schreiben:
            warnungen.append("Bild '%s' wuerde in die Mediathek hochgeladen" % name)
            continue
        url_map[name] = client.upload_media(pfad)

    html = mdconvert.ersetze_medien(mdconvert.to_html(md_text), url_map)
    titel = daten.get("title") or os.path.splitext(os.path.basename(notiz_pfad))[0]

    kat_ids, kat_fehlend = client.term_ids(
        "categories", daten.get("categories") or [cfg["default_category"]], anlegen=schreiben)
    tag_ids, tag_fehlend = client.term_ids(
        "tags", daten.get("tags") or [], anlegen=schreiben)
    for tax, fehlend in (("Kategorie", kat_fehlend), ("Tag", tag_fehlend)):
        for name in fehlend:
            warnungen.append("%s '%s' existiert nicht und wuerde neu angelegt" % (tax, name))

    payload = {
        "title": str(titel),
        "content": html,
        "status": daten.get("wp_status") or cfg["default_status"],
        "categories": kat_ids,
        "tags": tag_ids,
    }
    return payload, warnungen


def main(argv=None):
    parser = argparse.ArgumentParser(description="Obsidian-Notiz nach WordPress veroeffentlichen")
    parser.add_argument("notiz")
    parser.add_argument("--status", choices=["draft", "publish"], default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    pfad = os.path.abspath(args.notiz)
    with open(pfad, "r", encoding="utf-8") as fh:
        text = fh.read()

    cfg = credentials.load_config()
    client = wpclient.WPClient(cfg["site"], cfg["username"],
                               credentials.get_app_password(cfg["site"], cfg["username"]))

    payload, warnungen = baue_payload(text, cfg, client, pfad, schreiben=not args.dry_run)
    if args.status:
        payload["status"] = args.status
    wp_id = fm.split_note(text)[0].get("wp_id")

    for w in warnungen:
        print("Warnung: %s" % w)

    if args.dry_run:
        print("--- DRY RUN, es wird nichts gesendet ---")
        print("Ziel:   %s" % ("Update von Post %s" % wp_id if wp_id else "Neuer Post"))
        print("Titel:  %s" % payload["title"])
        print("Status: %s" % payload["status"])
        print("Terms:  categories=%s tags=%s" % (payload["categories"], payload["tags"]))
        print("HTML (erste 600 Zeichen):\n%s" % payload["content"][:600])
        return 0

    if wp_id:
        ergebnis = client.update_post(int(wp_id), payload)
        print("Post %s aktualisiert (%s)" % (ergebnis["id"], ergebnis["status"]))
    else:
        ergebnis = client.create_post(payload)
        fm.write_note(pfad, fm.set_field(text, "wp_id", int(ergebnis["id"])))
        print("Post %s angelegt (%s), wp_id ins Frontmatter geschrieben"
              % (ergebnis["id"], ergebnis["status"]))
    print("Bearbeiten: %s/wp-admin/post.php?post=%s&action=edit" % (cfg["site"], ergebnis["id"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
