"""Servicos compartilhados pelas rotas de upload de notas de entrada."""

from dataclasses import dataclass
from datetime import UTC, datetime
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models import Cliente
from app.notas_entrada.fornecedores import criar_fornecedor_automatico
from app.notas_entrada.produtos import (
    _aplicar_codigos_barras_item_no_produto,
    encontrar_produto_similar,
    gerar_sku_automatico,
)
from app.produtos_models import NotaEntrada, NotaEntradaItem

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EntradaComItens:
    nota: NotaEntrada
    vinculados: int
    nao_vinculados: int
    produtos_reativados: int


def agora_utc_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def buscar_nota_por_chave(db: Session, chave_acesso: str) -> NotaEntrada | None:
    return (
        db.query(NotaEntrada).filter(NotaEntrada.chave_acesso == chave_acesso).first()
    )


def buscar_ou_criar_fornecedor_nfe(
    db: Session,
    *,
    dados_nfe: dict[str, Any],
    current_user: Any,
    tenant_id: int,
    somente_ativos: bool,
) -> tuple[Cliente | None, bool]:
    query = db.query(Cliente).filter(
        Cliente.cnpj == dados_nfe["fornecedor_cnpj"],
        Cliente.tenant_id == tenant_id,
    )
    if somente_ativos:
        query = query.filter(Cliente.ativo)

    fornecedor = query.first()
    if fornecedor:
        logger.info(
            "Fornecedor encontrado: %s (ID: %s)", fornecedor.nome, fornecedor.id
        )
        return fornecedor, False

    logger.warning("Fornecedor nao cadastrado; criando automaticamente")
    return criar_fornecedor_automatico(dados_nfe, db, current_user, tenant_id)


def salvar_entrada_com_itens(
    db: Session,
    *,
    dados_nfe: dict[str, Any],
    xml_str: str,
    fornecedor: Cliente | None,
    current_user: Any,
    tenant_id: int,
    origem_documento: str,
    campos_xml_obrigatorios: bool,
) -> EntradaComItens:
    nota = _criar_nota_entrada(
        dados_nfe=dados_nfe,
        xml_str=xml_str,
        fornecedor=fornecedor,
        current_user=current_user,
        tenant_id=tenant_id,
    )
    db.add(nota)
    db.flush()

    vinculados, nao_vinculados, produtos_reativados = _criar_itens_nota(
        db,
        dados_nfe=dados_nfe,
        nota=nota,
        fornecedor=fornecedor,
        current_user=current_user,
        tenant_id=tenant_id,
        origem_documento=origem_documento,
        campos_xml_obrigatorios=campos_xml_obrigatorios,
    )

    nota.produtos_vinculados = vinculados
    nota.produtos_nao_vinculados = nao_vinculados

    db.commit()
    db.refresh(nota)

    if produtos_reativados > 0:
        logger.info(
            "Produtos inativos reativados durante importacao de nota: %s",
            produtos_reativados,
        )

    logger.info(
        "Nota %s processada: %s vinculados, %s nao vinculados",
        nota.numero_nota,
        vinculados,
        nao_vinculados,
    )

    return EntradaComItens(
        nota=nota,
        vinculados=vinculados,
        nao_vinculados=nao_vinculados,
        produtos_reativados=produtos_reativados,
    )


def montar_resposta_upload(
    *,
    entrada: EntradaComItens,
    dados_nfe: dict[str, Any],
    message: str,
    fornecedor_criado_automaticamente: bool,
    origem_documento: str | None = None,
    avisos: list[str] | None = None,
) -> dict[str, Any]:
    nota = entrada.nota
    payload: dict[str, Any] = {"message": message}
    if origem_documento:
        payload["origem_documento"] = origem_documento

    payload.update(
        {
            "nota_id": nota.id,
            "numero_nota": nota.numero_nota,
            "chave_acesso": nota.chave_acesso,
            "fornecedor": nota.fornecedor_nome,
            "fornecedor_id": nota.fornecedor_id,
            "fornecedor_criado_automaticamente": fornecedor_criado_automaticamente,
            "valor_total": nota.valor_total,
            "itens_total": len(dados_nfe["itens"]),
            "produtos_vinculados": entrada.vinculados,
            "produtos_nao_vinculados": entrada.nao_vinculados,
            "produtos_reativados": entrada.produtos_reativados,
        }
    )
    if avisos:
        payload["avisos"] = avisos
    return payload


def _criar_nota_entrada(
    *,
    dados_nfe: dict[str, Any],
    xml_str: str,
    fornecedor: Cliente | None,
    current_user: Any,
    tenant_id: int,
) -> NotaEntrada:
    return NotaEntrada(
        numero_nota=dados_nfe["numero_nota"],
        serie=dados_nfe["serie"],
        chave_acesso=dados_nfe["chave_acesso"],
        fornecedor_cnpj=dados_nfe["fornecedor_cnpj"],
        fornecedor_nome=dados_nfe["fornecedor_nome"],
        fornecedor_id=fornecedor.id if fornecedor else None,
        data_emissao=dados_nfe["data_emissao"],
        data_entrada=agora_utc_naive(),
        valor_produtos=dados_nfe["valor_produtos"],
        valor_frete=dados_nfe["valor_frete"],
        valor_desconto=dados_nfe["valor_desconto"],
        valor_total=dados_nfe["valor_total"],
        xml_content=xml_str,
        status="pendente",
        user_id=current_user.id,
        tenant_id=tenant_id,
    )


