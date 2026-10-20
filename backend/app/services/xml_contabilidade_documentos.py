"""Coleta saídas e estornos próprios validados, preservando os XMLs oficiais."""

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from io import BytesIO
import json
import re
from types import SimpleNamespace
from zipfile import ZIP_DEFLATED, ZipFile

from defusedxml import ElementTree as ET
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import noload

from app.vendas_models import Venda
from app.intnfe.estorno_models import IntNFeEstorno
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
    estorno: object = None


def _estornos_elegiveis(db, tenant_id):
    """A tabela própria é a origem; um XML de entrada avulso não é elegível."""
    return (
        db.query(IntNFeEstorno)
        .join(
            Venda,
            and_(
                Venda.id == IntNFeEstorno.venda_id,
                Venda.tenant_id == IntNFeEstorno.tenant_id,
            ),
        )
        .filter(
            IntNFeEstorno.tenant_id == _tenant(tenant_id),
            IntNFeEstorno.ambiente_codigo == 1,
            IntNFeEstorno.status.in_(("autorizado", "cancelado")),
            IntNFeEstorno.xml_validado.is_(True),
            IntNFeEstorno.autorizado_em.isnot(None),
            Venda.nfe_provider == "intnfe",
            Venda.nfe_ambiente == 1,
            Venda.nfe_modelo == "65",
            Venda.nfe_chave == IntNFeEstorno.original_chave,
        )
    )


def _documento_estorno(estorno):
    referencia = f"estorno:{estorno.id}"
    situacao = "cancelada" if estorno.status == "cancelado" else "autorizada"
    # Compatibilidade com os consumidores fiscais legados. O id tem namespace
    # próprio e nunca representa outra venda nem substitui seu documento fiscal.
    origem = SimpleNamespace(
        id=referencia,
        venda_id=estorno.venda_id,
        estorno_id=estorno.id,
        original_chave=estorno.original_chave,
        nfe_tipo="nfe",
        nfe_modelo="55",
        nfe_correlation_id=estorno.correlation_id,
        nfe_ambiente=1,
        nfe_xml=estorno.xml,
        nfe_chave=estorno.chave,
        nfe_numero=estorno.numero,
        nfe_status=situacao,
        nfe_data_emissao=estorno.autorizado_em,
    )
    return Documento(
        "intnfe",
        referencia,
        str(estorno.chave or ""),
        55,
        situacao,
        estorno.autorizado_em,
        venda=origem,
        estorno=estorno,
    )


