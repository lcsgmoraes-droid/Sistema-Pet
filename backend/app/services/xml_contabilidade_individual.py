"""Captura durável de notas e eventos para entrega individual e lotes mensais.

O provedor informa os eventos por nota. O cursor consulta inclusive notas antigas
em rodízio, e cada comprovante validado ganha uma identidade persistente. Ativar
o envio não reenvia o histórico: o instante oficial do registro decide a entrega.
"""

from datetime import date, datetime, timedelta
import logging

from sqlalchemy import and_, func, or_

from app.nfe_cache_models import BlingNotaFiscalCache
from app.services.xml_contabilidade_common import (
    BRASILIA,
    NS,
    STATUS_VALIDOS,
    XmlContabilidadeError,
    _tenant,
    _utc,
)
from app.services import xml_contabilidade_documentos as documentos
from app.vendas_models import Venda
from app.xml_contabilidade_models import (
    XmlContabilidadeConfig,
    XmlContabilidadeEnvio,
    XmlContabilidadeEvento,
    XmlContabilidadeMonitor,
)

logger = logging.getLogger(__name__)
LIMITE_CONSULTAS_CICLO = 10
# Consulta completa por período é obrigatória: ultrapassar o limite bloqueia,
# em vez de afirmar que um lote incompleto contém todos os eventos.
MAX_MONITOR_DOCUMENTOS = 10000


def _config(db, tenant_id):
    return (
        db.query(XmlContabilidadeConfig)
        .filter(XmlContabilidadeConfig.tenant_id == _tenant(tenant_id))
        .first()
    )


def _referencias(db, tenant_id):
    vendas = (
        db.query(Venda.id, Venda.nfe_provider, Venda.nfe_bling_id)
        .filter(
            Venda.tenant_id == _tenant(tenant_id),
            func.lower(Venda.nfe_status).in_(STATUS_VALIDOS),
            Venda.nfe_data_emissao.isnot(None),
            or_(
                and_(Venda.nfe_provider == "intnfe", Venda.nfe_ambiente == 1),
                and_(
                    Venda.nfe_bling_id > 0,
                    or_(Venda.nfe_provider.is_(None), Venda.nfe_provider == "bling"),
                ),
            ),
        )
        .order_by(Venda.id)
        .limit(MAX_MONITOR_DOCUMENTOS + 1)
        .all()
    )
    caches = (
        db.query(BlingNotaFiscalCache.bling_id)
        .filter(
            BlingNotaFiscalCache.tenant_id == _tenant(tenant_id),
            func.lower(BlingNotaFiscalCache.status).in_(STATUS_VALIDOS),
            BlingNotaFiscalCache.data_emissao.isnot(None),
            or_(
                BlingNotaFiscalCache.provider.is_(None),
                BlingNotaFiscalCache.provider == "bling",
            ),
        )
        .order_by(BlingNotaFiscalCache.id)
        .limit(MAX_MONITOR_DOCUMENTOS + 1)
        .all()
    )
    refs = {
        ("intnfe", str(row[0])) if row[1] == "intnfe" else ("bling", str(row[2]))
        for row in vendas
    }
    refs.update(("bling", str(row[0])) for row in caches if str(row[0]).isdigit())
    if (
        len(refs) > MAX_MONITOR_DOCUMENTOS
        or len(vendas) > MAX_MONITOR_DOCUMENTOS
        or len(caches) > MAX_MONITOR_DOCUMENTOS
    ):
        raise XmlContabilidadeError(
            "O histórico excede o limite de consulta de eventos fiscais. Contate o suporte; nenhum lote parcial foi preparado.",
            409,
        )
    return sorted(refs)


