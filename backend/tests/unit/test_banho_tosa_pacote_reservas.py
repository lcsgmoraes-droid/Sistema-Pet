from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace as NS

import pytest

from app import banho_tosa_pacote_reservas as regras
from app.banho_tosa_pacotes import calcular_saldo_creditos, credito_disponivel
from app.banho_tosa_pacotes_serializers import resumo_financeiro_credito
from app.banho_tosa_pacotes_serializers import serializar_credito


def _credito(**campos):
    base = dict(
        id=1,
        cliente_id=2,
        pet_id=3,
        status="ativo",
        data_inicio=date.today() - timedelta(days=5),
        data_validade=date.today() + timedelta(days=25),
        creditos_total=Decimal("4"),
        creditos_usados=Decimal("0"),
        creditos_cancelados=Decimal("0"),
        creditos_reservados=Decimal("0"),
        servicos=[
            {"servico_id": 10, "servico_nome": "Banho", "quantidade_creditos": 4}
        ],
        movimentos=[],
        valor_pacote=Decimal("200"),
        venda=None,
    )
    base.update(campos)
    return NS(**base)


def test_disponivel_respeita_inicio_reserva_e_vencimento_sem_apagar_saldo():
    credito = _credito(creditos_reservados=Decimal("4"))
    assert credito_disponivel(credito) is False
    credito.creditos_reservados = Decimal("0")
    credito.data_inicio = date.today() + timedelta(days=1)
    assert credito_disponivel(credito) is False
    credito.data_inicio = date.today() - timedelta(days=30)
    credito.data_validade = date.today() - timedelta(days=1)
    assert credito_disponivel(credito) is False
    assert calcular_saldo_creditos(
        credito.creditos_total, credito.creditos_usados, credito.creditos_cancelados
    ) == Decimal("4")


def test_validade_termina_meia_noite_brasilia_em_vez_de_21h(monkeypatch):
    from app.utils import timezone as timezone_utils

    relogio = {"utc": datetime(2026, 10, 28, 0, 30, tzinfo=timezone.utc)}

    class DatetimeFixo:
        @classmethod
        def now(cls, tz=None):
            return (
                relogio["utc"].astimezone(tz)
                if tz
                else relogio["utc"].replace(tzinfo=None)
            )

    monkeypatch.setattr(timezone_utils, "datetime", DatetimeFixo)
    credito = _credito(
        data_inicio=date(2026, 10, 1),
        data_validade=date(2026, 10, 27),
        pacote_id=1,
        pacote=None,
        cliente=None,
        pet=None,
        venda_id=None,
        observacoes=None,
    )
    assert credito_disponivel(credito) is True
    assert serializar_credito(credito)["vencido"] is False
    assert serializar_credito(credito)["disponivel"] is True
    relogio["utc"] = datetime(2026, 10, 28, 3, 0, tzinfo=timezone.utc)
    assert credito_disponivel(credito) is False
    assert serializar_credito(credito)["vencido"] is True
    assert serializar_credito(credito)["saldo_creditos"] == Decimal("4")


def test_cotas_por_servico_e_estorno_nao_misturam_banho_com_tosa():
    credito = _credito(
        creditos_total=Decimal("6"),
        servicos=[
            {"servico_id": 10, "quantidade_creditos": 4},
            {"servico_id": 20, "quantidade_creditos": 2},
        ],
        movimentos=[
            NS(servico_id=10, tipo="consumo", quantidade=1),
            NS(servico_id=10, tipo="reserva", quantidade=2),
            NS(servico_id=10, tipo="estorno_reserva", quantidade=1),
            NS(servico_id=20, tipo="consumo", quantidade=1),
            NS(servico_id=20, tipo="estorno", quantidade=1),
        ],
    )
    saldo = {s["servico_id"]: s for s in regras.saldos_por_servico(credito)}
    assert saldo[10]["saldo_creditos"] == Decimal("2")
    assert saldo[10]["creditos_usados"] == Decimal("1")
    assert saldo[10]["creditos_reservados"] == Decimal("1")
    assert saldo[20]["saldo_creditos"] == Decimal("2")


