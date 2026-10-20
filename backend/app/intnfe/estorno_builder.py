"""Escopo inicial: inversão integral de NFC-e interna CRT1, SN102 e PIS/COFINS49."""

from __future__ import annotations

import hashlib
import json
import re
from decimal import Decimal, ROUND_HALF_UP

from defusedxml import ElementTree as ET
from defusedxml.common import DefusedXmlException

NS = {"n": "http://www.portalfiscal.inf.br/nfe"}
CENT = Decimal("0.01")
FRASE_LEGAL_ESTORNO = (
    "Nota Fiscal emitida de acordo com inciso VII do caput do art. 298 do RICMS"
)


class EstornoError(Exception):
    def __init__(self, mensagem, *, status=422, code="EstornoInvalido"):
        super().__init__(mensagem)
        self.status, self.code = status, code


def exigir(condicao, mensagem):
    if not condicao:
        raise EstornoError(mensagem)


def parse_xml(value):
    raw = value.encode("utf-8") if isinstance(value, str) else value
    exigir(
        isinstance(raw, bytes) and 0 < len(raw) <= 2_000_000,
        "XML fiscal ausente ou inválido.",
    )
    exigir(
        b"<!DOCTYPE" not in raw.upper() and b"<!ENTITY" not in raw.upper(),
        "XML com declaração não permitida.",
    )
    try:
        return ET.fromstring(
            raw, forbid_dtd=True, forbid_entities=True, forbid_external=True
        )
    except (ET.ParseError, DefusedXmlException):
        raise EstornoError("O XML fiscal não pôde ser lido.") from None


def text(node, path, required=True):
    value = node.findtext(path, namespaces=NS) if node is not None else None
    value = str(value or "").strip()
    exigir(
        value or not required, "O XML não contém todos os dados necessários ao estorno."
    )
    return value


def decimal(node, path, default=None):
    value = text(node, path, required=default is None)
    try:
        result = Decimal(value if value else str(default))
    except Exception:
        raise EstornoError("O XML contém um valor numérico inválido.") from None
    exigir(result.is_finite(), "O XML contém um valor numérico inválido.")
    return result


def money(value):
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def xml_endereco(node):
    return {
        key: text(node, "n:" + tag)
        for key, tag in (
            ("logradouro", "xLgr"),
            ("numero", "nro"),
            ("bairro", "xBairro"),
            ("municipio", "xMun"),
            ("codigoMunicipio", "cMun"),
            ("uf", "UF"),
            ("cep", "CEP"),
        )
    }


def destinatario_anonimo(venda):
    dest = parse_xml(venda.nfe_xml).find(".//n:infNFe/n:dest", NS)
    return not (text(dest, "n:CPF", False) or text(dest, "n:CNPJ", False))


def destinatario_proprio(venda):
    exigir(
        destinatario_anonimo(venda),
        "O destinatário já está identificado no documento original.",
    )
    emit = parse_xml(venda.nfe_xml).find(".//n:infNFe/n:emit", NS)
    return {
        "cnpj": text(emit, "n:CNPJ"),
        "razaoSocial": text(emit, "n:xNome"),
        "indicadorIe": "1",
        "inscricaoEstadual": text(emit, "n:IE"),
        "endereco": xml_endereco(emit.find("n:enderEmit", NS)),
    }


