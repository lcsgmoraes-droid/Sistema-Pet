"""
Sincronização em tempo real entre lançamentos financeiros e DRE.
Garante que toda movimentação financeira atualize imediatamente a DRE.
"""

from decimal import Decimal
from datetime import date
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.dre_plano_contas_models import DRESubcategoria, NaturezaDRE, TipoCusto
from app.ia.aba7_models import DREPeriodo
from app.ia.aba7_dre_detalhada_models import DREDetalheCanal


def atualizar_dre_por_lancamento(
    db: Session,
    *,
    tenant_id,
    dre_subcategoria_id: int,
    canal: str,
    valor: Decimal,
    data_lancamento: date,
    tipo_movimentacao: str  # 'DESPESA' ou 'RECEITA'
) -> None:
    """
    Atualiza DREDetalheCanal em tempo real ao criar lançamento financeiro.
    
    REGRAS:
    - Se período estiver FECHADO → NÃO FAZ NADA
    - Se DREDetalheCanal não existir → CRIA
    - Atualiza campos conforme natureza da subcategoria
    - Persiste imediatamente
    
    Args:
        db: Sessão do banco
        tenant_id: ID do tenant (multi-tenant)
        dre_subcategoria_id: ID da subcategoria DRE (fonte da verdade)
        canal: Canal de venda (loja_fisica, mercado_livre, etc)
        valor: Valor do lançamento
        data_lancamento: Data do lançamento (para identificar período)
        tipo_movimentacao: 'DESPESA' ou 'RECEITA'
    """
    
    # 1. Validar subcategoria DRE
    subcategoria = (
        db.query(DRESubcategoria)
        .filter(
            DRESubcategoria.id == dre_subcategoria_id,
            DRESubcategoria.tenant_id == tenant_id,
            DRESubcategoria.ativo.is_(True),
        )
        .first()
    )
    
    if not subcategoria:
        raise HTTPException(
            status_code=400,
            detail=f"Subcategoria DRE {dre_subcategoria_id} inválida ou inativa para este tenant."
        )
    
    # 2. Identificar período DRE ABERTO correspondente à data
    # NOTA: DREPeriodo não possui campo 'fechado' - modelo legado
    # TODO: Migrar DREPeriodo para usar BaseTenantModel com tenant_id e campo fechado
    periodo = (
        db.query(DREPeriodo)
        .filter(
            DREPeriodo.data_inicio <= data_lancamento,
            DREPeriodo.data_fim >= data_lancamento,
        )
        .first()
    )
    
    if not periodo:
        # Se não há período aberto, não atualiza DRE
        # (pode ser período futuro ou passado já fechado)
        return
    
    # 3. Buscar ou criar DREDetalheCanal para este período + canal
    dre_detalhe = (
        db.query(DREDetalheCanal)
        .filter(
            DREDetalheCanal.tenant_id == tenant_id,
            DREDetalheCanal.usuario_id == periodo.usuario_id,
            DREDetalheCanal.data_inicio == periodo.data_inicio,
            DREDetalheCanal.data_fim == periodo.data_fim,
            DREDetalheCanal.canal == canal,
        )
        .first()
    )
    
    if not dre_detalhe:
        # Criar nova linha de DRE para este canal
        dre_detalhe = DREDetalheCanal(
            tenant_id=tenant_id,
            usuario_id=periodo.usuario_id,
            data_inicio=periodo.data_inicio,
            data_fim=periodo.data_fim,
            mes=periodo.data_inicio.month,
            ano=periodo.data_inicio.year,
            canal=canal,
            receita_bruta=0,
            deducoes_receita=0,
            receita_liquida=0,
            custo_produtos_vendidos=0,
            lucro_bruto=0,
            margem_bruta_percent=0,
            despesas_vendas=0,
            despesas_pessoal=0,
            despesas_administrativas=0,
            despesas_financeiras=0,
            outras_despesas=0,
            total_despesas_operacionais=0,
            lucro_operacional=0,
            margem_operacional_percent=0,
            impostos=0,
            lucro_liquido=0,
            margem_liquida_percent=0,
        )
        db.add(dre_detalhe)
        db.flush()
    
    # 4. Atualizar valores conforme natureza da subcategoria
    valor_decimal = float(valor)
    
    if subcategoria.categoria.natureza == NaturezaDRE.RECEITA:
        dre_detalhe.receita_bruta += valor_decimal
        dre_detalhe.receita_liquida = dre_detalhe.receita_bruta - dre_detalhe.deducoes_receita
    
    elif subcategoria.categoria.natureza == NaturezaDRE.CUSTO:
        dre_detalhe.custo_produtos_vendidos += valor_decimal
    
    elif subcategoria.categoria.natureza == NaturezaDRE.DESPESA:
        # Determinar tipo de despesa pelo nome da subcategoria (pode ser refinado)
        nome_lower = subcategoria.nome.lower()
        
        if 'venda' in nome_lower or 'comiss' in nome_lower or 'taxa' in nome_lower:
            dre_detalhe.despesas_vendas += valor_decimal
        elif 'pessoal' in nome_lower or 'salario' in nome_lower or 'folha' in nome_lower:
            dre_detalhe.despesas_pessoal += valor_decimal
        elif 'admin' in nome_lower or 'aluguel' in nome_lower or 'agua' in nome_lower or 'luz' in nome_lower:
            dre_detalhe.despesas_administrativas += valor_decimal
        elif 'financ' in nome_lower or 'juro' in nome_lower or 'banco' in nome_lower:
            dre_detalhe.despesas_financeiras += valor_decimal
        else:
            dre_detalhe.outras_despesas += valor_decimal
    
    # 5. Recalcular totalizadores
    dre_detalhe.lucro_bruto = dre_detalhe.receita_liquida - dre_detalhe.custo_produtos_vendidos
    
    if dre_detalhe.receita_liquida > 0:
        dre_detalhe.margem_bruta_percent = (dre_detalhe.lucro_bruto / dre_detalhe.receita_liquida) * 100
    
    dre_detalhe.total_despesas_operacionais = (
        dre_detalhe.despesas_vendas +
        dre_detalhe.despesas_pessoal +
        dre_detalhe.despesas_administrativas +
        dre_detalhe.despesas_financeiras +
        dre_detalhe.outras_despesas
    )
    
    dre_detalhe.lucro_operacional = dre_detalhe.lucro_bruto - dre_detalhe.total_despesas_operacionais
    
    if dre_detalhe.receita_liquida > 0:
        dre_detalhe.margem_operacional_percent = (dre_detalhe.lucro_operacional / dre_detalhe.receita_liquida) * 100
    
    dre_detalhe.lucro_liquido = dre_detalhe.lucro_operacional - dre_detalhe.impostos
    
    if dre_detalhe.receita_liquida > 0:
        dre_detalhe.margem_liquida_percent = (dre_detalhe.lucro_liquido / dre_detalhe.receita_liquida) * 100
    
    # Definir status
    if dre_detalhe.lucro_liquido > 0:
        dre_detalhe.status = 'lucro'
    elif dre_detalhe.lucro_liquido < 0:
        dre_detalhe.status = 'prejuizo'
    else:
        dre_detalhe.status = 'equilibrio'
    
    # 6. Inserir lançamento detalhado para drill-down (cada subcategoria visível)
    from sqlalchemy import text
    db.execute(text("""
        INSERT INTO dre_lancamentos (
            tenant_id, usuario_id, dre_detalhe_canal_id, dre_subcategoria_id,
            canal, valor, data_lancamento, data_competencia, origem, descricao
        ) VALUES (
            :tenant_id, :usuario_id, :dre_detalhe_id, :subcategoria_id,
            :canal, :valor, :data_lancamento, :data_competencia, :origem, :descricao
        )
    """), {
        'tenant_id': str(tenant_id),
        'usuario_id': dre_detalhe.usuario_id,
        'dre_detalhe_id': dre_detalhe.id,
        'subcategoria_id': dre_subcategoria_id,
        'canal': canal,
        'valor': valor_decimal,
        'data_lancamento': data_lancamento,
        'data_competencia': data_lancamento,
        'origem': tipo_movimentacao,
        'descricao': f"{subcategoria.nome} - {data_lancamento.strftime('%Y-%m-%d')}"
    })
    
    # 7. Persistir
    db.commit()
    db.refresh(dre_detalhe)
    
    # 8. Se subcategoria for INDIRETO_RATEAVEL, acionar rateio
    if subcategoria.tipo_custo == TipoCusto.INDIRETO_RATEAVEL:
        try:
            from app.domain.dre.rateio_engine import calcular_rateio_dre
            calcular_rateio_dre(
                db=db,
                periodo=periodo,
                tenant_id=tenant_id
            )
        except Exception as e:
            # Rateio não é crítico, apenas loga erro
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"⚠️ Erro ao calcular rateio após lançamento: {e}")
