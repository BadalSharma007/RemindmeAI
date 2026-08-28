"""Smart deadline extractor.

Strategy (in priority order):
  1. Keyword-anchored patterns — find phrases like "due by 5pm", "submit before April 30",
     "meeting at 3pm tomorrow", "deadline: Friday". These get high confidence.
  2. spaCy NER — extract DATE/TIME entities from the subject line only (shorter, cleaner).
  3. Full-text fallback — dateparser scan on subject only (not full body) to avoid noise.

Dedup: one deadline per calendar day, prefer specific time over midnight.
Cap: max 2 deadlines per email.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import dateparser

DATEPARSER_SETTINGS: dict = {
    "RETURN_AS_TIMEZONE_AWARE": True,
    "PREFER_DATES_FROM": "future",
    "TO_TIMEZONE": "UTC",
    "PREFER_DAY_OF_MONTH": "first",
}

# Action keywords that strongly signal a deadline is nearby
_DEADLINE_PATTERNS = [
    # "due by/on/at ...", "due: ..."
    r"due\s*(?:by|on|at|:)?\s*([^.\n]{3,50})",
    # "deadline: ...", "deadline is ..."
    r"deadline\s*(?:is|:|by|on|at)?\s*([^.\n]{3,50})",
    # "submit by/before/on ..."
    r"submit(?:ted|ted by)?\s*(?:by|before|on|at)\s*([^.\n]{3,50})",
    # "complete/finish/done by ..."
    r"(?:complete|finish|done|send|pay|payment|fees?)\s*(?:by|before|on|at)\s*([^.\n]{3,50})",
    # "meeting/call/class/exam/quiz at/on ..."
    r"(?:meeting|call|class|exam|quiz|test|interview|webinar|session|seminar)\s*(?:at|on|scheduled for|tomorrow|today)\s*([^.\n]{3,50})",
    # "by [time/date]" — short form
    r"\bby\s+((?:today|tomorrow|tonight|\d{1,2}(?::\d{2})?\s*(?:am|pm)|(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2})[^.\n]{0,30})",
    # "at [time] today/tomorrow"
    r"\bat\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)\s*(?:today|tomorrow|tonight)?)",
    # "today at ...", "tomorrow at ..."
    r"(today|tomorrow|tonight)\s+at\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm))",
    # "last date: ...", "last day: ..."
    r"last\s+(?:date|day)\s*(?:is|:|for|to)?\s*([^.\n]{3,40})",
]

_COMPILED_PATTERNS = [(re.compile(p, re.IGNORECASE), i) for i, p in enumerate(_DEADLINE_PATTERNS)]


@dataclass
class ExtractedDeadline:
    due_at: datetime
    source_text: str
    confidence: float
    ner_used: bool = False


def _parse(text: str, settings: dict) -> Optional[datetime]:
    """Parse a date string, return None on failure."""
    try:
        return dateparser.parse(text.strip(), settings=settings)
    except Exception:
        return None


def _confidence_for_pattern(idx: int, date_str: str) -> float:
    """Higher confidence for more specific patterns."""
    lower = date_str.lower()
    has_time = bool(re.search(r'\d{1,2}(?::\d{2})?\s*(?:am|pm)', lower))
    has_month = any(m in lower for m in (
        "jan", "feb", "mar", "apr", "may", "jun",
        "jul", "aug", "sep", "oct", "nov", "dec",
    ))
    # Patterns 0-4 are strong keyword anchors
    base = 0.85 if idx <= 4 else 0.70
    if has_time:
        base = min(base + 0.10, 0.95)
    if has_month:
        base = min(base + 0.05, 0.95)
    return base


def _keyword_anchored_extract(
    text: str,
    settings: dict,
    now: datetime,
) -> list[ExtractedDeadline]:
    """Step 1: Find dates anchored to deadline keywords."""
    results = []
    for pattern, idx in _COMPILED_PATTERNS:
        for match in pattern.finditer(text):
            # Handle patterns with 2 capture groups (e.g. "today at 3pm")
            groups = [g for g in match.groups() if g]
            date_candidate = " ".join(groups).strip()
            if not date_candidate:
                continue

            parsed = _parse(date_candidate, settings)
            if parsed is None:
                continue
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            if parsed < (now - timedelta(hours=1)):
                continue

            # Source context: up to 120 chars around the match
            start = max(0, match.start() - 40)
            end = min(len(text), match.end() + 40)
            source = text[start:end].strip()[:200]

            results.append(ExtractedDeadline(
                due_at=parsed,
                source_text=source,
                confidence=_confidence_for_pattern(idx, date_candidate),
                ner_used=False,
            ))
    return results


def _ner_extract(
    subject: str,
    settings: dict,
    now: datetime,
) -> list[ExtractedDeadline]:
    """Step 2: spaCy NER on subject only (cleaner signal than full body)."""
    try:
        from app.services.nlp.ner_extractor import extract_date_entities
        entities = extract_date_entities(subject)
        results = []
        for ent in entities:
            parsed = _parse(ent.text, settings)
            if parsed is None:
                continue
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            if parsed < (now - timedelta(hours=1)):
                continue
            results.append(ExtractedDeadline(
                due_at=parsed,
                source_text=subject[:200],
                confidence=0.75,
                ner_used=True,
            ))
        return results
    except Exception:
        return []


def _subject_dateparser_extract(
    subject: str,
    settings: dict,
    now: datetime,
) -> list[ExtractedDeadline]:
    """Step 3: Full dateparser scan on subject only."""
    try:
        import dateparser.search
        pairs = dateparser.search.search_dates(subject, settings=settings) or []
        results = []
        for date_str, parsed in pairs:
            if parsed is None:
                continue
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            if parsed < (now - timedelta(hours=1)):
                continue
            has_time = bool(re.search(r'\d{1,2}(?::\d{2})?\s*(?:am|pm)', date_str.lower()))
            results.append(ExtractedDeadline(
                due_at=parsed,
                source_text=subject[:200],
                confidence=0.70 if has_time else 0.50,
                ner_used=False,
            ))
        return results
    except Exception:
        return []


def _dedup(candidates: list[ExtractedDeadline]) -> list[ExtractedDeadline]:
    """Keep best deadline per calendar day. Prefer specific time over midnight."""
    best: dict[tuple, ExtractedDeadline] = {}
    for dl in sorted(candidates, key=lambda d: -d.confidence):
        key = (dl.due_at.year, dl.due_at.month, dl.due_at.day)
        existing = best.get(key)
        if existing is None:
            best[key] = dl
            continue
        existing_midnight = existing.due_at.hour == 0 and existing.due_at.minute == 0
        new_midnight = dl.due_at.hour == 0 and dl.due_at.minute == 0
        if existing_midnight and not new_midnight:
            best[key] = dl
        elif dl.confidence > existing.confidence and not (new_midnight and not existing_midnight):
            best[key] = dl
    return sorted(best.values(), key=lambda d: d.due_at)


def extract_deadlines(
    text: str,
    reference_time: datetime | None = None,
    user_timezone: str = "Asia/Kolkata",
) -> list[ExtractedDeadline]:
    """
    Extract deadlines from email text using a 3-tier strategy.

    Args:
        text: Cleaned subject + snippet (subject should come first).
        reference_time: Email received_at (UTC). Defaults to utcnow().
        user_timezone: User's local timezone (e.g. 'Asia/Kolkata').

    Returns:
        Up to 2 unique deadlines sorted by due_at ascending (in UTC).
    """
    if not text or not text.strip():
        return []

    now = reference_time or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    # Localize reference time to user's timezone for accurate relative base
    try:
        import pytz
        local_tz = pytz.timezone(user_timezone)
        now_local = now.astimezone(local_tz)
    except Exception:
        now_local = now

    settings = dict(DATEPARSER_SETTINGS)
    settings["TIMEZONE"] = user_timezone
    settings["TO_TIMEZONE"] = "UTC"
    settings["RELATIVE_BASE"] = now_local.replace(tzinfo=None)

    # Subject is the first line (most reliable signal)
    lines = text.strip().splitlines()
    subject = lines[0] if lines else text[:200]

    # Tier 1: keyword-anchored (full text — catches "submit by 5pm" in body)
    candidates = _keyword_anchored_extract(text, settings, now)

    # Tier 2: NER on subject only
    if not candidates:
        candidates = _ner_extract(subject, settings, now)

    # Tier 3: dateparser on subject only
    if not candidates:
        candidates = _subject_dateparser_extract(subject, settings, now)

    # Dedup and cap
    return _dedup(candidates)[:2]
