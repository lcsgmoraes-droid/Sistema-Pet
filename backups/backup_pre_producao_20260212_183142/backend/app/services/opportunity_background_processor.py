"""
OPPORTUNITY BACKGROUND PROCESSOR

Serviço silencioso que analisa contexto de venda e prepara oportunidades
para uso futuro, sem impacto visual ou funcional no PDV.

Comportamento:
- Recebe eventos mínimos da venda (cliente, itens)
- Executa lógica placeholder (if simples, comentários)
- Prepara oportunidades em memória por sessão
- NÃO persiste, NÃO emite eventos, NÃO retorna dados ao PDV
- Totalmente fail-safe com try/except silencioso

Estrutura preparada para:
- Regras de negócio customizáveis
- IA generativa (fase futura)
- Cache por sessão de venda
"""

from typing import Dict, List, Any, Optional, Tuple
from uuid import UUID
from datetime import datetime, timedelta
import threading
import time


class OpportunityBackgroundProcessor:
    """
    Processador passivo de oportunidades por sessão de venda.
    
    Uma instância por sessão PDV (tenant + session_id).
    Acumula contexto e prepara oportunidades sem qualquer I/O externo.
    """
    
    def __init__(self, tenant_id: UUID, session_id: str):
        """
        Inicializa processador para uma sessão de venda específica.
        
        Args:
            tenant_id: ID do tenant (isolamento multi-tenant)
            session_id: ID único da sessão de venda no PDV
        """
        self.tenant_id = tenant_id
        self.session_id = session_id
        
        # Estado da sessão (em memória, descartado ao final da venda)
        self.cliente_id: Optional[UUID] = None
        self.itens_carrinho: List[Dict[str, Any]] = []
        self.contexto_venda: Dict[str, Any] = {
            "cliente_selecionado": False,
            "itens_totais": 0,
            "categorias_presentes": set(),
            "timestamp_inicio": datetime.utcnow().isoformat(),
        }
        
        # Oportunidades preparadas (em memória, nunca persistidas)
        self._oportunidades_candidatas: List[Dict[str, Any]] = []
    
    
    # ============================================================================
    # GATILHOS INTERNOS - Chamados pelo PDV/backend sem retorno esperado
    # ============================================================================
    
    def on_client_selected(self, cliente_id: UUID) -> None:
        """
        Gatilho: Cliente selecionado na venda.
        
        Contexto: Agora sabemos quem é o cliente, podemos preparar
        oportunidades baseadas no perfil/histórico (fase futura).
        
        Args:
            cliente_id: ID do cliente selecionado
        """
        try:
            self.cliente_id = cliente_id
            self.contexto_venda["cliente_selecionado"] = True
            self.contexto_venda["cliente_id"] = str(cliente_id)
            
            # PLACEHOLDER: Lógica de análise de cliente
            # Fase futura: Buscar histórico, preferências, segmentação IA
            if cliente_id:
                self._processar_contexto_cliente()
            
        except Exception as e:
            # Fail-safe: Silenciar qualquer erro, nunca afeta PDV
            pass
    
    
    def on_item_added(
        self, 
        cliente_id: UUID, 
        itens_carrinho: List[Dict[str, Any]]
    ) -> None:
        """
        Gatilho: Item adicionado ao carrinho.
        
        Contexto: Atualizamos lista de itens, podemos sugerir complementos
        ou bundles baseado no carrinho (fase futura).
        
        Args:
            cliente_id: ID do cliente (validação)
            itens_carrinho: Lista atual de itens no carrinho
        """
        try:
            # Validar consistência
            if cliente_id != self.cliente_id:
                return  # Sessão desynchronized, ignore
            
            self.itens_carrinho = itens_carrinho or []
            
            # Atualizar contexto de venda
            self.contexto_venda["itens_totais"] = len(self.itens_carrinho)
            self.contexto_venda["timestamp_ultima_acao"] = datetime.utcnow().isoformat()
            
            # PLACEHOLDER: Análise de carrinho
            # Fase futura: Lógica de cross-sell, upsell, bundles IA
            if self.itens_carrinho:
                self._processar_carrinho_adicionado()
            
        except Exception as e:
            # Fail-safe: Silenciar qualquer erro, nunca afeta PDV
            pass
    
    
    def on_item_removed(
        self, 
        cliente_id: UUID, 
        itens_carrinho: List[Dict[str, Any]]
    ) -> None:
        """
        Gatilho: Item removido do carrinho.
        
        Contexto: Cliente removeu item, pode indicar objeção ou mudança
        de estratégia de compra (insights para IA futura).
        
        Args:
            cliente_id: ID do cliente (validação)
            itens_carrinho: Lista atual de itens no carrinho
        """
        try:
            # Validar consistência
            if cliente_id != self.cliente_id:
                return  # Sessão desynchronized, ignore
            
            # Registrar remoção (para análise futura)
            itens_removidos = len(self.itens_carrinho) - len(itens_carrinho or [])
            if itens_removidos > 0:
                self.contexto_venda["itens_removidos"] = itens_removidos
            
            self.itens_carrinho = itens_carrinho or []
            self.contexto_venda["itens_totais"] = len(self.itens_carrinho)
            self.contexto_venda["timestamp_ultima_acao"] = datetime.utcnow().isoformat()
            
            # PLACEHOLDER: Análise de abandono
            # Fase futura: Detecção de objeções, retenção IA
            self._processar_carrinho_removido()
            
        except Exception as e:
            # Fail-safe: Silenciar qualquer erro, nunca afeta PDV
            pass
    
    
    # ============================================================================
    # LÓGICA INTERNA - Processamento e preparação de oportunidades (em memória)
    # ============================================================================
    
    def _processar_contexto_cliente(self) -> None:
        """
        Processa contexto do cliente selecionado.
        Preparação placeholder para análise de perfil.
        """
        # PLACEHOLDER: Regras simples de negócio
        # Ex: if cliente.segmento == "premium": preparar_ofertas_premium()
        pass
    
    
    def _processar_carrinho_adicionado(self) -> None:
        """
        Processa adição de item ao carrinho.
        Identifica categorias, detecta padrões, prepara oportunidades.
        """
        # PLACEHOLDER: Análise de carrinho
        # 1. Extrair categorias de itens
        categorias = set()
        for item in self.itens_carrinho:
            if isinstance(item, dict) and "categoria" in item:
                categorias.add(item["categoria"])
        
        self.contexto_venda["categorias_presentes"] = list(categorias)
        
        # 2. Lógica de preparação (em memória, nunca persistida)
        # Ex: if "ração" in categorias: preparar_oportunidade_complementos()
        self._preparar_oportunidades_contextualizadas()
    
    
    def _processar_carrinho_removido(self) -> None:
        """
        Processa remoção de item do carrinho.
        Detecta padrões de abandono e objeções.
        """
        # PLACEHOLDER: Análise de abandono
        # Pode indicar objeção, falta de confiança ou mudança de estratégia
        # Fase futura: IA detecta padrão e ajusta abordagem
        pass
    
    
    def _preparar_oportunidades_contextualizadas(self) -> None:
        """
        Preparação silenciosa de oportunidades baseado no contexto.
        
        Placeholder: Prepara lista em memória sem persistência.
        Fase futura: 
            - Regras de negócio customizáveis por tenant
            - IA generativa para sugestões inteligentes
            - Cache por sessão para otimizar
        """
        try:
            # Limpar candidatas anteriores (refresh de contexto)
            self._oportunidades_candidatas = []
            
            # PLACEHOLDER: Lógica de preparação
            # Exemplo estrutura para regra futura:
            # if "pet_alimentacao" in self.contexto_venda["categorias_presentes"]:
            #     self._oportunidades_candidatas.append({
            #         "tipo": "complemento",
            #         "categoria": "acessórios",
            #         "confianca": 0.75,
            #         "motivo": "Cliente comprou ração - sugerir comedouro"
            #     })
            
            # 💾 SALVAR NO CACHE após preparação
            self._save_to_cache()
            
        except Exception:
            # Fail-safe: Limpar e continuar
            self._oportunidades_candidatas = []
    
    
    # ============================================================================
    # CACHE METHODS - Armazenamento temporário de oportunidades
    # ============================================================================
    
    def _save_to_cache(self) -> None:
        """
        Salva oportunidades preparadas no cache global.
        Cache é indexado por (tenant_id, session_id) com TTL de 5 minutos.
        """
        try:
            from .opportunity_background_processor import _cache_manager
            _cache_manager.set_opportunities(
                tenant_id=self.tenant_id,
                session_id=self.session_id,
                opportunities=self._oportunidades_candidatas.copy()
            )
        except Exception:
            pass  # Fail-safe: erro no cache não afeta processamento
    
    
    def _invalidate_cache(self) -> None:
        """
        Invalida cache de oportunidades para esta sessão.
        Chamado quando venda é finalizada/cancelada.
        """
        try:
            from .opportunity_background_processor import _cache_manager
            _cache_manager.invalidate(
                tenant_id=self.tenant_id,
                session_id=self.session_id
            )
        except Exception:
            pass  # Fail-safe
    
    
    # ============================================================================
    # MÉTODOS INTERNOS (Private) - Nunca expostos ao PDV
    # ============================================================================
    
    def get_session_context(self) -> Dict[str, Any]:
        """
        Retorna contexto da sessão (INTERNO - nunca chamado pelo PDV).
        Útil para debugging e análise interna apenas.
        """
        return {
            "tenant_id": str(self.tenant_id),
            "session_id": self.session_id,
            "cliente_id": str(self.cliente_id) if self.cliente_id else None,
            "contexto": self.contexto_venda,
            "oportunidades_preparadas": len(self._oportunidades_candidatas),
        }
    
    
    def cleanup(self) -> None:
        """
        Limpeza de sessão (chamado ao finalizar venda).
        Descarta contexto e oportunidades preparadas (garbage collection).
        Invalida cache associado.
        """
        try:
            self._invalidate_cache()  # Limpar cache primeiro
            self.cliente_id = None
            self.itens_carrinho = []
            self.contexto_venda = {}
            self._oportunidades_candidatas = []
        except Exception:
            pass


