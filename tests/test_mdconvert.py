import mdconvert as mc


def test_embedded_image_becomes_a_placeholder():
    text, images, _ = mc.preprocess("Before\n\n![[diagram.png]]\n\nAfter\n")
    assert images == ["diagram.png"]
    assert "WPMEDIA::diagram.png" in text and "![[" not in text


def test_wikilink_becomes_plain_text_and_warns():
    text, _, warnings = mc.preprocess("See [[HPC cluster|the cluster]] and [[Blog]].\n")
    assert "the cluster" in text and "Blog" in text and "[[" not in text
    assert len(warnings) == 2


def test_callout_becomes_a_blockquote_with_a_bold_line():
    text, _, _ = mc.preprocess("> [!warning] Careful\n> second line\n")
    assert "> **Careful**" in text and "[!warning]" not in text


def test_code_block_keeps_its_language():
    html = mc.to_html("```bash\nls -la\n```\n")
    assert "<pre>" in html and 'class="language-bash"' in html and "ls -la" in html


def test_heading_list_and_link():
    html = mc.to_html("## Title\n\n- one\n- two\n\n[Example](https://example.com)\n")
    assert "<h2>Title</h2>" in html
    assert "<li>one</li>" in html
    assert '<a href="https://example.com">Example</a>' in html
