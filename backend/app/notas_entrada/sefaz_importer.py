"""Importacao automatica de documentos SEFAZ para notas de entrada."""

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import logging
from uuid import UUID

from defusedxml import ElementTree as ET
from sqlalchemy import case

from ..models import Cliente, User
from ..produtos_models import NotaEntrada, NotaEntradaItem
from ..produtos_compras_models import SefazDocumentoDistribuido
from ..services.sefaz_tenant_config_service import SefazTenantConfigService
from ..tenancy.context import tenant_context
from .fornecedores import criar_fornecedor_automatico
from .produtos import _aplicar_codigos_barras_item_no_produto, encontrar_produto_similar
from .xml_parser import parse_nfe_xml

logger = logging.getLogger(__name__)


def _nome_tag(elemento) -> str:
    return str(elemento.tag).rsplit("}", 1)[-1]


def _filho(elemento, nome: str):
    if elemento is None:
        return None
    return next((filho for filho in elemento if _nome_tag(filho) == nome), None)


def _texto(elemento, nome: str) -> str:
    filho = _filho(elemento, nome)
    return str(filho.text or "").strip() if filho is not None else ""


def _primeiro(elemento, nome: str):
    return next((item for item in elemento.iter() if _nome_tag(item) == nome), None)


def _tipo_documento(schema: str, xml: str) -> str:
    nome = schema.lower()
    if "resnfe" in nome:
        return "resNFe"
    if "procnfe" in nome:
        return "procNFe"
    if "evento" in nome:
        return "evento"
    inicio = xml[:300]
    if "resNFe" in inicio:
        return "resNFe"
    if "nfeProc" in inicio or "procNFe" in inicio:
        return "procNFe"
    if "Evento" in inicio or "evento" in inicio:
        return "evento"
    return "outro"


def _metadados_documento(xml: str, tipo: str) -> dict:
    """Extrai dados para a lista; XML inválido continua preservado no estágio."""
    try:
        raiz = ET.fromstring(xml)
    except Exception:
        return {}

    if tipo == "resNFe":
        base = _primeiro(raiz, "resNFe") or raiz
        chave = _texto(base, "chNFe")
        cnpj = _texto(base, "CNPJ")
        nome = _texto(base, "xNome")
        emissao = _texto(base, "dhEmi")
        valor = _texto(base, "vNF")
        numero = chave[25:34].lstrip("0") if len(chave) == 44 else ""
    elif tipo == "procNFe":
        inf_nfe = _primeiro(raiz, "infNFe")
        ide = _filho(inf_nfe, "ide")
        emitente = _filho(inf_nfe, "emit")
        icms_tot = _filho(_filho(inf_nfe, "total"), "ICMSTot")
        chave = (
            str(inf_nfe.get("Id", "")).removeprefix("NFe")
            if inf_nfe is not None
            else ""
        )
        cnpj = _texto(emitente, "CNPJ")
        nome = _texto(emitente, "xNome")
        emissao = _texto(ide, "dhEmi") or _texto(ide, "dEmi")
        valor = _texto(icms_tot, "vNF")
        numero = _texto(ide, "nNF")
    else:
        chave = _texto(_primeiro(raiz, "infEvento"), "chNFe") or _texto(raiz, "chNFe")
        cnpj = nome = emissao = valor = numero = ""

    if len(chave) != 44:
        chave = ""
    try:
        data_emissao = (
            datetime.fromisoformat(emissao.replace("Z", "+00:00")) if emissao else None
        )
    except ValueError:
        data_emissao = None
    try:
        valor_total = Decimal(valor) if valor else None
    except InvalidOperation:
        valor_total = None

    return {
        "chave_acesso": chave or None,
        "emitente_cnpj": cnpj or None,
        "emitente_nome": nome or None,
        "numero_nota": numero or None,
        "data_emissao": data_emissao,
        "valor_total": valor_total,
    }


def _cnpj_destinatario(xml: str) -> str:
    """Le o destinatario da NF-e, sem confundir com transportador ou autXML."""
    raiz = ET.fromstring(xml)
    inf_nfe = _primeiro(raiz, "infNFe")
    destinatario = _filho(inf_nfe, "dest")
    return "".join(ch for ch in _texto(destinatario, "CNPJ") if ch.isdigit())


