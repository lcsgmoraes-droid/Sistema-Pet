"""Converte apenas campos documentados pela IntNFe, sem perdas silenciosas.

Contrato: https://intnfe.com.br/api/doc#objetos. Identidade, protocolo, datas
e cálculos agregados são recriados pelo emissor. Dados sem equivalente no
contrato interrompem a clonagem em vez de gerar uma nota incompleta.
"""

from decimal import Decimal, InvalidOperation
from xml.etree.ElementTree import ParseError

from defusedxml import ElementTree as ET
from defusedxml.common import DefusedXmlException
from fastapi import HTTPException

# Identificador do namespace oficial da NF-e (MOC), sem conexão HTTP.
NS = {"n": "http://www.portalfiscal.inf.br/nfe"}  # NOSONAR


class Reader:
    def __init__(self, xml):
        self.root = ET.fromstring(xml)
        self.info = self.root.find(".//n:infNFe", NS)
        if self.info is None:
            raise HTTPException(
                422, "O XML original não contém uma nota fiscal completa."
            )
        self.used = set()

    def text(self, node, path, default=None):
        child = (
            node.find("/".join("n:" + part for part in path.split("/")), NS)
            if node is not None
            else None
        )
        if child is None:
            return default
        self.used.add(child)
        return (child.text or "").strip() or default

    def number(self, node, path, default=None):
        value = self.text(node, path)
        return float(Decimal(value)) if value is not None else default

    def mapping(self, node, fields, numbers=()):
        result = {}
        for source, target in fields.items():
            value = (
                self.number(node, source)
                if target in numbers
                else self.text(node, source)
            )
            if value is not None:
                result[target] = value
        return result

    def consume(self, node):
        if node is not None:
            self.used.update(node.iter())


ADDRESS = {
    "xLgr": "logradouro",
    "nro": "numero",
    "xBairro": "bairro",
    "xMun": "municipio",
    "cMun": "codigoMunicipio",
    "UF": "uf",
    "CEP": "cep",
    "xCpl": "complemento",
    "cPais": "codigoPais",
    "xPais": "pais",
}
ICMS = {
    "orig": "origem",
    "CST": "cst",
    "CSOSN": "cst",
    "pICMS": "aliquota",
    "vICMS": "valor",
    "pCredSN": "aliquota",
    "vCredICMSSN": "valor",
    "pRedBC": "percentualReducaoBc",
    "pDif": "percentualDiferimento",
    "vBCST": "baseCalculoSt",
    "pICMSST": "aliquotaSt",
    "vICMSST": "valorSt",
    "vBCSTRet": "baseCalculoStRetido",
    "pST": "aliquotaStRetido",
    "vICMSSTRet": "valorStRetido",
}


