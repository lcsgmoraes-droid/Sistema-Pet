"""Envio contábil só pode usar XML completo do destinatário correto."""

from datetime import datetime, timedelta, timezone
import json
from uuid import UUID

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.notas_entrada import sefaz_importer  # noqa: F401 - registra modelos relacionados
from app.produtos_compras_models import (
    SefazDocumentoDistribuido,
    SefazXmlEncaminhamento,
)
from app.services import sefaz_xml_forwarding as forwarding
from app.tenancy.context import tenant_context


TENANT = UUID("11111111-1111-4111-8111-111111111111")
CHAVE = "35261012345678000199550010000001231000001234"
CNPJ = "11111111000111"


@pytest.fixture
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    SefazDocumentoDistribuido.__table__.create(engine)
    SefazXmlEncaminhamento.__table__.create(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def _xml(destinatario=CNPJ, chave=CHAVE):
    return (
        '<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe"><NFe>'
        f'<infNFe Id="NFe{chave}"><ide><nNF>123</nNF></ide>'
        "<emit><CNPJ>12345678000199</CNPJ></emit>"
        f"<dest><CNPJ>{destinatario}</CNPJ></dest>"
        "</infNFe></NFe><protNFe><infProt><cStat>100</cStat></infProt></protNFe>"
        "</nfeProc>"
    )


def _config():
    return {
        "encaminhamento_email_ativo": True,
        "encaminhamento_email_destino": "contabil@example.com",
        "encaminhamento_ativado_em": (
            datetime.now(timezone.utc) - timedelta(hours=1)
        ).isoformat(),
        "cnpj": CNPJ,
    }


def _doc(db, nsu, tipo, xml, *, status="importada", chave=CHAVE):
    with tenant_context(TENANT):
        doc = SefazDocumentoDistribuido(
            tenant_id=TENANT,
            nsu=str(nsu).zfill(15),
            schema=f"{tipo}_v4.00.xsd",
            tipo=tipo,
            raw_xml=xml,
            chave_acesso=chave,
            status=status,
            processado_em=datetime.now(timezone.utc),
        )
        db.add(doc)
        db.commit()
        return doc


def _outbox(db):
    with tenant_context(TENANT):
        return db.query(SefazXmlEncaminhamento).all()


def test_envia_somente_xml_completo_do_cnpj_e_uma_vez_por_chave(db, monkeypatch):
    _doc(db, 1, "resNFe", "<resNFe/>")
    _doc(db, 2, "procNFe", _xml("22222222000122"))
    _doc(db, 3, "procNFe", _xml())
    _doc(db, 4, "procNFe", _xml())
    enviados = []
    monkeypatch.setattr(forwarding, "is_email_configured", lambda: True)
    monkeypatch.setattr(forwarding, "resolve_tenant_reply_to", lambda *_: None)
    monkeypatch.setattr(
        forwarding, "send_email", lambda **kwargs: enviados.append(kwargs) or True
    )

    resultado = forwarding.processar_encaminhamentos_sefaz(db, str(TENANT), _config())
    repeticao = forwarding.processar_encaminhamentos_sefaz(db, str(TENANT), _config())

    assert resultado["enviados"] == 1
    assert repeticao["enviados"] == 0
    assert len(enviados) == 1
    assert enviados[0]["to"] == "contabil@example.com"
    assert enviados[0]["attachments"][0]["content"] == _xml()
    assert enviados[0]["simulate_if_unconfigured"] is False
    assert len(_outbox(db)) == 1
    assert _outbox(db)[0].status == "enviado"


def test_falha_smtp_fica_pendente_e_eh_retentada_sem_nova_consulta(db, monkeypatch):
    _doc(db, 1, "procNFe", _xml())
    resultados = iter((False, True))
    monkeypatch.setattr(forwarding, "is_email_configured", lambda: True)
    monkeypatch.setattr(forwarding, "resolve_tenant_reply_to", lambda *_: None)
    monkeypatch.setattr(forwarding, "send_email", lambda **kwargs: next(resultados))
    cfg = _config()

    primeira = forwarding.processar_encaminhamentos_sefaz(db, str(TENANT), cfg)
    assert primeira["falhas"] == 1
    assert _outbox(db)[0].status == "erro"
    assert _outbox(db)[0].tentativas == 1
    assert _outbox(db)[0].proxima_tentativa_em is not None

    with tenant_context(TENANT):
        entrega = _outbox(db)[0]
        entrega.proxima_tentativa_em = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()

    segunda = forwarding.processar_encaminhamentos_sefaz(db, str(TENANT), cfg)
    assert segunda["enviados"] == 1
    assert _outbox(db)[0].status == "enviado"
    assert _outbox(db)[0].tentativas == 2


def test_sem_smtp_nunca_marca_xml_como_enviado(db, monkeypatch):
    _doc(db, 1, "procNFe", _xml())
    monkeypatch.setattr(forwarding, "is_email_configured", lambda: False)
    monkeypatch.setattr(forwarding, "resolve_tenant_reply_to", lambda *_: None)
    monkeypatch.setattr(
        forwarding, "send_email", lambda **kwargs: pytest.fail("SMTP nao configurado")
    )

    forwarding.processar_encaminhamentos_sefaz(db, str(TENANT), _config())

    assert _outbox(db)[0].status == "erro"
    assert _outbox(db)[0].enviado_em is None


def test_xml_capturado_eh_enviado_mesmo_se_importacao_local_falhar(db, monkeypatch):
    _doc(db, 1, "procNFe", _xml(), status="erro_processamento")
    enviados = []
    monkeypatch.setattr(forwarding, "is_email_configured", lambda: True)
    monkeypatch.setattr(forwarding, "resolve_tenant_reply_to", lambda *_: None)
    monkeypatch.setattr(
        forwarding, "send_email", lambda **kwargs: enviados.append(kwargs) or True
    )

    resultado = forwarding.processar_encaminhamentos_sefaz(db, str(TENANT), _config())

    assert resultado["enviados"] == 1
    assert enviados[0]["attachments"][0]["content"] == _xml()


def test_xml_ainda_pendente_de_importacao_usa_data_de_captura(db, monkeypatch):
    _doc(db, 1, "procNFe", _xml(), status="pendente_importacao")
    with tenant_context(TENANT):
        doc = db.query(SefazDocumentoDistribuido).first()
        doc.processado_em = None
        db.commit()
    enviados = []
    monkeypatch.setattr(forwarding, "is_email_configured", lambda: True)
    monkeypatch.setattr(forwarding, "resolve_tenant_reply_to", lambda *_: None)
    monkeypatch.setattr(
        forwarding, "send_email", lambda **kwargs: enviados.append(kwargs) or True
    )

    resultado = forwarding.processar_encaminhamentos_sefaz(db, str(TENANT), _config())

    assert resultado["enviados"] == 1
    assert len(enviados) == 1


def test_data_inicial_permitem_xmls_capturados_antes_da_ativacao(db, monkeypatch):
    _doc(db, 1, "procNFe", _xml())
    enviados = []
    monkeypatch.setattr(forwarding, "is_email_configured", lambda: True)
    monkeypatch.setattr(forwarding, "resolve_tenant_reply_to", lambda *_: None)
    monkeypatch.setattr(
        forwarding, "send_email", lambda **kwargs: enviados.append(kwargs) or True
    )
    cfg = {
        **_config(),
        "encaminhamento_ativado_em": datetime.now(timezone.utc).isoformat(),
        "encaminhamento_inicio_em": (
            datetime.now(timezone.utc) - timedelta(days=1)
        ).isoformat(),
    }

    resultado = forwarding.processar_encaminhamentos_sefaz(db, str(TENANT), cfg)

    assert resultado["enviados"] == 1
    assert len(enviados) == 1


def test_desativacao_durante_lote_interrompe_proximo_email(db, monkeypatch, tmp_path):
    segunda_chave = CHAVE[:-1] + ("5" if CHAVE[-1] != "5" else "6")
    _doc(db, 1, "procNFe", _xml())
    _doc(db, 2, "procNFe", _xml(chave=segunda_chave), chave=segunda_chave)
    cfg = _config()
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(cfg), encoding="utf-8")
    enviados = []

    def enviar(**kwargs):
        enviados.append(kwargs)
        config_path.write_text(
            json.dumps({**cfg, "encaminhamento_email_ativo": False}),
            encoding="utf-8",
        )
        return True

    monkeypatch.setattr(forwarding, "is_email_configured", lambda: True)
    monkeypatch.setattr(forwarding, "resolve_tenant_reply_to", lambda *_: None)
    monkeypatch.setattr(forwarding, "send_email", enviar)

    resultado = forwarding.processar_encaminhamentos_sefaz(
        db, str(TENANT), cfg, config_path=config_path
    )

    assert resultado["enviados"] == 1
    assert len(enviados) == 1
    assert sorted(row.status for row in _outbox(db)) == ["enviado", "pendente"]


