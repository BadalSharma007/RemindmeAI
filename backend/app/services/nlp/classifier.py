from __future__ import annotations

from dataclasses import dataclass, field

DEADLINE_KEYWORDS: frozenset[str] = frozenset(
    {
        "deadline",
        "due",
        "due date",
        "by eod",
        "end of day",
        "by end of day",
        "submit by",
        "submission deadline",
        "respond by",
        "reply by",
        "action required",
        "action needed",
        "urgent",
        "reminder",
        "expires",
        "expiry",
        "expiration",
        "rsvp",
        "rsvp by",
        "confirm by",
        "confirmation required",
        "complete by",
        "must be completed",
        "payment due",
        "invoice due",
        "overdue",
        "last day",
        "final day",
        "closing date",
        "cutoff",
        "cut-off",
        "by friday",
        "by monday",
        "by tuesday",
        "by wednesday",
        "by thursday",
        "by saturday",
        "by sunday",
        "by tomorrow",
        "by today",
        "by noon",
        "by midnight",
        "meeting",
        "interview",
        "appointment",
        "schedule",
        "register by",
        "registration closes",
        "apply by",
        "application deadline",
    }
)


@dataclass
class ClassificationResult:
    is_deadline_related: bool
    confidence: float
    matched_keywords: list[str] = field(default_factory=list)
    tier: int = 1  # 1 = rule-based, 2 = ML (Phase 2)


def classify_email(subject: str, snippet: str) -> ClassificationResult:
    """
    Tier 1 rule-based classifier.
    Scans the lowercased subject + snippet for DEADLINE_KEYWORDS.
    Confidence is proportional to the number of unique keyword hits.
    """
    combined = f"{subject} {snippet}".lower()
    matched: list[str] = []

    for keyword in DEADLINE_KEYWORDS:
        if keyword in combined:
            matched.append(keyword)

    if not matched:
        return ClassificationResult(
            is_deadline_related=False,
            confidence=0.0,
            matched_keywords=[],
        )

    # Confidence scales from 0.4 (1 match) to 0.95 (5+ matches)
    confidence = min(0.4 + (len(matched) - 1) * 0.11, 0.95)

    return ClassificationResult(
        is_deadline_related=True,
        confidence=round(confidence, 2),
        matched_keywords=matched,
    )


# ---------------------------------------------------------------------------
# Phase 2: Two-tier combined classifier
# ---------------------------------------------------------------------------

def classify_email_combined(subject: str, snippet: str) -> ClassificationResult:
    """
    Two-tier classifier used by the ingestion pipeline in Phase 2.

    Tier 1 (rule-based) always runs first.  When its confidence is below
    0.5 *and* the ML model is available, Tier 2 (DistilBERT zero-shot) runs
    to re-score the email.  Final confidence is a weighted blend.

    If the ML model is unavailable (``fallback_used=True``), Tier 1 result
    is returned unchanged.

    Weights:
      - Tier 1 contribution: 40 %
      - Tier 2 contribution: 60 %
    """
    from app.config import settings  # noqa: PLC0415

    tier1 = classify_email(subject, snippet)

    # High Tier 1 confidence — no need for expensive ML inference
    if tier1.confidence >= 0.5 or not settings.enable_ml_classifier:
        return tier1

    # Run ML Tier 2
    from app.services.nlp.ml_classifier import classify_email_ml  # noqa: PLC0415

    tier2 = classify_email_ml(subject, snippet)
    if tier2.fallback_used:
        return tier1  # ML unavailable — trust Tier 1

    # Weighted blend
    blended = round(tier1.confidence * 0.4 + tier2.confidence * 0.6, 2)

    return ClassificationResult(
        is_deadline_related=blended >= 0.4 or tier2.is_deadline_related,
        confidence=blended,
        matched_keywords=tier1.matched_keywords,
        tier=2,
    )
