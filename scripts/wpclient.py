"""Duenner Client fuer die WordPress-REST-API v2."""
import html
import mimetypes
import os

import requests


class WPError(Exception):
    pass


class WPClient:
    def __init__(self, site, user, app_password):
        self.base = site.rstrip("/") + "/wp-json"
        self.session = requests.Session()
        self.session.auth = (user, app_password)
        self.session.headers.update({"Accept": "application/json"})
        self._term_cache = {}

    def _call(self, methode, pfad, **kwargs):
        kwargs.setdefault("timeout", 60)
        antwort = self.session.request(methode, self.base + pfad, **kwargs)
        if antwort.status_code >= 400:
            # Bewusst ohne Auth-Header/Passwort in der Meldung.
            raise WPError("%s %s -> HTTP %s: %s"
                          % (methode, pfad, antwort.status_code, antwort.text[:300]))
        return antwort.json()

    def _alle_terms(self, taxonomy):
        """Vollstaendige Termliste einer Taxonomie, einmal je Lauf geladen.

        Bewusst OHNE den search-Parameter: Namen mit Sonderzeichen liegen in
        WordPress als HTML-Entity in der Datenbank ("Code &amp; Technik"), die
        Suche nach dem Klartextnamen liefert dann null Treffer. Am echten Blog
        am 29.08.2026 gemessen - der Client haette ein Duplikat angelegt.
        """
        if taxonomy in self._term_cache:
            return self._term_cache[taxonomy]
        alle = []
        seite = 1
        while True:
            teil = self._call("GET", "/wp/v2/%s" % taxonomy,
                              params={"per_page": 100, "page": seite, "hide_empty": "false"})
            alle.extend(teil)
            if len(teil) < 100:
                break
            seite += 1
        self._term_cache[taxonomy] = alle
        return alle

    @staticmethod
    def _term_key(name):
        return html.unescape(str(name)).strip().lower()

    def term_ids(self, taxonomy, namen, anlegen=True):
        """Namen auf Term-IDs abbilden. Gibt (ids, fehlende_namen) zurueck.

        Zahlen werden unveraendert als bereits bekannte ID durchgereicht.
        Mit anlegen=False wird nichts geschrieben: unbekannte Terms landen
        stattdessen in der zweiten Rueckgabeliste. Das braucht der Dry-Run,
        der nach eigener Zusage nichts an WordPress sendet.
        """
        ids = []
        fehlend = []
        for name in namen or []:
            if isinstance(name, int) and not isinstance(name, bool):
                ids.append(name)
                continue
            name = str(name).strip()
            if not name:
                continue
            gesucht = self._term_key(name)
            passend = [t for t in self._alle_terms(taxonomy)
                       if self._term_key(t.get("name", "")) == gesucht]
            if passend:
                ids.append(passend[0]["id"])
            elif anlegen:
                neu = self._call("POST", "/wp/v2/%s" % taxonomy, json={"name": name})
                self._term_cache[taxonomy].append(neu)      # nicht zweimal anlegen
                ids.append(neu["id"])
            else:
                fehlend.append(name)
        return ids, fehlend

    def upload_media(self, pfad):
        name = os.path.basename(pfad)
        typ = mimetypes.guess_type(name)[0] or "application/octet-stream"
        with open(pfad, "rb") as fh:
            daten = fh.read()
        antwort = self._call("POST", "/wp/v2/media", data=daten, headers={
            "Content-Disposition": 'attachment; filename="%s"' % name,
            "Content-Type": typ,
        })
        return antwort["source_url"]

    def get_post(self, post_id):
        return self._call("GET", "/wp/v2/posts/%s" % post_id, params={"context": "edit"})

    def create_post(self, payload):
        return self._call("POST", "/wp/v2/posts", json=payload)

    def update_post(self, post_id, payload):
        return self._call("POST", "/wp/v2/posts/%s" % post_id, json=payload)
