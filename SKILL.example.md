---
name: blog-publish
description: >-
  Publishes an Obsidian note to a WordPress site as a draft (REST API +
  application password) and updates the same post on a later run via wp_id
  instead of duplicating it. Converts Obsidian Markdown to HTML (code blocks,
  lists, links, headings), uploads embedded images to the media library and
  maps category and tag names to term IDs. Use this skill when the user wants
  to publish, upload or update a blog post - e.g. "publish this note",
  "put this on the blog", "update the blog post", "/blog-publish". NOT for
  writing the text itself, not for capturing post ideas, and not for sites
  other than the one in config.json.
---

# Blog Publish

Takes a note from the vault to WordPress as a draft — and on the next run the
same note to the same post, without duplicating it and without damaging the
frontmatter.

> Copy this file to `SKILL.md` and adapt it. `SKILL.md` is gitignored, so your
> own site, wording and language stay local. If your vault has related skills
> or capture routines, name them under "boundaries" so this one is not
> triggered by mistake.

## Procedure

1. **Check the note.** The frontmatter has to be valid (see schema). If it is
   not, the tool aborts and sends nothing — that is intended, do not work
   around it.
2. **Show a dry run.** Always first:
   ```
   python scripts/wp_publish.py "<note.md>" --dry-run
   ```
   It prints the target (update or new post), title, status, resolved term IDs
   and the beginning of the HTML. Show that output to the user.
3. **Wait for approval.** Only publish for real once the user agrees.
4. **Real run** — the same command without `--dry-run`.
5. **Verify both sides.** The note's frontmatter must still be valid and carry
   every field; in WordPress check formatting, category and tags.

A habit worth keeping, learned the hard way: count on the live system before
and after — categories, tags, media. A green test suite cannot tell you that
your assumption about WordPress was wrong; a changed count can.

## Frontmatter schema

```yaml
---
title: Title of the post
tags:
  - linux
categories:
  - Uncategorized      # names, not IDs - the tool maps them
wp_status: draft       # optional, otherwise default_status from config.json
wp_id: 168             # set by the tool, never by hand
---
```

Without `title` the filename is used. Without `categories`, `default_category`
from `config.json` applies. Integers in `categories`/`tags` count as known
term IDs.

## Boundaries

- **Never `--status publish` without the user explicitly asking.** The default
  is `draft` so nothing goes live unreviewed.
- **Never write any frontmatter field other than `wp_id`.** Everything else
  belongs to the user.
- No publishing without a preceding dry run.
- Wikilinks become plain text — the target notes do not exist on the blog. The
  run warns for each one. If a note is full of them, ask before publishing.

## Failure modes

| Message | Cause and remedy |
|---|---|
| `No application password in the credential store` | Run `python scripts/set_credentials.py` once. It prompts interactively, so the user has to start it themselves. |
| `HTTP 401` | Application password wrong or revoked. Create a new one in WordPress and store it again. |
| `This note has no valid frontmatter` | Not a tool failure but the safeguard. Repair the note, then retry. |
| `Image ... not found` | The file is neither next to the note nor under a configured attachment folder. The placeholder stays in the HTML. |

## Technical

Tests: `python -m pytest tests/ -v`
The application password lives in the OS credential store, never in the vault.
