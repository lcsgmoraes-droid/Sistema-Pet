"""API oficial da Meta: cliente, erros traduzidos, vinculo da loja e webhook assinado."""

import asyncio
import hashlib
import hmac
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.routers import whatsapp_meta as rota
from app.whatsapp import (
    meta_cloud,
    models_handoff,  # noqa: F401  (mapeia WhatsAppHandoff)
    webhook,
)
from app.whatsapp import sender as sender_module
from app.whatsapp.meta_cloud import (
    MetaCloudClient,
    MetaCloudError,
    traduzir_erro_da_meta,
)
from app.whatsapp.models import TenantWhatsAppConfig

RAIZ = Path(__file__).resolve().parents[2]
TENANT = uuid4()


# --- erros da Meta viram orientacao -------------------------------------------


@pytest.mark.parametrize(
    "status,codigo,trecho,passo",
    [
        (401, 190, "token de acesso", "token"),
        (403, 10, "permissão", "token"),
        (400, 100, "não encontrou esse ID", "ids"),
        (429, 4, "limitou", None),
    ],
)
def test_erros_da_meta_viram_mensagens_que_a_loja_entende(
    status, codigo, trecho, passo
):
    erro = traduzir_erro_da_meta(status, {"error": {"code": codigo, "message": "x"}})

    assert trecho in erro.mensagem
    assert erro.passo == passo


def test_erro_desconhecido_nao_vaza_o_corpo_da_resposta():
    erro = traduzir_erro_da_meta(
        500, {"error": {"code": 1, "message": "falha interna"}}
    )

    assert "Confira os dados" in erro.mensagem


# --- cliente ------------------------------------------------------------------


class _Resposta:
    def __init__(self, status=200, corpo=None):
        self.status_code = status
        self._corpo = corpo or {}

    def json(self):
        return self._corpo


def _http_falso(monkeypatch, respostas):
    chamadas = []

    class _Cliente:
        def __init__(self, **_k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_a):
            return False

        async def request(self, metodo, url, headers=None, json=None, params=None):
            chamadas.append(
                {
                    "metodo": metodo,
                    "url": url,
                    "headers": headers,
                    "json": json,
                    "params": params,
                }
            )
            return respostas.pop(0)

    monkeypatch.setattr(meta_cloud.httpx, "AsyncClient", _Cliente)
    return chamadas


def test_envio_de_texto_usa_o_numero_da_loja_e_o_token_no_cabecalho(monkeypatch):
    chamadas = _http_falso(
        monkeypatch, [_Resposta(200, {"messages": [{"id": "wamid.1"}]})]
    )
    cliente = MetaCloudClient("TOKEN-SECRETO", "123456", "999")

    resposta = asyncio.run(cliente.send_text_message("5511999998888", "Oi"))

    chamada = chamadas[0]
    assert chamada["url"].endswith("/123456/messages")
    assert chamada["headers"]["Authorization"] == "Bearer TOKEN-SECRETO"
    assert chamada["json"]["messaging_product"] == "whatsapp"
    assert chamada["json"]["to"] == "5511999998888"
    assert chamada["json"]["text"] == {"body": "Oi"}
    # Mesmo formato que o envio ja espera ler (messages[0].id).
    assert resposta["messages"][0]["id"] == "wamid.1"


def test_modelo_aprovado_leva_idioma_e_variaveis(monkeypatch):
    chamadas = _http_falso(monkeypatch, [_Resposta(200, {"messages": [{"id": "w"}]})])

    asyncio.run(
        MetaCloudClient("t", "1").send_template_message(
            "5511", "aniversario", parameters=["Rex"]
        )
    )

    modelo = chamadas[0]["json"]["template"]
    assert modelo["name"] == "aniversario" and modelo["language"]["code"] == "pt_BR"
    assert modelo["components"][0]["parameters"] == [{"type": "text", "text": "Rex"}]


def test_falha_da_meta_vira_erro_traduzido(monkeypatch):
    _http_falso(
        monkeypatch, [_Resposta(401, {"error": {"code": 190, "message": "expired"}})]
    )

    with pytest.raises(MetaCloudError) as erro:
        asyncio.run(MetaCloudClient("velho", "1").consultar_numero())

    assert "token" in erro.value.mensagem and "expired" not in erro.value.mensagem


# --- envio escolhe o cliente da Meta -----------------------------------------


class _DB:
    def __init__(self, config):
        self.config = config

    def query(self, *_a):
        return self

    def filter(self, *_a, **_k):
        return self

    def first(self):
        return self.config


def _config(**campos):
    base = TenantWhatsAppConfig(tenant_id=TENANT, provider="meta_cloud")
    for nome, valor in campos.items():
        setattr(base, nome, valor)
    return base


def test_provedor_meta_monta_o_cliente_oficial_com_o_token_proprio():
    config = _config(meta_phone_number_id="777", meta_waba_id="888")
    config.meta_access_token = "token-meta"
    config.api_key = "chave-do-360dialog"  # nao pode ser usada pelo provedor Meta

    cliente = sender_module._build_whatsapp_client(_DB(config), str(TENANT))

    assert isinstance(cliente, MetaCloudClient)
    assert cliente.access_token == "token-meta" and cliente.phone_number_id == "777"


