from datetime import datetime, timezone
import json
import re
from collections import Counter

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.estoque_reserva_service import EstoqueReservaService
from app.nfe_cache_models import BlingNotaFiscalCache
from app.pedido_integrado_item_models import PedidoIntegradoItem
from app.pedido_integrado_models import PedidoIntegrado
from app.produtos_models import Produto, ProdutoKitComponente, EstoqueMovimentacao
from app.services.kit_estoque_service import KitEstoqueService
from app.services.bling_flow_monitor_service import (
    abrir_incidente,
    registrar_evento,
    resolver_incidentes_relacionados,
)
from app.utils.logger import logger


AUTO_CADASTRO_BING_TAG = "[AUTO-BLING-NF]"


def _text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def buscar_produto_do_item(db: Session, tenant_id, sku: str):
    if not sku:
        return None

    return (
        db.query(Produto)
        .filter(
            Produto.tenant_id == tenant_id,
            or_(Produto.codigo == sku, Produto.codigo_barras == sku),
        )
        .first()
    )


def produto_usa_composicao_virtual(produto: Produto | None) -> bool:
    return bool(
        produto
        and produto.tipo_kit == "VIRTUAL"
        and produto.tipo_produto in {"KIT", "VARIACAO"}
    )


def produto_ids_estoque_afetados(db: Session, produto: Produto | None) -> list[int]:
    if not produto:
        return []

    if produto_usa_composicao_virtual(produto):
        componentes = (
            db.query(ProdutoKitComponente)
            .filter(ProdutoKitComponente.kit_id == produto.id)
            .all()
        )
        ids: list[int] = []
        for componente in componentes:
            if componente.produto_componente_id and componente.produto_componente_id not in ids:
                ids.append(int(componente.produto_componente_id))
        return ids

    return [int(produto.id)] if getattr(produto, "id", None) else []


def consumir_movimentacoes_esperadas(
    ids_esperados: list[int],
    movimentos_por_produto: Counter,
    movimentos_consumidos: Counter,
) -> bool:
    if not ids_esperados:
        return False

    for produto_id in ids_esperados:
        if movimentos_consumidos[produto_id] >= movimentos_por_produto[produto_id]:
            return False

    for produto_id in ids_esperados:
        movimentos_consumidos[produto_id] += 1
    return True


def _regex_token_numerico(valor: str | None) -> str | None:
    texto = _text(valor)
    if not texto:
        return None
    return rf"(?<!\d){re.escape(texto)}(?!\d)"


def movimento_documentado_por_nf(
    mov: EstoqueMovimentacao | None,
    *,
    nf_numero: str | None = None,
    nf_bling_id: str | None = None,
) -> bool:
    if not mov:
        return False

    documento = _text(getattr(mov, "documento", None))
    observacao = _text(getattr(mov, "observacao", None)) or ""
    nf_numero = _text(nf_numero)
    nf_bling_id = _text(nf_bling_id)

    if nf_numero and documento == nf_numero:
        return True

    padrao_nf_numero = _regex_token_numerico(nf_numero)
    if padrao_nf_numero and re.search(padrao_nf_numero, observacao):
        return True

    padrao_nf_bling = _regex_token_numerico(nf_bling_id)
    if padrao_nf_bling and re.search(padrao_nf_bling, observacao):
        return True

    return False


def movimento_legado_pedido_para_nf(
    mov: EstoqueMovimentacao | None,
    *,
    pedido_bling_numero: str | None = None,
    nf_numero: str | None = None,
    nf_bling_id: str | None = None,
) -> bool:
    if not mov or movimento_documentado_por_nf(mov, nf_numero=nf_numero, nf_bling_id=nf_bling_id):
        return False

    documento = _text(getattr(mov, "documento", None))
    observacao = (_text(getattr(mov, "observacao", None)) or "").lower()
    pedido_bling_numero = _text(pedido_bling_numero)

    if pedido_bling_numero and documento == pedido_bling_numero:
        return True

    if "webhook bling" in observacao or "pedido criado ja atendido" in observacao:
        return True

    return False


def _consumir_movimentacoes_esperadas_lista(
    ids_esperados: list[int],
    movimentos_por_produto: dict[int, list[EstoqueMovimentacao]],
) -> list[EstoqueMovimentacao] | None:
    if not ids_esperados:
        return None

    selecionadas: list[EstoqueMovimentacao] = []
    for produto_id in ids_esperados:
        lista = movimentos_por_produto.get(produto_id) or []
        if not lista:
            return None
        selecionadas.append(lista[0])

    for movimentacao in selecionadas:
        lista = movimentos_por_produto.get(int(movimentacao.produto_id)) or []
        if lista:
            lista.pop(0)

    return selecionadas