def test_contrato_preserva_composicao_mesmo_se_modelo_do_pacote_mudar():
    credito = _credito(pacote=NS(servico_id=99, quantidade_creditos=10))
    assert regras.composicao_contrato(credito)[0]["servico_id"] == 10
    assert regras.composicao_contrato(credito)[0]["quantidade_creditos"] == 4


def test_encerramento_manual_exibe_cotas_sem_disponibilidade():
    credito = _credito(status="encerrado", creditos_cancelados=4)
    assert regras.saldos_por_servico(credito)[0]["saldo_creditos"] == 0


class _Query:
    def __init__(self, db):
        self.db = db

    def filter(self, *args):
        return self

    def order_by(self, *args):
        return self

    def with_for_update(self, **kwargs):
        self.db.bloqueios += 1
        return self

    def populate_existing(self):
        return self

    def all(self):
        return self.db.creditos


class _Db:
    def __init__(self, creditos):
        self.creditos = creditos
        self.bloqueios = 0
        self.novos = []

    def query(self, *args):
        return _Query(self)

    def flush(self):
        pass

    def expire(self, *args):
        pass

    def add(self, movimento):
        self.novos.append(movimento)
        next(
            c for c in self.creditos if c.id == movimento.credito_id
        ).movimentos.append(movimento)


def _agendamento(id=1, servico=10, quantidade=1):
    return NS(
        id=id,
        cliente_id=2,
        pet_id=3,
        data_hora_inicio=datetime.now(),
        servicos=[
            NS(
                id=id,
                servico_id=servico,
                quantidade=Decimal(str(quantidade)),
                pacote_credito_id=None,
                pacote_quantidade=Decimal("0"),
            )
        ],
    )


def test_agendar_reserva_uma_vez_e_impede_gastar_o_ultimo_saldo_duas_vezes(monkeypatch):
    monkeypatch.setattr(
        regras, "BanhoTosaPacoteMovimento", lambda **kwargs: NS(**kwargs)
    )
    credito = _credito(
        creditos_total=Decimal("1"),
        servicos=[{"servico_id": 10, "quantidade_creditos": 1}],
    )
    db = _Db([credito])
    primeiro, segundo = _agendamento(), _agendamento(id=2)
    regras.reservar_creditos_agendamento(db, "tenant", primeiro, 9)
    regras.reservar_creditos_agendamento(db, "tenant", primeiro, 9)
    regras.reservar_creditos_agendamento(db, "tenant", segundo, 9)
    assert credito.creditos_reservados == Decimal("1")
    assert primeiro.servicos[0].pacote_quantidade == Decimal("1")
    assert segundo.servicos[0].pacote_quantidade == Decimal("0")
    assert len(db.novos) == 1
    assert db.bloqueios == 3


def test_pacote_que_vence_primeiro_e_aplicado_e_extras_continuam_cobraveis(monkeypatch):
    monkeypatch.setattr(
        regras, "BanhoTosaPacoteMovimento", lambda **kwargs: NS(**kwargs)
    )
    primeiro = _credito(id=1, data_validade=date.today() + timedelta(days=20))
    vence_antes = _credito(id=2, data_validade=date.today() + timedelta(days=2))
    db = _Db([primeiro, vence_antes])
    agendamento = _agendamento()
    agendamento.servicos.append(
        NS(
            id=3,
            servico_id=99,
            quantidade=1,
            pacote_credito_id=None,
            pacote_quantidade=0,
        )
    )
    regras.reservar_creditos_agendamento(db, "tenant", agendamento)
    assert agendamento.servicos[0].pacote_credito_id == 2
    assert agendamento.servicos[1].pacote_credito_id is None
    assert primeiro.creditos_reservados == 0


def test_reserva_pode_somar_dois_contratos_sem_cobrar_o_mesmo_servico_de_novo(
    monkeypatch,
):
    monkeypatch.setattr(
        regras, "BanhoTosaPacoteMovimento", lambda **kwargs: NS(**kwargs)
    )
    creditos = [
        _credito(
            id=i,
            creditos_total=Decimal("1"),
            servicos=[{"servico_id": 10, "quantidade_creditos": 1}],
        )
        for i in (1, 2)
    ]
    db = _Db(creditos)
    agendamento = _agendamento(quantidade=3)
    regras.reservar_creditos_agendamento(db, "tenant", agendamento)
    assert agendamento.servicos[0].pacote_quantidade == Decimal("2")
    assert len(db.novos) == 2
    assert all(c.creditos_reservados == Decimal("1") for c in creditos)


