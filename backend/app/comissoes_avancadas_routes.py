"""
SPRINT 6 - PASSO 6: Endpoints de Conferência Avançada e Pagamento Parcial

Novos endpoints:
- GET /comissoes/conferencia-avancada/{funcionario_id} - Com filtros (grupo, produto, período)
- POST /comissoes/fechar-com-pagamento - Fechar com valor_pago, forma_pagamento, saldo_restante
- GET /comissoes/formas-pagamento - Lista de formas de pagamento disponíveis

Mantém snapshot imutável: valor_comissao NUNCA é alterado
"""

from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Optional, Dict, List
from datetime import date, datetime
import logging
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import bindparam, text

from .db import SessionLocal, get_session
from .auth.dependencies import get_current_user_and_tenant
from .models import Cliente
from .financeiro_models import (
    ContaPagar, Pagamento, CategoriaFinanceira, FormaPagamento,
    MovimentacaoFinanceira, ContaBancaria
)
from .comissoes_avancadas_models import (
    ConferenciaComFiltrosResponse,
    FecharComPagamentoResponse,
    ListaFormasPagamento,
    PeriodoSelecionado,
    ResumoComFiltros,
    ComissaoItem
)
from .utils.auditoria_compensacao import (
    criar_json_auditoria_compensacao,
    formatar_observacao_simples_compensacao
)
from .utils.tenant_safe_sql import execute_tenant_safe

router = APIRouter(prefix="/comissoes", tags=["comissoes-avancadas"])

logger = logging.getLogger(__name__)

# Logger estruturado (para auditoria)
class StructuredLogger:
    def info(self, event_type: str, message: str, extra: Dict = None):
        logger.info(f"[{event_type}] {message}", extra=extra or {})

struct_logger = StructuredLogger()


# ==================== ENDPOINTS DE LEITURA ====================

@router.get("/conferencia-avancada/{funcionario_id}", 
            summary="Conferência avançada com filtros por produto e período")
