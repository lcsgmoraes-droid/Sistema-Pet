"""Comprovantes oficiais de eventos, preservados sem reserializar assinaturas."""

from dataclasses import dataclass
from datetime import datetime
import re

from defusedxml import ElementTree as ET

from app.services.xml_contabilidade_common import (
    BRASILIA,
    MAX_XML_BYTES,
    NS,
    XmlContabilidadeError,
)

# MOC 7.0 / NT 2018.004: 110112 é cancelamento por substituição da NFC-e.
TIPOS_CANCELAMENTO = {"110111", "110112"}


@dataclass
class EventoFiscal:
    identidade: str
    tipo: str
    sequencia: int
    protocolo: str
    data: str
    xml: bytes | None
    registrado_em: datetime


def _xml_bytes(value):
    if isinstance(value, str):
        value = value.encode("utf-8")
    if not isinstance(value, bytes) or not value.strip() or len(value) > MAX_XML_BYTES:
        raise XmlContabilidadeError(
            "O comprovante XML de um evento fiscal está ausente ou excede o limite.",
            409,
        )
    return value


def _validar_evento(root, xml, chave, cnpj, metadados=None):
    info = root.find("n:evento/n:infEvento", NS)
    retorno = root.find("n:retEvento/n:infEvento", NS)
    if root.tag != f"{{{NS['n']}}}procEventoNFe" or info is None or retorno is None:
        raise XmlContabilidadeError(
            "Um evento fiscal não possui comprovante procEventoNFe com protocolo.", 409
        )
    tipo = info.findtext("n:tpEvento", namespaces=NS) or ""
    seq = info.findtext("n:nSeqEvento", namespaces=NS) or ""
    protocolo = retorno.findtext("n:nProt", namespaces=NS) or ""
    if not re.fullmatch(r"\d{6}", tipo) or not seq.isdigit() or not 1 <= int(seq) <= 99:
        raise XmlContabilidadeError(
            "Um evento fiscal não possui tipo/sequência válidos.", 409
        )
    identidade = f"ID{tipo}{chave}{int(seq):02d}"
    if (
        info.get("Id") != identidade
        or chave[6:20] != cnpj
        or info.findtext("n:chNFe", namespaces=NS) != chave
        or info.findtext("n:tpAmb", namespaces=NS) != "1"
        or any(
            retorno.findtext(f"n:{campo}", namespaces=NS) != valor
            for campo, valor in (
                ("chNFe", chave),
                ("tpAmb", "1"),
                ("tpEvento", tipo),
                ("nSeqEvento", seq),
            )
        )
        or (
            tipo in {"110110", *TIPOS_CANCELAMENTO}
            and info.findtext("n:CNPJ", namespaces=NS) != cnpj
        )
    ):
        raise XmlContabilidadeError(
            "Um evento fiscal não corresponde à chave, empresa ou ambiente da nota solicitada.",
            409,
        )
    codigos_aceitos = {"135", "155"} if tipo in TIPOS_CANCELAMENTO else {"135", "136"}
    if retorno.findtext(
        "n:cStat", namespaces=NS
    ) not in codigos_aceitos or not re.fullmatch(r"\d{15}", protocolo):
        raise XmlContabilidadeError(
            "Um evento fiscal não possui protocolo de registro válido.", 409
        )
    if metadados:
        tipo_remoto = metadados.get("tipoEventoCodigo")
        protocolo_remoto = metadados.get("protocolo")
        if (tipo_remoto is not None and str(tipo_remoto) != tipo) or (
            protocolo_remoto and str(protocolo_remoto) != protocolo
        ):
            raise XmlContabilidadeError(
                "O comprovante de um evento diverge do protocolo informado pelo emissor.",
                409,
            )
    raw_date = retorno.findtext("n:dhRegEvento", namespaces=NS) or info.findtext(
        "n:dhEvento", namespaces=NS
    )
    try:
        data = datetime.fromisoformat(str(raw_date).replace("Z", "+00:00"))
        if data.tzinfo is None:
            raise ValueError()
    except (TypeError, ValueError):
        raise XmlContabilidadeError(
            "Um evento fiscal não possui data de registro válida.", 409
        ) from None
    evento = EventoFiscal(
        identidade,
        tipo,
        int(seq),
        protocolo,
        data.astimezone(BRASILIA).date().isoformat(),
        xml,
        data,
    )
    from app.services.xml_contabilidade_relatorios import atual

    if atual():
        atual().evento_encontrado(chave, evento)
    return evento