def _normalizar_movimentacoes_legadas_para_nf(
    db: Session,
    movimentos: list[EstoqueMovimentacao],
    *,
    nf_numero: str | None,
    nf_bling_id: str | None,
) -> int:
    movimentos_atualizados = 0
    observacao_nf = (
        f"Baixa automatica via NF {nf_numero}"
        if _text(nf_numero)
        else f"Baixa automatica via NF Bling #{nf_bling_id}"
        if _text(nf_bling_id)
        else None
    )

    for movimentacao in movimentos:
        if _text(nf_numero):
            movimentacao.documento = _text(nf_numero)
        if observacao_nf:
            movimentacao.observacao = observacao_nf
        db.add(movimentacao)
        movimentos_atualizados += 1

    return movimentos_atualizados


def _sincronizar_cache_estoque_virtual(db: Session, tenant_id, kit_id: int) -> float | None:
    produto_kit = (
        db.query(Produto)
        .filter(Produto.id == kit_id, Produto.tenant_id == tenant_id)
        .first()
    )
    if not produto_kit or not produto_usa_composicao_virtual(produto_kit):
        return None

    estoque_virtual = float(KitEstoqueService.calcular_estoque_virtual_kit(db, kit_id))
    produto_kit.estoque_atual = estoque_virtual
    db.add(produto_kit)
    return estoque_virtual


def _numero_nf_pedido(pedido: PedidoIntegrado | None, fallback_nf_id: str | None = None) -> str | None:
    payload_bruto = getattr(pedido, "payload", None)
    payload = payload_bruto if isinstance(payload_bruto, dict) else {}
    pedido_payload = payload.get("pedido") if isinstance(payload.get("pedido"), dict) else {}
    ultima_nf = (
        payload.get("ultima_nf")
        or pedido_payload.get("notaFiscal")
        or pedido_payload.get("nota")
        or pedido_payload.get("nfe")
    )
    ultima_nf = ultima_nf if isinstance(ultima_nf, dict) else {}
    numero = str(ultima_nf.get("numero") or "").strip()
    return numero or None


def _nf_cache_pertence_a_outro_pedido(
    db: Session,
    *,
    tenant_id,
    nf_bling_id: str | None,
    pedido_bling_id_atual: str | None,
) -> str | None:
    nf_bling_id = _text(nf_bling_id)
    pedido_bling_id_atual = _text(pedido_bling_id_atual)
    if not nf_bling_id or not pedido_bling_id_atual:
        return None

    registro = (
        db.query(BlingNotaFiscalCache)
        .filter(
            BlingNotaFiscalCache.tenant_id == tenant_id,
            BlingNotaFiscalCache.bling_id == nf_bling_id,
        )
        .order_by(BlingNotaFiscalCache.id.desc())
        .first()
    )
    pedido_ref = _text(getattr(registro, "pedido_bling_id_ref", None))
    if pedido_ref and pedido_ref != pedido_bling_id_atual:
        return pedido_ref
    return None


def _restaurar_lotes_consumidos(db: Session, movimentacao: EstoqueMovimentacao) -> int:
    from app.produtos_models import ProdutoLote

    bruto = getattr(movimentacao, "lotes_consumidos", None)
    if not bruto:
        return 0
    try:
        lotes = json.loads(bruto) if isinstance(bruto, str) else bruto
    except Exception:
        lotes = []

    restaurados = 0
    for item_lote in lotes or []:
        lote_id = item_lote.get("lote_id")
        quantidade = float(item_lote.get("quantidade") or 0)
        if not lote_id or quantidade <= 0:
            continue

        lote = db.query(ProdutoLote).filter(ProdutoLote.id == lote_id).first()
        if not lote:
            continue

        lote.quantidade_disponivel = float(lote.quantidade_disponivel or 0) + quantidade
        if lote.quantidade_disponivel > 0:
            lote.status = "ativo"
        db.add(lote)
        restaurados += 1

    return restaurados