def _criar_itens_nota(
    db: Session,
    *,
    dados_nfe: dict[str, Any],
    nota: NotaEntrada,
    fornecedor: Cliente | None,
    current_user: Any,
    tenant_id: int,
    origem_documento: str,
    campos_xml_obrigatorios: bool,
) -> tuple[int, int, int]:
    vinculados = 0
    nao_vinculados = 0
    produtos_reativados = 0

    for item_data in dados_nfe["itens"]:
        produto, confianca, foi_inativo, origem_vinculo, referencia_vinculo = (
            encontrar_produto_similar(
                item_data["descricao"],
                item_data["codigo_produto"],
                db,
                tenant_id=tenant_id,
                fornecedor_id=fornecedor.id if fornecedor else None,
                ean=item_data.get("ean"),
                ean_tributario=item_data.get("ean_tributario"),
            )
        )

        if produto:
            vinculados += 1
            produtos_reativados += int(bool(foi_inativo))
            produto_id = produto.id
            vinculado = True
            item_status = "vinculado"
            _garantir_sku_produto(produto, db, current_user.id)
            _logar_vinculo_item(
                origem_documento=origem_documento,
                item_data=item_data,
                produto=produto,
                confianca=confianca,
                origem_vinculo=origem_vinculo,
                referencia_vinculo=referencia_vinculo,
                foi_inativo=foi_inativo,
            )
        else:
            nao_vinculados += 1
            produto_id = None
            vinculado = False
            item_status = "nao_vinculado"
            confianca = 0
            logger.warning(
                "%s item nao vinculado: %s",
                origem_documento.upper(),
                item_data["descricao"][:50],
            )

        item = _montar_item_nota(
            item_data=item_data,
            nota_id=nota.id,
            produto_id=produto_id,
            vinculado=vinculado,
            confianca=confianca,
            item_status=item_status,
            tenant_id=tenant_id,
            campos_xml_obrigatorios=campos_xml_obrigatorios,
        )
        db.add(item)
        if produto:
            _aplicar_codigos_barras_item_no_produto(produto, item)

    return vinculados, nao_vinculados, produtos_reativados


def _garantir_sku_produto(produto: Any, db: Session, user_id: int) -> None:
    if produto.codigo and produto.codigo.strip():
        return

    novo_sku = gerar_sku_automatico("PROD", db, user_id)
    produto.codigo = novo_sku
    logger.info("SKU gerado automaticamente: %s", novo_sku)


def _logar_vinculo_item(
    *,
    origem_documento: str,
    item_data: dict[str, Any],
    produto: Any,
    confianca: float,
    origem_vinculo: str | None,
    referencia_vinculo: str | None,
    foi_inativo: bool,
) -> None:
    detalhe_match = ""
    if origem_vinculo and referencia_vinculo:
        detalhe_match = f" [match por {origem_vinculo}: {referencia_vinculo}]"

    status_msg = " (INATIVO - sera reativado no processamento)" if foi_inativo else ""
    logger.info(
        "%s item vinculado: %s -> %s (confianca: %.0f%%)%s%s",
        origem_documento.upper(),
        item_data["descricao"][:50],
        produto.nome,
        confianca * 100,
        detalhe_match,
        status_msg,
    )


def _montar_item_nota(
    *,
    item_data: dict[str, Any],
    nota_id: int,
    produto_id: int | None,
    vinculado: bool,
    confianca: float,
    item_status: str,
    tenant_id: int,
    campos_xml_obrigatorios: bool,
) -> NotaEntradaItem:
    return NotaEntradaItem(
        nota_entrada_id=nota_id,
        numero_item=item_data["numero_item"],
        codigo_produto=_valor_item(
            item_data, "codigo_produto", campos_xml_obrigatorios
        ),
        descricao=item_data["descricao"],
        ncm=_valor_item(item_data, "ncm", campos_xml_obrigatorios),
        cest=item_data.get("cest"),
        cfop=_valor_item(item_data, "cfop", campos_xml_obrigatorios),
        origem=item_data.get("origem", "0" if campos_xml_obrigatorios else None),
        aliquota_icms=item_data.get(
            "aliquota_icms", 0 if campos_xml_obrigatorios else None
        ),
        aliquota_pis=item_data.get(
            "aliquota_pis", 0 if campos_xml_obrigatorios else None
        ),
        aliquota_cofins=item_data.get(
            "aliquota_cofins", 0 if campos_xml_obrigatorios else None
        ),
        unidade=_valor_item(
            item_data, "unidade", campos_xml_obrigatorios, default="UN"
        ),
        quantidade=item_data["quantidade"],
        valor_unitario=item_data["valor_unitario"],
        valor_total=item_data["valor_total"],
        ean=item_data.get("ean"),
        ean_tributario=item_data.get("ean_tributario"),
        lote=item_data.get("lote"),
        data_validade=item_data.get("data_validade"),
        produto_id=produto_id,
        vinculado=vinculado,
        confianca_vinculo=confianca,
        status=item_status,
        tenant_id=tenant_id,
    )


def _valor_item(
    item_data: dict[str, Any],
    campo: str,
    obrigatorio: bool,
    *,
    default: Any = None,
) -> Any:
    if obrigatorio:
        return item_data[campo]
    return item_data.get(campo) or default
