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

    if sku_limpo:
        existente = buscar_produto_do_item(db=db, tenant_id=tenant_id, sku=sku_limpo)
        if existente:
            return existente

    if codigo_barras:
        existente = buscar_produto_do_item(
            db=db, tenant_id=tenant_id, sku=codigo_barras
        )
        if existente:
            return existente

    usuario = _obter_usuario_padrao_tenant(db=db, tenant_id=tenant_id)
    if not usuario:
        logger.warning(
            "Produto Bling sem usuario padrao no tenant %s para autocadastro", tenant_id
        )
        return None

    chave_base = sku_limpo or codigo_barras or _texto(item_bling.get("id"), "BLING")
    novo_produto = _montar_produto_local_do_bling(
        item_bling=item_bling,
        tenant_id=tenant_id,
        user_id=usuario.id,
        sku_padrao=chave_base,
    )

    if _codigo_ja_existe_global(db, novo_produto.codigo):
        codigo_original = novo_produto.codigo
        novo_produto.codigo = _gerar_codigo_fallback(
            db=db, sku=chave_base, tenant_id=tenant_id
        )
        if not (novo_produto.codigo_barras or "").strip():
            novo_produto.codigo_barras = chave_base[:20]
        logger.info(
            "[AUTO-BLING-NF] Ajuste de codigo por colisao global: '%s' -> '%s'",
            codigo_original,
            novo_produto.codigo,
        )

    try:
        with db.begin_nested():
            db.add(novo_produto)
            db.flush()
        logger.info("Produto Bling criado automaticamente com id=%s", novo_produto.id)
        return novo_produto
    except Exception as e:
        logger.warning("Falha no autocadastro por item do Bling: %s", e)
        if sku_limpo:
            existente = buscar_produto_do_item(
                db=db, tenant_id=tenant_id, sku=sku_limpo
            )
            if existente:
                return existente
        if codigo_barras:
            return buscar_produto_do_item(db=db, tenant_id=tenant_id, sku=codigo_barras)
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


def criar_produto_automatico_do_bling(db: Session, tenant_id, sku: str):
    sku_limpo = (sku or "").strip()
    if not sku_limpo:
        return None

    existente = buscar_produto_do_item(db=db, tenant_id=tenant_id, sku=sku_limpo)
    if existente:
        return existente

    item_bling = _buscar_produto_bling_por_sku(sku_limpo)
    if not item_bling:
        logger.warning(
            f"⚠️ SKU {sku_limpo}: produto não encontrado no Bling para autocadastro"
        )
        return None

    usuario = _obter_usuario_padrao_tenant(db=db, tenant_id=tenant_id)
    if not usuario:
        logger.warning(
            f"⚠️ SKU {sku_limpo}: não há usuário no tenant para autocadastro do produto"
        )
        return None

    novo_produto = _montar_produto_local_do_bling(
        item_bling=item_bling,
        tenant_id=tenant_id,
        user_id=usuario.id,
        sku_padrao=sku_limpo,
    )

    if _codigo_ja_existe_global(db, novo_produto.codigo):
        codigo_original = novo_produto.codigo
        novo_produto.codigo = _gerar_codigo_fallback(
            db=db, sku=sku_limpo, tenant_id=tenant_id
        )
        # Mantém o SKU original indexável para busca e baixa por SKU.
        if not (novo_produto.codigo_barras or "").strip():
            novo_produto.codigo_barras = sku_limpo[:20]
        logger.info(
            f"[AUTO-BLING-NF] Ajuste de código por colisão global: '{codigo_original}' -> '{novo_produto.codigo}'"
        )

    try:
        with db.begin_nested():
            db.add(novo_produto)
            db.flush()
        logger.info(
            f"✅ SKU {sku_limpo}: produto criado automaticamente com id={novo_produto.id}"
        )
        return novo_produto
    except Exception as e:
        logger.warning(f"⚠️ SKU {sku_limpo}: falha no autocadastro do produto: {e}")
        return buscar_produto_do_item(db=db, tenant_id=tenant_id, sku=sku_limpo)
