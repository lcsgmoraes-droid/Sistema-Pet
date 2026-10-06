"""Rotas de devolução de vendas."""

import hashlib
import json
import logging
import unicodedata
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.audit_log import log_action
from app.auth.dependencies import get_current_user_and_tenant
from app.categorias_integridade import normalizar_nome_categoria
from app.caixa.service import CaixaService
from app.caixa.escopo import buscar_caixa_acessivel
from app.db import get_session
from app.empresa_grupo_estoque_compartilhado_service import (
    contexto_tenant_estoque,
    resolver_tenant_estoque_item,
)
from app.estoque.service import EstoqueService
from app.financeiro_models import ContaReceber
from app.produtos_models import EstoqueMovimentacao, Produto
from app.utils.timezone import now_brasilia
from app.vendas.devolucao_dre import custo_original_item_devolvido
from app.vendas.devolucao_valores import (
    cotar_devolucao,
    quantidades_devolvidas_por_item,
    validar_itens_devolucao,
)
from app.vendas.routes_common import (
    _obter_cliente_ou_404,
    _validar_tenant_e_obter_usuario,
)
from app.vendas_models import Venda, VendaItem
from app.vendas_devolucoes_models import VendaDevolucao

router = APIRouter()
logger = logging.getLogger(__name__)


def _validar_saldo_devolucao(
    quantidade_vendida: float,
    quantidade_ja_devolvida: float,
    quantidade_solicitada: float,
) -> float:
    quantidade_disponivel = max(quantidade_vendida - quantidade_ja_devolvida, 0)
    if quantidade_solicitada > quantidade_disponivel + 1e-9:
        raise HTTPException(
            status_code=400,
            detail=(
                "Quantidade de devolução excede o saldo vendido. "
                f"Disponível para devolver: {quantidade_disponivel:g}"
            ),
        )
    return quantidade_disponivel


def _buscar_categoria_devolucoes(db: Session, tenant_id):
    """Reutiliza a categoria de devolução, inclusive o nome plural legado."""
    from app.financeiro_models import CategoriaFinanceira

    candidatas = (
        db.query(CategoriaFinanceira)
        .filter(
            CategoriaFinanceira.tenant_id == tenant_id,
            CategoriaFinanceira.tipo == "despesa",
            CategoriaFinanceira.ativo.is_(True),
            CategoriaFinanceira.nome.ilike("%devolu%"),
        )
        .order_by(CategoriaFinanceira.id)
        .all()
    )
    return next(
        (
            categoria
            for categoria in candidatas
            if normalizar_nome_categoria(categoria.nome).startswith("devoluc")
            and "venda" in normalizar_nome_categoria(categoria.nome)
        ),
        None,
    )


def _recebivel_exige_conciliacao(conta: ContaReceber) -> bool:
    """Um saldo aberto impede desembolso e abatimento simultaneos ao cliente."""
    status = str(getattr(conta, "status", "") or "").lower()
    if status in {"cancelado", "cancelada"}:
        return False
    if status != "recebido":
        return True
    valor_final = Decimal(str(getattr(conta, "valor_final", 0) or 0))
    valor_recebido = Decimal(str(getattr(conta, "valor_recebido", 0) or 0))
    return valor_final > valor_recebido


def _validar_recebiveis_liquidados(db: Session, venda_id: int, tenant_id) -> None:
    contas_receber = (
        db.query(ContaReceber)
        .filter(
            ContaReceber.venda_id == venda_id,
            ContaReceber.tenant_id == tenant_id,
        )
        .all()
    )
    if any(_recebivel_exige_conciliacao(conta) for conta in contas_receber):
        raise HTTPException(
            status_code=409,
            detail=(
                "A venda tem recebivel em aberto. Concilie o valor recebido "
                "antes de registrar a devolucao."
            ),
        )


def _validar_pagamentos_beneficio(venda: Venda, tenant_id) -> None:
    """Impede converter cashback ou crédito usado no pagamento em espécie."""
    for pagamento in getattr(venda, "pagamentos", []) or []:
        if str(getattr(pagamento, "tenant_id", tenant_id)) != str(tenant_id):
            continue
        nome = str(getattr(pagamento, "forma_pagamento", "") or "")
        normalizado = "".join(
            caractere
            for caractere in unicodedata.normalize("NFKD", nome.lower())
            if not unicodedata.combining(caractere)
        )
        normalizado = normalizado.replace(" ", "_").replace("-", "_")
        if normalizado in {"cashback", "credito_cliente"}:
            raise HTTPException(
                status_code=409,
                detail=(
                    "A venda foi paga com cashback ou Credito Cliente. "
                    "Concilie a devolucao na forma original de pagamento."
                ),
            )


def _item_controlava_estoque_na_venda(item) -> bool:
    """O tipo salvo na venda distingue servico de catalogo com produto_id."""
    return (
        bool(getattr(item, "produto_id", None))
        and str(getattr(item, "tipo", "produto") or "").lower() == "produto"
    )


