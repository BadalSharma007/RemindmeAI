"""
LangGraph-powered deadline extraction agent using Gemma via Ollama.

Graph flow:
  classify → extract_dates → validate → resolve_ambiguity → done

LangSmith traces every run automatically when LANGCHAIN_TRACING_V2=true.
"""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, TypedDict

import pytz

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Agent state — passed between nodes
# ---------------------------------------------------------------------------

class DeadlineState(TypedDict):
    subject: str
    snippet: str
    received_at: str               # ISO datetime string
    user_timezone: str             # e.g. "Asia/Kolkata"
    is_deadline_related: bool
    raw_dates: list[str]           # date strings found by LLM
    resolved_deadlines: list[dict] # final output [{due_at, confidence, source_text}]
    needs_clarification: bool
    error: str


# ---------------------------------------------------------------------------
# LLM setup
# ---------------------------------------------------------------------------

def _get_llm():
    from app.config import settings
    if settings.use_gemini and settings.gemini_api_key:
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=settings.gemini_api_key,
            temperature=0,
        )
    from langchain_ollama import ChatOllama
    return ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=0,
    )


# ---------------------------------------------------------------------------
# Node 1: Classify — is this email deadline-related?
# ---------------------------------------------------------------------------

def classify_node(state: DeadlineState) -> DeadlineState:
    llm = _get_llm()
    prompt = f"""Analyze this email. Is it important or does it require any action?

Subject: {state['subject']}
Body: {state['snippet']}

Return true if the email is important or requires action. Examples:
- Has a date, time, or deadline
- Requires a reply or response
- Contains an offer, opportunity, or invitation
- Is from a college, bank, company, or official source
- Mentions money, payment, fees, or billing
- Contains an OTP, verification, or security alert
- Is about a job, internship, or interview
- Has any instructions or tasks to complete
- Contains news or updates that matter

Only return false for clearly unimportant emails like promotional ads, newsletters, or spam.

Reply with ONLY valid JSON:
{{"is_deadline_related": true, "reason": "brief reason"}}"""

    try:
        response = llm.invoke([
            SystemMessage(content="You find important emails that need attention. Be very inclusive — when in doubt return true. Only exclude obvious spam and ads. Respond with valid JSON only."),
            HumanMessage(content=prompt),
        ])
        text = response.content.strip()
        # Extract JSON even if model adds extra text
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            data = json.loads(match.group())
            state['is_deadline_related'] = bool(data.get('is_deadline_related', False))
        else:
            state['is_deadline_related'] = False
    except Exception as exc:
        logger.warning("LangGraph classify_node error: %s", exc)
        state['is_deadline_related'] = False

    return state


# ---------------------------------------------------------------------------
# Node 2: Extract dates
# ---------------------------------------------------------------------------

def extract_dates_node(state: DeadlineState) -> DeadlineState:
    if not state['is_deadline_related']:
        state['raw_dates'] = []
        return state

    llm = _get_llm()
    prompt = f"""Extract ALL dates and times from this email that relate to any action, meeting, deadline, or event.

Subject: {state['subject']}
Body: {state['snippet']}
Email received at: {state['received_at']}

Extract dates for:
- Deadlines: "submit by April 30", "due today at 8pm"
- Meetings: "meeting on Monday at 3pm", "call scheduled for tomorrow"
- Events: "webinar on Friday", "exam on 25th April"
- Payments: "pay by 30th", "invoice due next week"

Time resolution rules:
- "today" = {state['received_at'][:10]}
- "tonight" = today at 23:59
- "tomorrow" = next day
- "next week" = 7 days from received_at
- "ASAP" = received_at + 2 hours
- Always include the time if mentioned

Reply with ONLY valid JSON:
{{"dates": ["today at 8pm", "Monday April 21 at 3pm"], "needs_clarification": false}}"""

    try:
        response = llm.invoke([
            SystemMessage(content="You are a precise date extractor. Always respond with valid JSON only."),
            HumanMessage(content=prompt),
        ])
        text = response.content.strip()
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            data = json.loads(match.group())
            state['raw_dates'] = data.get('dates', [])
            state['needs_clarification'] = bool(data.get('needs_clarification', False))
        else:
            state['raw_dates'] = []
    except Exception as exc:
        logger.warning("LangGraph extract_dates_node error: %s", exc)
        state['raw_dates'] = []

    return state


# ---------------------------------------------------------------------------
# Node 3: Resolve ambiguity — convert relative dates to absolute ISO datetimes
# ---------------------------------------------------------------------------

