"""Schemas for company-wide reports and global analytics (FEAT-025, TODO-213)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class CompanyLedgerSummary(BaseModel):
    """Executive KPI totals for the selected reporting window."""

    period_from: date | None = None
    period_to: date | None = None
    new_projects_count: int = 0
    new_clients_count: int = 0
    new_services_count: int = 0
    new_services_value: str = "0.00"
    total_invoiced: str = "0.00"
    total_collected: str = "0.00"
    total_due: str = "0.00"
    total_advance_balance: str = "0.00"


class CompanyLedgerTimelineItem(BaseModel):
    """Chronological time-bucketed rollup for operational and financial movement."""

    period: str  # e.g. "2026-09" or "2026-09-26"
    period_label: str  # e.g. "Sep 2026" or "26 Sep 2026"
    new_projects: int = 0
    new_clients: int = 0
    new_services: int = 0
    invoiced_amount: str = "0.00"
    collected_amount: str = "0.00"
    net_due_change: str = "0.00"


class CompanyLedgerProjectItem(BaseModel):
    """Project-level financial and operational summary."""

    project_id: uuid.UUID
    short_id: str
    name: str
    client_id: uuid.UUID
    client_name: str
    status: str
    created_at: datetime
    services_count: int = 0
    total_value: str = "0.00"
    total_invoiced: str = "0.00"
    total_paid: str = "0.00"
    balance_due: str = "0.00"


class CompanyLedgerClientItem(BaseModel):
    """Client-level cumulative billing and receivables summary."""

    client_id: uuid.UUID
    name: str
    client_type: str
    created_at: datetime
    active_projects_count: int = 0
    total_services_count: int = 0
    total_invoiced: str = "0.00"
    total_paid: str = "0.00"
    total_due: str = "0.00"
    advance_balance: str = "0.00"


class CompanyLedgerResponse(BaseModel):
    """Complete company global ledger & analytics response."""

    summary: CompanyLedgerSummary
    timeline: list[CompanyLedgerTimelineItem]
    projects: list[CompanyLedgerProjectItem]
    clients: list[CompanyLedgerClientItem]
    filters_applied: dict[str, Any] = Field(default_factory=dict)
