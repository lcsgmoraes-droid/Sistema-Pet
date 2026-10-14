import asyncio
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.routes import sefaz_routes
from app.services.sefaz_service import SefazConsumoIndevidoError
from app.security import permissions_decorator
from app.tenancy.context import clear_current_tenant


TENANT_ID = UUID("11111111-1111-4111-8111-111111111111")


def teardown_function():
    clear_current_tenant()


class _QueryTenant:
    def filter(self, *args):
        return self

    def first(self):
        return SimpleNamespace(cnpj="", uf="SP")


class _DBTenant:
    def query(self, *args):
        return _QueryTenant()


class _QueryDocumentos:
    def __init__(self, docs):
        self.docs = docs

    def filter(self, *args):
        return self

    def count(self):
        return len(self.docs)

    def order_by(self, *args):
        return self

    def offset(self, offset):
        return self

    def limit(self, limite):
        return self

    def all(self):
        return self.docs


class _DBDocumentos:
    def __init__(self, docs):
        self.docs = docs

    def query(self, *args):
        return _QueryDocumentos(self.docs)


def test_mutacoes_sefaz_exigem_permissao_configuracoes_editar(monkeypatch):
    rotas_protegidas = {
        "/sefaz/config",
        "/sefaz/upload-certificado",
        "/sefaz/sync-now",
        "/sefaz/reset-nsu",
        "/sefaz/pular-para-hoje",
        "/sefaz/sync-diagnostico",
    }
    for rota in sefaz_routes.router.routes:
        if rota.path in rotas_protegidas and "POST" in rota.methods:
            assert any(
                dependencia.call is sefaz_routes.can_configure_sefaz
                for dependencia in rota.dependant.dependencies
            ), rota.path

    def _negar(*args, **kwargs):
        raise HTTPException(status_code=403, detail="Sem permissão")

    monkeypatch.setattr(permissions_decorator, "check_permission", _negar)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            sefaz_routes.can_configure_sefaz(
                db=_DBTenant(),
                user_and_tenant=(SimpleNamespace(id=1), TENANT_ID),
            )
        )
    assert exc.value.status_code == 403


@pytest.mark.parametrize(
    ("status", "ultimo_max", "confirmado", "esperado"),
    [
        ("erro_656", "000000000000000", None, None),
        ("ok", "000000000000123", None, "000000000000123"),
        ("erro_656", "000000000000000", "000000000000123", "000000000000123"),
    ],
)
def test_nsu_status_exibe_apenas_max_confirmado(
    monkeypatch, status, ultimo_max, confirmado, esperado
):
    monkeypatch.setattr(
        sefaz_routes.SefazTenantConfigService,
        "merged_config",
        lambda tenant_id, tenant: {
            "ultimo_nsu": "000000000000010",
            "ultimo_sync_status": status,
            "ultimo_sync_max_nsu_retorno": ultimo_max,
            "ultimo_max_nsu_confirmado": confirmado,
        },
    )

    resposta = sefaz_routes.get_nsu_status(
        auth=(SimpleNamespace(id=1), TENANT_ID), db=_DBTenant()
    )
    assert resposta["max_nsu_sefaz"] == esperado
    assert resposta["atualizado"] is bool(esperado)


def test_listagem_documentos_oculta_xml_e_erro_interno():
    campos = {
        campo: None
        for campo in (
            "id",
            "nsu",
            "schema",
            "tipo",
            "chave_acesso",
            "emitente_cnpj",
            "emitente_nome",
            "numero_nota",
            "data_emissao",
            "valor_total",
            "nota_entrada_id",
            "processado_em",
            "created_at",
            "updated_at",
        )
    }
    documento = SimpleNamespace(
        **campos,
        status="erro_processamento",
        raw_xml="<xml>segredo</xml>",
        erro_mensagem="erro SQL com dados privados",
    )
    resposta = sefaz_routes.listar_documentos_distribuidos(
        page=1,
        page_size=20,
        tipos="resNFe,procNFe",
        auth=(SimpleNamespace(id=1), TENANT_ID),
        db=_DBDocumentos([documento]),
    )

    assert resposta["total"] == 1
    assert "raw_xml" not in resposta["items"][0]
    assert "segredo" not in str(resposta)
    assert "erro SQL" not in str(resposta)


def test_listagem_rejeita_tipo_desconhecido():
    with pytest.raises(HTTPException) as exc:
        sefaz_routes.listar_documentos_distribuidos(
            page=1,
            page_size=20,
            tipos="evento,nao-existe",
            auth=(SimpleNamespace(id=1), TENANT_ID),
            db=_DBDocumentos([]),
        )
    assert exc.value.status_code == 422


