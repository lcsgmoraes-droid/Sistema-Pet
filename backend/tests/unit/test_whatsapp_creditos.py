"""Creditos de WhatsApp: franquia, pacotes avulsos, bloqueio ao esgotar e compras."""

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.api.endpoints import whatsapp as endpoint
from app.db import Base
from app.models import Tenant
from app.ops_tenant_log_models import OpsTenantChangeLog
from app.services import ops_whatsapp_creditos_service as ops
from app.tenancy.context import clear_current_tenant, set_current_tenant
from app.whatsapp import consent_service
from app.whatsapp import consumo_models  # noqa: F401
from app.whatsapp import creditos_service as creditos
from app.whatsapp import ledger_service  # noqa: F401
from app.whatsapp import models_handoff  # noqa: F401  (mapeia WhatsAppHandoff)
from app.whatsapp import sender as sender_module
from app.whatsapp import usage_limits
from app.whatsapp.creditos_models import (
    WhatsAppCreditoMovimento,
    WhatsAppPacote,
)
from app.whatsapp.ledger_models import WhatsAppLedger
from app.whatsapp.models import (
    TenantWhatsAppConfig,
    WhatsAppMessage,
    WhatsAppSession,
)

TENANT = uuid4()
OUTRA_LOJA = uuid4()
ADMIN = SimpleNamespace(id=1, email="ops@corepet.test")


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _now(conexao, _registro):
        conexao.create_function("now", 0, lambda: "2026-10-27 09:00:00")

    nomes = (
        "tenants",
        "tenant_whatsapp_config",
        "whatsapp_creditos_movimentos",
        "whatsapp_pacotes",
        "whatsapp_custos_creditos",
        "whatsapp_compras_pacote",
        "whatsapp_ledger",
        "whatsapp_tarifas",
        "whatsapp_ia_sessions",
        "whatsapp_ia_messages",
        "ops_tenant_change_log",
    )
    Base.metadata.create_all(
        engine, tables=[Base.metadata.tables[nome] for nome in nomes]
    )
    sessao = sessionmaker(bind=engine)()
    sessao.add(Tenant(id=str(TENANT), name="Loja Teste", name_normalized="loja teste"))
    sessao.commit()
    set_current_tenant(TENANT)
    yield sessao
    clear_current_tenant()
    sessao.close()


def _config(db, ativo=True, franquia=10):
    config = TenantWhatsAppConfig(
        tenant_id=TENANT,
        provider="meta_cloud",
        creditos_controle_ativo=ativo,
        creditos_franquia_mensal=franquia,
    )
    db.add(config)
    db.commit()
    return config


def _pacote(db, nome="Pacote 100", creditos=100, preco="49.90"):
    pacote = ops.criar_pacote(
        db, nome=nome, creditos=creditos, preco=preco, admin_email="ops@x"
    )
    db.commit()
    return pacote


# --- saldo ------------------------------------------------------------------------


def test_controle_desligado_nunca_bloqueia(db):
    _config(db, ativo=False, franquia=0)

    situacao = creditos.saldo(db, TENANT)

    assert situacao["nivel"] == "desligado"
    assert creditos.pode_gastar(db, TENANT, 9999) is True
    assert creditos.debitar(db, TENANT, 5) is False  # nem registra consumo
    assert db.query(WhatsAppCreditoMovimento).count() == 0


def test_loja_sem_configuracao_do_whatsapp_nao_e_bloqueada(db):
    assert creditos.pode_gastar(db, TENANT, 5) is True


def test_gasta_a_franquia_primeiro_e_depois_os_pacotes_avulsos(db):
    _config(db, franquia=10)
    ops.ajustar_loja(
        db, str(TENANT), quantidade=20, descricao="Pacote de teste", admin=ADMIN
    )
    db.commit()

    assert creditos.debitar(db, TENANT, 7) is True
    assert creditos.debitar(db, TENANT, 8) is True  # 3 da franquia + 5 do avulso

    situacao = creditos.saldo(db, TENANT)
    assert (situacao["franquia_usada"], situacao["franquia_restante"]) == (10, 0)
    assert situacao["avulso"] == 15 and situacao["disponivel"] == 15