def desvincular_nf_de_pedido_incorreto(
    db: Session,
    *,
    pedido: PedidoIntegrado,
    itens: list[PedidoIntegradoItem],
    nf_id: str | None = None,
    nf_numero: str | None = None,
    pedido_bling_id_esperado: str | None = None,
) -> dict:
    from app.estoque.service import EstoqueService
    from app.integracao_bling_nf_routes import _remover_nf_do_pedido

    pedido, itens = _recarregar_pedido_e_itens_para_nf(db, pedido, itens)
    nf_id = _text(nf_id)
    nf_numero = _text(nf_numero) or _numero_nf_pedido(pedido, nf_id)
    pedido_bling_id_esperado = _text(pedido_bling_id_esperado)

    movimentos = (
        db.query(EstoqueMovimentacao)
        .filter(
            EstoqueMovimentacao.tenant_id == pedido.tenant_id,
            EstoqueMovimentacao.referencia_tipo == "pedido_integrado",
            EstoqueMovimentacao.referencia_id == pedido.id,
            EstoqueMovimentacao.tipo == "saida",
            EstoqueMovimentacao.status != "cancelado",
        )
        .order_by(EstoqueMovimentacao.id.asc())
        .all()
    )
    movimentos_nf = [
        mov
        for mov in movimentos
        if movimento_documentado_por_nf(mov, nf_numero=nf_numero, nf_bling_id=nf_id)
    ]

    usuario_padrao = _obter_usuario_padrao_tenant(db=db, tenant_id=pedido.tenant_id)
    user_id_execucao = getattr(usuario_padrao, "id", None)

    movimentos_cancelados = 0
    estornos_criados = 0
    itens_reabertos = 0
    lotes_restaurados = 0

    for movimentacao in movimentos_nf:
        lotes_restaurados += _restaurar_lotes_consumidos(db, movimentacao)

        user_id_movimentacao = getattr(movimentacao, "user_id", None) or user_id_execucao
        if not user_id_movimentacao:
            raise ValueError(
                f"Nenhum usuario valido disponivel para estornar a movimentacao {movimentacao.id} "
                f"do pedido {pedido.id}."
            )

        EstoqueService.estornar_estoque(
            produto_id=movimentacao.produto_id,
            quantidade=float(movimentacao.quantidade or 0),
            motivo="nf_vinculada_pedido_incorreto",
            referencia_id=pedido.id,
            referencia_tipo="pedido_integrado",
            user_id=user_id_movimentacao,
            db=db,
            tenant_id=pedido.tenant_id,
            documento=nf_numero or nf_id,
            observacao=(
                f"Estorno automatico por desvinculo da NF {nf_numero or nf_id} "
                f"do pedido incorreto {pedido.pedido_bling_numero or pedido.pedido_bling_id}"
            ),
        )
        for kit_id, _estoque_virtual in KitEstoqueService.recalcular_kits_que_usam_produto(
            db,
            movimentacao.produto_id,
        ).items():
            _sincronizar_cache_estoque_virtual(db, pedido.tenant_id, kit_id)

        movimentacao.status = "cancelado"
        observacao_original = (movimentacao.observacao or "").strip()
        complemento = (
            f"Desvinculada automaticamente da NF {nf_numero or nf_id} "
            f"(pedido correto {pedido_bling_id_esperado})"
            if pedido_bling_id_esperado
            else f"Desvinculada automaticamente da NF {nf_numero or nf_id}"
        )
        movimentacao.observacao = (
            f"{observacao_original} | {complemento}"
            if observacao_original and complemento not in observacao_original
            else complemento
        )
        db.add(movimentacao)
        movimentos_cancelados += 1
        estornos_criados += 1

    for item in itens:
        if getattr(item, "vendido_em", None):
            item.vendido_em = None
            db.add(item)
            itens_reabertos += 1

    vinculo_removido = _remover_nf_do_pedido(
        pedido,
        nf_id=nf_id,
        nf_numero=nf_numero,
    )
    db.add(pedido)

    return {
        "vinculo_removido": vinculo_removido,
        "movimentos_cancelados": movimentos_cancelados,
        "estornos_criados": estornos_criados,
        "itens_reabertos": itens_reabertos,
        "lotes_restaurados": lotes_restaurados,
        "nf_numero": nf_numero,
        "nf_bling_id": nf_id,
        "pedido_bling_id_esperado": pedido_bling_id_esperado,
    }


def _recarregar_pedido_e_itens_para_nf(
    db: Session,
    pedido: PedidoIntegrado,
    itens: list[PedidoIntegradoItem],
) -> tuple[PedidoIntegrado, list[PedidoIntegradoItem]]:
    if not isinstance(db, Session):
        return pedido, list(itens or [])

    pedido_query = db.query(PedidoIntegrado).filter(
        PedidoIntegrado.id == pedido.id,
        PedidoIntegrado.tenant_id == pedido.tenant_id,
    )
    if hasattr(pedido_query, "with_for_update"):
        pedido_query = pedido_query.with_for_update()
    pedido_lock = pedido_query.first() or pedido

    itens_query = db.query(PedidoIntegradoItem).filter(
        PedidoIntegradoItem.pedido_integrado_id == pedido_lock.id
    )
    if hasattr(itens_query, "with_for_update"):
        itens_query = itens_query.with_for_update()
    itens_lock = itens_query.all() or list(itens or [])

    return pedido_lock, itens_lock