def _staging_documentos(
    docs: list[dict], tenant_uuid: UUID, db
) -> list[SefazDocumentoDistribuido]:
    """Confirma o lote inteiro no banco antes de importar qualquer nota."""
    encontrados: dict[str, SefazDocumentoDistribuido] = {}
    try:
        for doc in docs:
            nsu = str(doc.get("nsu") or "").strip()
            schema = str(doc.get("schema") or "").strip()
            xml = doc.get("xml")
            if (
                not nsu.isdigit()
                or len(nsu) > 15
                or not schema
                or not isinstance(xml, str)
                or not xml.strip()
            ):
                raise ValueError(
                    f"Documento SEFAZ inválido para staging: NSU {nsu or '-'}"
                )
            nsu = nsu.zfill(15)
            existente = encontrados.get(nsu)
            if existente is None:
                existente = (
                    db.query(SefazDocumentoDistribuido)
                    .filter(
                        SefazDocumentoDistribuido.tenant_id == tenant_uuid,
                        SefazDocumentoDistribuido.nsu == nsu,
                    )
                    .first()
                )
            if existente is not None:
                if existente.raw_xml != xml or existente.schema != schema:
                    raise ValueError(f"NSU {nsu} já existe com conteúdo diferente")
                encontrados[nsu] = existente
                continue

            tipo = _tipo_documento(schema, xml)
            status = {
                "resNFe": "aguardando_xml",
                "procNFe": "pendente_importacao",
                "evento": "evento_recebido",
            }.get(tipo, "outro_documento")
            novo = SefazDocumentoDistribuido(
                tenant_id=tenant_uuid,
                nsu=nsu,
                schema=schema,
                tipo=tipo,
                raw_xml=xml,
                status=status,
                **_metadados_documento(xml, tipo),
            )
            db.add(novo)
            encontrados[nsu] = novo
        db.commit()
    except Exception:
        db.rollback()
        raise
    return list(encontrados.values())


def _atualizar_resumos_da_chave(db, documento: SefazDocumentoDistribuido) -> None:
    if not documento.chave_acesso or documento.status not in {
        "importada",
        "duplicada",
        "saida_descartada",
        "nao_destinada",
    }:
        return
    resumos = (
        db.query(SefazDocumentoDistribuido)
        .filter(
            SefazDocumentoDistribuido.tenant_id == documento.tenant_id,
            SefazDocumentoDistribuido.chave_acesso == documento.chave_acesso,
            SefazDocumentoDistribuido.tipo == "resNFe",
            SefazDocumentoDistribuido.status == "aguardando_xml",
        )
        .all()
    )
    for resumo in resumos:
        resumo.status = (
            "importada"
            if documento.status in {"importada", "duplicada"}
            else documento.status
        )
        resumo.nota_entrada_id = documento.nota_entrada_id
        resumo.processado_em = datetime.now(timezone.utc)


