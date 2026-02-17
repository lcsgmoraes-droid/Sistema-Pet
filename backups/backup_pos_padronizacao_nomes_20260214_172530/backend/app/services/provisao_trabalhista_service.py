"""
Serviço para geração automática de provisões trabalhistas mensais.
Gera provisões de Folha, INSS Patronal e FGTS no DRE.

VERSÃO 2.3: Calcula baseado em funcionários ativos e seus cargos
"""

from decimal import Decimal
from datetime import date
import calendar
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.ia.aba7_models import DREPeriodo
from app.empresa_config_fiscal_models import EmpresaConfigFiscal
from app.models import Cliente
from app.cargo_models import Cargo

import logging
logger = logging.getLogger(__name__)


def gerar_provisao_trabalhista_mensal(
    db: Session,
    tenant_id,
    mes: int,
    ano: int,
    usuario_id: int = None
) -> dict:
    """
    Gera provisões mensais de folha, INSS e FGTS no DRE.
    
    VERSÃO 2.3: Calcula automaticamente baseado nos funcionários ativos e seus cargos.
    
    Args:
        db: Sessão do banco de dados
        tenant_id: ID do tenant
        mes: Mês de competência (1-12)
        ano: Ano de competência
        usuario_id: ID do usuário (opcional)
        
    Returns:
        dict com informações das provisões geradas
    """
    
    # 1️⃣ Buscar funcionários ativos com cargos
    funcionarios = (
        db.query(Cliente, Cargo)
        .join(Cargo, Cliente.cargo_id == Cargo.id)
        .filter(
            Cliente.tenant_id == tenant_id,
            Cliente.tipo_cadastro == "funcionario",
            Cliente.ativo == True,
            Cliente.cargo_id.isnot(None),
            Cargo.ativo == True
        )
        .all()
    )
    
    if not funcionarios:
        return {
            "sucesso": False,
            "motivo": "Nenhum funcionário ativo com cargo definido",
            "sugestao": "Cadastre funcionários e associe-os a cargos"
        }
    
    # 2️⃣ Calcular totais
    folha_total = Decimal("0.00")
    inss_total = Decimal("0.00")
    fgts_total = Decimal("0.00")
    
    detalhes_funcionarios = []
    
    for func, cargo in funcionarios:
        salario = Decimal(str(cargo.salario_base))
        inss = (salario * Decimal(str(cargo.inss_patronal_percentual)) / Decimal(100)).quantize(Decimal("0.01"))
        fgts = (salario * Decimal(str(cargo.fgts_percentual)) / Decimal(100)).quantize(Decimal("0.01"))
        
        folha_total += salario
        inss_total += inss
        fgts_total += fgts
        
        detalhes_funcionarios.append({
            "nome": func.nome,
            "cargo": cargo.nome,
            "salario": float(salario),
            "inss": float(inss),
            "fgts": float(fgts)
        })
    
    total_provisoes = folha_total + inss_total + fgts_total
    
    # 3️⃣ Buscar ou criar período DRE
    periodo = (
        db.query(DREPeriodo)
        .filter(
            and_(
                DREPeriodo.usuario_id == usuario_id,
                DREPeriodo.mes == mes,
                DREPeriodo.ano == ano
            )
        )
        .first()
    )
    
    if not periodo:
        # Criar período básico
        ultimo_dia = calendar.monthrange(ano, mes)[1]
        
        periodo = DREPeriodo(
            usuario_id=usuario_id,
            data_inicio=date(ano, mes, 1),
            data_fim=date(ano, mes, ultimo_dia),
            mes=mes,
            ano=ano,
            receita_bruta=0,
            deducoes_receita=0,
            receita_liquida=0,
            custo_produtos_vendidos=0,
            lucro_bruto=0,
            despesas_vendas=0,
            despesas_administrativas=0,
            despesas_financeiras=0,
            outras_despesas=0,
            total_despesas_operacionais=0,
            lucro_operacional=0,
            impostos=0,
            lucro_liquido=0
        )
        db.add(periodo)
        db.flush()
        logger.info(f"✅ Período DRE criado: {mes}/{ano}")
    
    # 4️⃣ Verificar se já existe provisão (idempotência básica)
    detalhamento = periodo.impostos_detalhamento or ""
    if "Provisão Trabalhista Automática" in detalhamento and f"{mes:02d}/{ano}" in detalhamento:
        return {
            "sucesso": False,
            "motivo": f"Provisões já geradas para {mes:02d}/{ano}",
            "valores_existentes": {
                "folha": float(folha_total),
                "inss": float(inss_total),
                "fgts": float(fgts_total),
                "total": float(total_provisoes)
            },
            "funcionarios": detalhes_funcionarios
        }
    
    # 5️⃣ Registrar provisões no DRE
    # Provisões trabalhistas vão em despesas_administrativas
    periodo.despesas_administrativas = (periodo.despesas_administrativas or 0) + float(total_provisoes)
    
    # 6️⃣ Recalcular totais
    periodo.total_despesas_operacionais = (
        (periodo.despesas_vendas or 0) +
        (periodo.despesas_administrativas or 0) +
        (periodo.despesas_financeiras or 0) +
        (periodo.outras_despesas or 0)
    )
    
    periodo.lucro_operacional = (periodo.lucro_bruto or 0) - periodo.total_despesas_operacionais
    periodo.lucro_liquido = periodo.lucro_operacional - (periodo.impostos or 0)
    
    # 7️⃣ Atualizar margens
    if periodo.receita_liquida and periodo.receita_liquida > 0:
        periodo.margem_operacional_percent = (periodo.lucro_operacional / periodo.receita_liquida) * 100
        periodo.margem_liquida_percent = (periodo.lucro_liquido / periodo.receita_liquida) * 100
    
    # 8️⃣ Registrar detalhamento (rastreabilidade)
    novo_detalhamento = f"""
═══════════════════════════════════════════════════════
PROVISÃO TRABALHISTA AUTOMÁTICA - {mes:02d}/{ano}
Baseada em {len(funcionarios)} funcionário(s) ativo(s)
═══════════════════════════════════════════════════════
"""
    
    for det in detalhes_funcionarios:
        novo_detalhamento += f"{det['nome']:30s} ({det['cargo']})\n"
        novo_detalhamento += f"   Salário: R$ {det['salario']:>10,.2f}\n"
        novo_detalhamento += f"   INSS:    R$ {det['inss']:>10,.2f}\n"
        novo_detalhamento += f"   FGTS:    R$ {det['fgts']:>10,.2f}\n"
        novo_detalhamento += f"   ───────────────────────────────────────\n"
    
    novo_detalhamento += f"""
TOTAIS:
   Folha de Pagamento: R$ {folha_total:>12,.2f}
   INSS Patronal:      R$ {inss_total:>12,.2f}
   FGTS:               R$ {fgts_total:>12,.2f}
   ───────────────────────────────────────────────────────
   TOTAL PROVISÕES:    R$ {total_provisoes:>12,.2f}
═══════════════════════════════════════════════════════
"""
    
    periodo.impostos_detalhamento = (detalhamento + novo_detalhamento)
    
    db.flush()
    
    logger.info(f"✅ Provisões trabalhistas geradas para {mes:02d}/{ano}")
    logger.info(f"   Funcionários: {len(funcionarios)}")
    logger.info(f"   Folha: R$ {folha_total:.2f}")
    logger.info(f"   INSS:  R$ {inss_total:.2f}")
    logger.info(f"   FGTS:  R$ {fgts_total:.2f}")
    logger.info(f"   Total: R$ {total_provisoes:.2f}")
    
    return {
        "sucesso": True,
        "periodo_id": periodo.id,
        "mes": mes,
        "ano": ano,
        "funcionarios_count": len(funcionarios),
        "valores": {
            "folha_total": float(folha_total),
            "inss_total": float(inss_total),
            "fgts_total": float(fgts_total),
            "total": float(total_provisoes)
        },
        "funcionarios": detalhes_funcionarios
    }
