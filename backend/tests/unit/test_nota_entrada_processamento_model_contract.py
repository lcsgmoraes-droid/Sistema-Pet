from app.produtos_models import NotaEntrada


def test_nota_entrada_expoe_acoes_processamento():
    columns = NotaEntrada.__table__.columns

    assert "processamento_acoes" in columns
    assert "processamento_contexto" in columns