def _processar_documento_staged(
    db, tenant_id_str: str, documento: SefazDocumentoDistribuido
) -> dict:
    if documento.tipo != "procNFe":
        return {
            "importadas": 0,
            "duplicadas": 0,
            "erros": 0,
            "saidas_descartadas": 0,
            "nao_destinadas": 0,
        }
    if documento.status in {
        "importada",
        "duplicada",
        "saida_descartada",
        "nao_destinada",
    }:
        return {
            "importadas": 0,
            "duplicadas": int(documento.status in {"importada", "duplicada"}),
            "erros": 0,
            "saidas_descartadas": int(documento.status == "saida_descartada"),
            "nao_destinadas": int(documento.status == "nao_destinada"),
        }

    try:
        resultado = _importar_docs_sefaz_scoped(
            [
                {
                    "nsu": documento.nsu,
                    "schema": documento.schema,
                    "xml": documento.raw_xml,
                }
            ],
            tenant_id_str,
            db,
        )
        if resultado.get("importadas"):
            documento.status = "importada"
        elif resultado.get("duplicadas"):
            documento.status = "duplicada"
        elif resultado.get("saidas_descartadas"):
            documento.status = "saida_descartada"
        elif resultado.get("nao_destinadas"):
            documento.status = "nao_destinada"
        else:
            documento.status = "erro_processamento"
        if documento.status in {"importada", "duplicada"} and documento.chave_acesso:
            nota = (
                db.query(NotaEntrada)
                .filter(
                    NotaEntrada.tenant_id == documento.tenant_id,
                    NotaEntrada.chave_acesso == documento.chave_acesso,
                )
                .first()
            )
            documento.nota_entrada_id = nota.id if nota else None
        documento.erro_mensagem = (
            "Falha ao importar o XML; documento preservado para nova tentativa."
            if documento.status == "erro_processamento"
            else None
        )
        documento.processado_em = datetime.now(timezone.utc)
        _atualizar_resumos_da_chave(db, documento)
        db.commit()
        return resultado
    except Exception as exc:
        db.rollback()
        documento.status = "erro_processamento"
        documento.erro_mensagem = (
            "Falha no processamento local; XML preservado para nova tentativa."
        )
        documento.processado_em = datetime.now(timezone.utc)
        db.commit()
        logger.warning(
            "[SEFAZ] NSU %s: XML preservado, falha no processamento (%s)",
            documento.nsu,
            type(exc).__name__,
        )
        return {
            "importadas": 0,
            "duplicadas": 0,
            "erros": 1,
            "saidas_descartadas": 0,
            "nao_destinadas": 0,
        }


def importar_documentos_distribuicao(db, tenant_id_str: str, docs: list[dict]) -> dict:
    """Salva todos os docZip; só então tenta importar os XML completos."""
    tenant_uuid = UUID(tenant_id_str)
    with tenant_context(tenant_uuid):
        staged = _staging_documentos(docs, tenant_uuid, db)
        resultado = {
            "staging_salvo": True,
            "documentos_salvos": len(docs),
            "importadas": 0,
            "duplicadas": 0,
            "erros": 0,
            "saidas_descartadas": 0,
            "nao_destinadas": 0,
        }
        for documento in staged:
            parcial = _processar_documento_staged(db, tenant_id_str, documento)
            for campo in (
                "importadas",
                "duplicadas",
                "erros",
                "saidas_descartadas",
                "nao_destinadas",
            ):
                resultado[campo] += parcial.get(campo, 0)
        return resultado


def reprocessar_documentos_sefaz_pendentes(
    db, tenant_id_str: str, limite: int = 100
) -> dict:
    """Repete localmente imports falhos sem consultar a SEFAZ nem alterar o NSU."""
    tenant_uuid = UUID(tenant_id_str)
    with tenant_context(tenant_uuid):
        pendentes = (
            db.query(SefazDocumentoDistribuido)
            .filter(
                SefazDocumentoDistribuido.tenant_id == tenant_uuid,
                SefazDocumentoDistribuido.tipo == "procNFe",
                SefazDocumentoDistribuido.status.in_(
                    ("pendente_importacao", "erro_processamento")
                ),
            )
            # XML ainda nao tentado tem prioridade. Erros giram pelo horario da
            # ultima tentativa para que um erro permanente nao bloqueie os demais.
            .order_by(
                case(
                    (SefazDocumentoDistribuido.status == "pendente_importacao", 0),
                    else_=1,
                ),
                SefazDocumentoDistribuido.processado_em,
                SefazDocumentoDistribuido.nsu,
            )
            .limit(max(1, min(limite, 500)))
            .all()
        )
        resultado = {
            "importadas": 0,
            "duplicadas": 0,
            "erros": 0,
            "saidas_descartadas": 0,
            "nao_destinadas": 0,
        }
        for documento in pendentes:
            parcial = _processar_documento_staged(db, tenant_id_str, documento)
            for campo in resultado:
                resultado[campo] += parcial.get(campo, 0)
        return resultado


