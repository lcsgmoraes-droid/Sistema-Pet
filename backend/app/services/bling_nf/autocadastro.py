"""Autocadastro de produtos locais a partir do catalogo Bling."""

from datetime import datetime, timezone
import re

from sqlalchemy.orm import Session

from app.produtos_models import Produto
from app.utils.logger import logger

from .common import AUTO_CADASTRO_BING_TAG, _texto, _to_float
from .estoque import buscar_produto_do_item


def _extrair_lista_produtos_bling(resultado: dict | None) -> list[dict]:
    itens = (resultado or {}).get("data", [])
    produtos = []
    for item in itens:
        if isinstance(item, dict) and isinstance(item.get("produto"), dict):
            produtos.append(item.get("produto") or {})
        elif isinstance(item, dict):
            produtos.append(item)
    return produtos


def _obter_usuario_padrao_tenant(db: Session, tenant_id):
    from app.models import User

    usuario = (
        db.query(User)
        .filter(User.tenant_id == tenant_id)
        .order_by(User.id.asc())
        .first()
    )
    return usuario


def _buscar_produto_bling_por_sku(sku: str) -> dict | None:
    from app.bling_integration import BlingAPI

    bling = BlingAPI()
    for filtro in ("codigo", "sku"):
        resultado = bling.listar_produtos(**{filtro: sku, "limite": 5})
        itens = _extrair_lista_produtos_bling(resultado)
        if itens:
            return itens[0]
    return None


def _montar_produto_local_do_bling(
    item_bling: dict, tenant_id, user_id: int, sku_padrao: str
) -> Produto:
    codigo = (
        _texto(item_bling.get("sku") or item_bling.get("codigo"), sku_padrao) or ""
    ).upper()[:50]
    nome = _texto(
        item_bling.get("nome") or item_bling.get("descricao"), f"Produto {codigo}"
    )[:200]
    codigo_barras = (
        _texto(item_bling.get("codigoBarras") or item_bling.get("gtin"))[:20] or None
    )
    gtin = _texto(item_bling.get("gtin"))[:13] or None
    unidade = _texto(item_bling.get("unidade"), "UN")[:10] or "UN"

    preco_venda = max(
        _to_float(
            item_bling.get("preco"), _to_float(item_bling.get("precoVenda"), 0.0)
        ),
        0.0,
    )
    estoque_bling = max(
        _to_float(
            item_bling.get("estoque"),
            _to_float(item_bling.get("saldoFisicoTotal"), 0.0),
        ),
        0.0,
    )

    return Produto(
        tenant_id=tenant_id,
        user_id=user_id,
        codigo=codigo,
        nome=nome,
        codigo_barras=codigo_barras,
        gtin_ean=gtin,
        tipo="produto",
        tipo_produto="SIMPLES",
        is_parent=False,
        is_sellable=True,
        situacao=True,
        ativo=True,
        unidade=unidade,
        preco_custo=0,
        preco_venda=preco_venda,
        estoque_atual=estoque_bling,
        estoque_fisico=estoque_bling,
        estoque_minimo=0,
        informacoes_adicionais_nf=(
            f"{AUTO_CADASTRO_BING_TAG} sku={sku_padrao} "
            f"criado_em={datetime.now(timezone.utc).isoformat()}"
        ),
    )


def _buscar_produto_existente_por_chaves(db: Session, tenant_id, *chaves):
    for chave in chaves:
        chave_limpa = _texto(chave)
        if not chave_limpa:
            continue
        existente = buscar_produto_do_item(
            db=db,
            tenant_id=tenant_id,
            sku=chave_limpa,
        )
        if existente:
            return existente
    return None


def _usuario_padrao_autocadastro(db: Session, tenant_id, *, origem: str):
    usuario = _obter_usuario_padrao_tenant(db=db, tenant_id=tenant_id)
    if usuario:
        return usuario

    logger.warning(
        "Produto Bling sem usuario padrao no tenant %s para autocadastro (%s)",
        tenant_id,
        origem,
    )
    return None


def _slug_codigo(valor: str) -> str:
    base = re.sub(r"[^A-Za-z0-9_-]", "", (valor or "").strip())
    return base[:42] if base else "SKU"


def _codigo_ja_existe_global(db: Session, codigo: str) -> bool:
    return db.query(Produto.id).filter(Produto.codigo == codigo).first() is not None


