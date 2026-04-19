"""Phase 2 — Tier 2 ML classifier using DistilBERT zero-shot classification.

Uses the HuggingFace `transformers` zero-shot pipeline backed by
`cross-encoder/nli-distilroberta-base` (~82 MB, CPU-friendly).

Design:
- Lazy-loaded on first call; model is downloaded to the HF cache directory.
- Thread-safe singleton protected by a lock.
- Returns `fallback_used=True` when `transformers` / `torch` is not installed
  or the model fails to load — callers should fall back to Tier 1 (rule-based).
- Text is truncated to 512 characters before inference (DistilBERT token limit).
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MODEL_ID = "cross-encoder/nli-distilroberta-base"

CANDIDATE_LABELS: list[str] = [
    "email with a deadline, due date, or required action",
    "general information, newsletter, or promotional content",
]

# ---------------------------------------------------------------------------
# Lazy-loaded pipeline singleton
# ---------------------------------------------------------------------------
_pipeline = None          # HF pipeline | False (tried, unavailable)
_pipeline_lock = threading.Lock()


def _get_pipeline():
    """Return the lazy-loaded zero-shot pipeline, or None if unavailable."""
    global _pipeline
    if _pipeline is None:
        with _pipeline_lock:
            if _pipeline is None:
                try:
                    from transformers import pipeline as hf_pipeline  # noqa: PLC0415

                    _pipeline = hf_pipeline(
                        "zero-shot-classification",
                        model=MODEL_ID,
                        device=-1,  # CPU
                    )
                    logger.info("ML classifier loaded: %s", MODEL_ID)
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "ML classifier unavailable (%s: %s) — "
                        "falling back to rule-based Tier 1.",
                        type(exc).__name__,
                        exc,
                    )
                    _pipeline = False

    return None if _pipeline is False else _pipeline


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------
@dataclass
class MLClassificationResult:
    is_deadline_related: bool
    confidence: float
    model_id: str
    fallback_used: bool = False
    candidate_scores: dict[str, float] = field(default_factory=dict)


def classify_email_ml(subject: str, snippet: str) -> MLClassificationResult:
    """
    Tier 2 ML zero-shot classifier.

    Args:
        subject: Email subject line.
        snippet: Short email preview text (≤500 chars).

    Returns:
        MLClassificationResult.  When the model is unavailable,
        ``fallback_used=True`` and ``confidence=0.0`` — the caller must
        use the Tier 1 rule-based result instead.
    """
    pipe = _get_pipeline()
    if pipe is None:
        return MLClassificationResult(
            is_deadline_related=False,
            confidence=0.0,
            model_id=MODEL_ID,
            fallback_used=True,
        )

    # DistilBERT context window: keep well within 512 sub-word tokens
    text = f"{subject}. {snippet}"[:512]

    try:
        raw = pipe(text, candidate_labels=CANDIDATE_LABELS)
        # raw = {"labels": [...], "scores": [...]}
        label_scores: dict[str, float] = dict(zip(raw["labels"], raw["scores"]))
        top_label: str = raw["labels"][0]
        top_score: float = raw["scores"][0]

        is_deadline = "deadline" in top_label or "action" in top_label

        return MLClassificationResult(
            is_deadline_related=is_deadline,
            confidence=round(top_score, 4),
            model_id=MODEL_ID,
            candidate_scores=label_scores,
        )

    except Exception as exc:  # noqa: BLE001
        logger.error("ML classifier inference error: %s", exc, exc_info=True)
        return MLClassificationResult(
            is_deadline_related=False,
            confidence=0.0,
            model_id=MODEL_ID,
            fallback_used=True,
        )


def reset_pipeline_cache() -> None:
    """Force next call to reload the pipeline (useful in tests)."""
    global _pipeline
    with _pipeline_lock:
        _pipeline = None