def test_checkin_com_dois_servicos_preserva_deltas_com_autoflush_desligado(monkeypatch):
    from app.banho_tosa_models import BanhoTosaPacoteMovimento

    movimentos = [
        NS(
            id=i,
            credito_id=1,
            quantidade=Decimal("1"),
            tipo="reserva",
            servico_id=s,
            observacoes="Reserva",
            atendimento_id=None,
        )
        for i, s in ((1, 10), (2, 20))
    ]
    estado = {"creditos_usados": Decimal("0"), "creditos_reservados": Decimal("2")}

    class DbSemAutoflush:
        def __init__(self):
            self.carregado = None
            self.confirmacoes = []

        def query(self, *args):
            return NS(
                filter=lambda *args: NS(
                    order_by=lambda *args: NS(all=lambda: movimentos)
                )
            )

        def add(self, movimento):
            self.confirmacoes.append(movimento)

        def flush(self):
            if self.carregado:
                estado.update(
                    creditos_usados=self.carregado.creditos_usados,
                    creditos_reservados=self.carregado.creditos_reservados,
                )

    db = DbSemAutoflush()

    def recarregar(*args):
        # Simula populate_existing: descarta mudanças ainda não enviadas ao banco.
        db.carregado = _credito(**estado)
        return db.carregado

    monkeypatch.setattr(regras, "reservar_creditos_agendamento", lambda *args: None)
    monkeypatch.setattr(regras, "_bloquear_credito", recarregar)

    # Objeto callable que mantém as colunas consultadas pelo helper.
    class FabricaMovimento:
        tenant_id = BanhoTosaPacoteMovimento.tenant_id
        agendamento_id = BanhoTosaPacoteMovimento.agendamento_id
        tipo = BanhoTosaPacoteMovimento.tipo
        credito_id = BanhoTosaPacoteMovimento.credito_id
        id = BanhoTosaPacoteMovimento.id

        def __new__(cls, **kwargs):
            return NS(**kwargs)

    monkeypatch.setattr(regras, "BanhoTosaPacoteMovimento", FabricaMovimento)
    atendimento = NS(id=42, pacote_credito_id=None, pacote_movimento_id=None)
    regras.confirmar_reservas_checkin(db, "tenant", _agendamento(), atendimento)
    assert estado == {
        "creditos_usados": Decimal("2"),
        "creditos_reservados": Decimal("0"),
    }
    assert len(db.confirmacoes) == 2
    assert all(m.tipo == "consumo" for m in movimentos)


@pytest.mark.parametrize(
    ("pagamentos", "contas", "status", "pago"),
    [
        ([NS(valor=200, status="estornado", forma_pagamento="pix")], [], "pendente", 0),
        (
            [
                NS(
                    valor=200,
                    status="aprovado",
                    forma_pagamento="crediario",
                    forma_pagamento_id=1,
                )
            ],
            [],
            "pendente",
            0,
        ),
        (
            [
                NS(
                    valor=200,
                    status="aprovado",
                    forma_pagamento="crediario",
                    forma_pagamento_id=1,
                )
            ],
            [NS(forma_pagamento_id=1, valor_recebido=50, status="parcial")],
            "parcial",
            50,
        ),
        ([NS(valor=200, status="aprovado", forma_pagamento="pix")], [], "pago", 200),
    ],
)
def test_financeiro_reflete_recebimentos_reais_sem_mudar_saldo(
    pagamentos, contas, status, pago
):
    credito = _credito(
        venda=NS(
            id=1,
            numero_venda="VEN-1",
            status="finalizada",
            total=200,
            pagamentos=pagamentos,
            contas_receber=contas,
        )
    )
    resumo = resumo_financeiro_credito(credito)
    assert resumo["status_pagamento"] == status
    assert resumo["valor_pago"] == Decimal(str(pago))
    assert credito.creditos_total == Decimal("4")
