"""Unit tests for app.services.nlp.ner_extractor — no network / no model download."""
from __future__ import annotations

import pytest

from app.services.nlp.ner_extractor import (
    NERDateEntity,
    extract_date_entities,
    has_temporal_entities,
    reset_model_cache,
)


# ---------------------------------------------------------------------------
# Helpers — mock spaCy model returned by _get_nlp()
# ---------------------------------------------------------------------------

class _MockEnt:
    def __init__(self, text: str, label_: str, start_char: int, end_char: int) -> None:
        self.text = text
        self.label_ = label_
        self.start_char = start_char
        self.end_char = end_char


class _MockDoc:
    def __init__(self, ents: list) -> None:
        self.ents = ents


def _make_nlp(*entities: _MockEnt):
    """Return a callable that mimics spacy.Language and yields fixed entities."""
    doc = _MockDoc(list(entities))
    return lambda text: doc  # noqa: ARG005


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_cache():
    """Ensure the module-level NLP singleton is cleared between tests."""
    reset_model_cache()
    yield
    reset_model_cache()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_extract_date_entity(monkeypatch):
    import app.services.nlp.ner_extractor as m

    monkeypatch.setattr(m, "_get_nlp", lambda: _make_nlp(
        _MockEnt("April 10, 2026", "DATE", 10, 24),
    ))

    entities = extract_date_entities("Submit by April 10, 2026.")
    assert len(entities) == 1
    assert entities[0].label == "DATE"
    assert entities[0].text == "April 10, 2026"
    assert entities[0].start_char == 10
    assert entities[0].end_char == 24


def test_extract_time_entity(monkeypatch):
    import app.services.nlp.ner_extractor as m

    monkeypatch.setattr(m, "_get_nlp", lambda: _make_nlp(
        _MockEnt("5pm", "TIME", 0, 3),
    ))

    entities = extract_date_entities("5pm meeting")
    assert len(entities) == 1
    assert entities[0].label == "TIME"


def test_non_date_entities_filtered(monkeypatch):
    """PERSON / ORG entities must not appear in the result."""
    import app.services.nlp.ner_extractor as m

    monkeypatch.setattr(m, "_get_nlp", lambda: _make_nlp(
        _MockEnt("Google", "ORG", 0, 6),
        _MockEnt("Alice", "PERSON", 7, 12),
    ))

    entities = extract_date_entities("Google Alice")
    assert entities == []


def test_multiple_date_entities(monkeypatch):
    import app.services.nlp.ner_extractor as m

    monkeypatch.setattr(m, "_get_nlp", lambda: _make_nlp(
        _MockEnt("April 5", "DATE", 0, 7),
        _MockEnt("April 20", "DATE", 20, 28),
    ))

    entities = extract_date_entities("April 5 first, then April 20.")
    assert len(entities) == 2


def test_returns_empty_on_empty_text(monkeypatch):
    import app.services.nlp.ner_extractor as m

    monkeypatch.setattr(m, "_get_nlp", lambda: _make_nlp())
    assert extract_date_entities("") == []
    assert extract_date_entities("   ") == []


def test_fallback_when_model_unavailable(monkeypatch):
    """When _get_nlp() returns None, extract_date_entities returns []."""
    import app.services.nlp.ner_extractor as m

    monkeypatch.setattr(m, "_get_nlp", lambda: None)
    assert extract_date_entities("Due by April 10, 2026.") == []


def test_has_temporal_entities_true(monkeypatch):
    import app.services.nlp.ner_extractor as m

    monkeypatch.setattr(m, "_get_nlp", lambda: _make_nlp(
        _MockEnt("tomorrow", "DATE", 7, 15),
    ))
    assert has_temporal_entities("Due by tomorrow") is True


def test_has_temporal_entities_false(monkeypatch):
    import app.services.nlp.ner_extractor as m

    monkeypatch.setattr(m, "_get_nlp", lambda: _make_nlp())
    assert has_temporal_entities("No dates here at all.") is False
