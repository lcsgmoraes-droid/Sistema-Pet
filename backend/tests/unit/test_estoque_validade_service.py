import os

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"

from app.estoque_validade_models import EstoqueValidadeBloqueio


def test_validade_bloqueio_model_declares_statuses_and_quantities():
    campos = EstoqueValidadeBloqueio.__table__.columns

    assert "produto_id" in campos
    assert "lote_id" in campos
    assert "status" in campos
    assert "quantidade_bloqueada" in campos
    assert "quantidade_resolvida" in campos
    assert "custo_total_estimado" in campos
    assert "movimentacao_bloqueio_id" in campos
    assert "movimentacao_resolucao_id" in campos