def priorizar_documento(db, tenant_id, provider, documento_id, agora):
    if provider not in {"intnfe", "bling"} or not str(documento_id).isdigit():
        return None
    monitor = (
        db.query(XmlContabilidadeMonitor)
        .filter(
            XmlContabilidadeMonitor.tenant_id == _tenant(tenant_id),
            XmlContabilidadeMonitor.provider == provider,
            XmlContabilidadeMonitor.documento_id == str(documento_id),
        )
        .first()
    )
    if not monitor:
        monitor = XmlContabilidadeMonitor(
            tenant_id=_tenant(tenant_id),
            provider=provider,
            documento_id=str(documento_id),
            proxima_consulta_em=agora,
        )
        db.add(monitor)
    else:
        monitor.proxima_consulta_em = agora
    return monitor


def _enfileirar(db, tenant_id, config, doc, key, dia, status, agora):
    existente = (
        db.query(XmlContabilidadeEnvio)
        .filter(
            XmlContabilidadeEnvio.tenant_id == _tenant(tenant_id),
            XmlContabilidadeEnvio.idempotency_key == key,
        )
        .first()
    )
    if existente:
        return existente
    envio = XmlContabilidadeEnvio(
        tenant_id=_tenant(tenant_id),
        origem="automatico",
        status="pendente",
        email_destino=config.email_contador,
        data_inicio=dia,
        data_fim=dia,
        provider=doc.provider,
        documento_id=doc.documento_id,
        documento_status=status,
        proxima_tentativa_em=agora,
        idempotency_key=key,
    )
    db.add(envio)
    db.flush()
    return envio


def _ativo(config):
    return bool(
        config
        and config.envio_automatico
        and config.email_contador
        and config.envio_automatico_desde
    )


def enfileirar_nota(db, tenant_id, provider, documento_id, agora):
    """Hook sem rede/commit; evento posterior é capturado no worker."""
    config = _config(db, tenant_id)
    if not _ativo(config):
        return None
    doc = documentos._documento(db, tenant_id, provider, documento_id)
    if not doc:
        return None
    priorizar_documento(db, tenant_id, provider, documento_id, agora)
    # A coluna legada não informa o fuso. O instante oficial do XML decide o
    # corte; sem XML em memória o worker fará a consulta já priorizada.
    if doc.venda is None or not doc.venda.nfe_xml:
        return None
    xml = documentos._xml_bytes(doc.venda.nfe_xml)
    validacao = documentos.validar_xml_saida(xml, doc.chave, doc.modelo)
    if validacao is None or validacao[0].findtext(
        ".//n:infNFe/n:emit/n:CNPJ", namespaces=NS
    ) != documentos._cnpj_empresa(db, tenant_id):
        return None
    emissao = _emissao_oficial(validacao[0])
    if emissao < _utc(config.envio_automatico_desde):
        return None
    # A chave fiscal independe da origem do cache: importar a mesma nota não
    # gera outro e-mail. Emitente/produção já foram confirmados no XML.
    if not doc.chave:
        return None
    return _enfileirar(
        db,
        tenant_id,
        config,
        doc,
        f"nota:{doc.chave}",
        emissao.astimezone(BRASILIA).date(),
        "nota",
        agora,
    )


def _emissao_oficial(root):
    raw = root.findtext(".//n:infNFe/n:ide/n:dhEmi", namespaces=NS) or root.findtext(
        ".//n:infNFe/n:ide/n:dEmi", namespaces=NS
    )
    value = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    return _utc(value.replace(tzinfo=BRASILIA) if value.tzinfo is None else value)


