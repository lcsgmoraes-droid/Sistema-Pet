"""Etapa 0.5 do CRM: segredos e exposicao de dados no WhatsApp."""

import asyncio
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api import whatsapp_orchestrator_internal_routes as interno
from app.routers import whatsapp_config
from app.routes import whatsapp_routes
from app.whatsapp import sender as sender_module
from app.whatsapp.log_safety import mascarar_telefone

RAIZ = Path(__file__).resolve().parents[3]
LOJA_A = "11111111-1111-1111-1111-111111111111"
LOJA_B = "22222222-2222-2222-2222-222222222222"
TOKEN_FORTE = "tok-forte-9f2c7a41b8d04e6f"


@pytest.fixture(autouse=True)
def _ambiente_limpo(monkeypatch):
    monkeypatch.delenv("WHATSAPP_ORCHESTRATOR_INTERNAL_TOKEN", raising=False)
    monkeypatch.delenv("WHATSAPP_ORCHESTRATOR_ALLOWED_TENANTS", raising=False)
    monkeypatch.delenv("WHATSAPP_WEBHOOK_VERIFY_TOKEN", raising=False)
    monkeypatch.setattr(interno, "_is_strict_runtime_environment", lambda: False)


def _codigo(excecao: pytest.ExceptionInfo) -> int:
    return excecao.value.status_code


# ---------------------------------------------------------------------------
# Token interno do canal do orquestrador
# ---------------------------------------------------------------------------


def test_sem_token_configurado_o_canal_fica_indisponivel():
    with pytest.raises(HTTPException) as erro:
        interno._validate_internal_token("qualquer")

    assert _codigo(erro) == 503


def test_token_correto_passa_e_errado_ou_ausente_e_recusado(monkeypatch):
    monkeypatch.setenv("WHATSAPP_ORCHESTRATOR_INTERNAL_TOKEN", TOKEN_FORTE)

    interno._validate_internal_token(TOKEN_FORTE)
    interno._validate_internal_token(f"  {TOKEN_FORTE}  ")
    for invalido in ("errado", "", None):
        with pytest.raises(HTTPException) as erro:
            interno._validate_internal_token(invalido)
        assert _codigo(erro) == 401


def test_token_de_exemplo_e_recusado_em_producao_mas_aceito_em_desenvolvimento(
    monkeypatch,
):
    monkeypatch.setenv(
        "WHATSAPP_ORCHESTRATOR_INTERNAL_TOKEN", "dev_whatsapp_internal_token"
    )

    interno._validate_internal_token("dev_whatsapp_internal_token")  # dev: ok

    monkeypatch.setattr(interno, "_is_strict_runtime_environment", lambda: True)
    with pytest.raises(HTTPException) as erro:
        interno._validate_internal_token("dev_whatsapp_internal_token")
    assert _codigo(erro) == 503


def test_lista_de_lojas_permitidas_restringe_o_token(monkeypatch):
    monkeypatch.setenv("WHATSAPP_ORCHESTRATOR_INTERNAL_TOKEN", TOKEN_FORTE)
    monkeypatch.setenv("WHATSAPP_ORCHESTRATOR_ALLOWED_TENANTS", f" {LOJA_A.upper()} ")

    interno._validate_internal_token(TOKEN_FORTE, LOJA_A)
    with pytest.raises(HTTPException) as erro:
        interno._validate_internal_token(TOKEN_FORTE, LOJA_B)
    assert _codigo(erro) == 403


def test_sem_lista_de_lojas_o_comportamento_anterior_e_mantido(monkeypatch):
    monkeypatch.setenv("WHATSAPP_ORCHESTRATOR_INTERNAL_TOKEN", TOKEN_FORTE)

    interno._validate_internal_token(TOKEN_FORTE, LOJA_B)


def test_comparacao_do_token_e_em_tempo_constante_e_rotas_informam_a_loja():
    fonte = (
        RAIZ / "backend/app/api/whatsapp_orchestrator_internal_routes.py"
    ).read_text(encoding="utf-8")
    assert "secrets.compare_digest" in fonte
    assert "!= expected_token" not in fonte

    dados = (RAIZ / "backend/app/api/whatsapp_data_internal_routes.py").read_text(
        encoding="utf-8"
    )
    assert "_validate_internal_token(x_internal_token)" not in dados
    assert dados.count("_validate_internal_token(x_internal_token, tenant_id)") == 5


# ---------------------------------------------------------------------------
# Valores fixos removidos do repositorio
# ---------------------------------------------------------------------------


def test_fluxo_n8n_nao_tem_loja_nem_token_padrao():
    fluxo = (RAIZ / "automation/n8n/whatsapp_pilot_ingest_workflow.json").read_text(
        encoding="utf-8"
    )
    assert "dev_whatsapp_internal_token" not in fluxo
    assert "7be8dad7-8956-4758-b7bc-855a5259fe2b" not in fluxo
    assert "$env.BACKEND_TENANT_ID" in fluxo and "$env.BACKEND_INTERNAL_TOKEN" in fluxo


def test_compose_de_producao_nao_tem_token_interno_padrao():
    compose = (RAIZ / "docker-compose.prod.yml").read_text(encoding="utf-8")
    assert "dev_whatsapp_internal_token" not in compose
    assert "WHATSAPP_ORCHESTRATOR_INTERNAL_TOKEN" in compose


def test_webhook_antigo_nao_tem_token_fixo_no_codigo():
    fonte = (RAIZ / "backend/app/routes/whatsapp_routes.py").read_text(encoding="utf-8")
    assert "meu_token_secreto" not in fonte


