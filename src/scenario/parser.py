"""
Scenario input parser.

Parses natural language scenario descriptions into structured
ScenarioAction objects. Supports budget changes, scope cuts,
delays, and project removal.

Sprint 2 — Week 4 deliverable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class ActionType(Enum):
    BUDGET_INCREASE = "budget_increase"
    BUDGET_DECREASE = "budget_decrease"
    SCOPE_CUT = "scope_cut"
    DELAY = "delay"
    REMOVE = "remove"


@dataclass
class ScenarioAction:
    """A parsed scenario action."""

    action: ActionType
    project: str
    amount: float = 0.0          # Percentage (0.0-1.0) or absolute value
    amount_absolute: float = 0.0  # Absolute currency amount (if specified)
    duration_weeks: int = 0       # For delay actions
    description: str = ""         # Original input text


class ParseError(Exception):
    """Raised when scenario input cannot be parsed."""
    pass


# ──────────────────────────────────────────────
# Duration mappings
# ──────────────────────────────────────────────

DURATION_WEEKS = {
    "week": 1,
    "weeks": 1,
    "fortnight": 2,
    "fortnights": 2,
    "month": 4,
    "months": 4,
    "quarter": 13,
    "quarters": 13,
    "year": 52,
    "years": 52,
}


def parse_scenario(text: str) -> ScenarioAction:
    """Parse a natural language scenario into a ScenarioAction.

    Supported patterns:
    - "increase Project Beta budget by 20%"
    - "decrease Project Alpha budget by £50,000"
    - "cut Project Beta scope by 30%"
    - "reduce Project Beta scope by 30%"
    - "delay Project Gamma by 1 quarter"
    - "push back Project Gamma by 3 months"
    - "remove Project Delta"
    - "cancel Project Delta"

    Args:
        text: Natural language scenario description.

    Returns:
        ScenarioAction with parsed action, project, and parameters.

    Raises:
        ParseError: If the input cannot be parsed.
    """
    text = text.strip()
    if not text:
        raise ParseError("Empty scenario input.")

    original = text
    normalised = text.lower()

    # Try each parser in order
    parsers = [
        _parse_remove,
        _parse_budget_change,
        _parse_scope_cut,
        _parse_delay,
    ]

    for parser in parsers:
        result = parser(normalised, original)
        if result is not None:
            result.description = original
            return result

    raise ParseError(
        f"Could not parse scenario: '{text}'. "
        f"Supported patterns: budget increase/decrease, scope cut, delay, remove."
    )


# ──────────────────────────────────────────────
# Individual parsers
# ──────────────────────────────────────────────


def _parse_remove(normalised: str, original: str) -> ScenarioAction | None:
    """Parse 'remove/cancel/drop Project X' patterns."""
    patterns = [
        r"(?:remove|cancel|drop|kill|delete)\s+(?:project\s+)?(.+?)(?:\s+from\s+portfolio)?$",
    ]
    for pattern in patterns:
        match = re.match(pattern, normalised.strip())
        if match:
            project = _clean_project_name(match.group(1), original)
            return ScenarioAction(
                action=ActionType.REMOVE,
                project=project,
            )
    return None


def _parse_budget_change(normalised: str, original: str) -> ScenarioAction | None:
    """Parse 'increase/decrease Project X budget by Y%' or 'by £Y' patterns."""
    # Percentage-based: "increase project beta budget by 20%"
    pct_patterns = [
        r"(increase|decrease|reduce|raise|boost|lower)\s+(?:project\s+)?(.+?)\s+budget\s+by\s+(\d+(?:\.\d+)?)\s*%",
        r"(increase|decrease|reduce|raise|boost|lower)\s+(?:the\s+)?budget\s+(?:for|of|on)\s+(?:project\s+)?(.+?)\s+by\s+(\d+(?:\.\d+)?)\s*%",
    ]
    for pattern in pct_patterns:
        match = re.match(pattern, normalised.strip())
        if match:
            verb = match.group(1)
            project = _clean_project_name(match.group(2), original)
            pct = float(match.group(3)) / 100.0
            action_type = ActionType.BUDGET_DECREASE if verb in ("decrease", "reduce", "lower") else ActionType.BUDGET_INCREASE
            return ScenarioAction(
                action=action_type,
                project=project,
                amount=pct,
            )

    # Absolute amount: "increase project beta budget by £50,000"
    abs_patterns = [
        r"(increase|decrease|reduce|raise|boost|lower)\s+(?:project\s+)?(.+?)\s+budget\s+by\s+[£$€]?\s*(\d[\d,]*(?:\.\d+)?)",
        r"(increase|decrease|reduce|raise|boost|lower)\s+(?:the\s+)?budget\s+(?:for|of|on)\s+(?:project\s+)?(.+?)\s+by\s+[£$€]?\s*(\d[\d,]*(?:\.\d+)?)",
    ]
    for pattern in abs_patterns:
        match = re.match(pattern, normalised.strip())
        if match:
            verb = match.group(1)
            project = _clean_project_name(match.group(2), original)
            amount = float(match.group(3).replace(",", ""))
            action_type = ActionType.BUDGET_DECREASE if verb in ("decrease", "reduce", "lower") else ActionType.BUDGET_INCREASE
            return ScenarioAction(
                action=action_type,
                project=project,
                amount_absolute=amount,
            )

    return None


def _parse_scope_cut(normalised: str, original: str) -> ScenarioAction | None:
    """Parse 'cut/reduce Project X scope by Y%' patterns."""
    patterns = [
        r"(?:cut|reduce|trim|shrink)\s+(?:project\s+)?(.+?)\s+scope\s+by\s+(\d+(?:\.\d+)?)\s*%",
        r"(?:cut|reduce|trim|shrink)\s+(?:the\s+)?scope\s+(?:for|of|on)\s+(?:project\s+)?(.+?)\s+by\s+(\d+(?:\.\d+)?)\s*%",
    ]
    for pattern in patterns:
        match = re.match(pattern, normalised.strip())
        if match:
            project = _clean_project_name(match.group(1), original)
            pct = float(match.group(2)) / 100.0
            return ScenarioAction(
                action=ActionType.SCOPE_CUT,
                project=project,
                amount=pct,
            )
    return None


def _parse_delay(normalised: str, original: str) -> ScenarioAction | None:
    """Parse 'delay Project X by N weeks/months/quarters' patterns."""
    patterns = [
        r"(?:delay|push back|postpone|defer|extend)\s+(?:project\s+)?(.+?)\s+by\s+(\d+)\s+(week|weeks|month|months|quarter|quarters|year|years|fortnight|fortnights)",
        r"(?:delay|push back|postpone|defer|extend)\s+(?:project\s+)?(.+?)\s+(\d+)\s+(week|weeks|month|months|quarter|quarters|year|years|fortnight|fortnights)",
    ]
    for pattern in patterns:
        match = re.match(pattern, normalised.strip())
        if match:
            project = _clean_project_name(match.group(1), original)
            count = int(match.group(2))
            unit = match.group(3).lower()
            weeks_per_unit = DURATION_WEEKS.get(unit, 1)
            return ScenarioAction(
                action=ActionType.DELAY,
                project=project,
                duration_weeks=count * weeks_per_unit,
            )
    return None


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def _clean_project_name(name: str, original: str) -> str:
    """Clean and restore original case for project name.

    The regex match is from the normalised (lowercase) text.
    We find the same substring in the original text to preserve case.
    """
    name = name.strip().rstrip("'\"")

    # Find original case version
    name_lower = name.lower()
    orig_lower = original.lower()
    pos = orig_lower.find(name_lower)
    if pos != -1:
        name = original[pos:pos + len(name)].strip()

    return name
