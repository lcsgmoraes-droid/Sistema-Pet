"""
Serviço de Acerto Financeiro de Entregas
ETAPA 7 - Versão Final com Matriz Corrigida
"""
from decimal import Decimal
from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, Column, Integer, String, Numeric, Date, Text, ForeignKey
from app.models import Cliente
from app.rotas_entrega_models import RotaEntrega
from typing import Optional, Dict
from sqlalchemy.ext.declarative import declarative_base

# Model simplificado de ContasPagar (enquanto não tem o model completo)
Base = declarative_base()

class ContasPagar(Base):
    __tablename__ = "contas_pagar"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    fornecedor_id = Column(Integer, ForeignKey("clientes.id"))
    valor = Column(Numeric(10, 2))
    descricao = Column(Text)
    data_emissao = Column(Date)
    data_vencimento = Column(Date)
    status = Column(String(20))
    tipo_documento = Column(String(50))
    observacoes = Column(Text)


def acerto_vence_hoje(entregador: Cliente, hoje: date) -> bool:
    """
    Verifica se o acerto do entregador vence hoje.
    
    Regras:
    - Semanal: verifica dia da semana (1=segunda, 7=domingo)
    - Quinzenal: dias 1 e 15 de cada mês
    - Mensal: dia configurado (1-28)
    """
    if not entregador.tipo_acerto_entrega:
        return False
    
    # Verifica se já foi processado hoje
    if entregador.data_ultimo_acerto == hoje:
        return False
    
    if entregador.tipo_acerto_entrega == "semanal":
        # 1=segunda, 7=domingo (isoweekday: 1=seg, 7=dom)
        dia_semana_hoje = hoje.isoweekday()
        return dia_semana_hoje == entregador.dia_semana_acerto
    
    elif entregador.tipo_acerto_entrega == "quinzenal":
        # Dias 1 e 15
        return hoje.day in (1, 15)
    
    elif entregador.tipo_acerto_entrega == "mensal":
        # Dia configurado (1-28)
        return hoje.day == entregador.dia_mes_acerto
    
    return False


def gerar_conta_pagar(
    db: Session,
    tenant_id: int,
    credor_id: int,
    valor: Decimal,
    descricao: str,
    tipo: str = "CUSTO_ENTREGA",
    vencimento: Optional[date] = None
) -> ContasPagar:
    """
    Cria uma conta a pagar no financeiro.
    
    Args:
        db: Sessão do banco
        tenant_id: ID do tenant
        credor_id: ID do credor (entregador)
        valor: Valor da conta
        descricao: Descrição detalhada
        tipo: Tipo da conta (CUSTO_ENTREGA ou REPASSE_ENTREGA)
        vencimento: Data de vencimento (default: hoje + 7 dias)
    """
    if vencimento is None:
        vencimento = date.today() + timedelta(days=7)
    
    conta = ContasPagar(
        tenant_id=tenant_id,
        fornecedor_id=credor_id,
        valor=valor,
        descricao=descricao,
        data_emissao=date.today(),
        data_vencimento=vencimento,
        status="pendente",
        tipo_documento="ACERTO_ENTREGA",
        observacoes=f"Tipo: {tipo}"
    )
    
    db.add(conta)
    db.flush()
    
    return conta