def _produto_estoque_original(db: Session, item, tenant_id):
    """Busca o produto no tenant dono do estoque, inclusive quando compartilhado."""
    tenant_estoque, _ = resolver_tenant_estoque_item(item, tenant_id)
    with contexto_tenant_estoque(tenant_estoque, tenant_id) as tenant_estoque_uuid:
        produto = (
            db.query(Produto)
            .filter(
                Produto.id == item.produto_id,
                Produto.tenant_id == tenant_estoque_uuid,
            )
            .first()
        )
    return produto, tenant_estoque


def _validar_estoque_devolucao_seguro(
    db: Session, venda_id: int, tenant_id, itens_venda, itens_solicitados
) -> None:
    """Exige saida rastreavel e evita recompor KIT virtual ou FIFO sem lote."""
    itens_por_id = {item.id: item for item in itens_venda}
    grupos_solicitados = set()
    quantidades_vendidas = defaultdict(Decimal)
    for item in itens_venda:
        if not _item_controlava_estoque_na_venda(item):
            continue
        tenant_estoque, _ = resolver_tenant_estoque_item(item, tenant_id)
        quantidades_vendidas[(item.produto_id, tenant_estoque)] += Decimal(
            str(item.quantidade or 0)
        )

    for solicitado in itens_solicitados:
        item = itens_por_id.get(solicitado.get("item_id"))
        if item is None or not _item_controlava_estoque_na_venda(item):
            continue
        produto, tenant_estoque = _produto_estoque_original(db, item, tenant_id)
        if produto is None:
            raise HTTPException(
                status_code=409,
                detail="Produto original indisponivel. Concilie o estoque manualmente.",
            )
        if getattr(produto, "controlar_estoque", True) is False:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Produto nao controla estoque atualmente. "
                    "Concilie a devolucao e o estoque manualmente."
                ),
            )
        if getattr(item, "lote_id", None) is not None:
            raise HTTPException(
                status_code=409,
                detail="Devolucao de item com lote exige recomposicao manual do estoque.",
            )
        if (
            getattr(produto, "tipo_produto", None) == "KIT"
            and (getattr(produto, "tipo_kit", None) or "VIRTUAL") != "FISICO"
        ):
            raise HTTPException(
                status_code=409,
                detail="KIT virtual exige devolucao e recomposicao manual dos componentes.",
            )
        grupos_solicitados.add((item.produto_id, tenant_estoque))

    for produto_id, tenant_estoque in grupos_solicitados:
        with contexto_tenant_estoque(tenant_estoque, tenant_id) as tenant_estoque_uuid:
            saidas = (
                db.query(EstoqueMovimentacao)
                .filter(
                    EstoqueMovimentacao.tenant_id == tenant_estoque_uuid,
                    EstoqueMovimentacao.produto_id == produto_id,
                    EstoqueMovimentacao.referencia_tipo == "venda",
                    EstoqueMovimentacao.referencia_id == venda_id,
                    EstoqueMovimentacao.tipo == "saida",
                    EstoqueMovimentacao.status != "cancelado",
                )
                .all()
            )
        if any(saida.lotes_consumidos for saida in saidas):
            raise HTTPException(
                status_code=409,
                detail="Devolucao de item com lote exige recomposicao manual do estoque.",
            )
        quantidade_saida = sum(
            (abs(Decimal(str(saida.quantidade or 0))) for saida in saidas),
            Decimal("0"),
        )
        if abs(
            quantidade_saida - quantidades_vendidas[(produto_id, tenant_estoque)]
        ) > Decimal("0.000001"):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Saida original de estoque nao rastreavel para o produto. "
                    "Concilie o estoque manualmente."
                ),
            )


def _hash_requisicao_devolucao(venda_id: int, dados: dict, itens: list) -> str:
    corpo = {
        "venda_id": venda_id,
        "itens": itens,
        "motivo": dados.get("motivo"),
        "gerar_credito": dados.get("gerar_credito", False),
        "caixa_id": dados.get("caixa_id"),
    }
    canonico = json.dumps(
        corpo, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
    )
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


