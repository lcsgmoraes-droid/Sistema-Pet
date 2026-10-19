"""Coleta documentos oficiais de saída, valida a empresa e produz ZIP íntegro."""

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from io import BytesIO
import json
import re
from zipfile import ZIP_DEFLATED, ZipFile

from defusedxml import ElementTree as ET
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import noload

from app.nfe_cache_models import BlingNotaFiscalCache
from app.vendas_models import Venda
from app.services.xml_contabilidade_common import (
    BRASILIA,
    MAX_DOCUMENTOS,
    MAX_XML_BYTES,
    MAX_TOTAL_BYTES,
    MAX_ZIP_BYTES,
    NS,
    STATUS_VALIDOS,
    XmlContabilidadeError,
    _tenant,
    _status,
    _validar_periodo,
)


@dataclass
class Documento:
    provider: str
    documento_id: str
    chave: str
    modelo: int
    status: str
    data_emissao: datetime
    venda: object = None
    cache: object = None


def _documento(db, tenant_id, provider, documento_id):
    if provider == "intnfe":
        if not str(documento_id).isdigit():
            return None
        venda = (
            db.query(Venda)
            .options(noload("*"))
            .filter(
                Venda.tenant_id == _tenant(tenant_id),
                Venda.id == int(documento_id),
                Venda.nfe_provider == "intnfe",
            )
            .first()
        )
        if (
            not venda
            or _status(venda.nfe_status) not in STATUS_VALIDOS
            or venda.nfe_ambiente != 1
            or not venda.nfe_data_emissao
        ):
            return None
        return Documento(
            "intnfe",
            str(venda.id),
            str(venda.nfe_chave or ""),
            int(venda.nfe_modelo or 0),
            _status(venda.nfe_status),
            venda.nfe_data_emissao,
            venda=venda,
        )
    if provider != "bling" or not str(documento_id).isdigit() or int(documento_id) <= 0:
        return None
    cache = (
        db.query(BlingNotaFiscalCache)
        .filter(
            BlingNotaFiscalCache.tenant_id == _tenant(tenant_id),
            BlingNotaFiscalCache.bling_id == str(documento_id),
            or_(
                BlingNotaFiscalCache.provider.is_(None),
                BlingNotaFiscalCache.provider == "bling",
            ),
        )
        .order_by(BlingNotaFiscalCache.id.desc())
        .first()
    )
    if (
        not cache
        or _status(cache.status) not in STATUS_VALIDOS
        or not cache.data_emissao
    ):
        return None
    return Documento(
        "bling",
        str(cache.bling_id),
        str(cache.chave or ""),
        int(cache.modelo),
        _status(cache.status),
        cache.data_emissao,
        cache=cache,
    )


def _listar_documentos(db, tenant_id, data_inicio, data_fim):
    # As colunas legadas não preservam o fuso; ampliar a busca evita perder uma
    # emissão na virada do dia. O dhEmi do XML aplica o filtro definitivo.
    inicio = datetime.combine(data_inicio - timedelta(days=1), time.min)
    fim = datetime.combine(data_fim + timedelta(days=2), time.min)
    vendas = (
        db.query(Venda)
        .options(noload("*"))
        .filter(
            Venda.tenant_id == _tenant(tenant_id),
            or_(
                and_(Venda.nfe_provider == "intnfe", Venda.nfe_ambiente == 1),
                and_(
                    Venda.nfe_bling_id > 0,
                    or_(Venda.nfe_provider.is_(None), Venda.nfe_provider == "bling"),
                ),
            ),
            func.lower(Venda.nfe_status).in_(STATUS_VALIDOS),
            Venda.nfe_data_emissao >= inicio,
            Venda.nfe_data_emissao < fim,
        )
        .order_by(Venda.nfe_data_emissao, Venda.id)
        .limit(MAX_DOCUMENTOS + 1)
        .all()
    )
    notas = (
        db.query(BlingNotaFiscalCache)
        .filter(
            BlingNotaFiscalCache.tenant_id == _tenant(tenant_id),
            or_(
                BlingNotaFiscalCache.provider.is_(None),
                BlingNotaFiscalCache.provider == "bling",
            ),
            func.lower(BlingNotaFiscalCache.status).in_(STATUS_VALIDOS),
            BlingNotaFiscalCache.data_emissao >= inicio,
            BlingNotaFiscalCache.data_emissao < fim,
        )
        .order_by(BlingNotaFiscalCache.data_emissao, BlingNotaFiscalCache.id)
        .limit(MAX_DOCUMENTOS + 1)
        .all()
    )
    docs = [
        Documento(
            "intnfe" if v.nfe_provider == "intnfe" else "bling",
            str(v.id if v.nfe_provider == "intnfe" else v.nfe_bling_id),
            str(v.nfe_chave or ""),
            int(v.nfe_modelo or 0),
            _status(v.nfe_status),
            v.nfe_data_emissao,
            venda=v,
        )
        for v in vendas
    ]
    docs.extend(
        Documento(
            "bling",
            str(n.bling_id),
            str(n.chave or ""),
            int(n.modelo),
            _status(n.status),
            n.data_emissao,
            cache=n,
        )
        for n in notas
        if str(n.bling_id).isdigit() and int(n.bling_id) > 0
    )
    if len(docs) > MAX_DOCUMENTOS:
        raise XmlContabilidadeError(
            f"O período excede {MAX_DOCUMENTOS} notas. Divida-o em períodos menores."
        )
    return docs