def baixar_estoque_item_integrado(
    *,
    db: Session,
    tenant_id,
    produto: Produto,
    quantidade: float,
    motivo: str,
    referencia_id: int,
    referencia_tipo: str,
    user_id: int,
    documento: str | None = None,
    observacao: str | None = None,
) -> dict:
    from app.estoque.service import EstoqueService

    quantidade = float(quantidade or 0)
    if quantidade <= 0:
        return {"movimentos": [], "estoques_virtuais": {}}
    if not user_id:
        raise ValueError("Nenhum usuario valido disponivel para registrar a movimentacao automatica do estoque.")

    if produto_usa_composicao_virtual(produto):
        componentes = (
            db.query(ProdutoKitComponente)
            .filter(ProdutoKitComponente.kit_id == produto.id)
            .all()
        )
        if not componentes:
            raise ValueError(
                f"Produto composto '{produto.nome}' nao possui componentes cadastrados."
            )

        movimentos: list[dict] = []
        kits_recalculados: dict[int, float] = {}

        for componente in componentes:
            produto_componente = (
                db.query(Produto)
                .filter(
                    Produto.id == componente.produto_componente_id,
                    Produto.tenant_id == tenant_id,
                )
                .first()
            )
            if not produto_componente:
                raise ValueError(
                    f"Componente ID {componente.produto_componente_id} nao encontrado para '{produto.nome}'."
                )

            quantidade_componente = quantidade * float(componente.quantidade or 0)
            resultado = EstoqueService.baixar_estoque(
                produto_id=produto_componente.id,
                quantidade=quantidade_componente,
                motivo=motivo,
                referencia_id=referencia_id,
                referencia_tipo=referencia_tipo,
                user_id=user_id,
                db=db,
                tenant_id=tenant_id,
                documento=documento,
                observacao=(
                    observacao
                    or f"Componente do produto composto '{produto.nome}'"
                ),
            )
            movimentos.append(
                {
                    "produto_id": produto_componente.id,
                    "produto_nome": resultado.get("produto_nome"),
                    "quantidade": quantidade_componente,
                    "kit_origem_id": produto.id,
                    "kit_origem_nome": produto.nome,
                }
            )

            for kit_id, estoque_virtual in KitEstoqueService.recalcular_kits_que_usam_produto(
                db,
                produto_componente.id,
            ).items():
                kits_recalculados[kit_id] = float(estoque_virtual)

        for kit_id, estoque_virtual in list(kits_recalculados.items()):
            estoque_sincronizado = _sincronizar_cache_estoque_virtual(db, tenant_id, kit_id)
            if estoque_sincronizado is not None:
                kits_recalculados[kit_id] = estoque_sincronizado

        return {
            "movimentos": movimentos,
            "estoques_virtuais": kits_recalculados,
        }

    resultado = EstoqueService.baixar_estoque(
        produto_id=produto.id,
        quantidade=quantidade,
        motivo=motivo,
        referencia_id=referencia_id,
        referencia_tipo=referencia_tipo,
        user_id=user_id,
        db=db,
        tenant_id=tenant_id,
        documento=documento,
        observacao=observacao,
    )
    return {
        "movimentos": [
            {
                "produto_id": produto.id,
                "produto_nome": resultado.get("produto_nome"),
                "quantidade": quantidade,
            }
        ],
        "estoques_virtuais": {},
    }


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


def _to_float(valor, default: float = 0.0) -> float:
    try:
        return float(valor)
    except Exception:
        return default


def _texto(valor, default: str = "") -> str:
    return str(valor or default).strip()