def _documento(db, tenant_id, provider, documento_id):
    if provider != "intnfe":
        return None
    referencia = str(documento_id)
    if referencia.startswith("estorno:"):
        match = re.fullmatch(r"estorno:([1-9][0-9]*)", referencia)
        if not match:
            return None
        registro = (
            _estornos_elegiveis(db, tenant_id)
            .filter(IntNFeEstorno.id == int(match[1]))
            .first()
        )
        return _documento_estorno(registro) if registro else None
    if not referencia.isdigit():
        return None
    venda = (
        db.query(Venda)
        .options(noload("*"))
        .filter(
            Venda.tenant_id == _tenant(tenant_id),
            Venda.id == int(documento_id),
            Venda.nfe_provider == "intnfe",
            Venda.nfe_ambiente == 1,
        )
        .first()
    )
    if (
        not venda
        or _status(venda.nfe_status) not in STATUS_VALIDOS
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


def _chave_da_empresa_ou_desconhecida(coluna, cnpj):
    """Descarta fornecedores conhecidos antes de limites/HTTP; XML ainda valida.

    Chaves ausentes ou corrompidas continuam candidatas: a consulta oficial
    precisa resolvê-las ou bloquear o lote, nunca escondê-las como fornecedor.
    ``replace``/``substr`` são compatíveis com PostgreSQL e SQLite.
    """
    nao_numericos = coluna
    for digito in "0123456789":
        nao_numericos = func.replace(nao_numericos, digito, "")
    return or_(
        coluna.is_(None),
        func.length(coluna) != 44,
        nao_numericos != "",
        func.substr(coluna, 7, 14) == cnpj,
    )


def _listar_documentos(db, tenant_id, data_inicio, data_fim):
    # As colunas legadas não preservam o fuso; ampliar a busca evita perder uma
    # emissão na virada do dia. O dhEmi do XML aplica o filtro definitivo.
    inicio = datetime.combine(data_inicio - timedelta(days=1), time.min)
    fim = datetime.combine(data_fim + timedelta(days=2), time.min)
    cnpj = _cnpj_empresa(db, tenant_id)
    vendas = (
        db.query(Venda)
        .options(noload("*"))
        .filter(
            Venda.tenant_id == _tenant(tenant_id),
            _chave_da_empresa_ou_desconhecida(Venda.nfe_chave, cnpj),
            Venda.nfe_provider == "intnfe",
            Venda.nfe_ambiente == 1,
            func.lower(Venda.nfe_status).in_(STATUS_VALIDOS),
            Venda.nfe_data_emissao >= inicio,
            Venda.nfe_data_emissao < fim,
        )
        .order_by(Venda.nfe_data_emissao, Venda.id)
        .limit(MAX_DOCUMENTOS + 1)
        .all()
    )
    docs = [
        Documento(
            "intnfe",
            str(v.id),
            str(v.nfe_chave or ""),
            int(v.nfe_modelo or 0),
            _status(v.nfe_status),
            v.nfe_data_emissao,
            venda=v,
        )
        for v in vendas
    ]
    estornos = (
        _estornos_elegiveis(db, tenant_id)
        .filter(
            IntNFeEstorno.autorizado_em >= inicio.replace(tzinfo=BRASILIA),
            IntNFeEstorno.autorizado_em < fim.replace(tzinfo=BRASILIA),
        )
        .order_by(IntNFeEstorno.autorizado_em, IntNFeEstorno.id)
        .limit(MAX_DOCUMENTOS + 1)
        .all()
    )
    docs.extend(_documento_estorno(estorno) for estorno in estornos)
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
    if doc.provider != "intnfe" or doc.venda is None:
        raise XmlContabilidadeError(
            "Somente notas emitidas no CorePet em produção podem ser enviadas.", 409
        )
    if getattr(doc, "estorno", None) is not None:
        # Só é exportável o XML que o serviço de estorno já validou e guardou.
        # Baixar outro XML aqui não pode trocar silenciosamente essa evidência.
        return _xml_bytes(doc.estorno.xml), {}
    if doc.venda.nfe_xml:
        return _xml_bytes(doc.venda.nfe_xml), {}
    # A consulta usa a emissão CorePet já vinculada, sem commit intermediário.
    from app.intnfe.client import IntNFeClient
    from app.intnfe.emission import _access_token, _connection

    api = IntNFeClient()
    try:
        connection = _connection(db, tenant_id, require_enabled=False)
        token = _access_token(api, connection, doc.venda.nfe_ambiente)
        xml = _xml_bytes(
            api.document_xml(token, doc.venda.nfe_tipo, doc.venda.nfe_correlation_id)
        )
    finally:
        api.close()
    doc.venda.nfe_xml = xml.decode("utf-8-sig")
    return xml, {}


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
    return root, _data_xml(root)


def _data_xml(root):
    raw_date = root.findtext(
        ".//n:infNFe/n:ide/n:dhEmi", namespaces=NS
    ) or root.findtext(".//n:infNFe/n:ide/n:dEmi", namespaces=NS)
    try:
        dt = datetime.fromisoformat(str(raw_date).replace("Z", "+00:00"))
        dt = dt.replace(tzinfo=BRASILIA) if dt.tzinfo is None else dt
    except (TypeError, ValueError):
        raise XmlContabilidadeError(
            "O XML de uma nota não possui data de emissão válida.", 409
        ) from None
    return dt.astimezone(BRASILIA).date()


def validar_xml_documento(xml, doc, tenant_id, cnpj_empresa):
    """Exceção restrita ao estorno próprio; a validação geral segue só saída."""
    registro = getattr(doc, "estorno", None)
    if registro is None:
        return validar_xml_saida(xml, doc.chave, doc.modelo)
    from app.intnfe.estorno_builder import EstornoError
    from app.intnfe.estorno_xml import validate_xml

    snapshot = registro.snapshot
    if (
        doc.provider != "intnfe"
        or doc.documento_id != f"estorno:{registro.id}"
        or registro.tenant_id != _tenant(tenant_id)
        or registro.ambiente_codigo != 1
        or registro.status not in {"autorizado", "cancelado"}
        or registro.xml_validado is not True
        or not isinstance(snapshot, dict)
        or snapshot.get("ambiente_codigo") != 1
        or snapshot.get("emitente_cnpj") != cnpj_empresa
        or snapshot.get("original_chave") != registro.original_chave
        or not re.fullmatch(r"[0-9]{44}", doc.chave)
        or doc.chave[6:20] != cnpj_empresa
        or doc.modelo != 55
    ):
        raise XmlContabilidadeError(
            "O estorno não possui origem fiscal própria validada.", 409
        )
    raw = _xml_bytes(xml)
    try:
        autorizado = validate_xml(raw, snapshot)
    except (EstornoError, KeyError, TypeError, ValueError):
        raise XmlContabilidadeError(
            "O XML do estorno não corresponde ao documento fiscal autorizado.", 409
        ) from None
    if (
        any(
            autorizado[campo] != getattr(registro, campo)
            for campo in ("chave", "numero", "serie", "protocolo")
        )
        or autorizado["chave"] != doc.chave
    ):
        raise XmlContabilidadeError(
            "O XML do estorno diverge da identificação registrada.", 409
        )
    root = ET.fromstring(raw)
    return root, _data_xml(root)


def _obter_eventos(db, tenant_id, doc):
    from app.services.xml_contabilidade_eventos import obter_eventos_intnfe
    from app.xml_contabilidade_models import XmlContabilidadeEvento

    if (
        doc.provider != "intnfe"
        or doc.venda is None
        or not str(doc.venda.nfe_correlation_id or "").strip()
    ):
        raise XmlContabilidadeError(
            "Uma nota emitida no CorePet não possui referência fiscal válida para confirmar todos os eventos. Nenhum lote parcial foi preparado.",
            409,
        )
    # Uma falha remota continua bloqueando a coleta completa. Só após a
    # confirmação atual acrescentamos comprovantes já recebidos, para que
    # retenção/omissão do provedor não elimine eventos fiscais do arquivo.
    detalhe = {"_eventos_intnfe": obter_eventos_intnfe(db, tenant_id, doc)}
    persistidos = (
        db.query(XmlContabilidadeEvento)
        .filter(
            XmlContabilidadeEvento.tenant_id == _tenant(tenant_id),
            XmlContabilidadeEvento.provider == "intnfe",
            XmlContabilidadeEvento.documento_id == doc.documento_id,
            XmlContabilidadeEvento.chave == doc.chave,
        )
        .all()
    )
    detalhe["_eventos_persistidos"] = [
        {
            "autorizado": True,
            "tipoEventoCodigo": e.tipo,
            "protocolo": e.protocolo,
            "identidade": e.identidade,
            "xmlEvento": e.xml,
            "_persistido": True,
        }
        for e in persistidos
    ]
    return detalhe


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
    from app.services.xml_contabilidade_relatorios import atual

    relatorio = atual()
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
            validacao = validar_xml_documento(xml, doc, tenant_id, cnpj_empresa)
            if validacao is None:
                if relatorio:
                    relatorio.excluir(
                        doc, "XML de entrada ou homologação, fora do envio contábil."
                    )
                continue
            root, data_real = validacao
            cnpj_emitente = root.findtext(".//n:infNFe/n:emit/n:CNPJ", namespaces=NS)
            if cnpj_emitente != cnpj_empresa:
                # Apenas o XML emitido pelo CNPJ da própria empresa pertence ao lote.
                if relatorio:
                    relatorio.excluir(
                        doc, "O CNPJ emitente do XML não corresponde à empresa."
                    )
                continue
            if relatorio:
                relatorio.nota_validada(doc, root, data_real)
            if not data_inicio <= data_real <= data_fim or doc.chave in chaves:
                continue
            from app.services.xml_contabilidade_eventos import coletar_eventos

            detalhe.update(_obter_eventos(db, tenant_id, doc))
            eventos, resumo_eventos, cancelamento_incluido = coletar_eventos(
                root,
                detalhe,
                doc.chave,
                cnpj_empresa,
                cancelada=doc.status == "cancelada",
                xml_original=xml,
            )
        except XmlContabilidadeError as exc:
            if relatorio:
                relatorio.falha_documento(doc, exc)
            raise
        except Exception as exc:
            if relatorio:
                relatorio.falha_documento(doc, exc)
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
            "documento_id": doc.documento_id,
            "modelo": doc.modelo,
            "status": "cancelada" if cancelamento_incluido else doc.status,
            "provedor": doc.provider,
            "data_emissao": data_real.isoformat(),
            "eventos_incluidos": len(resumo_eventos),
            "eventos": resumo_eventos,
            "emitente_cnpj": cnpj_emitente,
            "emitente_nome": root.findtext(".//n:infNFe/n:emit/n:xNome", namespaces=NS)
            or cnpj_emitente,
        }
        if getattr(doc, "estorno", None) is not None:
            nota.update(
                tipo_documento="estorno",
                venda_id=doc.estorno.venda_id,
                chave_original=doc.estorno.original_chave,
            )
        if any(e["data_registro"] > data_fim.isoformat() for e in resumo_eventos):
            nota["observacao"] = (
                "Inclui eventos registrados após o período de emissão selecionado."
            )
        notas.append(nota)
        if relatorio:
            relatorio.coleta(doc, nota)
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
            "criterio_periodo": "Data de emissão da nota; inclui todos os eventos registrados dessas notas disponíveis no momento da coleta.",
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
            db.query(Venda)
            .options(noload("*"))
            .filter(
                Venda.tenant_id == _tenant(tenant_id),
                Venda.nfe_provider == "intnfe",
                Venda.nfe_ambiente == 1,
                Venda.nfe_status.in_(STATUS_PENDENTES),
                Venda.nfe_data_emissao >= inicio,
                Venda.nfe_data_emissao < fim,
            )
            .all()
        )

    restantes = pendentes()
    consultadas = [v.id for v in restantes]
    if restantes:
        reconciliar_pendentes(db, tenant_id, inicio.replace(tzinfo=BRASILIA))
        restantes = pendentes()
    from app.services.xml_contabilidade_relatorios import atual, ACOES_PENDENTES

    relatorio = atual()
    if relatorio:
        if consultadas:
            for venda in (
                db.query(Venda)
                .options(noload("*"))
                .filter(
                    Venda.tenant_id == _tenant(tenant_id), Venda.id.in_(consultadas)
                )
                .populate_existing()
                .all()
            ):
                relatorio._venda(venda)
        relatorio.pendentes(restantes)
    if isinstance(db.info, dict):
        db.info["xml_contabilidade_pendencias"] = [
            {
                "documento_id": str(v.id),
                "venda_id": v.id,
                "numero": v.nfe_numero,
                "status_fiscal": v.nfe_status,
                "motivo": "Emissão sem confirmação fiscal; não incluída nos anexos.",
                "acao_recomendada": ACOES_PENDENTES,
            }
            for v in restantes
        ]
    return restantes


