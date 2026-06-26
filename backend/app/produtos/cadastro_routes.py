"""Rotas de cadastro, detalhe e edicao completa de produtos."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.produtos.core import (
    _nome_indica_granel,
    _normalizar_payload_granel,
    _normalizar_promocao_erp_payload,
    _normalizar_sku_produto,
)
from app.produtos.listagem import _resolver_promocao_erp_produto
from app.produtos.racao import _normalizar_payload_racao
from app.produtos.schemas import ProdutoCreate, ProdutoResponse, ProdutoUpdate
from app.produtos.validators import _validar_sku_unico, _validar_tenant_e_obter_usuario
from app.produtos_models import Categoria, Marca, Produto, ProdutoKitComponente
from app.security.permissions_decorator import require_permission
from app.services.produto_service import ProdutoService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", response_model=ProdutoResponse, status_code=status.HTTP_201_CREATED)
@require_permission("produtos.criar")
def criar_produto(
    produto: ProdutoCreate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Cria um novo produto"""

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # LOG: Dados recebidos
    logger.info("Criando produto")
    logger.info("Dados de produto recebidos para criacao")
    produto.codigo = _normalizar_sku_produto(produto.codigo)

    # ========================================
    # VALIDAÃ‡Ã•ES DE INFRAESTRUTURA (mantidas na rota)
    # ========================================

    _validar_sku_unico(db, produto.codigo, tenant_id)

    # Verificar se cÃ³digo de barras jÃ¡ existe
    if produto.codigo_barras:
        existe_barcode = (
            db.query(Produto)
            .filter(
                Produto.codigo_barras == produto.codigo_barras,
                Produto.tenant_id == tenant_id,
            )
            .first()
        )

        if existe_barcode:
            raise HTTPException(
                status_code=400,
                detail=f"CÃ³digo de barras '{produto.codigo_barras}' jÃ¡ cadastrado",
            )

    # Verificar se categoria existe
    if produto.categoria_id:
        categoria = (
            db.query(Categoria)
            .filter(
                Categoria.id == produto.categoria_id,
                Categoria.tenant_id == tenant_id,
                Categoria.ativo.is_(True),
            )
            .first()
        )
        if not categoria:
            raise HTTPException(status_code=404, detail="Categoria nÃ£o encontrada")

    # Verificar se marca existe
    if produto.marca_id:
        marca = (
            db.query(Marca)
            .filter(
                Marca.id == produto.marca_id,
                Marca.tenant_id == tenant_id,
                Marca.ativo.is_(True),
            )
            .first()
        )
        if not marca:
            raise HTTPException(status_code=404, detail="Marca nÃ£o encontrada")

    # ========================================
    # ðŸ”’ TRAVA 3 â€” VALIDAÃ‡ÃƒO: PRODUTO PAI NÃƒO TEM PREÃ‡O
    # ========================================
    if produto.tipo_produto == "PAI":
        if produto.preco_venda and produto.preco_venda > 0:
            raise HTTPException(
                status_code=400,
                detail="âŒ Produto pai nÃ£o pode ter preÃ§o de venda. O preÃ§o deve ser definido nas variaÃ§Ãµes individuais.",
            )
        # Verificar estoque_atual se existir no modelo (pode nÃ£o existir em ProdutoCreate)
        estoque = getattr(produto, "estoque_atual", None)
        if estoque and estoque > 0:
            raise HTTPException(
                status_code=400,
                detail="âŒ Produto pai nÃ£o pode ter estoque inicial. O estoque deve ser gerenciado nas variaÃ§Ãµes.",
            )

    # ========================================
    # ðŸ”’ VALIDAÃ‡ÃƒO: VARIAÃ‡ÃƒO DUPLICADA
    # ========================================
    # Se estÃ¡ criando uma VARIAÃ‡ÃƒO, verificar duplicidade por signature
    variation_sig = getattr(produto, "variation_signature", None)
    if produto.produto_pai_id and variation_sig:
        variacao_existente = (
            db.query(Produto)
            .filter(
                Produto.tenant_id == tenant_id,
                Produto.produto_pai_id == produto.produto_pai_id,
                Produto.variation_signature == variation_sig,
                Produto.ativo.is_(True),
            )
            .first()
        )

        if variacao_existente:
            raise HTTPException(
                status_code=409,
                detail=f"âŒ JÃ¡ existe uma variaÃ§Ã£o com os mesmos atributos para este produto. VariaÃ§Ã£o existente: '{variacao_existente.nome}' (ID: {variacao_existente.id})",
            )

    # ========================================
    # ðŸ”’ PREDECESSOR/SUCESSOR: Marcar predecessor como descontinuado
    # ========================================
    if produto.produto_predecessor_id:
        predecessor = (
            db.query(Produto)
            .filter(
                Produto.id == produto.produto_predecessor_id,
                Produto.tenant_id == tenant_id,
            )
            .first()
        )

        if not predecessor:
            raise HTTPException(
                status_code=404, detail="Produto predecessor nÃ£o encontrado"
            )

        # Marcar predecessor como descontinuado
        predecessor.data_descontinuacao = datetime.utcnow()
        if produto.motivo_descontinuacao:
            predecessor.motivo_descontinuacao = produto.motivo_descontinuacao
        else:
            predecessor.motivo_descontinuacao = f"SubstituÃ­do por: {produto.nome}"

        logger.info(
            f"ðŸ“¦ Produto predecessor {predecessor.id} marcado como descontinuado"
        )

    # ========================================
    # DELEGAR PARA SERVICE LAYER
    # ========================================

    try:
        # Preparar dados do produto
        produto_data = _normalizar_promocao_erp_payload(
            _normalizar_payload_granel(_normalizar_payload_racao(produto.model_dump()))
        )

        # Adicionar user_id aos dados (necessÃ¡rio para o modelo)
        produto_data["user_id"] = current_user.id

        # Chamar service com regras de negÃ³cio
        novo_produto = ProdutoService.create_produto(
            dados=produto_data, db=db, tenant_id=tenant_id
        )

        logger.info(f"âœ… Produto criado com sucesso! ID: {novo_produto.id}")
        return novo_produto

    except ValueError as e:
        # Erros de validaÃ§Ã£o de negÃ³cio
        logger.warning(f"âš ï¸ ValidaÃ§Ã£o de negÃ³cio falhou: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"âŒ Erro ao criar produto: {str(e)}")
        logger.error(f"âŒ Tipo do erro: {type(e).__name__}")
        raise HTTPException(status_code=500, detail=f"Erro ao criar produto: {str(e)}")


# ============================================================================
# LISTAGEM DE PRODUTOS
# ============================================================================


@router.get("/{produto_id}", response_model=ProdutoResponse)
def obter_produto(
    produto_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    ObtÃ©m detalhes completos de um produto

    Para produtos do tipo KIT:
    - Retorna composicao_kit (lista de componentes)
    - Retorna estoque_virtual (calculado automaticamente se tipo_kit=VIRTUAL)
    """

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    produto = (
        db.query(Produto)
        .filter(Produto.id == produto_id, Produto.tenant_id == tenant_id)
        .options(
            joinedload(Produto.imagens),
            joinedload(Produto.categoria),
            joinedload(Produto.marca),
        )
        .first()
    )

    if not produto:
        raise HTTPException(status_code=404, detail="Produto nÃ£o encontrado")

    # Preparar resposta base
    response_data = {
        **produto.__dict__,
        "categoria": produto.categoria,
        "marca": produto.marca,
        "imagens": produto.imagens,
        "lotes": produto.lotes,
        "composicao_kit": [],
        "estoque_virtual": None,
        "estoque_disponivel": None,
    }

    # ========================================
    # PROCESSAR PRODUTOS DO TIPO KIT ou VARIACAO-KIT
    # ========================================
    if produto.tipo_produto in ("KIT", "VARIACAO") and produto.tipo_kit:
        from app.services.kit_estoque_service import KitEstoqueService
        from app.services.kit_custo_service import KitCustoService

        # Buscar composiÃ§Ã£o do KIT
        composicao = KitEstoqueService.obter_detalhes_composicao(
            db,
            produto_id,
            tenant_id=getattr(produto, "tenant_id", tenant_id),
        )
        response_data["composicao_kit"] = composicao
        response_data["preco_custo"] = float(
            KitCustoService.calcular_custo_kit(produto_id, db)
        )

        # Calcular estoque virtual (se for KIT VIRTUAL)
        if produto.tipo_kit == "VIRTUAL":
            estoque_virtual = KitEstoqueService.calcular_estoque_virtual_kit(
                db,
                produto_id,
                tenant_id=getattr(produto, "tenant_id", tenant_id),
            )
            response_data["estoque_virtual"] = estoque_virtual
            logger.info(f"ðŸ§© Kit #{produto_id}: estoque_virtual={estoque_virtual}")
        else:
            # KIT FÃSICO usa estoque prÃ³prio
            response_data["estoque_virtual"] = int(produto.estoque_atual or 0)

    # Mapear tipo_kit para e_kit_fisico (compatibilidade com frontend)
    response_data["e_kit_fisico"] = produto.tipo_kit == "FISICO"

    # Calcular estoque reservado (pedidos Bling em aberto)
    try:
        from app.estoque_reserva_service import EstoqueReservaService

        response_data["estoque_reservado"] = float(
            EstoqueReservaService.quantidade_reservada_produto(db, tenant_id, produto)
            or 0.0
        )
    except Exception:
        response_data["estoque_reservado"] = 0.0

    if produto.tipo_produto in ("KIT", "VARIACAO") and produto.tipo_kit == "VIRTUAL":
        response_data["estoque_disponivel"] = float(
            response_data.get("estoque_virtual") or 0
        )
    else:
        response_data["estoque_disponivel"] = max(
            float(produto.estoque_atual or 0)
            - float(response_data.get("estoque_reservado") or 0),
            0.0,
        )

    promocao_pdv = _resolver_promocao_erp_produto(produto)
    response_data["preco_venda_original"] = promocao_pdv["preco_regular"]
    response_data["preco_venda_pdv"] = promocao_pdv["preco_pdv"]
    response_data["preco_venda_efetivo"] = promocao_pdv["preco_pdv"]
    response_data["promocao_pdv_ativa"] = promocao_pdv["promocao_ativa"]
    response_data["promocao_origem_pdv"] = (
        "Promocao ERP" if promocao_pdv["promocao_ativa"] else None
    )
    response_data["desconto_promocional_pdv"] = promocao_pdv["desconto"]

    return response_data


@router.put("/{produto_id}", response_model=ProdutoResponse)
@require_permission("produtos.editar")
def atualizar_produto(
    produto_id: int,
    produto_update: ProdutoUpdate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Atualiza um produto

    Para produtos KIT:
    - Pode atualizar composicao_kit (diff inteligente)
    - Pode alterar tipo_kit (VIRTUAL <-> FISICO)
    """
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    produto = (
        db.query(Produto)
        .filter(Produto.id == produto_id, Produto.tenant_id == tenant_id)
        .first()
    )

    if not produto:
        raise HTTPException(status_code=404, detail="Produto nÃ£o encontrado")

    # Verificar se novo SKU jÃ¡ existe
    if produto_update.codigo is not None:
        produto_update.codigo = _normalizar_sku_produto(produto_update.codigo)
        if produto_update.codigo.lower() != str(produto.codigo or "").strip().lower():
            _validar_sku_unico(
                db, produto_update.codigo, tenant_id, produto_id=produto_id
            )

    # Verificar se novo cÃ³digo de barras jÃ¡ existe
    if (
        produto_update.codigo_barras
        and produto_update.codigo_barras != produto.codigo_barras
    ):
        existe_barcode = (
            db.query(Produto)
            .filter(
                Produto.codigo_barras == produto_update.codigo_barras,
                Produto.tenant_id == tenant_id,
                Produto.id != produto_id,
            )
            .first()
        )

        if existe_barcode:
            raise HTTPException(
                status_code=400,
                detail=f"CÃ³digo de barras '{produto_update.codigo_barras}' jÃ¡ cadastrado",
            )

    # Extrair dados
    dados_recebidos = produto_update.model_dump(exclude_unset=True)
    composicao_kit = dados_recebidos.pop("composicao_kit", None)

    dados_recebidos = _normalizar_payload_granel(
        _normalizar_payload_racao(dados_recebidos)
    )
    dados_recebidos = _normalizar_promocao_erp_payload(dados_recebidos, produto)

    # ========================================
    # ï¿½ðŸ”’ TRAVA 3 â€” VALIDAÃ‡ÃƒO: PRODUTO PAI NÃƒO TEM PREÃ‡O (ATUALIZAÃ‡ÃƒO)
    # ========================================
    is_parent_atual = produto.is_parent
    is_parent_novo = dados_recebidos.get("is_parent", is_parent_atual)

    if is_parent_novo:
        # Bloquear alteraÃ§Ã£o de preÃ§o em produto PAI
        if (
            "preco_venda" in dados_recebidos
            and dados_recebidos["preco_venda"]
            and dados_recebidos["preco_venda"] > 0
        ):
            raise HTTPException(
                status_code=400,
                detail="âŒ Produto pai nÃ£o pode ter preÃ§o de venda. O preÃ§o deve ser definido nas variaÃ§Ãµes individuais.",
            )

        # Bloquear alteraÃ§Ã£o de estoque em produto PAI
        if (
            "estoque_atual" in dados_recebidos
            and dados_recebidos["estoque_atual"]
            and dados_recebidos["estoque_atual"] > 0
        ):
            raise HTTPException(
                status_code=400,
                detail="âŒ Produto pai nÃ£o pode ter estoque. O estoque deve ser gerenciado nas variaÃ§Ãµes.",
            )

    # ========================================
    # ðŸ”’ VALIDAÃ‡ÃƒO: VARIAÃ‡ÃƒO DUPLICADA (ATUALIZAÃ‡ÃƒO)
    # ========================================
    # Se estÃ¡ atualizando signature de uma VARIAÃ‡ÃƒO, verificar duplicidade
    if (
        "variation_signature" in dados_recebidos
        and dados_recebidos["variation_signature"]
    ):
        variacao_existente = (
            db.query(Produto)
            .filter(
                Produto.tenant_id == tenant_id,
                Produto.produto_pai_id == produto.produto_pai_id,
                Produto.variation_signature == dados_recebidos["variation_signature"],
                Produto.id != produto_id,  # Excluir o prÃ³prio produto
                Produto.ativo.is_(True),
            )
            .first()
        )

        if variacao_existente:
            raise HTTPException(
                status_code=409,
                detail=f"âŒ JÃ¡ existe uma variaÃ§Ã£o com os mesmos atributos para este produto. VariaÃ§Ã£o existente: '{variacao_existente.nome}' (ID: {variacao_existente.id})",
            )

    tipo_produto_final = dados_recebidos.get("tipo_produto", produto.tipo_produto)
    tipo_kit_informado = "tipo_kit" in dados_recebidos
    remover_tipo_kit = tipo_kit_informado and not dados_recebidos.get("tipo_kit")

    # ========================================
    # PROCESSAR e_kit_fisico -> tipo_kit
    # ========================================
    if "e_kit_fisico" in dados_recebidos:
        e_kit_fisico = dados_recebidos.pop("e_kit_fisico")
        if (
            tipo_produto_final in ("KIT", "VARIACAO")
            and not remover_tipo_kit
            and (
                tipo_kit_informado
                or bool(dados_recebidos.get("tipo_kit", produto.tipo_kit))
            )
        ):
            dados_recebidos["tipo_kit"] = "FISICO" if e_kit_fisico else "VIRTUAL"

    tipo_kit_final = dados_recebidos.get("tipo_kit", produto.tipo_kit)
    produto_sera_composto = tipo_produto_final in ("KIT", "VARIACAO") and bool(
        tipo_kit_final
    )
    produto_sera_granel = bool(
        dados_recebidos.get("e_granel", produto.e_granel)
    ) or _nome_indica_granel(dados_recebidos.get("nome", produto.nome))

    if produto_sera_granel:
        dados_recebidos["e_granel"] = True
        dados_recebidos["tipo_produto"] = "SIMPLES"
        dados_recebidos["tipo_kit"] = None
        dados_recebidos["unidade"] = "KG"
        dados_recebidos["participa_sugestao_compra"] = False
        tipo_produto_final = "SIMPLES"
        tipo_kit_final = None
        produto_sera_composto = False

    # ========================================
    # ATUALIZAR COMPOSIÃ‡ÃƒO DO KIT (se enviado)
    # ========================================
    if composicao_kit is not None and produto_sera_composto:
        from app.services.kit_estoque_service import KitEstoqueService

        # âš ï¸ VALIDAÃ‡ÃƒO OBRIGATÃ“RIA: KIT deve ter pelo menos 1 componente
        if len(composicao_kit) == 0:
            raise HTTPException(
                status_code=400,
                detail="Produto do tipo KIT deve ter pelo menos 1 componente na composiÃ§Ã£o. Adicione os produtos que fazem parte do kit antes de salvar.",
            )

        # Validar novos componentes
        valido, erro = KitEstoqueService.validar_componentes_kit(
            db=db, kit_id=produto_id, componentes=composicao_kit
        )

        if not valido:
            raise HTTPException(
                status_code=400, detail=f"ComposiÃ§Ã£o invÃ¡lida: {erro}"
            )

        # Remover componentes antigos
        db.query(ProdutoKitComponente).filter(
            ProdutoKitComponente.kit_id == produto_id
        ).delete()

        # Adicionar novos componentes
        for comp in composicao_kit:
            novo_comp = ProdutoKitComponente(
                kit_id=produto_id,
                produto_componente_id=comp.get("produto_componente_id"),
                quantidade=comp.get("quantidade", 1.0),
                ordem=comp.get("ordem", 0),
                opcional=comp.get("opcional", False),
                tenant_id=produto.tenant_id,
            )
            db.add(novo_comp)

        logger.info(
            f"ðŸ§© ComposiÃ§Ã£o do Kit #{produto_id} atualizada: {len(composicao_kit)} componentes"
        )
    elif composicao_kit is not None and not produto_sera_composto:
        db.query(ProdutoKitComponente).filter(
            ProdutoKitComponente.kit_id == produto_id
        ).delete()
        logger.info(
            f"🧹 Composição removida do produto #{produto_id} ao desmarcar o kit"
        )

    # ========================================
    # ATUALIZAR CAMPOS DO PRODUTO
    # ========================================
    custo_componente_alterado = "preco_custo" in dados_recebidos

    for key, value in dados_recebidos.items():
        setattr(produto, key, value)

    if not bool(produto.ativo) or produto.situacao is False:
        produto.anunciar_ecommerce = False
        produto.anunciar_app = False

    produto.updated_at = datetime.utcnow()

    try:
        from app.services.kit_custo_service import KitCustoService

        db.flush()

        if KitCustoService.produto_usa_custo_por_componentes(produto):
            KitCustoService.sincronizar_custo_kit(db, produto.id)

        if custo_componente_alterado:
            KitCustoService.recalcular_kits_que_usam_produto(db, produto.id)

        if (
            produto.tipo_produto in ("KIT", "VARIACAO")
            and produto.tipo_kit == "VIRTUAL"
        ):
            from app.services.kit_estoque_service import KitEstoqueService

            produto.estoque_atual = float(
                KitEstoqueService.calcular_estoque_virtual_kit(
                    db,
                    produto.id,
                    tenant_id=getattr(produto, "tenant_id", tenant_id),
                )
            )
            db.add(produto)

        db.commit()
        db.refresh(produto)
        logger.info(f"âœ… Produto #{produto_id} atualizado com sucesso")

        # Notificar clientes "Avise-me" se estoque voltou ao positivo
        if (
            "estoque_atual" in dados_recebidos
            and produto.estoque_atual
            and produto.estoque_atual > 0
        ):
            try:
                from app.routes.ecommerce_notify_routes import (
                    notificar_clientes_estoque_disponivel,
                )

                notificar_clientes_estoque_disponivel(
                    db, str(tenant_id), produto_id, produto.nome
                )
            except Exception as _notify_err:
                logger.warning(
                    f"Aviso: erro ao enviar notificacoes avise-me: {_notify_err}"
                )

        # Retornar com composiÃ§Ã£o e estoque virtual
        return obter_produto(produto_id, db, user_and_tenant)

    except Exception as e:
        db.rollback()
        logger.error(f"âŒ Erro ao atualizar produto: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao atualizar produto: {str(e)}"
        )


# ============================================================================
# ATUALIZAÃ‡ÃƒO EM LOTE
# ============================================================================
