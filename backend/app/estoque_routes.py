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
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
from typing import List, Optional
from datetime import datetime, timedelta, date
from pydantic import BaseModel, Field
from decimal import Decimal
import json
import io
import re
import xml.etree.ElementTree as ET
from collections import defaultdict

from .db import get_session
from .auth import get_current_user
from .auth.dependencies import get_current_user_and_tenant
from .models import User, Cliente
from .security.permissions_decorator import require_permission
from .produtos_models import (
    Produto,
    ProdutoLote,
    EstoqueMovimentacao,
)
from .financeiro_models import (
    CategoriaFinanceira,
    ContaReceber,
    ContaPagar,
    LancamentoManual,
    Recebimento,
    Pagamento,
    FormaPagamento,
)
from .dre_plano_contas_models import DRECategoria, DRESubcategoria, NaturezaDRE
from .domain.dre.lancamento_dre_sync import atualizar_dre_por_lancamento
from .pedido_integrado_models import PedidoIntegrado
from .vendas_models import Venda
from .bling_estoque_sync import sincronizar_bling_background
from .estoque.service import EstoqueService
from .estoque.granel import (
    _produto_e_granel,
)
from .estoque_movimentacoes_context import (
    _contexto_venda_pedido_integrado,
    _detalhar_reservas_ativas_produto,
    _label_canal_movimentacao,
    _observacao_exibicao_movimentacao_bling,
)
from .services.email_service import is_email_configured, send_email
import logging
logger = logging.getLogger(__name__)

try:
    import pdfplumber
except Exception:
    pdfplumber = None

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


def _parse_data_lote(valor: Optional[str]) -> Optional[datetime]:
    texto = str(valor or "").strip()
    if not texto:
        return None

    candidatos = [
        texto,
        texto.replace("Z", "+00:00"),
        texto.replace(" ", "T"),
        texto.split("T")[0],
    ]
    for candidato in candidatos:
        try:
            dt = datetime.fromisoformat(candidato)
            return dt.replace(tzinfo=None) if dt.tzinfo else dt
        except ValueError:
            continue

    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto[:10], formato)
        except ValueError:
            continue
    return None


