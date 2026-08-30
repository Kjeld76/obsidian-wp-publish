import pytest
import frontmatter as fm

NOTE = (
    "---\n"
    "title: Test post\n"
    "tags:\n"
    "  - linux\n"
    "  - hpc\n"
    "categories:\n"
    "  - Uncategorized\n"
    "---\n"
    "\n"
    "# Heading\n"
    "\n"
    "- one\n"
    "- two\n"
)

# Exactly the damage observed in the wild: the opening --- is missing, so
# Obsidian stops recognising the block as frontmatter altogether.
BROKEN = "categories:\n  - 1\n---\n\nThis is a test post.\n"


def test_split_reads_every_field():
    data, raw, body = fm.split_note(NOTE)
    assert data["title"] == "Test post"
    assert data["tags"] == ["linux", "hpc"]
    assert data["categories"] == ["Uncategorized"]
    assert body.startswith("\n# Heading")


def test_set_field_appends_and_leaves_everything_else_alone():
    new = fm.set_field(NOTE, "wp_id", 168)
    data, _, body = fm.split_note(new)
    assert data["wp_id"] == 168
    assert data["title"] == "Test post"
    assert data["tags"] == ["linux", "hpc"]
    assert data["categories"] == ["Uncategorized"]
    assert body == fm.split_note(NOTE)[2]
    assert new.startswith("---\n") and "\n---\n" in new


def test_set_field_updates_instead_of_duplicating():
    twice = fm.set_field(fm.set_field(NOTE, "wp_id", 168), "wp_id", 999)
    assert twice.count("wp_id:") == 1
    assert fm.split_note(twice)[0]["wp_id"] == 999


def test_broken_frontmatter_is_rejected_instead_of_overwritten():
    with pytest.raises(fm.FrontmatterError):
        fm.set_field(BROKEN, "wp_id", 168)


def test_crlf_note_stays_readable():
    assert fm.split_note(NOTE.replace("\n", "\r\n"))[0]["title"] == "Test post"


def test_indented_key_of_the_same_name_is_not_touched():
    note = "---\nmeta:\n  wp_id: 1\ntitle: X\n---\n\nText\n"
    data, _, _ = fm.split_note(fm.set_field(note, "wp_id", 168))
    assert data["meta"]["wp_id"] == 1
    assert data["wp_id"] == 168
