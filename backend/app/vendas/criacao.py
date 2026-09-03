"""Criacao de vendas do orquestrador de vendas."""

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Callable, Dict, List

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.utils.timezone import now_brasilia
from app.vendas.regras import validar_consistencia_desconto_cupom

logger = logging.getLogger(__name__)


def criar_venda(
    payload: Dict[str, Any],
    user_id: int,
    db: Session,
    *,
    gerar_numero_venda: Callable[..., str],
    processar_baixa_estoque_item: Callable[..., List[Dict[str, Any]]],
) -> Dict[str, Any]:
    """
    Cria uma nova venda com todas as validações e cálculos necessários.

    Operações executadas:
    1. Validar payload (itens obrigatórios, cliente, etc)
    2. Gerar número sequencial da venda
    3. Calcular totais (subtotal, desconto, frete)
    4. Criar registro de venda
    5. Criar itens da venda
    6. Criar lançamento financeiro previsto
    7. Criar conta a receber inicial
    8. COMMIT
    9. Retornar venda criada

    Args:
        payload: Dict com dados da venda:
            - cliente_id: Optional[int]
            - vendedor_id: Optional[int]
            - funcionario_id: Optional[int]
            - itens: List[dict] (obrigatório)
            - desconto_valor: float
            - desconto_percentual: float
            - observacoes: Optional[str]
            - tem_entrega: bool
            - taxa_entrega: float
            - entregador_id: Optional[int]
            - loja_origem: Optional[str]
            - endereco_entrega: Optional[str]
        user_id: ID do usuário criando a venda
        db: Sessão do SQLAlchemy

    Returns:
        Dict com venda criada (formato to_dict())

    Raises:
        HTTPException(400): Validação falhou (sem itens, etc)
    """
    from app.vendas_models import Venda, VendaItem
    from app.financeiro_models import LancamentoManual, CategoriaFinanceira
    from app.audit_log import log_action
    from app.vendas.racao_previsao import validar_previsao_fim_racao

    logger.info(f"📝 Criando nova venda para user_id={user_id}")

    try:
        # ============================================================
        # ETAPA 1: VALIDAÇÕES
        # ============================================================

        itens = payload.get("itens", [])
        if not itens or len(itens) == 0:
            raise HTTPException(
                status_code=400, detail="A venda deve ter pelo menos um item"
            )

        logger.debug(f"✅ Validação OK: {len(itens)} itens")

        # ============================================================
        # ETAPA 2: GERAR NÚMERO DA VENDA
        # ============================================================

        numero_venda = gerar_numero_venda(
            db,
            tenant_id=payload.get("tenant_id"),
            user_id=user_id,
        )
        logger.debug(f"✅ Número gerado: {numero_venda}")

        # ============================================================
        # ETAPA 3: CALCULAR TOTAIS
        # ============================================================

        subtotal_itens = sum(item["subtotal"] for item in itens)
        desconto_itens = sum(float(item.get("desconto_item") or 0) for item in itens)
        desconto_valor = (
            desconto_itens
            if desconto_itens > 0
            else float(payload.get("desconto_valor", 0) or 0)
        )
        try:
            validar_consistencia_desconto_cupom(
                cupom_code=payload.get("cupom_code"),
                cupom_discount_applied=payload.get("cupom_discount_applied"),
                desconto_total=desconto_valor,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        tem_entrega = bool(payload.get("tem_entrega", False))
        taxa_entrega = (payload.get("taxa_entrega", 0) or 0) if tem_entrega else 0
        total = subtotal_itens + taxa_entrega

        # 🚚 Calcular distribuição da taxa de entrega
        percentual_taxa_entregador = (
            (payload.get("percentual_taxa_entregador", 0) or 0) if tem_entrega else 0
        )
        percentual_taxa_loja = (
            (payload.get("percentual_taxa_loja", 100 if taxa_entrega > 0 else 0) or 0)
            if tem_entrega
            else 0
        )

        logger.info(
            f"📥 PAYLOAD RECEBIDO - percentual_taxa_entregador: {percentual_taxa_entregador}, percentual_taxa_loja: {percentual_taxa_loja}"
        )

        # Se não foi informado percentual mas tem taxa, assumir 100% para loja (compatibilidade)
        if (
            taxa_entrega > 0
            and percentual_taxa_entregador == 0
            and percentual_taxa_loja == 0
        ):
            percentual_taxa_loja = 100

        # Calcular valores baseados nos percentuais
        valor_taxa_entregador = (
            (taxa_entrega * percentual_taxa_entregador / 100) if taxa_entrega > 0 else 0
        )
        valor_taxa_loja = (
            (taxa_entrega * percentual_taxa_loja / 100) if taxa_entrega > 0 else 0
        )

        logger.info(
            f"💰 Totais: Subtotal=R$ {subtotal_itens:.2f}, "
            f"Frete=R$ {taxa_entrega:.2f}, Total=R$ {total:.2f}"
        )
        if taxa_entrega > 0:
            logger.info(
                f"🚚 Taxa entrega: Loja {percentual_taxa_loja}% (R$ {valor_taxa_loja:.2f}), "
                f"Entregador {percentual_taxa_entregador}% (R$ {valor_taxa_entregador:.2f})"
            )

        # ============================================================
        # ETAPA 4: CRIAR VENDA
        # ============================================================

        venda = Venda(
            numero_venda=numero_venda,
            cliente_id=payload.get("cliente_id"),
            vendedor_id=payload.get("vendedor_id") or user_id,
            funcionario_id=payload.get("funcionario_id"),
            subtotal=float(subtotal_itens),
            desconto_valor=float(desconto_valor),  # Desconto aplicado na venda
            desconto_percentual=payload.get("desconto_percentual", 0) or 0,
            cupom_code=(
                str(payload.get("cupom_code")).strip().upper()
                if payload.get("cupom_code")
                else None
            ),
            cupom_discount_applied=payload.get("cupom_discount_applied"),
            total=float(total),
            observacoes=payload.get("observacoes"),
            tem_entrega=tem_entrega,
            taxa_entrega=float(taxa_entrega),
            percentual_taxa_entregador=float(percentual_taxa_entregador),
            percentual_taxa_loja=float(percentual_taxa_loja),
            valor_taxa_entregador=float(valor_taxa_entregador),
            valor_taxa_loja=float(valor_taxa_loja),
            entregador_id=payload.get("entregador_id") if tem_entrega else None,
            loja_origem=payload.get("loja_origem") if tem_entrega else None,
            endereco_entrega=payload.get("endereco_entrega") if tem_entrega else None,
            distancia_km=payload.get("distancia_km") if tem_entrega else None,
            valor_por_km=payload.get("valor_por_km") if tem_entrega else None,
            observacoes_entrega=payload.get("observacoes_entrega")
            if tem_entrega
            else None,
            status_entrega="pendente" if tem_entrega else None,
            canal=payload.get("canal", "loja_fisica"),  # Canal de venda para DRE
            status="aberta",
            data_venda=now_brasilia(),
            user_id=user_id,
            tenant_id=payload.get("tenant_id"),
        )

        # 🔒 BLINDAGEM FINAL (obrigatória) - Garante que PostgreSQL gere o ID
        venda.id = None

        db.add(venda)
        db.flush()  # Para obter o ID

        logger.info(f"✅ Venda criada: ID={venda.id}, Número={numero_venda}")

        # ============================================================
        # ETAPA 5: CRIAR ITENS
        # ============================================================

        from app.produtos_models import Produto
        from app.empresa_grupo_estoque_compartilhado_service import (
            EmpresaGrupoEstoqueCompartilhadoService,
            contexto_tenant_estoque,
            resolver_tenant_estoque_item,
        )

        for item_data in itens:
            # 🔒 VALIDAÇÃO CRÍTICA: XOR entre produto_id e product_variation_id
            produto_id = item_data.get("produto_id")
            product_variation_id = item_data.get("product_variation_id")
            tipo_solicitado = str(item_data.get("tipo") or "produto").strip().lower()
            produto_catalogo = None
            produto_resolvido = None

            if produto_id and product_variation_id:
                raise HTTPException(
                    status_code=400,
                    detail="Item de venda não pode conter product_id e product_variation_id ao mesmo tempo",
                )

            # O tipo informado pelo cliente nunca pode burlar a regra do cadastro.
            # Todo item ligado ao catalogo e carregado no tenant e normalizado aqui.
            if produto_id:
                produto_resolvido = (
                    EmpresaGrupoEstoqueCompartilhadoService.resolver_produto_venda(
                        db, payload.get("tenant_id"), produto_id
                    )
                )
                produto_catalogo = produto_resolvido.produto
                if produto_catalogo.tipo_produto == "PAI":
                    raise HTTPException(
                        status_code=400,
                        detail=f"Produto '{produto_catalogo.nome}' é do tipo PAI e não pode ser vendido. Selecione uma variação.",
                    )
            elif product_variation_id:
                produto_catalogo = (
                    db.query(Produto)
                    .filter(
                        Produto.id == product_variation_id,
                        Produto.tenant_id == payload.get("tenant_id"),
                        Produto.tipo_produto == "VARIACAO",
                    )
                    .first()
                )
                if not produto_catalogo:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Variação de produto ID {product_variation_id} não encontrada",
                    )
            elif tipo_solicitado == "produto":
                raise HTTPException(
                    status_code=400,
                    detail="Item de venda deve conter product_id ou product_variation_id",
                )

            tipo_item = tipo_solicitado
            if produto_catalogo is not None:
                tipo_item = (
                    "produto"
                    if getattr(produto_catalogo, "controlar_estoque", True)
                    else "servico"
                )

            previsao_racao = validar_previsao_fim_racao(
                item_data,
                produto=produto_catalogo,
                cliente_id=payload.get("cliente_id"),
            )

            # 🔒 ISOLAMENTO MULTI-TENANT: tenant_id obrigatório
            item = VendaItem(
                venda_id=venda.id,
                tenant_id=payload.get(
                    "tenant_id"
                ),  # ✅ Dupla proteção: injeção automática + explícita
                tipo=tipo_item,
                produto_id=produto_id,
                product_variation_id=product_variation_id,
                servico_descricao=item_data.get("servico_descricao")
                or (
                    produto_catalogo.nome
                    if produto_catalogo is not None
                    and (
                        tipo_item == "servico"
                        or (
                            produto_resolvido is not None
                            and produto_resolvido.compartilhado
                        )
                    )
                    else None
                ),
                estoque_origem_tenant_id=(
                    produto_resolvido.tenant_origem_id
                    if produto_resolvido is not None and produto_resolvido.compartilhado
                    else None
                ),
                estoque_compartilhado_id=(
                    produto_resolvido.compartilhamento_id
                    if produto_resolvido is not None
                    else None
                ),
                estoque_origem_nome=(
                    produto_resolvido.empresa_origem_nome
                    if produto_resolvido is not None
                    else None
                ),
                quantidade=item_data["quantidade"],
                preco_unitario=item_data["preco_unitario"],
                desconto_item=item_data.get("desconto_item", 0) or 0,
                subtotal=item_data["subtotal"],
                lote_id=item_data.get("lote_id"),
                pet_id=item_data.get("pet_id"),
                racao_data_prevista_fim=previsao_racao.data_prevista,
                racao_prazo_estimado_dias=previsao_racao.prazo_dias,
            )
            db.add(item)

        # 🔥 CRÍTICO: Flush para persistir os itens antes de baixar estoque
        db.flush()

        logger.debug(f"✅ {len(itens)} itens adicionados")

        # ============================================================
        # ETAPA 6: CRIAR LANÇAMENTO PREVISTO E CONTA A RECEBER
        # ============================================================

        # Buscar ou criar categoria de receitas
        tenant_id = payload.get("tenant_id")
        categoria_receitas = (
            db.query(CategoriaFinanceira)
            .filter(
                CategoriaFinanceira.nome.ilike("%vendas%"),
                CategoriaFinanceira.tipo == "receita",
                CategoriaFinanceira.user_id == user_id,
                CategoriaFinanceira.tenant_id == tenant_id,
            )
            .first()
        )

        if not categoria_receitas:
            categoria_receitas = CategoriaFinanceira(
                nome="Receitas de Vendas",
                tipo="receita",
                user_id=user_id,
                tenant_id=tenant_id,
            )
            db.add(categoria_receitas)
            db.flush()

        # Criar lançamento previsto (30 dias)
        prazo_dias = 30
        data_prevista = date.today() + timedelta(days=prazo_dias)

        lancamento = LancamentoManual(
            tipo="entrada",
            valor=Decimal(str(total)),
            descricao=f"Venda {numero_venda} - A receber",
            data_lancamento=data_prevista,
            status="previsto",
            categoria_id=categoria_receitas.id,
            documento=f"VENDA-{venda.id}",
            fornecedor_cliente=venda.cliente.nome
            if venda.cliente
            else "Cliente Avulso",
            user_id=user_id,
            tenant_id=tenant_id,
        )
        db.add(lancamento)

        # ⚠️ IMPORTANTE: Contas a receber NÃO são criadas aqui!
        # Elas são criadas durante a FINALIZAÇÃO da venda (ContasReceberService.criar_de_venda)
        # Isso evita duplicação e permite tratamento correto de parcelamento

        logger.info(
            f"📊 Lançamento previsto criado (R$ {total:.2f} em {data_prevista})"
        )

        # ============================================================
        # ETAPA 6.5: BAIXAR ESTOQUE IMEDIATAMENTE (PRODUTOS SEPARADOS)
        # ============================================================
        # 🎯 NOVO FLUXO: Estoque é baixado no momento da criação da venda
        # Motivo: Produtos são fisicamente separados ao criar a venda (pedido/entrega)

        logger.info(
            f"🔍 Iniciando baixa de estoque para venda #{venda.id} ({numero_venda})"
        )

        estoque_baixado = []

        # Buscar itens recém-criados
        itens_criados = db.query(VendaItem).filter_by(venda_id=venda.id).all()
        logger.info(f"📋 Encontrados {len(itens_criados)} itens para processar estoque")

        for item in itens_criados:
            logger.info(
                f"  → Item: tipo={item.tipo}, produto_id={item.produto_id}, qtd={item.quantidade}"
            )

            if item.tipo == "produto" and item.produto_id:
                try:
                    from app.produtos_models import Produto

                    tenant_estoque, compartilhado = resolver_tenant_estoque_item(
                        item, tenant_id
                    )
                    with contexto_tenant_estoque(
                        tenant_estoque, tenant_id
                    ) as tenant_estoque_uuid:
                        produto = (
                            db.query(Produto)
                            .filter(
                                Produto.id == item.produto_id,
                                Produto.tenant_id == tenant_estoque_uuid,
                            )
                            .first()
                        )

                        if not produto:
                            logger.warning(
                                f"⚠️  Produto {item.produto_id} não encontrado ao criar venda"
                            )
                            continue

                        # A movimentação e a fila do Bling pertencem ao tenant de origem.
                        resultados = processar_baixa_estoque_item(
                            produto=produto,
                            quantidade_vendida=float(item.quantidade),
                            venda_id=venda.id,
                            user_id=0 if compartilhado else user_id,
                            tenant_id=tenant_estoque_uuid,
                            db=db,
                            product_variation_id=None,
                            venda_codigo=numero_venda,
                            observacao=(
                                f"Venda em estoque compartilhado pelo tenant {tenant_id}"
                                if compartilhado
                                else None
                            ),
                        )

                    estoque_baixado.extend(resultados)
                    logger.info(
                        f"📦 Estoque baixado ao criar venda: {produto.nome} -{item.quantidade}"
                    )

                except Exception as e:
                    logger.error(
                        f"❌ Erro ao baixar estoque do produto {item.produto_id}: {e}"
                    )
                    # Reverter transação se falhar baixa de estoque
                    db.rollback()
                    raise HTTPException(
                        status_code=400, detail=f"Erro ao baixar estoque: {str(e)}"
                    )

        if estoque_baixado:
            logger.info(
                f"✅ Estoque baixado: {len(estoque_baixado)} item(ns) processado(s)"
            )

        # ============================================================
        # ETAPA 7: COMMIT
        # ============================================================

        db.commit()
        db.refresh(venda)

        logger.info(f"✅ ✅ ✅ Venda {numero_venda} criada com sucesso! ✅ ✅ ✅")

        # ============================================================
        # ETAPA 8: AUDITORIA
        # ============================================================

        log_action(
            db,
            user_id,
            "CREATE",
            "vendas",
            venda.id,
            details=f"Venda {numero_venda} criada - Total: R$ {total:.2f}",
        )

        # ============================================================
        # ETAPA 9: EMITIR EVENTO DE DOMÍNIO
        # ============================================================

        # 🔒 EVENTOS DESABILITADOS TEMPORARIAMENTE (publish_event não exportado)
        # try:
        #     from app.domain.events import VendaCriada, publish_event
        #
        #     evento = VendaCriada(
        #         venda_id=venda.id,
        #         numero_venda=venda.numero_venda,
        #         user_id=user_id,
        #         cliente_id=venda.cliente_id,
        #         funcionario_id=venda.funcionario_id,
        #         total=float(venda.total),
        #         quantidade_itens=len(itens),
        #         tem_entrega=venda.tem_entrega,
        #         metadados={
        #             'taxa_entrega': float(taxa_entrega),
        #             'subtotal': float(subtotal_itens)
        #         }
        #     )
        #
        #     publish_event(evento)
        #     logger.debug(f"📢 Evento VendaCriada publicado (venda_id={venda.id})")
        #
        # except Exception as e:
        #     logger.error(f"⚠️  Erro ao publicar evento VendaCriada: {str(e)}", exc_info=True)
        #     # Não aborta a criação da venda

        try:
            from app.domain.events import VendaCriada, publish_event

            publish_event(
                VendaCriada(
                    venda_id=venda.id,
                    numero_venda=venda.numero_venda,
                    user_id=user_id,
                    cliente_id=venda.cliente_id,
                    funcionario_id=venda.funcionario_id,
                    total=float(venda.total),
                    quantidade_itens=len(itens),
                    tem_entrega=venda.tem_entrega,
                    metadados={
                        "taxa_entrega": float(taxa_entrega),
                        "subtotal": float(subtotal_itens),
                    },
                )
            )
            logger.debug("Evento VendaCriada publicado (venda_id=%s)", venda.id)
        except Exception as e:
            logger.error(
                "Erro ao publicar evento VendaCriada: %s", str(e), exc_info=True
            )

        return venda.to_dict()

    except HTTPException:
        db.rollback()
        logger.error("❌ HTTPException ao criar venda - Rollback executado")
        raise

    except Exception as e:
        db.rollback()
        logger.error(f"❌ ERRO CRÍTICO ao criar venda: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao criar venda: {str(e)}")
