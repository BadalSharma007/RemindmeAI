"""Unit tests for app.services.nlp.spam_detector — pure Python, no external deps."""
from __future__ import annotations

import pytest

from app.services.nlp.spam_detector import SPAM_THRESHOLD, SpamResult, detect_spam


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_spam(subject="", snippet="", headers=None) -> bool:
    return detect_spam(subject, snippet, headers).is_spam


# ---------------------------------------------------------------------------
# Tests — clean emails (should NOT be spam)
# ---------------------------------------------------------------------------

def test_clean_email_not_spam():
    result = detect_spam(
        subject="Q2 report deadline — please submit by Friday",
        snippet="Hi team, the report is due this Friday at 5 PM.",
    )
    assert not result.is_spam
    assert result.spam_score < SPAM_THRESHOLD


def test_deadline_subject_not_flagged():
    assert not _is_spam(subject="Reminder: project deliverable due Monday")


# ---------------------------------------------------------------------------
# Tests — spam signals
# ---------------------------------------------------------------------------

def test_list_unsubscribe_header_detected():
    result = detect_spam(
        subject="Your weekly digest",
        snippet="See what's new this week.",
        headers={"List-Unsubscribe": "<mailto:unsub@example.com>"},
    )
    assert result.is_spam
    assert "header:list-unsubscribe" in result.signals


def test_precedence_bulk_detected():
    result = detect_spam(
        subject="Company newsletter",
        snippet="Read our monthly update.",
        headers={"Precedence": "bulk"},
    )
    assert result.is_spam
    assert any("precedence" in s for s in result.signals)


def test_subject_keyword_sale_detected():
    result = detect_spam(
        subject="50% OFF SALE — Limited time only",
        snippet="Shop now for exclusive deals.",
    )
    assert result.is_spam
    assert any("subject_kw" in s for s in result.signals)


def test_noreply_sender_contributes_score():
    result = detect_spam(
        subject="Your order confirmation",
        snippet="Your order has been shipped.",
        headers={"from": "noreply@shop.example.com"},
    )
    assert any("sender_pattern" in s for s in result.signals)


def test_x_spam_score_high():
    result = detect_spam(
        subject="Win a prize!",
        snippet="Click here to claim.",
        headers={"X-Spam-Score": "8.5"},
    )
    assert result.is_spam


def test_combined_signals_accumulate():
    """Multiple weak signals should push score above threshold."""
    result = detect_spam(
        subject="Newsletter: exclusive offer inside",
        snippet="Unsubscribe from our list.",
        headers={
            "Precedence": "list",
            "from": "newsletter@marketing.example.com",
        },
    )
    assert result.is_spam
    assert len(result.signals) >= 2


def test_spam_score_clamped_to_one():
    """Score must never exceed 1.0 even with many signals."""
    result = detect_spam(
        subject="50% off sale — act now",
        snippet="click here",
        headers={
            "List-Unsubscribe": "<...>",
            "Precedence": "bulk",
            "X-Spam-Score": "15.0",
            "X-Campaign-Id": "camp123",
            "from": "noreply@promo.example.com",
        },
    )
    assert result.spam_score <= 1.0


def test_result_type():
    result = detect_spam("Hello", "World")
    assert isinstance(result, SpamResult)
    assert isinstance(result.is_spam, bool)
    assert isinstance(result.spam_score, float)
    assert isinstance(result.signals, list)
