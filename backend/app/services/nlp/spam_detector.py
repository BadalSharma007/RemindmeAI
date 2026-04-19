"""Spam / marketing-email detector.

Runs *before* the NLP pipeline so we skip deadline extraction for bulk
promotional mail.  No external models required — pure header + keyword analysis.

Strategy
--------
1. Header signals  — ``List-Unsubscribe``, ``Precedence: bulk/list/junk``,
   ``X-Spam-Score``, ``X-Mailer`` / ``X-Campaign-ID`` marketing headers.
2. Subject keywords — "unsubscribe", "offer", "% off", "sale", "newsletter", …
3. Sender patterns  — no-reply / noreply / marketing / promo addresses.
4. Weighted scoring — weighted sum → ``is_spam`` when score ≥ SPAM_THRESHOLD.

Returns a ``SpamResult`` dataclass so callers can store the score.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# Threshold above which an email is considered spam/marketing.
SPAM_THRESHOLD: float = 0.5

# ---------------------------------------------------------------------------
# Keyword sets
# ---------------------------------------------------------------------------

_SUBJECT_SPAM_KEYWORDS: frozenset[str] = frozenset(
    {
        "unsubscribe",
        "newsletter",
        "% off",
        "percent off",
        "sale",
        "discount",
        "offer",
        "promotion",
        "promo",
        "coupon",
        "deal",
        "free shipping",
        "limited time",
        "act now",
        "exclusive",
        "congratulations",
        "you've been selected",
        "you have been selected",
        "click here",
        "buy now",
        "shop now",
        "order now",
        "get yours",
        "earn rewards",
        "win a",
        "you won",
        "claim your",
    }
)

_SENDER_SPAM_PATTERNS: tuple[re.Pattern, ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in [
        r"no[-_]?reply",
        r"noreply",
        r"do[-_]?not[-_]?reply",
        r"mailer[-_]?daemon",
        r"newsletter",
        r"marketing",
        r"promotions?",
        r"notifications?@",
        r"alerts?@",
        r"updates?@",
        r"info@",
        r"hello@",
    ]
)

# Headers that conclusively indicate marketing / bulk mail
_BULK_HEADERS: frozenset[str] = frozenset(
    {
        "list-unsubscribe",
        "list-id",
        "list-post",
        "x-campaign-id",
        "x-mailchimp",
        "x-sendgrid",
        "x-ses-message-tags",
        "x-marketo",
        "x-hubspot",
        "x-salesforce",
    }
)


@dataclass
class SpamResult:
    is_spam: bool
    spam_score: float  # 0.0–1.0
    signals: list[str] = field(default_factory=list)  # human-readable reasons


# ---------------------------------------------------------------------------
# Public function
# ---------------------------------------------------------------------------


def detect_spam(
    subject: str,
    snippet: str,
    headers: dict[str, Any] | None = None,
) -> SpamResult:
    """Analyse an email for spam/marketing signals.

    Parameters
    ----------
    subject:   Email subject line.
    snippet:   Short preview text (first ~200 chars).
    headers:   Dict of header-name → value (lowercase keys preferred).
               Pass ``{}`` or ``None`` when headers are unavailable.

    Returns
    -------
    SpamResult with ``is_spam``, ``spam_score``, and human-readable ``signals``.
    """
    headers = {k.lower(): str(v) for k, v in (headers or {}).items()}
    signals: list[str] = []
    score: float = 0.0

    # --- 1. Bulk / marketing headers ---
    for hdr in _BULK_HEADERS:
        if hdr in headers:
            signals.append(f"header:{hdr}")
            score += 0.55  # definitive: bulk-mail header alone → spam
            break  # one bulk header is enough; cap contribution

    # --- 2. Precedence header ---
    precedence = headers.get("precedence", "")
    if precedence.lower() in {"bulk", "list", "junk"}:
        signals.append(f"precedence:{precedence}")
        score += 0.30

    # --- 3. X-Spam-Score header ---
    x_spam = headers.get("x-spam-score", "")
    try:
        spam_score_val = float(x_spam)
        if spam_score_val >= 5.0:
            signals.append(f"x-spam-score:{spam_score_val:.1f}")
            score += min(0.40, spam_score_val / 20.0)
    except ValueError:
        pass

    # --- 4. Subject keyword matching ---
    subject_lower = subject.lower()
    for kw in _SUBJECT_SPAM_KEYWORDS:
        if kw in subject_lower:
            signals.append(f"subject_kw:{kw!r}")
            score += 0.55  # strong signal: promotional subject → spam
            break  # one subject keyword hit is enough

    # --- 5. Sender pattern matching ---
    sender = headers.get("from", "") or headers.get("sender", "")
    for pattern in _SENDER_SPAM_PATTERNS:
        if pattern.search(sender):
            signals.append(f"sender_pattern:{pattern.pattern!r}")
            score += 0.15
            break

    # Clamp to [0, 1]
    score = min(1.0, score)

    return SpamResult(
        is_spam=score >= SPAM_THRESHOLD,
        spam_score=round(score, 3),
        signals=signals,
    )
