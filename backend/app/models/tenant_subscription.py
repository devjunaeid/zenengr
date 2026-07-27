from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin
from app.models.enums import BillingCycle, SubscriptionStatus

if TYPE_CHECKING:
    from app.models.tenant import Tenant


class TenantSubscription(TimestampMixin, Base):
    __tablename__ = "tenant_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id"), unique=True, nullable=False
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("plans.id"), nullable=False)
    status: Mapped[SubscriptionStatus] = mapped_column(
        default=SubscriptionStatus.TRIALING, nullable=False
    )
    billing_cycle: Mapped[BillingCycle] = mapped_column(
        default=BillingCycle.MONTHLY, nullable=False
    )
    renewal_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="subscription")