def _registrar_lote_entrada(
    *,
    db: Session,
    produto: Produto,
    quantidade: float,
    custo_unitario: Optional[float],
    numero_lote: Optional[str],
    data_fabricacao: Optional[str],
    data_validade: Optional[str],
) -> tuple[ProdutoLote | None, int | None]:
    lote = None
    lote_id = None
    if not (numero_lote or data_validade):
        return lote, lote_id

    nome_lote = numero_lote or f"{produto.sku or produto.codigo}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    produto.controle_lote = True

    lote = db.query(ProdutoLote).filter(
        ProdutoLote.produto_id == produto.id,
        ProdutoLote.nome_lote == nome_lote,
    ).first()

    data_val = _parse_data_lote(data_validade)
    data_fab = _parse_data_lote(data_fabricacao)

    if lote:
        lote.quantidade_inicial = float(lote.quantidade_inicial or 0) + quantidade
        lote.quantidade_disponivel = float(lote.quantidade_disponivel or 0) + quantidade
        lote.quantidade_reservada = float(lote.quantidade_reservada or 0)
        lote.data_fabricacao = data_fab or lote.data_fabricacao
        lote.data_validade = data_val or lote.data_validade
        if custo_unitario and custo_unitario > 0:
            lote.custo_unitario = custo_unitario
        lote.status = "ativo"
        logger.info(f"📦 Adicionado ao lote existente: {nome_lote} (+{quantidade})")
    else:
        lote = ProdutoLote(
            produto_id=produto.id,
            nome_lote=nome_lote,
            quantidade_inicial=quantidade,
            quantidade_disponivel=quantidade,
            quantidade_reservada=0,
            data_fabricacao=data_fab,
            data_validade=data_val,
            custo_unitario=custo_unitario or produto.preco_custo,
            ordem_entrada=int(datetime.now().timestamp()),
            status="ativo",
        )
        db.add(lote)
        db.flush()
        logger.info(f"📦 Lote criado: {nome_lote}")

    lote_id = lote.id
    return lote, lote_id


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

    if _produto_e_granel(produto) and entrada.motivo not in {"conversao_granel", "balanco"}:
        raise HTTPException(
            status_code=400,
            detail=(
                "Produto granel deve receber estoque pela conversao de pacote para kg. "
                "Use a entrada de granel para baixar o produto base e abastecer os kg corretamente. "
                "Para inventario, use o motivo balanco."
            ),
        )

    estoque_anterior = produto.estoque_atual or 0

    # Controle de lotes: se informar lote ou validade, persiste no produto
    lote, lote_id = _registrar_lote_entrada(
        db=db,
        produto=produto,
        quantidade=entrada.quantidade,
        custo_unitario=entrada.custo_unitario,
        numero_lote=entrada.numero_lote,
        data_fabricacao=entrada.data_fabricacao,
        data_validade=entrada.data_validade,
    )

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

    pedido_integrado_ids = sorted(
        {
            int(mov.referencia_id)
            for mov in movimentacoes
            if mov.referencia_tipo == 'pedido_integrado' and mov.referencia_id
        }
    )
    pedidos_integrados = (
        db.query(PedidoIntegrado)
        .filter(
            PedidoIntegrado.tenant_id == tenant_id,
            PedidoIntegrado.id.in_(pedido_integrado_ids),
        )
        .all()
        if pedido_integrado_ids
        else []
    )
    pedidos_integrados_por_id = {pedido.id: pedido for pedido in pedidos_integrados}

    resultado = []
    custo_anterior_entrada = None

    # Dicionário para rastrear consumo acumulado por lote
    consumo_por_lote = {}
    saldo_estimado = 0.0

    for mov in movimentacoes:
        if mov.quantidade_nova is not None:
            saldo_apos_lancamento = float(mov.quantidade_nova)
            saldo_estimado = saldo_apos_lancamento
        else:
            quantidade_movimento = float(mov.quantidade or 0)
            if mov.status != "cancelado":
                if mov.tipo == "entrada":
                    saldo_estimado += quantidade_movimento
                elif mov.tipo == "saida":
                    saldo_estimado -= quantidade_movimento
            saldo_apos_lancamento = saldo_estimado

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

        # Buscar canal da venda quando for movimentação de venda
        canal_venda = None
        preco_venda_unitario = None
        nf_numero = None
        documento_exibicao = mov.documento
        observacao_exibicao = mov.observacao
        if mov.referencia_tipo == 'venda' and mov.referencia_id:
            venda = db.query(Venda.canal, Venda.total).filter(Venda.id == mov.referencia_id).first()
            if venda:
                canal_venda = venda.canal
                if mov.quantidade and mov.quantidade > 0:
                    preco_venda_unitario = float(venda.total) / float(mov.quantidade) if venda.total else None
        elif mov.referencia_tipo == 'pedido_integrado' and mov.referencia_id:
            pedido_integrado = pedidos_integrados_por_id.get(int(mov.referencia_id))
            if pedido_integrado:
                contexto_venda = _contexto_venda_pedido_integrado(db, pedido_integrado, produto_id)
                canal_venda = contexto_venda.get("canal")
                nf_numero = contexto_venda.get("nf_numero")
                nf_id = contexto_venda.get("nf_id")
                try:
                    from .services.bling_nf_service import movimento_documentado_por_nf
                except Exception:
                    movimento_documentado_por_nf = None

                movimento_usa_nf = bool(
                    movimento_documentado_por_nf
                    and movimento_documentado_por_nf(
                        mov,
                        nf_numero=nf_numero,
                        nf_bling_id=nf_id,
                    )
                )

                if movimento_usa_nf:
                    preco_venda_unitario = contexto_venda.get("preco_venda_unitario")
                    documento_exibicao = nf_numero or mov.documento
                    observacao_exibicao = _observacao_exibicao_movimentacao_bling(
                        canal=canal_venda,
                        nf_numero=nf_numero,
                        observacao_original=mov.observacao,
                    )
                else:
                    nf_numero = None

        resultado.append({
            "id": mov.id,
            "tipo": mov.tipo,
            "status": mov.status,
            "motivo": mov.motivo,
            "quantidade": mov.quantidade,
            "quantidade_anterior": mov.quantidade_anterior,
            "quantidade_nova": mov.quantidade_nova,
            "saldo_apos_lancamento": saldo_apos_lancamento,
            "custo_unitario": mov.custo_unitario,
            "valor_total": mov.valor_total,
            "documento": documento_exibicao,
            "documento_original": mov.documento,
            "referencia_id": mov.referencia_id,
            "referencia_tipo": mov.referencia_tipo,
            "observacao": mov.observacao,
            "observacao_exibicao": observacao_exibicao,
            "lote_id": mov.lote_id,
            "lote_nome": lote_nome,
            "lote_info": lote_info,
            "variacao_custo": variacao_custo,
            "canal": canal_venda,
            "canal_label": _label_canal_movimentacao(canal_venda),
            "nf_numero": nf_numero,
            "preco_venda_unitario": preco_venda_unitario,
            "created_at": mov.created_at.isoformat() if mov.created_at else None,
            "user_id": mov.user_id
        })

    # Inverter para mostrar mais recentes primeiro
    resultado.reverse()

    return resultado


@router.get("/produto/{produto_id}/reservas-ativas")
def listar_reservas_ativas_produto(
    produto_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = user_and_tenant
    logger.info(f"🔎 Listando reservas ativas do produto {produto_id}")

    produto = db.query(Produto).filter(
        Produto.id == produto_id,
        Produto.tenant_id == tenant_id,
    ).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    reservas = _detalhar_reservas_ativas_produto(
        db,
        tenant_id=tenant_id,
        produto_id=produto_id,
    )

    return {
        "produto_id": produto_id,
        "produto_nome": produto.nome,
        "total_pedidos": len(reservas),
        "quantidade_reservada": round(
            sum(float(item.get("quantidade_reservada") or 0) for item in reservas),
            4,
        ),
        "pedidos": reservas,
    }

