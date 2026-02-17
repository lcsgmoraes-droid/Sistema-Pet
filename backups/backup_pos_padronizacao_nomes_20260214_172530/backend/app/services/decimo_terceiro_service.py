"""
Serviço de Pagamento do 13º Salário

VERSÃO 3.3: Consumo de Provisão + Contas a Pagar

Quando 13º é pago (1ª ou 2ª parcela):
1. Calcula valor real (percentual do salário)
2. Consome provisão acumulada
3. Gera conta a pagar real
4. Ajusta DRE se houver diferença

📌 Provisão vira obrigação financeira real
📌 Suporta pagamento parcial (1ª parcela 50%) ou total
"""

from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, datetime
import calendar

from app.ia.aba7_dre_detalhada_models import DREDetalheCanal
from app.financeiro_models import CategoriaFinanceira, ContaPagar
from app.models import Cliente
from app.cargo_models import Cargo

import logging
logger = logging.getLogger(__name__)


def pagar_decimo_terceiro(
    db: Session,
    tenant_id: str,
    funcionario_id: int,
    percentual: float,
    mes: int,
    ano: int,
    usuario_id: int = None,
    data_pagamento: date = None,
    descricao_parcela: str = None
) -> dict:
    """
    Paga 13º salário (parcial ou total).
    
    Processo:
    1. Busca funcionário e salário
    2. Calcula valor real (percentual do salário)
    3. Busca provisão acumulada de 13º
    4. Gera baixa da provisão no DRE
    5. Gera ajuste se necessário
    6. Cria conta a pagar
    
    Args:
        db: Sessão do banco de dados
        tenant_id: ID do tenant
        funcionario_id: ID do funcionário
        percentual: Percentual do 13º a pagar (50 para 1ª parcela, 100 para integral)
        mes: Mês de competência
        ano: Ano de competência
        usuario_id: ID do usuário que está pagando
        data_pagamento: Data de vencimento da conta (default: último dia do mês)
        descricao_parcela: Descrição da parcela (ex: "1ª Parcela", "2ª Parcela")
        
    Returns:
        dict com informações do pagamento
    """
    
    logger.info(
        f"[13º SALARIO] Iniciando pagamento - "
        f"funcionario_id={funcionario_id}, percentual={percentual}%, periodo={mes}/{ano}"
    )
    
    # 1️⃣ Buscar funcionário
    funcionario = (
        db.query(Cliente)
        .join(Cargo, Cliente.cargo_id == Cargo.id)
        .filter(
            Cliente.id == funcionario_id,
            Cliente.tenant_id == tenant_id,
            Cliente.tipo_cadastro == "funcionario",
            Cliente.ativo == True
        )
        .first()
    )
    
    if not funcionario:
        logger.error(f"[13º SALARIO] Funcionário não encontrado - ID={funcionario_id}")
        raise Exception("Funcionário não encontrado ou não é funcionário ativo")
    
    if not funcionario.cargo_id:
        logger.error(f"[13º SALARIO] Funcionário sem cargo - ID={funcionario_id}")
        raise Exception("Funcionário não possui cargo definido")
    
    cargo = (
        db.query(Cargo)
        .filter_by(id=funcionario.cargo_id, tenant_id=tenant_id)
        .first()
    )
    
    if not cargo:
        logger.error(f"[13º SALARIO] Cargo não encontrado - cargo_id={funcionario.cargo_id}")
        raise Exception("Cargo não encontrado")
    
    logger.info(
        f"[13º SALARIO] Funcionário: {funcionario.nome}, "
        f"Salário: R$ {cargo.salario_base}"
    )
    
    # 2️⃣ Calcular valor real do 13º
    salario = Decimal(str(cargo.salario_base))
    percentual_decimal = Decimal(str(percentual)) / Decimal("100")
    valor_real = (salario * percentual_decimal).quantize(Decimal("0.01"))
    
    logger.info(
        f"[13º SALARIO] Cálculo - {percentual}% de R$ {salario:.2f} = R$ {valor_real:.2f}"
    )
    
    # 3️⃣ Buscar categorias
    cat_13_provisao = (
        db.query(CategoriaFinanceira)
        .filter_by(
            tenant_id=tenant_id,
            nome="Provisão de 13º Salário"
        )
        .first()
    )
    
    cat_13_pago = (
        db.query(CategoriaFinanceira)
        .filter_by(
            tenant_id=tenant_id,
            nome="13º Salário Pago"
        )
        .first()
    )
    
    if not cat_13_provisao:
        logger.error("[13º SALARIO] Categoria de provisão não encontrada")
        raise Exception(
            "Categoria 'Provisão de 13º Salário' não configurada. "
            "Execute: criar_categorias_provisao_beneficios.py"
        )
    
    if not cat_13_pago:
        logger.error("[13º SALARIO] Categoria '13º Salário Pago' não encontrada")
        raise Exception(
            "Categoria '13º Salário Pago' não configurada. "
            "Execute: criar_categoria_13_pago.py"
        )
    
    # 4️⃣ Calcular provisão acumulada de 13º
    # Soma todos os lançamentos de provisão de 13º
    provisao_13_acum = (
        db.query(func.coalesce(func.sum(DREDetalheCanal.despesas_pessoal), 0))
        .filter(
            DREDetalheCanal.tenant_id == tenant_id,
            DREDetalheCanal.canal == "provisao"
            # Filtro por categoria seria ideal, mas DREDetalheCanal não tem
            # Vamos assumir proporção: 13º = 200/466.67 ≈ 42,86%
        )
        .scalar()
    )
    
    # Calcular proporção do 13º na provisão total
    # Total provisão = férias(250) + 1/3(83.33) + 13º(250) = 583.33 por mês
    # 13º = 250/583.33 = 42.86%
    total_provisao = Decimal(str(provisao_13_acum))
    prop_13 = Decimal("0.4286")  # 42,86% aproximadamente
    
    provisao_13 = (total_provisao * prop_13).quantize(Decimal("0.01"))
    
    logger.info(
        f"[13º SALARIO] Provisão acumulada: R$ {provisao_13:.2f}"
    )
    
    # 5️⃣ Consumir provisão (até o limite disponível)
    consumo = min(valor_real, provisao_13)
    
    ultima_data_mes = date(ano, mes, calendar.monthrange(ano, mes)[1])
    
    if consumo > 0:
        # Baixa provisão de 13º
        baixa = DREDetalheCanal(
            tenant_id=tenant_id,
            usuario_id=usuario_id,
            mes=mes,
            ano=ano,
            data_inicio=date(ano, mes, 1),
            data_fim=ultima_data_mes,
            canal="provisao_consumo_13",
            despesas_pessoal=-float(consumo)
        )
        
        db.add(baixa)
        
        logger.info(
            f"[13º SALARIO] Baixa de provisão gerada: R$ -{consumo:.2f}"
        )
    
    # 6️⃣ Calcular diferença e gerar ajuste se necessário
    diferenca = valor_real - consumo
    
    if abs(diferenca) > Decimal("0.01"):  # Tolerância de 1 centavo
        ajuste = DREDetalheCanal(
            tenant_id=tenant_id,
            usuario_id=usuario_id,
            mes=mes,
            ano=ano,
            data_inicio=date(ano, mes, 1),
            data_fim=ultima_data_mes,
            canal="ajuste_13",
            despesas_pessoal=float(diferenca)
        )
        
        db.add(ajuste)
        
        logger.info(
            f"[13º SALARIO] Ajuste gerado: R$ {diferenca:.2f} "
            f"({'excedente' if diferenca > 0 else 'sobra'})"
        )
    
    # 7️⃣ Gerar conta a pagar
    if not data_pagamento:
        data_pagamento = ultima_data_mes
    
    if not descricao_parcela:
        if percentual <= 50:
            descricao_parcela = "1ª Parcela"
        elif percentual < 100:
            descricao_parcela = "Parcial"
        else:
            descricao_parcela = "Integral"
    
    conta = ContaPagar(
        tenant_id=tenant_id,
        user_id=usuario_id or 1,
        descricao=f"13º Salário ({descricao_parcela} - {percentual}%) - {funcionario.nome}",
        fornecedor_id=funcionario_id,
        categoria_id=cat_13_pago.id,
        dre_subcategoria_id=1,  # TODO: Mapear corretamente
        canal="loja_fisica",  # TODO: Parametrizar
        valor_original=float(valor_real),
        valor_final=float(valor_real),
        data_emissao=date(ano, mes, 1),
        data_vencimento=data_pagamento,
        status="pendente",
        observacoes=f"13º Salário ({percentual}%) - {mes}/{ano}\nProvisão consumida: R$ {consumo:.2f}"
    )
    
    db.add(conta)
    db.flush()
    
    logger.info(
        f"[13º SALARIO] Conta a pagar gerada - "
        f"ID={conta.id}, Valor=R$ {valor_real:.2f}"
    )
    
    # 8️⃣ Commit
    db.commit()
    
    logger.info(
        f"[13º SALARIO] ✅ Pagamento realizado com sucesso - "
        f"Funcionário={funcionario.nome}, CP={conta.id}"
    )
    
    return {
        "sucesso": True,
        "mensagem": f"13º Salário ({descricao_parcela}) pago para {funcionario.nome}",
        "funcionario": {
            "id": funcionario.id,
            "nome": funcionario.nome,
            "salario": float(salario)
        },
        "valores": {
            "percentual": float(percentual),
            "valor_calculado": float(valor_real)
        },
        "provisao": {
            "disponivel": float(provisao_13),
            "consumida": float(consumo)
        },
        "ajuste": float(diferenca) if abs(diferenca) > Decimal("0.01") else 0,
        "conta_pagar": {
            "id": conta.id,
            "valor": float(valor_real),
            "vencimento": data_pagamento.isoformat(),
            "status": "pendente",
            "descricao": descricao_parcela
        }
    }


