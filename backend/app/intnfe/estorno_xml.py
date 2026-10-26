"""Autorização do estorno só é aceita com XML equivalente ao snapshot original."""

from decimal import Decimal
from datetime import datetime, timezone
import re

from app.intnfe.estorno_builder import (
    NS,
    FRASE_LEGAL_ESTORNO,
    decimal,
    exigir,
    parse_xml,
    text,
    tributacao_item,
)


def validate_xml(raw, snapshot):
    root = parse_xml(raw)
    exigir(
        root.tag == "{" + NS["n"] + "}nfeProc",
        "O XML deve conter um nfeProc autorizado.",
    )
    exigir(
        len(root.findall(".//n:NFe", NS)) == len(root.findall("n:NFe", NS)) == 1
        and len(root.findall(".//n:infNFe", NS))
        == len(root.findall("n:NFe/n:infNFe", NS))
        == 1,
        "O XML deve conter uma única NF-e identificada.",
    )
    exigir(
        len(root.findall(".//n:protNFe", NS)) == len(root.findall("n:protNFe", NS)) == 1
        and len(root.findall(".//n:infProt", NS))
        == len(root.findall("n:protNFe/n:infProt", NS))
        == 1,
        "O XML deve conter um único protocolo fiscal.",
    )
    inf = root.find("n:NFe/n:infNFe", NS)
    exigir(inf is not None, "XML do estorno sem identificação.")
    ide = inf.find("n:ide", NS)
    for path, expected in (
        ("mod", "55"),
        ("tpAmb", str(snapshot["ambiente_codigo"])),
        ("tpNF", "0"),
        ("finNFe", "3"),
    ):
        exigir(
            text(ide, "n:" + path) == expected,
            "XML do estorno diverge em " + path + ".",
        )
    exigir(
        decimal(ide, "n:serie") == snapshot["serie"],
        "Série do estorno diverge do envio.",
    )
    exigir(
        text(inf, "n:emit/n:CNPJ") == snapshot["emitente_cnpj"],
        "Emitente do estorno diverge da nota original.",
    )
    exigir(
        text(inf, "n:emit/n:CRT") == "1",
        "O regime tributário do estorno diverge do original.",
    )
    refs = [no.text for no in ide.findall("n:NFref/n:refNFe", NS)]
    exigir(
        refs == [snapshot["original_chave"]],
        "Referência do estorno diverge da nota original.",
    )
    fisco = " ".join(text(inf, "n:infAdic/n:infAdFisco").split())
    exigir(
        FRASE_LEGAL_ESTORNO in fisco
        and fisco == " ".join(snapshot["informacoes_fisco"].split()),
        "Informações fiscais do estorno não contêm a expressão legal, referência e motivo enviados.",
    )
    recipient = snapshot["destinatario"]
    key = "CNPJ" if recipient.get("cnpj") else "CPF"
    exigir(
        text(inf, "n:dest/n:" + key) == recipient[key.lower()],
        "Destinatário do estorno diverge do envio.",
    )
    exigir(
        decimal(inf, "n:total/n:ICMSTot/n:vNF") == Decimal(snapshot["total"]),
        "Total do estorno diverge da nota original.",
    )
    for tag, expected in (
        ("vProd", sum(Decimal(item["valor_produtos"]) for item in snapshot["itens"])),
        ("vDesc", sum(Decimal(item["desconto"]) for item in snapshot["itens"])),
    ):
        exigir(
            decimal(inf, "n:total/n:ICMSTot/n:" + tag) == expected,
            "Produtos/descontos totais do estorno divergem do original.",
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
            "O estorno possui tributos ou acréscimos totais não previstos.",
        )
    payments = inf.findall("n:pag/n:detPag", NS)
    exigir(
        len(payments) == 1
        and text(payments[0], "n:tPag") == "90"
        and decimal(payments[0], "n:vPag") == 0,
        "O estorno deve ser sem pagamento, código90 e valor zero.",
    )
    items = inf.findall("n:det", NS)
    exigir(
        len(items) == len(snapshot["itens"]),
        "Itens do estorno divergem da nota original.",
    )
    for item, expected in zip(items, snapshot["itens"]):
        prod = item.find("n:prod", NS)
        for tag, field in (
            ("cProd", "codigo_produto"),
            ("xProd", "descricao"),
            ("NCM", "ncm"),
            ("uCom", "unidade"),
            ("CFOP", "cfop"),
            ("CEST", "cest"),
        ):
            exigir(
                text(prod, "n:" + tag, required=tag != "CEST") == expected[field],
                "Identificação/CFOP de um item do estorno diverge do original.",
            )
        for tag, field in (
            ("qCom", "quantidade"),
            ("vUnCom", "valor_unitario"),
            ("vProd", "valor_produtos"),
            ("vDesc", "desconto"),
        ):
            exigir(
                decimal(prod, "n:" + tag, 0 if tag == "vDesc" else None)
                == Decimal(expected[field]),
                "Valores de um item do estorno divergem do original.",
            )
        exigir(
            decimal(prod, "n:vFrete", 0)
            == decimal(prod, "n:vSeg", 0)
            == decimal(prod, "n:vOutro", 0)
            == 0,
            "Estorno possui acréscimos não previstos.",
        )
        exigir(
            tributacao_item(item)["icms"]["origem"] == expected["origem"],
            "Origem/tributação do estorno diverge do original.",
        )
    prot = root.find("n:protNFe/n:infProt", NS)
    exigir(
        text(prot, "n:tpAmb") == str(snapshot["ambiente_codigo"]),
        "Ambiente do protocolo fiscal diverge do envio.",
    )
    identifier = inf.attrib.get("Id", "")
    exigir(identifier.startswith("NFe"), "Identificador da NF-e de estorno inválido.")
    chave = identifier.removeprefix("NFe")
    numero = decimal(ide, "n:nNF")
    exigir(
        1 <= numero <= 999_999_999 and numero == int(numero),
        "Número da NF-e de estorno inválido.",
    )
    exigir(
        bool(re.fullmatch(r"[0-9]{44}", chave)) and text(prot, "n:chNFe") == chave,
        "Chave/protocolo do estorno inválido.",
    )
    exigir(
        chave[6:20] == snapshot["emitente_cnpj"]
        and chave[20:22] == "55"
        and int(chave[22:25]) == snapshot["serie"]
        and int(chave[25:34]) == int(numero),
        "A chave de acesso diverge do emitente, modelo, série ou número do estorno.",
    )
    exigir(
        text(prot, "n:cStat") in {"100", "150"},
        "O XML do estorno não contém autorização fiscal.",
    )
    protocolo = text(prot, "n:nProt")
    exigir(re.fullmatch(r"[0-9]{15}", protocolo), "Protocolo fiscal inválido.")
    data_autorizacao = text(prot, "n:dhRecbto", required=False) or text(ide, "n:dhEmi")
    try:
        autorizado_em = datetime.fromisoformat(data_autorizacao.replace("Z", "+00:00"))
    except ValueError:
        exigir(False, "A data de autorização do XML do estorno é inválida.")
    exigir(
        autorizado_em.tzinfo is not None and autorizado_em.utcoffset() is not None,
        "A data de autorização do XML do estorno precisa informar o fuso horário.",
    )
    return {
        "numero": int(numero),
        "serie": int(text(ide, "n:serie")),
        "chave": chave,
        "protocolo": protocolo,
        "autorizado_em": autorizado_em.astimezone(timezone.utc),
    }