def importar_docs_sefaz(docs: list, tenant_id_str: str, db) -> dict:
    if docs:
        return importar_documentos_distribuicao(db, tenant_id_str, docs)
    try:
        tenant_uuid = UUID(tenant_id_str)
    except ValueError:
        logger.warning(f"[SEFAZ] tenant_id invalido: {tenant_id_str}")
        return {
            "importadas": 0,
            "duplicadas": 0,
            "erros": len(docs),
            "saidas_descartadas": 0,
        }

    with tenant_context(tenant_uuid):
        return _importar_docs_sefaz_scoped(docs, tenant_id_str, db)


def _importar_docs_sefaz_scoped(docs: list, tenant_id_str: str, db) -> dict:
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
    nao_destinadas = 0

    # Buscar CNPJ do tenant na config SEFAZ para identificar NF de saida
    tenant_cnpj = ""
    try:
        cfg_tenant = SefazTenantConfigService.load_config(UUID(tenant_id_str))
        tenant_cnpj = "".join(
            ch for ch in str(cfg_tenant.get("cnpj", "")) if ch.isdigit()
        )
    except Exception as exc_cfg:
        logger.warning(
            f"[SEFAZ] Nao foi possivel carregar CNPJ do tenant {tenant_id_str}: {exc_cfg}"
        )

    # Buscar um usuario sistema do tenant para associar as notas
    user_sistema = (
        db.query(User).filter(User.tenant_id == tenant_id_str).order_by(User.id).first()
    )

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

        # A distribuicao tambem pode incluir documentos em que o interessado
        # figura como transportador ou autorizado no autXML. So notas cujo
        # destinatario e o CNPJ configurado pertencem a compras deste tenant.
        if len(tenant_cnpj) != 14:
            logger.warning(
                "[SEFAZ] NSU %s: CNPJ do tenant ausente ou invalido; importacao pendente",
                nsu,
            )
            erros += 1
            continue
        try:
            destinatario_cnpj = _cnpj_destinatario(xml_str)
        except Exception as exc:
            logger.warning(
                "[SEFAZ] NSU %s: nao foi possivel ler destinatario (%s)",
                nsu,
                type(exc).__name__,
            )
            erros += 1
            continue
        if destinatario_cnpj != tenant_cnpj:
            nao_destinadas += 1
            continue

        # Descartar NF de saida (emitida pela propria empresa)
        # emit.CNPJ == tenant CNPJ significa que a empresa emitiu essa NF (saida/venda)
        if tenant_cnpj:
            cnpj_emitente = "".join(
                ch for ch in str(dados_nfe.get("fornecedor_cnpj", "")) if ch.isdigit()
            )
            if cnpj_emitente and cnpj_emitente == tenant_cnpj:
                logger.debug(
                    f"[SEFAZ] NSU {nsu}: NF de saida descartada (emitente == tenant)"
                )
                saidas_descartadas += 1
                continue

        chave = dados_nfe.get("chave_acesso", "")
        if not chave:
            logger.warning(f"[SEFAZ] NSU {nsu}: chave de acesso nao encontrada no XML")
            erros += 1
            continue

        # Verificar se ja existe
        existente = (
            db.query(NotaEntrada)
            .filter(
                NotaEntrada.tenant_id == tenant_id_str,
                NotaEntrada.chave_acesso == chave,
            )
            .first()
        )
        if existente:
            duplicadas += 1
            continue

        try:
            # Buscar ou criar fornecedor
            fornecedor = (
                db.query(Cliente)
                .filter(
                    Cliente.cnpj == dados_nfe["fornecedor_cnpj"],
                    Cliente.tenant_id == tenant_id_str,
                    Cliente.ativo.is_(True),
                )
                .first()
            )

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
                    cst_icms=item_data.get("cst_icms"),
                    icms_st=item_data.get("icms_st"),
                    icms_base_st=item_data.get("icms_base_st"),
                    icms_valor_st=item_data.get("icms_valor_st"),
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
                    _aplicar_codigos_barras_item_no_produto(produto, item)
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
            logger.warning(
                f"[SEFAZ] NSU {nsu}: erro ao salvar nota {chave[:10]}... - {exc}"
            )
            erros += 1

    return {
        "importadas": importadas,
        "duplicadas": duplicadas,
        "erros": erros,
        "saidas_descartadas": saidas_descartadas,
        "nao_destinadas": nao_destinadas,
    }