def cancelar_decimo_terceiro(
    db: Session,
    tenant_id: str,
    conta_pagar_id: int,
    mes: int,
    ano: int,
    usuario_id: int = None
) -> dict:
    """
    Cancela pagamento de 13º (estorna provisão).
    
    ⚠️ Usar apenas em casos excepcionais.
    
    Args:
        db: Sessão do banco
        tenant_id: ID do tenant
        conta_pagar_id: ID da conta a pagar de 13º
        mes: Mês do estorno
        ano: Ano do estorno
        usuario_id: ID do usuário
        
    Returns:
        dict com resultado do cancelamento
    """
    
    logger.info(
        f"[13º SALARIO] Cancelando pagamento - conta_pagar_id={conta_pagar_id}"
    )
    
    # Buscar conta
    conta = (
        db.query(ContaPagar)
        .filter_by(
            id=conta_pagar_id,
            tenant_id=tenant_id
        )
        .first()
    )
    
    if not conta:
        raise Exception("Conta a pagar não encontrada")
    
    if conta.status == "pago":
        raise Exception("Não é possível cancelar 13º já pago")
    
    # Cancelar conta
    conta.status = "cancelado"
    conta.observacoes = (conta.observacoes or "") + f"\nCancelado em {datetime.now()}"
    
    # Estornar baixa de provisão (devolver provisão)
    ultima_data_mes = date(ano, mes, calendar.monthrange(ano, mes)[1])
    
    estorno = DREDetalheCanal(
        tenant_id=tenant_id,
        usuario_id=usuario_id,
        mes=mes,
        ano=ano,
        data_inicio=date(ano, mes, 1),
        data_fim=ultima_data_mes,
        canal="estorno_13",
        despesas_pessoal=float(conta.valor_original)  # Devolve provisão
    )
    
    db.add(estorno)
    db.commit()
    
    logger.info(
        f"[13º SALARIO] ✅ Pagamento cancelado - conta={conta_pagar_id}"
    )
    
    return {
        "sucesso": True,
        "mensagem": "13º cancelado e provisão estornada",
        "conta_id": conta.id,
        "valor_estornado": float(conta.valor_original)
    }