def conferencia_com_filtros_avancados(
    funcionario_id: int,
    _user_and_tenant=Depends(get_current_user_and_tenant),
    grupo_produto: Optional[int] = Query(None, description="Filtro por grupo/categoria de produto"),
    produto_id: Optional[int] = Query(None, description="Filtro por produto específico"),
    data_inicio: Optional[date] = Query(None, description="Data inicial do período"),
    data_fim: Optional[date] = Query(None, description="Data final do período"),
) -> ConferenciaComFiltrosResponse:
    """
    SPRINT 6 - PASSO 6: CONFERÊNCIA COM FILTROS AVANÇADOS
    
    Retorna comissões pendentes de um funcionário com suporte a filtros avançados:
    - Por grupo/categoria de produto
    - Por produto específico
    - Por período de data
    
    Regras mantidas:
    - Snapshot imutável: valor_comissao NUNCA é recalculado
    - Status: apenas comissões pendentes
    - Sem alteração: apenas leitura
    - Transparência: todos os campos visíveis
    
    Retorna:
    - Período selecionado para auditoria
    - Resumo com totais do filtro aplicado
    - Lista completa de comissões visíveis
    """
    try:
        struct_logger.info(
            "CONFERENCE_ADVANCED_START",
            f"Conferência avançada para funcionário {funcionario_id}",
            extra={
                'funcionario_id': funcionario_id,
                'filtros_aplicados': {
                    'grupo_produto': grupo_produto,
                    'produto_id': produto_id,
                    'data_inicio': str(data_inicio) if data_inicio else None,
                    'data_fim': str(data_fim) if data_fim else None
                }
            }
        )
        
        _, tenant_id = _user_and_tenant
        db = SessionLocal()
        
        try:
            # 1. Buscar dados do funcionário
            result = execute_tenant_safe(
                db,
                "SELECT id, nome, tipo_cadastro FROM clientes WHERE id = :funcionario_id AND {tenant_filter}",
                {"funcionario_id": funcionario_id},
                tenant_id=tenant_id,
            )
            func_row = result.fetchone()
            
            if not func_row:
                raise HTTPException(
                    status_code=404,
                    detail=f"Funcionário {funcionario_id} não encontrado"
                )
            
            # 2. Construir query com filtros
            query = """
                SELECT 
                    ci.id,
                    ci.venda_id,
                    ci.data_venda,
                    ci.produto_id,
                    ci.categoria_id,
                    ci.subcategoria_id,
                    ci.quantidade,
                    ci.valor_venda,
                    ci.valor_base_calculo,
                    ci.percentual_comissao,
                    ci.valor_comissao_gerada,
                    ci.tipo_calculo,
                    ci.status,
                    ci.forma_pagamento,
                    ci.valor_pago,
                    ci.saldo_restante,
                    p.nome as nome_produto,
                    cat.nome as nome_categoria,
                    v.cliente_id
                FROM comissoes_itens ci
                LEFT JOIN produtos p ON ci.produto_id = p.id AND p.tenant_id = ci.tenant_id
                LEFT JOIN categorias cat ON ci.categoria_id = cat.id AND cat.tenant_id = ci.tenant_id
                LEFT JOIN vendas v ON ci.venda_id = v.id AND v.tenant_id = ci.tenant_id
                WHERE ci.{tenant_filter}
                  AND ci.funcionario_id = :funcionario_id
                  AND ci.status = 'pendente'
            """
            
            params = {"funcionario_id": funcionario_id}
            
            # Aplicar filtros
            if grupo_produto:
                query += " AND ci.categoria_id = :grupo_produto"
                params["grupo_produto"] = grupo_produto
            
            if produto_id:
                query += " AND ci.produto_id = :produto_id"
                params["produto_id"] = produto_id
            
            if data_inicio:
                query += " AND DATE(ci.data_venda) >= :data_inicio"
                params["data_inicio"] = str(data_inicio)
            
            if data_fim:
                query += " AND DATE(ci.data_venda) <= :data_fim"
                params["data_fim"] = str(data_fim)
            
            query += " ORDER BY ci.data_venda ASC, ci.id ASC"
            
            result = execute_tenant_safe(db, query, params, tenant_id=tenant_id)
            rows = result.fetchall()
            
            # 3. Buscar nomes dos clientes
            cliente_ids = list(set([row.cliente_id for row in rows if row.cliente_id]))
            clientes_map = {}
            
            if cliente_ids:
                stmt_clientes = text(
                    "SELECT id, nome FROM clientes WHERE id IN :ids AND {tenant_filter}"
                ).bindparams(bindparam("ids", expanding=True))
                result_clientes = execute_tenant_safe(
                    db,
                    stmt_clientes,
                    {"ids": tuple(cliente_ids)},
                    tenant_id=tenant_id,
                )
                for cliente in result_clientes.fetchall():
                    clientes_map[cliente.id] = cliente.nome
            
            # 4. Buscar nome do grupo de produto se filtrado
            grupo_nome = None
            if grupo_produto:
                result_grupo = execute_tenant_safe(
                    db,
                    "SELECT nome FROM categorias WHERE id = :id AND {tenant_filter}",
                    {"id": grupo_produto},
                    tenant_id=tenant_id,
                )
                grupo_row = result_grupo.fetchone()
                grupo_nome = grupo_row.nome if grupo_row else None
            
            # 5. Buscar nome do produto se filtrado
            produto_nome = None
            if produto_id:
                result_produto = execute_tenant_safe(
                    db,
                    "SELECT nome FROM produtos WHERE id = :id AND {tenant_filter}",
                    {"id": produto_id},
                    tenant_id=tenant_id,
                )
                prod_row = result_produto.fetchone()
                produto_nome = prod_row.nome if prod_row else None
            
            # 6. Montar lista de comissões com calculo de saldo
            comissoes = []
            valor_total = 0.0
            valor_pago_total = 0.0
            saldo_total = 0.0
            
            for row in rows:
                cliente_nome = clientes_map.get(row.cliente_id, 'Cliente não identificado') if row.cliente_id else 'Venda sem cliente'
                
                valor_comissao = float(row.valor_comissao_gerada) if row.valor_comissao_gerada else 0.0
                valor_pago = float(row.valor_pago) if row.valor_pago else 0.0
                saldo_restante = float(row.saldo_restante) if row.saldo_restante else valor_comissao - valor_pago
                
                comissao_dict = ComissaoItem(
                    id=row.id,
                    venda_id=row.venda_id,
                    data_venda=row.data_venda.isoformat() if row.data_venda else None,
                    produto_id=row.produto_id,
                    nome_produto=row.nome_produto or f'Produto #{row.produto_id}',
                    cliente_nome=cliente_nome,
                    quantidade=float(row.quantidade) if row.quantidade else 0.0,
                    valor_venda=float(row.valor_venda) if row.valor_venda else 0.0,
                    valor_base_calculo=float(row.valor_base_calculo) if row.valor_base_calculo else 0.0,
                    percentual_comissao=float(row.percentual_comissao) if row.percentual_comissao else 0.0,
                    valor_comissao=valor_comissao,
                    tipo_calculo=row.tipo_calculo,
                    status=row.status,
                    forma_pagamento=row.forma_pagamento,
                    valor_pago=valor_pago if valor_pago > 0 else None,
                    saldo_restante=saldo_restante if valor_pago > 0 else None
                )
            
                comissoes.append(comissao_dict)
                valor_total += valor_comissao
                valor_pago_total += valor_pago
                saldo_total += saldo_restante
            
            # 7. Calcular percentual pago
            percentual_pago = (valor_pago_total / valor_total * 100) if valor_total > 0 else 0.0
            
            # 8. Montar resposta
            periodo = PeriodoSelecionado(
                data_inicio=data_inicio,
                data_fim=data_fim,
                grupo_produto=grupo_produto,
                produto_id=produto_id,
                grupo_produto_nome=grupo_nome,
                produto_nome=produto_nome
            )
            
            resumo = ResumoComFiltros(
                quantidade_comissoes=len(comissoes),
                valor_total=round(valor_total, 2),
                valor_pago_total=round(valor_pago_total, 2),
                saldo_restante_total=round(saldo_total, 2),
                percentual_pago=round(percentual_pago, 2)
            )
            
            response = ConferenciaComFiltrosResponse(
                success=True,
                funcionario={
                    'id': func_row.id,
                    'nome': func_row.nome,
                    'tipo': func_row.tipo_cadastro
                },
                periodo_selecionado=periodo,
                resumo=resumo,
                comissoes=comissoes
            )
            
            struct_logger.info(
                "CONFERENCE_ADVANCED_SUCCESS",
                f"Conferência carregada: {len(comissoes)} comissões, R$ {valor_total:.2f}",
                extra={
                    'funcionario_id': funcionario_id,
                    'quantidade': len(comissoes),
                    'valor_total': valor_total,
                    'valor_pago_total': valor_pago_total,
                    'saldo_total': saldo_total
                }
            )
            
            return response
        
        finally:
            db.close()
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro na conferência avançada: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao buscar conferência: {str(e)}")