def test_sync_manual_respeita_proxima_janela_sem_nova_chamada(monkeypatch):
    proxima = datetime.now(timezone.utc) + timedelta(minutes=9)
    monkeypatch.setattr(
        sefaz_routes.SefazTenantConfigService,
        "merged_config",
        lambda tenant_id, tenant: {
            "ultimo_nsu": "000000000000010",
            "_proximo_sync_permitido_at": proxima.isoformat(),
        },
    )

    with pytest.raises(HTTPException) as exc:
        sefaz_routes.sync_now(
            auth=(SimpleNamespace(id=1), TENANT_ID),
            db=_DBTenant(),
            _permission=None,
        )
    assert exc.value.status_code == 429
    assert "Proxima consulta SEFAZ permitida" in exc.value.detail


def _config_payload(**alteracoes):
    dados = {
        "enabled": True,
        "modo": "real",
        "ambiente": "producao",
        "uf": "SP",
        "cnpj": "12345678000199",
        "importacao_automatica": True,
    }
    dados.update(alteracoes)
    return sefaz_routes.SefazConfigUpdateRequest(**dados)


def test_update_config_preserva_cursor_avancado_por_sync(monkeypatch):
    atual = {
        "enabled": True,
        "modo": "real",
        "ambiente": "producao",
        "uf": "SP",
        "cnpj": "12345678000199",
        "ultimo_nsu": "000000000000090",
        "ultimo_sync_at": "2026-10-14T12:00:00+00:00",
    }
    salvos = []
    monkeypatch.setattr(
        sefaz_routes.SefazTenantConfigService,
        "merged_config",
        lambda tenant_id, tenant: dict(atual),
    )
    monkeypatch.setattr(
        sefaz_routes.SefazTenantConfigService,
        "save_config",
        lambda tenant_id, config: salvos.append(dict(config)),
    )
    monkeypatch.setattr(
        sefaz_routes.SefazService,
        "status_configuracao",
        lambda config: SimpleNamespace(
            cert_ok=False, mensagem="Pendente", cert_existe=False, cnpj_configurado=True
        ),
    )

    sefaz_routes.update_config(
        _config_payload(importacao_automatica=False),
        auth=(SimpleNamespace(id=1), TENANT_ID),
        db=_DBTenant(),
        _permission=None,
    )

    assert salvos[0]["ultimo_nsu"] == "000000000000090"
    assert salvos[0]["importacao_automatica"] is False


def test_config_preserva_encaminhamento_quando_outra_tela_salva_sem_campos(monkeypatch):
    atual = {
        "enabled": True,
        "modo": "real",
        "ambiente": "producao",
        "uf": "SP",
        "cnpj": "12345678000199",
        "encaminhamento_email_ativo": True,
        "encaminhamento_email_destino": "contabil@example.com",
        "encaminhamento_ativado_em": "2026-10-14T19:00:00+00:00",
        "encaminhamento_inicio_em": "2026-10-14T03:00:00+00:00",
    }
    salvos = []
    monkeypatch.setattr(
        sefaz_routes.SefazTenantConfigService,
        "merged_config",
        lambda tenant_id, tenant: dict(atual),
    )
    monkeypatch.setattr(
        sefaz_routes.SefazTenantConfigService,
        "save_config",
        lambda tenant_id, config: salvos.append(dict(config)),
    )
    monkeypatch.setattr(sefaz_routes, "is_email_configured", lambda: True)
    monkeypatch.setattr(
        sefaz_routes.SefazService,
        "status_configuracao",
        lambda config: SimpleNamespace(
            cert_ok=True, mensagem="OK", cert_existe=True, cnpj_configurado=True
        ),
    )

    sefaz_routes.update_config(
        _config_payload(),
        auth=(SimpleNamespace(id=1), TENANT_ID),
        db=_DBTenant(),
        _permission=None,
    )

    assert salvos[0]["encaminhamento_email_ativo"] is True
    assert salvos[0]["encaminhamento_email_destino"] == "contabil@example.com"
    assert salvos[0]["encaminhamento_ativado_em"] == atual["encaminhamento_ativado_em"]
    assert salvos[0]["encaminhamento_inicio_em"] == atual["encaminhamento_inicio_em"]


def test_config_bloqueia_ativacao_de_envio_sem_smtp(monkeypatch):
    monkeypatch.setattr(
        sefaz_routes.SefazTenantConfigService,
        "merged_config",
        lambda tenant_id, tenant: {
            "cnpj": "12345678000199", "ambiente": "producao"
        },
    )
    monkeypatch.setattr(sefaz_routes, "is_email_configured", lambda: False)
    monkeypatch.setattr(
        sefaz_routes.SefazTenantConfigService,
        "save_config",
        lambda *args: pytest.fail("Nao deve ativar o envio sem SMTP"),
    )

    with pytest.raises(HTTPException) as exc:
        sefaz_routes.update_config(
            _config_payload(
                encaminhamento_email_ativo=True,
                encaminhamento_email_destino="contabil@example.com",
            ),
            auth=(SimpleNamespace(id=1), TENANT_ID),
            db=_DBTenant(),
            _permission=None,
        )
    assert exc.value.status_code == 422


