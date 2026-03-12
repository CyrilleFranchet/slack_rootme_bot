from utils.formatter import build_help_blocks


def test_build_help_blocks_contains_help_command() -> None:
    blocks = build_help_blocks()

    section_texts = [
        block["text"]["text"]
        for block in blocks
        if block["type"] == "section"
    ]

    assert any("/rootme help" in text for text in section_texts)