def consultar_documento(db, tenant_id, provider, documento_id, agora, config=None):
    """Coleta oficial validada, registra eventos e agenda somente fatos novos."""
    doc = documentos._documento(db, tenant_id, provider, documento_id)
    if not doc:
        return [], []
    arquivos, notas = documentos._coletar_arquivos(
        db, tenant_id, [doc], date.min, date.max
    )
    if not notas:
        return [], []
    por_nome = dict(arquivos)
    config = config if config is not None else _config(db, tenant_id)
    ativo = _ativo(config)
    nota = notas[0]
    desde = _utc(config.envio_automatico_desde) if ativo else None
    if ativo:
        # A coluna legada pode guardar UTC sem fuso; o XML decide o instante.
        validacao = documentos.validar_xml_saida(
            por_nome[f"{doc.chave}-nfe.xml"], doc.chave, doc.modelo
        )
        emissao = _emissao_oficial(validacao[0])
        if emissao >= desde:
            _enfileirar(
                db,
                tenant_id,
                config,
                doc,
                f"nota:{doc.chave}",
                emissao.astimezone(BRASILIA).date(),
                "nota",
                agora,
            )
    for evento in nota.get("eventos", []):
        identidade = evento["identidade"]
        protocolo = evento["protocolo"]
        registrado = _utc(datetime.fromisoformat(evento["data_hora_registro"]))
        nome = evento["nome_arquivo"]
        xml = por_nome.get(nome)
        if xml is None:
            raise XmlContabilidadeError(
                "Um evento fiscal não possui XML oficial preservado. Nenhum lote parcial foi preparado.",
                409,
            )
        existente = (
            db.query(XmlContabilidadeEvento)
            .filter(
                XmlContabilidadeEvento.tenant_id == _tenant(tenant_id),
                XmlContabilidadeEvento.identidade == identidade,
                XmlContabilidadeEvento.protocolo == protocolo,
            )
            .first()
        )
        if not existente:
            db.add(
                XmlContabilidadeEvento(
                    tenant_id=_tenant(tenant_id),
                    provider=provider,
                    documento_id=str(documento_id),
                    chave=doc.chave,
                    identidade=identidade,
                    tipo=evento["tipo"],
                    sequencia=evento["sequencia"],
                    protocolo=protocolo,
                    registrado_em=registrado,
                    nome_arquivo=nome,
                    xml=xml,
                )
            )
            db.flush()
        if ativo and registrado >= desde:
            _enfileirar(
                db,
                tenant_id,
                config,
                doc,
                f"evento:{identidade}:{protocolo}",
                registrado.astimezone(BRASILIA).date(),
                "evento",
                agora,
            )
    return arquivos, notas


def capturar_novos_eventos(db, tenant_id, agora, limite=LIMITE_CONSULTAS_CICLO):
    config = _config(db, tenant_id)
    if not _ativo(config):
        return 0
    from app.services.xml_contabilidade_reconciliation import reconciliar_pendentes

    reconciliar_pendentes(db, tenant_id, config.envio_automatico_desde)
    existentes = {
        (row[0], row[1])
        for row in db.query(
            XmlContabilidadeMonitor.provider, XmlContabilidadeMonitor.documento_id
        )
        .filter(XmlContabilidadeMonitor.tenant_id == _tenant(tenant_id))
        .all()
    }
    for provider, documento_id in _referencias(db, tenant_id):
        if (provider, documento_id) not in existentes:
            priorizar_documento(db, tenant_id, provider, documento_id, agora)
    db.commit()
    monitores = (
        db.query(XmlContabilidadeMonitor)
        .filter(
            XmlContabilidadeMonitor.tenant_id == _tenant(tenant_id),
            XmlContabilidadeMonitor.proxima_consulta_em <= agora,
        )
        .order_by(
            XmlContabilidadeMonitor.proxima_consulta_em, XmlContabilidadeMonitor.id
        )
        .limit(min(max(limite, 1), 50))
        .all()
    )
    total = 0
    for monitor in monitores:
        monitor_id = monitor.id
        try:
            consultar_documento(
                db, tenant_id, monitor.provider, monitor.documento_id, agora, config
            )
            monitor.ultima_consulta_em = agora
            monitor.proxima_consulta_em = agora + timedelta(minutes=10)
            db.commit()
            total += 1
        except Exception as exc:
            db.rollback()
            atual = (
                db.query(XmlContabilidadeMonitor)
                .filter(
                    XmlContabilidadeMonitor.tenant_id == _tenant(tenant_id),
                    XmlContabilidadeMonitor.id == monitor_id,
                )
                .first()
            )
            if atual:
                atual.proxima_consulta_em = agora + timedelta(minutes=5)
                db.commit()
            logger.warning(
                "Falha ao consultar eventos contábeis monitor=%s tipo=%s",
                monitor_id,
                type(exc).__name__,
            )
    return total


