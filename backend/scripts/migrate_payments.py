"""Migration script to backfill legacy direct LedgerEntry payments and Transaction records into unified Payment rows (TODO-225).

Usage:
    # Dry run (default - reports what would be migrated without committing):
    uv run python -m scripts.migrate_payments

    # Commit changes:
    uv run python -m scripts.migrate_payments --commit
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import get_settings
from app.models.enums import (
    LedgerEntryType,
    LedgerSourceType,
    PaymentKind,
    PaymentMethod,
    TransactionDirection,
)
from app.models.invoice import Invoice
from app.models.ledger_entry import LedgerEntry
from app.models.payment import Payment
from app.models.project import Project
from app.models.transaction import PaymentAllocation, Transaction


async def run_migration(commit: bool = False) -> None:
    settings = get_settings()
    db_url = settings.database_url
    print(f"==> Connecting to database: {db_url.split('@')[-1] if '@' in db_url else db_url}")
    print(f"==> Mode: {'COMMIT' if commit else 'DRY RUN (no database changes will be saved)'}\n")

    engine = create_async_engine(db_url)
    async with AsyncSession(engine) as session:
        # ── 1. Direct Ledger Payments Migration ─────────────────────────────
        direct_entries_stmt = (
            select(LedgerEntry)
            .where(
                LedgerEntry.type == LedgerEntryType.PAYMENT,
                LedgerEntry.source_id.is_(None),
            )
            .order_by(LedgerEntry.created_at)
        )
        direct_entries = list((await session.execute(direct_entries_stmt)).scalars().all())
        print(f"==> Found {len(direct_entries)} direct LedgerEntry payment(s) to migrate.")

        ledger_migrated_count = 0
        for entry in direct_entries:
            project = await session.get(Project, entry.project_id)
            if not project:
                print(f"    [WARN] LedgerEntry {entry.id} references missing project {entry.project_id}, skipping.")
                continue

            # Determine payment method from description if mentioned
            desc_lower = (entry.description or "").lower()
            method = PaymentMethod.OTHER
            if "cash" in desc_lower:
                method = PaymentMethod.CASH
            elif "bank" in desc_lower or "transfer" in desc_lower or "wire" in desc_lower:
                method = PaymentMethod.BANK_TRANSFER
            elif "card" in desc_lower or "stripe" in desc_lower:
                method = PaymentMethod.CARD
            elif "cheque" in desc_lower or "check" in desc_lower:
                method = PaymentMethod.CHEQUE

            payment = Payment(
                tenant_id=project.tenant_id,
                project_id=project.id,
                client_id=project.client_id,
                amount=entry.amount,
                kind=PaymentKind.RECEIPT,
                method=method,
                paid_on=entry.entry_date,
                reference_note=entry.description or "",
                created_at=entry.created_at,
                voided_at=entry.voided_at,
                void_reason=entry.void_reason or "",
            )
            session.add(payment)
            await session.flush()

            entry.source_type = LedgerSourceType.TRANSACTION
            entry.source_id = payment.id
            ledger_migrated_count += 1
            print(
                f"    [+] Created Payment {payment.id} for LedgerEntry {entry.id} "
                f"(Amount: {payment.amount}, Project: {project.name})"
            )

        # ── 2. Invoice Transactions Migration ───────────────────────────────
        unlinked_tx_stmt = (
            select(Transaction)
            .where(Transaction.payment_id.is_(None))
            .order_by(Transaction.created_at)
        )
        unlinked_txs = list((await session.execute(unlinked_tx_stmt)).scalars().all())
        print(f"\n==> Found {len(unlinked_txs)} unlinked Invoice Transaction(s) to migrate.")

        tx_migrated_count = 0
        allocations_linked_count = 0

        for tx in unlinked_txs:
            invoice = await session.get(Invoice, tx.invoice_id)
            if not invoice:
                print(f"    [WARN] Transaction {tx.id} references missing invoice {tx.invoice_id}, skipping.")
                continue

            project = await session.get(Project, invoice.project_id)
            if not project:
                print(f"    [WARN] Invoice {invoice.id} references missing project {invoice.project_id}, skipping.")
                continue

            pay_date = tx.recorded_at.date() if tx.recorded_at else tx.created_at.date()
            kind = PaymentKind.REFUND if tx.direction == TransactionDirection.CREDIT else PaymentKind.RECEIPT

            payment = Payment(
                tenant_id=invoice.tenant_id,
                project_id=invoice.project_id,
                client_id=project.client_id,
                amount=tx.amount,
                kind=kind,
                method=tx.method,
                paid_on=pay_date,
                reference_note=tx.reference_note or "",
                created_at=tx.created_at,
                voided_at=tx.voided_at,
                void_reason="",
            )
            session.add(payment)
            await session.flush()

            tx.payment_id = payment.id
            tx_migrated_count += 1

            # Link existing payment allocations
            alloc_stmt = select(PaymentAllocation).where(
                PaymentAllocation.transaction_id == tx.id,
                PaymentAllocation.payment_id.is_(None),
            )
            allocs = list((await session.execute(alloc_stmt)).scalars().all())
            for alloc in allocs:
                alloc.payment_id = payment.id
                allocations_linked_count += 1

            print(
                f"    [+] Created Payment {payment.id} for Transaction {tx.id} "
                f"(Amount: {payment.amount}, Invoice: {invoice.invoice_number or invoice.id}, Allocations: {len(allocs)})"
            )

        print("\n" + "=" * 60)
        print("SUMMARY:")
        print(f"  Direct ledger payments migrated : {ledger_migrated_count}")
        print(f"  Invoice transactions migrated   : {tx_migrated_count}")
        print(f"  Allocations linked              : {allocations_linked_count}")
        print("=" * 60)

        if commit:
            await session.commit()
            print("\n🎉 All migrations successfully COMMITTED to the database!")
        else:
            await session.rollback()
            print("\nℹ️ DRY RUN complete: No database changes were saved. Pass --commit to apply.")

    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill legacy payments and transactions into Payment rows.")
    parser.add_argument("--commit", action="store_true", help="Persist the changes to the database.")
    args = parser.parse_args()

    asyncio.run(run_migration(commit=args.commit))


if __name__ == "__main__":
    main()
