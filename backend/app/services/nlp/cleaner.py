from __future__ import annotations

import re

from bs4 import BeautifulSoup

MAX_NLP_CHARS = 2000

# Patterns for reply chain detection (MULTILINE only — no DOTALL so .* stops at line end)
_REPLY_PATTERNS = re.compile(
    r"^(on .{0,100}wrote:|>+\s|-{3,}\s*original message\s*-{3,}).*$",
    re.IGNORECASE | re.MULTILINE,
)

# Lines that signal an email signature (allow optional surrounding whitespace)
_SIGNATURE_MARKERS = re.compile(
    r"\n[ \t]*(--|best regards|kind regards|thanks and regards|sincerely|warm regards|"
    r"cheers,|thank you,|regards,|thanks,)[ \t]*(\n|$).*$",
    re.IGNORECASE | re.DOTALL,
)


def strip_html(html: str) -> str:
    """Convert HTML to plain text, preserving newlines at block elements."""
    soup = BeautifulSoup(html, "html.parser")
    # Replace block and line-break tags with newline text nodes
    for tag in soup.find_all(["br", "p", "div", "li", "tr", "h1", "h2", "h3"]):
        tag.replace_with("\n" + tag.get_text() + "\n")
    return soup.get_text(separator=" ")


def remove_reply_chain(text: str) -> str:
    """Remove reply chain lines (lines starting with '>' or 'On ... wrote:')."""
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        # Stop at "On ... wrote:" headers
        if re.match(r"on .{0,100}wrote:", stripped, re.IGNORECASE):
            break
        # Skip quoted lines
        if stripped.startswith(">"):
            continue
        lines.append(line)
    return "\n".join(lines)


def remove_signature(text: str) -> str:
    """Remove email signature heuristically."""
    match = _SIGNATURE_MARKERS.search(text)
    if match:
        text = text[: match.start()]
    return text


def clean_text(raw: str) -> str:
    """
    Full cleaning pipeline:
    1. Strip HTML tags
    2. Remove reply chains
    3. Remove signatures
    4. Normalize whitespace
    5. Truncate to MAX_NLP_CHARS
    """
    text = strip_html(raw)
    text = remove_reply_chain(text)
    text = remove_signature(text)
    # Normalize whitespace: collapse multiple spaces/newlines
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()
    return text[:MAX_NLP_CHARS]
