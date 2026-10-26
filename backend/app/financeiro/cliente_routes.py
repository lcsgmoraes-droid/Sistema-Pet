"""Rotas financeiras dedicadas ao historico de clientes."""

from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session

router = APIRouter()


def _divida_do_cliente(tenant_id):
    from app.financeiro_models import ContaReceber, FormaPagamento
    from app.financeiro.recebiveis_operadora import TIPOS_RECEBIVEL_OPERADORA

    # A venda no cartao ja foi paga pelo cliente. O saldo a repassar pertence
    # a operadora, mesmo quando guarda cliente_id para rastrear a origem.
    return ~ContaReceber.forma_pagamento.has(
        and_(
            FormaPagamento.tenant_id == tenant_id,
            FormaPagamento.tipo.in_(TIPOS_RECEBIVEL_OPERADORA),
        )
    )


@router.get("/cliente/{cliente_id}")
async def get_historico_financeiro_cliente(
    cliente_id: int,
    page: int = 1,
    per_page: int = 20,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    tipo: Optional[str] = None,  # venda, devolucao, conta_receber, recebimento, credito
    status: Optional[str] = None,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    ## 📊 HISTÓRICO FINANCEIRO COMPLETO DO CLIENTE (NOVA ROTA DEDICADA)

    **Rota performática com paginação obrigatória para análise financeira detalhada.**

    ### Parâmetros:
    - **cliente_id**: ID do cliente
    - **page**: Número da página (padrão: 1)
    - **per_page**: Itens por página (padrão: 20, máximo: 100)
    - **data_inicio**: Filtro data inicial (formato: YYYY-MM-DD)
    - **data_fim**: Filtro data final (formato: YYYY-MM-DD)
    - **tipo**: Filtro por tipo de transação
    - **status**: Filtro por status

    ### Tipos de transação:
    - `venda`: Vendas finalizadas
    - `devolucao`: Vendas canceladas/devolvidas
    - `conta_receber`: Contas a receber (parcelas)
    - `recebimento`: Recebimentos de contas
    - `credito`: Movimentações de crédito do cliente

    ### Retorna:
    - **cliente**: Dados básicos do cliente
    - **resumo**: Totais agregados (últimos 90 dias)
    - **historico**: Lista paginada de transações
    - **paginacao**: Metadados de paginação (total, páginas, etc)

    ### Performance:
    - ✅ Paginação em nível de banco (não carrega tudo em memória)
    - ✅ Índices otimizados
    - ✅ Filtros aplicados antes da ordenação
    - ✅ Aggregations separadas do histórico
    """
    # Importar modelos
    from app.vendas_models import Venda
    from app.financeiro_models import ContaReceber

    # Extrair usuário e tenant
    current_user, tenant_id = user_and_tenant

    # Validar paginação
    if page < 1:
        raise HTTPException(status_code=400, detail="Página deve ser >= 1")
    if per_page < 1 or per_page > 100:
        raise HTTPException(status_code=400, detail="per_page deve estar entre 1 e 100")

    # Verificar se cliente existe e pertence ao tenant
    from app.models import Cliente

    cliente = (
        db.query(Cliente)
        .filter(Cliente.id == cliente_id, Cliente.tenant_id == tenant_id)
        .first()
    )

    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    # Parse de datas
    filtro_data_inicio = None
    filtro_data_fim = None
    if data_inicio:
        try:
            filtro_data_inicio = datetime.strptime(data_inicio, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=400, detail="data_inicio inválida (use YYYY-MM-DD)"
            )

    if data_fim:
        try:
            filtro_data_fim = datetime.strptime(data_fim, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=400, detail="data_fim inválida (use YYYY-MM-DD)"
            )

    from app.financeiro.cliente_historico import consultar_movimentos_cliente

    if tipo and tipo not in {
        "venda",
        "devolucao",
        "conta_receber",
        "recebimento",
        "credito",
    }:
        raise HTTPException(status_code=400, detail="Tipo de movimento invalido")
    if filtro_data_inicio and filtro_data_fim and filtro_data_inicio > filtro_data_fim:
        raise HTTPException(
            status_code=400, detail="Data inicial deve ser anterior a data final"
        )
    historico_paginado, total_items = consultar_movimentos_cliente(
        db,
        tenant_id=tenant_id,
        cliente_id=cliente_id,
        page=page,
        per_page=per_page,
        data_inicio=filtro_data_inicio,
        data_fim=filtro_data_fim + timedelta(days=1) if filtro_data_fim else None,
        tipo=tipo,
        status=status,
    )
    total_pages = (total_items + per_page - 1) // per_page

    # ========== CALCULAR RESUMO (últimos 90 dias) ==========
    data_90_dias_atras = date.today() - timedelta(days=90)

    # Total de vendas (últimos 90 dias)
    total_vendas = (
        db.query(func.sum(Venda.total))
        .filter(
            Venda.cliente_id == cliente_id,
            Venda.tenant_id == tenant_id,
            Venda.status.notin_(["cancelada", "devolvida"]),
            Venda.data_venda >= data_90_dias_atras,
        )
        .scalar()
        or 0
    )

    # Total em aberto
    total_em_aberto = (
        db.query(
            func.sum(
                ContaReceber.valor_final - func.coalesce(ContaReceber.valor_recebido, 0)
            )
        )
        .filter(
            ContaReceber.cliente_id == cliente_id,
            ContaReceber.tenant_id == tenant_id,
            ContaReceber.status.in_(
                ("pendente", "parcial", "baixa_parcial", "vencido", "vencida")
            ),
            _divida_do_cliente(tenant_id),
        )
        .scalar()
        or 0
    )

    # Última compra
    ultima_venda = (
        db.query(Venda.data_venda, Venda.total, Venda.numero_venda)
        .filter(
            Venda.cliente_id == cliente_id,
            Venda.tenant_id == tenant_id,
            Venda.status.notin_(["cancelada", "devolvida"]),
        )
        .order_by(desc(Venda.data_venda))
        .first()
    )

    ultima_compra = None
    if ultima_venda:
        ultima_compra = {
            "data": (
                ultima_venda.data_venda.isoformat() if ultima_venda.data_venda else None
            ),
            "valor": float(ultima_venda.total) if ultima_venda.total else 0,
            "numero_venda": ultima_venda.numero_venda,
        }

    return {
        "cliente": {
            "id": cliente.id,
            "codigo": cliente.codigo,
            "nome": cliente.nome,
            "credito_atual": float(cliente.credito) if cliente.credito else 0,
        },
        "resumo": {
            "total_vendas_90d": float(total_vendas),
            "total_em_aberto": float(total_em_aberto),
            "ultima_compra": ultima_compra,
            "total_transacoes_historico": total_items,
        },
        "historico": historico_paginado,
        "paginacao": {
            "pagina_atual": page,
            "itens_por_pagina": per_page,
            "total_itens": total_items,
            "total_paginas": total_pages,
            "tem_proxima": page < total_pages,
            "tem_anterior": page > 1,
        },
    }


@router.get("/cliente/{cliente_id}/resumo")
async def get_resumo_financeiro_cliente(
    cliente_id: int,
    periodo_dias: int = 90,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = current_user_and_tenant
    """
    ## 📈 RESUMO FINANCEIRO LEVE DO CLIENTE
    
    **Rota otimizada para exibição rápida no cadastro de clientes.**
    
    ### Parâmetros:
    - **cliente_id**: ID do cliente
    - **periodo_dias**: Período para análise (padrão: 90 dias)
    
    ### Retorna apenas dados agregados:
    - Total de vendas no período
    - Total em aberto (todas as contas pendentes)
    - Última compra (data + valor)
    - Contagem de transações no histórico
    
    ### Performance:
    - ✅ Usa apenas COUNT() e SUM() - não carrega transações individuais
    - ✅ Ideal para exibir no Step 6 do wizard
    - ✅ Resposta em ~10-50ms mesmo com milhares de transações
    
    ### Diferenças da rota completa:
    - ❌ Não retorna lista de transações
    - ❌ Não tem paginação
    - ✅ Muito mais rápida
    - ✅ Baixo consumo de memória
    """
    # Importar modelos
    from app.vendas_models import Venda
    from app.financeiro_models import ContaReceber
    from app.models import Cliente

    # Verificar se cliente existe
    cliente = (
        db.query(Cliente)
        .filter(Cliente.id == cliente_id, Cliente.tenant_id == tenant_id)
        .first()
    )

    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    # Calcular data limite
    data_limite = date.today() - timedelta(days=periodo_dias)

    # ========== AGGREGATIONS (SEM CARREGAR DADOS INDIVIDUAIS) ==========

    # 1. Total de vendas no período
    total_vendas = (
        db.query(func.sum(Venda.total))
        .filter(
            Venda.cliente_id == cliente_id,
            Venda.tenant_id == tenant_id,
            Venda.status.notin_(["cancelada", "devolvida"]),
            Venda.data_venda >= data_limite,
        )
        .scalar()
        or 0
    )

    # 2. Quantidade de vendas no período
    qtd_vendas = (
        db.query(func.count(Venda.id))
        .filter(
            Venda.cliente_id == cliente_id,
            Venda.tenant_id == tenant_id,
            Venda.status.notin_(["cancelada", "devolvida"]),
            Venda.data_venda >= data_limite,
        )
        .scalar()
        or 0
    )

    # 3. Total em aberto (todas as contas pendentes, não só do período)
    total_em_aberto = (
        db.query(
            func.sum(
                ContaReceber.valor_final - func.coalesce(ContaReceber.valor_recebido, 0)
            )
        )
        .filter(
            ContaReceber.cliente_id == cliente_id,
            ContaReceber.tenant_id == tenant_id,
            ContaReceber.status.in_(
                ("pendente", "parcial", "baixa_parcial", "vencido", "vencida")
            ),
            _divida_do_cliente(tenant_id),
        )
        .scalar()
        or 0
    )

    # 4. Contas vencidas (em aberto com vencimento no passado)
    total_vencido = (
        db.query(
            func.sum(
                ContaReceber.valor_final - func.coalesce(ContaReceber.valor_recebido, 0)
            )
        )
        .filter(
            ContaReceber.cliente_id == cliente_id,
            ContaReceber.tenant_id == tenant_id,
            ContaReceber.status.in_(
                ("pendente", "parcial", "baixa_parcial", "vencido", "vencida")
            ),
            _divida_do_cliente(tenant_id),
            ContaReceber.data_vencimento < date.today(),
        )
        .scalar()
        or 0
    )

    # 5. Última compra (só buscar 1 registro)
    ultima_venda = (
        db.query(Venda.data_venda, Venda.total, Venda.numero_venda)
        .filter(
            Venda.cliente_id == cliente_id,
            Venda.tenant_id == tenant_id,
            Venda.status.notin_(["cancelada", "devolvida"]),
        )
        .order_by(desc(Venda.data_venda))
        .first()
    )

    ultima_compra = None
    if ultima_venda:
        dias_desde_ultima = (
            (date.today() - ultima_venda.data_venda.date()).days
            if ultima_venda.data_venda
            else None
        )
        ultima_compra = {
            "data": (
                ultima_venda.data_venda.isoformat() if ultima_venda.data_venda else None
            ),
            "valor": float(ultima_venda.total) if ultima_venda.total else 0,
            "numero_venda": ultima_venda.numero_venda,
            "dias_atras": dias_desde_ultima,
        }

    # 6. Ticket médio
    ticket_medio = float(total_vendas) / qtd_vendas if qtd_vendas > 0 else 0

    # 7. Contagem total de transações no histórico (para saber se tem histórico completo)
    total_transacoes = (
        db.query(func.count(Venda.id))
        .filter(Venda.cliente_id == cliente_id, Venda.tenant_id == tenant_id)
        .scalar()
        or 0
    )

    return {
        "cliente_id": cliente_id,
        "periodo_analisado": f"Últimos {periodo_dias} dias",
        "resumo": {
            "total_vendas": float(total_vendas),
            "quantidade_vendas": qtd_vendas,
            "ticket_medio": round(ticket_medio, 2),
            "total_em_aberto": float(total_em_aberto),
            "total_vencido": float(total_vencido),
            "tem_debitos": float(total_em_aberto) > 0,
            "tem_debitos_vencidos": float(total_vencido) > 0,
            "ultima_compra": ultima_compra,
            "total_transacoes_historico": total_transacoes,
            "credito_disponivel": float(cliente.credito) if cliente.credito else 0,
        },
        "alertas": [],
    }
