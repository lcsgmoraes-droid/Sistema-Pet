from datetime import datetime, timezone

from app.campaigns.models import CashbackTransaction
from app.routes.ecommerce_auth import _cashback_disponivel_clause


def test_cashback_disponivel_clause_usa_or_sqlalchemy():
    clause = _cashback_disponivel_clause(
        CashbackTransaction,
        datetime(2026, 4, 24, tzinfo=timezone.utc),
    )

    sql = str(clause.compile(compile_kwargs={"literal_binds": False})).upper()

    assert " OR " in sql
    assert "EXPIRES_AT IS NULL" in sql
    assert "TX_TYPE" in sql

