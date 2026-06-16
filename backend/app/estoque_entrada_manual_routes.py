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
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

from .db import get_session
from .auth.dependencies import get_current_user_and_tenant
from .produtos_models import (
    Produto,
    ProdutoLote,
    EstoqueMovimentacao,
)
from .bling_estoque_sync import sincronizar_bling_background
from .estoque.granel import (
    _produto_e_granel,
)
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

    codigo_produto = (
        getattr(produto, "codigo", None)
        or getattr(produto, "codigo_barras", None)
        or f"produto-{produto.id}"
    )
    nome_lote = numero_lote or f"{codigo_produto}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
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
        EstoqueMovimentacao.custo_unitario.is_not(None),
        EstoqueMovimentacao.id.is_not(None)  # Excluir a entrada atual
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
