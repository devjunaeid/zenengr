"""add_payments_and_void_tracking

Revision ID: 9dd10cbef8d3
Revises: 304989425c5d
Create Date: 2026-10-10 01:55:52.875340
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '9dd10cbef8d3'
down_revision: Union[str, None] = '304989425c5d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'paymentkind') THEN "
        "CREATE TYPE paymentkind AS ENUM ('RECEIPT', 'REFUND'); "
        "END IF; END $$;"
    )

    payment_method_enum = postgresql.ENUM(
        'BANK_TRANSFER', 'CARD', 'CASH', 'OTHER',
        name='paymentmethod',
        create_type=False,
    )
    payment_kind_enum = postgresql.ENUM(
        'RECEIPT', 'REFUND',
        name='paymentkind',
        create_type=False,
    )

    op.create_table('payments',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('client_id', sa.Uuid(), nullable=False),
    sa.Column('project_id', sa.Uuid(), nullable=True),
    sa.Column('kind', payment_kind_enum, nullable=False),
    sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('method', payment_method_enum, nullable=False),
    sa.Column('paid_on', sa.Date(), nullable=False),
    sa.Column('reference_note', sa.Text(), nullable=False),
    sa.Column('notes', sa.Text(), nullable=False),
    sa.Column('recorded_by_id', sa.Uuid(), nullable=True),
    sa.Column('voided_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('voided_by_id', sa.Uuid(), nullable=True),
    sa.Column('void_reason', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('amount > 0', name=op.f('ck_payments_ck_payments_amount_positive')),
    sa.ForeignKeyConstraint(['client_id'], ['clients.id'], name=op.f('fk_payments_client_id_clients'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name=op.f('fk_payments_project_id_projects'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['recorded_by_id'], ['admin_users.id'], name=op.f('fk_payments_recorded_by_id_admin_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name=op.f('fk_payments_tenant_id_tenants'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['voided_by_id'], ['admin_users.id'], name=op.f('fk_payments_voided_by_id_admin_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_payments'))
    )
    op.create_index(op.f('ix_payments_client_id'), 'payments', ['client_id'], unique=False)
    op.create_index(op.f('ix_payments_project_id'), 'payments', ['project_id'], unique=False)
    op.create_index('ix_payments_tenant_client', 'payments', ['tenant_id', 'client_id'], unique=False)
    op.create_index(op.f('ix_payments_tenant_id'), 'payments', ['tenant_id'], unique=False)
    op.create_index('ix_payments_tenant_project_date', 'payments', ['tenant_id', 'project_id', 'paid_on'], unique=False)
    op.add_column('ledger_entries', sa.Column('voided_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('ledger_entries', sa.Column('voided_by_id', sa.Uuid(), nullable=True))
    op.add_column('ledger_entries', sa.Column('void_reason', sa.Text(), nullable=False, server_default=''))
    op.create_foreign_key(op.f('fk_ledger_entries_voided_by_id_admin_users'), 'ledger_entries', 'admin_users', ['voided_by_id'], ['id'], ondelete='SET NULL')
    op.add_column('payment_allocations', sa.Column('payment_id', sa.Uuid(), nullable=True))
    op.add_column('payment_allocations', sa.Column('voided_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_payment_allocations_payment_id'), 'payment_allocations', ['payment_id'], unique=False)
    op.create_foreign_key(op.f('fk_payment_allocations_payment_id_payments'), 'payment_allocations', 'payments', ['payment_id'], ['id'], ondelete='CASCADE')
    op.add_column('transactions', sa.Column('payment_id', sa.Uuid(), nullable=True))
    op.add_column('transactions', sa.Column('voided_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_transactions_payment_id'), 'transactions', ['payment_id'], unique=False)
    op.create_foreign_key(op.f('fk_transactions_payment_id_payments'), 'transactions', 'payments', ['payment_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    op.drop_constraint(op.f('fk_transactions_payment_id_payments'), 'transactions', type_='foreignkey')
    op.drop_index(op.f('ix_transactions_payment_id'), table_name='transactions')
    op.drop_column('transactions', 'voided_at')
    op.drop_column('transactions', 'payment_id')
    op.drop_constraint(op.f('fk_payment_allocations_payment_id_payments'), 'payment_allocations', type_='foreignkey')
    op.drop_index(op.f('ix_payment_allocations_payment_id'), table_name='payment_allocations')
    op.drop_column('payment_allocations', 'voided_at')
    op.drop_column('payment_allocations', 'payment_id')
    op.drop_constraint(op.f('fk_ledger_entries_voided_by_id_admin_users'), 'ledger_entries', type_='foreignkey')
    op.drop_column('ledger_entries', 'void_reason')
    op.drop_column('ledger_entries', 'voided_by_id')
    op.drop_column('ledger_entries', 'voided_at')
    op.drop_index('ix_payments_tenant_project_date', table_name='payments')
    op.drop_index(op.f('ix_payments_tenant_id'), table_name='payments')
    op.drop_index('ix_payments_tenant_client', table_name='payments')
    op.drop_index(op.f('ix_payments_project_id'), table_name='payments')
    op.drop_index(op.f('ix_payments_client_id'), table_name='payments')
    op.drop_table('payments')

    op.execute("DROP TYPE IF EXISTS paymentkind;")


