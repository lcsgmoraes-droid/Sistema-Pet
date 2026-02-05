"""
Serviço para gerar provisão de Simples Nacional no DRE
quando uma NF for autorizada.
"""

from decimal import Decimal
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.empresa_config_fiscal_models import EmpresaConfigFiscal
from app.ia.aba7_models import DREPeriodo


def gerar_provisao_simples_por_nf(
    db: Session,
    tenant_id,
    valor_nf: Decimal,
    data_emissao: date,
    usuario_id: int = None
) -> dict:
    """
    Gera provisão de Simples Nacional no DRE
    com base na NF autorizada.
    
    REGRAS:
    - Evento gerador: NF autorizada (não venda, não pagamento)
    - Não gera conta a pagar
    - Não gera DAS
    - Lança apenas provisão contábil no DRE
    - Usa alíquota vigente no momento da emissão
    - Respeita competência (mês/ano da NF)
    - Se o período não existir, cria automaticamente
    
    Args:
        db: Sessão do banco
        tenant_id: ID do tenant (usado para buscar config fiscal)
        valor_nf: Valor total da NF
        data_emissao: Data de emissão da NF
        usuario_id: ID do usuário (necessário para criar período se não existir)
        
    Returns:
        dict com informações da provisão criada
    """
    
    # 1. Buscar configuração do Simples Nacional pelo tenant
    config = (
        db.query(EmpresaConfigFiscal)
        .filter(EmpresaConfigFiscal.tenant_id == tenant_id)
        .first()
    )
    
    if not config or not config.simples_ativo:
        return {
            "sucesso": False,
            "motivo": "Simples Nacional não está ativo"
        }
    
    if not config.simples_aliquota_vigente:
        return {
            "sucesso": False,
            "motivo": "Alíquota não configurada"
        }
    
    # 2. Calcular valor da provisão
    aliquota = Decimal(str(config.simples_aliquota_vigente)) / Decimal("100")
    valor_provisao = (Decimal(str(valor_nf)) * aliquota).quantize(Decimal("0.01"))
    
    # 3. Identificar competência
    competencia_mes = data_emissao.month
    competencia_ano = data_emissao.year
    
    # 4. Buscar período DRE correspondente
    periodo = (
        db.query(DREPeriodo)
        .filter(
            and_(
                DREPeriodo.mes == competencia_mes,
                DREPeriodo.ano == competencia_ano
            )
        )
        .first()
    )
    
    # 5. Se o período não existir, criar
    if not periodo:
        # Buscar usuario_id se não fornecido
        if not usuario_id:
            from app.models import User
            usuario = db.query(User).first()
            usuario_id = usuario.id if usuario else 1
        
        # Calcular datas do período
        data_inicio = datetime(competencia_ano, competencia_mes, 1).date()
        if competencia_mes == 12:
            data_fim = datetime(competencia_ano, 12, 31).date()
        else:
            data_fim = (datetime(competencia_ano, competencia_mes + 1, 1) - timedelta(days=1)).date()
        
        periodo = DREPeriodo(
            usuario_id=usuario_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            mes=competencia_mes,
            ano=competencia_ano,
            status='aberto',
            impostos=Decimal("0"),
            regime_tributario='Simples Nacional'
        )
        db.add(periodo)
        db.flush()
    
    # 6. Verificar se o período está fechado
    if periodo.status == 'fechado':
        return {
            "sucesso": False,
            "motivo": f"Período {competencia_mes}/{competencia_ano} está fechado"
        }
    
    # 7. Adicionar provisão ao período
    impostos_anterior = periodo.impostos or Decimal("0")
    periodo.impostos = impostos_anterior + valor_provisao
    
    # Atualizar detalhamento
    detalhamento_atual = periodo.impostos_detalhamento or ""
    periodo.impostos_detalhamento = (
        detalhamento_atual + 
        f"Simples Nacional (NF autorizada {data_emissao.strftime('%d/%m/%Y')}): R$ {valor_provisao:.2f}\n"
    )
    
    # Garantir regime tributário
    if not periodo.regime_tributario:
        periodo.regime_tributario = 'Simples Nacional'
    
    # 8. Calcular alíquota efetiva se houver receita
    if periodo.receita_bruta and periodo.receita_bruta > 0:
        periodo.aliquota_efetiva_percent = float(
            (periodo.impostos / periodo.receita_bruta * 100).quantize(Decimal("0.01"))
        )
    
    # 9. Recalcular lucro líquido
    _recalcular_lucro_liquido(periodo)
    
    # Commit
    db.commit()
    
    return {
        "sucesso": True,
        "periodo_id": periodo.id,
        "mes": competencia_mes,
        "ano": competencia_ano,
        "valor_provisao": float(valor_provisao),
        "impostos_total": float(periodo.impostos),
        "aliquota": float(config.simples_aliquota_vigente),
        "anexo": config.simples_anexo
    }


def _recalcular_lucro_liquido(periodo: DREPeriodo) -> None:
    """
    Recalcula o lucro líquido do período considerando impostos.
    
    Lucro Líquido = Lucro Operacional - Impostos
    """
    if periodo.lucro_operacional is not None and periodo.impostos is not None:
        periodo.lucro_liquido = periodo.lucro_operacional - periodo.impostos
        
        # Atualizar margem líquida
        if periodo.receita_liquida and periodo.receita_liquida > 0:
            periodo.margem_liquida_percent = float(
                (periodo.lucro_liquido / periodo.receita_liquida * 100).quantize(Decimal("0.01"))
            )