@router.get("/formas-pagamento", summary="Lista de formas de pagamento disponíveis")
def listar_formas_pagamento(
    _user_and_tenant=Depends(get_current_user_and_tenant),
) -> ListaFormasPagamento:
    """
    Lista todas as formas de pagamento disponíveis para comissões.
    
    Formas padrão:
    - Dinheiro
    - Transferência bancária
    - Cheque
    - Cartão de crédito
    - PIX
    - Não informado
    """
    db = SessionLocal()
    try:
        result = db.execute(
            text("SELECT id, nome, descricao, ativo FROM formas_pagamento_comissoes WHERE ativo = 1 ORDER BY nome")
        )
        
        formas_list = []
        for row in result.fetchall():
            formas_list.append({
                'id': row.id,
                'nome': row.nome,
                'descricao': row.descricao,
                'ativo': bool(row.ativo)
            })
        
        return ListaFormasPagamento(
            success=True,
            formas=formas_list
        )
        
    except Exception as e:
        logger.error(f"Erro ao listar formas de pagamento: {str(e)}")
        
        # 🔧 FALLBACK: Se tabela não existir, retornar formas padrão hardcoded
        formas_default = [
            {'id': 1, 'nome': 'Dinheiro', 'descricao': 'Pagamento em dinheiro', 'ativo': True},
            {'id': 2, 'nome': 'Transferência', 'descricao': 'Transferência bancária', 'ativo': True},
            {'id': 3, 'nome': 'Cheque', 'descricao': 'Pagamento em cheque', 'ativo': True},
            {'id': 4, 'nome': 'Cartão de Crédito', 'descricao': 'Pagamento via cartão de crédito', 'ativo': True},
            {'id': 5, 'nome': 'PIX', 'descricao': 'Pagamento via PIX', 'ativo': True},
            {'id': 6, 'nome': 'Não informado', 'descricao': 'Forma de pagamento não especificada', 'ativo': True}
        ]
        
        logger.warning("⚠️ Usando formas de pagamento padrão (tabela não existe). Execute: migrate_formas_pagamento_comissoes.py")
        
        return ListaFormasPagamento(
            success=True,
            formas=formas_default
        )
    finally:
        db.close()