def test_franquia_nao_acumula_de_um_mes_para_o_outro(db):
    _config(db, franquia=10)
    db.add(
        WhatsAppCreditoMovimento(
            tenant_id=TENANT,
            tipo="consumo",
            fonte="franquia",
            quantidade=-10,
            mes="2026-09",  # mes passado: nao conta neste mes
        )
    )
    db.commit()

    assert creditos.saldo(db, TENANT, mes="2026-10")["franquia_restante"] == 10


def test_sem_saldo_bloqueia_e_com_saldo_exato_libera(db):
    _config(db, franquia=3)

    assert creditos.pode_gastar(db, TENANT, 3) is True
    creditos.debitar(db, TENANT, 3)
    assert creditos.saldo(db, TENANT)["nivel"] == "esgotado"
    assert creditos.pode_gastar(db, TENANT, 1) is False
    with pytest.raises(creditos.SemCreditos):
        creditos.exigir_creditos(db, TENANT, 1)


def test_aviso_de_saldo_baixo(db):
    _config(db, franquia=1000)
    creditos.debitar(db, TENANT, 850)

    assert creditos.saldo(db, TENANT)["nivel"] == "baixo"  # restam 150 (menos de 20%)


def test_custos_padrao_e_ajuste_do_ops(db):
    assert creditos.custo_em_creditos(db, "ia") == 2
    assert (
        creditos.custo_em_creditos(db, "sistema") == 0
    )  # aviso de espera nunca bloqueia
    assert creditos.custo_em_creditos(db, "automacao", "modelo", "marketing") == 10
    assert creditos.custo_em_creditos(db, "automacao", "modelo", "utility") == 3

    ops.definir_custo(db, "ia", 5, "ops@x")
    db.commit()

    assert creditos.custo_em_creditos(db, "ia") == 5
    with pytest.raises(ops.CreditosError):
        ops.definir_custo(db, "inventado", 1, "ops@x")


# --- compras ---------------------------------------------------------------------


def test_compra_confirmada_libera_os_creditos_uma_unica_vez(db):
    _config(db, franquia=0)
    pacote = _pacote(db)
    compra = ops.solicitar_compra(
        db, tenant_id=TENANT, pacote_id=pacote.id, solicitante="dono@loja"
    )
    db.commit()
    assert (
        creditos.saldo(db, TENANT)["disponivel"] == 0
    )  # pedido pendente nao libera nada

    ops.confirmar_compra(db, compra.id, admin=ADMIN, observacao="Pix recebido")
    db.commit()

    assert creditos.saldo(db, TENANT)["avulso"] == 100
    with pytest.raises(ops.CreditosError) as erro:
        ops.confirmar_compra(db, compra.id, admin=ADMIN, observacao=None)
    assert erro.value.status_code == 409
    assert creditos.saldo(db, TENANT)["avulso"] == 100
    historico = (
        db.query(OpsTenantChangeLog).filter_by(categoria="creditos_whatsapp").all()
    )
    assert len(historico) == 1 and "+100 créditos" in historico[0].depois


def test_pedido_guarda_a_copia_do_pacote_e_limita_os_pendentes(db):
    pacote = _pacote(db)
    for _ in range(3):
        ops.solicitar_compra(db, tenant_id=TENANT, pacote_id=pacote.id, solicitante="x")
    db.commit()
    pacote.creditos = 999  # o catalogo mudou depois do pedido

    pedido = db.query(ops.WhatsAppCompraPacote).first()
    assert pedido.creditos == 100 and pedido.pacote_nome == "Pacote 100"
    with pytest.raises(ops.CreditosError) as erro:
        ops.solicitar_compra(db, tenant_id=TENANT, pacote_id=pacote.id, solicitante="x")
    assert erro.value.status_code == 409


def test_pacote_desativado_nao_pode_ser_comprado(db):
    pacote = _pacote(db)
    ops.alterar_pacote(db, pacote.id, ativo=False)

    with pytest.raises(ops.CreditosError) as erro:
        ops.solicitar_compra(db, tenant_id=TENANT, pacote_id=pacote.id, solicitante="x")
    assert erro.value.status_code == 404


