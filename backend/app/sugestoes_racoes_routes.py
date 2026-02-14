# -*- coding: utf-8 -*-
"""
Rotas de Sugestões Inteligentes para Rações
Detecção de duplicatas, padronização e gaps de estoque

Versão: 1.0.0 (2026-02-14)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from difflib import SequenceMatcher
from datetime import datetime
import re

from .db import get_session
from .auth.dependencies import get_current_user_and_tenant
from .produtos_models import Produto, Marca, Categoria
from .opcoes_racao_models import PorteAnimal, FasePublico, SaborProteina, TipoTratamento
from .vendas_models import VendaItem, Venda
from .duplicatas_ignoradas_models import DuplicataIgnorada

router = APIRouter(prefix="/racoes/sugestoes", tags=["Sugestões Inteligentes - Rações"])


# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def _validar_tenant_e_obter_usuario(user_and_tenant):
    """Desempacota e valida user_and_tenant"""
    current_user, tenant_id = user_and_tenant
    return current_user, tenant_id


# ============================================================================
# SCHEMAS
# ============================================================================

class DuplicataDetectada(BaseModel):
    """Possível duplicata detectada"""
    produto_1: Dict[str, Any]
    produto_2: Dict[str, Any]
    score_similaridade: float
    razoes: List[str]
    sugestao_acao: str


class PadronizacaoNome(BaseModel):
    """Sugestão de padronização de nome"""
    produto_id: int
    nome_atual: str
    nome_sugerido: str
    razao: str
    confianca: float


class GapEstoque(BaseModel):
    """Gap de estoque em segmento importante"""
    segmento_tipo: str  # "porte", "fase", "sabor", etc
    segmento_valor: str  # "Pequeno", "Adulto", "Frango"
    total_produtos: int
    produtos_sem_estoque: int
    percentual_sem_estoque: float
    importancia: str  # "Alta", "Média", "Baixa"
    faturamento_historico: float
    sugestao: str


# ============================================================================
# ENDPOINTS - DETECÇÃO DE DUPLICATAS
# ============================================================================

@router.get("/duplicatas", response_model=List[DuplicataDetectada])
async def detectar_duplicatas(
    threshold_similaridade: float = Query(0.80, ge=0.5, le=1.0, description="Limiar de similaridade (0-1)"),
    apenas_ativas: bool = Query(True, description="Apenas produtos ativos"),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Detecta possíveis produtos duplicados baseado em:
    - Nome similar (>80% de similaridade)
    - Mesmas características (porte, fase, sabor, peso)
    - Mesma marca
    
    Útil para:
    - Limpar cadastro antes de importação
    - Identificar produtos cadastrados duas vezes
    - Consolidar estoque
    """
    
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    # Buscar pares já ignorados pelo usuário
    pares_ignorados = db.query(DuplicataIgnorada).filter(
        DuplicataIgnorada.tenant_id == tenant_id
    ).all()
    
    # Criar set de pares ignorados para lookup rápido
    # Formato: {(menor_id, maior_id)}
    pares_ignorados_set = set()
    for par in pares_ignorados:
        id_menor = min(par.produto_id_1, par.produto_id_2)
        id_maior = max(par.produto_id_1, par.produto_id_2)
        pares_ignorados_set.add((id_menor, id_maior))
    
    # Buscar todos os produtos de ração
    query = db.query(Produto).filter(
        Produto.tenant_id == tenant_id,
        Produto.tipo == 'ração'
    )
    
    if apenas_ativas:
        query = query.filter(Produto.ativo == True)
    
    produtos = query.all()
    
    # Comparar produtos entre si
    duplicatas = []
    
    for i, prod1 in enumerate(produtos):
        for prod2 in produtos[i+1:]:
            # Verificar se este par foi ignorado anteriormente
            id_menor = min(prod1.id, prod2.id)
            id_maior = max(prod1.id, prod2.id)
            if (id_menor, id_maior) in pares_ignorados_set:
                continue  # Pular, usuário já marcou como não-duplicata
            
            score = 0
            razoes = []
            
            # ====== VERIFICAÇÕES QUE DESCARTAM DUPLICATA ======
            
            # 1. Peso DIFERENTE (diferença > 0.5kg) = NÃO É DUPLICATA
            if prod1.peso_embalagem and prod2.peso_embalagem:
                diferenca_peso = abs(prod1.peso_embalagem - prod2.peso_embalagem)
                if diferenca_peso > 0.5:
                    continue  # Pular, não é duplicata
            
            # 2. Fase DIFERENTE = NÃO É DUPLICATA
            # Verificar FK (nova arquitetura)
            if prod1.fase_publico_id and prod2.fase_publico_id:
                if prod1.fase_publico_id != prod2.fase_publico_id:
                    continue  # Pular, são fases diferentes (adulto vs filhote)
            
            # 3. Porte MUITO DIFERENTE = NÃO É DUPLICATA
            if prod1.porte_animal_id and prod2.porte_animal_id:
                # Se portes diferentes E nenhum é "Todos" = não duplicata
                if prod1.porte_animal_id != prod2.porte_animal_id:
                    porte1 = db.query(PorteAnimal).filter(PorteAnimal.id == prod1.porte_animal_id).first()
                    porte2 = db.query(PorteAnimal).filter(PorteAnimal.id == prod2.porte_animal_id).first()
                    if porte1 and porte2:
                        # Se nenhum é "Todos", considerar diferente
                        if porte1.nome != "Todos" and porte2.nome != "Todos":
                            # Permitir Pequeno/Médio ou Médio/Grande (próximos) mas não Pequeno/Grande
                            portes_ordem = {"Pequeno": 1, "Médio": 2, "Grande": 3, "Gigante": 4}
                            if porte1.nome in portes_ordem and porte2.nome in portes_ordem:
                                diferenca = abs(portes_ordem[porte1.nome] - portes_ordem[porte2.nome])
                                if diferenca > 1:
                                    continue  # Pular, portes muito diferentes
            
            # ====== ANÁLISE DE SIMILARIDADE ======
            
            # 1. Similaridade de nome (Levenshtein)
            nome_similarity = SequenceMatcher(None, prod1.nome.lower(), prod2.nome.lower()).ratio()
            
            if nome_similarity >= threshold_similaridade:
                score += 60
                razoes.append(f"Nomes {int(nome_similarity * 100)}% similares")
            else:
                # Se nome não for similar o suficiente, não é duplicata
                continue
            
            # 2. Mesma marca (OBRIGATÓRIO para considerar duplicata)
            if prod1.marca_id and prod2.marca_id:
                if prod1.marca_id == prod2.marca_id:
                    score += 15
                    razoes.append("Mesma marca")
                else:
                    # Marcas diferentes = não é duplicata
                    continue
            
            # 3. Mesmo peso (exato ou muito próximo)
            if prod1.peso_embalagem and prod2.peso_embalagem:
                if abs(prod1.peso_embalagem - prod2.peso_embalagem) < 0.1:
                    score += 10
                    razoes.append("Mesmo peso")
            
            # 4. Mesmo porte (usando FK)
            if prod1.porte_animal_id and prod2.porte_animal_id:
                if prod1.porte_animal_id == prod2.porte_animal_id:
                    score += 5
                    razoes.append("Mesmo porte")
            
            # 5. Mesma fase (usando FK)
            if prod1.fase_publico_id and prod2.fase_publico_id:
                if prod1.fase_publico_id == prod2.fase_publico_id:
                    score += 5
                    razoes.append("Mesma fase")
            
            # 6. Mesmo sabor (usando FK)
            if prod1.sabor_proteina_id and prod2.sabor_proteina_id:
                if prod1.sabor_proteina_id == prod2.sabor_proteina_id:
                    score += 5
                    razoes.append("Mesmo sabor")
            
            # Se score >= 70%, considerar possível duplicata
            if score >= 70:
                marca1 = db.query(Marca).filter(Marca.id == prod1.marca_id).first()
                marca2 = db.query(Marca).filter(Marca.id == prod2.marca_id).first()
                
                sugestao = "Verificar manualmente"
                if score >= 90:
                    sugestao = "Alta probabilidade de duplicata - Considerar mesclar"
                elif score >= 80:
                    sugestao = "Possível duplicata - Revisar características"
                
                duplicatas.append(DuplicataDetectada(
                    produto_1={
                        "id": prod1.id,
                        "nome": prod1.nome,
                        "marca": marca1.nome if marca1 else "Sem Marca",
                        "preco": float(prod1.preco_venda),
                        "estoque": float(prod1.estoque_atual) if prod1.estoque_atual else 0
                    },
                    produto_2={
                        "id": prod2.id,
                        "nome": prod2.nome,
                        "marca": marca2.nome if marca2 else "Sem Marca",
                        "preco": float(prod2.preco_venda),
                        "estoque": float(prod2.estoque_atual) if prod2.estoque_atual else 0
                    },
                    score_similaridade=round(score / 100, 2),
                    razoes=razoes,
                    sugestao_acao=sugestao
                ))
    
    # Ordenar por score decrescente
    duplicatas.sort(key=lambda x: x.score_similaridade, reverse=True)
    
    return duplicatas