def resolve_dates_node(state: DeadlineState) -> DeadlineState:
    if not state['raw_dates']:
        state['resolved_deadlines'] = []
        return state

    user_tz = state.get('user_timezone') or 'Asia/Kolkata'
    received_utc = datetime.fromisoformat(state['received_at'].replace('Z', '+00:00'))

    # Convert reference time to user's local time so "today/tomorrow" resolves correctly
    try:
        import pytz
        local_tz = pytz.timezone(user_tz)
        received_local = received_utc.astimezone(local_tz)
        local_date = received_local.strftime('%Y-%m-%d')
        local_datetime = received_local.strftime('%Y-%m-%d %H:%M %Z')
    except Exception:
        local_date = received_utc.strftime('%Y-%m-%d')
        local_datetime = received_utc.strftime('%Y-%m-%d %H:%M UTC')

    llm = _get_llm()
    prompt = f"""Convert these date/time expressions to LOCAL datetime strings in {user_tz} timezone.

User's local time when email was received: {local_datetime}
User's local date (today): {local_date}
User timezone: {user_tz}
Email subject: {state['subject']}
Dates to convert: {json.dumps(state['raw_dates'])}

IMPORTANT: Times in the email are in the user's LOCAL timezone ({user_tz}).
DO NOT convert to UTC. Output local times only.

Rules:
- "today at 4pm" → {local_date} 16:00
- "tonight" → {local_date} 23:59
- "tomorrow at 4pm" → tomorrow's date at 16:00
- "Monday at 3pm" → next Monday at 15:00
- "next week" → {local_date} + 7 days
- "ASAP" → current time + 2 hours
- Missing year → use current year
- If no time given → use 23:59

Reply with ONLY a valid JSON array:
[
  {{"due_at_local": "2026-04-21 16:00", "confidence": 0.95, "source_text": "tomorrow at 4pm"}},
  ...
]
confidence: 1.0=exact, 0.7=inferred, 0.4=vague"""

    try:
        response = llm.invoke([
            SystemMessage(content="You are a date resolver. Output local times only, not UTC. Always respond with valid JSON only."),
            HumanMessage(content=prompt),
        ])
        text = response.content.strip()
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            deadlines = json.loads(match.group())
            validated = []
            for d in deadlines:
                local_str = d.get('due_at_local') or d.get('due_at', '')
                if not local_str:
                    continue
                try:
                    # Parse the local datetime string Gemini returned
                    # Try common formats: "2026-04-21 09:30" or "2026-04-21 09:30:00"
                    local_dt = None
                    for fmt in ('%Y-%m-%d %H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M', '%Y-%m-%dT%H:%M:%S'):
                        try:
                            local_dt = datetime.strptime(local_str.strip(), fmt)
                            break
                        except ValueError:
                            continue

                    if local_dt:
                        # Localize to user's timezone then convert to UTC
                        local_tz_obj = pytz.timezone(user_tz)
                        localized = local_tz_obj.localize(local_dt)
                        utc_dt = localized.astimezone(pytz.UTC)
                        validated.append({
                            'due_at': utc_dt.strftime('%Y-%m-%dT%H:%M:%SZ'),
                            'confidence': float(d.get('confidence', 0.5)),
                            'source_text': d.get('source_text', ''),
                        })
                except Exception:
                    pass
            state['resolved_deadlines'] = validated
        else:
            state['resolved_deadlines'] = []
    except Exception as exc:
        logger.warning("LangGraph resolve_dates_node error: %s", exc)
        state['resolved_deadlines'] = []

    return state


# ---------------------------------------------------------------------------
# Routing — skip extraction if not deadline-related
# ---------------------------------------------------------------------------

def should_extract(state: DeadlineState) -> str:
    return "extract_dates" if state['is_deadline_related'] else END


# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------

def build_deadline_graph():
    graph = StateGraph(DeadlineState)

    graph.add_node("classify", classify_node)
    graph.add_node("extract_dates", extract_dates_node)
    graph.add_node("resolve_dates", resolve_dates_node)

    graph.set_entry_point("classify")
    graph.add_conditional_edges("classify", should_extract)
    graph.add_edge("extract_dates", "resolve_dates")
    graph.add_edge("resolve_dates", END)

    return graph.compile()


# Singleton compiled graph
_graph = None

def get_graph():
    global _graph
    if _graph is None:
        _graph = build_deadline_graph()
    return _graph


# ---------------------------------------------------------------------------
# Public API — called from processor.py
# ---------------------------------------------------------------------------

def extract_deadlines_with_agent(
    subject: str,
    snippet: str,
    received_at: datetime,
    user_timezone: str = "Asia/Kolkata",
) -> list[dict]:
    """
    Run the LangGraph deadline extraction agent.
    Returns list of dicts: [{due_at: datetime, confidence: float, source_text: str}]
    """
    # Set LangSmith env vars at runtime
    from app.config import settings
    if settings.langchain_tracing_v2 and settings.langchain_api_key:
        os.environ['LANGCHAIN_TRACING_V2'] = 'true'
        os.environ['LANGCHAIN_API_KEY'] = settings.langchain_api_key
        os.environ['LANGCHAIN_PROJECT'] = settings.langchain_project

    initial_state: DeadlineState = {
        'subject': subject or '',
        'snippet': snippet or '',
        'received_at': received_at.isoformat() if received_at else datetime.now(timezone.utc).isoformat(),
        'user_timezone': user_timezone or 'Asia/Kolkata',
        'is_deadline_related': False,
        'raw_dates': [],
        'resolved_deadlines': [],
        'needs_clarification': False,
        'error': '',
    }

    try:
        graph = get_graph()
        final_state = graph.invoke(initial_state)
        results = []
        for d in final_state.get('resolved_deadlines', []):
            try:
                due_at = datetime.fromisoformat(d['due_at'].replace('Z', '+00:00'))
                results.append({
                    'due_at': due_at,
                    'confidence': d['confidence'],
                    'source_text': d['source_text'],
                })
            except Exception:
                pass
        return results
    except Exception as exc:
        logger.error("LangGraph agent failed: %s", exc, exc_info=True)
        return []