def _payload_from_xml(xml, *, cnpj, environment):
    reader = Reader(xml)
    info = reader.info
    ide = info.find("n:ide", NS)
    model = int(reader.text(ide, "mod", "0"))
    if model not in {55, 65} or reader.text(ide, "tpNF") != "1":
        raise HTTPException(422, "A clonagem aceita somente NF-e ou NFC-e de saída.")
    emitter = info.find("n:emit", NS)
    if reader.text(emitter, "CNPJ") != cnpj:
        raise HTTPException(
            403, "O emitente da nota original não corresponde a esta empresa."
        )
    payload = reader.mapping(
        ide,
        {
            "serie": "serie",
            "natOp": "naturezaOperacao",
            "indPres": "indicadorPresenca",
            "tpNF": "tipoOperacao",
            "finNFe": "finalidade",
        },
    )
    payload["ambienteCodigo"] = environment
    # Campos de geração/identidade, calculados novamente pelo emissor.
    for tag in (
        "cUF",
        "cNF",
        "mod",
        "nNF",
        "dhEmi",
        "dhSaiEnt",
        "dEmi",
        "dSaiEnt",
        "tpImp",
        "tpEmis",
        "cDV",
        "tpAmb",
        "procEmi",
        "verProc",
        "idDest",
        "cMunFG",
    ):
        reader.text(ide, tag)
    if reader.text(ide, "indFinal", "1") != "1":
        raise HTTPException(
            422,
            "A clonagem deste emissor aceita operações destinadas ao consumidor final.",
        )
    payload["documentosReferenciados"] = []
    for ref in ide.findall("n:NFref", NS):
        key = reader.text(ref, "refNFe")
        if key:
            payload["documentosReferenciados"].append(key)
    payload["emitente"] = reader.mapping(
        emitter,
        {
            "CNPJ": "cnpj",
            "xNome": "razaoSocial",
            "xFant": "nomeFantasia",
            "IE": "inscricaoEstadual",
            "CRT": "crt",
        },
    )
    payload["emitente"]["endereco"] = reader.mapping(
        emitter.find("n:enderEmit", NS), ADDRESS
    )
    reader.text(
        emitter.find("n:enderEmit", NS), "fone"
    )  # contato técnico cadastral, não dado fiscal
    recipient = info.find("n:dest", NS)
    if recipient is not None:
        person = reader.mapping(
            recipient,
            {
                "CNPJ": "cnpj",
                "CPF": "cpf",
                "xNome": "razaoSocial" if model == 55 else "nome",
                "IE": "inscricaoEstadual",
                "indIEDest": "indicadorIe",
                "email": "email",
            },
        )
        address = reader.mapping(recipient.find("n:enderDest", NS), ADDRESS)
        if address:
            person["endereco"] = address
        reader.text(recipient.find("n:enderDest", NS), "fone")
        payload["destinatario" if model == 55 else "consumidor"] = person
    payload["produtos"] = []
    for detail in info.findall("n:det", NS):
        product_node = detail.find("n:prod", NS)
        product = reader.mapping(
            product_node,
            {
                "cProd": "codigoProduto",
                "xProd": "descricao",
                "NCM": "ncm",
                "CFOP": "cfop",
                "uCom": "unidade",
                "qCom": "quantidade",
                "vUnCom": "valorUnitario",
                "vProd": "valorTotal",
                "vDesc": "desconto",
                "vFrete": "frete",
                "CEST": "cest",
            },
            numbers={"quantidade", "valorUnitario", "valorTotal", "desconto", "frete"},
        )
        # Tributação igual à comercial e ausência de GTIN são reproduzíveis.
        for tag, reference in (
            ("uTrib", "unidade"),
            ("qTrib", "quantidade"),
            ("vUnTrib", "valorUnitario"),
        ):
            existing = product_node.find("n:" + tag, NS)
            if existing is not None:
                raw = (existing.text or "").strip()
                equivalent = (
                    raw == str(product.get(reference))
                    if tag == "uTrib"
                    else Decimal(raw or 0) == Decimal(str(product.get(reference, 0)))
                )
                if equivalent:
                    reader.used.add(existing)
        for tag in ("cEAN", "cEANTrib"):
            node = product_node.find("n:" + tag, NS)
            if node is not None and (node.text or "").strip() in {"", "SEM GTIN"}:
                reader.used.add(node)
        if reader.text(product_node, "indTot", "1") != "1":
            raise HTTPException(
                422,
                "A nota possui itens fora do total, ainda não suportados na clonagem.",
            )
        tax = detail.find("n:imposto", NS)
        product["impostos"] = {}
        icms_node = tax.find("n:ICMS", NS) if tax is not None else None
        icms_node = next(iter(icms_node), None) if icms_node is not None else None
        if (
            icms_node is not None
            and icms_node.find("n:pCredSN", NS) is not None
            and icms_node.find("n:pICMS", NS) is not None
        ):
            raise HTTPException(
                422,
                "A nota possui crédito do Simples e ICMS próprio simultâneos, sem equivalente no emissor atual.",
            )
        icms = reader.mapping(
            icms_node, ICMS, numbers=set(ICMS.values()) - {"cst", "origem"}
        )
        product["impostos"]["icms"] = icms
        benefit = reader.text(product_node, "cBenef")
        if benefit:
            icms["codigoBeneficioFiscal"] = benefit
        fcp = reader.mapping(
            icms_node,
            {"vBCFCP": "baseCalculo", "pFCP": "aliquota", "vFCP": "valor"},
            numbers={"baseCalculo", "aliquota", "valor"},
        )
        if fcp:
            icms["fcp"] = fcp
        # Modalidade 3/base normal é calculada pelo contrato da API.
        taxable_base = (
            Decimal(str(product["valorTotal"]))
            - Decimal(str(product.get("desconto", 0)))
            + Decimal(str(product.get("frete", 0)))
        )
        expected_base = (
            taxable_base * (1 - Decimal(str(icms.get("percentualReducaoBc", 0))) / 100)
        ).quantize(Decimal("0.01"))
        for tag in (
            "modBC",
            "vBC",
            "vICMSOp",
            "vICMSDif",
            "modBCST",
            "pMVAST",
            "pRedBCST",
        ):
            node = icms_node.find("n:" + tag, NS) if icms_node is not None else None
            value = Decimal(node.text or "0") if node is not None else None
            if node is not None and (
                (tag == "modBC" and value == 3)
                or (tag == "vBC" and value == expected_base)
                or (tag not in {"modBC", "vBC"} and value == 0)
            ):
                reader.used.add(node)
        for kind in ("PIS", "COFINS"):
            group = tax.find("n:" + kind, NS) if tax is not None else None
            node = next(iter(group), None) if group is not None else None
            product["impostos"][kind.lower()] = reader.mapping(
                node,
                {
                    "CST": "cst",
                    "vBC": "baseCalculo",
                    "p" + kind: "aliquota",
                    "v" + kind: "valor",
                },
                numbers={"baseCalculo", "aliquota", "valor"},
            )
        ipi = tax.find("n:IPI", NS) if tax is not None else None
        if ipi is not None:
            group = ipi.find("n:IPITrib", NS)
            if group is None:
                group = ipi.find("n:IPINT", NS)
            values = reader.mapping(
                group,
                {
                    "CST": "cst",
                    "vBC": "baseCalculo",
                    "pIPI": "aliquota",
                    "vIPI": "valor",
                },
                numbers={"baseCalculo", "aliquota", "valor"},
            )
            values.update(reader.mapping(ipi, {"cEnq": "codigoEnquadramento"}))
            product["impostos"]["ipi"] = values
        ibs = tax.find("n:IBSCBS", NS) if tax is not None else None
        if ibs is not None:
            values = reader.mapping(
                ibs, {"CST": "cst", "cClassTrib": "classificacaoTributaria"}
            )
            values.update(
                reader.mapping(
                    ibs,
                    {
                        "gIBSCBS/vBC": "baseCalculo",
                        "gIBSCBS/gIBSUF/pIBSUF": "aliquotaIbsUf",
                        "gIBSCBS/gIBSUF/vIBSUF": "valorIbsUf",
                        "gIBSCBS/gIBSMun/pIBSMun": "aliquotaIbsMun",
                        "gIBSCBS/gIBSMun/vIBSMun": "valorIbsMun",
                        "gIBSCBS/gCBS/pCBS": "aliquotaCbs",
                        "gIBSCBS/gCBS/vCBS": "valorCbs",
                    },
                    numbers={
                        "baseCalculo",
                        "aliquotaIbsUf",
                        "valorIbsUf",
                        "aliquotaIbsMun",
                        "valorIbsMun",
                        "aliquotaCbs",
                        "valorCbs",
                    },
                )
            )
            aggregate = ibs.find("n:gIBSCBS/n:vIBS", NS)
            if aggregate is not None and Decimal(aggregate.text or 0) == Decimal(
                str(values.get("valorIbsUf", 0))
            ) + Decimal(str(values.get("valorIbsMun", 0))):
                reader.used.add(aggregate)
            product["impostos"]["ibsCbs"] = values
        payload["produtos"].append(product)
    payment = info.find("n:pag", NS)
    payload["pagamentos"] = []
    for node in payment.findall("n:detPag", NS) if payment is not None else []:
        value = reader.mapping(
            node, {"tPag": "formaPagamento", "vPag": "valor"}, numbers={"valor"}
        )
        value.update(
            reader.mapping(
                node.find("n:card", NS),
                {
                    "tpIntegra": "tipoIntegracao",
                    "CNPJ": "cnpjCredenciadora",
                    "tBand": "bandeira",
                    "cAut": "autorizacao",
                },
            )
        )
        indicator = node.find("n:indPag", NS)
        if indicator is not None and (indicator.text or "").strip() == "0":
            reader.used.add(indicator)
        payload["pagamentos"].append(value)
    transport = info.find("n:transp", NS)
    payload["frete"] = {
        "modalidade": reader.text(transport, "modFrete", "9"),
        "valor": reader.number(info, "total/ICMSTot/vFrete", 0),
    }
    carrier = transport.find("n:transporta", NS) if transport is not None else None
    if carrier is not None:
        payload["frete"]["transportadora"] = reader.mapping(
            carrier,
            {
                "CNPJ": "cnpj",
                "CPF": "cpf",
                "xNome": "razaoSocial",
                "IE": "inscricaoEstadual",
                "xEnder": "enderecoCompleto",
                "xMun": "municipio",
                "UF": "uf",
            },
        )
    intermediary = info.find("n:infIntermed", NS)
    if intermediary is not None:
        payload["intermediador"] = reader.mapping(
            intermediary, {"CNPJ": "cnpj", "idCadIntTran": "identificadorCadastro"}
        )
    if reader.text(ide, "indIntermed", "0") != (
        "1" if intermediary is not None else "0"
    ):
        raise HTTPException(
            422,
            "O indicador de intermediador da nota não corresponde aos dados cadastrados.",
        )
    payload.update(
        reader.mapping(
            info.find("n:infAdic", NS),
            {"infCpl": "informacoesAdicionais", "infAdFisco": "informacoesFisco"},
        )
    )
    # Totais são revalidados abaixo; informações técnicas do software não se clonam.
    totals = info.find("n:total/n:ICMSTot", NS)
    original_total = reader.number(totals, "vNF", 0)
    expected = sum(
        Decimal(str(item["valorTotal"]))
        - Decimal(str(item.get("desconto", 0)))
        + Decimal(str(item.get("impostos", {}).get("ipi", {}).get("valor", 0)))
        for item in payload["produtos"]
    ) + Decimal(str(payload["frete"]["valor"]))
    if abs(expected - Decimal(str(original_total))) > Decimal("0.01"):
        raise HTTPException(
            422,
            "Os totais da nota incluem valores ainda não suportados pela clonagem. Nenhum dado foi descartado.",
        )
    reader.consume(totals)
    reader.consume(info.find("n:infRespTec", NS))
    # Omitir um grupo opcional zerado conserva o mesmo valor fiscal.
    zero_equivalent = {
        "vTotTrib",
        "vTroco",
        "vSeg",
        "vOutro",
        "vFCPST",
        "vFCPSTRet",
        "vIPIDevol",
    }
    for node in info.iter():
        if (
            node.tag.split("}")[-1] in zero_equivalent
            and not len(node)
            and Decimal(node.text or 0) == 0
        ):
            reader.used.add(node)
    unsupported = sorted(
        {
            node.tag.split("}")[-1]
            for node in info.iter()
            if not len(node) and node not in reader.used and (node.text or "").strip()
        }
    )
    if unsupported:
        raise HTTPException(
            422,
            "Esta nota contém campos sem equivalente no emissor atual: "
            + ", ".join(unsupported[:15])
            + ". A clonagem foi interrompida para preservar todos os dados.",
        )
    if not payload["produtos"] or not payload["pagamentos"]:
        raise HTTPException(
            422,
            "O XML original precisa conter produtos e pagamentos completos para clonar.",
        )
    return payload, model


def payload_from_xml(xml, *, cnpj, environment):
    try:
        return _payload_from_xml(xml, cnpj=cnpj, environment=environment)
    except (
        ParseError,
        DefusedXmlException,
        InvalidOperation,
        ValueError,
        TypeError,
        KeyError,
    ):
        raise HTTPException(
            422,
            "O XML original está incompleto ou inválido para clonagem. Nenhuma nota foi criada.",
        ) from None