# ==================== ENDPOINTS DE ESCRITA ====================

@router.post("/fechar-com-pagamento", summary="Fechar comissões com pagamento e compensação automática")
async def fechar_com_pagamento_parcial(
    comissoes_ids: List[int] = Query(..., description="IDs das comissões a fechar"),
    valor_pago: float = Query(..., description="Valor a ser pago"),
    forma_pagamento: str = Query("nao_informado", description="Forma de pagamento"),
    conta_bancaria_id: Optional[int] = Query(None, description="ID da conta bancária"),
    data_pagamento: date = Query(..., description="Data do pagamento"),
    observacoes: Optional[str] = Query(None, description="Observações do fechamento"),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
) -> FecharComPagamentoResponse:
    """
    SPRINT 6 - PASSO 7: FECHAR COMISSÕES COM COMPENSAÇÃO AUTOMÁTICA
    
    Funcionalidade ATUALIZADA:
    - Permite pagamento parcial de comissões
    - **NOVO:** Compensação automática de dívidas do parceiro
    - Calcula saldo_restante = valor_comissao - valor_pago
    - Snapshot imutável: valor_comissao NUNCA é alterado
    - Registro completo de forma_pagamento e observações
    - Auditoria completa via JSON em observacoes
    
    Fluxo de Compensação:
    1. Busca dívidas abertas/parcialmente compensadas (FIFO)
    2. Calcula: valor_compensado = MIN(valor_bruto, total_dividas)
    3. Calcula: valor_liquido = valor_bruto - valor_compensado
    4. Atualiza comissoes_dividas com compensação
    5. Cria conta_pagar com valor_desconto = compensacao
    6. Cria movimentacao SOMENTE se valor_liquido > 0
    
    Regras:
    - valor_pago pode ser menor que valor_total (pagamento parcial)
    - Compensação é AUTOMÁTICA e segue ordem FIFO
    - Atualiza: status, data_pagamento, forma_pagamento, valor_pago, saldo_restante
    - NÃO recalcula: valor_comissao (snapshot)
    - Operação em transação única (tudo ou nada)
    - Rastreabilidade: origem_tipo + origem_id em todas as tabelas
    
    Retorna:
    - Total de comissões processadas
    - Valores: total fechado, pago, saldo
    - **NOVO:** Valor compensado em dívidas
    - Quantidade com saldo restante
    """
    try:
        if not comissoes_ids:
            raise HTTPException(status_code=400, detail="Nenhuma comissão selecionada")
        
        if valor_pago <= 0:
            raise HTTPException(status_code=400, detail="Valor pago deve ser maior que zero")
        
        # Obter user do contexto
        current_user, tenant_id = user_and_tenant
        
        total_processadas = 0
        total_ignoradas = 0
        valor_total_comissoes = 0.0
        valor_total_pago = 0.0
        saldo_total_restante = 0.0
        comissoes_com_saldo = 0
        
        # ========================================================================
        # FASE 1: VALIDAR E CALCULAR VALOR BRUTO DAS COMISSÕES
        # ========================================================================
        funcionario_id = None
        funcionario_nome = "Funcionário"
        
        for comissao_id in comissoes_ids:
            # Buscar comissão
            result = execute_tenant_safe(
                db,
                "SELECT id, funcionario_id, valor_comissao_gerada, status FROM comissoes_itens WHERE id = :id AND {tenant_filter}",
                {"id": comissao_id},
                tenant_id=tenant_id,
            )
            
            comissao_row = result.fetchone()
            if not comissao_row:
                logger.warning(f"Comissão {comissao_id} não encontrada")
                total_ignoradas += 1
                continue
            
            # Verificar status
            if comissao_row.status != 'pendente':
                logger.warning(f"Comissão {comissao_id} não está pendente (status: {comissao_row.status})")
                total_ignoradas += 1
                continue
            
            # Capturar funcionario_id da primeira comissão válida
            if funcionario_id is None:
                funcionario_id = comissao_row.funcionario_id
            
            # Somar valor bruto
            valor_comissao = float(comissao_row.valor_comissao_gerada) if comissao_row.valor_comissao_gerada else 0.0
            valor_total_comissoes += valor_comissao
        
        if total_processadas == 0 and valor_total_comissoes == 0:
            db.rollback()
            raise HTTPException(status_code=400, detail="Nenhuma comissão válida para processar")
        
        # Buscar nome do funcionário
        if funcionario_id:
            funcionario = db.query(Cliente).filter(Cliente.id == funcionario_id).first()
            if funcionario:
                funcionario_nome = funcionario.nome
        
        # ========================================================================
        # FASE 2: BUSCAR DÍVIDAS ABERTAS DO PARCEIRO (COMPENSAÇÃO AUTOMÁTICA)
        # ========================================================================
        result_dividas = db.execute(text("""
            SELECT id, tipo, valor_divida, motivo, venda_id, data_criacao
            FROM comissoes_dividas
            WHERE funcionario_id = :funcionario_id
              AND status IN ('aberta', 'parcialmente_compensada')
            ORDER BY data_criacao ASC, id ASC
        """), {"funcionario_id": funcionario_id})
        
        dividas_abertas = result_dividas.fetchall()
        total_dividas = sum(float(d.valor_divida) for d in dividas_abertas)
        
        # Calcular compensação
        valor_compensado = min(valor_total_comissoes, total_dividas)
        valor_liquido = valor_total_comissoes - valor_compensado
        
        logger.info(f"""
        💰 COMPENSAÇÃO AUTOMÁTICA:
           Funcionário: {funcionario_nome} (ID: {funcionario_id})
           Valor bruto comissão: R$ {valor_total_comissoes:.2f}
           Total dívidas: R$ {total_dividas:.2f}
           Valor compensado: R$ {valor_compensado:.2f}
           Valor líquido a pagar: R$ {valor_liquido:.2f}
        """)
        
        # ========================================================================
        # FASE 3: APLICAR COMPENSAÇÃO NAS DÍVIDAS (FIFO)
        # ========================================================================
        dividas_compensadas_lista = []
        valor_restante_compensar = valor_compensado
        
        for divida in dividas_abertas:
            if valor_restante_compensar <= 0:
                break
            
            divida_id = divida.id
            valor_divida = float(divida.valor_divida)
            
            # Quanto será compensado nesta dívida
            valor_compensar_nesta = min(valor_restante_compensar, valor_divida)
            saldo_devedor = valor_divida - valor_compensar_nesta
            
            # Determinar novo status
            if saldo_devedor == 0:
                novo_status = 'compensada'
            else:
                novo_status = 'parcialmente_compensada'
            
            # Criar JSON de auditoria para a dívida
            import json
            auditoria_divida = {
                "tipo": "compensacao_automatica",
                "data_compensacao": datetime.now().isoformat(),
                "valor_compensado": valor_compensar_nesta,
                "saldo_devedor": saldo_devedor,
                "comissoes_ids": comissoes_ids
            }
            
            # Atualizar dívida
            db.execute(text("""
                UPDATE comissoes_dividas
                SET status = :status,
                    observacoes = :observacoes,
                    origem_tipo = 'comissao_fechamento',
                    origem_id = :origem_id
                WHERE id = :id
            """), {
                "status": novo_status,
                "observacoes": json.dumps(auditoria_divida, ensure_ascii=False),
                "origem_id": comissoes_ids[0] if comissoes_ids else None,
                "id": divida_id
            })
            
            # Adicionar à lista para auditoria
            dividas_compensadas_lista.append({
                "divida_id": divida_id,
                "valor_original": valor_divida,
                "valor_compensado": valor_compensar_nesta,
                "saldo_restante": saldo_devedor,
                "tipo": divida.tipo,
                "venda_id": divida.venda_id
            })
            
            valor_restante_compensar -= valor_compensar_nesta
            
            logger.info(f"   ✓ Dívida #{divida_id}: R$ {valor_compensar_nesta:.2f} compensados (saldo: R$ {saldo_devedor:.2f})")
        
        # ========================================================================
        # FASE 4: ATUALIZAR COMISSÕES_ITENS
        # ========================================================================
        total_processadas = 0
        
        for comissao_id in comissoes_ids:
            result_comissao = execute_tenant_safe(
                db,
                "SELECT id, valor_comissao_gerada, status FROM comissoes_itens WHERE id = :id AND {tenant_filter}",
                {"id": comissao_id},
                tenant_id=tenant_id,
            )
            
            comissao_row = result_comissao.fetchone()
            if not comissao_row or comissao_row.status != 'pendente':
                continue
            
            valor_comissao = float(comissao_row.valor_comissao_gerada) if comissao_row.valor_comissao_gerada else 0.0
            
            # Determinar status baseado em compensação
            if valor_liquido == 0:
                status_comissao = 'compensado_integralmente'
            elif valor_compensado > 0:
                status_comissao = 'pago_com_compensacao'
            else:
                status_comissao = 'pago'
            
            # Observação explicativa
            if valor_compensado > 0:
                obs_pagamento = formatar_observacao_simples_compensacao(
                    valor_compensado,
                    [d['divida_id'] for d in dividas_compensadas_lista]
                )
            else:
                obs_pagamento = observacoes
            
            # Atualizar comissão
            execute_tenant_safe(db, """
                UPDATE comissoes_itens 
                SET status = :status,
                    data_pagamento = :data_pagamento,
                    forma_pagamento = :forma_pagamento,
                    valor_pago = :valor_pago,
                    saldo_restante = 0,
                    percentual_pago = 100,
                    observacao_pagamento = :observacao,
                    data_atualizacao = CURRENT_TIMESTAMP
                WHERE id = :id
                  AND {tenant_filter}
            """, {
                "status": status_comissao,
                "data_pagamento": str(data_pagamento),
                "forma_pagamento": forma_pagamento,
                "valor_pago": valor_liquido,
                "observacao": obs_pagamento,
                "id": comissao_id
            }, tenant_id=tenant_id)
            
            total_processadas += 1
            valor_total_pago += valor_liquido
        
        # ========================================================================
        # FASE 5: CRIAR CONTA A PAGAR (COM DESCONTO = COMPENSAÇÃO)
        # ========================================================================
        
        # Buscar categoria de comissão
        categoria_comissao = db.query(CategoriaFinanceira).filter(
            CategoriaFinanceira.nome.ilike('%comis%')
        ).first()
        
        if not categoria_comissao:
            # Criar categoria se não existir
            categoria_comissao = CategoriaFinanceira(
                nome="Comissões",
                tipo="despesa",
                descricao="Comissões de vendas",
                user_id=current_user.id
            )
            db.add(categoria_comissao)
            db.flush()
        
        # Buscar forma de pagamento
        forma_pag_obj = db.query(FormaPagamento).filter(
            FormaPagamento.nome.ilike(f"%{forma_pagamento}%")
        ).first()
        
        # Criar JSON de auditoria completo
        observacoes_json = criar_json_auditoria_compensacao(
            fechamento_id=comissoes_ids[0] if comissoes_ids else 0,
            funcionario_id=funcionario_id,
            funcionario_nome=funcionario_nome,
            valor_bruto_comissao=valor_total_comissoes,
            valor_compensado=valor_compensado,
            valor_liquido_pago=valor_liquido,
            dividas_compensadas=dividas_compensadas_lista,
            usuario_id=current_user.id
        )
        
        # Criar conta a pagar
        periodo = f"{data_pagamento.strftime('%m/%Y')}"
        descricao_conta = f"Comissão - {funcionario_nome} - {periodo}"
        if valor_compensado > 0:
            descricao_conta += " (c/ compensação)"
        
        conta_pagar = ContaPagar(
            descricao=descricao_conta,
            fornecedor_id=funcionario_id,
            categoria_id=categoria_comissao.id,
            valor_original=Decimal(str(valor_total_comissoes)),  # Valor bruto
            valor_desconto=Decimal(str(valor_compensado)),  # Compensação
            valor_final=Decimal(str(valor_liquido)),  # Líquido
            valor_pago=Decimal(str(valor_liquido)),
            data_emissao=data_pagamento,
            data_vencimento=data_pagamento,
            data_pagamento=data_pagamento,
            status='pago',
            origem_tipo='comissao_fechamento',
            origem_id=comissoes_ids[0] if comissoes_ids else None,
            observacoes=observacoes_json,
            user_id=current_user.id
        )
        db.add(conta_pagar)
        db.flush()  # Para obter o ID
        
        if valor_liquido == 0:
            logger.info(f"✓ Conta a pagar #{conta_pagar.id} criada: R$ {valor_total_comissoes:.2f} - COMPENSAÇÃO INTEGRAL (sem movimentação bancária)")
        else:
            logger.info(f"✓ Conta a pagar #{conta_pagar.id} criada: R$ {valor_total_comissoes:.2f} (líquido: R$ {valor_liquido:.2f})")
        
        # ========================================================================
        # FASE 6: CRIAR PAGAMENTO
        # ========================================================================
        
        # Observação explicativa baseada no tipo de compensação
        if valor_liquido == 0:
            obs_pagamento = f"Pago integralmente por compensação automática (sem movimentação bancária). Compensado: R$ {valor_compensado:.2f}. {observacoes or ''}"
        elif valor_compensado > 0:
            obs_pagamento = f"Pago parcialmente com compensação de R$ {valor_compensado:.2f}. Valor líquido pago: R$ {valor_liquido:.2f}. {observacoes or ''}"
        else:
            obs_pagamento = f"Pago integralmente sem compensação. {observacoes or ''}"
        
        novo_pagamento = Pagamento(
            conta_pagar_id=conta_pagar.id,
            forma_pagamento_id=forma_pag_obj.id if forma_pag_obj else None,
            valor_pago=valor_liquido,
            data_pagamento=data_pagamento,
            observacoes=obs_pagamento,
            user_id=current_user.id
        )
        db.add(novo_pagamento)
        
        # ========================================================================
        # FASE 7: CRIAR MOVIMENTAÇÃO FINANCEIRA (SOMENTE SE VALOR_LIQUIDO > 0)
        # ========================================================================
        if valor_liquido > 0 and conta_bancaria_id:
            # Buscar conta bancária
            conta_bancaria = db.query(ContaBancaria).filter(
                ContaBancaria.id == conta_bancaria_id
            ).first()
            
            if not conta_bancaria:
                raise HTTPException(
                    status_code=404,
                    detail=f"Conta bancária {conta_bancaria_id} não encontrada"
                )
            
            if not conta_bancaria.ativa:
                raise HTTPException(
                    status_code=400,
                    detail=f"Conta bancária '{conta_bancaria.nome}' está inativa"
                )
            
            # Converter valor para centavos
            valor_centavos = int(valor_liquido * 100)
            
            # Criar movimentação financeira (SAÍDA)
            movimentacao = MovimentacaoFinanceira(
                conta_bancaria_id=conta_bancaria.id,
                tipo='saida',
                valor=valor_centavos,
                descricao=f"Pgto comissão {funcionario_nome} (bruto: R$ {valor_total_comissoes:.2f} - comp: R$ {valor_compensado:.2f})",
                data_movimento=data_pagamento,
                categoria_id=categoria_comissao.id,
                status='realizado',
                forma_pagamento_id=forma_pag_obj.id if forma_pag_obj else None,
                origem_tipo='conta_pagar',
                origem_id=conta_pagar.id,
                observacoes=f"Compensação: R$ {valor_compensado:.2f}",
                user_id=current_user.id
            )
            db.add(movimentacao)
            
            # Atualizar saldo da conta bancária (DÉBITO)
            conta_bancaria.saldo_atual -= valor_centavos
            
            logger.info(
                f"🏦 Movimentação bancária criada: {conta_bancaria.nome} "
                f"-R$ {valor_liquido:.2f} (Saldo: R$ {conta_bancaria.saldo_atual/100:.2f})"
            )
        elif valor_liquido == 0:
            logger.info("ℹ️  Nenhuma movimentação bancária criada (compensação integral)")
        
        # ========================================================================
        # FASE 8: COMMIT FINAL
        # ========================================================================
        db.commit()
        
        # Montar mensagem
        if valor_compensado > 0:
            mensagem = f"{total_processadas} comissões fechadas. Compensado: R$ {valor_compensado:.2f}. Pago: R$ {valor_liquido:.2f}"
        else:
            mensagem = f"{total_processadas} comissões fechadas com sucesso"
        
        struct_logger.info(
            "COMMISSION_CLOSE_WITH_COMPENSATION",
            mensagem,
            extra={
                'total_processadas': total_processadas,
                'total_ignoradas': total_ignoradas,
                'valor_bruto': valor_total_comissoes,
                'valor_compensado': valor_compensado,
                'valor_liquido_pago': valor_liquido,
                'dividas_compensadas': len(dividas_compensadas_lista),
                'forma_pagamento': forma_pagamento,
                'data_pagamento': str(data_pagamento)
            }
        )
        
        return FecharComPagamentoResponse(
            success=True,
            total_processadas=total_processadas,
            total_ignoradas=total_ignoradas,
            valor_total_fechado=round(valor_total_comissoes, 2),
            valor_total_pago=round(valor_liquido, 2),
            saldo_total_restante=round(saldo_total_restante, 2),
            comissoes_com_saldo=comissoes_com_saldo,
            forma_pagamento=forma_pagamento,
            data_pagamento=str(data_pagamento),
            observacoes=observacoes,
            mensagem=mensagem
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao fechar comissões com pagamento: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao fechar comissões: {str(e)}")
