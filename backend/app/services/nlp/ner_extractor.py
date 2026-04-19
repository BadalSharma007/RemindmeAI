"""spaCy NER-based temporal entity extractor.

Phase 2 addition: uses en_core_web_sm to identify DATE and TIME named
entities before passing them to dateparser.  Falls back gracefully to an
empty list when the model is not installed — the deadline_extractor then
reverts to its full-text dateparser scan (Phase 1 behaviour).
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_nlp = None           # spaCy Language object | False (tried, unavailable)
_nlp_lock = threading.Lock()
_MODEL_NAME = "en_core_web_sm"


def _get_nlp():
    """Return the lazy-loaded spaCy model, or None if unavailable."""
    global _nlp
    if _nlp is None:
        with _nlp_lock:
            if _nlp is None:
                try:
                    import spacy  # noqa: PLC0415

                    _nlp = spacy.load(_MODEL_NAME)
                    logger.info("spaCy model loaded: %s", _MODEL_NAME)
                except OSError:
                    logger.warning(
                        "spaCy model '%s' not found — "
                        "run: python -m spacy download %s",
                        _MODEL_NAME,
                        _MODEL_NAME,
                    )
                    _nlp = False  # sentinel: avoid retrying on every call
                except Exception as exc:  # noqa: BLE001
                    logger.warning("spaCy load error: %s", exc)
                    _nlp = False

    return None if _nlp is False else _nlp


@dataclass
class NERDateEntity:
    """A DATE or TIME entity identified by spaCy."""

    text: str         # raw entity span text as it appears in the document
    label: str        # "DATE" or "TIME"
    start_char: int   # character offset in the original text
    end_char: int


def extract_date_entities(text: str) -> list[NERDateEntity]:
    """
    Run spaCy NER on *text* and return all DATE / TIME entities.

    Falls back to an empty list when the spaCy model is unavailable,
    allowing callers to use alternative extraction strategies.
    """
    if not text or not text.strip():
        return []

    nlp = _get_nlp()
    if nlp is None:
        return []

    doc = nlp(text)
    return [
        NERDateEntity(
            text=ent.text,
            label=ent.label_,
            start_char=ent.start_char,
            end_char=ent.end_char,
        )
        for ent in doc.ents
        if ent.label_ in ("DATE", "TIME")
    ]


def has_temporal_entities(text: str) -> bool:
    """Return True if *text* contains at least one DATE or TIME entity."""
    return bool(extract_date_entities(text))


def reset_model_cache() -> None:
    """Force the next call to reload the spaCy model (useful in tests)."""
    global _nlp
    with _nlp_lock:
        _nlp = None
