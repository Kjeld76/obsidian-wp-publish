import wp_publish as wp

NOTE = (
    "---\ntitle: My Post\ntags:\n  - linux\ncategories:\n  - Uncategorized\n---\n"
    "\nText with a code block:\n\n```bash\nuname -a\n```\n"
)

CFG = {"site": "https://example.test", "username": "someone",
       "default_status": "draft", "default_category": "Uncategorized",
       "vault_path": "", "attachment_folders": []}


def cfg_with(vault, folders):
    """A config pointing at a temporary vault, for the image lookup tests."""
    merged = dict(CFG)
    merged["vault_path"] = str(vault)
    merged["attachment_folders"] = [str(f) for f in folders]
    return merged


class FakeClient:
    """Knows every term. Records whether it was allowed to create or upload."""

    def __init__(self):
        self.create_flags = []
        self.uploads = []

    def term_ids(self, taxonomy, names, create=True):
        self.create_flags.append(create)
        base = {"tags": 10, "categories": 20}[taxonomy]
        return [base + i for i, _ in enumerate(names or [])], []

    def upload_media(self, path):
        self.uploads.append(path)
        return "https://example.test/wp-content/uploads/image.png"


class FakeClientWithoutTerms(FakeClient):
    """Knows no term at all - how a fresh blog behaves."""

    def term_ids(self, taxonomy, names, create=True):
        self.create_flags.append(create)
        if create:
            return [99 for _ in names or []], []
        return [], [str(n) for n in names or []]


def test_payload_carries_title_status_and_terms():
    payload, _ = wp.build_payload(NOTE, CFG, FakeClient(), "/tmp/Note.md")
    assert payload["title"] == "My Post"
    assert payload["status"] == "draft"
    assert payload["tags"] == [10] and payload["categories"] == [20]
    assert "<code" in payload["content"] and "uname -a" in payload["content"]


def test_filename_is_used_when_title_is_missing():
    without = NOTE.replace("title: My Post\n", "")
    payload, _ = wp.build_payload(without, CFG, FakeClient(), "/tmp/Building Spack.md")
    assert payload["title"] == "Building Spack"


def test_frontmatter_does_not_leak_into_the_content():
    payload, _ = wp.build_payload(NOTE, CFG, FakeClient(), "/tmp/Note.md")
    assert "categories" not in payload["content"] and "---" not in payload["content"]


def test_dry_run_must_not_create_terms():
    """Regression: the dry run used to create a category and a tag for real."""
    client = FakeClientWithoutTerms()
    payload, warnings = wp.build_payload(NOTE, CFG, client, "/tmp/Note.md", write=False)
    assert client.create_flags == [False, False]
    assert payload["categories"] == [] and payload["tags"] == []
    assert any("would be created" in w for w in warnings)


def test_dry_run_must_not_upload_an_image():
    note = NOTE.replace("Text with a code block:", "![[diagram.png]]")
    client = FakeClient()
    _, warnings = wp.build_payload(note, CFG, client, "/tmp/Note.md", write=False)
    assert client.uploads == []
    assert any("diagram.png" in w for w in warnings)


def test_real_run_creates_terms():
    client = FakeClientWithoutTerms()
    payload, _ = wp.build_payload(NOTE, CFG, client, "/tmp/Note.md", write=True)
    assert client.create_flags == [True, True]
    assert payload["categories"] == [99]


# --- image lookup ----------------------------------------------------------
# Attachments are commonly filed per post, so they sit in a SUBfolder of the
# attachment directory. Looking only at its root is not enough.

def test_image_is_found_in_a_subfolder_of_the_attachment_dir(tmp_path):
    attachments = tmp_path / "attachments"
    (attachments / "blog" / "my-post").mkdir(parents=True)
    image = attachments / "blog" / "my-post" / "diagram.png"
    image.write_bytes(b"x")
    cfg = cfg_with(tmp_path, [attachments])
    assert wp.find_image("diagram.png", str(tmp_path / "Note.md"), cfg) == str(image)


def test_image_with_spaces_in_the_name_is_found(tmp_path):
    """Obsidian's default when pasting: 'Pasted image 20260829.png'."""
    attachments = tmp_path / "attachments"
    (attachments / "blog").mkdir(parents=True)
    image = attachments / "blog" / "Pasted image 20260829.png"
    image.write_bytes(b"x")
    cfg = cfg_with(tmp_path, [attachments])
    found = wp.find_image("Pasted image 20260829.png", str(tmp_path / "N.md"), cfg)
    assert found == str(image)


