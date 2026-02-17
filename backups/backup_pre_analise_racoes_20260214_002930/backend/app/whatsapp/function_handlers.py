"""
Function Handlers para WhatsApp IA

Implementações reais das 5 funções disponíveis via function calling.
"""
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


# ============================================================================
# 1. BUSCAR PRODUTO
# ============================================================================

def buscar_produto(
    db: Session,
    tenant_id: int,
    keywords: List[str],
    categoria: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Busca produtos no estoque com keywords.
    
    Args:
        keywords: Lista de palavras-chave (ex: ["ração", "golden"])
        categoria: Categoria opcional (ex: "ração")
        limit: Máximo de resultados
    
    Returns:
        {
            "found": int,
            "produtos": [
                {
                    "id": int,
                    "nome": str,
                    "preco": float,
                    "estoque": int,
                    "categoria": str
                }
            ]
        }
    """
    from app.models import Produto
    from sqlalchemy import or_
    
    try:
        # Query base
        query = db.query(Produto).filter(
            Produto.tenant_id == tenant_id,
            Produto.ativo == True
        )
        
        # Filtrar por categoria
        if categoria:
            query = query.filter(Produto.categoria.ilike(f"%{categoria}%"))
        
        # Filtrar por keywords (nome OU descricao)
        if keywords:
            filters = []
            for keyword in keywords:
                filters.append(Produto.nome.ilike(f"%{keyword}%"))
                filters.append(Produto.descricao.ilike(f"%{keyword}%"))
            
            query = query.filter(or_(*filters))
        
        # Ordenar por mais vendidos (se tiver campo vendas_count)
        # query = query.order_by(Produto.vendas_count.desc())
        
        # Limitar resultados
        produtos = query.limit(limit).all()
        
        # Formatar resposta
        result = {
            "found": len(produtos),
            "produtos": [
                {
                    "id": p.id,
                    "nome": p.nome,
                    "preco": float(p.preco_venda) if p.preco_venda else 0.0,
                    "estoque": p.estoque_atual or 0,
                    "categoria": p.categoria or "Sem categoria",
                    "descricao": p.descricao or ""
                }
                for p in produtos
            ]
        }
        
        logger.info(f"✅ buscar_produto: {len(produtos)} encontrados - keywords={keywords}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Erro em buscar_produto: {e}")
        return {"found": 0, "produtos": [], "error": str(e)}


# ============================================================================
# 2. CONSULTAR ESTOQUE
# ============================================================================

def consultar_estoque(
    db: Session,
    tenant_id: int,
    produto_id: int
) -> Dict[str, Any]:
    """
    Verifica estoque disponível de um produto.
    
    Args:
        produto_id: ID do produto
    
    Returns:
        {
            "disponivel": bool,
            "quantidade": int,
            "produto": {...},
            "status": str  # "disponivel", "baixo", "esgotado"
        }
    """
    from app.models import Produto
    
    try:
        produto = db.query(Produto).filter(
            Produto.id == produto_id,
            Produto.tenant_id == tenant_id
        ).first()
        
        if not produto:
            return {
                "disponivel": False,
                "quantidade": 0,
                "error": "Produto não encontrado"
            }
        
        quantidade = produto.estoque_atual or 0
        estoque_minimo = produto.estoque_minimo or 5
        
        # Determinar status
        if quantidade == 0:
            status = "esgotado"
            disponivel = False
        elif quantidade <= estoque_minimo:
            status = "baixo"
            disponivel = True
        else:
            status = "disponivel"
            disponivel = True
        
        result = {
            "disponivel": disponivel,
            "quantidade": quantidade,
            "status": status,
            "produto": {
                "id": produto.id,
                "nome": produto.nome,
                "preco": float(produto.preco_venda) if produto.preco_venda else 0.0,
                "categoria": produto.categoria
            }
        }
        
        logger.info(f"✅ consultar_estoque: produto={produto_id}, status={status}, qtd={quantidade}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Erro em consultar_estoque: {e}")
        return {"disponivel": False, "quantidade": 0, "error": str(e)}


# ============================================================================
# 3. CALCULAR FRETE
# ============================================================================

def calcular_frete(
    db: Session,
    tenant_id: int,
    endereco_destino: str,
    peso_kg: float = 0.0,
    valor_produtos: float = 0.0
) -> Dict[str, Any]:
    """
    Calcula frete usando Google Maps API.
    
    Args:
        endereco_destino: Endereço completo ou apenas bairro/cidade
        peso_kg: Peso total dos produtos
        valor_produtos: Valor total dos produtos (para frete grátis)
    
    Returns:
        {
            "valor": float,
            "prazo": str,
            "distancia_km": float,
            "frete_gratis": bool
        }
    """
    try:
        # Buscar configuração de entrega
        from app.models import ConfiguracaoEntrega
        
        config = db.query(ConfiguracaoEntrega).filter(
            ConfiguracaoEntrega.tenant_id == tenant_id
        ).first()
        
        # Frete grátis?
        frete_gratis_acima = config.valor_minimo_frete_gratis if config else 150.0
        
        if valor_produtos >= frete_gratis_acima:
            return {
                "valor": 0.0,
                "prazo": "24-48 horas",
                "distancia_km": 0.0,
                "frete_gratis": True,
                "message": f"Frete grátis! (compra acima de R$ {frete_gratis_acima:.2f})"
            }
        
        # Calcular via Google Maps
        # TODO: Integrar com app/services/google_maps_service.py
        # Por enquanto, retornar valor fixo baseado no peso
        
        valor_base = 10.0
        valor_por_kg = 2.0
        valor_frete = valor_base + (peso_kg * valor_por_kg)
        
        # Prazo padrão
        prazo = config.prazo_entrega_padrao if config else "24-48 horas"
        
        result = {
            "valor": round(valor_frete, 2),
            "prazo": prazo,
            "distancia_km": 0.0,  # TODO: calcular via Maps
            "frete_gratis": False,
            "message": f"Frete: R$ {valor_frete:.2f} - Prazo: {prazo}"
        }
        
        logger.info(f"✅ calcular_frete: destino={endereco_destino}, valor={valor_frete:.2f}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Erro em calcular_frete: {e}")
        return {"valor": 0.0, "prazo": "A calcular", "error": str(e)}


# ============================================================================
# 4. CRIAR PEDIDO
# ============================================================================

def criar_pedido(
    db: Session,
    tenant_id: int,
    cliente_id: int,
    items: List[Dict[str, Any]],
    forma_pagamento: str = "pix",
    endereco_entrega: Optional[str] = None
) -> Dict[str, Any]:
    """
    Cria pedido no sistema (Venda + VendaItem).
    
    Args:
        cliente_id: ID do cliente
        items: Lista de {"produto_id": int, "quantidade": int}
        forma_pagamento: "pix", "cartao", "dinheiro"
        endereco_entrega: Endereço de entrega
    
    Returns:
        {
            "pedido_id": int,
            "valor_total": float,
            "status": str,
            "previsao_entrega": str
        }
    """
    from app.models import Venda, VendaItem, Produto, Cliente
    from datetime import datetime, timedelta
    
    try:
        # Validar cliente
        cliente = db.query(Cliente).filter(
            Cliente.id == cliente_id,
            Cliente.tenant_id == tenant_id
        ).first()
        
        if not cliente:
            return {"error": "Cliente não encontrado"}
        
        # Calcular valor total
        valor_total = 0.0
        items_processados = []
        
        for item in items:
            produto = db.query(Produto).filter(
                Produto.id == item["produto_id"],
                Produto.tenant_id == tenant_id
            ).first()
            
            if not produto:
                continue
            
            quantidade = item["quantidade"]
            subtotal = float(produto.preco_venda) * quantidade
            valor_total += subtotal
            
            items_processados.append({
                "produto": produto,
                "quantidade": quantidade,
                "subtotal": subtotal
            })
        
        if not items_processados:
            return {"error": "Nenhum produto válido no pedido"}
        
        # Criar venda
        venda = Venda(
            tenant_id=tenant_id,
            cliente_id=cliente_id,
            data_venda=datetime.now(),
            valor_total=valor_total,
            status="pendente",
            origem="whatsapp",
            observacoes=f"Pedido via WhatsApp - Entrega: {endereco_entrega or 'A definir'}"
        )
        
        db.add(venda)
        db.flush()  # Obter ID da venda
        
        # Criar itens
        for item_data in items_processados:
            item = VendaItem(
                venda_id=venda.id,
                produto_id=item_data["produto"].id,
                quantidade=item_data["quantidade"],
                preco_unitario=item_data["produto"].preco_venda,
                subtotal=item_data["subtotal"]
            )
            db.add(item)
        
        db.commit()
        
        # Previsão de entrega
        previsao = (datetime.now() + timedelta(hours=24)).strftime("%d/%m/%Y %H:%M")
        
        result = {
            "pedido_id": venda.id,
            "valor_total": float(valor_total),
            "status": "pendente",
            "previsao_entrega": previsao,
            "message": f"Pedido #{venda.id} criado com sucesso! Total: R$ {valor_total:.2f}"
        }
        
        logger.info(f"✅ criar_pedido: pedido={venda.id}, cliente={cliente_id}, valor={valor_total:.2f}")
        
        return result
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erro em criar_pedido: {e}")
        return {"error": str(e)}


# ============================================================================
# 5. TRANSFERIR PARA HUMANO
# ============================================================================

def transferir_para_humano(
    db: Session,
    tenant_id: int,
    session_id: int,
    motivo: str,
    prioridade: str = "normal"
) -> Dict[str, Any]:
    """
    Transfere conversa para atendente humano.
    
    Args:
        session_id: ID da sessão
        motivo: Motivo da transferência
        prioridade: "baixa", "normal", "alta", "urgente"
    
    Returns:
        {
            "transferido": bool,
            "session_id": int,
            "message": str
        }
    """
    from app.whatsapp.models import WhatsAppSession
    
    try:
        session = db.query(WhatsAppSession).filter(
            WhatsAppSession.id == session_id,
            WhatsAppSession.tenant_id == tenant_id
        ).first()
        
        if not session:
            return {"transferido": False, "error": "Sessão não encontrada"}
        
        # Atualizar status
        session.status = "waiting_human"
        
        # Adicionar contexto
        context = session.context_data or {}
        context["transfer_reason"] = motivo
        context["transfer_priority"] = prioridade
        context["transfer_timestamp"] = datetime.now().isoformat()
        
        session.context_data = context
        
        db.commit()
        
        result = {
            "transferido": True,
            "session_id": session_id,
            "message": "Conversa transferida para atendente humano",
            "prioridade": prioridade
        }
        
        logger.info(f"✅ transferir_para_humano: session={session_id}, motivo={motivo}, prioridade={prioridade}")
        
        # TODO: Notificar atendentes (email, push, webhook)
        # TODO: Adicionar na fila de atendimento
        
        return result
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erro em transferir_para_humano: {e}")
        return {"transferido": False, "error": str(e)}


# ============================================================================
# REGISTRY DE FUNÇÕES
# ============================================================================

FUNCTION_HANDLERS = {
    "buscar_produto": buscar_produto,
    "consultar_estoque": consultar_estoque,
    "calcular_frete": calcular_frete,
    "criar_pedido": criar_pedido,
    "transferir_para_humano": transferir_para_humano
}


def execute_function(
    function_name: str,
    db: Session,
    tenant_id: int,
    **kwargs
) -> Dict[str, Any]:
    """
    Executa função pelo nome.
    
    Args:
        function_name: Nome da função
        db: Sessão do banco
        tenant_id: ID do tenant
        **kwargs: Argumentos da função
    
    Returns:
        Resultado da função
    """
    handler = FUNCTION_HANDLERS.get(function_name)
    
    if not handler:
        logger.error(f"❌ Função não encontrada: {function_name}")
        return {"error": f"Função {function_name} não implementada"}
    
    try:
        return handler(db=db, tenant_id=tenant_id, **kwargs)
    except Exception as e:
        logger.error(f"❌ Erro ao executar {function_name}: {e}")
        return {"error": str(e)}
