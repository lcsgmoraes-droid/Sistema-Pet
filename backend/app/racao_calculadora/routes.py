"""Rotas publicas da calculadora de racao."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.auth import get_current_user_and_tenant
from app.db import get_session
from app.partner_utils import get_all_accessible_tenant_ids
from app.produtos_models import Categoria, Marca, Produto
from app.security.permissions_decorator import require_permission

from .core import (
    _avaliar_aptidao_calculadora,
    _campos_bloqueantes_calculadora,
    calcular_quantidade_diaria,
    calcular_resultado,
)
from .options import (
    _busca_racao_conditions,
    _produto_eh_racao_expr,
    _serializar_opcao_racao,
)
from .schemas import (
    CalculadoraRacaoRequest,
    ComparativoRacoesResponse,
    RacoesCalculadoraOptionsResponse,
    ResultadoCalculoRacao,
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/produtos", tags=["calculadora-racao"])


# ==================== ENDPOINTS ====================


@router.get(
    "/calculadora-racao/opcoes", response_model=RacoesCalculadoraOptionsResponse
)
@require_permission("produtos.visualizar")
async def listar_opcoes_calculadora_racao(
    busca: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(120, ge=1, le=1500),
    apenas_aptas: bool = Query(False),
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    """
    Lista leve de racoes para a calculadora.

    Evita usar /produtos/, que carrega hierarquia, imagens, lotes e outros dados
    desnecessarios para a busca da calculadora.
    """
    _current_user, tenant_id = user_and_tenant
    access_ids = get_all_accessible_tenant_ids(db, tenant_id)
    termo_busca = (busca or "").strip()

    query = (
        db.query(
            Produto,
            Categoria.nome.label("categoria_nome"),
            Marca.nome.label("marca_nome"),
        )
        .outerjoin(Categoria, Produto.categoria_id == Categoria.id)
        .outerjoin(Marca, Produto.marca_id == Marca.id)
        .filter(
            Produto.tenant_id.in_(access_ids),
            or_(
                Produto.tipo_produto.is_(None),
                Produto.tipo_produto.in_(["SIMPLES", "VARIACAO", "KIT"]),
            ),
            or_(Produto.ativo.is_(True), Produto.ativo.is_(None)),
            Produto.deleted_at.is_(None),
            _produto_eh_racao_expr(),
        )
    )

    if termo_busca:
        palavras = [p.strip() for p in termo_busca.split() if p.strip()]
        for palavra in palavras:
            query = query.filter(_busca_racao_conditions(palavra, db))

    total = query.count()
    offset = (page - 1) * page_size
    linhas = (
        query.order_by(Produto.nome.asc(), Produto.id.asc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    items = [
        _serializar_opcao_racao(produto, categoria_nome, marca_nome)
        for produto, categoria_nome, marca_nome in linhas
    ]
    if apenas_aptas:
        items = [item for item in items if item.apta]
    aptas = sum(1 for item in items if item.apta)

    return RacoesCalculadoraOptionsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        aptas=aptas,
        incompletas=len(items) - aptas,
    )


@router.post("/calculadora-racao", response_model=ResultadoCalculoRacao)
@require_permission("produtos.visualizar")
async def calcular_racao(
    req: CalculadoraRacaoRequest,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    """
    Calcula duração e custo de uma ração

    Exemplos:
    - Passar produto_id: busca dados do produto
    - Passar peso_embalagem_kg + preco: calcula manualmente
    - Passar quantidade_diaria_g: usa valor fornecido
    - Se não passar quantidade_diaria_g: calcula automaticamente
    """
    current_user, tenant_id = user_and_tenant

    try:
        # 1. Buscar dados do produto (se fornecido)
        produto = None
        peso_embalagem_kg = req.peso_embalagem_kg
        preco = req.preco
        produto_nome = None
        classificacao = None
        categoria_racao = None

        if req.produto_id:
            access_ids = get_all_accessible_tenant_ids(db, tenant_id)
            produto = (
                db.query(Produto)
                .filter(Produto.id == req.produto_id, Produto.tenant_id.in_(access_ids))
                .first()
            )

            if not produto:
                raise HTTPException(status_code=404, detail="Produto não encontrado")

            campos_faltantes = _campos_bloqueantes_calculadora(
                produto,
                peso_fallback=req.peso_embalagem_kg,
                preco_fallback=req.preco,
                exigir_tabela_consumo=req.quantidade_diaria_g is None,
            )
            if campos_faltantes:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Ração com cadastro incompleto para a calculadora. "
                        f"Falta preencher: {', '.join(campos_faltantes)}"
                    ),
                )

            campos_recomendados = _avaliar_aptidao_calculadora(produto)
            if campos_recomendados:
                logger.info(
                    "Racao %s sem cadastro detalhado completo; calculadora seguira com fallback quando necessario: %s",
                    req.produto_id,
                    ", ".join(campos_recomendados),
                )

            peso_embalagem_kg = produto.peso_embalagem or req.peso_embalagem_kg
            preco = produto.preco_venda or req.preco
            produto_nome = produto.nome
            classificacao = produto.classificacao_racao
            categoria_racao = produto.categoria_racao

            logger.info(
                f"🔍 Produto {req.produto_id}: categoria={categoria_racao}, tabela_consumo length={len(produto.tabela_consumo or '')}"
            )

            if not peso_embalagem_kg:
                raise HTTPException(
                    status_code=400, detail="Produto não tem peso_embalagem cadastrado"
                )

        # 2. Validações
        if not peso_embalagem_kg or not preco:
            raise HTTPException(
                status_code=400, detail="peso_embalagem_kg e preco são obrigatórios"
            )

        # 3. Calcular quantidade diária
        quantidade_diaria_g = req.quantidade_diaria_g
        if not quantidade_diaria_g:
            # Passar tabela_consumo do produto se disponível
            tabela_consumo = produto.tabela_consumo if produto else None
            logger.info("Calculando sugestao de racao")
            if tabela_consumo:
                logger.info("Tabela de consumo do produto disponivel")
            quantidade_diaria_g = calcular_quantidade_diaria(
                peso_pet_kg=req.peso_pet_kg,
                idade_meses=req.idade_meses,
                nivel_atividade=req.nivel_atividade,
                tabela_consumo_json=tabela_consumo,
            )
            logger.info(f"✅ Quantidade calculada: {quantidade_diaria_g}g/dia")

        # 4. Calcular resultado
        resultado = calcular_resultado(
            peso_embalagem_kg=peso_embalagem_kg,
            preco=preco,
            quantidade_diaria_g=quantidade_diaria_g,
            produto_id=req.produto_id,
            produto_nome=produto_nome,
            classificacao=classificacao,
            categoria_racao=categoria_racao,
            peso_pet_kg=req.peso_pet_kg,
            nivel_atividade=req.nivel_atividade,
        )

        return resultado

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao calcular ração: {e}")
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


@router.post("/comparar-racoes", response_model=ComparativoRacoesResponse)
@require_permission("produtos.visualizar")
async def comparar_racoes(
    peso_pet_kg: float = Query(..., description="Peso do pet em kg"),
    idade_meses: Optional[int] = Query(None, description="Idade do pet em meses"),
    nivel_atividade: str = Query("normal", description="baixo, normal, alto"),
    classificacao: Optional[str] = Query(None, description="Filtrar por classificação"),
    especies: Optional[str] = Query(None, description="dog, cat, both"),
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    """
    Compara todas as rações cadastradas e retorna ordenadas por custo-benefício
    """
    current_user, tenant_id = user_and_tenant

    try:
        # Buscar produtos que são rações
        access_ids = get_all_accessible_tenant_ids(db, tenant_id)
        query = db.query(Produto).filter(
            Produto.tenant_id.in_(access_ids),
            _produto_eh_racao_expr(),
            Produto.peso_embalagem.isnot(None),
            Produto.peso_embalagem > 0,
            Produto.preco_venda.isnot(None),
            Produto.preco_venda > 0,
            Produto.tabela_consumo.isnot(None),
            func.length(func.trim(Produto.tabela_consumo)) > 0,
        )

        # Filtros opcionais
        if classificacao:
            query = query.filter(Produto.classificacao_racao == classificacao)
        if especies:
            query = query.filter(Produto.especies_indicadas.in_([especies, "both"]))

        produtos = query.all()

        produtos_aptos = [
            produto for produto in produtos if not _avaliar_aptidao_calculadora(produto)
        ]

        if not produtos_aptos:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Nenhuma ração apta para análise com os filtros. "
                    "Complete a aba Ração e a tabela de consumo dos produtos."
                ),
            )

        # Calcular para cada produto usando SUA PRÓPRIA tabela de consumo
        resultados = []

        for produto in produtos_aptos:
            # IMPORTANTE: Calcular quantidade diária ESPECÍFICA deste produto
            quantidade_diaria_g = calcular_quantidade_diaria(
                peso_pet_kg=peso_pet_kg,
                idade_meses=idade_meses,
                nivel_atividade=nivel_atividade,
                tabela_consumo_json=produto.tabela_consumo,  # ← USAR TABELA DO PRODUTO!
            )

            resultado = calcular_resultado(
                peso_embalagem_kg=produto.peso_embalagem,
                preco=produto.preco_venda,
                quantidade_diaria_g=quantidade_diaria_g,
                produto_id=produto.id,
                produto_nome=produto.nome,
                classificacao=produto.classificacao_racao,
                peso_pet_kg=peso_pet_kg,
                nivel_atividade=nivel_atividade,
            )
            resultados.append(resultado)

        # Ordenar por custo-benefício (menor custo diário)
        resultados.sort(key=lambda x: x.custo_por_dia)

        # Identificar melhores
        melhor_custo_beneficio = resultados[0].produto_id if resultados else None
        maior_duracao = (
            max(resultados, key=lambda x: x.duracao_dias).produto_id
            if resultados
            else None
        )
        menor_custo_diario = (
            min(resultados, key=lambda x: x.custo_por_dia).produto_id
            if resultados
            else None
        )

        return ComparativoRacoesResponse(
            racoes=resultados,
            melhor_custo_beneficio=melhor_custo_beneficio,
            maior_duracao=maior_duracao,
            menor_custo_diario=menor_custo_diario,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao comparar rações: {e}")
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")
