"""
AI Context Builder

Constrói contexto rico do ERP para injetar na IA.
Busca dados relevantes baseados na mensagem do cliente.

Contexto inclui:
- Info do tenant (políticas, horários, etc)
- Info do cliente (histórico, últimos pedidos)
- Produtos (busca semântica, estoque, preços)
- Promoções ativas
- Histórico da conversa
"""
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.models import Cliente, Produto
from app.vendas_models import Venda, VendaItem
from app.whatsapp.models import TenantWhatsAppConfig, WhatsAppSession, WhatsAppMessage
from app.cache.cache_manager import cache

logger = logging.getLogger(__name__)


class ContextBuilder:
    """
    Constrói contexto do ERP para IA.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    async def build_context(
        self,
        tenant_id: str,
        session_id: str,
        message: str
    ) -> Dict[str, Any]:
        """
        Constrói contexto completo para IA.
        
        Args:
            tenant_id: ID do tenant
            session_id: ID da sessão
            message: Mensagem atual do cliente
            
        Returns:
            Dicionário com todo contexto necessário
        """
        try:
            # Buscar dados em paralelo (otimização)
            tenant_config = await self._get_tenant_config(tenant_id)
            session = await self._get_session(session_id)
            cliente = await self._get_cliente_info(tenant_id, session.cliente_id) if session.cliente_id else None
            produtos = await self._search_produtos(tenant_id, message)
            historico = await self._get_conversation_history(session_id, limit=10)
            
            context = {
                "tenant": tenant_config,
                "session": {
                    "id": session.id,
                    "status": session.status,
                    "message_count": session.message_count
                },
                "cliente": cliente,
                "produtos_relevantes": produtos,
                "historico_conversa": historico,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"✅ Contexto construído: {len(produtos)} produtos, cliente={cliente is not None}")
            
            return context
            
        except Exception as e:
            logger.error(f"Erro ao construir contexto: {e}")
            return self._get_minimal_context()
    
    # ========================================================================
    # TENANT CONFIG
    # ========================================================================
    
    @cache.cached(ttl=300, key_prefix="tenant_config")
    async def _get_tenant_config(self, tenant_id: str) -> Dict[str, Any]:
        """
        Busca configuração do tenant (com cache).
        """
        config = self.db.query(TenantWhatsAppConfig).filter(
            TenantWhatsAppConfig.tenant_id == tenant_id
        ).first()
        
        if not config:
            return {}
        
        return {
            "bot_name": config.bot_name or "Assistente",
            "tone": config.tone or "friendly",
            "greeting": config.greeting_message,
            "working_hours": {
                "start": config.working_hours_start.isoformat() if config.working_hours_start else None,
                "end": config.working_hours_end.isoformat() if config.working_hours_end else None
            },
            "auto_response_enabled": config.auto_response_enabled,
            "politicas": self._get_politicas_negocio(tenant_id)
        }
    
    def _get_politicas_negocio(self, tenant_id: str) -> Dict[str, Any]:
        """
        Políticas de negócio (hard rules).
        
        TODO: Buscar do banco de dados (tabela de configurações)
        """
        return {
            "proibido_vender": ["animais vivos", "medicamentos controlados"],
            "exige_prescricao": ["antibióticos", "vermífugos específicos"],
            "minimo_entrega": 50.00,
            "areas_entrega": ["zona sul", "centro", "jardins"],
            "formas_pagamento": ["Dinheiro", "Pix", "Cartão Débito", "Cartão Crédito"]
        }
    
    # ========================================================================
    # SESSION
    # ========================================================================
    
    async def _get_session(self, session_id: str) -> WhatsAppSession:
        """Busca sessão."""
        session = self.db.query(WhatsAppSession).get(session_id)
        if not session:
            raise ValueError(f"Sessão {session_id} não encontrada")
        return session
    
    # ========================================================================
    # CLIENTE INFO
    # ========================================================================
    
    @cache.cached(ttl=60, key_prefix="cliente_info")
    async def _get_cliente_info(self, tenant_id: str, cliente_id: str) -> Optional[Dict[str, Any]]:
        """
        Busca informações do cliente.
        """
        if not cliente_id:
            return None
        
        cliente = self.db.query(Cliente).filter(
            Cliente.id == cliente_id,
            Cliente.tenant_id == tenant_id
        ).first()
        
        if not cliente:
            return None
        
        # Buscar último pedido
        ultimo_pedido = self.db.query(Venda).filter(
            Venda.cliente_id == cliente_id,
            Venda.tenant_id == tenant_id
        ).order_by(Venda.data_venda.desc()).first()
        
        # Buscar histórico de compras (últimos 3 meses)
        tres_meses_atras = datetime.now() - timedelta(days=90)
        total_compras = self.db.query(Venda).filter(
            Venda.cliente_id == cliente_id,
            Venda.tenant_id == tenant_id,
            Venda.data_venda >= tres_meses_atras
        ).count()
        
        return {
            "id": cliente.id,
            "nome": cliente.nome,
            "email": cliente.email,
            "telefone": cliente.celular,
            "endereco": f"{cliente.endereco}, {cliente.bairro}" if cliente.endereco else None,
            "ultimo_pedido": {
                "id": ultimo_pedido.id,
                "data": ultimo_pedido.data_venda.isoformat(),
                "valor": float(ultimo_pedido.valor_total),
                "forma_pagamento": ultimo_pedido.forma_pagamento
            } if ultimo_pedido else None,
            "total_compras_3m": total_compras,
            "cliente_fiel": total_compras >= 3
        }
    
    # ========================================================================
    # PRODUTOS
    # ========================================================================
    
    async def _search_produtos(
        self,
        tenant_id: str,
        query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Busca produtos relevantes baseado na mensagem.
        
        Busca simples por LIKE (futuramente: busca vetorial/embeddings).
        """
        try:
            # Extrair palavras-chave da query
            keywords = self._extract_keywords(query)
            
            if not keywords:
                # Se não tem keywords, retornar produtos populares
                return await self._get_produtos_populares(tenant_id, limit)
            
            # Buscar produtos que contenham qualquer keyword
            produtos = self.db.query(Produto).filter(
                Produto.tenant_id == tenant_id,
                Produto.ativo == True
            )
            
            # Aplicar filtros de busca
            for keyword in keywords[:3]:  # Máx 3 keywords
                produtos = produtos.filter(
                    Produto.nome.ilike(f"%{keyword}%") |
                    Produto.descricao.ilike(f"%{keyword}%")
                )
            
            produtos = produtos.limit(limit).all()
            
            return [self._format_produto(p) for p in produtos]
            
        except Exception as e:
            logger.error(f"Erro ao buscar produtos: {e}")
            return []
    
    @cache.cached(ttl=600, key_prefix="produtos_populares")
    async def _get_produtos_populares(
        self,
        tenant_id: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retorna produtos mais vendidos (com cache).
        """
        # Buscar produtos mais vendidos (últimos 30 dias)
        from sqlalchemy import func, desc
        
        trinta_dias = datetime.now() - timedelta(days=30)
        
        produtos = self.db.query(
            Produto,
            func.count(VendaItem.id).label("vendas")
        ).join(
            VendaItem, VendaItem.produto_id == Produto.id
        ).join(
            Venda, Venda.id == VendaItem.venda_id
        ).filter(
            Produto.tenant_id == tenant_id,
            Produto.ativo == True,
            Venda.data_venda >= trinta_dias
        ).group_by(
            Produto.id
        ).order_by(
            desc("vendas")
        ).limit(limit).all()
        
        return [self._format_produto(p[0]) for p in produtos]
    
    def _format_produto(self, produto: Produto) -> Dict[str, Any]:
        """Formata produto para contexto."""
        return {
            "id": produto.id,
            "nome": produto.nome,
            "descricao": produto.descricao or "",
            "preco": float(produto.preco_venda) if produto.preco_venda else 0.0,
            "estoque": int(produto.estoque_atual) if produto.estoque_atual else 0,
            "disponivel": (produto.estoque_atual or 0) > 0,
            "categoria": produto.categoria.nome if hasattr(produto, 'categoria') and produto.categoria else None,
            "imagem_url": produto.imagem_url if hasattr(produto, 'imagem_url') else None
        }
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extrai palavras-chave relevantes da mensagem.
        
        Remove stopwords, mantém substantivos importantes.
        """
        # Stopwords comuns
        stopwords = {
            "o", "a", "os", "as", "um", "uma", "de", "do", "da", "em", "no", "na",
            "para", "por", "com", "sem", "que", "qual", "quais", "tem", "têm",
            "você", "vocês", "eu", "meu", "minha", "olá", "oi", "bom", "boa",
            "dia", "tarde", "noite", "quero", "gostaria", "preciso", "quanto",
            "custa", "preço", "valor", "vende", "vendem", "aí", "ai"
        }
        
        # Normalizar e dividir
        words = text.lower().split()
        
        # Filtrar stopwords e palavras curtas
        keywords = [
            w.strip(",.!?") for w in words
            if len(w) > 3 and w.lower() not in stopwords
        ]
        
        return keywords[:5]  # Máx 5 keywords
    
    # ========================================================================
    # HISTÓRICO CONVERSA
    # ========================================================================
    
    async def _get_conversation_history(
        self,
        session_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Busca histórico recente da conversa.
        """
        messages = self.db.query(WhatsAppMessage).filter(
            WhatsAppMessage.session_id == session_id
        ).order_by(
            WhatsAppMessage.created_at.desc()
        ).limit(limit).all()
        
        # Inverter ordem (mais antiga primeiro)
        messages = reversed(messages)
        
        return [
            {
                "tipo": msg.tipo,
                "conteudo": msg.conteudo,
                "timestamp": msg.created_at.isoformat(),
                "intent": msg.intent_detected
            }
            for msg in messages
        ]
    
    # ========================================================================
    # FALLBACK
    # ========================================================================
    
    def _get_minimal_context(self) -> Dict[str, Any]:
        """Contexto mínimo em caso de erro."""
        return {
            "tenant": {"bot_name": "Assistente", "tone": "friendly"},
            "session": {"status": "bot"},
            "cliente": None,
            "produtos_relevantes": [],
            "historico_conversa": [],
            "timestamp": datetime.utcnow().isoformat()
        }