def _preparar_periodo(db, tenant_id, data_inicio, data_fim):
    _validar_periodo(data_inicio, data_fim)
    _confirmar_emissoes_periodo(db, tenant_id, data_inicio, data_fim)
    docs = _listar_documentos(db, tenant_id, data_inicio, data_fim)
    arquivos, notas = _coletar_arquivos(db, tenant_id, docs, data_inicio, data_fim)
    # Um cancelamento/CC-e registrado no mês também pertence à contabilidade
    # desse mês quando a nota foi emitida em uma competência anterior.
    from app.services.xml_contabilidade_individual import coletar_eventos_periodo
    from app.services.xml_contabilidade_pacotes import mesclar_coletas

    extras, notas_eventos = coletar_eventos_periodo(
        db, tenant_id, data_inicio, data_fim, coleta_pronta=(arquivos, notas)
    )
    return mesclar_coletas(arquivos, notas, extras, notas_eventos)


def gerar_anexos_periodo(db, tenant_id, data_inicio, data_fim):
    from app.services.xml_contabilidade_pacotes import criar_anexos_por_tipo

    arquivos, notas = _preparar_periodo(db, tenant_id, data_inicio, data_fim)
    pendencias = (
        db.info.get("xml_contabilidade_pendencias", [])
        if isinstance(db.info, dict)
        else []
    )
    if not notas and pendencias:
        raise XmlContabilidadeError(
            "Há notas pendentes de confirmação e nenhum documento pronto para enviar. Consulte a situação fiscal e solicite um novo lote após regularizar.",
            409,
        )
    return criar_anexos_por_tipo(
        arquivos, notas, data_inicio, data_fim, pendencias=pendencias
    )


def gerar_zip_periodo(db, tenant_id, data_inicio, data_fim):
    from app.services.xml_contabilidade_pacotes import agrupar_download

    anexos, nome, quantidade = gerar_anexos_periodo(
        db, tenant_id, data_inicio, data_fim
    )
    return agrupar_download(anexos, nome), nome, quantidade
