"""Unit tests for app.services.nlp.cleaner — no external dependencies."""
import pytest

from app.services.nlp.cleaner import (
    MAX_NLP_CHARS,
    clean_text,
    remove_reply_chain,
    remove_signature,
    strip_html,
)


def test_strip_html_removes_tags():
    result = strip_html("<p>Hello <b>world</b></p>")
    assert "Hello" in result
    assert "world" in result
    assert "<p>" not in result
    assert "<b>" not in result


def test_strip_html_handles_plain_text():
    plain = "No HTML here, just plain text."
    result = strip_html(plain)
    assert "plain text" in result
    assert "<" not in result


def test_remove_reply_chain_on_forwarded_email():
    text = "Please find attached.\n\nOn Mon, Jan 5 wrote:\n> Here is the original message."
    result = remove_reply_chain(text)
    assert "original message" not in result
    assert "Please find attached" in result


def test_remove_reply_chain_angle_bracket_lines():
    text = "My reply here.\n> Quoted line 1\n> Quoted line 2"
    result = remove_reply_chain(text)
    assert "> Quoted line 1" not in result
    assert "My reply here" in result


def test_remove_signature_double_dash():
    text = "Meeting confirmed.\n-- \nJohn Doe\nCTO, Acme Corp"
    result = remove_signature(text)
    assert "John Doe" not in result
    assert "Meeting confirmed" in result


def test_remove_signature_best_regards():
    text = "Please submit the report.\nBest regards\nAlice"
    result = remove_signature(text)
    assert "Alice" not in result
    assert "submit the report" in result


def test_clean_text_full_pipeline():
    html = (
        "<p>Please <b>submit</b> your report.</p>"
        "<p>On Mon, Jan 1 wrote:<br>&gt; previous message</p>"
        "<p>Best regards<br>Bob</p>"
    )
    result = clean_text(html)
    assert "submit" in result
    assert "your report" in result
    # Signature and reply chain should be stripped
    assert "Bob" not in result


def test_clean_text_truncates_at_max_chars():
    long_text = "a" * 5000
    result = clean_text(long_text)
    assert len(result) <= MAX_NLP_CHARS
