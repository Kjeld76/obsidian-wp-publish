# obsidian-wp-publish

Publish an Obsidian note to WordPress as a draft, and update the same post on
every later run instead of creating duplicates.

The point of this tool is what it *doesn't* do to your notes. It exists because
the plugin I used before rewrote the whole YAML frontmatter on publish and
reproducibly destroyed it — on the second run the opening `---` was gone, which
means Obsidian stops seeing frontmatter at all and renders it as body text.

So the core here is a deliberately paranoid frontmatter writer: surgical
line-level edits instead of a YAML round-trip, and a self-check before anything
touches the disk. If the result wouldn't parse, or any field other than the one
being set has changed, the write is aborted and your note stays as it was.

> **Status:** this works for me. It is a small personal tool, published in case
> it is useful to someone else. Issues are read, but nothing is promised —
> please don't rely on it for anything you can't afford to lose.

## What it does

- Converts Obsidian Markdown to HTML — fenced code blocks, tables, lists, links
- Uploads embedded images (`![[image.png]]`) to the media library and rewrites
  the links, reusing an image that is already there instead of duplicating it
- Maps category and tag *names* to WordPress term IDs, creating what's missing
- Turns wikilinks into plain text and warns for each one, since the target note
  doesn't exist on your blog
- Writes `wp_id` back into the note — the only field it ever touches

## Requirements

Python 3.8+ and:

```
python -m pip install requests markdown keyring pytest
```

`keyring` uses whatever credential store your OS provides — Windows Credential
Manager, macOS Keychain, or Secret Service on Linux.

## Setup

Copy the example config and fill in your own values:

```
cp config.example.json config.json
```

```json
{
  "site": "https://example.com",
  "username": "your-wordpress-username",
  "vault_path": "",
  "attachment_folders": [],
  "default_category": "Uncategorized",
  "default_status": "draft"
}
```

| Key | Meaning |
|---|---|
| `site` | Your WordPress site, without a trailing slash |
| `username` | Your WordPress username |
| `vault_path` | Absolute path to your vault. Optional — without it, images are only looked for next to the note |
| `attachment_folders` | Where your attachments live, absolute or relative to the vault. Searched recursively, so per-post subfolders are found |
| `default_category` | Used when a note has no `categories` |
| `default_status` | `draft` unless you have a good reason |

Then create an application password in WordPress (Users → Profile → Application
Passwords) and store it once:

```
python scripts/set_credentials.py
```

It is read via `getpass`, so it is never echoed or logged. It goes into your OS
credential store — never into `config.json`, never into the vault. `config.json`
is gitignored because it holds your site and username.

## Usage

Always look before you leap:

```
python scripts/wp_publish.py "path/to/note.md" --dry-run
```

The dry run shows the target (new post or update), title, status, resolved term
IDs and the start of the generated HTML. It sends nothing — no terms are
created, no images uploaded. Then, for real:

```
python scripts/wp_publish.py "path/to/note.md"
```

`--status publish` exists but the default is `draft` on purpose, so nothing goes
live unreviewed.

## Frontmatter

```yaml
---
title: Title of the post
tags:
  - linux
categories:
  - Uncategorized      # names, not IDs — the tool maps them
wp_status: draft       # optional, falls back to default_status
wp_id: 168             # written by the tool, never by hand
---
```

Without `title` the filename is used. Integers in `categories` or `tags` are
passed through as term IDs you already know.

`wp_id` is what makes re-publishing safe: if it's there, the existing post is
updated rather than a second one created.

## Using it with Claude Code

This started life as a Claude Code skill, and `SKILL.example.md` is the skill
file. Copy it to `SKILL.md` and adapt the wording — your own site, your
language, and the names of any neighbouring skills so this one isn't triggered
by mistake. `SKILL.md` is gitignored on purpose, so your local version stays
yours.

None of this is required. The scripts are plain Python and work on their own.

## What it deliberately does not do

- It does not send `slug`, `excerpt` or the featured image. WordPress derives
  the permalink from the title, and the rest you set in the editor.
- It does not touch any frontmatter field except `wp_id`.
- It does not publish without you asking for it.

## Known limitations

- Filenames are normalised to ASCII for predictable media slugs. Characters
  without an ASCII decomposition — `ß`, CJK, emoji — are dropped rather than
  transliterated, so `Größe.png` becomes `groe.png`.
- Callouts become plain blockquotes with a bold title.
- Only tested against a single self-hosted WordPress site.

## Tests

```
python -m pytest tests/ -v
```

The tests run entirely against fakes, so they need no network and no
credentials. Worth knowing: four real bugs once survived a completely green
suite, because the fakes modelled WordPress the way I *imagined* it rather than
how it behaves. Several tests are regressions for exactly those cases —
the dry run that wrote, term names containing `&` that could never be found,
images in subfolders, and a media upload that duplicated on every run.

## License

MIT — see [LICENSE](LICENSE).
