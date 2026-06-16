"""
Módulo de Memória Conversacional para IA.

Permite que a IA mantenha contexto durante a sessão,
lembrando informações como mês/ano em análise, última simulação, etc.

📌 Características:
- Armazenamento em memória (não persiste no banco)
- Contexto por sessão
- Sem impacto contábil
- Apenas leitura/escrita de contexto
"""

from typing import Any, Dict


class MemoriaConversacionalIA:
    """
    Gerencia o contexto conversacional da IA durante uma sessão.
    
    Permite que a IA lembre informações entre perguntas e respostas,
    criando uma experiência mais natural e inteligente.
    """
    
    def __init__(self):
        """Inicializa a memória conversacional vazia."""
        self.contexto: Dict[str, Any] = {}
    
    def set(self, chave: str, valor: Any) -> None:
        """
        Armazena um valor no contexto.
        
        Args:
            chave: Identificador único do contexto
            valor: Qualquer valor a ser armazenado
            
        Exemplos:
            memoria.set("mes", 6)
            memoria.set("ano", 2026)
            memoria.set("ultima_simulacao", {"salario": 3000, "cargo": "Vendedor"})
        """
        self.contexto[chave] = valor
    
    def get(self, chave: str, default: Any = None) -> Any:
        """
        Recupera um valor do contexto.
        
        Args:
            chave: Identificador do contexto
            default: Valor padrão se a chave não existir
            
        Returns:
            Valor armazenado ou valor padrão
            
        Exemplos:
            mes = memoria.get("mes")
            simulacao = memoria.get("ultima_simulacao", {})
        """
        return self.contexto.get(chave, default)
    
    def limpar(self) -> None:
        """
        Limpa todo o contexto armazenado.
        
        Útil para iniciar uma nova conversa ou resetar o estado.
        """
        self.contexto = {}
    
    def tem(self, chave: str) -> bool:
        """
        Verifica se uma chave existe no contexto.
        
        Args:
            chave: Identificador a verificar
            
        Returns:
            True se a chave existe, False caso contrário
        """
        return chave in self.contexto
    
    def remover(self, chave: str) -> None:
        """
        Remove uma chave específica do contexto.
        
        Args:
            chave: Identificador a remover
        """
        if chave in self.contexto:
            del self.contexto[chave]
    
    def listar_chaves(self) -> list:
        """
        Retorna todas as chaves armazenadas no contexto.
        
        Returns:
            Lista de chaves
        """
        return list(self.contexto.keys())
    
    def obter_resumo(self) -> Dict[str, Any]:
        """
        Retorna um resumo do contexto atual.
        
        Returns:
            Dicionário com o contexto completo
        """
        return self.contexto.copy()
