"""Duenner Client fuer die WordPress-REST-API v2."""
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

    def _call(self, methode, pfad, **kwargs):
        kwargs.setdefault("timeout", 60)
        antwort = self.session.request(methode, self.base + pfad, **kwargs)
        if antwort.status_code >= 400:
            # Bewusst ohne Auth-Header/Passwort in der Meldung.
            raise WPError("%s %s -> HTTP %s: %s"
                          % (methode, pfad, antwort.status_code, antwort.text[:300]))
        return antwort.json()

    def term_ids(self, taxonomy, namen):
        """Namen auf Term-IDs abbilden; fehlende Terms werden angelegt.

        Zahlen werden unveraendert als bereits bekannte ID durchgereicht.
        """
        ids = []
        for name in namen or []:
            if isinstance(name, int) and not isinstance(name, bool):
                ids.append(name)
                continue
            name = str(name).strip()
            if not name:
                continue
            treffer = self._call("GET", "/wp/v2/%s" % taxonomy,
                                 params={"search": name, "per_page": 100})
            passend = [t for t in treffer if t.get("name", "").lower() == name.lower()]
            if passend:
                ids.append(passend[0]["id"])
            else:
                ids.append(self._call("POST", "/wp/v2/%s" % taxonomy, json={"name": name})["id"])
        return ids

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