def test_config_grava_inicio_do_dia_em_sao_paulo(monkeypatch):
    salvos = []
    monkeypatch.setattr(
        sefaz_routes.SefazTenantConfigService,
        "merged_config",
        lambda tenant_id, tenant: {
            "cnpj": "12345678000199", "ambiente": "producao"
        },
    )
    monkeypatch.setattr(
        sefaz_routes.SefazTenantConfigService,
        "save_config",
        lambda tenant_id, config: salvos.append(dict(config)),
    )
    monkeypatch.setattr(
        sefaz_routes.SefazService,
        "status_configuracao",
        lambda config: SimpleNamespace(
            cert_ok=False, mensagem="Pendente", cert_existe=False, cnpj_configurado=True
        ),
    )

    sefaz_routes.update_config(
        _config_payload(encaminhamento_inicio_em=date(2026, 10, 14)),
        auth=(SimpleNamespace(id=1), TENANT_ID),
        db=_DBTenant(),
        _permission=None,
    )

    assert salvos[0]["encaminhamento_inicio_em"] == "2026-10-14T03:00:00+00:00"


@pytest.mark.parametrize(
    "alteracoes", [{"cnpj": "98765432000100"}, {"ambiente": "homologacao"}]
)
def test_update_config_bloqueia_troca_identidade_apos_sync(monkeypatch, alteracoes):
    monkeypatch.setattr(
        sefaz_routes.SefazTenantConfigService,
        "merged_config",
        lambda tenant_id, tenant: {
            "ultimo_nsu": "000000000000090",
            "cnpj": "12345678000199",
            "ambiente": "producao",
        },
    )
    monkeypatch.setattr(
        sefaz_routes.SefazTenantConfigService,
        "save_config",
        lambda *args: pytest.fail("Nao deve sobrescrever checkpoint"),
    )

    with pytest.raises(HTTPException) as exc:
        sefaz_routes.update_config(
            _config_payload(**alteracoes),
            auth=(SimpleNamespace(id=1), TENANT_ID),
            db=_DBTenant(),
            _permission=None,
        )
    assert exc.value.status_code == 409


def test_consulta_por_chave_persiste_bloqueio_656_sem_mexer_no_nsu(monkeypatch):
    atual = {
        "enabled": True,
        "modo": "real",
        "ultimo_nsu": "000000000000090",
        "consultas_chave_timestamps": [],
    }
    chamadas = []
    monkeypatch.setattr(
        sefaz_routes.SefazTenantConfigService,
        "merged_config",
        lambda tenant_id, tenant: dict(atual),
    )
    monkeypatch.setattr(
        sefaz_routes.SefazTenantConfigService,
        "save_config",
        lambda tenant_id, config: atual.update(config),
    )
    monkeypatch.setattr(
        sefaz_routes.SefazService,
        "garantir_pronto_para_consulta_real",
        lambda config: None,
    )

    def _rejeitar(chave, config):
        chamadas.append(chave)
        raise SefazConsumoIndevidoError("656", "0", "0")

    monkeypatch.setattr(sefaz_routes.SefazService, "consultar_nfe_por_chave", _rejeitar)

    for _ in range(2):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                sefaz_routes.consultar_nfe(
                    sefaz_routes.ConsultaNFeRequest(chave_acesso="1" * 44),
                    auth=(SimpleNamespace(id=1), TENANT_ID),
                    db=_DBTenant(),
                )
            )
        assert exc.value.status_code == 429

    assert len(chamadas) == 1
    assert atual["ultimo_nsu"] == "000000000000090"
    assert datetime.fromisoformat(atual["dfe_656_bloqueado_ate"]) > datetime.now(
        timezone.utc
    ) + timedelta(minutes=64)


def test_consulta_por_chave_respeita_cota_por_hora(monkeypatch):
    agora = datetime.now(timezone.utc)
    monkeypatch.setattr(
        sefaz_routes.SefazTenantConfigService,
        "merged_config",
        lambda tenant_id, tenant: {
            "consultas_chave_timestamps": [agora.isoformat()] * 18
        },
    )
    monkeypatch.setattr(
        sefaz_routes.SefazService,
        "garantir_pronto_para_consulta_real",
        lambda config: None,
    )
    monkeypatch.setattr(
        sefaz_routes.SefazService,
        "consultar_nfe_por_chave",
        lambda *args: pytest.fail("Nao deve chamar SEFAZ acima da cota"),
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            sefaz_routes.consultar_nfe(
                sefaz_routes.ConsultaNFeRequest(chave_acesso="1" * 44),
                auth=(SimpleNamespace(id=1), TENANT_ID),
                db=_DBTenant(),
            )
        )
    assert exc.value.status_code == 429