def test_verificacao_do_webhook_antigo_usa_token_do_ambiente(monkeypatch):
    def _verificar(token):
        return asyncio.run(
            whatsapp_routes.webhook(
                hub_mode="subscribe",
                hub_verify_token=token,
                hub_challenge="123",
                db=None,
            )
        )

    with pytest.raises(HTTPException) as erro:
        _verificar("meu_token_secreto")  # nada configurado: sempre recusa
    assert _codigo(erro) == 403

    monkeypatch.setenv("WHATSAPP_WEBHOOK_VERIFY_TOKEN", "segredo-da-loja-123")
    assert _verificar("segredo-da-loja-123") == 123
    with pytest.raises(HTTPException):
        _verificar("outro")


# ---------------------------------------------------------------------------
# Teste de conexao: sem vazar detalhes internos
# ---------------------------------------------------------------------------


class _Consulta:
    def __init__(self, config):
        self.config = config

    def filter(self, *_a, **_k):
        return self

    def first(self):
        return self.config


class _DB:
    def __init__(self, config):
        self.config = config

    def query(self, *_a):
        return _Consulta(self.config)


def _testar_conexao(monkeypatch, cliente_cls):
    monkeypatch.setattr(sender_module, "Dialog360Client", cliente_cls)
    config = SimpleNamespace(api_key="chave", phone_number="5511999998888")
    return asyncio.run(
        whatsapp_config.test_webhook_connection(tenant_id=uuid4(), db=_DB(config))
    )


def test_erro_interno_no_teste_de_conexao_nao_vaza_para_a_tela(monkeypatch):
    class _ClienteQueFalha:
        def __init__(self, api_key):
            pass

        async def send_text_message(self, **_kw):
            raise RuntimeError("Authorization: Bearer segredo-interno-xyz")

    with pytest.raises(HTTPException) as erro:
        _testar_conexao(monkeypatch, _ClienteQueFalha)

    assert _codigo(erro) == 500
    assert "segredo-interno-xyz" not in str(erro.value.detail)


def test_teste_de_conexao_nao_devolve_a_resposta_crua_do_provedor(monkeypatch):
    class _ClienteOk:
        def __init__(self, api_key):
            pass

        async def send_text_message(self, **_kw):
            return {"messages": [{"id": "wamid.interno"}], "token": "x"}

    resposta = _testar_conexao(monkeypatch, _ClienteOk)

    assert resposta == {"status": "success", "message": "Mensagem de teste enviada"}


# ---------------------------------------------------------------------------
# Quem pode configurar o WhatsApp
# ---------------------------------------------------------------------------


def _verificar_permissao(monkeypatch, permissoes_do_usuario):
    def _check(_db, _uid, permissao, _tenant, current_user=None):
        if permissao not in permissoes_do_usuario:
            raise HTTPException(status_code=403, detail=f"negada: {permissao}")

    monkeypatch.setattr(whatsapp_config, "check_permission", _check)
    asyncio.run(
        whatsapp_config._exigir_permissao_configurar_whatsapp(
            db=None, user_and_tenant=(SimpleNamespace(id=7), uuid4())
        )
    )


@pytest.mark.parametrize(
    "permissao", ["ia.whatsapp", "configuracoes.editar", "usuarios.manage"]
)
def test_qualquer_permissao_de_configuracao_libera(monkeypatch, permissao):
    _verificar_permissao(monkeypatch, {permissao})


def test_usuario_sem_permissao_de_configuracao_e_barrado(monkeypatch):
    with pytest.raises(HTTPException) as erro:
        _verificar_permissao(monkeypatch, {"vendas.criar", "clientes.visualizar"})

    assert _codigo(erro) == 403


def test_so_as_rotas_que_alteram_exigem_a_permissao():
    por_rota = {
        (rota.path, tuple(sorted(rota.methods))): [
            d.dependency for d in rota.dependencies
        ]
        for rota in whatsapp_config.router.routes
    }
    exigem = whatsapp_config._exigir_permissao_configurar_whatsapp

    for caminho, metodo in (
        ("/whatsapp/config", "POST"),
        ("/whatsapp/config", "PUT"),
        ("/whatsapp/config", "DELETE"),
        ("/whatsapp/config/test-webhook", "POST"),
    ):
        assert exigem in por_rota[(caminho, (metodo,))], (caminho, metodo)
    assert exigem not in por_rota[("/whatsapp/config", ("GET",))]
    assert exigem not in por_rota[("/whatsapp/config/stats", ("GET",))]


# ---------------------------------------------------------------------------
# Dados pessoais fora dos logs
# ---------------------------------------------------------------------------


def test_mascara_de_telefone_mostra_so_os_quatro_ultimos_digitos():
    assert mascarar_telefone("5511999998888") == "*********8888"
    assert mascarar_telefone("(11) 99999-8888") == "*******8888"
    assert mascarar_telefone("266915104710838@lid") == "***********0838@lid"
    assert mascarar_telefone("123") == "****"
    assert mascarar_telefone(None) == "****"


def test_logs_do_atendimento_nao_gravam_telefone_nem_resultado_de_ferramenta():
    base = RAIZ / "backend/app/whatsapp"
    webhook = (base / "webhook.py").read_text(encoding="utf-8")
    assert "phone={phone}" not in webhook
    assert "executada: {result}" not in (base / "processor_ai_flow.py").read_text(
        encoding="utf-8"
    )
    assert "{tool_result}" not in (base / "ai_service.py").read_text(encoding="utf-8")
