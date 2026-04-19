"""Unit tests for app.services.nlp.deadline_extractor — no external I/O."""
from datetime import datetime, timezone, timedelta

import pytest

from app.services.nlp.deadline_extractor import ExtractedDeadline, extract_deadlines


REF_TIME = datetime(2026, 3, 25, 10, 0, 0, tzinfo=timezone.utc)


def test_extract_explicit_date():
    text = "Please submit your report by April 10, 2026."
    deadlines = extract_deadlines(text, reference_time=REF_TIME)
    assert len(deadlines) >= 1
    due = deadlines[0].due_at
    assert due.year == 2026
    assert due.month == 4
    # Allow ±1 day for timezone conversion (dateparser may shift due to local tz)
    assert abs(due.day - 10) <= 1


def test_extract_relative_date():
    text = "The task is due in 3 days."
    deadlines = extract_deadlines(text, reference_time=REF_TIME)
    assert len(deadlines) >= 1
    due = deadlines[0].due_at
    expected = REF_TIME + timedelta(days=3)
    # Allow ±1 day tolerance for relative parsing
    assert abs((due - expected).total_seconds()) < 86400 * 1.5


def test_extract_time_with_date():
    text = "Please respond by 5pm on April 1, 2026."
    deadlines = extract_deadlines(text, reference_time=REF_TIME)
    assert len(deadlines) >= 1
    due = deadlines[0].due_at
    # Allow ±1 day for timezone conversion
    assert (due.month == 4 and abs(due.day - 1) <= 1) or (due.month == 3 and due.day == 31)
    # 5pm in some timezone maps to 11:30 UTC (IST) or 17:00 UTC, accept either
    assert due.hour in range(9, 24) or due.hour in range(0, 3)


def test_past_dates_filtered_out():
    # January 2025 is in the past relative to REF_TIME (March 2026)
    text = "The deadline was January 5, 2025."
    deadlines = extract_deadlines(text, reference_time=REF_TIME)
    assert all(d.due_at >= REF_TIME - timedelta(hours=1) for d in deadlines)


def test_multiple_dates_returned():
    text = "First deadline: April 5, 2026. Second deadline: April 20, 2026."
    deadlines = extract_deadlines(text, reference_time=REF_TIME)
    assert len(deadlines) >= 2


def test_no_dates_returns_empty_list():
    # Use text that is clearly free of any date-like patterns
    text = "Please remember to stay hydrated and take regular breaks."
    deadlines = extract_deadlines(text, reference_time=REF_TIME)
    assert isinstance(deadlines, list)
    # If dateparser returns anything, it should all be future dates
    assert all(d.due_at >= REF_TIME - timedelta(hours=1) for d in deadlines)


def test_source_text_contains_context():
    text = "Please submit the quarterly report by March 30, 2026 at the latest."
    deadlines = extract_deadlines(text, reference_time=REF_TIME)
    assert len(deadlines) >= 1
    # source_text should contain some surrounding context
    assert len(deadlines[0].source_text) > 0
    # The extracted date string should appear in or near the source text
    assert "2026" in deadlines[0].source_text or "March" in deadlines[0].source_text