def _xml_bytes(value):
    if isinstance(value, str):
        value = value.encode("utf-8")
    if not isinstance(value, bytes) or not value.strip():
        raise XmlContabilidadeError(
            "Um XML não está disponível. Nenhum arquivo parcial foi gerado.", 409
        )
    if len(value) > MAX_XML_BYTES:
        raise XmlContabilidadeError(
            "Um XML excede o tamanho permitido. Divida o período."
        )
    return value


def _obter_xml(db, tenant_id, doc):
    detalhe = {}
    if doc.venda is not None and doc.venda.nfe_xml:
        return _xml_bytes(doc.venda.nfe_xml), detalhe
    if doc.provider == "intnfe":
        # download_document faz commit no cache e não deve interferir no claim
        # da fila. Usa-se o mesmo cliente/autenticação, sem commit intermediário.
        from app.intnfe.client import IntNFeClient
        from app.intnfe.emission import _access_token, _connection

        api = IntNFeClient()
        try:
            connection = _connection(db, tenant_id, require_enabled=False)
            token = _access_token(api, connection, doc.venda.nfe_ambiente)
            xml = _xml_bytes(
                api.document_xml(
                    token, doc.venda.nfe_tipo, doc.venda.nfe_correlation_id
                )
            )
        finally:
            api.close()
        doc.venda.nfe_xml = xml.decode("utf-8-sig")
        return xml, detalhe
    from app.nfe.documentos import obter_nota_documento, obter_xml_documento

    detalhe, modelo, _ = obter_nota_documento(db, tenant_id, int(doc.documento_id))
    if doc.modelo != modelo:
        raise XmlContabilidadeError(
            "O modelo do documento não corresponde ao cache fiscal.", 409
        )
    doc.chave = doc.chave or str(detalhe.get("chaveAcesso") or "")
    return _xml_bytes(obter_xml_documento(detalhe, modelo)), detalhe


def validar_xml_saida(xml, chave, modelo):
    """Retorna (árvore, data civil) ou None para homologação/notas de entrada."""
    try:
        root = ET.fromstring(_xml_bytes(xml))
    except XmlContabilidadeError:
        raise
    except Exception:
        raise XmlContabilidadeError(
            "Um documento retornou XML inválido. Nenhum arquivo parcial foi gerado.",
            409,
        ) from None
    info = root.find(".//n:infNFe", NS)
    if (
        info is None
        or not re.fullmatch(r"\d{44}", chave)
        or info.get("Id") != f"NFe{chave}"
        or info.findtext("n:ide/n:mod", namespaces=NS) != str(modelo)
    ):
        raise XmlContabilidadeError(
            "Um XML não corresponde à chave/modelo da nota solicitada.", 409
        )
    if (
        info.findtext("n:ide/n:tpAmb", namespaces=NS) != "1"
        or info.findtext("n:ide/n:tpNF", namespaces=NS) != "1"
    ):
        return None
    prot = root.find(".//n:protNFe/n:infProt", NS)
    if (
        prot is None
        or prot.findtext("n:cStat", namespaces=NS) not in {"100", "150"}
        or prot.findtext("n:chNFe", namespaces=NS) != chave
    ):
        raise XmlContabilidadeError(
            "Uma nota não possui XML com protocolo de autorização válido.", 409
        )
    raw_date = info.findtext("n:ide/n:dhEmi", namespaces=NS) or info.findtext(
        "n:ide/n:dEmi", namespaces=NS
    )
    try:
        dt = datetime.fromisoformat(str(raw_date).replace("Z", "+00:00"))
        dt = dt.replace(tzinfo=BRASILIA) if dt.tzinfo is None else dt
    except (TypeError, ValueError):
        raise XmlContabilidadeError(
            "O XML de uma nota não possui data de emissão válida.", 409
        ) from None
    return root, dt.astimezone(BRASILIA).date()


