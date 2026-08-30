"""Thin client for the WordPress REST API v2."""
import html
import mimetypes
import os
import re
import unicodedata

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

    def _call(self, method, path, **kwargs):
        kwargs.setdefault("timeout", 60)
        response = self.session.request(method, self.base + path, **kwargs)
        if response.status_code >= 400:
            # Deliberately without the auth header or password in the message.
            raise WPError("%s %s -> HTTP %s: %s"
                          % (method, path, response.status_code, response.text[:300]))
        return response.json()

    def _all_terms(self, taxonomy):
        """The full term list of a taxonomy, fetched once per run.

        Deliberately WITHOUT the search parameter: names containing special
        characters are stored as HTML entities in WordPress ("Code &amp;
        Technik"), so searching for the plain text name returns zero results.
        Measured against a live blog - the client used to create a duplicate.
        """
        if taxonomy in self._term_cache:
            return self._term_cache[taxonomy]
        all_terms = []
        page = 1
        while True:
            chunk = self._call("GET", "/wp/v2/%s" % taxonomy,
                               params={"per_page": 100, "page": page, "hide_empty": "false"})
            all_terms.extend(chunk)
            if len(chunk) < 100:
                break
            page += 1
        self._term_cache[taxonomy] = all_terms
        return all_terms

    @staticmethod
    def _term_key(name):
        return html.unescape(str(name)).strip().lower()

    def term_ids(self, taxonomy, names, create=True):
        """Map names to term IDs. Returns (ids, missing_names).

        Integers are passed through unchanged as known IDs. With create=False
        nothing is written: unknown terms end up in the second return value
        instead. The dry run needs this, since it promises to send nothing.
        """
        ids = []
        missing = []
        for name in names or []:
            if isinstance(name, int) and not isinstance(name, bool):
                ids.append(name)
                continue
            name = str(name).strip()
            if not name:
                continue
            wanted = self._term_key(name)
            matches = [t for t in self._all_terms(taxonomy)
                       if self._term_key(t.get("name", "")) == wanted]
            if matches:
                ids.append(matches[0]["id"])
            elif create:
                new = self._call("POST", "/wp/v2/%s" % taxonomy, json={"name": name})
                self._term_cache[taxonomy].append(new)      # do not create it twice
                ids.append(new["id"])
            else:
                missing.append(name)
        return ids, missing

    @staticmethod
    def media_filename(path):
        """A deterministic, WordPress-safe filename.

        Applied before the upload on purpose, so the WordPress slug is
        predictable and a later run finds the same file again.
        """
        stem, ext = os.path.splitext(os.path.basename(path))
        stem = unicodedata.normalize("NFKD", stem)
        stem = stem.encode("ascii", "ignore").decode("ascii")
        stem = re.sub(r"[^A-Za-z0-9]+", "-", stem).strip("-").lower()
        return (stem or "image") + ext.lower()

    def upload_media(self, path, reuse=True):
        """Upload a file and return its source_url.

        If it is already in the media library, the existing one is reused.
        Without this, every republish created another copy - measured live
        ('some-image-1.png' after the second run).
        """
        name = self.media_filename(path)
        if reuse:
            hits = self._call("GET", "/wp/v2/media",
                              params={"slug": os.path.splitext(name)[0], "per_page": 5})
            if hits:
                return hits[0]["source_url"]
        mime = mimetypes.guess_type(name)[0] or "application/octet-stream"
        with open(path, "rb") as fh:
            data = fh.read()
        response = self._call("POST", "/wp/v2/media", data=data, headers={
            "Content-Disposition": 'attachment; filename="%s"' % name,
            "Content-Type": mime,
        })
        return response["source_url"]

    def get_post(self, post_id):
        return self._call("GET", "/wp/v2/posts/%s" % post_id, params={"context": "edit"})

    def create_post(self, payload):
        return self._call("POST", "/wp/v2/posts", json=payload)

    def update_post(self, post_id, payload):
        return self._call("POST", "/wp/v2/posts/%s" % post_id, json=payload)