# ============================================================================
# CACHE MANAGER - Armazena oportunidades temporariamente (TTL: 5 minutos)
# ============================================================================

class OpportunityCacheManager:
    """
    Gerenciador de cache em memória para oportunidades preparadas.
    
    Estrutura:
    - Cache: Dict[(tenant_id, session_id), (oportunidades, timestamp)]
    - TTL: 5 minutos
    - Thread-safe com Lock
    - Auto-cleanup periódico
    """
    
    TTL_SECONDS = 300  # 5 minutos
    
    def __init__(self):
        self._cache: Dict[Tuple[UUID, str], Tuple[List[Dict[str, Any]], float]] = {}
        self._lock = threading.Lock()
        self._start_cleanup_thread()
    
    
    def set_opportunities(
        self,
        tenant_id: UUID,
        session_id: str,
        opportunities: List[Dict[str, Any]]
    ) -> None:
        """
        Salva oportunidades no cache com timestamp.
        
        Args:
            tenant_id: ID do tenant
            session_id: ID da sessão
            opportunities: Lista de oportunidades preparadas
        """
        try:
            with self._lock:
                key = (tenant_id, session_id)
                timestamp = time.time()
                self._cache[key] = (opportunities, timestamp)
        except Exception:
            pass  # Fail-safe: erro no cache não afeta sistema
    
    
    def get_opportunities(
        self,
        tenant_id: UUID,
        session_id: str
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Recupera oportunidades do cache (se não expirou).
        
        Args:
            tenant_id: ID do tenant
            session_id: ID da sessão
            
        Returns:
            Lista de oportunidades ou None se expirado/não encontrado
        """
        try:
            with self._lock:
                key = (tenant_id, session_id)
                if key not in self._cache:
                    return None
                
                opportunities, timestamp = self._cache[key]
                
                # Verificar se expirou
                if time.time() - timestamp > self.TTL_SECONDS:
                    del self._cache[key]  # Remover se expirado
                    return None
                
                return opportunities
        except Exception:
            return None  # Fail-safe
    
    
    def invalidate(self, tenant_id: UUID, session_id: str) -> None:
        """
        Invalida cache para uma sessão específica.
        
        Args:
            tenant_id: ID do tenant
            session_id: ID da sessão
        """
        try:
            with self._lock:
                key = (tenant_id, session_id)
                if key in self._cache:
                    del self._cache[key]
        except Exception:
            pass  # Fail-safe
    
    
    def _cleanup_expired(self) -> None:
        """
        Remove entradas expiradas do cache (limpeza periódica).
        """
        try:
            with self._lock:
                now = time.time()
                expired_keys = [
                    key for key, (_, timestamp) in self._cache.items()
                    if now - timestamp > self.TTL_SECONDS
                ]
                for key in expired_keys:
                    del self._cache[key]
        except Exception:
            pass  # Fail-safe
    
    
    def _start_cleanup_thread(self) -> None:
        """
        Inicia thread de limpeza automática (roda a cada 60 segundos).
        """
        def cleanup_loop():
            while True:
                time.sleep(60)  # Limpar a cada 1 minuto
                self._cleanup_expired()
        
        thread = threading.Thread(target=cleanup_loop, daemon=True)
        thread.start()


# ============================================================================
# SINGLETON MANAGER - Gerencia instâncias por sessão (compartilhado no backend)
# ============================================================================

class OpportunityBackgroundProcessorManager:
    """
    Gerenciador de instâncias do processador.
    Uma instância por (tenant_id, session_id) ativo.
    """
    
    def __init__(self):
        self._sessions: Dict[tuple, OpportunityBackgroundProcessor] = {}
    
    
    def get_or_create(
        self, 
        tenant_id: UUID, 
        session_id: str
    ) -> OpportunityBackgroundProcessor:
        """
        Obtém ou cria processador para sessão.
        
        Args:
            tenant_id: ID do tenant
            session_id: ID único da sessão PDV
            
        Returns:
            OpportunityBackgroundProcessor para a sessão
        """
        key = (tenant_id, session_id)
        if key not in self._sessions:
            self._sessions[key] = OpportunityBackgroundProcessor(tenant_id, session_id)
        return self._sessions[key]
    
    
    def cleanup_session(self, tenant_id: UUID, session_id: str) -> None:
        """
        Remove processador de sessão (garbage collection).
        
        Args:
            tenant_id: ID do tenant
            session_id: ID único da sessão PDV
        """
        try:
            key = (tenant_id, session_id)
            if key in self._sessions:
                self._sessions[key].cleanup()
                del self._sessions[key]
        except Exception:
            pass


# Instâncias globais (compartilhadas em todo o backend)
_cache_manager = OpportunityCacheManager()
_processor_manager = OpportunityBackgroundProcessorManager()


def get_opportunity_processor(
    tenant_id: UUID, 
    session_id: str
) -> OpportunityBackgroundProcessor:
    """
    Função helper para obter processador de oportunidades.
    
    Args:
        tenant_id: ID do tenant
        session_id: ID único da sessão PDV
        
    Returns:
        OpportunityBackgroundProcessor para a sessão
    """
    return _processor_manager.get_or_create(tenant_id, session_id)
