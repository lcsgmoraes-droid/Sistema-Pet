"""Parser de XML NF-e para notas de entrada."""
from datetime import date, datetime, timedelta
import xml.etree.ElementTree as ET

from .conferencia import _extrair_lote_validade_info_adicional


def parse_nfe_xml(xml_content: str) -> dict:
    """
    Parse de XML de NF-e (padrão SEFAZ)
    Retorna dados estruturados da nota
    """
    try:
        root = ET.fromstring(xml_content)

        # Namespace do XML da NF-e
        ns = {"nfe": "http://www.portalfiscal.inf.br/nfe"}

        # Buscar informações principais
        inf_nfe = root.find(".//nfe:infNFe", ns)
        if not inf_nfe:
            raise ValueError("Tag infNFe não encontrada no XML")

        # Chave de acesso
        chave_acesso = inf_nfe.get("Id", "").replace("NFe", "")

        # Identificação da nota
        ide = inf_nfe.find(".//nfe:ide", ns)
        numero_nota = ide.find("nfe:nNF", ns).text if ide.find("nfe:nNF", ns) is not None else ""
        serie = ide.find("nfe:serie", ns).text if ide.find("nfe:serie", ns) is not None else "1"
        data_emissao_str = (
            ide.find("nfe:dhEmi", ns).text
            if ide.find("nfe:dhEmi", ns) is not None
            else ide.find("nfe:dEmi", ns).text
        )
        # Usar date.fromisoformat para evitar problema de timezone (perda de 1 dia)
        data_emissao = date.fromisoformat(
            data_emissao_str.replace("Z", "+00:00").split("T")[0]
        )

        # Emitente (fornecedor) - Dados completos
        emit = inf_nfe.find(".//nfe:emit", ns)
        fornecedor_cnpj = (
            emit.find("nfe:CNPJ", ns).text if emit.find("nfe:CNPJ", ns) is not None else ""
        )
        fornecedor_nome = (
            emit.find("nfe:xNome", ns).text if emit.find("nfe:xNome", ns) is not None else ""
        )
        fornecedor_fantasia = (
            emit.find("nfe:xFant", ns).text if emit.find("nfe:xFant", ns) is not None else ""
        )
        fornecedor_ie = (
            emit.find("nfe:IE", ns).text if emit.find("nfe:IE", ns) is not None else ""
        )

        # Endereço do fornecedor
        ender_emit = emit.find("nfe:enderEmit", ns)
        fornecedor_endereco = ""
        fornecedor_numero = ""
        fornecedor_bairro = ""
        fornecedor_cidade = ""
        fornecedor_uf = ""
        fornecedor_cep = ""
        fornecedor_telefone = ""

        if ender_emit is not None:
            fornecedor_endereco = (
                ender_emit.find("nfe:xLgr", ns).text
                if ender_emit.find("nfe:xLgr", ns) is not None
                else ""
            )
            fornecedor_numero = (
                ender_emit.find("nfe:nro", ns).text
                if ender_emit.find("nfe:nro", ns) is not None
                else ""
            )
            fornecedor_bairro = (
                ender_emit.find("nfe:xBairro", ns).text
                if ender_emit.find("nfe:xBairro", ns) is not None
                else ""
            )
            fornecedor_cidade = (
                ender_emit.find("nfe:xMun", ns).text
                if ender_emit.find("nfe:xMun", ns) is not None
                else ""
            )
            fornecedor_uf = (
                ender_emit.find("nfe:UF", ns).text
                if ender_emit.find("nfe:UF", ns) is not None
                else ""
            )
            fornecedor_cep = (
                ender_emit.find("nfe:CEP", ns).text
                if ender_emit.find("nfe:CEP", ns) is not None
                else ""
            )
            fornecedor_telefone = (
                ender_emit.find("nfe:fone", ns).text
                if ender_emit.find("nfe:fone", ns) is not None
                else ""
            )

        # Totais
        total = inf_nfe.find(".//nfe:total/nfe:ICMSTot", ns)
        valor_produtos = (
            float(total.find("nfe:vProd", ns).text)
            if total.find("nfe:vProd", ns) is not None
            else 0
        )
        valor_frete = (
            float(total.find("nfe:vFrete", ns).text)
            if total.find("nfe:vFrete", ns) is not None
            else 0
        )
        valor_desconto = (
            float(total.find("nfe:vDesc", ns).text)
            if total.find("nfe:vDesc", ns) is not None
            else 0
        )
        valor_total = (
            float(total.find("nfe:vNF", ns).text)
            if total.find("nfe:vNF", ns) is not None
            else 0
        )

        # Itens
        itens = []
        det_list = inf_nfe.findall(".//nfe:det", ns)

        for idx, det in enumerate(det_list, start=1):
            prod = det.find("nfe:prod", ns)

            codigo_produto = (
                prod.find("nfe:cProd", ns).text
                if prod.find("nfe:cProd", ns) is not None
                else ""
            )
            descricao = (
                prod.find("nfe:xProd", ns).text if prod.find("nfe:xProd", ns) is not None else ""
            )
            ncm = prod.find("nfe:NCM", ns).text if prod.find("nfe:NCM", ns) is not None else ""
            cest = prod.find("nfe:CEST", ns).text if prod.find("nfe:CEST", ns) is not None else ""
            cfop = prod.find("nfe:CFOP", ns).text if prod.find("nfe:CFOP", ns) is not None else ""
            origem = prod.find("nfe:orig", ns).text if prod.find("nfe:orig", ns) is not None else "0"
            unidade = prod.find("nfe:uCom", ns).text if prod.find("nfe:uCom", ns) is not None else "UN"
            quantidade = (
                float(prod.find("nfe:qCom", ns).text)
                if prod.find("nfe:qCom", ns) is not None
                else 0
            )
            valor_unitario = (
                float(prod.find("nfe:vUnCom", ns).text)
                if prod.find("nfe:vUnCom", ns) is not None
                else 0
            )
            valor_total_item = (
                float(prod.find("nfe:vProd", ns).text)
                if prod.find("nfe:vProd", ns) is not None
                else 0
            )
            ean = prod.find("nfe:cEAN", ns).text if prod.find("nfe:cEAN", ns) is not None else ""
            ean_tributario = (
                prod.find("nfe:cEANTrib", ns).text
                if prod.find("nfe:cEANTrib", ns) is not None
                else ""
            )

            # Extrair lote e validade da tag <rastro> (rastreabilidade)
            lote = ""
            data_validade = None

            # Buscar tag de rastreabilidade
            rastro = prod.find("nfe:rastro", ns)
            if rastro is not None:
                # Número do lote
                lote_elem = rastro.find("nfe:nLote", ns)
                if lote_elem is not None:
                    lote = lote_elem.text

                # Data de validade
                validade_elem = rastro.find("nfe:dVal", ns)
                if validade_elem is not None:
                    try:
                        data_validade = datetime.strptime(validade_elem.text, "%Y-%m-%d").date()
                    except Exception:
                        pass

            # Extrair alíquotas de impostos
            aliquota_icms = 0.0
            aliquota_pis = 0.0
            aliquota_cofins = 0.0

            # Buscar impostos do item
            imposto = det.find("nfe:imposto", ns)
            if imposto is not None:
                # ICMS - pode estar em várias tags (ICMS00, ICMS10, ICMS20, etc)
                icms_group = imposto.find("nfe:ICMS", ns)
                if icms_group is not None:
                    # Tentar várias possibilidades de tag ICMS
                    for icms_tag in [
                        "ICMS00",
                        "ICMS10",
                        "ICMS20",
                        "ICMS30",
                        "ICMS40",
                        "ICMS51",
                        "ICMS60",
                        "ICMS70",
                        "ICMS90",
                        "ICMSSN101",
                        "ICMSSN102",
                        "ICMSSN201",
                        "ICMSSN202",
                        "ICMSSN500",
                        "ICMSSN900",
                    ]:
                        icms_elem = icms_group.find(f"nfe:{icms_tag}", ns)
                        if icms_elem is not None:
                            picms = icms_elem.find("nfe:pICMS", ns)
                            if picms is not None:
                                try:
                                    aliquota_icms = float(picms.text)
                                    break
                                except Exception:
                                    pass

                # PIS
                pis_group = imposto.find("nfe:PIS", ns)
                if pis_group is not None:
                    # PISAliq ou PISOutr
                    for pis_tag in ["PISAliq", "PISOutr", "PISNT"]:
                        pis_elem = pis_group.find(f"nfe:{pis_tag}", ns)
                        if pis_elem is not None:
                            ppis = pis_elem.find("nfe:pPIS", ns)
                            if ppis is not None:
                                try:
                                    aliquota_pis = float(ppis.text)
                                    break
                                except Exception:
                                    pass

                # COFINS
                cofins_group = imposto.find("nfe:COFINS", ns)
                if cofins_group is not None:
                    # COFINSAliq ou COFINSOutr
                    for cofins_tag in ["COFINSAliq", "COFINSOutr", "COFINSNT"]:
                        cofins_elem = cofins_group.find(f"nfe:{cofins_tag}", ns)
                        if cofins_elem is not None:
                            pcofins = cofins_elem.find("nfe:pCOFINS", ns)
                            if pcofins is not None:
                                try:
                                    aliquota_cofins = float(pcofins.text)
                                    break
                                except Exception:
                                    pass

            # Se nao encontrar em rastro, tentar informacoes adicionais do item.
            # Na NF-e, infAdProd costuma ser filho de <det>, nao de <prod>.
            if not lote or not data_validade:
                inf_ad_prod = det.find("nfe:infAdProd", ns)
                if inf_ad_prod is None:
                    inf_ad_prod = prod.find("nfe:infAdProd", ns)

                if inf_ad_prod is not None and inf_ad_prod.text:
                    lote_info, validade_info = _extrair_lote_validade_info_adicional(
                        inf_ad_prod.text
                    )
                    if not lote and lote_info:
                        lote = lote_info
                    if not data_validade and validade_info:
                        data_validade = validade_info

            itens.append(
                {
                    "numero_item": idx,
                    "codigo_produto": codigo_produto,
                    "descricao": descricao,
                    "ncm": ncm,
                    "cest": cest,
                    "cfop": cfop,
                    "origem": origem,
                    "aliquota_icms": aliquota_icms,
                    "aliquota_pis": aliquota_pis,
                    "aliquota_cofins": aliquota_cofins,
                    "unidade": unidade,
                    "quantidade": quantidade,
                    "valor_unitario": valor_unitario,
                    "valor_total": valor_total_item,
                    "ean": ean,
                    "ean_tributario": ean_tributario,
                    "lote": lote,
                    "data_validade": data_validade,
                }
            )

        # Duplicatas (Cobranças) - FASE 4: Para gerar contas a pagar
        duplicatas = []
        cobr = inf_nfe.find(".//nfe:cobr", ns)
        if cobr is not None:
            dup_list = cobr.findall(".//nfe:dup", ns)
            for dup in dup_list:
                numero_dup = (
                    dup.find("nfe:nDup", ns).text
                    if dup.find("nfe:nDup", ns) is not None
                    else ""
                )
                vencimento_str = (
                    dup.find("nfe:dVenc", ns).text
                    if dup.find("nfe:dVenc", ns) is not None
                    else ""
                )
                valor_dup = (
                    float(dup.find("nfe:vDup", ns).text)
                    if dup.find("nfe:vDup", ns) is not None
                    else 0
                )

                # Parse data de vencimento (formato YYYY-MM-DD) - usar date para evitar problema de timezone
                vencimento = (
                    date.fromisoformat(vencimento_str)
                    if vencimento_str
                    else (datetime.now() + timedelta(days=30)).date()
                )

                duplicatas.append(
                    {
                        "numero": numero_dup,
                        "vencimento": vencimento,
                        "valor": valor_dup,
                    }
                )

        return {
            "chave_acesso": chave_acesso,
            "numero_nota": numero_nota,
            "serie": serie,
            "data_emissao": data_emissao,
            "fornecedor_cnpj": fornecedor_cnpj,
            "fornecedor_nome": fornecedor_nome,
            "fornecedor_fantasia": fornecedor_fantasia,
            "fornecedor_ie": fornecedor_ie,
            "fornecedor_endereco": fornecedor_endereco,
            "fornecedor_numero": fornecedor_numero,
            "fornecedor_bairro": fornecedor_bairro,
            "fornecedor_cidade": fornecedor_cidade,
            "fornecedor_uf": fornecedor_uf,
            "fornecedor_cep": fornecedor_cep,
            "fornecedor_telefone": fornecedor_telefone,
            "valor_produtos": valor_produtos,
            "valor_frete": valor_frete,
            "valor_desconto": valor_desconto,
            "valor_total": valor_total,
            "itens": itens,
            "duplicatas": duplicatas,
        }

    except ET.ParseError as e:
        raise ValueError(f"Erro ao fazer parse do XML: {str(e)}")
    except Exception as e:
        raise ValueError(f"Erro ao processar XML: {str(e)}")
