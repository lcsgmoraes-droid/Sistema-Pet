"""
Serviço de Concessão de Férias

VERSÃO 3.2: Consumo de Provisão + Contas a Pagar

Quando férias são concedidas:
1. Calcula valor real das férias
2. Consome provisão acumulada (férias + 1/3)
3. Gera conta a pagar real
4. Ajusta DRE se houver diferença

📌 Provisão vira obrigação financeira real
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


def conceder_ferias(
    db: Session,
    tenant_id: str,
    funcionario_id: int,
    mes: int,
    ano: int,
    usuario_id: int = None,
    data_pagamento: date = None,
    dias_ferias: int = 30
) -> dict:
    """
    Concede férias a um funcionário.

    Processo:
    1. Busca funcionário e salário
    2. Calcula valor real (férias + 1/3)
    3. Busca provisões acumuladas
    4. Gera baixa das provisões no DRE
    5. Gera ajuste se necessário
    6. Cria conta a pagar

    Args:
        db: Sessão do banco de dados
        tenant_id: ID do tenant
        funcionario_id: ID do funcionário
        mes: Mês de competência
        ano: Ano de competência
        usuario_id: ID do usuário que está concedendo
        data_pagamento: Data de vencimento da conta (default: último dia do mês)
        dias_ferias: Dias de férias concedidos (default: 30)

    Returns:
        dict com informações da concessão
    """

    logger.info(
        f"[FERIAS] Iniciando concessão de férias - "
        f"funcionario_id={funcionario_id}, periodo={mes}/{ano}"
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
        logger.error(f"[FERIAS] Funcionário não encontrado - ID={funcionario_id}")
        raise Exception("Funcionário não encontrado ou não é funcionário ativo")

    if not funcionario.cargo_id:
        logger.error(f"[FERIAS] Funcionário sem cargo - ID={funcionario_id}")
        raise Exception("Funcionário não possui cargo definido")

    cargo = (
        db.query(Cargo)
        .filter_by(id=funcionario.cargo_id, tenant_id=tenant_id)
        .first()
    )

    if not cargo:
        logger.error(f"[FERIAS] Cargo não encontrado - cargo_id={funcionario.cargo_id}")
        raise Exception("Cargo não encontrado")

    logger.info(
        f"[FERIAS] Funcionário: {funcionario.nome}, "
        f"Salário: R$ {cargo.salario_base}"
    )

    # 2️⃣ Calcular valor real das férias
    salario = Decimal(str(cargo.salario_base))

    # Proporcional aos dias
    valor_ferias = (salario / Decimal("30")) * Decimal(str(dias_ferias))
    valor_terco = valor_ferias / Decimal("3")  # 1/3 constitucional
    valor_total = (valor_ferias + valor_terco).quantize(Decimal("0.01"))

    logger.info(
        f"[FERIAS] Cálculo - Férias: R$ {valor_ferias:.2f}, "
        f"1/3: R$ {valor_terco:.2f}, Total: R$ {valor_total:.2f}"
    )

    # 3️⃣ Buscar categorias
    cat_ferias_provisao = (
        db.query(CategoriaFinanceira)
        .filter_by(
            tenant_id=tenant_id,
            nome="Provisão de Férias"
        )
        .first()
    )

    cat_terco_provisao = (
        db.query(CategoriaFinanceira)
        .filter_by(
            tenant_id=tenant_id,
            nome="Provisão 1/3 Constitucional"
        )
        .first()
    )

    cat_ferias_pagas = (
        db.query(CategoriaFinanceira)
        .filter_by(
            tenant_id=tenant_id,
            nome="Férias Pagas"
        )
        .first()
    )

    if not cat_ferias_provisao or not cat_terco_provisao:
        logger.error("[FERIAS] Categorias de provisão não encontradas")
        raise Exception(
            "Categorias de provisão não configuradas. "
            "Execute: criar_categorias_provisao_beneficios.py"
        )

    if not cat_ferias_pagas:
        logger.error("[FERIAS] Categoria 'Férias Pagas' não encontrada")
        raise Exception(
            "Categoria 'Férias Pagas' não configurada. "
            "Execute: criar_categoria_ferias_pagas.py"
        )

    # 4️⃣ Calcular provisões individuais do funcionário (salário + tempo trabalhado)
    # dre_detalhe_canais não tem funcionario_id, então calculamos diretamente
    hoje = date.today()
    data_contratacao = funcionario.created_at.date() if funcionario.created_at else hoje
    delta_dias = (hoje - data_contratacao).days
    meses_aquisitivos = int(delta_dias / 30.44) % 12
    if meses_aquisitivos == 0 and delta_dias >= 1:
        meses_aquisitivos = 1

    if cargo.gera_ferias:
        prov_ferias = (salario / 12 * meses_aquisitivos).quantize(Decimal("0.01"))
        prov_terco = (prov_ferias / 3).quantize(Decimal("0.01"))
    else:
        prov_ferias = Decimal("0.00")
        prov_terco = Decimal("0.00")

    total_provisao_ferias = prov_ferias + prov_terco

    logger.info(
        f"[FERIAS] Provisão acumulada - "
        f"Férias: R$ {prov_ferias:.2f}, "
        f"1/3: R$ {prov_terco:.2f}, "
        f"Total: R$ {total_provisao_ferias:.2f}"
    )

    # 5️⃣ Gerar baixa das provisões (valores negativos)
    ultima_data_mes = date(ano, mes, calendar.monthrange(ano, mes)[1])

    if total_provisao_ferias > 0:
        # Baixa provisão de férias
        baixa_ferias = DREDetalheCanal(
            tenant_id=tenant_id,
            usuario_id=usuario_id,
            mes=mes,
            ano=ano,
            data_inicio=date(ano, mes, 1),
            data_fim=ultima_data_mes,
            canal="provisao_consumo",
            despesas_pessoal=-float(prov_ferias + prov_terco)
        )

        db.add(baixa_ferias)

        logger.info(
            f"[FERIAS] Baixa de provisão gerada: R$ -{(prov_ferias + prov_terco):.2f}"
        )

    # 6️⃣ Calcular diferença e gerar ajuste se necessário
    diferenca = valor_total - total_provisao_ferias

    if abs(diferenca) > Decimal("0.01"):  # Tolerância de 1 centavo
        ajuste = DREDetalheCanal(
            tenant_id=tenant_id,
            usuario_id=usuario_id,
            mes=mes,
            ano=ano,
            data_inicio=date(ano, mes, 1),
            data_fim=ultima_data_mes,
            canal="ajuste_ferias",
            despesas_pessoal=float(diferenca)
        )

        db.add(ajuste)

        logger.info(
            f"[FERIAS] Ajuste gerado: R$ {diferenca:.2f} "
            f"({'excedente' if diferenca > 0 else 'sobra'})"
        )

    # 7️⃣ Gerar conta a pagar
    if not data_pagamento:
        data_pagamento = ultima_data_mes

    # ContaPagar requer dre_subcategoria_id e canal
    # Como não temos subcategoria específica, vamos usar um valor padrão
    # Em produção, isso deveria ser mapeado corretamente

    conta = ContaPagar(
        tenant_id=tenant_id,
        user_id=usuario_id or 1,
        descricao=f"Férias - {funcionario.nome} ({dias_ferias} dias)",
        fornecedor_id=funcionario_id,  # Funcionário como "fornecedor"
        categoria_id=cat_ferias_pagas.id,
        dre_subcategoria_id=None,  # DRE usa keyword-matching na descrição, não subcategoria
        canal="loja_fisica",  # TODO: Parametrizar
        valor_original=float(valor_total),
        valor_final=float(valor_total),
        data_emissao=date(ano, mes, 1),
        data_vencimento=data_pagamento,
        status="pendente",
        observacoes=f"Férias concedidas - {mes}/{ano}\nProvisão consumida: R$ {total_provisao_ferias:.2f}"
    )

    db.add(conta)
    db.flush()  # Para obter o ID

    logger.info(
        f"[FERIAS] Conta a pagar gerada - "
        f"ID={conta.id}, Valor=R$ {valor_total:.2f}"
    )

    # 8️⃣ Commit
    db.commit()

    logger.info(
        f"[FERIAS] ✅ Férias concedidas com sucesso - "
        f"Funcionário={funcionario.nome}, CP={conta.id}"
    )

    return {
        "sucesso": True,
        "mensagem": f"Férias concedidas para {funcionario.nome}",
        "funcionario": {
            "id": funcionario.id,
            "nome": funcionario.nome,
            "salario": float(salario)
        },
        "valores": {
            "ferias": float(valor_ferias),
            "terco_constitucional": float(valor_terco),
            "total": float(valor_total)
        },
        "provisao": {
            "ferias": float(prov_ferias),
            "terco": float(prov_terco),
            "total": float(total_provisao_ferias)
        },
        "ajuste": float(diferenca) if abs(diferenca) > Decimal("0.01") else 0,
        "conta_pagar": {
            "id": conta.id,
            "valor": float(valor_total),
            "vencimento": data_pagamento.isoformat(),
            "status": "pendente"
        }
    }


def cancelar_ferias(
    db: Session,
    tenant_id: str,
    conta_pagar_id: int,
    mes: int,
    ano: int,
    usuario_id: int = None
) -> dict:
    """
    Cancela férias concedidas (estorna provisão).

    ⚠️ Usar apenas em casos excepcionais.

    Args:
        db: Sessão do banco
        tenant_id: ID do tenant
        conta_pagar_id: ID da conta a pagar de férias
        mes: Mês do estorno
        ano: Ano do estorno
        usuario_id: ID do usuário

    Returns:
        dict com resultado do cancelamento
    """

    logger.info(
        f"[FERIAS] Cancelando férias - conta_pagar_id={conta_pagar_id}"
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
        raise Exception("Não é possível cancelar férias já pagas")

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
        canal="estorno_ferias",
        despesas_pessoal=float(conta.valor_original)  # Devolve provisão
    )

    db.add(estorno)
    db.commit()

    logger.info(
        f"[FERIAS] ✅ Férias canceladas - conta={conta_pagar_id}"
    )

    return {
        "sucesso": True,
        "mensagem": "Férias canceladas e provisão estornada",
        "conta_id": conta.id,
        "valor_estornado": float(conta.valor_original)
    }
