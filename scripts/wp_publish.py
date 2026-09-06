"""Publish an Obsidian note to WordPress as a draft, or update it in place."""
import argparse
import os
import sys

import credentials
import frontmatter as fm
import mdconvert
import wpclient


def _search_roots(cfg, note_path):
    """Directories to look for embedded images, in order of preference.

    Obsidian writes embeds sometimes as a bare filename, sometimes as a full
    vault-relative path, and attachments usually live in a folder of their own.
    Everything except "next to the note" comes from config.json, so this works
    for any vault layout.
    """
    roots = [os.path.dirname(note_path)]
    vault = cfg.get("vault_path") or ""
    if vault:
        roots.append(vault)
        for folder in cfg.get("attachment_folders") or []:
            roots.append(folder if os.path.isabs(folder)
                         else os.path.join(vault, folder))
    return roots


def find_image(name, note_path, cfg):
    """Locate the file behind an ![[...]] embed. Returns a path or None."""
    name = name.replace("\\", "/").strip()
    roots = _search_roots(cfg, note_path)

    for root in roots:
        candidate = os.path.join(root, name)
        if os.path.isfile(candidate):
            return os.path.normpath(candidate)

    # Fall back to a recursive search for the bare filename. Attachments are
    # commonly filed into per-post subfolders, so looking only at the root of
    # the attachment folder is not enough.
    basename = os.path.basename(name)
    for root in roots[1:]:
        if not os.path.isdir(root):
            continue
        for current, _, files in os.walk(root):
            if basename in files:
                return os.path.normpath(os.path.join(current, basename))
    return None


def _image_texts(data):
    """images[] from the frontmatter as {normalised path or basename: (alt, caption)}."""
    texts = {}
    for item in data.get("images") or []:
        if not isinstance(item, dict) or not item.get("path"):
            continue
        key = str(item["path"]).replace("\\", "/").strip()
        entry = (str(item.get("alt") or "").strip(), str(item.get("caption") or "").strip())
        texts[key] = entry
        texts[os.path.basename(key)] = entry
    return texts


def _upload(client, path):
    """Upload via the client; returns (url, media_id). Older clients lack ids."""
    if hasattr(client, "upload_media_item"):
        item = client.upload_media_item(path)
        return item["source_url"], item.get("id")
    return client.upload_media(path), None


def build_payload(note_text, cfg, client, note_path, write=True):
    """Build the WordPress payload. Returns (payload, warnings).

    With write=False nothing is sent to WordPress: missing terms are not
    created and images are not uploaded. Both are reported as warnings
    instead. That is what --dry-run relies on, which promises to send nothing.
    """
    data, raw, body = fm.split_note(note_text)
    if raw is None:
        raise fm.FrontmatterError(
            "This note has no valid frontmatter - please repair it first. "
            "Nothing was sent to WordPress."
        )

    md_text, images, warnings = mdconvert.preprocess(body)
    texts = _image_texts(data)

    def text_for(name):
        key = name.replace("\\", "/").strip()
        return texts.get(key) or texts.get(os.path.basename(key)) or ("", "")

    url_map, alt_map = {}, {}
    for name in images:
        path = find_image(name, note_path, cfg)
        alt, caption = text_for(name)
        if alt:
            alt_map[name] = alt
        if path is None:
            warnings.append("Image '%s' not found - placeholder left in place" % name)
            continue
        if not write:
            warnings.append("Image '%s' would be uploaded to the media library" % name)
            continue
        url_map[name], media_id = _upload(client, path)
        if media_id and (alt or caption) and hasattr(client, "set_media_text"):
            client.set_media_text(media_id, alt, caption)

    html = mdconvert.replace_media(mdconvert.to_html(md_text), url_map, alt_map)

    # Featured image: from the frontmatter, never from an inline embed. The
    # old rule "embed it as well so it gets uploaded" showed it twice on the
    # page (theme header + first paragraph) - measured on three posts.
    featured_media = None
    featured = data.get("featured_image")
    if featured:
        featured = str(featured)
        path = find_image(featured, note_path, cfg)
        if path is None:
            warnings.append("Featured image '%s' not found - no featured image set" % featured)
        elif not write:
            warnings.append("Featured image '%s' would be uploaded and set" % featured)
        else:
            _, featured_media = _upload(client, path)
            if featured_media is None:
                warnings.append("Featured image '%s' uploaded, but the client returned no id - not set" % featured)
            else:
                alt, caption = text_for(featured)
                if (alt or caption) and hasattr(client, "set_media_text"):
                    client.set_media_text(featured_media, alt, caption)
    title = data.get("title") or os.path.splitext(os.path.basename(note_path))[0]

    cat_ids, cat_missing = client.term_ids(
        "categories", data.get("categories") or [cfg["default_category"]], create=write)
    tag_ids, tag_missing = client.term_ids(
        "tags", data.get("tags") or [], create=write)
    for taxonomy, missing in (("Category", cat_missing), ("Tag", tag_missing)):
        for name in missing:
            warnings.append("%s '%s' does not exist and would be created" % (taxonomy, name))

    payload = {
        "title": str(title),
        "content": html,
        "status": data.get("wp_status") or cfg["default_status"],
        "categories": cat_ids,
        "tags": tag_ids,
    }
    if featured_media:
        payload["featured_media"] = featured_media
    return payload, warnings


def main(argv=None):
    parser = argparse.ArgumentParser(description="Publish an Obsidian note to WordPress")
    parser.add_argument("note", help="path to the .md file")
    parser.add_argument("--status", choices=["draft", "publish"], default=None,
                        help="override the post status (default comes from the note or config)")
    parser.add_argument("--dry-run", action="store_true",
                        help="show what would happen without sending anything")
    args = parser.parse_args(argv)

    path = os.path.abspath(args.note)
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()

    cfg = credentials.load_config()
    client = wpclient.WPClient(cfg["site"], cfg["username"],
                               credentials.get_app_password(cfg["site"], cfg["username"]))

    payload, warnings = build_payload(text, cfg, client, path, write=not args.dry_run)
    if args.status:
        payload["status"] = args.status
    wp_id = fm.split_note(text)[0].get("wp_id")

    for w in warnings:
        print("Warning: %s" % w)

    if args.dry_run:
        print("--- DRY RUN, nothing is sent ---")
        print("Target: %s" % ("update of post %s" % wp_id if wp_id else "new post"))
        print("Title:  %s" % payload["title"])
        print("Status: %s" % payload["status"])
        print("Terms:  categories=%s tags=%s" % (payload["categories"], payload["tags"]))
        print("Featured image: %s" % (fm.split_note(text)[0].get("featured_image") or "none"))
        print("HTML (first 600 characters):\n%s" % payload["content"][:600])
        return 0

    if wp_id:
        result = client.update_post(int(wp_id), payload)
        print("Post %s updated (%s)" % (result["id"], result["status"]))
    else:
        result = client.create_post(payload)
        fm.write_note(path, fm.set_field(text, "wp_id", int(result["id"])))
        print("Post %s created (%s), wp_id written to the frontmatter"
              % (result["id"], result["status"]))
    print("Edit: %s/wp-admin/post.php?post=%s&action=edit" % (cfg["site"], result["id"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