def obter_eventos_intnfe(db, tenant_id, doc):
    """Consulta mesmo com NF-e em cache: eventos podem ser posteriores à emissão."""
    from app.intnfe.client import IntNFeClient
    from app.intnfe.emission import _access_token, _connection

    estorno = getattr(doc, "estorno", None)
    correlation_id = (
        estorno.correlation_id
        if estorno is not None
        else getattr(doc.venda, "nfe_correlation_id", None)
    )
    if estorno is not None and (
        str(estorno.tenant_id) != str(tenant_id)
        or doc.documento_id != f"estorno:{estorno.id}"
        or estorno.ambiente_codigo != 1
        or estorno.xml_validado is not True
    ):
        raise XmlContabilidadeError("A referência fiscal do estorno é inválida.", 409)
    if not isinstance(correlation_id, str) or not re.fullmatch(
        r"[A-Za-z0-9_-]{1,128}", correlation_id
    ):
        raise XmlContabilidadeError(
            "Uma nota emitida no CorePet não possui referência fiscal válida para confirmar todos os eventos. Nenhum lote parcial foi preparado.",
            409,
        )
    api = None
    try:
        api = IntNFeClient()
        connection = _connection(db, tenant_id, require_enabled=False)
        token = _access_token(api, connection, 1)
        return api.document_events(
            token, "nfe" if estorno is not None else doc.venda.nfe_tipo, correlation_id
        )
    except Exception:
        raise XmlContabilidadeError(
            f"Não foi possível confirmar todos os eventos fiscais da nota {doc.documento_id} (IntNFe). Nenhum ZIP parcial foi gerado.",
            409,
        ) from None
    finally:
        if api is not None:
            api.close()


def coletar_eventos(root, detalhe, chave, cnpj, *, cancelada=False, xml_original=None):
    """Inclui todos os eventos confirmados e rejeita comprovantes ausentes."""
    eventos, faltantes = {}, []
    for node in root.findall(".//n:procEventoNFe", NS):
        evento = _validar_evento(node, None, chave, cnpj)
        # Sem XML avulso oficial, conserva o arquivo fonte inteiro: extrair e
        # reserializar o nó mudaria namespaces e poderia invalidar assinatura.
        evento.xml = xml_original
        eventos[evento.identidade] = evento
    candidatos = []
    for row in detalhe.get("_eventos_persistidos", []) + detalhe.get(
        "_eventos_intnfe", []
    ):
        if row.get("autorizado") is not True:
            # Tentativa rejeitada não é evento registrado pela SEFAZ.
            if row.get("autorizado") is False:
                continue
            raise XmlContabilidadeError(
                "O emissor não confirmou a situação de um evento fiscal.", 409
            )
        if not row.get("xmlEvento"):
            tipo = str(row.get("tipoEventoCodigo") or "")
            tipo = tipo if re.fullmatch(r"\d{6}", tipo) else "desconhecido"
            protocolo = str(row.get("protocolo") or "")
            if not any(
                e.tipo == tipo and e.protocolo == protocolo for e in eventos.values()
            ):
                faltantes.append(f"evento {tipo} (comprovante XML ausente)")
            continue
        candidatos.append((row["xmlEvento"], row))
    for raw, metadados in candidatos:
        xml = _xml_bytes(raw)
        try:
            event_root = ET.fromstring(xml)
        except Exception:
            raise XmlContabilidadeError(
                "Um evento fiscal retornou XML inválido.", 409
            ) from None
        if (
            metadados
            and metadados.get("_persistido")
            and event_root.tag != f"{{{NS['n']}}}procEventoNFe"
        ):
            # Um comprovante embutido foi armazenado como arquivo fonte inteiro
            # para manter assinatura/namespaces. Valida novamente o nó do evento
            # correspondente, mantendo como anexo os bytes do arquivo original.
            event_root = next(
                (
                    node
                    for node in event_root.findall(".//n:procEventoNFe", NS)
                    if node.find("n:evento/n:infEvento", NS) is not None
                    and node.find("n:evento/n:infEvento", NS).get("Id")
                    == metadados.get("identidade")
                ),
                event_root,
            )
        evento = _validar_evento(event_root, xml, chave, cnpj, metadados)
        # Preferir o comprovante avulso oficial ao documento fonte que contém
        # um evento embutido, preservando seus bytes originais em ambos casos.
        if not (
            metadados and metadados.get("_persistido") and evento.identidade in eventos
        ):
            eventos[evento.identidade] = evento
    cancelamento = any(e.tipo in TIPOS_CANCELAMENTO for e in eventos.values())
    if cancelada and not cancelamento:
        faltantes.append("cancelamento (evento 110111)")
    sequencias_cce = {e.sequencia for e in eventos.values() if e.tipo == "110110"}
    # A API retorna todos os registros; a existência da CC-e 3 exige 1 e 2.
    if sequencias_cce:
        faltantes.extend(
            f"carta de correção (sequência {seq})"
            for seq in range(1, max(sequencias_cce) + 1)
            if seq not in sequencias_cce
        )
    if faltantes:
        raise XmlContabilidadeError(
            f"XMLs fiscais ausentes na nota {chave}: {'; '.join(faltantes)}. Nenhum ZIP parcial foi gerado.",
            409,
        )
    arquivos = [
        (f"{e.identidade}.xml", e.xml) for e in eventos.values() if e.xml is not None
    ]
    resumo = [
        {
            "tipo": e.tipo,
            "sequencia": e.sequencia,
            "protocolo": e.protocolo,
            "data_registro": e.data,
            "data_hora_registro": e.registrado_em.isoformat(),
            "identidade": e.identidade,
            "nome_arquivo": f"{e.identidade}.xml",
        }
        for e in eventos.values()
    ]
    return arquivos, resumo, cancelamento
