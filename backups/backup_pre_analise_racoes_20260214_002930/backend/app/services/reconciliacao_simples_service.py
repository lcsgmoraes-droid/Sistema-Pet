"""
Serviço de reconciliação do DAS Simples Nacional.
Substitui provisões por valores reais e gera ajustes no DRE.
"""

from decimal import Decimal
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import and_, extract, func

from app.ia.aba7_models import DREPeriodo
from app.empresa_config_fiscal_models import EmpresaConfigFiscal


def reconciliar_das_simples(
    db: Session,
    tenant_id,
    valor_das: Decimal,
    mes_competencia: int,
    ano_competencia: int,
    usuario_id: int = None
) -> dict:
    """
    Substitui provisão de Simples pelo valor real do DAS.
    Gera ajuste automático no DRE.
    
    REGRAS:
    - Busca provisão acumulada do mês (no campo impostos_detalhamento)
    - Calcula diferença: DAS real - Provisão acumulada
    - Gera ajuste no DRE (positivo ou negativo)
    - Atualiza valor final de impostos
    - Sugere nova alíquota para próximo mês
    
    Args:
        db: Sessão do banco
        tenant_id: ID do tenant
        valor_das: Valor real do DAS a pagar
        mes_competencia: Mês de competência do DAS
        ano_competencia: Ano de competência do DAS
        usuario_id: ID do usuário (opcional)
        
    Returns:
        dict com informações da reconciliação
    """
    
    valor_das = Decimal(str(valor_das))
    
    # 1️⃣ Buscar período DRE correspondente
    periodo = (
        db.query(DREPeriodo)
        .filter(
            and_(
                DREPeriodo.mes == mes_competencia,
                DREPeriodo.ano == ano_competencia
            )
        )
        .first()
    )
    
    if not periodo:
        return {
            "sucesso": False,
            "motivo": f"Período DRE {mes_competencia}/{ano_competencia} não encontrado",
            "sugestao": "Execute o fechamento do DRE deste mês primeiro"
        }
    
    # 2️⃣ Identificar provisão acumulada do mês
    # As provisões estão no campo impostos e detalhadas em impostos_detalhamento
    provisao_acumulada = periodo.impostos or Decimal("0.00")
    
    # Verificar se há provisões de Simples Nacional no detalhamento
    detalhamento = periodo.impostos_detalhamento or ""
    tem_provisao_simples = "Simples Nacional" in detalhamento
    
    if not tem_provisao_simples and provisao_acumulada == 0:
        # Não há provisão, apenas registrar o DAS como imposto real
        provisao_acumulada = Decimal("0.00")
    
    # 3️⃣ Calcular diferença
    diferenca = (valor_das - provisao_acumulada).quantize(Decimal("0.01"))
    
    # 4️⃣ Atualizar período DRE
    # Substituir provisão pelo valor real
    periodo.impostos = valor_das
    
    # Atualizar detalhamento
    novo_detalhamento = f"DAS Simples Nacional (REAL) - {mes_competencia:02d}/{ano_competencia}: R$ {valor_das:.2f}\n"
    if diferenca != 0:
        tipo_ajuste = "positivo" if diferenca > 0 else "negativo"
        novo_detalhamento += f"Ajuste DAS ({tipo_ajuste}): R$ {abs(diferenca):.2f}\n"
    
    periodo.impostos_detalhamento = novo_detalhamento
    periodo.regime_tributario = 'Simples Nacional'
    
    # 5️⃣ Recalcular lucro líquido
    if periodo.lucro_operacional is not None:
        periodo.lucro_liquido = periodo.lucro_operacional - periodo.impostos
        
        # Atualizar margem líquida
        if periodo.receita_liquida and periodo.receita_liquida > 0:
            periodo.margem_liquida_percent = float(
                (periodo.lucro_liquido / periodo.receita_liquida * 100).quantize(Decimal("0.01"))
            )
    
    # 6️⃣ Calcular alíquota efetiva real
    aliquota_efetiva_real = None
    if periodo.receita_bruta and periodo.receita_bruta > 0:
        aliquota_efetiva_real = float(
            (valor_das / periodo.receita_bruta * 100).quantize(Decimal("0.01"))
        )
        periodo.aliquota_efetiva_percent = aliquota_efetiva_real
    
    # 7️⃣ Sugerir nova alíquota para próximo mês
    # Atualizar config fiscal com dados reais
    config = (
        db.query(EmpresaConfigFiscal)
        .filter(EmpresaConfigFiscal.tenant_id == tenant_id)
        .first()
    )
    
    sugestao_aliquota = None
    if config and aliquota_efetiva_real:
        # Guardar alíquota anterior
        aliquota_anterior = config.simples_aliquota_vigente
        
        # Sugerir nova alíquota (arredondada para cima)
        import math
        sugestao_aliquota = math.ceil(aliquota_efetiva_real * 10) / 10
        
        # Atualizar automaticamente se diferença > 0.5%
        if abs(sugestao_aliquota - float(aliquota_anterior or 0)) > 0.5:
            config.simples_aliquota_vigente = Decimal(str(sugestao_aliquota))
            config.simples_ultima_atualizacao = date.today()
    
    # Commit
    db.commit()
    
    return {
        "sucesso": True,
        "periodo_id": periodo.id,
        "mes": mes_competencia,
        "ano": ano_competencia,
        "provisao_acumulada": float(provisao_acumulada),
        "valor_das_real": float(valor_das),
        "diferenca": float(diferenca),
        "tipo_ajuste": "positivo" if diferenca > 0 else ("negativo" if diferenca < 0 else "sem_ajuste"),
        "impostos_final": float(periodo.impostos),
        "aliquota_efetiva_real": aliquota_efetiva_real,
        "aliquota_anterior": float(config.simples_aliquota_vigente) if config else None,
        "sugestao_aliquota": sugestao_aliquota,
        "aliquota_atualizada_automaticamente": sugestao_aliquota != float(config.simples_aliquota_vigente) if config and sugestao_aliquota else False
    }


def criar_categoria_das_simples(db: Session, tenant_id, usuario_id: int) -> int:
    """
    Cria a categoria financeira DAS_SIMPLES se não existir.
    
    Returns:
        ID da categoria criada ou existente
    """
    from app.financeiro_models import CategoriaFinanceira
    from app.dre_models import DRESubcategoria
    
    # Verificar se já existe
    categoria = (
        db.query(CategoriaFinanceira)
        .filter(
            CategoriaFinanceira.tenant_id == tenant_id,
            CategoriaFinanceira.nome.ilike("%DAS%Simples%")
        )
        .first()
    )
    
    if categoria:
        return categoria.id
    
    # Buscar subcategoria de impostos no DRE
    subcategoria_impostos = (
        db.query(DRESubcategoria)
        .filter(
            DRESubcategoria.tenant_id == tenant_id,
            DRESubcategoria.nome.ilike("%impost%")
        )
        .first()
    )
    
    # Criar categoria
    nova_categoria = CategoriaFinanceira(
        tenant_id=tenant_id,
        user_id=usuario_id,
        nome="DAS - Simples Nacional",
        tipo="despesa",
        cor="#FF5733",
        icone="receipt_long",
        descricao="Documento de Arrecadação do Simples Nacional",
        dre_subcategoria_id=subcategoria_impostos.id if subcategoria_impostos else None,
        ativo=True
    )
    
    db.add(nova_categoria)
    db.commit()
    db.refresh(nova_categoria)
    
    return nova_categoria.id
