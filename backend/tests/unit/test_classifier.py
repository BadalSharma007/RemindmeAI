"""Unit tests for app.services.nlp.classifier — no external dependencies."""
import pytest

from app.services.nlp.classifier import ClassificationResult, classify_email


def test_deadline_keyword_in_subject():
    result = classify_email("Submit by Friday", "Please see details below.")
    assert result.is_deadline_related is True
    assert result.confidence > 0.0


def test_deadline_keyword_in_snippet():
    result = classify_email("Team update", "Action required: please confirm by noon today.")
    assert result.is_deadline_related is True
    assert "action required" in result.matched_keywords or any(
        "action" in kw for kw in result.matched_keywords
    )


def test_no_keywords_returns_false():
    result = classify_email(
        "Weekly Newsletter",
        "Check out our latest offers and deals. Unsubscribe below.",
    )
    assert result.is_deadline_related is False
    assert result.confidence == 0.0
    assert result.matched_keywords == []


def test_confidence_proportional_to_keyword_count():
    # Single keyword
    single = classify_email("Reminder", "Nothing else here.")
    # Multiple keywords
    multi = classify_email(
        "Urgent: deadline tomorrow",
        "Action required. Submit by Friday. Confirm by noon.",
    )
    assert multi.confidence > single.confidence


def test_case_insensitive_matching():
    result = classify_email("DEADLINE APPROACHING", "DUE DATE IS TOMORROW.")
    assert result.is_deadline_related is True
    assert result.confidence > 0.0


def test_matched_keywords_list_populated():
    result = classify_email("Submit by EOD", "Due date: Friday. Action required.")
    assert isinstance(result.matched_keywords, list)
    assert len(result.matched_keywords) >= 1
    assert result.tier == 1
