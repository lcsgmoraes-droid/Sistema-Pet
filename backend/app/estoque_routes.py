# ⚠️ ARQUIVO CRÍTICO DE PRODUÇÃO
# Este arquivo impacta diretamente operações reais (PDV / Financeiro / Estoque).
# NÃO alterar sem:
# 1. Entender o fluxo completo
# 2. Testar cenário real
# 3. Validar impacto financeiro

"""
ROTAS DE ESTOQUE - Sistema Pet Shop Pro
Gestão completa de estoque com sincronização Bling

Funcionalidades:
- Entrada manual de estoque
- Saída manual (perdas, avarias, ajustes)
- Transferências entre estoques
- Sincronização bidirecional com Bling
- Entrada por XML (NF-e fornecedor)
- Alertas e relatórios
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import json
import xml.etree.ElementTree as ET

from .db import get_session
from .auth import get_current_user
from .auth.dependencies import get_current_user_and_tenant
from .models import User
from .produtos_models import (
    Produto, ProdutoLote, EstoqueMovimentacao, ProdutoKitComponente
)
from .bling_estoque_sync import sincronizar_bling_background
import logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/estoque", tags=["Estoque"])

# ============================================================================
# SCHEMAS
# ============================================================================

class EntradaEstoqueRequest(BaseModel):
    """Entrada manual de estoque"""
    produto_id: int
    quantidade: float = Field(gt=0)
    custo_unitario: Optional[float] = None
    motivo: str = Field(default="compra")  # compra, devolucao, ajuste, transferencia
    documento: Optional[str] = None
    observacao: Optional[str] = None
    
    # Dados do lote (se aplicável)
    criar_lote: bool = False
    numero_lote: Optional[str] = None
    data_fabricacao: Optional[str] = None
    data_validade: Optional[str] = None
    
class SaidaEstoqueRequest(BaseModel):
    """Saída manual de estoque"""
    produto_id: int
    quantidade: float = Field(gt=0)
    motivo: str = Field(default="perda")  # perda, avaria, roubo, amostra, uso_interno, devolucao_fornecedor, ajuste
    documento: Optional[str] = None
    observacao: Optional[str] = None
    # Para KIT FÍSICO: se True, desmontou o kit e volta os componentes ao estoque
    retornar_componentes: bool = False

class TransferenciaEstoqueRequest(BaseModel):
    """Transferência entre estoques"""
    produto_id: int
    quantidade: float = Field(gt=0)
    estoque_origem: str = Field(default="fisico")  # fisico, ecommerce, consignado
    estoque_destino: str
    motivo: Optional[str] = "transferencia"
    observacao: Optional[str] = None

class MovimentacaoResponse(BaseModel):
    id: int
    produto_id: int
    produto_nome: Optional[str]
    tipo: str
    motivo: Optional[str]
    quantidade: float
    quantidade_anterior: Optional[float]
    quantidade_nova: Optional[float]
    custo_unitario: Optional[float]
    valor_total: Optional[float]
    documento: Optional[str]
    observacao: Optional[str]
    user_id: int
    user_nome: Optional[str]
    created_at: datetime
    
    model_config = {"from_attributes": True}

# ============================================================================
# ENTRADA DE ESTOQUE
# ============================================================================

@router.post("/entrada", status_code=status.HTTP_201_CREATED)
def entrada_estoque(
    entrada: EntradaEstoqueRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Entrada manual de estoque
    
    Motivos:
    - compra: Compra de fornecedor
    - devolucao: Devolução de cliente
    - ajuste: Ajuste positivo de inventário
    - transferencia: Transferência recebida
    """
    current_user, tenant_id = user_and_tenant
    logger.info(f"📥 Entrada de estoque - Produto {entrada.produto_id}, Qtd: {entrada.quantidade}")
    
    # Buscar produto
    produto = db.query(Produto).filter(Produto.id == entrada.produto_id, Produto.tenant_id == tenant_id).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    
    # ========================================
    # 🔒 TRAVA 2 — VALIDAÇÃO: PRODUTO PAI NÃO TEM ESTOQUE
    # ========================================
    if produto.is_parent:
        raise HTTPException(
            status_code=400,
            detail=f"❌ Produto '{produto.nome}' possui variações. O estoque deve ser controlado nas variações individuais (cor, tamanho, etc.), não no produto pai."
        )
    
    # ========== VALIDAÇÃO: KIT VIRTUAL não permite movimentação manual ==========
    if produto.tipo_produto == 'KIT' and produto.tipo_kit == 'VIRTUAL':
        raise HTTPException(
            status_code=400,
            detail=(
                f"❌ Não é possível movimentar estoque manualmente para KIT VIRTUAL. "
                f"O estoque deste kit ('{produto.nome}') é calculado automaticamente "
                f"com base nos componentes que o compõem. "
                f"Para aumentar o estoque, movimente os produtos componentes individualmente."
            )
        )
    
    estoque_anterior = produto.estoque_atual or 0
    
    # Controle de Lotes (OPCIONAL - só se informar número do lote)
    lote = None
    lote_id = None
    
    if entrada.numero_lote or entrada.data_validade:
        # Se informou lote OU validade, trabalhar com controle de lote
        nome_lote = entrada.numero_lote or f"{produto.sku or produto.codigo}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Buscar se já existe esse lote
        lote = db.query(ProdutoLote).filter(
            ProdutoLote.produto_id == produto.id,
            ProdutoLote.nome_lote == nome_lote
        ).first()
        
        if lote:
            # Lote existente: adicionar quantidade
            lote.quantidade_disponivel += entrada.quantidade
            logger.info(f"📦 Adicionado ao lote existente: {nome_lote} (+{entrada.quantidade})")
        else:
            # Criar novo lote
            data_val = None
            if entrada.data_validade:
                try:
                    data_val = datetime.strptime(entrada.data_validade, "%Y-%m-%d")
                except:
                    data_val = datetime.strptime(entrada.data_validade, "%d/%m/%Y")
            
            data_fab = None
            if entrada.data_fabricacao:
                try:
                    data_fab = datetime.strptime(entrada.data_fabricacao, "%Y-%m-%d")
                except:
                    data_fab = datetime.strptime(entrada.data_fabricacao, "%d/%m/%Y")
            
            lote = ProdutoLote(
                produto_id=produto.id,
                nome_lote=nome_lote,
                quantidade_inicial=entrada.quantidade,
                quantidade_disponivel=entrada.quantidade,
                quantidade_reservada=0,
                data_fabricacao=data_fab,
                data_validade=data_val,
                custo_unitario=entrada.custo_unitario or produto.preco_custo,
                ordem_entrada=int(datetime.now().timestamp()),
                status='ativo'
            )
            db.add(lote)
            db.flush()  # Para pegar o ID
            logger.info(f"📦 Lote criado: {nome_lote}")
        
        lote_id = lote.id
    
    # Atualizar estoque do produto
    produto.estoque_atual = estoque_anterior + entrada.quantidade
    
    # Buscar última entrada para comparação de preço
    ultima_entrada = db.query(EstoqueMovimentacao).filter(
        EstoqueMovimentacao.produto_id == produto.id,
        EstoqueMovimentacao.tipo == 'entrada',
        EstoqueMovimentacao.custo_unitario != None,
        EstoqueMovimentacao.id != None  # Excluir a entrada atual
    ).order_by(desc(EstoqueMovimentacao.created_at)).first()
    
    custo_anterior = ultima_entrada.custo_unitario if ultima_entrada else produto.preco_custo
    
    # Atualizar preco_custo APENAS se a entrada tiver custo definido
    if entrada.custo_unitario and entrada.custo_unitario > 0:
        produto.preco_custo = entrada.custo_unitario
        logger.info(f"💰 Preço de custo atualizado: R$ {custo_anterior or 0:.2f} → R$ {produto.preco_custo:.2f}")
    variacao_preco = None
    if custo_anterior and entrada.custo_unitario:
        if entrada.custo_unitario > custo_anterior:
            variacao_preco = 'aumento'
        elif entrada.custo_unitario < custo_anterior:
            variacao_preco = 'reducao'
        else:
            variacao_preco = 'estavel'
    
    logger.info(f"✅ Entrada registrada - Custo: R$ {entrada.custo_unitario or 0:.2f} (Anterior: R$ {custo_anterior or 0:.2f})")
    
    # Registrar movimentação
    movimentacao = EstoqueMovimentacao(
        produto_id=produto.id,
        tipo='entrada',
        motivo=entrada.motivo,
        quantidade=entrada.quantidade,
        quantidade_anterior=estoque_anterior,
        quantidade_nova=produto.estoque_atual,
        custo_unitario=entrada.custo_unitario,
        valor_total=entrada.quantidade * entrada.custo_unitario if entrada.custo_unitario else None,
        lote_id=lote_id,
        documento=entrada.documento,
        observacao=entrada.observacao,
        user_id=current_user.id, tenant_id=tenant_id
    )
    db.add(movimentacao)
    db.commit()
    db.refresh(movimentacao)
    
    logger.info(f"✅ Entrada registrada - Estoque: {estoque_anterior} → {produto.estoque_atual}")
    
    # ========== AVISE-ME: notificar clientes se estoque voltou do zero ==========
    if estoque_anterior <= 0 and produto.estoque_atual > 0:
        try:
            from app.routes.ecommerce_notify_routes import notificar_clientes_estoque_disponivel
            notificar_clientes_estoque_disponivel(db, str(tenant_id), produto.id, produto.nome)
        except Exception as e_avise:
            logger.warning(f"[AVISE-ME] Erro ao notificar clientes: {e_avise}")

    # ========== SENSIBILIZAÇÃO: KIT FÍSICO - ENTRADA diminui componentes ==========
    # LÓGICA: Entrada no kit físico significa que os unitários foram consumidos para montar os kits
    # Exemplo: Entrada de 5 kits = os componentes DIMINUEM (foram usados para montar)
    componentes_sensibilizados = []
    if produto.tipo_produto == 'KIT' and produto.tipo_kit == 'FISICO':
        from .produtos_models import ProdutoKitComponente
        
        # Buscar componentes do kit
        componentes = db.query(ProdutoKitComponente).filter(
            ProdutoKitComponente.kit_id == produto.id
        ).all()
        
        logger.info(f"🧩 KIT FÍSICO - ENTRADA: Consumindo {len(componentes)} componentes do kit '{produto.nome}' (montando {entrada.quantidade} kits)")
        
        for comp in componentes:
            componente_produto = db.query(Produto).filter(
                Produto.id == comp.produto_componente_id
            ).first()
            
            if componente_produto:
                quantidade_componente = entrada.quantidade * comp.quantidade
                estoque_ant_comp = componente_produto.estoque_atual or 0
                
                # ⚠️ IMPORTANTE: DIMINUI os componentes (foram consumidos para montar os kits)
                componente_produto.estoque_atual = estoque_ant_comp - quantidade_componente
                
                # Registrar movimentação do componente como SAÍDA (consumo)
                mov_componente = EstoqueMovimentacao(
                    produto_id=componente_produto.id,
                    tipo='saida',
                    motivo='kit_fisico_montagem',
                    quantidade=quantidade_componente,
                    quantidade_anterior=estoque_ant_comp,
                    quantidade_nova=componente_produto.estoque_atual,
                    custo_unitario=componente_produto.preco_custo,
                    valor_total=quantidade_componente * (componente_produto.preco_custo or 0),
                    observacao=f"Consumo para montagem: componente usado para montar KIT FÍSICO '{produto.nome}' (montados {entrada.quantidade} kit(s))",
                    user_id=current_user.id, tenant_id=tenant_id
                )
                db.add(mov_componente)
                
                componentes_sensibilizados.append({
                    "id": componente_produto.id,
                    "nome": componente_produto.nome,
                    "quantidade": quantidade_componente,
                    "estoque_anterior": estoque_ant_comp,
                    "estoque_novo": componente_produto.estoque_atual
                })
                
                logger.info(f"   ↳ {componente_produto.nome}: {estoque_ant_comp} → {componente_produto.estoque_atual} (-{quantidade_componente}) [consumido para montagem]")
        
        db.commit()
        logger.info(f"✅ KIT FÍSICO: {len(componentes_sensibilizados)} componentes consumidos na montagem")
    
    # Retornar dict incluindo informação de variação de preço
    response_data = {
        "id": movimentacao.id,
        "produto_id": movimentacao.produto_id,
        "produto_nome": produto.nome,
        "tipo": movimentacao.tipo,
        "motivo": movimentacao.motivo,
        "quantidade": movimentacao.quantidade,
        "custo_unitario": movimentacao.custo_unitario,
        "custo_anterior": custo_anterior,
        "variacao_preco": variacao_preco,
        "quantidade_anterior": movimentacao.quantidade_anterior,
        "quantidade_nova": movimentacao.quantidade_nova,
        "custo_unitario": movimentacao.custo_unitario,
        "valor_total": movimentacao.valor_total,
        "documento": movimentacao.documento,
        "observacao": movimentacao.observacao,
        "user_id": movimentacao.user_id,
        "user_nome": current_user.nome,
        "created_at": movimentacao.created_at,
        "componentes_sensibilizados": componentes_sensibilizados
    }
    
    # Sincronizar estoque com Bling automaticamente
    try:
        sincronizar_bling_background(produto.id, produto.estoque_atual, "entrada_estoque")
    except Exception as e_sync:
        logger.warning(f"[BLING-SYNC] Erro ao agendar sync (entrada): {e_sync}")
    
    return response_data