def test_provedor_meta_sem_token_nao_envia():
    config = _config(meta_phone_number_id="777")

    assert sender_module._build_whatsapp_client(_DB(config), str(TENANT)) is None


# --- webhook: a Meta assina com o segredo do app ------------------------------


def _assinar(corpo: bytes, segredo: str) -> str:
    return "sha256=" + hmac.new(segredo.encode(), corpo, hashlib.sha256).hexdigest()


class _Requisicao:
    def __init__(self, corpo: bytes, cabecalhos: dict):
        self._corpo = corpo
        self.headers = cabecalhos

    async def body(self):
        return self._corpo

    async def json(self):
        return {"entry": []}


def _receber(monkeypatch, config, corpo, cabecalhos):
    registrado = []
    monkeypatch.setattr(
        webhook, "_registrar_webhook_recebido", lambda *_a: registrado.append(True)
    )

    async def _processar(**_k):
        return 0

    monkeypatch.setattr(webhook, "process_webhook_payload", _processar)
    monkeypatch.setattr(webhook, "whatsapp_tenant_context", lambda _t: _Contexto())
    resultado = asyncio.run(
        webhook.receive_webhook(
            str(TENANT), _Requisicao(corpo, cabecalhos), SimpleNamespace(), _DB(config)
        )
    )
    return resultado, registrado


class _Contexto:
    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return False


def test_post_da_meta_exige_assinatura_do_segredo_do_app(monkeypatch):
    config = _config()
    config.webhook_secret = "token-de-verificacao"
    config.meta_app_secret = "segredo-do-app"
    corpo = b'{"entry": []}'

    resultado, registrado = _receber(
        monkeypatch,
        config,
        corpo,
        {"X-Hub-Signature-256": _assinar(corpo, "segredo-do-app")},
    )

    assert resultado["status"] == "received" and registrado == [True]


def test_token_de_verificacao_nao_autentica_o_post_da_meta(monkeypatch):
    config = _config()
    config.webhook_secret = "token-de-verificacao"
    config.meta_app_secret = "segredo-do-app"
    corpo = b'{"entry": []}'

    for cabecalhos in (
        {webhook.WHATSAPP_WEBHOOK_TOKEN_HEADER: "token-de-verificacao"},
        {"X-Hub-Signature-256": _assinar(corpo, "token-de-verificacao")},
        {},
    ):
        with pytest.raises(HTTPException) as erro:
            _receber(monkeypatch, config, corpo, cabecalhos)
        assert erro.value.status_code == 403


def test_meta_sem_segredo_do_app_fica_bloqueada(monkeypatch):
    config = _config()
    config.webhook_secret = "token-de-verificacao"

    with pytest.raises(HTTPException) as erro:
        _receber(monkeypatch, config, b"{}", {})

    assert erro.value.status_code == 503


# --- estado e regras do vinculo -----------------------------------------------


def test_estado_nunca_devolve_token_nem_segredo():
    config = _config(meta_phone_number_id="777", meta_waba_id="888")
    config.meta_access_token = "TOKEN-SECRETO-XYZ"
    config.meta_app_secret = "SEGREDO-APP-XYZ"

    estado = rota.montar_estado(config, TENANT)

    texto = str(estado)
    assert "TOKEN-SECRETO-XYZ" not in texto and "SEGREDO-APP-XYZ" not in texto
    assert (
        estado["credenciais"]["tem_token"] and estado["credenciais"]["tem_app_secret"]
    )
    assert estado["webhook_url"].endswith(f"/webhook/whatsapp/{TENANT}")
    assert estado["ativo"] is True


def test_nao_ativa_sem_teste_bem_sucedido_nem_sem_segredo_do_app():
    config = _config()
    config.meta_status = "erro"
    db = _DB(config)
    usuario = (SimpleNamespace(id=1), TENANT)

    with pytest.raises(HTTPException) as sem_teste:
        asyncio.run(rota.ativar(db=db, user_and_tenant=usuario))
    assert sem_teste.value.status_code == 409

    config.meta_status = "conectado"
    with pytest.raises(HTTPException) as sem_segredo:
        asyncio.run(rota.ativar(db=db, user_and_tenant=usuario))
    assert "App Secret" in sem_segredo.value.detail


def test_salvar_credenciais_nao_troca_o_provedor_em_uso():
    fonte = (RAIZ / "app/routers/whatsapp_meta.py").read_text(encoding="utf-8")
    trecho = fonte.split("async def salvar_credenciais")[1].split("@router.post")[0]

    assert "config.provider =" not in trecho  # so a rota "ativar" troca o provedor


def test_rotas_exigem_modulo_crm_e_permissao_de_configurar():
    fonte = (RAIZ / "app/routers/whatsapp_meta.py").read_text(encoding="utf-8")
    montagem = (RAIZ / "app/main_routers.py").read_text(encoding="utf-8")

    assert 'require_permission_dependency("crm.configurar")' in fonte
    assert 'whatsapp_meta_router, dependencies=_module_dependencies("crm")' in montagem
