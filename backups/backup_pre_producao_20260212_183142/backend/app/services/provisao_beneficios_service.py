"""
Serviço de Provisão de Benefícios (Férias e 13º Salário)

VERSÃO 3.1: Provisões Acumuladas

Características:
- ✅ Acumula ao longo do tempo (não substitui)
- ✅ Calcula 1/12 do salário mensal
- ✅ Gera lançamentos no DRE
- ❌ NÃO gera contas a pagar
- ❌ NÃO integra com financeiro
"""

from decimal import Decimal
from sqlalchemy.orm import Session
from datetime import date
import calendar

from app.ia.aba7_dre_detalhada_models import DREDetalheCanal
from app.financeiro_models import CategoriaFinanceira
from app.models import Cliente
from app.cargo_models import Cargo

import logging
logger = logging.getLogger(__name__)


def gerar_provisao_ferias_e_13_mensal(
    db: Session,
    tenant_id: str,
    mes: int,
    ano: int,
    usuario_id: int = None
) -> dict:
    """
    Gera provisão mensal acumulada de férias, 1/3 constitucional e 13º salário.
    
    📌 IMPORTANTE: Esta função ACUMULA valores ao longo do tempo.
    Não substitui nem zera provisões anteriores.
    
    Cálculo:
    - Férias: salário / 12 (mensal)
    - 1/3 Constitucional: (salário / 12) / 3 = salário / 36
    - 13º Salário: salário / 12 (mensal)
    
    Args:
        db: Sessão do banco de dados
        tenant_id: ID do tenant
        mes: Mês de competência (1-12)
        ano: Ano de competência
        usuario_id: ID do usuário (opcional)
        
    Returns:
        dict com informações das provisões geradas
    """
    
    logger.info(
        f"[PROVISAO BENEFICIOS] Iniciando provisão mensal - "
        f"tenant={tenant_id}, periodo={mes}/{ano}"
    )
    
    # 1️⃣ Buscar funcionários ativos com cargos
    funcionarios = (
        db.query(Cliente, Cargo)
        .join(Cargo, Cliente.cargo_id == Cargo.id)
        .filter(
            Cliente.tenant_id == tenant_id,
            Cliente.tipo_cadastro == "funcionario",  # Funcionários
            Cliente.ativo == True,
            Cliente.cargo_id.isnot(None),
            Cargo.ativo == True
        )
        .all()
    )
    
    if not funcionarios:
        logger.warning(
            f"[PROVISAO BENEFICIOS] Nenhum funcionário ativo encontrado - "
            f"tenant={tenant_id}"
        )
        return {
            "sucesso": True,
            "mensagem": "Nenhum funcionário ativo para provisionar",
            "funcionarios": 0,
            "valores": {}
        }
    
    logger.info(
        f"[PROVISAO BENEFICIOS] Encontrados {len(funcionarios)} funcionários ativos"
    )
    
    # 2️⃣ Calcular provisões acumuladas
    total_ferias = Decimal("0.00")
    total_terco = Decimal("0.00")
    total_13 = Decimal("0.00")
    
    detalhes_funcionarios = []
    
    for funcionario, cargo in funcionarios:
        salario = Decimal(str(cargo.salario_base))
        
        # Provisão mensal = salário / 12
        ferias_mensal = salario / Decimal("12")
        terco_mensal = ferias_mensal / Decimal("3")  # 1/3 das férias
        decimo_mensal = salario / Decimal("12")
        
        total_ferias += ferias_mensal
        total_terco += terco_mensal
        total_13 += decimo_mensal
        
        detalhes_funcionarios.append({
            "funcionario": funcionario.nome,
            "salario": float(salario),
            "ferias": float(ferias_mensal),
            "terco": float(terco_mensal),
            "decimo_terceiro": float(decimo_mensal)
        })
        
        logger.debug(
            f"[PROVISAO BENEFICIOS] {funcionario.nome}: "
            f"salario={salario}, ferias={ferias_mensal}, "
            f"terco={terco_mensal}, 13={decimo_mensal}"
        )
    
    logger.info(
        f"[PROVISAO BENEFICIOS] Totais calculados - "
        f"ferias={total_ferias}, terco={total_terco}, 13={total_13}"
    )
    
    # 3️⃣ Mapear categorias para valores
    valores_por_categoria = {
        "Provisão de Férias": total_ferias,
        "Provisão 1/3 Constitucional": total_terco,
        "Provisão de 13º Salário": total_13,
    }
    
    # 4️⃣ Gerar lançamentos no DRE
    ultima_data_mes = date(ano, mes, calendar.monthrange(ano, mes)[1])
    
    lancamentos_criados = []
    
    for nome_categoria, valor in valores_por_categoria.items():
        if valor <= 0:
            logger.debug(
                f"[PROVISAO BENEFICIOS] Pulando {nome_categoria} - valor zerado"
            )
            continue
        
        # Buscar categoria financeira
        categoria = (
            db.query(CategoriaFinanceira)
            .filter_by(
                tenant_id=tenant_id,
                nome=nome_categoria
            )
            .first()
        )
        
        if not categoria:
            logger.warning(
                f"[PROVISAO BENEFICIOS] ⚠️ Categoria não encontrada: {nome_categoria}"
            )
            continue
        
        # Criar lançamento no DRE
        lancamento = DREDetalheCanal(
            tenant_id=tenant_id,
            usuario_id=usuario_id,
            mes=mes,
            ano=ano,
            data_inicio=date(ano, mes, 1),
            data_fim=ultima_data_mes,
            canal="provisao",  # Canal especial para provisões
            despesas_pessoal=float(valor.quantize(Decimal("0.01")))
        )
        
        db.add(lancamento)
        
        lancamentos_criados.append({
            "categoria": nome_categoria,
            "valor": float(valor.quantize(Decimal("0.01")))
        })
        
        logger.info(
            f"[PROVISAO BENEFICIOS] ✅ Lançamento criado - "
            f"{nome_categoria}: R$ {valor:.2f}"
        )
    
    # 5️⃣ Commit
    db.commit()
    
    logger.info(
        f"[PROVISAO BENEFICIOS] ✅ Provisões geradas com sucesso - "
        f"{len(lancamentos_criados)} lançamentos"
    )
    
    return {
        "sucesso": True,
        "mensagem": f"Provisões geradas para {len(funcionarios)} funcionários",
        "funcionarios": len(funcionarios),
        "valores": {
            "ferias": float(total_ferias.quantize(Decimal("0.01"))),
            "terco_constitucional": float(total_terco.quantize(Decimal("0.01"))),
            "decimo_terceiro": float(total_13.quantize(Decimal("0.01"))),
            "total": float((total_ferias + total_terco + total_13).quantize(Decimal("0.01")))
        },
        "lancamentos": lancamentos_criados,
        "detalhes_funcionarios": detalhes_funcionarios
    }