def test_loja_so_cancela_pedido_pendente_proprio(db):
    pacote = _pacote(db)
    compra = ops.solicitar_compra(
        db, tenant_id=TENANT, pacote_id=pacote.id, solicitante="x"
    )
    db.commit()

    with pytest.raises(ops.CreditosError) as outra:
        ops.cancelar_compra(db, compra.id, tenant_id=OUTRA_LOJA)
    assert outra.value.status_code == 404
    ops.cancelar_compra(db, compra.id, tenant_id=TENANT)
    with pytest.raises(ops.CreditosError) as repetido:
        ops.cancelar_compra(db, compra.id, tenant_id=TENANT)
    assert repetido.value.status_code == 409


def test_pacote_invalido_e_recusado(db):
    with pytest.raises(ops.CreditosError):
        ops.criar_pacote(db, nome="", creditos=10, preco=1, admin_email="x")
    with pytest.raises(ops.CreditosError):
        ops.criar_pacote(db, nome="Zero", creditos=0, preco=1, admin_email="x")
    with pytest.raises(ops.CreditosError):
        ops.criar_pacote(db, nome="Grátis", creditos=10, preco=0, admin_email="x")
    assert db.query(WhatsAppPacote).count() == 0


# --- controle por loja e ajustes (OPS) --------------------------------------------


def test_ops_liga_o_controle_com_historico_do_antes(db):
    _config(db, ativo=False, franquia=0)

    estado = ops.configurar_loja(
        db, str(TENANT), ativo=True, franquia_mensal=500, admin=ADMIN
    )
    db.commit()

    assert estado["controle_ativo"] is True and estado["franquia_mensal"] == 500
    campos = {
        (h.campo, h.antes, h.depois)
        for h in db.query(OpsTenantChangeLog).filter_by(categoria="creditos_whatsapp")
    }
    assert ("controle de créditos", "desligado", "ligado") in campos
    assert ("franquia mensal", "0", "500") in campos


def test_ajuste_negativo_e_exige_motivo(db):
    _config(db)
    with pytest.raises(ops.CreditosError, match="motivo"):
        ops.ajustar_loja(db, str(TENANT), quantidade=5, descricao=" ", admin=ADMIN)
    with pytest.raises(ops.CreditosError):
        ops.ajustar_loja(db, str(TENANT), quantidade=0, descricao="x", admin=ADMIN)

    ops.ajustar_loja(db, str(TENANT), quantidade=30, descricao="Cortesia", admin=ADMIN)
    estado = ops.ajustar_loja(
        db, str(TENANT), quantidade=-10, descricao="Correção", admin=ADMIN
    )

    assert estado["avulso"] == 20


# --- bloqueio nos envios -----------------------------------------------------------


class MetaCloudClient:  # o nome decide o provedor registrado
    def __init__(self):
        self.enviadas = []

    async def send_text_message(self, to, message):
        self.enviadas.append(message)
        return {"messages": [{"id": f"wamid.{len(self.enviadas)}"}]}

    async def send_template_message(self, to, template_name, language_code, parameters):
        self.enviadas.append(template_name)
        return {"messages": [{"id": "wamid.t"}]}


def _sessao(db, status="human"):
    sessao = WhatsAppSession(
        tenant_id=TENANT, phone_number="5511999998888", status=status
    )
    db.add(sessao)
    db.commit()
    return sessao


def test_mensagem_sem_creditos_nao_sai_e_o_motivo_fica_registrado(db, monkeypatch):
    _config(db, franquia=0)
    cliente = MetaCloudClient()
    monkeypatch.setattr(sender_module, "_build_whatsapp_client", lambda *_a: cliente)
    sessao = _sessao(db)

    resultado = asyncio.run(
        sender_module.send_whatsapp_message(
            db, TENANT, sessao.id, "Olá", sent_by_user_id=7
        )
    )

    linha = db.query(WhatsAppLedger).one()
    assert resultado is None and cliente.enviadas == []
    assert (linha.estado, linha.erro_codigo) == ("falhou", "sem_creditos")
    assert db.query(WhatsAppMessage).count() == 0


