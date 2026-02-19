"""
Benefits register parser & data model.

Parses benefit tracker CSVs/Excel and links benefits to projects.
Supports flexible column mapping (like the project parser).

Sprint 5 — Issue #29.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any

import pandas as pd


class BenefitCategory(Enum):
    REVENUE = "Revenue"
    COST_SAVING = "Cost Saving"
    COST_AVOIDANCE = "Cost Avoidance"
    EFFICIENCY = "Efficiency"
    STRATEGIC = "Strategic"
    RISK_MITIGATION = "Risk Mitigation"
    OTHER = "Other"


class BenefitStatus(Enum):
    ON_TRACK = "On Track"
    AT_RISK = "At Risk"
    DELAYED = "Delayed"
    CANCELLED = "Cancelled"
    REALISED = "Realised"
    PARTIAL = "Partial"
    NOT_STARTED = "Not Started"


class BenefitConfidence(Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


@dataclass
class Benefit:
    """A single benefit linked to a project."""
    benefit_id: str
    name: str
    project_name: str
    category: BenefitCategory
    expected_value: float
    realised_value: float
    target_date: date | None
    status: BenefitStatus
    confidence: BenefitConfidence
    owner: str
    notes: str

    @property
    def realisation_pct(self) -> float:
        if self.expected_value <= 0:
            return 0.0
        return self.realised_value / self.expected_value

    @property
    def unrealised_value(self) -> float:
        return max(0, self.expected_value - self.realised_value)

    @property
    def is_at_risk(self) -> bool:
        return self.status in (BenefitStatus.AT_RISK, BenefitStatus.DELAYED, BenefitStatus.CANCELLED)

    def to_dict(self) -> dict[str, Any]:
        return {
            "benefit_id": self.benefit_id,
            "name": self.name,
            "project_name": self.project_name,
            "category": self.category.value,
            "expected_value": self.expected_value,
            "realised_value": self.realised_value,
            "realisation_pct": round(self.realisation_pct * 100, 1),
            "target_date": self.target_date.isoformat() if self.target_date else None,
            "status": self.status.value,
            "confidence": self.confidence.value,
            "owner": self.owner,
            "notes": self.notes,
        }


# ──────────────────────────────────────────────
# Column aliases (flexible mapping)
# ──────────────────────────────────────────────

_PROJECT_ALIASES = {"project", "project name", "project_name", "project key", "programme"}
_NAME_ALIASES = {"benefit", "benefit name", "benefit_name", "description", "benefit description", "expected annual benefit"}
_EXPECTED_ALIASES = {"expected", "expected value", "expected_value", "expected annual benefit", "planned benefit", "target value", "forecast", "expected benefit"}
_REALISED_ALIASES = {"realised", "realised value", "realised_value", "actual benefit", "realised benefit", "realised benefit to date", "actual value", "actual"}
_STATUS_ALIASES = {"status", "benefit status", "benefit_status", "realisation status"}
_CATEGORY_ALIASES = {"category", "benefit category", "benefit_category", "type", "benefit type"}
_TARGET_DATE_ALIASES = {"target date", "target_date", "target realisation date", "realisation date", "due date", "benefit due"}
_OWNER_ALIASES = {"owner", "benefit owner", "benefit_owner", "responsible", "accountable"}
_CONFIDENCE_ALIASES = {"confidence", "confidence level", "certainty", "likelihood"}
_NOTES_ALIASES = {"notes", "comments", "remarks", "detail", "description"}

STATUS_MAP = {
    "on track": BenefitStatus.ON_TRACK,
    "on-track": BenefitStatus.ON_TRACK,
    "green": BenefitStatus.ON_TRACK,
    "at risk": BenefitStatus.AT_RISK,
    "at-risk": BenefitStatus.AT_RISK,
    "amber": BenefitStatus.AT_RISK,
    "delayed": BenefitStatus.DELAYED,
    "red": BenefitStatus.DELAYED,
    "cancelled": BenefitStatus.CANCELLED,
    "canceled": BenefitStatus.CANCELLED,
    "closed": BenefitStatus.CANCELLED,
    "realised": BenefitStatus.REALISED,
    "realized": BenefitStatus.REALISED,
    "complete": BenefitStatus.REALISED,
    "achieved": BenefitStatus.REALISED,
    "partial": BenefitStatus.PARTIAL,
    "partially realised": BenefitStatus.PARTIAL,
    "in progress": BenefitStatus.PARTIAL,
    "not started": BenefitStatus.NOT_STARTED,
    "not yet started": BenefitStatus.NOT_STARTED,
    "pending": BenefitStatus.NOT_STARTED,
    "planned": BenefitStatus.NOT_STARTED,
}

CATEGORY_MAP = {
    "revenue": BenefitCategory.REVENUE,
    "income": BenefitCategory.REVENUE,
    "sales": BenefitCategory.REVENUE,
    "new product": BenefitCategory.REVENUE,
    "new market": BenefitCategory.REVENUE,
    "cost saving": BenefitCategory.COST_SAVING,
    "cost reduction": BenefitCategory.COST_SAVING,
    "savings": BenefitCategory.COST_SAVING,
    "cost avoidance": BenefitCategory.COST_AVOIDANCE,
    "avoidance": BenefitCategory.COST_AVOIDANCE,
    "efficiency": BenefitCategory.EFFICIENCY,
    "productivity": BenefitCategory.EFFICIENCY,
    "process": BenefitCategory.EFFICIENCY,
    "automation": BenefitCategory.EFFICIENCY,
    "strategic": BenefitCategory.STRATEGIC,
    "capability": BenefitCategory.STRATEGIC,
    "risk": BenefitCategory.RISK_MITIGATION,
    "compliance": BenefitCategory.RISK_MITIGATION,
    "regulatory": BenefitCategory.RISK_MITIGATION,
    "risk mitigation": BenefitCategory.RISK_MITIGATION,
}


# ──────────────────────────────────────────────
# Parser
# ──────────────────────────────────────────────


def parse_benefits(file_path: str | Path) -> list[Benefit]:
    """Parse a benefits register file (CSV or Excel) into Benefit objects."""
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext == ".csv":
        df = pd.read_csv(path)
    elif ext in (".xlsx", ".xls"):
        df = pd.read_excel(path)
    elif ext == ".json":
        df = pd.read_json(path)
    else:
        raise ValueError(f"Unsupported format: {ext}")

    # Normalise column names
    df.columns = [str(c).strip().lower() for c in df.columns]

    # Map columns
    col_map = _find_columns(df.columns.tolist())

    benefits: list[Benefit] = []
    for idx, row in df.iterrows():
        try:
            b = _parse_row(row, col_map, idx)
            if b is not None:
                benefits.append(b)
        except Exception:
            continue

    return benefits


def _find_columns(columns: list[str]) -> dict[str, str | None]:
    """Map logical field names to actual column names."""
    def _find(aliases: set[str]) -> str | None:
        for col in columns:
            if col in aliases:
                return col
        # Partial match
        for col in columns:
            for alias in aliases:
                if alias in col or col in alias:
                    return col
        return None

    return {
        "project": _find(_PROJECT_ALIASES),
        "name": _find(_NAME_ALIASES),
        "expected": _find(_EXPECTED_ALIASES),
        "realised": _find(_REALISED_ALIASES),
        "status": _find(_STATUS_ALIASES),
        "category": _find(_CATEGORY_ALIASES),
        "target_date": _find(_TARGET_DATE_ALIASES),
        "owner": _find(_OWNER_ALIASES),
        "confidence": _find(_CONFIDENCE_ALIASES),
        "notes": _find(_NOTES_ALIASES),
    }


def _parse_row(row: pd.Series, col_map: dict[str, str | None], idx: int) -> Benefit | None:
    """Parse a single row into a Benefit."""
    project = _get_str(row, col_map.get("project"))
    if not project:
        return None

    name = _get_str(row, col_map.get("name")) or f"Benefit {idx + 1}"
    expected = _get_float(row, col_map.get("expected"))
    realised = _get_float(row, col_map.get("realised"))
    status = _parse_status(_get_str(row, col_map.get("status")))
    category = _parse_category(_get_str(row, col_map.get("category")))
    target_date = _parse_date(_get_str(row, col_map.get("target_date")))
    owner = _get_str(row, col_map.get("owner")) or "Unassigned"
    confidence = _parse_confidence(_get_str(row, col_map.get("confidence")))
    notes = _get_str(row, col_map.get("notes")) or ""

    # Auto-derive confidence from status if not provided
    if confidence == BenefitConfidence.MEDIUM:  # default
        if status == BenefitStatus.REALISED:
            confidence = BenefitConfidence.HIGH
        elif status in (BenefitStatus.AT_RISK, BenefitStatus.DELAYED):
            confidence = BenefitConfidence.LOW
        elif expected == 0 and realised == 0:
            confidence = BenefitConfidence.LOW

    return Benefit(
        benefit_id=f"BEN-{idx + 1:03d}",
        name=name,
        project_name=project,
        category=category,
        expected_value=expected,
        realised_value=realised,
        target_date=target_date,
        status=status,
        confidence=confidence,
        owner=owner,
        notes=notes,
    )


# ──────────────────────────────────────────────
# Value extraction helpers
# ──────────────────────────────────────────────

def _get_str(row: pd.Series, col: str | None) -> str:
    if col is None or col not in row.index:
        return ""
    val = row[col]
    if pd.isna(val):
        return ""
    return str(val).strip()


def _get_float(row: pd.Series, col: str | None) -> float:
    if col is None or col not in row.index:
        return 0.0
    val = row[col]
    if pd.isna(val):
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    # Try parsing string with currency symbols
    cleaned = str(val).replace("£", "").replace("$", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return 0.0


def _parse_date(val: str) -> date | None:
    if not val:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(val.split(" ")[0], fmt).date()
        except (ValueError, IndexError):
            continue
    # Try pandas
    try:
        return pd.to_datetime(val).date()
    except Exception:
        return None


def _parse_status(val: str) -> BenefitStatus:
    if not val:
        return BenefitStatus.NOT_STARTED
    key = val.strip().lower()
    # Direct match
    if key in STATUS_MAP:
        return STATUS_MAP[key]
    # Partial match
    for keyword, status in STATUS_MAP.items():
        if keyword in key:
            return status
    return BenefitStatus.NOT_STARTED


def _parse_category(val: str) -> BenefitCategory:
    if not val:
        return BenefitCategory.OTHER
    key = val.strip().lower()
    # Check each keyword
    for keyword, cat in CATEGORY_MAP.items():
        if keyword in key:
            return cat
    return BenefitCategory.OTHER


def _parse_confidence(val: str) -> BenefitConfidence:
    if not val:
        return BenefitConfidence.MEDIUM
    key = val.strip().lower()
    if "high" in key:
        return BenefitConfidence.HIGH
    if "low" in key:
        return BenefitConfidence.LOW
    return BenefitConfidence.MEDIUM
