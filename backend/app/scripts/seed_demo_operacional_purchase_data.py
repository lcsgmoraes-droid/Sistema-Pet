"""Pure data builders for operational purchase demo scenarios."""

from __future__ import annotations

import zlib
from datetime import datetime
from decimal import Decimal
from typing import Any


DEMO_SUPPLIER_CNPJ = "11222333000181"


def build_demo_purchase_scenarios() -> list[dict[str, Any]]:
    """Return the operational states shown in purchases and supplier pendings."""

    return [
        {"key": "draft", "order_status": "rascunho", "label": "Pedido em montagem"},
        {
            "key": "sent",
            "order_status": "enviado",
            "label": "Pedido enviado ao fornecedor",
        },
        {
            "key": "ok",
            "order_status": "recebido_total",
            "label": "NF e pedido sem divergencia",
            "invoice_number": 900001,
            "invoice_qty": Decimal("10"),
            "invoice_unit_cost": Decimal("30.94"),
            "received_qty": Decimal("10"),
            "damaged_qty": Decimal("0"),
        },
        {
            "key": "open",
            "order_status": "recebido_parcial",
            "label": "Diferenca de quantidade e preco",
            "invoice_number": 900002,
            "invoice_qty": Decimal("8"),
            "invoice_unit_cost": Decimal("33.50"),
            "received_qty": Decimal("6"),
            "damaged_qty": Decimal("0"),
            "pending_status": "aberta",
        },
        {
            "key": "waiting",
            "order_status": "confirmado",
            "label": "Aguardando retorno do fornecedor",
            "invoice_number": 900003,
            "invoice_qty": Decimal("10"),
            "invoice_unit_cost": Decimal("32.00"),
            "received_qty": Decimal("9"),
            "damaged_qty": Decimal("1"),
            "pending_status": "aguardando_fornecedor",
        },
        {
            "key": "negotiating",
            "order_status": "recebido_parcial",
            "label": "Reposicao em tratativa",
            "invoice_number": 900004,
            "invoice_qty": Decimal("12"),
            "invoice_unit_cost": Decimal("30.94"),
            "received_qty": Decimal("9"),
            "damaged_qty": Decimal("1"),
            "pending_status": "em_tratativa",
        },
        {
            "key": "resolved",
            "order_status": "recebido_total",
            "label": "Pendencia resolvida com credito",
            "invoice_number": 900005,
            "invoice_qty": Decimal("10"),
            "invoice_unit_cost": Decimal("30.94"),
            "received_qty": Decimal("8"),
            "damaged_qty": Decimal("0"),
            "pending_status": "resolvida",
        },
        {
            "key": "canceled",
            "order_status": "cancelado",
            "label": "Pendencia cancelada apos revisao",
            "invoice_number": 900006,
            "invoice_qty": Decimal("11"),
            "invoice_unit_cost": Decimal("34.00"),
            "received_qty": Decimal("9"),
            "damaged_qty": Decimal("0"),
            "pending_status": "cancelada",
        },
        {
            "key": "live_xml",
            "order_status": "confirmado",
            "label": "Pedido reservado para importar e confrontar XML ao vivo",
        },
    ]


def tenant_suffix(tenant_id: str) -> str:
    compact = "".join(character for character in str(tenant_id) if character.isalnum())
    return (compact[:8] or "DEMO").upper()


def invoice_key(tenant_id: str, invoice_number: int) -> str:
    control_number = (zlib.crc32(str(tenant_id).encode("utf-8")) + invoice_number) % 100_000_000
    return (
        "33"
        "2608"
        f"{DEMO_SUPPLIER_CNPJ:0>14}"
        "55"
        "001"
        f"{invoice_number:09d}"
        "1"
        f"{control_number:08d}"
        f"{invoice_number % 10}"
    )