def validar_destinatario(value):
    exigir(
        isinstance(value, dict),
        "Identifique o destinatário da NF-e de estorno antes de emitir.",
    )
    allowed = {
        "cnpj",
        "cpf",
        "razaoSocial",
        "indicadorIe",
        "inscricaoEstadual",
        "endereco",
    }
    exigir(not set(value) - allowed, "O destinatário contém campos não permitidos.")
    result = {key: str(val).strip() for key, val in value.items() if key != "endereco"}
    docs = [(key, result.get(key)) for key in ("cnpj", "cpf") if result.get(key)]
    exigir(len(docs) == 1, "Informe um CPF ou CNPJ para o destinatário do estorno.")
    key, number = docs[0]
    exigir(
        re.fullmatch(r"\d{%s}" % (14 if key == "cnpj" else 11), number),
        "Documento do destinatário inválido.",
    )
    exigir(
        1 <= len(result.get("razaoSocial", "")) <= 60, "Informe o nome do destinatário."
    )
    exigir(
        result.get("indicadorIe") in {"1", "2", "9"},
        "Indicador de IE do destinatário inválido.",
    )
    exigir(
        result["indicadorIe"] != "1" or result.get("inscricaoEstadual"),
        "Informe a IE do destinatário contribuinte.",
    )
    address = value.get("endereco")
    fields = {
        "logradouro",
        "numero",
        "bairro",
        "municipio",
        "codigoMunicipio",
        "uf",
        "cep",
    }
    exigir(
        isinstance(address, dict) and set(address) == fields,
        "Informe o endereço completo do destinatário.",
    )
    result["endereco"] = {key: str(val).strip() for key, val in address.items()}
    exigir(
        all(result["endereco"].values()), "Informe o endereço completo do destinatário."
    )
    exigir(
        re.fullmatch(r"\d{7}", result["endereco"]["codigoMunicipio"])
        and re.fullmatch(r"\d{8}", result["endereco"]["cep"]),
        "CEP ou município do destinatário inválido.",
    )
    exigir(
        result["endereco"]["uf"]
        in {
            "AC",
            "AL",
            "AP",
            "AM",
            "BA",
            "CE",
            "DF",
            "ES",
            "GO",
            "MA",
            "MT",
            "MS",
            "MG",
            "PA",
            "PB",
            "PR",
            "PE",
            "PI",
            "RJ",
            "RN",
            "RS",
            "RO",
            "RR",
            "SC",
            "SP",
            "SE",
            "TO",
        },
        "UF do destinatário inválida.",
    )
    return result


def tributacao_item(item):
    tax = item.find("n:imposto", NS)
    exigir(tax is not None, "O item não possui tributação no XML original.")
    exigir(
        all(
            node.tag.split("}")[-1] in {"ICMS", "PIS", "COFINS", "vTotTrib"}
            for node in tax
        ),
        "A tributação deste item ainda não é suportada no estorno.",
    )
    exigir(
        decimal(tax, "n:vTotTrib", 0) == 0,
        "Tributos adicionais do item exigem revisão fiscal.",
    )
    icms, pis, cofins = (
        tax.find(path, NS)
        for path in ("n:ICMS/n:ICMSSN102", "n:PIS/n:PISOutr", "n:COFINS/n:COFINSOutr")
    )
    exigir(text(icms, "n:CSOSN") == "102", "O estorno inicial suporta apenas CSOSN102.")
    origem = text(icms, "n:orig")
    exigir(origem in set("012345678"), "Origem da mercadoria inválida.")
    for group, rate, val in ((pis, "pPIS", "vPIS"), (cofins, "pCOFINS", "vCOFINS")):
        exigir(
            text(group, "n:CST") == "49"
            and decimal(group, "n:vBC")
            == decimal(group, "n:" + val)
            == decimal(group, "n:" + rate, 0)
            == 0,
            "O estorno inicial exige PIS/COFINS49 com valores e alíquotas zerados.",
        )
    return {
        "icms": {"cst": "102", "origem": origem},
        "pis": {"cst": "49", "aliquota": 0, "valor": 0},
        "cofins": {"cst": "49", "aliquota": 0, "valor": 0},
    }


