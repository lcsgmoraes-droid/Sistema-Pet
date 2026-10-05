"""Rotas de devolução de vendas."""

import logging
from collections import defaultdict
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
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
from app.produtos_models import EstoqueMovimentacao
from app.utils.timezone import now_brasilia
from app.vendas.devolucao_dre import custo_original_item_devolvido
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

        if str(venda.status or "").lower() not in {
            "finalizada",
            "pago_nf",
            "baixa_parcial",
            "finalizada_devolucao",
            "finalizada_devolucao_parcial",
        }:
            raise HTTPException(
                status_code=400,
                detail="A venda não está em situação que permita devolução",
            )

        logger.info(
            f"✅ Venda encontrada: #{venda.numero_venda} - Total: R$ {venda.total}"
        )

        caixa_id = dados.get("caixa_id")
        itens_devolucao = dados.get("itens", [])
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

        if not itens_devolucao:
            logger.info("❌ Nenhum item selecionado")
            raise HTTPException(
                status_code=400, detail="Nenhum item selecionado para devolução"
            )

        # A venda guarda apenas o preço do kit, sem composição e rateio originais.
        # O preço enviado pelo navegador não comprova o valor do componente.
        if any(item.get("is_componente_kit") for item in itens_devolucao):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Devolução por componente de KIT indisponível: a venda não "
                    "registra o preço original de cada componente. Devolva o KIT inteiro."
                ),
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
        historico_pre_evento = (
            str(venda.status or "").lower()
            in {"finalizada_devolucao", "finalizada_devolucao_parcial"}
            and not eventos_anteriores
        ) or any(
            bool(getattr(evento, "historico_pre_evento", False))
            for evento in eventos_anteriores
        )
        if historico_pre_evento and any(
            str(getattr(item, "tipo", "") or "").lower() == "servico"
            for item in itens_venda
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Devolução de serviço indisponível nesta venda: houve "
                    "devolução anterior sem saldo rastreável. Confira o histórico."
                ),
            )
        devolvido_por_item = defaultdict(Decimal)
        for evento_anterior in eventos_anteriores:
            for item_anterior in evento_anterior.itens or []:
                if not item_anterior.get("is_componente_kit"):
                    devolvido_por_item[item_anterior.get("venda_item_id")] += Decimal(
                        str(item_anterior.get("quantidade") or 0)
                    )

        vendido_por_produto = defaultdict(float)
        for item_venda in db.query(VendaItem).filter_by(venda_id=venda_id).all():
            if item_venda.produto_id:
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
            if item_venda.produto_id:
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

        # Processar cada item devolvido
        for item_dev in itens_devolucao:
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

                # Devolver ao estoque
                if item_venda.produto_id:
                    try:
                        tenant_estoque, compartilhado = resolver_tenant_estoque_item(
                            item_venda, tenant_id
                        )
                        with contexto_tenant_estoque(
                            tenant_estoque, tenant_id
                        ) as tenant_estoque_uuid:
                            EstoqueService.estornar_estoque(
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
                            )
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

                # Calcular valor devolvido
                valor_item = item_venda.preco_unitario * Decimal(
                    str(quantidade_devolvida)
                )
                valor_total_devolucao += valor_item
                custo_item, origem_custo, custo_pendente = (
                    custo_original_item_devolvido(
                        db,
                        venda,
                        item_venda,
                        Decimal(str(quantidade_devolvida)),
                        tenant_id,
                    )
                )
                tipo_item = str(
                    getattr(item_venda, "tipo", "produto") or "produto"
                ).lower()
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
                        "valor_devolvido": str(valor_item.quantize(Decimal("0.01"))),
                        "custo_estornado": str(custo_item),
                        "origem_custo": origem_custo,
                        "custo_pendente": custo_pendente,
                    }
                )

                itens_devolvidos.append(
                    {
                        "produto_id": item_venda.produto_id,
                        "produto_nome": item_venda.produto.nome
                        if item_venda.produto
                        else item_venda.servico_descricao,
                        "quantidade": quantidade_devolvida,
                        "valor_unitario": item_venda.preco_unitario,
                        "valor_total": valor_item,
                        "tipo": "item_normal",
                    }
                )

        if valor_total_devolucao <= 0 or not itens_evento_dre:
            raise HTTPException(
                status_code=400, detail="A devolução precisa ter valor positivo"
            )

        valor_total_devolucao = valor_total_devolucao.quantize(Decimal("0.01"))
        valor_ja_devolvido = sum(
            (
                Decimal(str(getattr(evento, "valor_devolvido", 0) or 0))
                for evento in eventos_anteriores
            ),
            Decimal("0"),
        )
        valor_acumulado_devolvido = valor_ja_devolvido + valor_total_devolucao
        if valor_acumulado_devolvido > Decimal(str(venda.total or 0)).quantize(
            Decimal("0.01")
        ):
            raise HTTPException(
                status_code=400,
                detail="Valor acumulado das devoluções excede o total pago na venda",
            )

        # O evento é a fonte da dedução na DRE. Caixa e crédito são apenas formas
        # de liquidá-la; tudo abaixo participa da mesma transação e do mesmo commit.
        evento_dre = VendaDevolucao(
            tenant_id=tenant_id,
            venda_id=venda_id,
            user_id=current_user.id,
            data_competencia=now_brasilia().date(),
            canal=getattr(venda, "canal", None) or "loja_fisica",
            forma_estorno="credito" if gerar_credito else "dinheiro",
            motivo=motivo,
            valor_devolvido=valor_total_devolucao,
            custo_produtos_estornado=custo_produtos_estornado,
            custo_servicos_estornado=custo_servicos_estornado,
            custo_pendente=any(item["custo_pendente"] for item in itens_evento_dre),
            historico_pre_evento=historico_pre_evento,
            itens=itens_evento_dre,
        )
        db.add(evento_dre)
        db.flush()

        # 💰 OPÇÃO 1: GERAR CRÉDITO PARA O CLIENTE
        if gerar_credito:
            if not venda.cliente_id:
                raise HTTPException(
                    status_code=400,
                    detail="Não é possível gerar crédito para venda sem cliente cadastrado",
                )

            # O criador do cadastro pode ser outro funcionário da mesma loja.
            cliente = _obter_cliente_ou_404(db, venda.cliente_id, tenant_id)

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
                data_lancamento=date.today(),
                status="realizado",
                categoria_id=categoria_devolucoes.id,
                documento=f"DEVOLUCAO-{venda_id}",
                fornecedor_cliente=venda.cliente.nome
                if venda.cliente
                else "Cliente Avulso",
                user_id=current_user.id,
                tenant_id=tenant_id,
            )
            db.add(lancamento_devolucao)
            logger.info(
                f"📊 Lançamento de devolução criado: R$ {valor_total_devolucao:.2f}"
            )

        # 🆕 AJUSTAR CONTAS A RECEBER (sempre, independente de crédito ou dinheiro)
        from app.financeiro_models import (
            ContaReceber,
            LancamentoManual,
            CategoriaFinanceira,
        )

        contas_receber = db.query(ContaReceber).filter_by(venda_id=venda_id).all()
        if contas_receber:
            # Reduzir proporcionalmente o valor das contas pendentes ou estornar pagas
            for conta in contas_receber:
                if conta.status in ["pendente", "parcial"]:
                    proporcao = float(valor_total_devolucao) / float(venda.total)
                    reducao = float(conta.valor_original) * proporcao

                    conta.valor_original -= Decimal(str(reducao))
                    conta.valor_final -= Decimal(str(reducao))

                    # Se ficou zerada, marcar como cancelada
                    if conta.valor_final <= 0:
                        conta.status = "cancelada"

                    logger.info(
                        f"💳 Ajustando ContaReceber #{conta.id}: -R$ {reducao:.2f}"
                    )
                elif conta.status == "pago":
                    # Cancelar a conta paga (estorno)
                    conta.status = "estornada"
                    logger.info(f"💳 Estornando ContaReceber #{conta.id} (paga)")

        # 🆕 MARCAR LANÇAMENTOS MANUAIS REALIZADOS COMO ESTORNADOS (Fluxo de Caixa)
        # Não criar novos lançamentos de estorno — o DEVOLUCAO acima já registra a saída.
        # Apenas marcar os lançamentos de entrada da venda como estornados para controle.
        lancamentos_entrada = (
            db.query(LancamentoManual)
            .filter(
                LancamentoManual.documento == f"VENDA-{venda_id}",
                LancamentoManual.tipo == "entrada",
                LancamentoManual.status == "realizado",
            )
            .all()
        )
        for lanc in lancamentos_entrada:
            lanc.status = "estornado"
            logger.info(f"💸 LancamentoManual #{lanc.id} marcado como estornado")

        # 🆕 ATUALIZAR STATUS DA VENDA
        if valor_acumulado_devolvido >= Decimal(str(venda.total or 0)):
            venda.status = "devolvida_total"
        else:
            venda.status = "finalizada_devolucao"

        # 📝 GERAR HISTÓRICO DE DEVOLUÇÃO NA OBSERVAÇÃO
        from datetime import datetime

        # Determinar tipo de devolução
        if valor_acumulado_devolvido >= Decimal(str(venda.total or 0)):
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

        db.commit()

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

        logger.info("✅ Devolução concluída com sucesso!")
        logger.info(f"{'=' * 80}\n")
        return resultado

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
