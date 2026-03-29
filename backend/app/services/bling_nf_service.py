from datetime import datetime, timezone
import re
from collections import Counter

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.estoque_reserva_service import EstoqueReservaService
from app.pedido_integrado_item_models import PedidoIntegradoItem
from app.pedido_integrado_models import PedidoIntegrado
from app.produtos_models import Produto, ProdutoKitComponente, EstoqueMovimentacao
from app.services.kit_estoque_service import KitEstoqueService
from app.services.bling_flow_monitor_service import abrir_incidente, registrar_evento
from app.utils.logger import logger


AUTO_CADASTRO_BING_TAG = "[AUTO-BLING-NF]"


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
    ultima_nf = payload.get("ultima_nf") if isinstance(payload.get("ultima_nf"), dict) else {}
    numero = str(ultima_nf.get("numero") or "").strip()
    if numero:
        return numero
    numero_pedido = str(getattr(pedido, "pedido_bling_numero", "") or "").strip()
    if numero_pedido:
        return numero_pedido
    fallback = str(fallback_nf_id or "").strip()
    return fallback or None


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
    pedido_bling_id = getattr(pedido, "pedido_bling_id", None)
    nf_numero = _numero_nf_pedido(pedido, nf_id)
    movimentos_existentes = db.query(EstoqueMovimentacao).filter(
        EstoqueMovimentacao.tenant_id == pedido.tenant_id,
        EstoqueMovimentacao.referencia_tipo == "pedido_integrado",
        EstoqueMovimentacao.referencia_id == pedido.id,
        EstoqueMovimentacao.tipo == "saida",
    ).all()
    movimentos_por_produto = Counter(
        int(mov.produto_id) for mov in movimentos_existentes if getattr(mov, "produto_id", None)
    )
    movimentos_consumidos = Counter()
    usuario_padrao = _obter_usuario_padrao_tenant(db=db, tenant_id=pedido.tenant_id)
    user_id_execucao = getattr(usuario_padrao, "id", None)
    venda_ja_confirmada = pedido.status == "confirmado" and all(item.vendido_em for item in itens)
    itens_confirmados = 0
    baixas_criadas = 0
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
            baixa_ja_existente = consumir_movimentacoes_esperadas(
                ids_esperados,
                movimentos_por_produto,
                movimentos_consumidos,
            )

            if baixa_ja_existente:
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
                documento=nf_numero or pedido.pedido_bling_numero,
                observacao=f"Baixa automatica via NF {nf_numero}" if nf_numero else f"Baixa automatica via NF Bling #{nf_id}",
            )
            movimentos_gerados = resultado_baixa.get("movimentos") or []
            if movimentos_gerados:
                for movimento in movimentos_gerados:
                    produto_id_mov = movimento.get("produto_id")
                    if produto_id_mov:
                        movimentos_consumidos[int(produto_id_mov)] += 1
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

    if venda_ja_confirmada and itens_confirmados == 0 and baixas_criadas == 0 and not houve_erros:
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
) -> str:
    pedido.status = "cancelado"
    pedido.cancelado_em = datetime.now(timezone.utc)

    for item in itens:
        EstoqueReservaService.liberar(db, item)

    db.add(pedido)
    db.commit()
    return "venda_cancelada"
