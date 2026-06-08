"""Importacao automatica de documentos SEFAZ para notas de entrada."""
from datetime import datetime
import logging
from uuid import UUID

from ..models import Cliente, User
from ..produtos_models import NotaEntrada, NotaEntradaItem
from ..services.sefaz_tenant_config_service import SefazTenantConfigService
from .fornecedores import criar_fornecedor_automatico
from .produtos import encontrar_produto_similar
from .xml_parser import parse_nfe_xml

logger = logging.getLogger(__name__)


def importar_docs_sefaz(docs: list, tenant_id_str: str, db) -> dict:
    """
    Importa documentos retornados pela SEFAZ para a tabela notas_entrada.

    Chamada pelo loop de sincronizacao automatica no main.py.
    Cada `doc` e um dict com chaves: nsu, schema, xml.

    So importa documentos com schema procNFe (XML completo).
    Documentos resNFe (resumo) sao ignorados pois nao tem itens.
    Documentos onde o CNPJ emitente == CNPJ do tenant (NF de saida) sao descartados.

    Retorna: {"importadas": N, "duplicadas": N, "erros": N, "saidas_descartadas": N}
    """
    importadas = 0
    duplicadas = 0
    erros = 0
    saidas_descartadas = 0

    # Buscar CNPJ do tenant na config SEFAZ para identificar NF de saida
    tenant_cnpj = ""
    try:
        cfg_tenant = SefazTenantConfigService.load_config(UUID(tenant_id_str))
        tenant_cnpj = "".join(ch for ch in str(cfg_tenant.get("cnpj", "")) if ch.isdigit())
    except Exception as exc_cfg:
        logger.warning(
            f"[SEFAZ] Nao foi possivel carregar CNPJ do tenant {tenant_id_str}: {exc_cfg}"
        )

    # Buscar um usuario sistema do tenant para associar as notas
    try:
        UUID(tenant_id_str)
    except ValueError:
        logger.warning(f"[SEFAZ] tenant_id invalido: {tenant_id_str}")
        return {"importadas": 0, "duplicadas": 0, "erros": len(docs), "saidas_descartadas": 0}

    user_sistema = db.query(User).filter(
        User.tenant_id == tenant_id_str
    ).order_by(User.id).first()

    if not user_sistema:
        logger.warning(f"[SEFAZ] Nenhum usuario encontrado para tenant {tenant_id_str}")
        return {"importadas": 0, "duplicadas": 0, "erros": len(docs)}

    for doc in docs:
        schema = doc.get("schema", "")
        xml_str = doc.get("xml", "")
        nsu = doc.get("nsu", "")

        # So processa XML completo de NF-e (procNFe) - resNFe nao tem itens nem XML da nota
        if "procNFe" not in schema and "nfeProc" not in xml_str[:200]:
            logger.debug(f"[SEFAZ] NSU {nsu} ignorado (schema: {schema})")
            continue

        try:
            dados_nfe = parse_nfe_xml(xml_str)
        except Exception as exc:
            logger.warning(f"[SEFAZ] NSU {nsu}: erro no parse do XML - {exc}")
            erros += 1
            continue

        # Descartar NF de saida (emitida pela propria empresa)
        # emit.CNPJ == tenant CNPJ significa que a empresa emitiu essa NF (saida/venda)
        if tenant_cnpj:
            cnpj_emitente = "".join(
                ch for ch in str(dados_nfe.get("fornecedor_cnpj", "")) if ch.isdigit()
            )
            if cnpj_emitente and cnpj_emitente == tenant_cnpj:
                logger.debug(f"[SEFAZ] NSU {nsu}: NF de saida descartada (emitente == tenant)")
                saidas_descartadas += 1
                continue

        chave = dados_nfe.get("chave_acesso", "")
        if not chave:
            logger.warning(f"[SEFAZ] NSU {nsu}: chave de acesso nao encontrada no XML")
            erros += 1
            continue

        # Verificar se ja existe
        existente = db.query(NotaEntrada).filter(
            NotaEntrada.chave_acesso == chave
        ).first()
        if existente:
            duplicadas += 1
            continue

        try:
            # Buscar ou criar fornecedor
            fornecedor = db.query(Cliente).filter(
                Cliente.cnpj == dados_nfe["fornecedor_cnpj"],
                Cliente.tenant_id == tenant_id_str,
                Cliente.ativo == True
            ).first()

            if not fornecedor:
                fornecedor, _ = criar_fornecedor_automatico(
                    dados_nfe, db, user_sistema, tenant_id_str
                )

            # Criar nota com status pendente
            nota = NotaEntrada(
                numero_nota=dados_nfe["numero_nota"],
                serie=dados_nfe["serie"],
                chave_acesso=chave,
                fornecedor_cnpj=dados_nfe["fornecedor_cnpj"],
                fornecedor_nome=dados_nfe["fornecedor_nome"],
                fornecedor_id=fornecedor.id if fornecedor else None,
                data_emissao=dados_nfe["data_emissao"],
                data_entrada=datetime.utcnow(),
                valor_produtos=dados_nfe["valor_produtos"],
                valor_frete=dados_nfe["valor_frete"],
                valor_desconto=dados_nfe["valor_desconto"],
                valor_total=dados_nfe["valor_total"],
                xml_content=xml_str,
                status="pendente",
                user_id=user_sistema.id,
                tenant_id=tenant_id_str,
            )
            db.add(nota)
            db.flush()

            # Criar itens com matching automatico
            vinculados = 0
            nao_vinculados = 0
            for item_data in dados_nfe["itens"]:
                produto, confianca, _, _, _ = encontrar_produto_similar(
                    item_data["descricao"],
                    item_data["codigo_produto"],
                    db,
                    tenant_id=tenant_id_str,
                    fornecedor_id=fornecedor.id if fornecedor else None,
                    ean=item_data.get("ean"),
                    ean_tributario=item_data.get("ean_tributario"),
                )
                item = NotaEntradaItem(
                    nota_entrada_id=nota.id,
                    numero_item=item_data["numero_item"],
                    codigo_produto=item_data["codigo_produto"],
                    descricao=item_data["descricao"],
                    ncm=item_data.get("ncm"),
                    cest=item_data.get("cest"),
                    cfop=item_data.get("cfop"),
                    origem=item_data.get("origem", "0"),
                    aliquota_icms=item_data.get("aliquota_icms", 0),
                    aliquota_pis=item_data.get("aliquota_pis", 0),
                    aliquota_cofins=item_data.get("aliquota_cofins", 0),
                    unidade=item_data.get("unidade", "UN"),
                    quantidade=item_data["quantidade"],
                    valor_unitario=item_data["valor_unitario"],
                    valor_total=item_data["valor_total"],
                    ean=item_data.get("ean"),
                    ean_tributario=item_data.get("ean_tributario"),
                    lote=item_data.get("lote"),
                    data_validade=item_data.get("data_validade"),
                    produto_id=produto.id if produto else None,
                    vinculado=bool(produto),
                    confianca_vinculo=confianca if produto else 0,
                    status="vinculado" if produto else "nao_vinculado",
                    tenant_id=tenant_id_str,
                )
                db.add(item)
                if produto:
                    vinculados += 1
                else:
                    nao_vinculados += 1

            nota.produtos_vinculados = vinculados
            nota.produtos_nao_vinculados = nao_vinculados
            db.commit()

            importadas += 1
            logger.info(
                f"[SEFAZ] NF-e {dados_nfe['numero_nota']} importada "
                f"(chave: {chave[:10]}..., {vinculados} vinculados, {nao_vinculados} nao vinculados)"
            )

        except Exception as exc:
            db.rollback()
            logger.warning(f"[SEFAZ] NSU {nsu}: erro ao salvar nota {chave[:10]}... - {exc}")
            erros += 1

    return {
        "importadas": importadas,
        "duplicadas": duplicadas,
        "erros": erros,
        "saidas_descartadas": saidas_descartadas,
    }