@router.get("/{venda_id}/devolucao/saldos")
def consultar_saldos_devolucao(
    venda_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Mostra o saldo de cada linha da venda antes de selecionar a devolução."""
    _, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    venda = db.query(Venda).filter_by(id=venda_id, tenant_id=tenant_id).first()
    if not venda:
        raise HTTPException(status_code=404, detail="Venda não encontrada")

    itens_venda = (
        db.query(VendaItem)
        .filter(VendaItem.venda_id == venda_id, VendaItem.tenant_id == tenant_id)
        .all()
    )
    eventos_anteriores = (
        db.query(VendaDevolucao)
        .filter(
            VendaDevolucao.tenant_id == tenant_id,
            VendaDevolucao.venda_id == venda_id,
        )
        .all()
    )
    if (
        str(venda.status or "").lower()
        in {
            "finalizada_devolucao",
            "finalizada_devolucao_parcial",
        }
        and not eventos_anteriores
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Esta venda tem devolução anterior sem saldo rastreável. "
                "Concilie manualmente o histórico antes de nova devolução."
            ),
        )

    devolvidas = quantidades_devolvidas_por_item(eventos_anteriores)
    return {
        "venda_id": venda_id,
        "itens": [
            {
                "item_id": item.id,
                "quantidade_vendida": float(item.quantidade),
                "quantidade_devolvida": float(devolvidas.get(item.id, 0)),
                "quantidade_disponivel": float(
                    max(
                        Decimal("0"),
                        Decimal(str(item.quantidade)) - devolvidas.get(item.id, 0),
                    )
                ),
            }
            for item in itens_venda
        ],
    }


@router.post("/{venda_id}/devolucao/previa")
def prever_devolucao(
    venda_id: int,
    dados: dict,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Mostra o mesmo valor líquido que será usado no registro da devolução."""
    _, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    venda = db.query(Venda).filter_by(id=venda_id, tenant_id=tenant_id).first()
    if not venda:
        raise HTTPException(status_code=404, detail="Venda não encontrada")
    _validar_pagamentos_beneficio(venda, tenant_id)
    itens_venda = (
        db.query(VendaItem)
        .filter(VendaItem.venda_id == venda_id, VendaItem.tenant_id == tenant_id)
        .all()
    )
    eventos_anteriores = (
        db.query(VendaDevolucao)
        .filter(
            VendaDevolucao.tenant_id == tenant_id,
            VendaDevolucao.venda_id == venda_id,
        )
        .all()
    )
    try:
        cotacao = cotar_devolucao(
            venda, itens_venda, eventos_anteriores, dados.get("itens") or []
        )
    except ValueError as erro:
        raise HTTPException(status_code=400, detail=str(erro)) from erro
    from app.campaigns.sale_return_service import (
        preflight_purchase_benefits_on_return,
    )

    preflight_purchase_benefits_on_return(
        db,
        tenant_id=tenant_id,
        venda=venda,
        valor_acumulado=cotacao.valor_acumulado,
    )
    _validar_recebiveis_liquidados(db, venda_id, tenant_id)
    _validar_estoque_devolucao_seguro(
        db, venda_id, tenant_id, itens_venda, dados.get("itens") or []
    )
    return {
        "valor_total_devolucao": float(cotacao.valor_total),
        "valor_ja_devolvido": float(cotacao.valor_ja_devolvido),
        "valor_acumulado": float(cotacao.valor_acumulado),
        "itens": [
            {
                "item_id": item.get("item_id"),
                "valor_devolvido": float(valor),
            }
            for item, valor in zip(dados.get("itens") or [], cotacao.valores_itens)
        ],
    }


@router.post("/{venda_id}/devolucao")
def registrar_devolucao(
    venda_id: int,
    dados: dict,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Registrar devolução de itens de uma venda"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    try:
        logger.info(f"\n{'=' * 80}")
        logger.info(f"🔄 INICIANDO DEVOLUÇÃO - Venda #{venda_id}")
        logger.info("=" * 80)
        logger.info("Dados de devolucao recebidos")
        logger.info("Usuario autenticado para devolucao")
        logger.info("Tenant validado para devolucao")

        # Buscar a venda
        venda = (
            db.query(Venda)
            .filter_by(id=venda_id, tenant_id=tenant_id)
            .with_for_update()
            .first()
        )

        if not venda:
            logger.info(f"❌ Venda #{venda_id} não encontrada")
            raise HTTPException(status_code=404, detail="Venda não encontrada")

        status_venda = str(venda.status or "").lower()
        if status_venda not in {
            "finalizada",
            "pago_nf",
            "baixa_parcial",
            "finalizada_devolucao",
            "finalizada_devolucao_parcial",
            "devolvida_total",
        }:
            raise HTTPException(
                status_code=400,
                detail="A venda não está em situação que permita devolução",
            )

        itens_devolucao = dados.get("itens", [])
        try:
            validar_itens_devolucao(itens_devolucao)
        except ValueError as erro:
            raise HTTPException(status_code=400, detail=str(erro)) from erro

        try:
            chave_operacao = str(UUID(str(dados.get("chave_operacao"))))
        except (TypeError, ValueError, AttributeError) as erro:
            raise HTTPException(
                status_code=400, detail="Chave da operacao de devolucao invalida"
            ) from erro
        requisicao_hash = _hash_requisicao_devolucao(venda_id, dados, itens_devolucao)
        evento_existente = (
            db.query(VendaDevolucao)
            .filter(
                VendaDevolucao.tenant_id == tenant_id,
                VendaDevolucao.chave_operacao == chave_operacao,
            )
            .first()
        )
        if evento_existente:
            if evento_existente.venda_id != venda_id:
                raise HTTPException(
                    status_code=409,
                    detail="Chave de operacao ja utilizada em outra venda",
                )
            if evento_existente.requisicao_hash != requisicao_hash:
                raise HTTPException(
                    status_code=409,
                    detail="Chave de operacao reutilizada com dados diferentes",
                )
            return evento_existente.resposta
        if status_venda == "devolvida_total":
            raise HTTPException(
                status_code=400,
                detail="A venda nao possui saldo para outra devolucao",
            )
        _validar_pagamentos_beneficio(venda, tenant_id)

        logger.info(
            f"✅ Venda encontrada: #{venda.numero_venda} - Total: R$ {venda.total}"
        )

        caixa_id = dados.get("caixa_id")
        motivo = dados.get("motivo", "")
        gerar_credito = dados.get("gerar_credito", False)  # 🆕 Nova opção

        logger.info(f"💰 Modo: {'CRÉDITO ao cliente' if gerar_credito else 'DINHEIRO'}")
        logger.info(f"📝 Motivo: {motivo}")
        logger.info(f"📦 Itens para devolução: {len(itens_devolucao)}")

        if not caixa_id and not gerar_credito:
            logger.info("❌ Caixa ID não fornecido para devolução em dinheiro")
            raise HTTPException(
                status_code=400,
                detail="ID do caixa é obrigatório para devolução em dinheiro",
            )

        if not motivo:
            logger.info("❌ Motivo não fornecido")
            raise HTTPException(
                status_code=400, detail="Motivo da devolução é obrigatório"
            )

        if gerar_credito and not venda.cliente_id:
            raise HTTPException(
                status_code=400,
                detail="Não é possível gerar crédito para venda sem cliente cadastrado",
            )

        # Verificar se o caixa existe e está aberto (apenas se for devolução em dinheiro)
        caixa = None
        if not gerar_credito:
            caixa, _ = buscar_caixa_acessivel(
                db,
                caixa_id=caixa_id,
                tenant_id=tenant_id,
                usuario_id=current_user.id,
            )

            if not caixa or caixa.status != "aberto":
                raise HTTPException(
                    status_code=400, detail="Caixa não encontrado ou não está aberto"
                )

        itens_normais = [
            item
            for item in itens_devolucao
            if not item.get("is_componente_kit", False)
            and float(item.get("quantidade", 0) or 0) > 0
        ]
        itens_ids = {item.get("item_id") for item in itens_normais}
        itens_venda = (
            db.query(VendaItem)
            .filter(
                VendaItem.venda_id == venda_id,
                VendaItem.tenant_id == tenant_id,
                VendaItem.id.in_(itens_ids),
            )
            .all()
            if itens_ids
            else []
        )
        itens_normais_por_id = {item.id: item for item in itens_venda}

        ids_ausentes = itens_ids - set(itens_normais_por_id)
        if ids_ausentes:
            item_id = sorted(ids_ausentes, key=lambda valor: str(valor))[0]
            raise HTTPException(
                status_code=404,
                detail=f"Item {item_id} não encontrado na venda",
            )

        eventos_anteriores = (
            db.query(VendaDevolucao)
            .filter(
                VendaDevolucao.tenant_id == tenant_id,
                VendaDevolucao.venda_id == venda_id,
            )
            .all()
        )
        status_original_venda = (
            str(
                getattr(
                    min(
                        eventos_anteriores,
                        key=lambda evento: getattr(evento, "id", 0),
                    ),
                    "status_original_venda",
                    "",
                )
                or ""
            ).lower()
            if eventos_anteriores
            else status_venda
        )
        todos_itens_venda = (
            db.query(VendaItem)
            .filter(VendaItem.venda_id == venda_id, VendaItem.tenant_id == tenant_id)
            .all()
        )
        try:
            cotacao = cotar_devolucao(
                venda, todos_itens_venda, eventos_anteriores, itens_devolucao
            )
        except ValueError as erro:
            raise HTTPException(status_code=400, detail=str(erro)) from erro
        if dados.get("valor_previsto") is not None:
            try:
                valor_previsto = Decimal(str(dados["valor_previsto"])).quantize(
                    Decimal("0.01")
                )
            except (InvalidOperation, ValueError, TypeError) as erro:
                raise HTTPException(
                    status_code=400, detail="Valor previsto da devolução inválido"
                ) from erro
            if valor_previsto != cotacao.valor_total:
                raise HTTPException(
                    status_code=409,
                    detail="O valor da devolução mudou. Revise a prévia antes de confirmar.",
                )
        _validar_recebiveis_liquidados(db, venda_id, tenant_id)
        _validar_estoque_devolucao_seguro(
            db, venda_id, tenant_id, todos_itens_venda, itens_devolucao
        )
        devolvido_por_item = defaultdict(Decimal)
        for evento_anterior in eventos_anteriores:
            for item_anterior in evento_anterior.itens or []:
                if not item_anterior.get("is_componente_kit"):
                    devolvido_por_item[item_anterior.get("venda_item_id")] += Decimal(
                        str(item_anterior.get("quantidade") or 0)
                    )

        vendido_por_produto = defaultdict(float)
        for item_venda in todos_itens_venda:
            if _item_controlava_estoque_na_venda(item_venda):
                origem, _compartilhado = resolver_tenant_estoque_item(
                    item_venda, tenant_id
                )
                vendido_por_produto[(item_venda.produto_id, origem)] += float(
                    item_venda.quantidade or 0
                )

        solicitado_por_produto = defaultdict(float)
        solicitado_por_item = defaultdict(Decimal)
        for item_dev in itens_normais:
            item_venda = itens_normais_por_id[item_dev.get("item_id")]
            quantidade_devolvida = float(item_dev.get("quantidade", 0) or 0)
            if quantidade_devolvida > float(item_venda.quantidade or 0):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Quantidade devolvida ({quantidade_devolvida}) maior que "
                        f"quantidade vendida ({item_venda.quantidade})"
                    ),
                )
            solicitado_por_item[item_venda.id] += Decimal(str(quantidade_devolvida))
            if devolvido_por_item[item_venda.id] + solicitado_por_item[
                item_venda.id
            ] > Decimal(str(item_venda.quantidade)):
                raise HTTPException(
                    status_code=400,
                    detail="Quantidade de devolução excede o saldo deste item",
                )
            if _item_controlava_estoque_na_venda(item_venda):
                origem, _compartilhado = resolver_tenant_estoque_item(
                    item_venda, tenant_id
                )
                solicitado_por_produto[(item_venda.produto_id, origem)] += (
                    quantidade_devolvida
                )

        for (
            produto_id,
            tenant_estoque,
        ), quantidade_solicitada in solicitado_por_produto.items():
            with contexto_tenant_estoque(
                tenant_estoque, tenant_id
            ) as tenant_estoque_uuid:
                quantidade_ja_devolvida = float(
                    db.query(func.coalesce(func.sum(EstoqueMovimentacao.quantidade), 0))
                    .filter(
                        EstoqueMovimentacao.tenant_id == tenant_estoque_uuid,
                        EstoqueMovimentacao.produto_id == produto_id,
                        EstoqueMovimentacao.referencia_tipo == "venda",
                        EstoqueMovimentacao.referencia_id == venda_id,
                        EstoqueMovimentacao.motivo == "devolucao",
                        EstoqueMovimentacao.status != "cancelado",
                    )
                    .scalar()
                    or 0
                )
            _validar_saldo_devolucao(
                vendido_por_produto[(produto_id, tenant_estoque)],
                quantidade_ja_devolvida,
                quantidade_solicitada,
            )

        valor_total_devolucao = Decimal("0")
        itens_devolvidos = []
        itens_evento_dre = []
        custo_produtos_estornado = Decimal("0")
        custo_servicos_estornado = Decimal("0")
        processado_por_item = defaultdict(Decimal)

        # Processar cada item devolvido
        for indice, item_dev in enumerate(itens_devolucao):
            # 🆕 Verificar se é componente de KIT
            is_componente_kit = item_dev.get("is_componente_kit", False)

            if is_componente_kit:
                # 🔥 DEVOLUÇÃO DE COMPONENTE DE KIT
                produto_id = item_dev.get("produto_id")
                quantidade_devolvida = float(item_dev.get("quantidade", 0))
                preco_unitario_componente = float(item_dev.get("preco_unitario", 0))
                kit_item_id = item_dev.get("kit_item_id")

                if quantidade_devolvida <= 0:
                    continue

                logger.info(
                    f"📦 Devolvendo componente do KIT - Produto ID: {produto_id}, Quantidade: {quantidade_devolvida}"
                )

                # Devolver componente ao estoque
                try:
                    EstoqueService.estornar_estoque(
                        produto_id=produto_id,
                        quantidade=quantidade_devolvida,
                        motivo="devolucao",
                        referencia_id=venda_id,
                        referencia_tipo="venda",
                        user_id=current_user.id,
                        tenant_id=tenant_id,
                        db=db,
                        documento=None,
                        observacao=f"{motivo} - Componente de KIT (Item #{kit_item_id})",
                        custo_unitario_override=0.0,
                        valor_total_override=0.0,
                    )

                    # Buscar nome do produto
                    from app.produtos_models import Produto

                    produto = db.query(Produto).filter_by(id=produto_id).first()
                    produto_nome = produto.nome if produto else f"Produto #{produto_id}"

                    logger.info(
                        f"  ✅ Componente estornado: {produto_nome} +{quantidade_devolvida}"
                    )

                    # Registrar auditoria
                    log_action(
                        db=db,
                        user_id=current_user.id,
                        action="update",
                        entity_type="produtos",
                        entity_id=produto_id,
                        details=f"Devolução de componente de KIT (+{quantidade_devolvida}) - Venda #{venda_id} - Motivo: {motivo}",
                        commit=False,
                    )
                except ValueError as e:
                    logger.error(f"Erro ao devolver componente de KIT: {e}")
                    raise HTTPException(status_code=400, detail=str(e)) from e

                # Calcular valor devolvido do componente
                valor_componente = Decimal(str(preco_unitario_componente)) * Decimal(
                    str(quantidade_devolvida)
                )
                valor_total_devolucao += valor_componente
                itens_evento_dre.append(
                    {
                        "venda_item_id": kit_item_id,
                        "produto_id": produto_id,
                        "tipo": "produto",
                        "is_componente_kit": True,
                        "quantidade": str(Decimal(str(quantidade_devolvida))),
                        "valor_devolvido": str(
                            valor_componente.quantize(Decimal("0.01"))
                        ),
                        "custo_estornado": "0.00",
                        "origem_custo": "kit_componente_sem_rateio_original",
                        "custo_pendente": True,
                    }
                )

                itens_devolvidos.append(
                    {
                        "produto_id": produto_id,
                        "produto_nome": produto_nome,
                        "quantidade": quantidade_devolvida,
                        "valor_unitario": preco_unitario_componente,
                        "valor_total": valor_componente,
                        "tipo": "componente_kit",
                    }
                )

            else:
                # 🔹 DEVOLUÇÃO NORMAL (Item inteiro - pode ser KIT inteiro ou produto simples)
                item_id = item_dev.get("item_id")
                quantidade_devolvida = float(item_dev.get("quantidade", 0))

                if quantidade_devolvida <= 0:
                    continue

                item_venda = itens_normais_por_id[item_id]
                quantidade_decimal = Decimal(str(quantidade_devolvida))
                valor_item = cotacao.valores_itens[indice]
                tipo_item = str(
                    getattr(item_venda, "tipo", "produto") or "produto"
                ).lower()
                custo_original, origem_custo, custo_pendente = (
                    custo_original_item_devolvido(
                        db,
                        venda,
                        item_venda,
                        quantidade_decimal,
                        tenant_id,
                        devolvido_por_item[item_id] + processado_por_item[item_id],
                    )
                )
                # Reembolso de serviço não comprova reversão de mão de obra/insumos.
                custo_item = Decimal("0") if tipo_item == "servico" else custo_original
                if tipo_item == "servico":
                    origem_custo = "servico_custo_mantido"

                # Devolver ao estoque
                produto_nome_estoque = None
                if _item_controlava_estoque_na_venda(item_venda):
                    try:
                        tenant_estoque, compartilhado = resolver_tenant_estoque_item(
                            item_venda, tenant_id
                        )
                        # Sem custo original comprovado, a entrada fica com
                        # valor zero provisório e exige ajuste manual. Nunca
                        # usa o preço de custo atual como custo histórico.
                        custo_estoque = {
                            "custo_unitario_override": (
                                0.0
                                if custo_pendente
                                else float(custo_item / quantidade_decimal)
                            ),
                            "valor_total_override": (
                                0.0 if custo_pendente else float(custo_item)
                            ),
                        }
                        with contexto_tenant_estoque(
                            tenant_estoque, tenant_id
                        ) as tenant_estoque_uuid:
                            resultado_estoque = EstoqueService.estornar_estoque(
                                produto_id=item_venda.produto_id,
                                quantidade=quantidade_devolvida,
                                motivo="devolucao",
                                referencia_id=venda_id,
                                referencia_tipo="venda",
                                user_id=0 if compartilhado else current_user.id,
                                tenant_id=tenant_estoque_uuid,
                                db=db,
                                documento=None,
                                observacao=(
                                    f"{motivo}. Venda originada no tenant {tenant_id}."
                                    if compartilhado
                                    else motivo
                                ),
                                **custo_estoque,
                            )
                        if isinstance(resultado_estoque, dict):
                            produto_nome_estoque = resultado_estoque.get("produto_nome")
                        # Registrar auditoria
                        log_action(
                            db=db,
                            user_id=current_user.id,
                            action="update",
                            entity_type="produtos",
                            entity_id=item_venda.produto_id,
                            details=f"Devolução de estoque (+{quantidade_devolvida}) - Venda #{venda_id} - Motivo: {motivo}",
                            commit=False,
                        )
                    except ValueError as e:
                        logger.error(f"Erro ao devolver estoque: {e}")
                        raise HTTPException(status_code=400, detail=str(e)) from e

                # A prévia e o registro usam exatamente a mesma cotação.
                valor_total_devolucao += valor_item
                processado_por_item[item_id] += quantidade_decimal
                if tipo_item == "servico":
                    custo_servicos_estornado += custo_item
                else:
                    custo_produtos_estornado += custo_item
                itens_evento_dre.append(
                    {
                        "venda_item_id": item_venda.id,
                        "produto_id": item_venda.produto_id,
                        "tipo": tipo_item,
                        "is_componente_kit": False,
                        "quantidade": str(Decimal(str(quantidade_devolvida))),
                        "valor_devolvido": str(valor_item),
                        "custo_original": (
                            str(custo_original) if not custo_pendente else None
                        ),
                        "custo_estornado": str(custo_item),
                        "origem_custo": origem_custo,
                        "custo_pendente": custo_pendente,
                    }
                )

                itens_devolvidos.append(
                    {
                        "produto_id": item_venda.produto_id,
                        "produto_nome": produto_nome_estoque
                        or (
                            item_venda.produto.nome
                            if item_venda.produto
                            else item_venda.servico_descricao
                        ),
                        "quantidade": quantidade_devolvida,
                        "valor_unitario": (valor_item / quantidade_decimal).quantize(
                            Decimal("0.01")
                        ),
                        "preco_unitario_original": item_venda.preco_unitario,
                        "valor_total": valor_item,
                        "tipo": "item_normal",
                    }
                )

        if valor_total_devolucao <= 0 or not itens_evento_dre:
            raise HTTPException(
                status_code=400, detail="A devolução precisa ter valor positivo"
            )

        if valor_total_devolucao != cotacao.valor_total:
            raise RuntimeError("Cotação e itens da devolução divergiram")

        # O evento é a fonte da dedução na DRE. Caixa e crédito são apenas formas
        # de liquidá-la; tudo abaixo participa da mesma transação e do mesmo commit.
        evento_dre = VendaDevolucao(
            tenant_id=tenant_id,
            venda_id=venda_id,
            chave_operacao=chave_operacao,
            requisicao_hash=requisicao_hash,
            resposta={},
            user_id=current_user.id,
            data_competencia=now_brasilia().date(),
            canal=getattr(venda, "canal", None) or "loja_fisica",
            status_original_venda=status_original_venda,
            forma_estorno="credito" if gerar_credito else "dinheiro",
            motivo=motivo,
            valor_devolvido=valor_total_devolucao,
            custo_produtos_estornado=custo_produtos_estornado,
            custo_servicos_estornado=custo_servicos_estornado,
            custo_pendente=any(item["custo_pendente"] for item in itens_evento_dre),
            itens=itens_evento_dre,
        )
        db.add(evento_dre)
        db.flush()
        from app.campaigns.sale_return_service import (
            reconcile_purchase_benefits_on_return,
        )

        reconcile_purchase_benefits_on_return(
            db,
            tenant_id=tenant_id,
            venda=venda,
            evento_devolucao=evento_dre,
            valor_acumulado=cotacao.valor_acumulado,
        )

        # 💰 OPÇÃO 1: GERAR CRÉDITO PARA O CLIENTE
        if gerar_credito:
            if not venda.cliente_id:
                raise HTTPException(
                    status_code=400,
                    detail="Não é possível gerar crédito para venda sem cliente cadastrado",
                )

            # O criador do cadastro pode ser outro funcionário da mesma loja.
            cliente = _obter_cliente_ou_404(
                db, venda.cliente_id, tenant_id, bloquear_credito=True
            )

            # Adicionar crédito ao cliente
            cliente.credito = (cliente.credito or Decimal("0")) + Decimal(
                str(valor_total_devolucao)
            )
            credito_cliente_resultado = float(cliente.credito)
            cliente_nome_resultado = cliente.nome
            logger.info(
                f"💰 Crédito adicionado ao cliente {cliente.nome}: +R$ {valor_total_devolucao:.2f} (Total: R$ {cliente.credito:.2f})"
            )

            # Não cria MovimentacaoCaixa nem LancamentoManual (apenas crédito)

        # 💵 OPÇÃO 2: DEVOLUÇÃO EM DINHEIRO
        else:
            # Verificar se o caixa existe e está aberto
            caixa, _ = buscar_caixa_acessivel(
                db,
                caixa_id=caixa_id,
                tenant_id=tenant_id,
                usuario_id=current_user.id,
            )

            if not caixa or caixa.status != "aberto":
                raise HTTPException(
                    status_code=400, detail="Caixa não encontrado ou não está aberto"
                )

            # Registrar devolução no caixa usando o service
            movimentacao = CaixaService.registrar_devolucao(
                caixa_id=caixa_id,
                venda_id=venda_id,
                venda_numero=venda.numero_venda,
                valor=valor_total_devolucao,
                motivo=motivo,
                user_id=current_user.id,
                user_nome=current_user.nome,
                tenant_id=tenant_id,  # 🔒 Isolamento multi-tenant
                db=db,
            )
            evento_dre.movimentacao_caixa_id = movimentacao["movimentacao_id"]

            # Criar lançamento manual de saída (estorno no fluxo de caixa)
            from app.financeiro_models import LancamentoManual, CategoriaFinanceira

            categoria_devolucoes = _buscar_categoria_devolucoes(db, tenant_id)

            if not categoria_devolucoes:
                categoria_devolucoes = CategoriaFinanceira(
                    nome="Devoluções de Vendas",
                    tipo="despesa",
                    user_id=current_user.id,
                    tenant_id=tenant_id,
                )
                db.add(categoria_devolucoes)
                db.flush()

            lancamento_devolucao = LancamentoManual(
                tipo="saida",
                valor=Decimal(str(valor_total_devolucao)),
                descricao=f"Devolução venda {venda.numero_venda} - {motivo}",
                data_lancamento=evento_dre.data_competencia,
                status="realizado",
                categoria_id=categoria_devolucoes.id,
                documento=f"DEVOLUCAO-{venda_id}",
                fornecedor_cliente=(
                    venda.cliente.nome if venda.cliente else "Cliente Avulso"
                ),
                user_id=current_user.id,
                tenant_id=tenant_id,
            )
            db.add(lancamento_devolucao)
            logger.info(
                f"📊 Lançamento de devolução criado: R$ {valor_total_devolucao:.2f}"
            )

        # Recebimentos e entradas realizados permanecem como historico. O evento
        # da devolucao registra a deducao da DRE e a saida de caixa, se houver.

        # O frete não é reembolsado na devolução dos itens; o status total
        # depende da quantidade devolvida, não do valor total com frete.
        todos_itens_devolvidos = bool(todos_itens_venda) and all(
            devolvido_por_item[item.id] + solicitado_por_item[item.id]
            >= Decimal(str(item.quantidade))
            for item in todos_itens_venda
        )
        if todos_itens_devolvidos:
            venda.status = "devolvida_total"
        else:
            venda.status = "finalizada_devolucao"

        # 📝 GERAR HISTÓRICO DE DEVOLUÇÃO NA OBSERVAÇÃO
        from datetime import datetime

        # Determinar tipo de devolução
        if cotacao.valor_acumulado >= Decimal(str(venda.total or 0)):
            tipo_desc = "Devolução total"
        else:
            # Verificar se tem componentes de KIT
            tem_componentes = any(
                item.get("tipo") == "componente_kit" for item in itens_devolvidos
            )
            if tem_componentes:
                tipo_desc = "Devolução parcial por componentes de KIT"
            else:
                tipo_desc = "Devolução parcial"

        # Montar histórico
        historico = f"\n\n{'=' * 60}\n"
        historico += f"[DEVOLUÇÃO | {datetime.now().strftime('%d/%m/%Y %H:%M')}]\n"
        historico += f"Usuário: {current_user.nome}\n"
        historico += f"Tipo: {tipo_desc}\n"

        # Agrupar itens por tipo
        itens_kit = [i for i in itens_devolvidos if i.get("tipo") == "componente_kit"]
        itens_normais = [
            i for i in itens_devolvidos if i.get("tipo") != "componente_kit"
        ]

        # Listar itens normais
        if itens_normais:
            historico += "Itens devolvidos:\n"
            for item in itens_normais:
                historico += f"  • {item['produto_nome']} → {item['quantidade']} un (R$ {float(item['valor_total']):.2f})\n"

        # Listar componentes de KIT
        if itens_kit:
            historico += "Componentes de KIT devolvidos:\n"
            for item in itens_kit:
                historico += f"  • {item['produto_nome']} → {item['quantidade']} un (R$ {float(item['valor_total']):.2f})\n"

        historico += f"Motivo: {motivo}\n"
        historico += "Forma de estorno:\n"

        if gerar_credito:
            historico += (
                f"  • Crédito em cliente → R$ {float(valor_total_devolucao):.2f}\n"
            )
        else:
            historico += (
                f"  • Dinheiro (Caixa) → R$ {float(valor_total_devolucao):.2f}\n"
            )

        historico += f"Valor total estornado: R$ {float(valor_total_devolucao):.2f}\n"
        historico += f"{'=' * 60}"

        # Anexar histórico à observação (APPEND, nunca sobrescrever)
        if venda.observacoes:
            venda.observacoes = venda.observacoes + historico
        else:
            venda.observacoes = historico.lstrip()

        logger.info("📝 Histórico de devolução adicionado às observações da venda")

        # Registrar auditoria da devolução
        tipo_devolucao = "Crédito ao cliente" if gerar_credito else "Dinheiro"
        log_action(
            db=db,
            user_id=current_user.id,
            action="devolucao",
            entity_type="vendas",
            entity_id=venda_id,
            details=f"Devolução registrada ({tipo_devolucao}) - Venda #{venda_id} - R$ {valor_total_devolucao:.2f} - Motivo: {motivo}",
            commit=False,
        )

        resultado = {
            "message": "Devolução registrada com sucesso",
            "venda_id": venda_id,
            "valor_total_devolucao": float(valor_total_devolucao),
            "tipo_devolucao": tipo_devolucao,
            "status_venda": venda.status,
            "itens_devolvidos": itens_devolvidos,
            "devolucao_id": evento_dre.id,
            "custo_pendente_dre": evento_dre.custo_pendente,
        }

        if gerar_credito:
            resultado["credito_cliente"] = credito_cliente_resultado
            resultado["cliente_nome"] = cliente_nome_resultado
        else:
            resultado["movimentacao_caixa_id"] = movimentacao["movimentacao_id"]

        resposta = jsonable_encoder(resultado)
        evento_dre.resposta = resposta
        db.commit()

        logger.info("✅ Devolução concluída com sucesso!")
        logger.info(f"{'=' * 80}\n")
        return resposta

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        logger.info(f"\n{'=' * 80}")
        logger.info("🚨 ERRO CRÍTICO NA DEVOLUÇÃO:")
        logger.info(f"{'=' * 80}")
        logger.info(f"Tipo: {type(e).__name__}")
        logger.info(f"Mensagem: {str(e)}")
        import traceback

        logger.info("Traceback completo:")
        traceback.print_exc()
        logger.info(f"{'=' * 80}\n")
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Erro ao processar devolução: {str(e)}"
        )


# ============================================================================
# ENDPOINTS - RELATÓRIOS