def coletar_eventos_periodo(db, tenant_id, inicio, fim):
    """Eventos registrados no período, inclusive de notas emitidas anteriormente."""
    from app.services.xml_contabilidade_service import _agora

    arquivos, notas = {}, []
    config = _config(db, tenant_id)
    for provider, documento_id in _referencias(db, tenant_id):
        try:
            coletados, documentos_coletados = consultar_documento(
                db, tenant_id, provider, documento_id, _agora(), config
            )
            for nota in documentos_coletados:
                eventos = [
                    e
                    for e in nota.get("eventos", [])
                    if inicio.isoformat() <= e["data_registro"] <= fim.isoformat()
                ]
                if not eventos:
                    continue
                por_nome = dict(coletados)
                for evento in eventos:
                    nome = evento["nome_arquivo"]
                    arquivos[nome] = por_nome[nome]
                notas.append(
                    {
                        **nota,
                        "eventos": eventos,
                        "eventos_incluidos": len(eventos),
                        "somente_eventos_periodo": True,
                    }
                )
            db.commit()
        except XmlContabilidadeError:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            raise XmlContabilidadeError(
                "Não foi possível confirmar todos os eventos do período. Nenhum lote parcial foi preparado.",
                409,
            ) from None
    return list(arquivos.items()), notas


def preparar_anexos_individual(db, tenant_id, envio):
    """Um único XML oficial por envio; os eventos têm identidade própria."""
    key = envio.idempotency_key or ""
    if key.startswith("evento:"):
        _, identidade, protocolo = key.split(":", 2)
        evento = (
            db.query(XmlContabilidadeEvento)
            .filter(
                XmlContabilidadeEvento.tenant_id == _tenant(tenant_id),
                XmlContabilidadeEvento.identidade == identidade,
                XmlContabilidadeEvento.protocolo == protocolo,
            )
            .first()
        )
        if not evento:
            raise XmlContabilidadeError(
                "O comprovante do evento fiscal não está disponível para envio.", 409
            )
        return (
            [
                {
                    "filename": evento.nome_arquivo,
                    "content": evento.xml,
                    "mime_subtype": "xml",
                }
            ],
            evento.nome_arquivo,
            1,
        )
    if not key.startswith("nota:"):
        raise XmlContabilidadeError(
            "Este envio individual antigo não pode ser retomado. Prepare um lote manual.",
            409,
        )
    doc = documentos._documento(db, tenant_id, envio.provider, envio.documento_id)
    if not doc:
        raise XmlContabilidadeError(
            "A nota fiscal não está disponível para envio.", 409
        )
    # No legado Bling o cache pode não ter chave. A consulta oficial preenche
    # doc.chave e só depois permite confirmar a identidade persistida na fila.
    xml, _ = documentos._obter_xml(db, tenant_id, doc)
    if key != f"nota:{doc.chave}":
        raise XmlContabilidadeError(
            "A nota fiscal não corresponde à identidade deste envio.", 409
        )
    validacao = documentos.validar_xml_saida(xml, doc.chave, doc.modelo)
    if validacao is None or validacao[0].findtext(
        ".//n:infNFe/n:emit/n:CNPJ", namespaces=NS
    ) != documentos._cnpj_empresa(db, tenant_id):
        raise XmlContabilidadeError(
            "O documento não é uma nota de saída em produção desta empresa.", 409
        )
    nome = f"{doc.chave}-nfe.xml"
    return [{"filename": nome, "content": xml, "mime_subtype": "xml"}], nome, 1
