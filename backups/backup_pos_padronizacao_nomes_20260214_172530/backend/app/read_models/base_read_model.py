"""
Base Read Model - Classe Base para Read Models
===============================================

Classe base abstrata para todos os Read Models do sistema.

Read Models são serviços de leitura que consomem eventos de domínio
e fornecem agregações/insights sem persistir dados.

Características:
- Acesso centralizado ao EventDispatcher
- Filtragem automática por tenant (user_id)
- Métodos utilitários comuns
- Interface consistente

Arquitetura:
- Cada read model herda de BaseReadModel
- Consumem eventos via EventDispatcher
- Trabalham apenas com leitura/agregação
- Retornam dados estruturados (dict/list)
- NÃO persistem dados
- NÃO modificam estado

Uso:
```python
class MeuReadModel(BaseReadModel):
    def meu_metodo(self, user_id: int) -> List[Dict]:
        eventos = self.get_eventos_por_usuario(user_id)
        # processar eventos
        return resultado
```
"""

from typing import List, Optional, Type
from app.events import EventDispatcher, DomainEvent


class BaseReadModel:
    """
    Classe base para todos os Read Models.
    
    Fornece acesso ao EventDispatcher e métodos utilitários
    para trabalhar com eventos de domínio.
    
    Read Models NÃO devem:
    - Persistir dados
    - Modificar estado
    - Executar comandos
    - Disparar novos eventos
    
    Read Models DEVEM:
    - Apenas ler eventos
    - Agregar dados
    - Retornar resultados estruturados
    - Respeitar multi-tenancy
    """
    
    def __init__(self):
        """Inicializa o read model com acesso ao EventDispatcher"""
        self.dispatcher = EventDispatcher()
    
    def get_all_eventos(self) -> List[DomainEvent]:
        """
        Retorna todos os eventos do sistema.
        
        Returns:
            Lista de todos os eventos publicados
        """
        return self.dispatcher.get_all_events()
    
    def get_eventos_por_tipo(self, event_type: Type[DomainEvent]) -> List[DomainEvent]:
        """
        Retorna eventos de um tipo específico.
        
        Args:
            event_type: Classe do evento (ex: VendaRealizadaEvent)
            
        Returns:
            Lista de eventos do tipo especificado
        """
        return self.dispatcher.get_events_by_type(event_type)
    
    def get_eventos_por_usuario(
        self, 
        user_id: Optional[int] = None,
        event_type: Optional[Type[DomainEvent]] = None
    ) -> List[DomainEvent]:
        """
        Retorna eventos de um tenant específico, opcionalmente filtrado por tipo.
        
        Args:
            user_id: ID do tenant (se None, retorna todos)
            event_type: Tipo de evento para filtrar (opcional)
            
        Returns:
            Lista de eventos do tenant
        """
        if user_id is None:
            eventos = self.get_all_eventos()
        else:
            eventos = self.dispatcher.get_events_by_user(user_id)
        
        if event_type is not None:
            eventos = [e for e in eventos if isinstance(e, event_type)]
        
        return eventos
    
    def get_eventos_por_venda(self, venda_id: int) -> List[DomainEvent]:
        """
        Retorna todos os eventos relacionados a uma venda.
        
        Args:
            venda_id: ID da venda
            
        Returns:
            Lista de eventos da venda
        """
        return self.dispatcher.get_events_by_venda(venda_id)
