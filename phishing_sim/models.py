"""Shared data structures for campaigns, recipients, and tracked events."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

# Event types recorded against a recipient
EVT_CLICK = "click"          # tracking link opened
EVT_SUBMIT = "submit"        # fake form submitted (credential not stored)


@dataclass
class Recipient:
    id: int | None
    campaign_id: int
    name: str
    email: str
    token: str  # unique URL token, hex(16)
    clicked_at: datetime | None = None
    submitted_at: datetime | None = None


@dataclass
class Campaign:
    id: int | None
    name: str
    template: str         # landing page template name
    created_at: datetime = field(default_factory=datetime.utcnow)
    recipients: list[Recipient] = field(default_factory=list)

    @property
    def click_count(self) -> int:
        return sum(1 for r in self.recipients if r.clicked_at)

    @property
    def submit_count(self) -> int:
        return sum(1 for r in self.recipients if r.submitted_at)

    @property
    def click_rate(self) -> float:
        n = len(self.recipients)
        return self.click_count / n if n else 0.0

    @property
    def submit_rate(self) -> float:
        n = len(self.recipients)
        return self.submit_count / n if n else 0.0