def build(
    venda,
    connection,
    *,
    ambiente_codigo,
    destinatario=None,
    motivo="Operação não realizada; mercadoria não saiu.",
):
    exigir(
        venda.status == "cancelada",
        "Cancele a venda comercial antes de emitir o estorno fiscal.",
    )
    exigir(
        venda.nfe_provider == "intnfe" and venda.nfe_status == "autorizada",
        "O estorno exige uma NFC-e IntNFe autorizada e vigente.",
    )
    cancel_status = getattr(venda, "nfe_cancelamento_status", None)
    exigir(
        cancel_status != "solicitado"
        and not (
            cancel_status == "pendente"
            and getattr(venda, "nfe_cancelamento_solicitado_em", None)
        ),
        "Consulte o pedido de cancelamento fiscal em andamento antes de emitir estorno.",
    )
    exigir(ambiente_codigo in (1, 2), "Ambiente fiscal inválido.")
    root = parse_xml(venda.nfe_xml)
    inf = root.find(".//n:infNFe", NS)
    exigir(inf is not None, "XML original sem identificação fiscal.")
    ide = inf.find("n:ide", NS)
    chave = inf.attrib.get("Id", "").removeprefix("NFe")
    exigir(
        re.fullmatch(r"\d{44}", chave) and chave == venda.nfe_chave,
        "Chave do XML original diverge da venda.",
    )
    exigir(
        text(ide, "n:mod") == "65"
        and int(text(ide, "n:nNF")) == venda.nfe_numero
        and int(text(ide, "n:serie")) == venda.nfe_serie,
        "Identificação da NFC-e original diverge da venda.",
    )
    exigir(
        int(text(ide, "n:tpAmb")) == venda.nfe_ambiente,
        "Ambiente do XML original diverge da venda.",
    )
    prot = root.find(".//n:protNFe/n:infProt", NS)
    exigir(
        text(prot, "n:cStat") in {"100", "150"}
        and text(prot, "n:chNFe") == chave
        and text(prot, "n:nProt") == venda.nfe_protocolo,
        "O XML original não comprova a autorização da NFC-e.",
    )
    emit = inf.find("n:emit", NS)
    exigir(
        text(emit, "n:CNPJ") == connection.cnpj and text(emit, "n:CRT") == "1",
        "O estorno inicial exige emitente CRT1 do mesmo vínculo fiscal.",
    )
    emitente = {
        "cnpj": connection.cnpj,
        "razaoSocial": text(emit, "n:xNome"),
        "nomeFantasia": text(emit, "n:xFant", False)
        or getattr(connection, "nome_fantasia", None)
        or text(emit, "n:xNome"),
        "inscricaoEstadual": text(emit, "n:IE"),
        "crt": "1",
        "endereco": xml_endereco(emit.find("n:enderEmit", NS)),
    }
    original_dest = inf.find("n:dest", NS)
    if (
        destinatario is None
        and original_dest is not None
        and (
            text(original_dest, "n:CPF", False) or text(original_dest, "n:CNPJ", False)
        )
    ):
        destinatario = {
            "razaoSocial": text(original_dest, "n:xNome"),
            "indicadorIe": text(original_dest, "n:indIEDest"),
            "endereco": xml_endereco(original_dest.find("n:enderDest", NS)),
        }
        for tag, field in (
            ("CPF", "cpf"),
            ("CNPJ", "cnpj"),
            ("IE", "inscricaoEstadual"),
        ):
            if text(original_dest, "n:" + tag, False):
                destinatario[field] = text(original_dest, "n:" + tag)
    destinatario = validar_destinatario(destinatario)
    exigir(
        destinatario["endereco"]["uf"] == emitente["endereco"]["uf"],
        "O estorno inicial suporta apenas operação interna com CFOP1102.",
    )
    products, snapshot_items = [], []
    for item in inf.findall("n:det", NS):
        prod = item.find("n:prod", NS)
        exigir(
            text(prod, "n:CFOP") == "5102",
            "O estorno inicial suporta apenas CFOP5102 para1102.",
        )
        qty, unit, gross, discount = (
            decimal(prod, path, default)
            for path, default in (
                ("n:qCom", None),
                ("n:vUnCom", None),
                ("n:vProd", None),
                ("n:vDesc", 0),
            )
        )
        exigir(
            qty > 0
            and unit > 0
            and gross == money(qty * unit)
            and 0 <= discount <= gross,
            "Valores do item original precisam de revisão fiscal.",
        )
        exigir(
            decimal(prod, "n:vFrete", 0)
            == decimal(prod, "n:vSeg", 0)
            == decimal(prod, "n:vOutro", 0)
            == 0,
            "Frete ou acréscimos ainda não são suportados neste estorno.",
        )
        p = {
            "codigoProduto": text(prod, "n:cProd"),
            "descricao": text(prod, "n:xProd"),
            "ncm": text(prod, "n:NCM"),
            "cfop": "1102",
            "unidade": text(prod, "n:uCom"),
            "quantidade": float(qty),
            "valorUnitario": float(unit),
            "valorTotal": float(gross),
            "desconto": float(discount),
            "impostos": tributacao_item(item),
        }
        if text(prod, "n:CEST", False):
            p["cest"] = text(prod, "n:CEST")
        products.append(p)
        snapshot_items.append(
            {
                "codigo_produto": p["codigoProduto"],
                "descricao": p["descricao"],
                "ncm": p["ncm"],
                "cest": p.get("cest", ""),
                "unidade": p["unidade"],
                "quantidade": str(qty),
                "valor_unitario": str(unit),
                "valor_produtos": str(gross),
                "desconto": str(discount),
                "total": str(gross - discount),
                "cfop": "1102",
                "origem": p["impostos"]["icms"]["origem"],
            }
        )
    total = decimal(inf, "n:total/n:ICMSTot/n:vNF")
    exigir(
        products and total > 0 and total == money(venda.total),
        "Total do XML original diverge da venda.",
    )
    exigir(
        sum(Decimal(p["total"]) for p in snapshot_items) == total,
        "Totais e tributos da nota exigem revisão fiscal.",
    )
    for tag, expected in (
        ("vProd", sum(Decimal(p["valor_produtos"]) for p in snapshot_items)),
        ("vDesc", sum(Decimal(p["desconto"]) for p in snapshot_items)),
    ):
        exigir(
            decimal(inf, "n:total/n:ICMSTot/n:" + tag) == expected,
            "Totais de produtos/descontos da nota exigem revisão fiscal.",
        )
    for tag in (
        "vBC",
        "vICMS",
        "vICMSDeson",
        "vFCP",
        "vBCST",
        "vST",
        "vFCPST",
        "vFCPSTRet",
        "vFrete",
        "vSeg",
        "vOutro",
        "vII",
        "vIPI",
        "vIPIDevol",
        "vPIS",
        "vCOFINS",
        "vTotTrib",
    ):
        exigir(
            decimal(inf, "n:total/n:ICMSTot/n:" + tag, 0) == 0,
            "Tributos ou acréscimos totais da nota ainda não são suportados neste estorno.",
        )
    serie = str(connection.nfe_series).strip()
    exigir(
        serie.isdigit() and 0 <= int(serie) <= 889,
        "Configure uma série NF-e válida na IntNFe.",
    )
    payload = {
        "serie": serie,
        "ambienteCodigo": ambiente_codigo,
        "tipoOperacao": "0",
        "finalidade": "3",
        "naturezaOperacao": "Estorno de NF-e nao cancelada no prazo legal",
        "emitente": emitente,
        "destinatario": destinatario,
        "produtos": products,
        "pagamentos": [{"formaPagamento": "90", "valor": 0}],
        "frete": {"modalidade": "9"},
        "documentosReferenciados": [chave],
        "indicadorPresenca": "9",
        "informacoesFisco": f"{FRASE_LEGAL_ESTORNO}. Estorno integral da NFC-e {venda.nfe_numero}, serie {venda.nfe_serie}, chave {chave}. {motivo}"[
            :2000
        ],
    }
    snapshot = {
        "original_chave": chave,
        "emitente_cnpj": connection.cnpj,
        "ambiente_codigo": ambiente_codigo,
        "serie": int(serie),
        "total": str(total),
        "itens": snapshot_items,
        "destinatario": destinatario,
        "informacoes_fisco": payload["informacoesFisco"],
    }
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return (
        payload,
        snapshot,
        hashlib.sha256(canonical.encode()).hexdigest(),
        hashlib.sha256(venda.nfe_xml.encode()).hexdigest(),
    )