# ============================================================================
# SAÍDA DE ESTOQUE
# ============================================================================

@router.post("/saida", status_code=status.HTTP_201_CREATED)
def saida_estoque(
    saida: SaidaEstoqueRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Saída manual de estoque
    
    Motivos:
    - perda: Vencimento, deterioração
    - avaria: Produto danificado
    - roubo: Roubo/furto
    - amostra: Amostra grátis
    - uso_interno: Uso da loja
    - devolucao_fornecedor: Devolução ao fornecedor
    - ajuste: Ajuste negativo de inventário
    """
    current_user, tenant_id = user_and_tenant
    logger.info(f"📤 Saída de estoque - Produto {saida.produto_id}, Qtd: {saida.quantidade}")
    
    # Buscar produto
    produto = db.query(Produto).filter(Produto.id == saida.produto_id, Produto.tenant_id == tenant_id).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    
    # ========================================
    # 🔒 TRAVA 2 — VALIDAÇÃO: PRODUTO PAI NÃO TEM ESTOQUE
    # ========================================
    if produto.is_parent:
        raise HTTPException(
            status_code=400,
            detail=f"❌ Produto '{produto.nome}' possui variações. O estoque deve ser controlado nas variações individuais (cor, tamanho, etc.), não no produto pai."
        )
    
    # ========== VALIDAÇÃO: KIT VIRTUAL não permite movimentação manual ==========
    if produto.tipo_produto == 'KIT' and produto.tipo_kit == 'VIRTUAL':
        raise HTTPException(
            status_code=400,
            detail=(
                f"❌ Não é possível movimentar estoque manualmente para KIT VIRTUAL. "
                f"O estoque deste kit ('{produto.nome}') é calculado automaticamente "
                f"com base nos componentes que o compõem. "
                f"Para reduzir o estoque, movimente os produtos componentes individualmente."
            )
        )
    
    estoque_anterior = produto.estoque_atual or 0
    
    # Validar estoque disponível
    if estoque_anterior < saida.quantidade:
        raise HTTPException(
            status_code=400,
            detail=f"Estoque insuficiente. Disponível: {estoque_anterior}, Solicitado: {saida.quantidade}"
        )
    
    # Sistema FIFO: consumir lotes mais antigos (se existirem lotes ativos)
    lotes_consumidos = []
    lotes_ativos = db.query(ProdutoLote).filter(
        ProdutoLote.produto_id == produto.id,
        ProdutoLote.quantidade_disponivel > 0,
        ProdutoLote.status == 'ativo'
    ).order_by(ProdutoLote.ordem_entrada).all()
    
    if lotes_ativos:
        # Se tem lotes, usar FIFO
        quantidade_restante = saida.quantidade
        
        for lote in lotes_ativos:
            if quantidade_restante <= 0:
                break
            
            saldo_anterior = lote.quantidade_disponivel  # Guardar saldo antes de consumir
            qtd_consumir = min(lote.quantidade_disponivel, quantidade_restante)
            lote.quantidade_disponivel -= qtd_consumir
            quantidade_restante -= qtd_consumir
            
            if lote.quantidade_disponivel == 0:
                lote.status = 'esgotado'
            
            lotes_consumidos.append({
                "lote_id": lote.id,
                "nome_lote": lote.nome_lote,
                "quantidade": qtd_consumir,
                "saldo_anterior": saldo_anterior  # Para mostrar (X/Y)
            })
            
            logger.info(f"📦 FIFO: Consumido lote {lote.nome_lote}: {qtd_consumir}")
        
        if quantidade_restante > 0:
            logger.warning(f"⚠️ Lotes insuficientes. Restante será deduzido do estoque geral: {quantidade_restante}")
    
    # Atualizar estoque do produto
    produto.estoque_atual = estoque_anterior - saida.quantidade
    
    # Registrar movimentação
    movimentacao = EstoqueMovimentacao(
        produto_id=produto.id,
        tipo='saida',
        motivo=saida.motivo,
        quantidade=saida.quantidade,
        quantidade_anterior=estoque_anterior,
        quantidade_nova=produto.estoque_atual,
        custo_unitario=produto.preco_custo,
        valor_total=saida.quantidade * (produto.preco_custo or 0),
        lotes_consumidos=json.dumps(lotes_consumidos) if lotes_consumidos else None,
        documento=saida.documento,
        observacao=saida.observacao,
        user_id=current_user.id, tenant_id=tenant_id
    )
    db.add(movimentacao)
    db.commit()
    db.refresh(movimentacao)
    
    logger.info(f"✅ Saída registrada - Estoque: {estoque_anterior} → {produto.estoque_atual}")
    
    # Alerta se estoque baixo
    if produto.estoque_atual <= (produto.estoque_minimo or 0):
        logger.warning(f"⚠️ Estoque abaixo do mínimo! {produto.nome}: {produto.estoque_atual}")
    
    # ========== SENSIBILIZAÇÃO: KIT FÍSICO - SAÍDA pode retornar componentes ==========
    # LÓGICA: Saída no kit físico PODE retornar os componentes ao estoque (se desmontou o kit)
    # Exemplo: 
    # - Desmontou o kit: retornar_componentes=True → componentes AUMENTAM (voltam ao estoque)
    # - Perdeu/vendeu o kit: retornar_componentes=False → componentes NÃO mexem
    componentes_sensibilizados = []
    if produto.tipo_produto == 'KIT' and produto.tipo_kit == 'FISICO':
        from .produtos_models import ProdutoKitComponente
        
        # Buscar componentes do kit
        componentes = db.query(ProdutoKitComponente).filter(
            ProdutoKitComponente.kit_id == produto.id
        ).all()
        
        if saida.retornar_componentes:
            # CASO 1: Desmontou o kit - componentes VOLTAM ao estoque
            logger.info(f"🧩 KIT FÍSICO - DESMONTAGEM: Retornando {len(componentes)} componentes ao estoque (desmontando {saida.quantidade} kits)")
            
            for comp in componentes:
                componente_produto = db.query(Produto).filter(
                    Produto.id == comp.produto_componente_id
                ).first()
                
                if componente_produto:
                    quantidade_componente = saida.quantidade * comp.quantidade
                    estoque_ant_comp = componente_produto.estoque_atual or 0
                    
                    # ⚠️ IMPORTANTE: AUMENTA os componentes (voltam ao estoque após desmontagem)
                    componente_produto.estoque_atual = estoque_ant_comp + quantidade_componente
                    
                    # Registrar movimentação do componente como ENTRADA (devolução)
                    mov_componente = EstoqueMovimentacao(
                        produto_id=componente_produto.id,
                        tipo='entrada',
                        motivo='kit_fisico_desmontagem',
                        quantidade=quantidade_componente,
                        quantidade_anterior=estoque_ant_comp,
                        quantidade_nova=componente_produto.estoque_atual,
                        custo_unitario=componente_produto.preco_custo,
                        valor_total=quantidade_componente * (componente_produto.preco_custo or 0),
                        observacao=f"Desmontagem: componente retornado ao estoque após desmontar KIT FÍSICO '{produto.nome}' (desmontados {saida.quantidade} kit(s))",
                        user_id=current_user.id, tenant_id=tenant_id
                    )
                    db.add(mov_componente)
                    
                    componentes_sensibilizados.append({
                        "id": componente_produto.id,
                        "nome": componente_produto.nome,
                        "quantidade": quantidade_componente,
                        "estoque_anterior": estoque_ant_comp,
                        "estoque_novo": componente_produto.estoque_atual,
                        "acao": "retornado"
                    })
                    
                    logger.info(f"   ↳ {componente_produto.nome}: {estoque_ant_comp} → {componente_produto.estoque_atual} (+{quantidade_componente}) [retornado ao estoque]")
            
            db.commit()
            logger.info(f"✅ KIT FÍSICO: {len(componentes_sensibilizados)} componentes retornados ao estoque")
        else:
            # CASO 2: NÃO desmontou - componentes NÃO mexem (perda, roubo, venda, etc)
            logger.info(f"🧩 KIT FÍSICO - SAÍDA SEM DESMONTAGEM: Componentes NÃO serão retornados ao estoque (perda/roubo/etc de {saida.quantidade} kits)")
            # Não faz nada com os componentes
    
    # Retornar dict
    response_data = {
        "id": movimentacao.id,
        "produto_id": movimentacao.produto_id,
        "produto_nome": produto.nome,
        "tipo": movimentacao.tipo,
        "motivo": movimentacao.motivo,
        "quantidade": movimentacao.quantidade,
        "quantidade_anterior": movimentacao.quantidade_anterior,
        "quantidade_nova": movimentacao.quantidade_nova,
        "custo_unitario": movimentacao.custo_unitario,
        "valor_total": movimentacao.valor_total,
        "documento": movimentacao.documento,
        "observacao": movimentacao.observacao,
        "user_id": movimentacao.user_id,
        "user_nome": current_user.nome,
        "created_at": movimentacao.created_at,
        "componentes_sensibilizados": componentes_sensibilizados if componentes_sensibilizados else None
    }
    
    # Sincronizar estoque com Bling automaticamente
    try:
        sincronizar_bling_background(produto.id, produto.estoque_atual, "saida_estoque")
    except Exception as e_sync:
        logger.warning(f"[BLING-SYNC] Erro ao agendar sync (saida): {e_sync}")
    
    return response_data

# ============================================================================
# TRANSFERÊNCIA ENTRE ESTOQUES
# ============================================================================

@router.post("/transferencia", status_code=status.HTTP_201_CREATED)
def transferencia_estoque(
    transf: TransferenciaEstoqueRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Transferência entre estoques
    
    Tipos de estoque:
    - fisico: Estoque físico da loja
    - ecommerce: Estoque online (marketplace)
    - consignado: Produtos em consignação
    """
    current_user, tenant_id = user_and_tenant
    logger.info(f"🔄 Transferência - Produto {transf.produto_id}: {transf.estoque_origem} → {transf.estoque_destino}")
    
    if transf.estoque_origem == transf.estoque_destino:
        raise HTTPException(status_code=400, detail="Origem e destino não podem ser iguais")
    
    # Buscar produto
    produto = db.query(Produto).filter(Produto.id == transf.produto_id, Produto.tenant_id == tenant_id).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    
    estoque_anterior = produto.estoque_atual or 0
    
    # Validar estoque origem
    # TODO: Implementar controle de estoques separados por tipo
    # Por enquanto, valida apenas o estoque_atual total
    if estoque_anterior < transf.quantidade:
        raise HTTPException(
            status_code=400,
            detail=f"Estoque insuficiente em '{transf.estoque_origem}'"
        )
    
    # Gerar código de transferência
    codigo_transf = f"TRF-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Movimentação de SAÍDA (origem)
    mov_saida = EstoqueMovimentacao(
        produto_id=produto.id,
        tipo='transferencia',
        motivo='transferencia_enviada',
        quantidade=transf.quantidade,
        quantidade_anterior=estoque_anterior,
        quantidade_nova=estoque_anterior,  # Não altera total ainda
        estoque_origem=transf.estoque_origem,
        estoque_destino=transf.estoque_destino,
        documento=codigo_transf,
        observacao=transf.observacao,
        user_id=current_user.id, tenant_id=tenant_id
    )
    db.add(mov_saida)
    
    # Movimentação de ENTRADA (destino)
    mov_entrada = EstoqueMovimentacao(
        produto_id=produto.id,
        tipo='transferencia',
        motivo='transferencia_recebida',
        quantidade=transf.quantidade,
        quantidade_anterior=estoque_anterior,
        quantidade_nova=estoque_anterior,  # Não altera total
        estoque_origem=transf.estoque_origem,
        estoque_destino=transf.estoque_destino,
        documento=codigo_transf,
        observacao=transf.observacao,
        user_id=current_user.id, tenant_id=tenant_id
    )
    db.add(mov_entrada)
    
    db.commit()
    
    logger.info(f"✅ Transferência registrada: {codigo_transf}")
    
    return {
        "message": "Transferência registrada com sucesso",
        "codigo": codigo_transf,
        "movimentacoes": [mov_saida.id, mov_entrada.id]
    }

# ============================================================================
# ALERTAS DE ESTOQUE
# ============================================================================

@router.get("/alertas")
def alertas_estoque(
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Alertas de estoque
    
    Retorna:
    - Produtos zerados
    - Produtos abaixo do mínimo
    - Lotes vencendo em 30 dias
    - Lotes vencidos
    """
    current_user, tenant_id = user_and_tenant
    logger.info("⚠️ Consultando alertas de estoque")
    
    hoje = datetime.now().date()
    daqui_30_dias = hoje + timedelta(days=30)
    
    # Produtos zerados
    zerados = db.query(Produto).filter(
        or_(
            Produto.estoque_atual == 0,
            Produto.estoque_atual == None
        ),
        Produto.tipo == 'produto',
        Produto.status == 'ativo',
        Produto.tenant_id == tenant_id
    ).all()
    
    # Produtos abaixo do mínimo
    abaixo_minimo = db.query(Produto).filter(
        Produto.estoque_atual <= Produto.estoque_minimo,
        Produto.estoque_atual > 0,
        Produto.estoque_minimo > 0,
        Produto.tipo == 'produto',
        Produto.status == 'ativo',
        Produto.tenant_id == tenant_id
    ).all()
    
    # Lotes vencendo
    lotes_vencendo = db.query(ProdutoLote).join(Produto).filter(
        ProdutoLote.data_validade.between(hoje, daqui_30_dias),
        ProdutoLote.quantidade > 0,
        ProdutoLote.status == 'disponivel',
        Produto.status == 'ativo',
        Produto.tenant_id == tenant_id
    ).options(joinedload(ProdutoLote.produto)).all()
    
    # Lotes vencidos
    lotes_vencidos = db.query(ProdutoLote).join(Produto).filter(
        ProdutoLote.data_validade < hoje,
        ProdutoLote.quantidade > 0,
        Produto.status == 'ativo',
        Produto.tenant_id == tenant_id
    ).options(joinedload(ProdutoLote.produto)).all()
    
    return {
        "zerados": {
            "total": len(zerados),
            "produtos": [{
                "id": p.id,
                "sku": p.sku,
                "nome": p.nome,
                "categoria": p.categoria.nome if p.categoria else None
            } for p in zerados[:20]]  # Limitar a 20
        },
        "abaixo_minimo": {
            "total": len(abaixo_minimo),
            "produtos": [{
                "id": p.id,
                "sku": p.sku,
                "nome": p.nome,
                "estoque_atual": p.estoque_atual,
                "estoque_minimo": p.estoque_minimo,
                "diferenca": p.estoque_minimo - p.estoque_atual
            } for p in abaixo_minimo[:20]]
        },
        "lotes_vencendo": {
            "total": len(lotes_vencendo),
            "lotes": [{
                "id": l.id,
                "produto_id": l.produto_id,
                "produto_nome": l.produto.nome,
                "numero_lote": l.numero_lote,
                "quantidade": l.quantidade,
                "data_validade": l.data_validade.isoformat(),
                "dias_restantes": (l.data_validade - hoje).days
            } for l in lotes_vencendo[:20]]
        },
        "lotes_vencidos": {
            "total": len(lotes_vencidos),
            "lotes": [{
                "id": l.id,
                "produto_id": l.produto_id,
                "produto_nome": l.produto.nome,
                "numero_lote": l.numero_lote,
                "quantidade": l.quantidade,
                "data_validade": l.data_validade.isoformat(),
                "dias_vencido": (hoje - l.data_validade).days
            } for l in lotes_vencidos[:20]]
        }
    }

# ============================================================================
# EXCLUSÃO E EDIÇÃO DE MOVIMENTAÇÕES
# ============================================================================

@router.delete("/movimentacoes/{movimentacao_id}")
def excluir_movimentacao(
    movimentacao_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Exclui uma movimentação de estoque e reverte o efeito no produto
    """
    current_user, tenant_id = user_and_tenant
    try:
        # Buscar movimentação
        movimentacao = db.query(EstoqueMovimentacao).filter(
            EstoqueMovimentacao.id == movimentacao_id,
            EstoqueMovimentacao.tenant_id == tenant_id
        ).first()
        
        if not movimentacao:
            raise HTTPException(status_code=404, detail="Movimentação não encontrada")
        
        # Buscar produto
        produto = db.query(Produto).filter(Produto.id == movimentacao.produto_id, Produto.tenant_id == tenant_id).first()
        if not produto:
            raise HTTPException(status_code=404, detail="Produto não encontrado")
        
        logger.info(f"🗑️ Excluindo movimentação {movimentacao_id} - Tipo: {movimentacao.tipo}, Qtd: {movimentacao.quantidade}")
        
        # ========== ESTORNO DE COMPONENTES PARA KIT FÍSICO ==========
        componentes_estornados = []
        if produto.tipo_produto == 'KIT' and produto.tipo_kit == 'FISICO':
            componentes_kit = db.query(ProdutoKitComponente).filter(
                ProdutoKitComponente.kit_id == produto.id
            ).all()
            
            if componentes_kit:
                logger.info(f"📦 KIT FÍSICO detectado - Estornando componentes...")
                
                for comp in componentes_kit:
                    componente_produto = db.query(Produto).filter(Produto.id == comp.produto_componente_id, Produto.tenant_id == tenant_id).first()
                    if componente_produto:
                        quantidade_componente = comp.quantidade * movimentacao.quantidade
                        estoque_ant_comp = componente_produto.estoque_atual
                        
                        # LÓGICA DE ESTORNO:
                        # - Se foi ENTRADA de kit: os componentes foram CONSUMIDOS (-) 
                        #   → Ao excluir, devemos DEVOLVER (+) os componentes
                        # - Se foi SAÍDA de kit com retorno: os componentes foram DEVOLVIDOS (+)
                        #   → Ao excluir, devemos REMOVER (-) os componentes novamente
                        
                        if movimentacao.tipo == 'entrada':
                            # Estornando entrada de kit: devolver componentes consumidos
                            componente_produto.estoque_atual += quantidade_componente
                            logger.info(f"   ↳ {componente_produto.nome}: {estoque_ant_comp} → {componente_produto.estoque_atual} (+{quantidade_componente}) [devolvido]")
                            componentes_estornados.append({
                                "nome": componente_produto.nome,
                                "quantidade": quantidade_componente,
                                "estoque_anterior": estoque_ant_comp,
                                "estoque_novo": componente_produto.estoque_atual,
                                "acao": "devolvido"
                            })
                        elif movimentacao.tipo == 'saida' and movimentacao.observacao and 'componentes retornados' in movimentacao.observacao.lower():
                            # Estornando saída com retorno: remover componentes que foram devolvidos
                            componente_produto.estoque_atual -= quantidade_componente
                            logger.info(f"   ↳ {componente_produto.nome}: {estoque_ant_comp} → {componente_produto.estoque_atual} (-{quantidade_componente}) [estornando retorno]")
                            componentes_estornados.append({
                                "nome": componente_produto.nome,
                                "quantidade": quantidade_componente,
                                "estoque_anterior": estoque_ant_comp,
                                "estoque_novo": componente_produto.estoque_atual,
                                "acao": "estornado"
                            })
                
                logger.info(f"✅ KIT FÍSICO: {len(componentes_estornados)} componentes estornados")
        
        # Reverter estoque do kit/produto principal
        estoque_anterior = produto.estoque_atual
        if movimentacao.tipo == 'entrada':
            produto.estoque_atual -= movimentacao.quantidade
            logger.info(f"📉 Estoque {produto.nome}: {estoque_anterior} → {produto.estoque_atual} (-{movimentacao.quantidade})")
        elif movimentacao.tipo == 'saida':
            produto.estoque_atual += movimentacao.quantidade
            logger.info(f"📈 Estoque {produto.nome}: {estoque_anterior} → {produto.estoque_atual} (+{movimentacao.quantidade})")
        
        # Se tinha lote, reverter também
        if movimentacao.lote_id:
            lote = db.query(ProdutoLote).filter(ProdutoLote.id == movimentacao.lote_id).first()
            if lote:
                if movimentacao.tipo == 'entrada':
                    lote.quantidade_disponivel -= movimentacao.quantidade
                    if lote.quantidade_disponivel <= 0:
                        lote.status = 'esgotado'
                elif movimentacao.tipo == 'saida':
                    lote.quantidade_disponivel += movimentacao.quantidade
                    lote.status = 'ativo'
        
        # Excluir movimentação
        db.delete(movimentacao)
        db.commit()
        
        logger.info(f"✅ Movimentação {movimentacao_id} excluída por {current_user.nome}")
        
        # Sincronizar estoque com Bling automaticamente
        try:
            sincronizar_bling_background(produto.id, produto.estoque_atual, "exclusao_movimentacao")
        except Exception as e_sync:
            logger.warning(f"[BLING-SYNC] Erro ao agendar sync (exclusao_mov): {e_sync}")
        
        return {
            "message": "Movimentação excluída com sucesso",
            "componentes_estornados": componentes_estornados
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao excluir movimentação: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class UpdateMovimentacaoRequest(BaseModel):
    quantidade: Optional[float] = None
    custo_unitario: Optional[float] = None
    observacao: Optional[str] = None


@router.patch("/movimentacoes/{movimentacao_id}")
def editar_movimentacao(
    movimentacao_id: int,
    dados: UpdateMovimentacaoRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Edita uma movimentação existente
    """
    current_user, tenant_id = user_and_tenant
    try:
        # Buscar movimentação
        movimentacao = db.query(EstoqueMovimentacao).filter(
            EstoqueMovimentacao.id == movimentacao_id,
            EstoqueMovimentacao.tenant_id == tenant_id
        ).first()
        
        if not movimentacao:
            raise HTTPException(status_code=404, detail="Movimentação não encontrada")
        
        # Buscar produto
        produto = db.query(Produto).filter(Produto.id == movimentacao.produto_id, Produto.tenant_id == tenant_id).first()
        if not produto:
            raise HTTPException(status_code=404, detail="Produto não encontrado")
        
        # Se mudou a quantidade, ajustar estoque
        if dados.quantidade is not None and dados.quantidade != movimentacao.quantidade:
            diferenca = dados.quantidade - movimentacao.quantidade
            
            if movimentacao.tipo == 'entrada':
                produto.estoque_atual += diferenca
                if movimentacao.lote_id:
                    lote = db.query(ProdutoLote).filter(ProdutoLote.id == movimentacao.lote_id).first()
                    if lote:
                        lote.quantidade_disponivel += diferenca
            elif movimentacao.tipo == 'saida':
                produto.estoque_atual -= diferenca
                if movimentacao.lote_id:
                    lote = db.query(ProdutoLote).filter(ProdutoLote.id == movimentacao.lote_id).first()
                    if lote:
                        lote.quantidade_disponivel -= diferenca
            
            movimentacao.quantidade = dados.quantidade
            movimentacao.quantidade_nova = produto.estoque_atual
        
        # Atualizar outros campos
        if dados.custo_unitario is not None:
            movimentacao.custo_unitario = dados.custo_unitario
            movimentacao.valor_total = movimentacao.quantidade * dados.custo_unitario
        
        if dados.observacao is not None:
            movimentacao.observacao = dados.observacao
        
        db.commit()
        db.refresh(movimentacao)
        
        logger.info(f"✅ Movimentação {movimentacao_id} editada por {current_user.nome}")
        
        # Sincronizar estoque com Bling se quantidade foi alterada
        if dados.quantidade is not None:
            try:
                sincronizar_bling_background(produto.id, produto.estoque_atual, "edicao_movimentacao")
            except Exception as e_sync:
                logger.warning(f"[BLING-SYNC] Erro ao agendar sync (edicao_mov): {e_sync}")
        
        return {
            "id": movimentacao.id,
            "quantidade": movimentacao.quantidade,
            "custo_unitario": movimentacao.custo_unitario,
            "observacao": movimentacao.observacao,
            "estoque_atual_produto": produto.estoque_atual
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao editar movimentação: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# RELATÓRIOS
# ============================================================================

@router.get("/relatorio/valorizado")
def relatorio_estoque_valorizado(
    data_referencia: Optional[str] = None,
    categoria_id: Optional[int] = None,
    marca_id: Optional[int] = None,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Relatório de estoque valorizado
    
    Calcula valor total do estoque baseado no preço de custo
    """
    current_user, tenant_id = user_and_tenant
    logger.info("📊 Gerando relatório de estoque valorizado")
    
    # Query base
    query = db.query(
        Produto.id,
        Produto.sku,
        Produto.nome,
        Produto.estoque_atual,
        Produto.preco_custo,
        (Produto.estoque_atual * Produto.preco_custo).label('valor_total')
    ).filter(
        Produto.tipo == 'produto',
        Produto.status == 'ativo',
        Produto.estoque_atual > 0,
        Produto.tenant_id == tenant_id
    )
    
    # Filtros
    if categoria_id:
        query = query.filter(Produto.categoria_id == categoria_id)
    if marca_id:
        query = query.filter(Produto.marca_id == marca_id)
    
    produtos = query.all()
    
    # Calcular totais
    valor_total = sum(p.valor_total for p in produtos if p.valor_total)
    total_itens = sum(p.estoque_atual for p in produtos if p.estoque_atual)
    
    return {
        "resumo": {
            "valor_total": valor_total,
            "total_produtos": len(produtos),
            "total_itens": total_itens,
            "custo_medio_unitario": valor_total / total_itens if total_itens > 0 else 0
        },
        "produtos": [{
            "id": p.id,
            "sku": p.sku,
            "nome": p.nome,
            "quantidade": p.estoque_atual,
            "custo_unitario": p.preco_custo,
            "valor_total": p.valor_total
        } for p in produtos]
    }

@router.get("/movimentacoes/produto/{produto_id}")
def listar_movimentacoes_produto(
    produto_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Lista todas as movimentações de um produto específico
    """
    current_user, tenant_id = user_and_tenant
    logger.info(f"📋 Listando movimentações do produto {produto_id}")
    
    # Verificar se produto existe
    produto = db.query(Produto).filter(Produto.id == produto_id, Produto.tenant_id == tenant_id).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    
    # Buscar movimentações ordenadas por data (mais antigas primeiro para calcular variações)
    movimentacoes = db.query(EstoqueMovimentacao).filter(
        EstoqueMovimentacao.produto_id == produto_id,
        EstoqueMovimentacao.tenant_id == tenant_id
    ).order_by(EstoqueMovimentacao.created_at).all()
    
    resultado = []
    custo_anterior_entrada = None
    
    # Dicionário para rastrear consumo acumulado por lote
    consumo_por_lote = {}
    
    for mov in movimentacoes:
        # Buscar informações do lote
        lote_nome = None
        lote_info = None
        
        # Para ENTRADAS: verificar se tem lote_id
        if mov.tipo == 'entrada' and mov.lote_id:
            lote = db.query(ProdutoLote).filter(ProdutoLote.id == mov.lote_id).first()
            if lote:
                lote_nome = lote.nome_lote
                lote_info = {
                    "nome": lote_nome,
                    "total_lote": lote.quantidade_inicial,
                    "tipo": "entrada"
                }
        
        # Para SAÍDAS: verificar lotes_consumidos
        elif mov.tipo == 'saida' and mov.lotes_consumidos:
            try:
                lotes = json.loads(mov.lotes_consumidos)
                if lotes and len(lotes) > 0:
                    # Pegar o primeiro lote consumido
                    primeiro_lote = lotes[0]
                    lote_id = primeiro_lote.get('lote_id')
                    
                    if lote_id:
                        # Rastrear consumo acumulado
                        if lote_id not in consumo_por_lote:
                            consumo_por_lote[lote_id] = 0
                        consumo_por_lote[lote_id] += primeiro_lote.get('quantidade', 0)
                        
                        # Buscar dados do lote
                        lote = db.query(ProdutoLote).filter(ProdutoLote.id == lote_id).first()
                        if lote:
                            lote_info = {
                                "nome": lote.nome_lote,
                                "consumido_acumulado": consumo_por_lote[lote_id],
                                "total_lote": lote.quantidade_inicial,
                                "quantidade_movimento": primeiro_lote.get('quantidade', 0),
                                "tipo": "saida"
                            }
            except:
                pass
        
        # Calcular variação de custo para entradas
        variacao_custo = None
        if mov.tipo == 'entrada' and mov.custo_unitario:
            if custo_anterior_entrada and custo_anterior_entrada > 0:
                diferenca_valor = mov.custo_unitario - custo_anterior_entrada
                diferenca_percentual = (diferenca_valor / custo_anterior_entrada) * 100
                
                variacao_custo = {
                    "custo_anterior": custo_anterior_entrada,
                    "custo_atual": mov.custo_unitario,
                    "diferenca_valor": diferenca_valor,
                    "diferenca_percentual": diferenca_percentual,
                    "tipo": "aumento" if diferenca_valor > 0 else "reducao" if diferenca_valor < 0 else "estavel"
                }
            
            # Atualizar custo anterior apenas se for entrada com custo
            custo_anterior_entrada = mov.custo_unitario
        
        resultado.append({
            "id": mov.id,
            "tipo": mov.tipo,
            "motivo": mov.motivo,
            "quantidade": mov.quantidade,
            "quantidade_anterior": mov.quantidade_anterior,
            "quantidade_nova": mov.quantidade_nova,
            "custo_unitario": mov.custo_unitario,
            "valor_total": mov.valor_total,
            "documento": mov.documento,
            "referencia_id": mov.referencia_id,
            "referencia_tipo": mov.referencia_tipo,
            "observacao": mov.observacao,
            "lote_id": mov.lote_id,
            "lote_nome": lote_nome,
            "lote_info": lote_info,
            "variacao_custo": variacao_custo,
            "created_at": mov.created_at.isoformat() if mov.created_at else None,
            "user_id": mov.user_id
        })
    
    # Inverter para mostrar mais recentes primeiro
    resultado.reverse()
    
    return resultado

