"""Unit tests for app.services.nlp.ml_classifier — no model download required."""
from __future__ import annotations

import pytest

from app.services.nlp.ml_classifier import (
    CANDIDATE_LABELS,
    MLClassificationResult,
    classify_email_ml,
    reset_pipeline_cache,
)


# ---------------------------------------------------------------------------
# Helpers — mock HuggingFace pipeline
# ---------------------------------------------------------------------------

def _make_pipeline(top_label: str, top_score: float):
    """Return a callable that mimics a zero-shot-classification pipeline."""
    other_label = next(l for l in CANDIDATE_LABELS if l != top_label)
    other_score = round(1.0 - top_score, 4)

    result = {
        "labels": [top_label, other_label],
        "scores": [top_score, other_score],
    }

    def _pipe(text: str, candidate_labels: list) -> dict:  # noqa: ARG001
        return result

    return _pipe


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_cache():
    reset_pipeline_cache()
    yield
    reset_pipeline_cache()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_deadline_email_classified_positive(monkeypatch):
    import app.services.nlp.ml_classifier as m

    monkeypatch.setattr(m, "_get_pipeline", lambda: _make_pipeline(
        CANDIDATE_LABELS[0],  # deadline label
        0.92,
    ))

    result = classify_email_ml(
        subject="Invoice Due — Action Required",
        snippet="Your invoice is due by Friday. Please pay immediately.",
    )

    assert result.is_deadline_related is True
    assert result.confidence == 0.92
    assert result.fallback_used is False
    assert result.model_id == m.MODEL_ID


def test_newsletter_classified_negative(monkeypatch):
    import app.services.nlp.ml_classifier as m

    monkeypatch.setattr(m, "_get_pipeline", lambda: _make_pipeline(
        CANDIDATE_LABELS[1],  # general/newsletter label
        0.88,
    ))

    result = classify_email_ml(
        subject="Weekly Digest",
        snippet="Here are the top stories from this week.",
    )

    assert result.is_deadline_related is False
    assert result.confidence == 0.88
    assert result.fallback_used is False


def test_fallback_when_model_unavailable(monkeypatch):
    """When _get_pipeline() returns None, fallback_used must be True."""
    import app.services.nlp.ml_classifier as m

    monkeypatch.setattr(m, "_get_pipeline", lambda: None)

    result = classify_email_ml("Any subject", "Any body")

    assert result.fallback_used is True
    assert result.is_deadline_related is False
    assert result.confidence == 0.0


def test_inference_exception_returns_fallback(monkeypatch):
    """A pipeline that raises must trigger fallback_used=True."""
    import app.services.nlp.ml_classifier as m

    def _bad_pipe(text, candidate_labels):  # noqa: ARG001
        raise RuntimeError("CUDA OOM")

    monkeypatch.setattr(m, "_get_pipeline", lambda: _bad_pipe)

    result = classify_email_ml("subject", "body")

    assert result.fallback_used is True


def test_text_truncated_to_512(monkeypatch):
    """Text passed to the pipeline must not exceed 512 chars."""
    import app.services.nlp.ml_classifier as m

    captured: list[str] = []

    def _capture_pipe(text: str, candidate_labels):  # noqa: ARG001
        captured.append(text)
        return {"labels": [CANDIDATE_LABELS[0]], "scores": [0.9]}

    monkeypatch.setattr(m, "_get_pipeline", lambda: _capture_pipe)

    classify_email_ml("S" * 300, "B" * 300)

    assert len(captured) == 1
    assert len(captured[0]) <= 512


def test_candidate_scores_populated(monkeypatch):
    import app.services.nlp.ml_classifier as m

    monkeypatch.setattr(m, "_get_pipeline", lambda: _make_pipeline(
        CANDIDATE_LABELS[0], 0.75
    ))

    result = classify_email_ml("Confirm your attendance", "Please confirm by Monday.")

    assert len(result.candidate_scores) == 2
    assert CANDIDATE_LABELS[0] in result.candidate_scores
