import os


os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from app.contas_pagar_routes import ContaPagarCreate, ContaPagarUpdate


def test_schema_recorrencia_trata_datas_opcionais_vazias_como_nulas():
    update = ContaPagarUpdate.model_validate(
        {
            "data_inicio_recorrencia": "",
            "data_fim_recorrencia": "",
        }
    )

    assert update.data_inicio_recorrencia is None
    assert update.data_fim_recorrencia is None

    create = ContaPagarCreate.model_validate(
        {
            "descricao": "Pro labore",
            "valor_original": 3000,
            "data_emissao": "2026-05-06",
            "data_vencimento": "2026-05-06",
            "data_inicio_recorrencia": "",
            "data_fim_recorrencia": "",
        }
    )

    assert create.data_inicio_recorrencia is None
    assert create.data_fim_recorrencia is None