def test_mensagem_com_creditos_sai_e_consome(db, monkeypatch):
    _config(db, franquia=5)
    cliente = MetaCloudClient()
    monkeypatch.setattr(sender_module, "_build_whatsapp_client", lambda *_a: cliente)
    sessao = _sessao(db)

    resultado = asyncio.run(
        sender_module.send_whatsapp_message(
            db, TENANT, sessao.id, "Olá", sent_by_user_id=7
        )
    )

    assert resultado is not None and cliente.enviadas == ["Olá"]
    situacao = creditos.saldo(db, TENANT)
    assert situacao["franquia_usada"] == 1  # atendente = 1 credito
    movimento = db.query(WhatsAppCreditoMovimento).one()
    assert movimento.referencia == "wamid.1"


def test_aviso_automatico_do_sistema_sai_mesmo_sem_creditos(db, monkeypatch):
    _config(db, franquia=0)
    cliente = MetaCloudClient()
    monkeypatch.setattr(sender_module, "_build_whatsapp_client", lambda *_a: cliente)
    sessao = _sessao(db)

    resultado = asyncio.run(
        sender_module.send_whatsapp_message(
            db,
            TENANT,
            sessao.id,
            "Aguarde um atendente",
            message_type="notificacao_sistema",
        )
    )

    assert resultado is not None and creditos.saldo(db, TENANT)["franquia_usada"] == 0


def test_modelo_sem_creditos_nao_sai(db, monkeypatch):
    _config(db, franquia=5)  # marketing custa 10
    cliente = MetaCloudClient()
    monkeypatch.setattr(sender_module, "_build_whatsapp_client", lambda *_a: cliente)
    monkeypatch.setattr(
        consent_service, "pode_enviar_whatsapp", lambda *_a, **_k: (True, "")
    )
    sessao = _sessao(db, status="bot")

    resultado = asyncio.run(
        sender_module.send_whatsapp_template(
            db, TENANT, sessao.id, "promo", "marketing"
        )
    )

    assert resultado is None and cliente.enviadas == []
    assert db.query(WhatsAppLedger).one().erro_codigo == "sem_creditos"


def test_ia_para_quando_os_creditos_acabam(db):
    _config(db, franquia=1)  # a resposta da IA custa 2
    sessao = _sessao(db, status="bot")

    assert (
        usage_limits.avaliar_limites(db, TENANT, sessao.id) == usage_limits.SEM_CREDITOS
    )


def test_ia_responde_normalmente_quando_o_controle_esta_desligado(db):
    _config(db, ativo=False, franquia=0)
    sessao = _sessao(db, status="bot")

    assert usage_limits.avaliar_limites(db, TENANT, sessao.id) is None


def test_atendente_recebe_erro_claro_sem_creditos(db, monkeypatch):
    _config(db, franquia=0)
    sessao = _sessao(db)
    monkeypatch.setattr(
        endpoint, "atendimento_humano_ativo", lambda *_a: True, raising=False
    )

    with pytest.raises(HTTPException) as erro:
        asyncio.run(
            endpoint.enviar_mensagem_do_atendente(
                request=endpoint.AtendenteMensagem(session_id=sessao.id, message="Oi"),
                user_and_tenant=(SimpleNamespace(id=7), TENANT),
                db=db,
            )
        )

    assert erro.value.status_code == 402 and "créditos" in erro.value.detail


def test_registro_de_consumo_nunca_derruba_o_envio():
    class _DbQuebrado:
        def query(self, *_a):
            raise RuntimeError("banco fora")

        def rollback(self):
            pass

    assert creditos.debitar(_DbQuebrado(), TENANT, 3) is False
    assert (
        creditos.pode_gastar(_DbQuebrado(), TENANT, 3) is True
    )  # na duvida, nao bloqueia


def test_hora_do_mes_e_formato_aaaa_mm():
    assert creditos.mes_de(datetime(2026, 3, 9, tzinfo=UTC)) == "2026-03"
