"""ZIPs fiscais separados por tipo, enviados juntos em uma única mensagem."""

from copy import deepcopy
from io import BytesIO
import json
import re
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

from app.services.xml_contabilidade_common import (
    MAX_DOCUMENTOS,
    MAX_TOTAL_BYTES,
    MAX_XML_BYTES,
    MAX_ZIP_BYTES,
    XmlContabilidadeError,
)

NOTA = re.compile(r"(?P<chave>\d{44})-nfe\.xml")
EVENTO = re.compile(r"ID(?P<tipo>\d{6})(?P<chave>\d{44})(?P<seq>\d{2})\.xml")


def _erro_integridade():
    return XmlContabilidadeError(
        "Há arquivos fiscais conflitantes ou sem identificação. Nenhum lote parcial foi gerado.",
        409,
    )


def mesclar_coletas(arquivos, notas, outros_arquivos, outras_notas):
    """Deduplica emissão/eventos por identidade, sem alterar o XML assinado."""
    unicos = {}
    for nome, conteudo in [*arquivos, *outros_arquivos]:
        if not (NOTA.fullmatch(nome) or EVENTO.fullmatch(nome)):
            raise _erro_integridade()
        if nome in unicos and unicos[nome] != conteudo:
            raise _erro_integridade()
        unicos[nome] = conteudo
    por_chave = {}
    for original in [*notas, *outras_notas]:
        nota = deepcopy(original)
        chave = nota["chave"]
        if chave not in por_chave:
            por_chave[chave] = nota
            continue
        anterior = por_chave[chave]
        if anterior["emitente_cnpj"] != nota["emitente_cnpj"]:
            raise _erro_integridade()
        if nota.get("status") == "cancelada":
            anterior["status"] = "cancelada"
        eventos = {
            (e["tipo"], e["sequencia"], e["protocolo"]): e
            for e in [*anterior.get("eventos", []), *nota.get("eventos", [])]
        }
        anterior["eventos"] = list(eventos.values())
        anterior["eventos_incluidos"] = len(eventos)
    if len(por_chave) > MAX_DOCUMENTOS:
        raise XmlContabilidadeError(
            f"O período excede {MAX_DOCUMENTOS} notas. Divida-o em períodos menores."
        )
    return list(unicos.items()), list(por_chave.values())


def _categoria(nome):
    nota = NOTA.fullmatch(nome)
    if nota:
        return "notas", nota["chave"], None
    evento = EVENTO.fullmatch(nome)
    if not evento:
        raise _erro_integridade()
    tipo = evento["tipo"]
    if tipo in {"110111", "110112"}:
        grupo = "cancelamentos"
    elif tipo == "110110":
        grupo = "cartas-correcao"
    else:
        grupo = f"eventos-{tipo}"
    return grupo, evento["chave"], tipo


def _manifesto(notas, inicio, fim, grupo, tipos):
    return {
        "data_inicio": inicio.isoformat(),
        "data_fim": fim.isoformat(),
        "fuso_horario": "America/Sao_Paulo",
        "criterio_periodo": (
            "Notas emitidas no período com seus eventos disponíveis, mais eventos "
            "registrados no período de notas emitidas anteriormente."
        ),
        "categoria": grupo,
        "tipos_evento": sorted(tipos),
        "quantidade_notas": len(notas),
        "emitente_cnpj": notas[0]["emitente_cnpj"],
        "emitente_nome": notas[0]["emitente_nome"],
        "observacao_xml": (
            "Os XMLs originais são preservados. Quando o provedor disponibiliza "
            "um evento apenas embutido na nota, o arquivo do evento contém esse "
            "documento original completo, sem extrair ou regravar a assinatura."
        ),
        "notas": notas,
    }


def criar_anexos_por_tipo(arquivos, notas, data_inicio, data_fim, *, pendencias=None):
    arquivos, notas = mesclar_coletas(arquivos, notas, [], [])
    if not arquivos or not notas:
        raise XmlContabilidadeError(
            "Nenhuma NF-e/NFC-e de saída ou evento em produção foi encontrado nesse período.",
            404,
        )
    if any(len(content) > MAX_XML_BYTES for _, content in arquivos):
        raise XmlContabilidadeError("Um XML excede o tamanho permitido.")
    if sum(len(content) for _, content in arquivos) > MAX_TOTAL_BYTES:
        raise XmlContabilidadeError(
            "Os XMLs excedem 30 MB. Divida o período em lotes menores."
        )
    por_chave = {nota["chave"]: nota for nota in notas}
    grupos = {}
    for nome, content in arquivos:
        grupo, chave, tipo = _categoria(nome)
        if chave not in por_chave:
            raise _erro_integridade()
        grupos.setdefault(grupo, []).append((nome, content, chave, tipo))
    anexos = []
    for grupo, items in sorted(grupos.items()):
        chaves = {item[2] for item in items}
        tipos = {item[3] for item in items if item[3]}
        notas_grupo = [deepcopy(n) for n in notas if n["chave"] in chaves]
        # O manifesto de cada ZIP lista somente os eventos daquele tipo.
        for nota in notas_grupo:
            nota["eventos"] = [e for e in nota.get("eventos", []) if e["tipo"] in tipos]
            nota["eventos_incluidos"] = len(nota["eventos"])
        buffer = BytesIO()
        with ZipFile(buffer, "w", ZIP_DEFLATED) as zipped:
            for nome, content, _, _ in items:
                zipped.writestr(nome, content)
            zipped.writestr(
                "manifesto.json",
                json.dumps(
                    _manifesto(notas_grupo, data_inicio, data_fim, grupo, tipos),
                    ensure_ascii=False,
                    indent=2,
                ).encode("utf-8"),
            )
            if pendencias:
                zipped.writestr(
                    "relatorio.json",
                    json.dumps(
                        {
                            "data_inicio": data_inicio.isoformat(),
                            "data_fim": data_fim.isoformat(),
                            "etapa": "preparacao",
                            "aviso": "Há emissões pendentes de confirmação que não foram incluídas nos XMLs. Este relatório não confirma envio de e-mail.",
                            "notas_pendentes": len(pendencias),
                            "pendencias": pendencias,
                        },
                        ensure_ascii=False,
                        indent=2,
                    ).encode("utf-8"),
                )
        anexos.append(
            {
                "filename": f"{grupo}-{data_inicio:%Y%m%d}-{data_fim:%Y%m%d}.zip",
                "content": buffer.getvalue(),
                "mime_subtype": "zip",
            }
        )
    if sum(len(a["content"]) for a in anexos) > MAX_ZIP_BYTES:
        raise XmlContabilidadeError(
            "Os ZIPs excedem 15 MB. Divida o período em lotes menores."
        )
    return (
        anexos,
        f"xml-saida-{data_inicio:%Y%m%d}-{data_fim:%Y%m%d}.zip",
        len(notas),
    )


def agrupar_download(anexos, nome):
    """Um único download, com os mesmos ZIPs por tipo anexados no e-mail."""
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_STORED) as zipped:
        for anexo in anexos:
            zipped.writestr(anexo["filename"], anexo["content"])
    if buffer.tell() > MAX_ZIP_BYTES:
        raise XmlContabilidadeError(
            "O ZIP excede 15 MB. Divida o período em lotes menores."
        )
    return buffer.getvalue()