def executar_acerto_entregador(db: Session, entregador: Cliente) -> Optional[Dict]:
    """
    Executa acerto financeiro de um entregador.
    
    MATRIZ FINAL IMPLEMENTADA:
    - Funcionário + controla_rh=true  → ❌ Nunca gera CP
    - Funcionário + controla_rh=false + gera_cp_custo=true → ✅ Gera CP
    - Funcionário + controla_rh=false + gera_cp_custo=false → ❌ Não gera CP
    - Fornecedor (terceirizado)       → ✅ Sempre gera CP
    
    Returns:
        Dict com resumo do acerto ou None se não houver processamento
    """
    hoje = date.today()

    # 1️⃣ Verifica se vence hoje
    if not acerto_vence_hoje(entregador, hoje):
        return None

    # 2️⃣ Busca rotas concluídas desde último acerto
    query = db.query(RotaEntrega).filter(
        and_(
            RotaEntrega.entregador_id == entregador.id,
            RotaEntrega.tenant_id == entregador.tenant_id,
            RotaEntrega.status == "concluida"
        )
    )

    if entregador.data_ultimo_acerto:
        query = query.filter(RotaEntrega.data_conclusao > entregador.data_ultimo_acerto)

    rotas = query.all()

    if not rotas:
        # Atualiza data mesmo sem rotas (evita reprocessar)
        entregador.data_ultimo_acerto = hoje
        db.commit()
        return None

    # 3️⃣ Apuração
    total_custo_operacional = Decimal("0")
    total_repasse_taxa = Decimal("0")

    for rota in rotas:
        total_custo_operacional += rota.custo_real or Decimal("0")
        # ETAPA 7.1: Agora ativo! PDV → Rota → Acerto
        total_repasse_taxa += rota.valor_repasse_entregador or Decimal("0")

    # 4️⃣ Contas a pagar — CUSTO OPERACIONAL
    gerar_cp_custo = False

    # ✅ CORREÇÃO: Usar tipo_cadastro (não tipo_vinculo_entrega)
    if entregador.tipo_cadastro == "fornecedor":
        # Fornecedor = Terceirizado no nosso sistema
        gerar_cp_custo = True

    elif entregador.tipo_cadastro == "funcionario":
        # ✅ MATRIZ FINAL implementada
        if not entregador.controla_rh and entregador.gera_conta_pagar_custo_entrega:
            gerar_cp_custo = True

    # Gera CP de custo operacional se aplicável
    if gerar_cp_custo and total_custo_operacional > 0:
        gerar_conta_pagar(
            db=db,
            tenant_id=entregador.tenant_id,
            credor_id=entregador.id,
            valor=total_custo_operacional,
            descricao=f"Acerto de entregas - Custo operacional - Período até {hoje.strftime('%d/%m/%Y')}",
            tipo="CUSTO_ENTREGA"
        )

    # 5️⃣ Contas a pagar — REPASSE DA TAXA DO CLIENTE
    if total_repasse_taxa > 0:
        gerar_conta_pagar(
            db=db,
            tenant_id=entregador.tenant_id,
            credor_id=entregador.id,
            valor=total_repasse_taxa,
            descricao=f"Acerto de entregas - Repasse taxa cliente - Período até {hoje.strftime('%d/%m/%Y')}",
            tipo="REPASSE_ENTREGA"
        )

    # 6️⃣ Atualiza controle
    entregador.data_ultimo_acerto = hoje
    db.commit()

    # 7️⃣ Retorno (relatório)
    return {
        "entregador_id": entregador.id,
        "entregador": entregador.nome,
        "tipo_cadastro": entregador.tipo_cadastro,
        "controla_rh": entregador.controla_rh,
        "gera_cp_custo": gerar_cp_custo,
        "rotas_processadas": len(rotas),
        "custo_operacional": float(total_custo_operacional),
        "repasse_taxa": float(total_repasse_taxa),
        "total_contas_pagar": float(
            (total_custo_operacional if gerar_cp_custo else Decimal("0"))
            + total_repasse_taxa
        ),
        "data_acerto": hoje.isoformat(),
    }


def processar_acertos_do_dia(db: Session, tenant_id: int) -> list[Dict]:
    """
    Processa todos os acertos que vencem hoje para um tenant.
    
    Executado pelo job diário.
    Não duplica processamento (verifica data_ultimo_acerto).
    """
    hoje = date.today()
    
    # Busca entregadores ativos com acerto configurado
    entregadores = db.query(Cliente).filter(
        and_(
            Cliente.tenant_id == tenant_id,
            Cliente.is_entregador == True,
            Cliente.entregador_ativo == True,
            Cliente.tipo_acerto_entrega.isnot(None)
        )
    ).all()
    
    resultados = []
    
    for entregador in entregadores:
        resultado = executar_acerto_entregador(db, entregador)
        if resultado:
            resultados.append(resultado)
    
    return resultados