def _montar_produto_local_do_bling(item_bling: dict, tenant_id, user_id: int, sku_padrao: str) -> Produto:
    codigo = _texto(item_bling.get("codigo") or item_bling.get("sku"), sku_padrao)[:50]
    nome = _texto(item_bling.get("nome") or item_bling.get("descricao"), f"Produto {codigo}")[:200]
    codigo_barras = _texto(item_bling.get("codigoBarras"))[:20] or None
    unidade = _texto(item_bling.get("unidade"), "UN")[:10] or "UN"

    preco_venda = max(
        _to_float(item_bling.get("preco"), _to_float(item_bling.get("precoVenda"), 0.0)),
        0.0,
    )
    estoque_bling = max(
        _to_float(item_bling.get("estoque"), _to_float(item_bling.get("saldoFisicoTotal"), 0.0)),
        0.0,
    )

    return Produto(
        tenant_id=tenant_id,
        user_id=user_id,
        codigo=codigo,
        nome=nome,
        codigo_barras=codigo_barras,
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
        logger.warning(f"⚠️ SKU {sku_limpo}: produto não encontrado no Bling para autocadastro")
        return None

    usuario = _obter_usuario_padrao_tenant(db=db, tenant_id=tenant_id)
    if not usuario:
        logger.warning(f"⚠️ SKU {sku_limpo}: não há usuário no tenant para autocadastro do produto")
        return None

    novo_produto = _montar_produto_local_do_bling(
        item_bling=item_bling,
        tenant_id=tenant_id,
        user_id=usuario.id,
        sku_padrao=sku_limpo,
    )

    if _codigo_ja_existe_global(db, novo_produto.codigo):
        codigo_original = novo_produto.codigo
        novo_produto.codigo = _gerar_codigo_fallback(db=db, sku=sku_limpo, tenant_id=tenant_id)
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
        logger.info(f"✅ SKU {sku_limpo}: produto criado automaticamente com id={novo_produto.id}")
        return novo_produto
    except Exception as e:
        logger.warning(f"⚠️ SKU {sku_limpo}: falha no autocadastro do produto: {e}")
        return buscar_produto_do_item(db=db, tenant_id=tenant_id, sku=sku_limpo)


def _processar_nf_autorizada_legado(
    db: Session,
    pedido: PedidoIntegrado,
    itens: list[PedidoIntegradoItem],
    nf_id: str,
) -> str:
    pedido_bling_id = getattr(pedido, "pedido_bling_id", None)

    if pedido.status == "confirmado" and all(item.vendido_em for item in itens):
        return "venda_ja_confirmada"

    pedido.status = "confirmado"
    pedido.confirmado_em = datetime.now(timezone.utc)

    for item in itens:
        if item.vendido_em:
            continue

        EstoqueReservaService.confirmar_venda(db, item)

        try:
            from app.estoque.service import EstoqueService

            produto = buscar_produto_do_item(
                db=db,
                tenant_id=pedido.tenant_id,
                sku=item.sku,
            )

            if not produto:
                produto = criar_produto_automatico_do_bling(
                    db=db,
                    tenant_id=pedido.tenant_id,
                    sku=item.sku,
                )

            if produto:
                EstoqueService.baixar_estoque(
                    produto_id=produto.id,
                    quantidade=float(item.quantidade),
                    motivo="venda_bling",
                    referencia_id=pedido.id,
                    referencia_tipo="pedido_integrado",
                    user_id=0,
                    db=db,
                    tenant_id=pedido.tenant_id,
                    documento=pedido.pedido_bling_numero,
                    observacao=f"Baixa automática via NF Bling #{nf_id}",
                )
            else:
                logger.warning(f"⚠️  Produto com código/SKU '{item.sku}' não encontrado para baixa de estoque")
                registrar_evento(
                    tenant_id=pedido.tenant_id,
                    source="runtime",
                    event_type="nf.baixa_estoque",
                    entity_type="nf",
                    status="error",
                    severity="critical",
                    message="Produto nao encontrado para baixa via NF",
                    error_message=f"SKU {item.sku} sem produto local",
                    pedido_integrado_id=pedido.id,
                    pedido_bling_id=pedido_bling_id,
                    nf_bling_id=nf_id,
                    sku=item.sku,
                )
                abrir_incidente(
                    tenant_id=pedido.tenant_id,
                    code="SKU_SEM_PRODUTO_LOCAL",
                    severity="critical",
                    title="SKU sem produto local",
                    message=f"O SKU '{item.sku}' nao foi encontrado ao processar a NF autorizada.",
                    suggested_action="Autocadastrar o produto pelo Bling e reconciliar a baixa pendente.",
                    auto_fixable=True,
                    pedido_integrado_id=pedido.id,
                    pedido_bling_id=pedido_bling_id,
                    nf_bling_id=nf_id,
                    sku=item.sku,
                    details={"origem": "nf_autorizada"},
                    source="runtime",
                )

        except Exception as e:
            logger.warning(f"⚠️  Falha ao baixar estoque para SKU {item.sku}: {e}")
            registrar_evento(
                tenant_id=pedido.tenant_id,
                source="runtime",
                event_type="nf.baixa_estoque",
                entity_type="nf",
                status="error",
                severity="critical",
                message="Falha ao baixar estoque via NF autorizada",
                error_message=str(e),
                pedido_integrado_id=pedido.id,
                pedido_bling_id=pedido_bling_id,
                nf_bling_id=nf_id,
                sku=item.sku,
            )
            abrir_incidente(
                tenant_id=pedido.tenant_id,
                code="PEDIDO_CONFIRMADO_SEM_BAIXA_ESTOQUE",
                severity="critical",
                title="Falha na baixa do estoque por NF",
                message=f"A NF autorizada nao conseguiu baixar o estoque do SKU '{item.sku}'.",
                suggested_action="Reconciliar o pedido confirmado e reaplicar a baixa faltante.",
                auto_fixable=True,
                pedido_integrado_id=pedido.id,
                pedido_bling_id=pedido_bling_id,
                nf_bling_id=nf_id,
                sku=item.sku,
                details={"erro": str(e)},
                source="runtime",
            )

    db.add(pedido)
    db.commit()
    registrar_evento(
        tenant_id=pedido.tenant_id,
        source="runtime",
        event_type="nf.processada",
        entity_type="nf",
        status="ok",
        severity="info",
        message="NF autorizada processada com reconciliacao de estoque",
        pedido_integrado_id=pedido.id,
        pedido_bling_id=pedido_bling_id,
        nf_bling_id=nf_id,
    )
    return "venda_confirmada"

def processar_nf_autorizada(
    db: Session,
    pedido: PedidoIntegrado,
    itens: list[PedidoIntegradoItem],
    nf_id: str,
) -> str:
    pedido, itens = _recarregar_pedido_e_itens_para_nf(db, pedido, itens)
    pedido_bling_id = getattr(pedido, "pedido_bling_id", None)
    nf_numero = _numero_nf_pedido(pedido, nf_id)
    pedido_ref_conflitante = _nf_cache_pertence_a_outro_pedido(
        db,
        tenant_id=pedido.tenant_id,
        nf_bling_id=nf_id,
        pedido_bling_id_atual=pedido_bling_id,
    )
    if pedido_ref_conflitante:
        resultado_desvinculo = desvincular_nf_de_pedido_incorreto(
            db=db,
            pedido=pedido,
            itens=itens,
            nf_id=nf_id,
            nf_numero=nf_numero,
            pedido_bling_id_esperado=pedido_ref_conflitante,
        )
        mensagem = (
            f"A NF {nf_numero or nf_id} pertence ao pedido Bling {pedido_ref_conflitante}, "
            f"nao ao pedido {pedido_bling_id}."
        )
        registrar_evento(
            tenant_id=pedido.tenant_id,
            source="runtime",
            event_type="nf.processada",
            entity_type="nf",
            status="error",
            severity="critical",
            message="Processamento da NF bloqueado por vinculo com outro pedido",
            error_message=mensagem,
            pedido_integrado_id=pedido.id,
            pedido_bling_id=pedido_bling_id,
            nf_bling_id=nf_id,
            payload={
                "nf_numero": nf_numero,
                "pedido_bling_id_esperado": pedido_ref_conflitante,
                "desvinculo": resultado_desvinculo,
            },
            auto_fix_applied=bool(
                resultado_desvinculo.get("vinculo_removido")
                or resultado_desvinculo.get("movimentos_cancelados")
            ),
        )
        resolver_incidentes_relacionados(
            db,
            tenant_id=pedido.tenant_id,
            codes=[
                "NF_VINCULADA_A_OUTRO_PEDIDO",
                "ITEM_NAO_CONFIRMADO_EM_PEDIDO_CONFIRMADO",
                "PEDIDO_CONFIRMADO_SEM_BAIXA_ESTOQUE",
            ],
            pedido_integrado_id=pedido.id,
            pedido_bling_id=pedido.pedido_bling_id,
            nf_bling_id=nf_id,
            resolution_note="Vinculo incorreto da NF removido automaticamente.",
        )
        db.add(pedido)
        db.commit()
        return "nf_vinculada_outro_pedido"
    movimentos_existentes = (
        db.query(EstoqueMovimentacao)
        .filter(
            EstoqueMovimentacao.tenant_id == pedido.tenant_id,
            EstoqueMovimentacao.referencia_tipo == "pedido_integrado",
            EstoqueMovimentacao.referencia_id == pedido.id,
            EstoqueMovimentacao.tipo == "saida",
            EstoqueMovimentacao.status != "cancelado",
        )
        .order_by(EstoqueMovimentacao.id.asc())
        .all()
    )
    movimentos_nf_por_produto: dict[int, list[EstoqueMovimentacao]] = {}
    movimentos_legados_por_produto: dict[int, list[EstoqueMovimentacao]] = {}
    for mov in movimentos_existentes:
        produto_id_mov = getattr(mov, "produto_id", None)
        if not produto_id_mov:
            continue
        produto_id_int = int(produto_id_mov)
        if movimento_documentado_por_nf(mov, nf_numero=nf_numero, nf_bling_id=nf_id):
            movimentos_nf_por_produto.setdefault(produto_id_int, []).append(mov)
        elif movimento_legado_pedido_para_nf(
            mov,
            pedido_bling_numero=getattr(pedido, "pedido_bling_numero", None),
            nf_numero=nf_numero,
            nf_bling_id=nf_id,
        ):
            movimentos_legados_por_produto.setdefault(produto_id_int, []).append(mov)
    usuario_padrao = _obter_usuario_padrao_tenant(db=db, tenant_id=pedido.tenant_id)
    user_id_execucao = getattr(usuario_padrao, "id", None)
    venda_ja_confirmada = pedido.status == "confirmado" and all(item.vendido_em for item in itens)
    itens_confirmados = 0
    baixas_criadas = 0
    baixas_normalizadas = 0
    houve_erros = False

    pedido.status = "confirmado"
    pedido.confirmado_em = pedido.confirmado_em or datetime.now(timezone.utc)

    for item in itens:
        try:
            produto = buscar_produto_do_item(
                db=db,
                tenant_id=pedido.tenant_id,
                sku=item.sku,
            )

            if not produto:
                produto = criar_produto_automatico_do_bling(
                    db=db,
                    tenant_id=pedido.tenant_id,
                    sku=item.sku,
                )

            if not produto:
                logger.warning(f"Produto com codigo/SKU '{item.sku}' nao encontrado para baixa de estoque")
                registrar_evento(
                    tenant_id=pedido.tenant_id,
                    source="runtime",
                    event_type="nf.baixa_estoque",
                    entity_type="nf",
                    status="error",
                    severity="critical",
                    message="Produto nao encontrado para baixa via NF",
                    error_message=f"SKU {item.sku} sem produto local",
                    pedido_integrado_id=pedido.id,
                    pedido_bling_id=pedido_bling_id,
                    nf_bling_id=nf_id,
                    sku=item.sku,
                )
                abrir_incidente(
                    tenant_id=pedido.tenant_id,
                    code="SKU_SEM_PRODUTO_LOCAL",
                    severity="critical",
                    title="SKU sem produto local",
                    message=f"O SKU '{item.sku}' nao foi encontrado ao processar a NF autorizada.",
                    suggested_action="Autocadastrar o produto pelo Bling e reconciliar a baixa pendente.",
                    auto_fixable=True,
                    pedido_integrado_id=pedido.id,
                    pedido_bling_id=pedido_bling_id,
                    nf_bling_id=nf_id,
                    sku=item.sku,
                    details={"origem": "nf_autorizada"},
                    source="runtime",
                )
                houve_erros = True
                continue

            ids_esperados = produto_ids_estoque_afetados(db=db, produto=produto)
            movimentos_nf_existentes = _consumir_movimentacoes_esperadas_lista(
                ids_esperados,
                movimentos_nf_por_produto,
            )

            if movimentos_nf_existentes:
                if not item.vendido_em:
                    EstoqueReservaService.confirmar_venda(db, item)
                    itens_confirmados += 1
                continue

            movimentos_legados = _consumir_movimentacoes_esperadas_lista(
                ids_esperados,
                movimentos_legados_por_produto,
            )
            if movimentos_legados:
                baixas_normalizadas += _normalizar_movimentacoes_legadas_para_nf(
                    db,
                    movimentos_legados,
                    nf_numero=nf_numero,
                    nf_bling_id=nf_id,
                )
                if not item.vendido_em:
                    EstoqueReservaService.confirmar_venda(db, item)
                    itens_confirmados += 1
                continue

            resultado_baixa = baixar_estoque_item_integrado(
                db=db,
                tenant_id=pedido.tenant_id,
                produto=produto,
                quantidade=float(item.quantidade),
                motivo="venda_bling",
                referencia_id=pedido.id,
                referencia_tipo="pedido_integrado",
                user_id=user_id_execucao,
                documento=nf_numero,
                observacao=f"Baixa automatica via NF {nf_numero}" if nf_numero else "Baixa automatica via NF autorizada do Bling",
            )
            movimentos_gerados = resultado_baixa.get("movimentos") or []
            if movimentos_gerados:
                for movimento in movimentos_gerados:
                    produto_id_mov = movimento.get("produto_id")
                    if produto_id_mov:
                        movimentos_nf_por_produto.setdefault(int(produto_id_mov), [])
                baixas_criadas += len(movimentos_gerados)
            else:
                baixas_criadas += 1

            if not item.vendido_em:
                EstoqueReservaService.confirmar_venda(db, item)
                itens_confirmados += 1

        except Exception as e:
            logger.warning(f"Falha ao baixar estoque para SKU {item.sku}: {e}")
            registrar_evento(
                tenant_id=pedido.tenant_id,
                source="runtime",
                event_type="nf.baixa_estoque",
                entity_type="nf",
                status="error",
                severity="critical",
                message="Falha ao baixar estoque via NF autorizada",
                error_message=str(e),
                pedido_integrado_id=pedido.id,
                pedido_bling_id=pedido_bling_id,
                nf_bling_id=nf_id,
                sku=item.sku,
            )
            abrir_incidente(
                tenant_id=pedido.tenant_id,
                code="PEDIDO_CONFIRMADO_SEM_BAIXA_ESTOQUE",
                severity="critical",
                title="Falha na baixa do estoque por NF",
                message=f"A NF autorizada nao conseguiu baixar o estoque do SKU '{item.sku}'.",
                suggested_action="Reconciliar o pedido confirmado e reaplicar a baixa faltante.",
                auto_fixable=True,
                pedido_integrado_id=pedido.id,
                pedido_bling_id=pedido_bling_id,
                nf_bling_id=nf_id,
                sku=item.sku,
                details={"erro": str(e)},
                source="runtime",
            )
            houve_erros = True

    db.add(pedido)
    db.commit()
    incidentes_resolvidos = resolver_incidentes_relacionados(
        db,
        tenant_id=pedido.tenant_id,
        codes=[
            "PEDIDO_CONFIRMADO_SEM_BAIXA_ESTOQUE",
            "ITEM_NAO_CONFIRMADO_EM_PEDIDO_CONFIRMADO",
            "NF_AUTORIZADA_PEDIDO_NAO_CONFIRMADO",
        ],
        pedido_integrado_id=pedido.id,
        pedido_bling_id=pedido_bling_id,
        nf_bling_id=nf_id,
        resolution_note="Baixa de estoque reconciliada a partir da NF autorizada.",
    )
    if incidentes_resolvidos:
        db.commit()

    if venda_ja_confirmada and itens_confirmados == 0 and baixas_criadas == 0 and baixas_normalizadas == 0 and not houve_erros:
        return "venda_ja_confirmada"

    registrar_evento(
        tenant_id=pedido.tenant_id,
        source="runtime",
        event_type="nf.processada",
        entity_type="nf",
        status="ok",
        severity="info",
        message="NF autorizada processada com reconciliacao de estoque",
        pedido_integrado_id=pedido.id,
        pedido_bling_id=pedido_bling_id,
        nf_bling_id=nf_id,
    )
    return "venda_confirmada"


def processar_nf_cancelada(
    db: Session,
    pedido: PedidoIntegrado,
    itens: list[PedidoIntegradoItem],
    nf_id: str | None = None,
) -> str:
    from app.estoque.service import EstoqueService

    pedido.status = "cancelado"
    pedido.cancelado_em = datetime.now(timezone.utc)

    movimentos_ativos = (
        db.query(EstoqueMovimentacao)
        .filter(
            EstoqueMovimentacao.tenant_id == pedido.tenant_id,
            EstoqueMovimentacao.referencia_tipo == "pedido_integrado",
            EstoqueMovimentacao.referencia_id == pedido.id,
            EstoqueMovimentacao.tipo == "saida",
            EstoqueMovimentacao.status != "cancelado",
        )
        .order_by(EstoqueMovimentacao.id.asc())
        .all()
    )

    usuario_padrao = _obter_usuario_padrao_tenant(db=db, tenant_id=pedido.tenant_id)
    user_id_execucao = getattr(usuario_padrao, "id", None)
    houve_estorno = False

    for movimentacao in movimentos_ativos:
        _restaurar_lotes_consumidos(db, movimentacao)

        user_id_movimentacao = getattr(movimentacao, "user_id", None) or user_id_execucao
        if not user_id_movimentacao:
            raise ValueError(
                f"Nenhum usuario valido disponivel para estornar a movimentacao de estoque do pedido {pedido.id}"
            )

        EstoqueService.estornar_estoque(
            produto_id=movimentacao.produto_id,
            quantidade=float(movimentacao.quantidade or 0),
            motivo="cancelamento_nf_bling",
            referencia_id=pedido.id,
            referencia_tipo="pedido_integrado",
            user_id=user_id_movimentacao,
            db=db,
            tenant_id=pedido.tenant_id,
            documento=pedido.pedido_bling_numero,
            observacao=(
                f"Estorno automatico por cancelamento da NF Bling #{nf_id or _numero_nf_pedido(pedido)}"
            ),
        )
        for kit_id, _estoque_virtual in KitEstoqueService.recalcular_kits_que_usam_produto(
            db,
            movimentacao.produto_id,
        ).items():
            _sincronizar_cache_estoque_virtual(db, pedido.tenant_id, kit_id)
        movimentacao.status = "cancelado"
        observacao_original = (movimentacao.observacao or "").strip()
        complemento = f"Cancelada pela NF Bling #{nf_id or _numero_nf_pedido(pedido)}"
        movimentacao.observacao = (
            f"{observacao_original} | {complemento}"
            if observacao_original and complemento not in observacao_original
            else complemento
        )
        db.add(movimentacao)
        houve_estorno = True

    for item in itens:
        item.vendido_em = None
        item.liberado_em = item.liberado_em or datetime.utcnow()
        db.add(item)

    db.add(pedido)
    db.commit()
    return "venda_cancelada_com_estorno" if houve_estorno else "venda_cancelada"