def demo_xml(
    *,
    invoice_number: int,
    access_key: str,
    issued_at: datetime,
    supplier_code: str,
    product_name: str,
    ean: str,
    quantity: Decimal,
    unit_cost: Decimal,
) -> str:
    total = quantity * unit_cost
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!-- DOCUMENTO SINTETICO PARA DEMONSTRACAO DO COREPET. SEM VALOR FISCAL. -->
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
  <NFe><infNFe Id="NFe{access_key}" versao="4.00">
    <ide><cUF>33</cUF><cNF>{invoice_number % 100000000:08d}</cNF><natOp>DEMONSTRACAO COREPET</natOp><mod>55</mod><serie>1</serie><nNF>{invoice_number}</nNF><dhEmi>{issued_at.isoformat()}-03:00</dhEmi><tpNF>1</tpNF><idDest>1</idDest><cMunFG>3300100</cMunFG><tpImp>1</tpImp><tpEmis>1</tpEmis><cDV>{invoice_number % 10}</cDV><tpAmb>2</tpAmb><finNFe>1</finNFe><indFinal>0</indFinal><indPres>0</indPres><procEmi>0</procEmi><verProc>COREPET-DEMO</verProc></ide>
    <emit><CNPJ>{DEMO_SUPPLIER_CNPJ}</CNPJ><xNome>Distribuidora Pet Brasil Demo LTDA</xNome><xFant>Distribuidora Pet Brasil</xFant><enderEmit><xLgr>Rua Demo de Suprimentos</xLgr><nro>100</nro><xBairro>Centro</xBairro><cMun>3300100</cMun><xMun>Angra dos Reis</xMun><UF>RJ</UF><CEP>23900000</CEP></enderEmit><IE>ISENTO</IE><CRT>1</CRT></emit>
    <dest><CNPJ>00000000000000</CNPJ><xNome>COREPET TENANT DEMO</xNome><indIEDest>9</indIEDest></dest>
    <det nItem="1"><prod><cProd>{supplier_code}</cProd><cEAN>{ean}</cEAN><xProd>{product_name}</xProd><NCM>23091000</NCM><CFOP>5102</CFOP><uCom>UN</uCom><qCom>{quantity:.4f}</qCom><vUnCom>{unit_cost:.4f}</vUnCom><vProd>{total:.2f}</vProd><cEANTrib>{ean}</cEANTrib><uTrib>UN</uTrib><qTrib>{quantity:.4f}</qTrib><vUnTrib>{unit_cost:.4f}</vUnTrib><indTot>1</indTot><rastro><nLote>DEMO-LOTE-{invoice_number}</nLote><qLote>{quantity:.3f}</qLote><dFab>2026-07-02</dFab><dVal>2027-07-02</dVal></rastro></prod><imposto><ICMS><ICMSSN102><orig>0</orig><CSOSN>102</CSOSN></ICMSSN102></ICMS><PIS><PISNT><CST>07</CST></PISNT></PIS><COFINS><COFINSNT><CST>07</CST></COFINSNT></COFINS></imposto></det>
    <total><ICMSTot><vBC>0.00</vBC><vICMS>0.00</vICMS><vProd>{total:.2f}</vProd><vFrete>0.00</vFrete><vSeg>0.00</vSeg><vDesc>0.00</vDesc><vII>0.00</vII><vIPI>0.00</vIPI><vPIS>0.00</vPIS><vCOFINS>0.00</vCOFINS><vOutro>0.00</vOutro><vNF>{total:.2f}</vNF></ICMSTot></total>
    <cobr><fat><nFat>DEMO-{invoice_number}</nFat><vOrig>{total:.2f}</vOrig><vDesc>0.00</vDesc><vLiq>{total:.2f}</vLiq></fat></cobr><infAdic><infCpl>ARQUIVO SINTETICO PARA DEMONSTRACAO DO COREPET. SEM VALOR FISCAL.</infCpl></infAdic>
  </infNFe></NFe>
</nfeProc>"""