def calcular_provisao_acumulada(
    db: Session,
    tenant_id: str,
    mes_inicio: int,
    ano_inicio: int,
    mes_fim: int,
    ano_fim: int
) -> dict:
    """
    Calcula o total acumulado de provisões entre dois períodos.
    
    Útil para saber quanto foi provisionado até determinado mês.
    
    Args:
        db: Sessão do banco
        tenant_id: ID do tenant
        mes_inicio: Mês inicial
        ano_inicio: Ano inicial
        mes_fim: Mês final
        ano_fim: Ano final
        
    Returns:
        dict com totais acumulados por tipo de provisão
    """
    
    from sqlalchemy import and_
    
    # Buscar todos os lançamentos de provisão no período
    lancamentos = (
        db.query(DREDetalheCanal)
        .filter(
            DREDetalheCanal.tenant_id == tenant_id,
            DREDetalheCanal.canal == "provisao",
            and_(
                DREDetalheCanal.ano >= ano_inicio,
                DREDetalheCanal.ano <= ano_fim
            )
        )
        .all()
    )
    
    # Filtrar por mês dentro do ano
    lancamentos_periodo = []
    for lanc in lancamentos:
        if (
            (lanc.ano > ano_inicio or (lanc.ano == ano_inicio and lanc.mes >= mes_inicio)) and
            (lanc.ano < ano_fim or (lanc.ano == ano_fim and lanc.mes <= mes_fim))
        ):
            lancamentos_periodo.append(lanc)
    
    total_acumulado = sum(l.despesas_pessoal or 0 for l in lancamentos_periodo)
    
    return {
        "periodo": f"{mes_inicio}/{ano_inicio} a {mes_fim}/{ano_fim}",
        "lancamentos": len(lancamentos_periodo),
        "total_acumulado": total_acumulado
    }