def _eventos_xml(root, detalhe, chave):
    # Os eventos embutidos já estão no XML original, byte a byte. Reserializar
    # subárvores alteraria namespaces e poderia invalidar a assinatura fiscal.
    embutidos = root.findall(".//n:procEventoNFe", NS)
    candidatos = []
    # Apenas campos oficiais explícitos; nunca segue URLs arbitrárias do payload.
    from app.nfe.documentos import baixar_link_documento

    for key in ("xmlCancelamento", "xmlCartaCorrecao", "xmlEvento"):
        value = detalhe.get(key)
        if value:
            candidatos.append(
                value
                if str(value).lstrip().startswith("<")
                else baixar_link_documento(value)
            )
    eventos, vistos, cancelamento = [], set(), False
    for event_root, xml in [(node, None) for node in embutidos] + [
        (None, _xml_bytes(value)) for value in candidatos
    ]:
        if event_root is None:
            try:
                event_root = ET.fromstring(xml)
            except Exception:
                raise XmlContabilidadeError(
                    "Um evento fiscal retornou XML inválido.", 409
                ) from None
        infos = event_root.findall(".//n:infEvento", NS)
        for info in infos:
            if (
                info.findtext("n:chNFe", namespaces=NS) != chave
                or info.findtext("n:tpAmb", namespaces=NS) != "1"
            ):
                raise XmlContabilidadeError(
                    "Um evento fiscal não corresponde à nota solicitada.", 409
                )
        identity = next((i.get("Id") for i in infos if i.get("Id")), None)
        if not infos or not identity:
            raise XmlContabilidadeError(
                "Um evento fiscal não possui identificação válida.", 409
            )
        if identity not in vistos:
            if xml is not None:
                eventos.append((re.sub(r"[^a-zA-Z0-9_-]", "", identity) + ".xml", xml))
            vistos.add(identity)
            cancelamento |= any(
                i.findtext("n:tpEvento", namespaces=NS) == "110111" for i in infos
            )
    return eventos, len(vistos), cancelamento


def _cnpj_empresa(db, tenant_id):
    from app.models import Tenant

    empresa = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
    cnpj = re.sub(r"\D", "", str(empresa.cnpj or "")) if empresa else ""
    if len(cnpj) != 14:
        raise XmlContabilidadeError(
            "Cadastre o CNPJ da empresa antes de preparar seus XMLs fiscais."
        )
    return cnpj