@router.post("/duplicatas/ignorar")
async def ignorar_duplicata(
    produto_id_1: int,
    produto_id_2: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Marca um par de produtos como NÃO-DUPLICATA
    Este par não aparecerá mais na lista de duplicatas
    
    Útil para falsos positivos do algoritmo
    """
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    # Validar que produtos existem e pertencem ao tenant
    prod1 = db.query(Produto).filter(
        Produto.id == produto_id_1,
        Produto.tenant_id == tenant_id
    ).first()
    
    prod2 = db.query(Produto).filter(
        Produto.id == produto_id_2,
        Produto.tenant_id == tenant_id
    ).first()
    
    if not prod1 or not prod2:
        raise HTTPException(status_code=404, detail="Um ou ambos produtos não encontrados")
    
    # Garantir que IDs sejam salvos em ordem (menor primeiro)
    id_menor = min(produto_id_1, produto_id_2)
    id_maior = max(produto_id_1, produto_id_2)
    
    # Verificar se já existe
    existente = db.query(DuplicataIgnorada).filter(
        DuplicataIgnorada.tenant_id == tenant_id,
        DuplicataIgnorada.produto_id_1 == id_menor,
        DuplicataIgnorada.produto_id_2 == id_maior
    ).first()
    
    if existente:
        return {
            "success": True,
            "mensagem": "Este par já estava marcado como não-duplicata"
        }
    
    # Criar registro
    nova_ignorada = DuplicataIgnorada(
        tenant_id=tenant_id,
        produto_id_1=id_menor,
        produto_id_2=id_maior,
        usuario_id=current_user.id
    )
    
    db.add(nova_ignorada)
    db.commit()
    
    return {
        "success": True,
        "mensagem": f"Par {prod1.nome} x {prod2.nome} marcado como não-duplicata e não será mais sugerido"
    }


@router.post("/duplicatas/mesclar")
async def mesclar_produtos(
    produto_id_manter: int,
    produto_id_remover: int,
    transferir_estoque: bool = True,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Mescla dois produtos duplicados:
    - Mantém um produto ativo
    - Inativa o outro
    - Opcionalmente transfere estoque
    - Atualiza referências em vendas antigas
    
    ATENÇÃO: Ação irreversível (apenas inativa, não deleta)
    """
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    # Buscar produtos
    prod_manter = db.query(Produto).filter(
        Produto.id == produto_id_manter,
        Produto.tenant_id == tenant_id
    ).first()
    
    prod_remover = db.query(Produto).filter(
        Produto.id == produto_id_remover,
        Produto.tenant_id == tenant_id
    ).first()
    
    if not prod_manter or not prod_remover:
        raise HTTPException(status_code=404, detail="Um ou ambos produtos não encontrados")
    
    # Transferir estoque se solicitado
    if transferir_estoque and prod_remover.estoque_atual:
        if not prod_manter.estoque_atual:
            prod_manter.estoque_atual = 0
        prod_manter.estoque_atual += prod_remover.estoque_atual
        prod_remover.estoque_atual = 0
    
    # Inativar produto removido
    prod_remover.ativo = False
    
    # Registrar produto predecessor (para histórico de mesclagem)
    prod_remover.produto_predecessor_id = produto_id_manter
    prod_remover.data_descontinuacao = datetime.utcnow()
    prod_remover.motivo_descontinuacao = "Mesclado - Duplicata"
    
    db.commit()
    
    return {
        "success": True,
        "mensagem": f"Produto {produto_id_remover} mesclado com {produto_id_manter}",
        "produto_mantido": {
            "id": prod_manter.id,
            "nome": prod_manter.nome,
            "estoque": float(prod_manter.estoque_atual) if prod_manter.estoque_atual else 0
        }
    }


# ============================================================================
# ENDPOINTS - PADRONIZAÇÃO DE NOMES
# ============================================================================

@router.get("/padronizar-nomes", response_model=List[PadronizacaoNome])
async def sugerir_padronizacao_nomes(
    limite: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Sugere padronização de nomes de produtos baseado em campos classificados.
    
    Padrão estruturado:
    Ração [Marca] [Espécie] [Fase] [Porte] [Sabor] [Tratamento] [Peso]
    
    Exemplos:
    - "Ração Premier Cães Adultos Raças Médias e Grandes Frango 15kg"
    - "Ração Special Dog Cães Adulto Raças Pequenas Carne 15kg"
    - "Ração Golden Gatos Senior Light Salmão 3kg"
    """
    
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    # Buscar produtos de ração
    produtos = db.query(Produto).filter(
        Produto.tenant_id == tenant_id,
        Produto.classificacao_racao == 'sim',
        Produto.ativo == True
    ).limit(limite).all()
    
    sugestoes = []
    
    for produto in produtos:
        nome_atual = produto.nome.strip()
        partes_nome = ["Ração"]  # Prefixo padrão
        campos_usados = []
        confianca = 1.0
        
        # 1. MARCA
        if produto.marca_id:
            marca = db.query(Marca).filter(Marca.id == produto.marca_id).first()
            if marca:
                partes_nome.append(marca.nome)
                campos_usados.append("marca")
            else:
                confianca -= 0.1
        else:
            confianca -= 0.2
        
        # 2. ESPÉCIE (Cães, Gatos)
        if produto.especies_indicadas:
            especie_str = produto.especies_indicadas.lower()
            if especie_str == "dog":
                partes_nome.append("Cães")
                campos_usados.append("especie")
            elif especie_str == "cat":
                partes_nome.append("Gatos")
                campos_usados.append("especie")
            elif especie_str == "both":
                # Se for para ambos, incluir "Cães e Gatos" ou omitir?
                # Por padrão vou omitir para não deixar nome muito longo
                # mas registrar que foi identificado
                campos_usados.append("especie")
        else:
            confianca -= 0.15
        
        # 3. FASE/PÚBLICO
        if produto.fase_publico_id:
            fase = db.query(FasePublico).filter(FasePublico.id == produto.fase_publico_id).first()
            if fase and fase.nome != "Todos":
                partes_nome.append(fase.nome)
                campos_usados.append("fase")
            else:
                confianca -= 0.1
        else:
            confianca -= 0.15
        
        # 4. PORTE (Raças Pequenas, Raças Grandes, etc)
        if produto.porte_animal_id:
            porte = db.query(PorteAnimal).filter(PorteAnimal.id == produto.porte_animal_id).first()
            if porte and porte.nome != "Todos":
                # Adicionar "Raças" antes do porte para ficar mais descritivo
                porte_formatado = f"Raças {porte.nome}s" if not porte.nome.endswith('s') else f"Raças {porte.nome}"
                partes_nome.append(porte_formatado)
                campos_usados.append("porte")
            # Não penalizar se for "Todos" (ração para todos os portes)
        
        # 5. SABOR/PROTEÍNA
        if produto.sabor_proteina_id:
            sabor = db.query(SaborProteina).filter(SaborProteina.id == produto.sabor_proteina_id).first()
            if sabor:
                partes_nome.append(sabor.nome)
                campos_usados.append("sabor")
            else:
                confianca -= 0.1
        else:
            confianca -= 0.15
        
        # 6. TRATAMENTO (Light, Hipoalergênico, etc)
        if produto.tipo_tratamento_id:
            tratamento = db.query(TipoTratamento).filter(TipoTratamento.id == produto.tipo_tratamento_id).first()
            if tratamento:
                partes_nome.append(tratamento.nome)
                campos_usados.append("tratamento")
        # Tratamento é opcional, não penalizar se não tiver
        
        # 7. PESO
        if produto.peso_embalagem:
            # Formatar peso: se for inteiro, mostrar sem decimal
            peso_str = f"{int(produto.peso_embalagem)}kg" if produto.peso_embalagem == int(produto.peso_embalagem) else f"{produto.peso_embalagem}kg"
            partes_nome.append(peso_str)
            campos_usados.append("peso")
        else:
            confianca -= 0.2
        
        # Construir nome sugerido
        nome_sugerido = " ".join(partes_nome)
        
        # Só sugerir se:
        # 1. Tem pelo menos 3 campos (Ração + Marca + algo mais)
        # 2. É diferente do nome atual
        # 3. Confiança >= 50%
        if len(partes_nome) >= 3 and nome_sugerido.lower() != nome_atual.lower() and confianca >= 0.5:
            razao = f"Padronização estruturada usando: {', '.join(campos_usados)}"
            
            sugestoes.append(PadronizacaoNome(
                produto_id=produto.id,
                nome_atual=nome_atual,
                nome_sugerido=nome_sugerido,
                razao=razao,
                confianca=confianca
            ))
    
    # Ordenar por confiança decrescente
    sugestoes.sort(key=lambda x: x.confianca, reverse=True)
    
    return sugestoes


# ============================================================================
# ENDPOINTS - GAPS DE ESTOQUE
# ============================================================================

@router.get("/gaps-estoque", response_model=List[GapEstoque])
async def identificar_gaps_estoque(
    tipo_segmento: str = Query("porte", description="porte, fase, sabor, linha"),
    dias_analise: int = Query(90, ge=30, le=365, description="Dias para cálculo de importância"),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Identifica segmentos importantes com falta de estoque
    
    Importância calculada por:
    - Faturamento histórico do segmento (último X dias)
    - Quantidade de produtos no segmento
    - Percentual de produtos sem estoque
    
    Alerta quando:
    - Segmento gera >10% do faturamento total
    - >50% dos produtos sem estoque
    """
    
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    from datetime import datetime, timedelta
    data_limite = datetime.now() - timedelta(days=dias_analise)
    
    # Mapear tipo de segmento para campo
    campo_map = {
        "porte": "porte_animal",
        "fase": "fase_publico",
        "sabor": "sabor_proteina",
        "linha": "linha_racao",
        "especie": "especie_animal"
    }
    
    if tipo_segmento not in campo_map:
        raise HTTPException(400, "Tipo de segmento inválido")
    
    campo_nome = campo_map[tipo_segmento]
    
    # Buscar produtos
    produtos = db.query(Produto).filter(
        Produto.tenant_id == tenant_id,
        Produto.tipo == 'ração',
        Produto.ativo == True
    ).all()
    
    # Agrupar por segmento
    segmentos_dict = {}
    
    for produto in produtos:
        valor_campo = getattr(produto, campo_nome)
        
        # Se for JSONB (lista), iterar
        if isinstance(valor_campo, list):
            segmentos = valor_campo
        else:
            segmentos = [valor_campo] if valor_campo else []
        
        for segmento in segmentos:
            if not segmento:
                continue
            
            if segmento not in segmentos_dict:
                segmentos_dict[segmento] = {
                    "produtos": [],
                    "sem_estoque": 0,
                    "faturamento": 0
                }
            
            segmentos_dict[segmento]["produtos"].append(produto.id)
            
            if not produto.estoque_atual or produto.estoque_atual <= 0:
                segmentos_dict[segmento]["sem_estoque"] += 1
    
    # Calcular faturamento por segmento
    faturamento_total = 0
    for segmento, dados in segmentos_dict.items():
        produto_ids = dados["produtos"]
        
        faturamento = db.query(
            func.sum(VendaItem.preco_unitario * VendaItem.quantidade)
        ).join(
            Venda, VendaItem.venda_id == Venda.id
        ).filter(
            Venda.tenant_id == tenant_id,
            VendaItem.produto_id.in_(produto_ids),
            Venda.data_venda >= data_limite,
            Venda.status != 'cancelada'
        ).scalar() or 0
        
        dados["faturamento"] = float(faturamento)
        faturamento_total += float(faturamento)
    
    # Identificar gaps
    gaps = []
    
    for segmento, dados in segmentos_dict.items():
        total_produtos = len(dados["produtos"])
        sem_estoque = dados["sem_estoque"]
        percentual_sem_estoque = (sem_estoque / total_produtos * 100) if total_produtos > 0 else 0
        faturamento = dados["faturamento"]
        
        # Calcular importância
        percentual_faturamento = (faturamento / faturamento_total * 100) if faturamento_total > 0 else 0
        
        if percentual_faturamento >= 10:
            importancia = "Alta"
        elif percentual_faturamento >= 5:
            importancia = "Média"
        else:
            importancia = "Baixa"
        
        # Apenas alertar se tiver alto percentual sem estoque
        if percentual_sem_estoque >= 50:
            sugestao = ""
            if importancia == "Alta":
                sugestao = f"URGENTE: Segmento gera {percentual_faturamento:.1f}% do faturamento. Repor estoque imediatamente!"
            elif importancia == "Média":
                sugestao = f"ATENÇÃO: Segmento importante com {percentual_sem_estoque:.1f}% de produtos sem estoque."
            else:
                sugestao = "Considerar reposição ou descontinuar produtos."
            
            gaps.append(GapEstoque(
                segmento_tipo=tipo_segmento,
                segmento_valor=segmento,
                total_produtos=total_produtos,
                produtos_sem_estoque=sem_estoque,
                percentual_sem_estoque=round(percentual_sem_estoque, 1),
                importancia=importancia,
                faturamento_historico=round(faturamento, 2),
                sugestao=sugestao
            ))
    
    # Ordenar por importância e percentual sem estoque
    ordem_importancia = {"Alta": 3, "Média": 2, "Baixa": 1}
    gaps.sort(key=lambda x: (ordem_importancia.get(x.importancia, 0), x.percentual_sem_estoque), reverse=True)
    
    return gaps


# ============================================================================
# ENDPOINTS - RELATÓRIO CONSOLIDADO
# ============================================================================

@router.get("/relatorio-completo")
async def obter_relatorio_completo(
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Relatório consolidado com todas as sugestões
    
    Retorna:
    - Total de duplicatas detectadas
    - Total de nomes para padronizar
    - Gaps de estoque críticos
    - Score geral de "saúde" do cadastro (0-100)
    """
    
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    # Total de produtos
    total_produtos = db.query(func.count(Produto.id)).filter(
        Produto.tenant_id == tenant_id,
        Produto.tipo == 'ração',
        Produto.ativo == True
    ).scalar() or 0
    
    # Detectar duplicatas (limitado)
    duplicatas_response = await detectar_duplicatas(
        threshold_similaridade=0.85,
        apenas_ativas=True,
        user_and_tenant=user_and_tenant,
        db=db
    )
    total_duplicatas = len(duplicatas_response)
    
    # Sugestões de padronização
    padronizacao_response = await sugerir_padronizacao_nomes(
        limite=100,
        user_and_tenant=user_and_tenant,
        db=db
    )
    total_padronizacoes = len(padronizacao_response)
    
    # Gaps de estoque (apenas alta importância)
    gaps_response = await identificar_gaps_estoque(
        tipo_segmento="porte",
        dias_analise=90,
        user_and_tenant=user_and_tenant,
        db=db
    )
    gaps_criticos = [g for g in gaps_response if g.importancia == "Alta"]
    
    # Calcular score de saúde (0-100)
    score_saude = 100
    
    # Penalizar por duplicatas (máx -30)
    if total_produtos > 0:
        percentual_duplicatas = (total_duplicatas / total_produtos) * 100
        penalizacao_duplicatas = min(percentual_duplicatas * 3, 30)
        score_saude -= penalizacao_duplicatas
    
    # Penalizar por nomes não padronizados (máx -20)
    if total_produtos > 0:
        percentual_padronizacao = (total_padronizacoes / total_produtos) * 100
        penalizacao_nomes = min(percentual_padronizacao * 2, 20)
        score_saude -= penalizacao_nomes
    
    # Penalizar por gaps críticos (máx -50)
    penalizacao_gaps = len(gaps_criticos) * 10
    score_saude -= min(penalizacao_gaps, 50)
    
    score_saude = max(score_saude, 0)
    
    # Classificação
    if score_saude >= 90:
        classificacao = "Excelente"
        cor = "green"
    elif score_saude >= 70:
        classificacao = "Bom"
        cor = "blue"
    elif score_saude >= 50:
        classificacao = "Regular"
        cor = "yellow"
    else:
        classificacao = "Crítico"
        cor = "red"
    
    return {
        "score_saude": round(score_saude, 1),
        "classificacao": classificacao,
        "cor": cor,
        "total_produtos": total_produtos,
        "resumo": {
            "duplicatas_detectadas": total_duplicatas,
            "nomes_padronizar": total_padronizacoes,
            "gaps_criticos": len(gaps_criticos)
        },
        "top_duplicatas": duplicatas_response[:5] if duplicatas_response else [],
        "top_padronizacoes": padronizacao_response[:10] if padronizacao_response else [],
        "gaps_estoque": gaps_criticos,
        "recomendacoes": [
            f"Revisar {total_duplicatas} possíveis duplicatas" if total_duplicatas > 0 else None,
            f"Padronizar {total_padronizacoes} nomes de produtos" if total_padronizacoes > 0 else None,
            f"Repor estoque em {len(gaps_criticos)} segmentos críticos" if len(gaps_criticos) > 0 else None,
        ]
    }
