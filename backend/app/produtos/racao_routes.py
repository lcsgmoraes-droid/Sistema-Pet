"""Rotas de classificacao e alertas de racoes."""

from __future__ import annotations

import logging
import traceback
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.produtos.racao import _produto_eh_racao_expr
from app.produtos.validators import _validar_tenant_e_obter_usuario
from app.produtos_models import Produto

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== CLASSIFICAï¿½ï¿½O INTELIGENTE DE RAï¿½ï¿½ES ====================


@router.post("/{produto_id}/classificar-ia")
async def classificar_produto_ia(
    produto_id: int,
    forcar: bool = False,  # Forï¿½a reclassificaï¿½ï¿½o mesmo se auto_classificar_nome = False
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Aplica classificaï¿½ï¿½o inteligente via IA em um produto
    Extrai automaticamente: porte, fase, tratamento, sabor e peso do nome
    """
    from app.classificador_racao import classificar_produto

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # Buscar produto
    produto = (
        db.query(Produto)
        .filter(Produto.id == produto_id, Produto.tenant_id == tenant_id)
        .first()
    )

    if not produto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Produto nï¿½o encontrado"
        )

    # Verificar se deve classificar
    if not forcar and not produto.auto_classificar_nome:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Auto-classificaï¿½ï¿½o desativada para este produto. Use forcar=true para forï¿½ar.",
        )

    # Executar classificaï¿½ï¿½o
    resultado, confianca, metadata = classificar_produto(
        produto.nome, produto.peso_embalagem
    )

    # Importar models de lookup
    from app.opcoes_racao_models import (
        PorteAnimal,
        FasePublico,
        TipoTratamento,
        SaborProteina,
        LinhaRacao,
    )

    # Atualizar produto apenas com campos que foram identificados
    campos_atualizados = []

    # Salvar metadados da classificaï¿½ï¿½o
    produto.classificacao_ia_versao = metadata["versao"]

    if resultado["especie_indicada"]:
        # Mapear para formato do banco (dog, cat, both, bird, etc)
        mapa_especies = {
            "CÃ£es": "dog",
            "Gatos": "cat",
            "PÃ¡ssaros": "bird",
            "Roedores": "rodent",
            "Peixes": "fish",
        }
        especie_db = mapa_especies.get(
            resultado["especie_indicada"], resultado["especie_indicada"].lower()
        )
        produto.especies_indicadas = especie_db
        campos_atualizados.append("especies_indicadas")

    # Buscar ID do porte baseado no nome retornado pela IA
    # Classificador retorna array, pegar primeiro elemento
    if resultado["porte_animal"] and len(resultado["porte_animal"]) > 0:
        nome_porte = resultado["porte_animal"][0]  # Pega primeiro porte do array
        porte = (
            db.query(PorteAnimal)
            .filter(
                PorteAnimal.tenant_id == tenant_id,
                PorteAnimal.nome == nome_porte,
                PorteAnimal.ativo.is_(True),
            )
            .first()
        )
        if porte:
            produto.porte_animal_id = porte.id
            campos_atualizados.append("porte_animal_id")

    # Buscar ID da fase baseado no nome retornado pela IA
    # Classificador retorna array, pegar primeiro elemento
    if resultado["fase_publico"] and len(resultado["fase_publico"]) > 0:
        nome_fase = resultado["fase_publico"][0]  # Pega primeira fase do array
        fase = (
            db.query(FasePublico)
            .filter(
                FasePublico.tenant_id == tenant_id,
                FasePublico.nome == nome_fase,
                FasePublico.ativo.is_(True),
            )
            .first()
        )
        if fase:
            produto.fase_publico_id = fase.id
            campos_atualizados.append("fase_publico_id")

    # Buscar ID do tipo de tratamento baseado no nome retornado pela IA
    # Classificador retorna array, pegar primeiro elemento
    if resultado["tipo_tratamento"] and len(resultado["tipo_tratamento"]) > 0:
        nome_tratamento = resultado["tipo_tratamento"][
            0
        ]  # Pega primeiro tratamento do array
        tratamento = (
            db.query(TipoTratamento)
            .filter(
                TipoTratamento.tenant_id == tenant_id,
                TipoTratamento.nome == nome_tratamento,
                TipoTratamento.ativo.is_(True),
            )
            .first()
        )
        if tratamento:
            produto.tipo_tratamento_id = tratamento.id
            campos_atualizados.append("tipo_tratamento_id")

    # Buscar ID do sabor/proteÃ­na baseado no nome retornado pela IA
    if resultado["sabor_proteina"]:
        sabor = (
            db.query(SaborProteina)
            .filter(
                SaborProteina.tenant_id == tenant_id,
                SaborProteina.nome == resultado["sabor_proteina"],
                SaborProteina.ativo.is_(True),
            )
            .first()
        )
        if sabor:
            produto.sabor_proteina_id = sabor.id
            campos_atualizados.append("sabor_proteina_id")

    # Buscar ID da linha de raÃ§Ã£o baseado no nome retornado pela IA
    if resultado.get("linha_racao"):
        linha = (
            db.query(LinhaRacao)
            .filter(
                LinhaRacao.tenant_id == tenant_id,
                LinhaRacao.nome == resultado["linha_racao"],
                LinhaRacao.ativo.is_(True),
            )
            .first()
        )
        if linha:
            produto.linha_racao_id = linha.id
            campos_atualizados.append("linha_racao_id")

    # Atualizar peso se retornado pela IA e ainda nÃ£o definido
    if resultado["peso_embalagem"] and not produto.peso_embalagem:
        produto.peso_embalagem = resultado["peso_embalagem"]
        campos_atualizados.append("peso_embalagem")

    # Salvar
    if campos_atualizados:
        db.commit()
        db.refresh(produto)

    return {
        "success": True,
        "produto_id": produto.id,
        "nome": produto.nome,
        "classificacao": resultado,
        "confianca": confianca,
        "campos_atualizados": campos_atualizados,
        "mensagem": f"Classificaï¿½ï¿½o aplicada com sucesso. Score: {confianca['score']}%",
    }


@router.post("/classificar-lote")
async def classificar_lote_produtos(
    produto_ids: List[
        int
    ] = None,  # Se None, classifica todos ativos com auto_classificar_nome=True
    apenas_sem_classificacao: bool = True,  # Sï¿½ classifica produtos sem classificaï¿½ï¿½o existente
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Classifica mï¿½ltiplos produtos em lote
    ï¿½til para classificar produtos histï¿½ricos
    """
    from app.classificador_racao import classificar_produto

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # Montar query
    query = db.query(Produto).filter(
        Produto.tenant_id == tenant_id,
        Produto.ativo.is_(True),
        Produto.auto_classificar_nome.is_(True),
    )

    # Filtrar por IDs especÃ­ficos se fornecido
    if produto_ids:
        query = query.filter(Produto.id.in_(produto_ids))

    # Filtrar apenas produtos sem classificaÃ§Ã£o completa
    if apenas_sem_classificacao:
        query = query.filter(
            (Produto.porte_animal.is_(None))
            | (Produto.fase_publico.is_(None))
            | (Produto.sabor_proteina.is_(None))
        )

    produtos = query.limit(100).all()  # Limite de seguranÃ§a

    sucesso = []
    erros = []

    for produto in produtos:
        try:
            resultado, confianca = classificar_produto(
                produto.nome, produto.peso_embalagem
            )

            campos_atualizados = []

            if resultado["especie_indicada"] and not produto.especies_indicadas:
                # Mapear para formato do banco
                mapa_especies = {
                    "CÃ£es": "dog",
                    "Gatos": "cat",
                    "PÃ¡ssaros": "bird",
                    "Roedores": "rodent",
                    "Peixes": "fish",
                }
                especie_db = mapa_especies.get(
                    resultado["especie_indicada"], resultado["especie_indicada"].lower()
                )
                produto.especies_indicadas = especie_db
                campos_atualizados.append("especies_indicadas")

            if resultado["porte_animal"] and not produto.porte_animal:
                produto.porte_animal = resultado["porte_animal"]
                campos_atualizados.append("porte_animal")

            if resultado["fase_publico"] and not produto.fase_publico:
                produto.fase_publico = resultado["fase_publico"]
                campos_atualizados.append("fase_publico")

            if resultado["tipo_tratamento"] and not produto.tipo_tratamento:
                produto.tipo_tratamento = resultado["tipo_tratamento"]
                campos_atualizados.append("tipo_tratamento")

            if resultado["sabor_proteina"] and not produto.sabor_proteina:
                produto.sabor_proteina = resultado["sabor_proteina"]
                campos_atualizados.append("sabor_proteina")

            if resultado["peso_embalagem"] and not produto.peso_embalagem:
                produto.peso_embalagem = resultado["peso_embalagem"]
                campos_atualizados.append("peso_embalagem")

            if campos_atualizados:
                db.commit()
                db.refresh(produto)

            sucesso.append(
                {
                    "produto_id": produto.id,
                    "nome": produto.nome,
                    "campos_atualizados": campos_atualizados,
                    "score": confianca["score"],
                }
            )

        except Exception as e:
            erros.append(
                {"produto_id": produto.id, "nome": produto.nome, "erro": str(e)}
            )

    return {
        "success": True,
        "total_processados": len(produtos),
        "sucessos": len(sucesso),
        "erros": len(erros),
        "detalhes_sucesso": sucesso,
        "detalhes_erros": erros,
    }


@router.get("/racao/alertas")
async def listar_racoes_sem_classificacao(
    limite: int = 50,
    offset: int = 0,
    especie: Optional[str] = None,  # Filtro por espÃ©cie: dog, cat, bird, rodent, fish
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Lista raï¿½ï¿½es sem classificaï¿½ï¿½o completa para alertas
    Filtra produtos classificados como raï¿½ï¿½o mas sem informaï¿½ï¿½es importantes

    ParÃ¢metros:
    - especie: Filtro opcional por espÃ©cie (dog, cat, bird, rodent, fish)
    """
    try:
        current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

        logger.info("[racao/alertas] Iniciando busca")

        # Buscar raÃ§Ãµes sem classificaÃ§Ã£o completa
        # Considera "raÃ§Ã£o" se:
        # 1. classificacao_racao != null AND != 'NÃ£o Ã© raÃ§Ã£o'
        # 2. OU categoria.nome LIKE '%raÃ§Ã£o%'

        # Usar joinedload para evitar N+1 queries
        query = (
            db.query(Produto)
            .options(joinedload(Produto.categoria), joinedload(Produto.marca))
            .filter(Produto.tenant_id == tenant_id, Produto.ativo.is_(True))
        )

        # Filtro: Ã© raÃ§Ã£o E estÃ¡ incompleta
        query = query.filter(_produto_eh_racao_expr())

        # Montar filtros dinamicamente baseado em campos que existem
        filtros_incompletos = []
        filtros_incompletos.append(Produto.especies_indicadas.is_(None))

        # Adicionar filtros apenas para campos que existem no modelo
        if hasattr(Produto, "porte_animal_id"):
            filtros_incompletos.append(Produto.porte_animal_id.is_(None))
            logger.info("[racao/alertas] Campo 'porte_animal_id' encontrado no modelo")
        else:
            logger.warning(
                "[racao/alertas] Campo 'porte_animal_id' NÃƒO existe no modelo"
            )

        if hasattr(Produto, "fase_publico_id"):
            filtros_incompletos.append(Produto.fase_publico_id.is_(None))
            logger.info("[racao/alertas] Campo 'fase_publico_id' encontrado no modelo")
        else:
            logger.warning(
                "[racao/alertas] Campo 'fase_publico_id' NÃƒO existe no modelo"
            )

        filtros_incompletos.append(Produto.sabor_proteina.is_(None))
        filtros_incompletos.append(Produto.peso_embalagem.is_(None))

        # Aplicar filtro OR (pelo menos um campo faltando)
        query = query.filter(or_(*filtros_incompletos))

        # Filtrar por espÃ©cie se especificado
        if especie:
            query = query.filter(Produto.especies_indicadas == especie)

        total = query.count()
        logger.info(f"[racao/alertas] Total de produtos encontrados: {total}")

        produtos = query.limit(limite).offset(offset).all()
        logger.info(
            f"[racao/alertas] Produtos retornados nesta pÃ¡gina: {len(produtos)}"
        )

        resultado = []
        for produto in produtos:
            try:
                campos_faltantes = []

                if not produto.especies_indicadas:
                    campos_faltantes.append("especies_indicadas")

                # Verificar campos FK apenas se existirem no modelo
                if hasattr(produto, "porte_animal_id"):
                    if not produto.porte_animal_id:
                        campos_faltantes.append("porte_animal")

                if hasattr(produto, "fase_publico_id"):
                    if not produto.fase_publico_id:
                        campos_faltantes.append("fase_publico")

                if not produto.sabor_proteina:
                    campos_faltantes.append("sabor_proteina")

                if not produto.peso_embalagem:
                    campos_faltantes.append("peso_embalagem")

                # Acesso seguro a relationships
                categoria_nome = None
                if produto.categoria:
                    categoria_nome = produto.categoria.nome

                marca_nome = None
                if produto.marca:
                    marca_nome = produto.marca.nome

                # Acesso seguro ao campo auto_classificar_nome
                auto_classificar = False
                if hasattr(produto, "auto_classificar_nome"):
                    auto_classificar = produto.auto_classificar_nome or False

                resultado.append(
                    {
                        "id": produto.id,
                        "codigo": produto.codigo,
                        "nome": produto.nome,
                        "classificacao_racao": produto.classificacao_racao,
                        "especies_indicadas": produto.especies_indicadas,
                        "categoria": categoria_nome,
                        "marca": marca_nome,
                        "campos_faltantes": campos_faltantes,
                        "completude": round((5 - len(campos_faltantes)) / 5 * 100, 1),
                        "auto_classificar_ativo": auto_classificar,
                    }
                )
            except Exception as e:
                logger.error(
                    f"[racao/alertas] Erro ao processar produto {produto.id}: {str(e)}"
                )
                logger.error(f"[racao/alertas] Stack trace: {traceback.format_exc()}")
                continue

        logger.info(
            f"[racao/alertas] Busca concluÃ­da com sucesso. Total de itens no resultado: {len(resultado)}"
        )

        return {
            "total": total,
            "limite": limite,
            "offset": offset,
            "especie_filtro": especie,
            "items": resultado,
        }

    except Exception as error:
        logger.error(f"[racao/alertas] ERRO CRÃTICO: {str(error)}")
        logger.error(f"[racao/alertas] Stack trace:\n{traceback.format_exc()}")

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Erro ao listar raÃ§Ãµes sem classificaÃ§Ã£o",
                "error": str(error),
                "stack": traceback.format_exc(),
                "endpoint": "/api/produtos/racao/alertas",
            },
        )