def _coletar_arquivos(db, tenant_id, documentos, data_inicio, data_fim):
    cnpj_empresa = _cnpj_empresa(db, tenant_id)
    arquivos, notas, chaves, total = [], [], set(), 0
    unicos = {}
    for doc in documentos:
        key = doc.chave or f"{doc.provider}:{doc.documento_id}:{doc.modelo}"
        if key not in unicos:
            unicos[key] = doc
        else:
            existente = unicos[key]
            if doc.status == "cancelada":
                existente.status = "cancelada"
            if existente.venda is None and doc.venda is not None:
                existente.venda = doc.venda
    for doc in unicos.values():
        try:
            xml, detalhe = _obter_xml(db, tenant_id, doc)
            validacao = validar_xml_saida(xml, doc.chave, doc.modelo)
            if validacao is None:
                continue
            root, data_real = validacao
            cnpj_emitente = root.findtext(".//n:infNFe/n:emit/n:CNPJ", namespaces=NS)
            if cnpj_emitente != cnpj_empresa:
                # XML de fornecedor importado no Bling também tem tpNF=1.
                # Apenas o CNPJ emitente da própria empresa pertence ao lote.
                continue
            if not data_inicio <= data_real <= data_fim or doc.chave in chaves:
                continue
            eventos, quantidade_eventos, cancelamento_incluido = _eventos_xml(
                root, detalhe, doc.chave
            )
        except XmlContabilidadeError:
            raise
        except Exception:
            raise XmlContabilidadeError(
                f"Não foi possível obter o XML da nota {doc.documento_id} ({doc.provider}). Nenhum arquivo parcial foi gerado.",
                409,
            ) from None
        chaves.add(doc.chave)
        arquivos.append((f"{doc.chave}-nfe.xml", xml))
        arquivos.extend(eventos)
        total += len(xml) + sum(len(content) for _, content in eventos)
        if total > MAX_TOTAL_BYTES:
            raise XmlContabilidadeError(
                "Os XMLs excedem 30 MB. Divida o período em lotes menores."
            )
        nota = {
            "chave": doc.chave,
            "modelo": doc.modelo,
            "status": doc.status,
            "provedor": doc.provider,
            "data_emissao": data_real.isoformat(),
            "eventos_incluidos": quantidade_eventos,
            "emitente_cnpj": cnpj_emitente,
            "emitente_nome": root.findtext(".//n:infNFe/n:emit/n:xNome", namespaces=NS)
            or cnpj_emitente,
        }
        if doc.status == "cancelada" and not cancelamento_incluido:
            nota["aviso"] = (
                "Nota cancelada. O emissor não disponibilizou o XML do evento de cancelamento; incluído o XML original autorizado."
            )
        notas.append(nota)
    return arquivos, notas


def _zip(arquivos, notas, data_inicio, data_fim):
    if not notas:
        raise XmlContabilidadeError(
            "Nenhuma NF-e/NFC-e de saída em produção foi encontrada nesse período.", 404
        )
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as zipped:
        for name, content in arquivos:
            zipped.writestr(name, content)
        manifesto = {
            "data_inicio": data_inicio.isoformat(),
            "data_fim": data_fim.isoformat(),
            "fuso_horario": "America/Sao_Paulo",
            "quantidade_notas": len(notas),
            "emitente_cnpj": notas[0]["emitente_cnpj"],
            "emitente_nome": notas[0]["emitente_nome"],
            "notas": notas,
        }
        zipped.writestr(
            "manifesto.json",
            json.dumps(manifesto, ensure_ascii=False, indent=2).encode("utf-8"),
        )
    if buffer.tell() > MAX_ZIP_BYTES:
        raise XmlContabilidadeError(
            "O ZIP excede 15 MB. Divida o período em lotes menores."
        )
    return (
        buffer.getvalue(),
        f"xml-saida-{data_inicio:%Y%m%d}-{data_fim:%Y%m%d}.zip",
        len(notas),
    )


def _confirmar_emissoes_periodo(db, tenant_id, data_inicio, data_fim):
    from app.services.xml_contabilidade_reconciliation import (
        STATUS_PENDENTES,
        reconciliar_pendentes,
    )

    inicio = datetime.combine(data_inicio, time.min)
    fim = datetime.combine(data_fim + timedelta(days=1), time.min)

    def pendentes():
        return (
            db.query(Venda.id)
            .filter(
                Venda.tenant_id == _tenant(tenant_id),
                Venda.nfe_provider == "intnfe",
                Venda.nfe_ambiente == 1,
                Venda.nfe_status.in_(STATUS_PENDENTES),
                Venda.nfe_data_emissao >= inicio,
                Venda.nfe_data_emissao < fim,
            )
            .first()
        )

    if pendentes():
        reconciliar_pendentes(db, tenant_id, inicio.replace(tzinfo=BRASILIA))
        if pendentes():
            raise XmlContabilidadeError(
                "Há notas em processamento ou sem confirmação nesse período. Aguarde a confirmação fiscal antes de preparar o lote; nenhum ZIP parcial foi gerado.",
                409,
            )


def gerar_zip_periodo(db, tenant_id, data_inicio, data_fim):
    _validar_periodo(data_inicio, data_fim)
    _confirmar_emissoes_periodo(db, tenant_id, data_inicio, data_fim)
    from app.services.xml_contabilidade_bling import sincronizar_periodo_bling

    sincronizar_periodo_bling(db, tenant_id, data_inicio, data_fim)
    docs = _listar_documentos(db, tenant_id, data_inicio, data_fim)
    arquivos, notas = _coletar_arquivos(db, tenant_id, docs, data_inicio, data_fim)
    return _zip(arquivos, notas, data_inicio, data_fim)