def test_vault_relative_embed_path_is_resolved(tmp_path):
    """Obsidian also writes embeds with the full vault-relative path."""
    (tmp_path / "attachments" / "blog" / "slug").mkdir(parents=True)
    image = tmp_path / "attachments" / "blog" / "slug" / "image.png"
    image.write_bytes(b"x")
    cfg = cfg_with(tmp_path, [tmp_path / "attachments"])
    found = wp.find_image("attachments/blog/slug/image.png", str(tmp_path / "N.md"), cfg)
    assert found == str(image)


def test_image_next_to_the_note_is_found_without_any_vault_config(tmp_path):
    """A configured vault is optional - next to the note always works."""
    image = tmp_path / "image.png"
    image.write_bytes(b"x")
    assert wp.find_image("image.png", str(tmp_path / "N.md"), CFG) == str(image)


def test_relative_attachment_folder_is_resolved_against_the_vault(tmp_path):
    (tmp_path / "assets").mkdir()
    image = tmp_path / "assets" / "image.png"
    image.write_bytes(b"x")
    cfg = dict(CFG)
    cfg["vault_path"] = str(tmp_path)
    cfg["attachment_folders"] = ["assets"]          # relative, not absolute
    assert wp.find_image("image.png", str(tmp_path / "N.md"), cfg) == str(image)


def test_missing_image_returns_none(tmp_path):
    cfg = cfg_with(tmp_path, [tmp_path])
    assert wp.find_image("nothere.png", str(tmp_path / "N.md"), cfg) is None


# --- featured image and alt texts -----------------------------------------
# The featured image used to require an inline embed, which made it appear
# twice on the page (theme header + first paragraph). Now it comes from the
# frontmatter and is set as featured_media; alt texts come from images[].

class FakeClientWithIds(FakeClient):
    """Returns media items with ids and records alt-text updates."""

    def __init__(self):
        super().__init__()
        self.alts = []

    def upload_media_item(self, path):
        self.uploads.append(path)
        return {"id": 7, "source_url": "https://example.test/wp-content/uploads/image.png"}

    def set_media_text(self, media_id, alt, caption):
        self.alts.append((media_id, alt, caption))


def note_with_featured(tmp_path, embed=False):
    (tmp_path / "attachments" / "blog" / "slug").mkdir(parents=True)
    (tmp_path / "attachments" / "blog" / "slug" / "hero.png").write_bytes(b"x")
    body = "![[attachments/blog/slug/hero.png]]\n\nText.\n" if embed else "Text.\n"
    note = (
        "---\ntitle: My Post\ncategories:\n  - Uncategorized\n"
        "featured_image: attachments/blog/slug/hero.png\n"
        "images:\n  - path: attachments/blog/slug/hero.png\n"
        "    alt: \"A grey hero image\"\n    caption: \"Grey is a state\"\n---\n\n" + body
    )
    return note, cfg_with(tmp_path, [tmp_path / "attachments"])


def test_featured_image_is_uploaded_and_set_without_an_embed(tmp_path):
    note, cfg = note_with_featured(tmp_path)
    client = FakeClientWithIds()
    payload, warnings = wp.build_payload(note, cfg, client, str(tmp_path / "N.md"))
    assert payload["featured_media"] == 7
    assert any(p.endswith("hero.png") for p in client.uploads)
    assert "<img" not in payload["content"]                  # not duplicated into the text
    assert (7, "A grey hero image", "Grey is a state") in client.alts


def test_dry_run_does_not_upload_the_featured_image(tmp_path):
    note, cfg = note_with_featured(tmp_path)
    client = FakeClientWithIds()
    payload, warnings = wp.build_payload(note, cfg, client, str(tmp_path / "N.md"), write=False)
    assert client.uploads == [] and client.alts == []
    assert "featured_media" not in payload
    assert any("hero.png" in w and "featured" in w.lower() for w in warnings)


def test_missing_featured_file_is_a_warning_not_a_crash(tmp_path):
    note, cfg = note_with_featured(tmp_path)
    note = note.replace("slug/hero.png", "slug/nothere.png")
    payload, warnings = wp.build_payload(note, cfg, FakeClientWithIds(), str(tmp_path / "N.md"))
    assert "featured_media" not in payload
    assert any("nothere.png" in w for w in warnings)


def test_alt_text_from_images_lands_in_the_img_tag(tmp_path):
    note, cfg = note_with_featured(tmp_path, embed=True)
    client = FakeClientWithIds()
    payload, _ = wp.build_payload(note, cfg, client, str(tmp_path / "N.md"))
    assert 'alt="A grey hero image"' in payload["content"]
    assert 'alt=""' not in payload["content"]


def test_note_without_featured_image_behaves_as_before():
    payload, warnings = wp.build_payload(NOTE, CFG, FakeClientWithIds(), "/tmp/Note.md")
    assert "featured_media" not in payload and warnings == []
