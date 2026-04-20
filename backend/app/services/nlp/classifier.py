from __future__ import annotations

import re
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
        "before",
        "submit",
        "submission",
        "finish by",
        "complete before",
        "hand in",
        "turn in",
        "due on",
        "by april",
        "by may",
        "by june",
        "by july",
        "by august",
        "by september",
        "by october",
        "by november",
        "by december",
        "by january",
        "by february",
        "by march",
        "no later than",
        "not later than",
        "end of week",
        "end of month",
        "by eow",
        "by eom",
        "task",
        "pending",
        "please complete",
        "please submit",
        "please send",
        "kindly submit",
        "kindly send",
        "need by",
        "needed by",
        "expected by",
        "required by",
        "must submit",
        "must complete",
        "must send",
        # Academic / student keywords
        "tomorrow",
        "tonight",
        "exam",
        "test",
        "quiz",
        "class test",
        "conducted",
        "present",
        "on time",
        "attendance",
        "lecture",
        "seminar",
        "workshop",
        "session",
        "assignment",
        "project",
        "viva",
        "practical",
        "lab",
        "report due",
        "next monday",
        "next tuesday",
        "next wednesday",
        "next thursday",
        "next friday",
        "next week",
        "this week",
        "this friday",
        "today at",
        "tomorrow at",
        "monday at",
        "tuesday at",
        "wednesday at",
        "thursday at",
        "friday at",
        "at 9",
        "at 10",
        "at 11",
        "at 12",
        "at 1",
        "at 2",
        "at 3",
        "at 4",
        "at 5",
        "at 6",
        "at 7",
        "at 8",
        "ensure",
        "be present",
        "must attend",
        "please attend",
        "kindly attend",
        "will be held",
        "will be conducted",
        "is scheduled",
        "has been scheduled",
        "event",
        "internship",
        "placement",
        "hackathon",
        "competition",
        "contest",
    }
)

# Regex patterns to catch time/date references the keyword list might miss
_TIME_PATTERNS: list[re.Pattern] = [
    re.compile(r'\b\d{1,2}:\d{2}\s*(am|pm)\b', re.IGNORECASE),   # 10:30 AM
    re.compile(r'\b\d{1,2}\s*(am|pm)\b', re.IGNORECASE),          # 10 AM
    re.compile(r'\btomorrow\b', re.IGNORECASE),
    re.compile(r'\btonight\b', re.IGNORECASE),
    re.compile(r'\bnext\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday|week|month)\b', re.IGNORECASE),
    re.compile(r'\bthis\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday|week)\b', re.IGNORECASE),
    re.compile(r'\bon\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', re.IGNORECASE),
    re.compile(r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}\b', re.IGNORECASE),
    re.compile(r'\b\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}\b'),        # 25/04/2026
    re.compile(r'\b\d{1,2}\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b', re.IGNORECASE),
]


@dataclass
class ClassificationResult:
    is_deadline_related: bool
    confidence: float
    matched_keywords: list[str] = field(default_factory=list)
    tier: int = 1  # 1 = rule-based, 2 = ML (Phase 2)


def classify_email(subject: str, snippet: str) -> ClassificationResult:
    """
    Tier 1 rule-based classifier.
    Step 1: keyword scan.
    Step 2: regex time/date pattern scan as fallback.
    """
    combined = f"{subject} {snippet}".lower()
    matched: list[str] = []

    for keyword in DEADLINE_KEYWORDS:
        if keyword in combined:
            matched.append(keyword)

    if matched:
        confidence = min(0.4 + (len(matched) - 1) * 0.11, 0.95)
        return ClassificationResult(
            is_deadline_related=True,
            confidence=round(confidence, 2),
            matched_keywords=matched,
        )

    # Fallback: check for time/date patterns
    for pattern in _TIME_PATTERNS:
        if pattern.search(combined):
            return ClassificationResult(
                is_deadline_related=True,
                confidence=0.4,
                matched_keywords=["[time/date pattern]"],
            )

    return ClassificationResult(
        is_deadline_related=False,
        confidence=0.0,
        matched_keywords=[],
    )


# ---------------------------------------------------------------------------
# Phase 2: Two-tier combined classifier
# ---------------------------------------------------------------------------

def classify_email_combined(subject: str, snippet: str) -> ClassificationResult:
    """
    Two-tier classifier used by the ingestion pipeline in Phase 2.
    """
    from app.config import settings  # noqa: PLC0415

    tier1 = classify_email(subject, snippet)

    if tier1.confidence >= 0.5 or not settings.enable_ml_classifier:
        return tier1

    from app.services.nlp.ml_classifier import classify_email_ml  # noqa: PLC0415

    tier2 = classify_email_ml(subject, snippet)
    if tier2.fallback_used:
        return tier1

    blended = round(tier1.confidence * 0.4 + tier2.confidence * 0.6, 2)

    return ClassificationResult(
        is_deadline_related=blended >= 0.4 or tier2.is_deadline_related,
        confidence=blended,
        matched_keywords=tier1.matched_keywords,
        tier=2,
    )
