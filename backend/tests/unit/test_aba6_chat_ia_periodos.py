from datetime import date, datetime, timedelta

from app.ia.aba6_chat_ia_parts.base import ChatIABase
from app.ia.aba6_chat_ia_parts.periodos import ChatIAPeriodosMixin
from app.ia.aba6_chat_ia_parts.service import ChatIAService
from app.ia.aba6_resposta_simples import gerar_resposta_simples


def test_helpers_refatorados_continuam_chamaveis_pela_instancia():
    service = ChatIAService(None)

    assert service._normalizar_texto("Situação Financeira") == "situacao financeira"
    assert service.LABEL_MES_ATUAL == "mes atual"
    assert service._date_bounds_for_today()[0].date() == date.today()
    assert service._date_bounds_for_current_month()[0] == datetime(
        date.today().year, date.today().month, 1
    )


def test_detecta_intervalo_explicito_em_portugues():
    service = ChatIAService(None)

    periodo = service._detectar_periodo(
        "Mostre o ranking de clientes de 01/08/2026 a 31/08/2026"
    )

    assert periodo["inicio"] == datetime(2026, 8, 1)
    assert periodo["fim"] == datetime(2026, 8, 31, 23, 59, 59, 999999)
    assert periodo["label"] == "01/08/2026 a 31/08/2026"


def test_detecta_ontem_com_dia_completo():
    service = ChatIAService(None)
    ontem = date.today() - timedelta(days=1)

    periodo = service._detectar_periodo("Qual foi o total de vendas de ontem?")

    assert periodo["inicio"] == datetime.combine(ontem, datetime.min.time())
    assert periodo["fim"] == datetime.combine(ontem, datetime.max.time())
    assert periodo["label"] == "ontem"


class _RespostaService(ChatIAPeriodosMixin, ChatIABase):
    def _montar_resumo_executivo_periodo(self, _tenant_id, periodo, limite_rankings=5):
        assert limite_rankings == 10
        return {
            "periodo": periodo,
            "resumo_vendas": {},
            "produtos": {},
            "dre": {},
            "rankings": {
                "top_clientes": [
                    {
                        "cliente": "Maria Silva",
                        "valor_total": 1234.56,
                        "quantidade_compras": 3,
                    }
                ]
            },
        }


def test_responde_ranking_de_clientes_no_intervalo_solicitado():
    service = _RespostaService(None)

    resposta = gerar_resposta_simples(
        service,
        (
            "Mostre o ranking dos 10 clientes que mais compraram de "
            "01/08/2026 a 31/08/2026"
        ),
        {},
        tenant_id="tenant-1",
    )

    assert "Clientes que Mais Compraram (01/08/2026 a 31/08/2026)" in resposta
    assert "1. Maria Silva" in resposta
    assert "R$ 1.234,56" in resposta
    assert "3 compra(s)" in resposta