def test_desligar_pausa_e_novo_destino_recebe_pendencia_nao_enviada(db, monkeypatch):
    _doc(db, 1, "procNFe", _xml())
    enviados = []
    monkeypatch.setattr(forwarding, "is_email_configured", lambda: True)
    monkeypatch.setattr(forwarding, "resolve_tenant_reply_to", lambda *_: None)
    monkeypatch.setattr(
        forwarding,
        "send_email",
        lambda **kwargs: enviados.append(kwargs["to"]) or False,
    )
    cfg = _config()
    forwarding.processar_encaminhamentos_sefaz(db, str(TENANT), cfg)
    with tenant_context(TENANT):
        entrega = _outbox(db)[0]
        entrega.proxima_tentativa_em = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()

    pausada = forwarding.processar_encaminhamentos_sefaz(
        db, str(TENANT), {**cfg, "encaminhamento_email_ativo": False}
    )
    monkeypatch.setattr(
        forwarding, "send_email", lambda **kwargs: enviados.append(kwargs["to"]) or True
    )
    novo_destino = forwarding.processar_encaminhamentos_sefaz(
        db,
        str(TENANT),
        {
            **cfg,
            "encaminhamento_email_destino": "novo@example.com",
            "encaminhamento_ativado_em": datetime.now(timezone.utc).isoformat(),
        },
    )
    retomada = forwarding.processar_encaminhamentos_sefaz(
        db,
        str(TENANT),
        {**cfg, "encaminhamento_ativado_em": datetime.now(timezone.utc).isoformat()},
    )

    assert pausada["status"] == "desativado"
    assert novo_destino["enviados"] == 1
    assert retomada["enviados"] == 0
    assert _outbox(db)[0].email_destino == "novo@example.com"
    assert enviados == ["contabil@example.com", "novo@example.com"]