def _gerar_codigo_fallback(db: Session, sku: str, tenant_id) -> str:
    tenant_tag = str(tenant_id).replace("-", "")[:8] or "TENANT"
    base = _slug_codigo(sku)

    candidato = f"{base}-{tenant_tag}"[:50]
    if not _codigo_ja_existe_global(db, candidato):
        return candidato

    for idx in range(2, 100):
        candidato = f"{base}-{tenant_tag}-{idx}"[:50]
        if not _codigo_ja_existe_global(db, candidato):
            return candidato

    return f"AUTO-{tenant_tag}-{int(datetime.now(timezone.utc).timestamp())}"[:50]


def _ajustar_codigo_colidido(
    db: Session,
    *,
    produto: Produto,
    sku_padrao: str,
    tenant_id,
) -> None:
    if not _codigo_ja_existe_global(db, produto.codigo):
        return

    codigo_original = produto.codigo
    produto.codigo = _gerar_codigo_fallback(db=db, sku=sku_padrao, tenant_id=tenant_id)
    if not (produto.codigo_barras or "").strip():
        produto.codigo_barras = sku_padrao[:20]
    logger.info(
        "[AUTO-BLING-NF] Ajuste de codigo por colisao global: '%s' -> '%s'",
        codigo_original,
        produto.codigo,
    )


def _salvar_produto_automatico(
    db: Session,
    *,
    produto: Produto,
    chaves_fallback: tuple[str | None, ...],
    mensagem_erro: str,
):
    try:
        with db.begin_nested():
            db.add(produto)
            db.flush()
        logger.info("Produto Bling criado automaticamente com id=%s", produto.id)
        return produto
    except Exception as e:
        logger.warning(mensagem_erro, e)
        return _buscar_produto_existente_por_chaves(
            db,
            produto.tenant_id,
            *chaves_fallback,
        )


def _preparar_produto_automatico(
    db: Session,
    *,
    tenant_id,
    item_bling: dict,
    sku_padrao: str,
    origem: str,
) -> Produto | None:
    usuario = _usuario_padrao_autocadastro(db, tenant_id, origem=origem)
    if not usuario:
        return None

    produto = _montar_produto_local_do_bling(
        item_bling=item_bling,
        tenant_id=tenant_id,
        user_id=usuario.id,
        sku_padrao=sku_padrao,
    )
    _ajustar_codigo_colidido(
        db,
        produto=produto,
        sku_padrao=sku_padrao,
        tenant_id=tenant_id,
    )
    return produto


def criar_produto_automatico_do_bling_por_item(
    db: Session,
    tenant_id,
    item_bling: dict | None,
    sku_preferencial: str | None = None,
):
    item_bling = item_bling or {}
    sku_limpo = _texto(
        sku_preferencial or item_bling.get("sku") or item_bling.get("codigo")
    )
    codigo_barras = _texto(item_bling.get("codigoBarras") or item_bling.get("gtin"))

    existente = _buscar_produto_existente_por_chaves(
        db,
        tenant_id,
        sku_limpo,
        codigo_barras,
    )
    if existente:
        return existente

    chave_base = sku_limpo or codigo_barras or _texto(item_bling.get("id"), "BLING")
    novo_produto = _preparar_produto_automatico(
        db,
        tenant_id=tenant_id,
        item_bling=item_bling,
        sku_padrao=chave_base,
        origem="item_nf",
    )
    if not novo_produto:
        return None

    return _salvar_produto_automatico(
        db,
        produto=novo_produto,
        chaves_fallback=(sku_limpo, codigo_barras),
        mensagem_erro="Falha no autocadastro por item do Bling: %s",
    )


def criar_produto_automatico_do_bling(db: Session, tenant_id, sku: str):
    sku_limpo = (sku or "").strip()
    if not sku_limpo:
        return None

    existente = _buscar_produto_existente_por_chaves(db, tenant_id, sku_limpo)
    if existente:
        return existente

    item_bling = _buscar_produto_bling_por_sku(sku_limpo)
    if not item_bling:
        logger.warning(
            "SKU %s: produto nao encontrado no Bling para autocadastro", sku_limpo
        )
        return None

    novo_produto = _preparar_produto_automatico(
        db,
        tenant_id=tenant_id,
        item_bling=item_bling,
        sku_padrao=sku_limpo,
        origem="sku",
    )
    if not novo_produto:
        return None

    return _salvar_produto_automatico(
        db,
        produto=novo_produto,
        chaves_fallback=(sku_limpo,),
        mensagem_erro=f"SKU {sku_limpo}: falha no autocadastro do produto: %s",
    )
