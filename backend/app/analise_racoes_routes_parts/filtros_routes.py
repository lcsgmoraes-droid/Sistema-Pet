# -*- coding: utf-8 -*-
"""Rota de opcoes de filtros da analise de racoes."""

import traceback

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.analise_racoes_filters import (
    _produto_eh_racao_expr,
    _validar_tenant_e_obter_usuario,
)
from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.opcoes_racao_models import FasePublico, LinhaRacao, PorteAnimal, TipoTratamento
from app.produtos_models import Categoria, Marca, Produto

router = APIRouter()


@router.get("/opcoes-filtros")
async def obter_opcoes_filtros(
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    """
    Retorna todas as opções disponíveis para filtros

    Útil para popular dropdowns e checkboxes dinamicamente
    """
    try:
        current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

        # Buscar valores únicos de cada campo JSONB
        from sqlalchemy import distinct
        import logging

        logger = logging.getLogger(__name__)
        logger.info("[opcoes-filtros] Iniciando busca de opcoes")

        # Marcas
        try:
            marcas = (
                db.query(Marca.id, Marca.nome)
                .join(Produto, Produto.marca_id == Marca.id)
                .filter(Produto.tenant_id == tenant_id, _produto_eh_racao_expr())
                .distinct()
                .all()
            )
            logger.info(f"[opcoes-filtros] Marcas encontradas: {len(marcas)}")
        except Exception as e:
            logger.error(f"[opcoes-filtros] Erro ao buscar marcas: {str(e)}")
            marcas = []

        # Categorias
        try:
            categorias = (
                db.query(Categoria.id, Categoria.nome)
                .join(Produto, Produto.categoria_id == Categoria.id)
                .filter(Produto.tenant_id == tenant_id, _produto_eh_racao_expr())
                .distinct()
                .all()
            )
            logger.info(f"[opcoes-filtros] Categorias encontradas: {len(categorias)}")
        except Exception as e:
            logger.error(f"[opcoes-filtros] Erro ao buscar categorias: {str(e)}")
            categorias = []

        # Sabores
        try:
            sabores = (
                db.query(distinct(Produto.sabor_proteina))
                .filter(
                    Produto.tenant_id == tenant_id,
                    _produto_eh_racao_expr(),
                    Produto.sabor_proteina.isnot(None),
                )
                .all()
            )
            logger.info(f"[opcoes-filtros] Sabores encontrados: {len(sabores)}")
        except Exception as e:
            logger.error(f"[opcoes-filtros] Erro ao buscar sabores: {str(e)}")
            sabores = []

        # Especies (usando especies_indicadas que é String: dog, cat, both)
        try:
            especies_result = (
                db.query(distinct(Produto.especies_indicadas))
                .filter(
                    Produto.tenant_id == tenant_id,
                    _produto_eh_racao_expr(),
                    Produto.especies_indicadas.isnot(None),
                )
                .all()
            )
            especies = [row[0] for row in especies_result if row[0]]
            logger.info(f"[opcoes-filtros] Espécies encontradas: {len(especies)}")
        except Exception as e:
            logger.error(f"[opcoes-filtros] Erro ao buscar espécies: {str(e)}")
            especies = []

        # Linhas de ração (buscar da tabela linhas_racao) - CAMPO NOVO
        linhas = []
        try:
            # Verificar se a coluna linha_racao_id existe no modelo
            if hasattr(Produto, "linha_racao_id"):
                linhas = (
                    db.query(LinhaRacao.id, LinhaRacao.nome)
                    .join(Produto, Produto.linha_racao_id == LinhaRacao.id)
                    .filter(
                        Produto.tenant_id == tenant_id,
                        _produto_eh_racao_expr(),
                        LinhaRacao.ativo.is_(True),
                    )
                    .distinct()
                    .all()
                )
                logger.info(f"[opcoes-filtros] Linhas encontradas: {len(linhas)}")
            else:
                logger.warning(
                    "[opcoes-filtros] Coluna 'linha_racao_id' não existe no modelo Produto"
                )
        except Exception as e:
            logger.error(
                f"[opcoes-filtros] Erro ao buscar linhas: {str(e)}\n{traceback.format_exc()}"
            )

        # Portes (buscar da tabela portes_animal via FK) - CAMPO NOVO
        portes = []
        try:
            # Verificar se a coluna porte_animal_id existe
            if hasattr(Produto, "porte_animal_id"):
                portes = (
                    db.query(PorteAnimal.id, PorteAnimal.nome)
                    .join(Produto, Produto.porte_animal_id == PorteAnimal.id)
                    .filter(
                        Produto.tenant_id == tenant_id,
                        _produto_eh_racao_expr(),
                        PorteAnimal.ativo.is_(True),
                    )
                    .distinct()
                    .all()
                )
                logger.info(f"[opcoes-filtros] Portes encontrados: {len(portes)}")
            else:
                logger.warning(
                    "[opcoes-filtros] Coluna 'porte_animal_id' não existe no modelo Produto"
                )
        except Exception as e:
            logger.error(
                f"[opcoes-filtros] Erro ao buscar portes: {str(e)}\n{traceback.format_exc()}"
            )

        # Fases (buscar da tabela fases_publico via FK) - CAMPO NOVO
        fases = []
        try:
            # Verificar se a coluna fase_publico_id existe
            if hasattr(Produto, "fase_publico_id"):
                fases = (
                    db.query(FasePublico.id, FasePublico.nome)
                    .join(Produto, Produto.fase_publico_id == FasePublico.id)
                    .filter(
                        Produto.tenant_id == tenant_id,
                        _produto_eh_racao_expr(),
                        FasePublico.ativo.is_(True),
                    )
                    .distinct()
                    .all()
                )
                logger.info(f"[opcoes-filtros] Fases encontradas: {len(fases)}")
            else:
                logger.warning(
                    "[opcoes-filtros] Coluna 'fase_publico_id' não existe no modelo Produto"
                )
        except Exception as e:
            logger.error(
                f"[opcoes-filtros] Erro ao buscar fases: {str(e)}\n{traceback.format_exc()}"
            )

        # Tratamentos (buscar da tabela tipos_tratamento via FK) - CAMPO NOVO
        tratamentos = []
        try:
            # Verificar se a coluna tipo_tratamento_id existe
            if hasattr(Produto, "tipo_tratamento_id"):
                tratamentos = (
                    db.query(TipoTratamento.id, TipoTratamento.nome)
                    .join(Produto, Produto.tipo_tratamento_id == TipoTratamento.id)
                    .filter(
                        Produto.tenant_id == tenant_id,
                        _produto_eh_racao_expr(),
                        TipoTratamento.ativo.is_(True),
                    )
                    .distinct()
                    .all()
                )
                logger.info(
                    f"[opcoes-filtros] Tratamentos encontrados: {len(tratamentos)}"
                )
            else:
                logger.warning(
                    "[opcoes-filtros] Coluna 'tipo_tratamento_id' não existe no modelo Produto"
                )
        except Exception as e:
            logger.error(
                f"[opcoes-filtros] Erro ao buscar tratamentos: {str(e)}\n{traceback.format_exc()}"
            )

        # Pesos (valores únicos de peso_embalagem)
        pesos = []
        try:
            pesos_result = (
                db.query(distinct(Produto.peso_embalagem))
                .filter(
                    Produto.tenant_id == tenant_id,
                    _produto_eh_racao_expr(),
                    Produto.peso_embalagem.isnot(None),
                )
                .order_by(Produto.peso_embalagem)
                .all()
            )
            pesos = [float(row[0]) for row in pesos_result if row[0]]
            logger.info(f"[opcoes-filtros] Pesos encontrados: {len(pesos)}")
        except Exception as e:
            logger.error(f"[opcoes-filtros] Erro ao buscar pesos: {str(e)}")

        logger.info("[opcoes-filtros] Busca concluída com sucesso")

        return {
            "marcas": [{"id": m.id, "nome": m.nome} for m in marcas],
            "categorias": [{"id": c.id, "nome": c.nome} for c in categorias],
            "especies": sorted(list(set(especies))),
            "linhas": [{"id": linha.id, "nome": linha.nome} for linha in linhas],
            "portes": [{"id": p.id, "nome": p.nome} for p in portes],
            "fases": [{"id": f.id, "nome": f.nome} for f in fases],
            "tratamentos": [{"id": t.id, "nome": t.nome} for t in tratamentos],
            "sabores": sorted([s[0] for s in sabores if s[0]]),
            "pesos": pesos,  # Em kg
        }

    except Exception as error:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"[opcoes-filtros] ERRO CRÍTICO: {str(error)}")
        logger.error(f"[opcoes-filtros] Stack trace:\n{traceback.format_exc()}")

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Erro ao buscar opções de filtros",
                "error": str(error),
                "stack": traceback.format_exc(),
                "endpoint": "/api/racoes/analises/opcoes-filtros",
            },
        )
