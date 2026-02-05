"""
Helper de Segurança - Validação Multi-Tenant
Sistema Pet Shop Pro

Utilitários para garantir isolamento de dados por user_id.
Evita vazamento de dados entre usuários diferentes (SaaS multi-tenant).
"""
from typing import TypeVar, Type, Optional, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status


T = TypeVar('T')


def get_by_id_user(
    db: Session,
    model: Type[T],
    entity_id: int,
    user_id: int,
    id_field: str = "id",
    user_field: str = "user_id",
    error_message: Optional[str] = None
) -> T:
    """
    Busca uma entidade por ID garantindo que pertence ao usuário.
    
    ⚠️ SEGURANÇA CRÍTICA: Sempre use esta função ao buscar por ID!
    
    Args:
        db: Sessão do banco de dados
        model: Modelo SQLAlchemy (ex: Cliente, Venda, Produto)
        entity_id: ID da entidade a buscar
        user_id: ID do usuário logado (current_user.id)
        id_field: Nome do campo ID no modelo (padrão: "id")
        user_field: Nome do campo user_id no modelo (padrão: "user_id")
        error_message: Mensagem customizada para erro 404
        
    Returns:
        Entidade encontrada
        
    Raises:
        HTTPException 404: Se não encontrado OU não pertence ao usuário
        
    Exemplo:
        >>> cliente = get_by_id_user(
        ...     db=db,
        ...     model=Cliente,
        ...     entity_id=cliente_id,
        ...     user_id=current_user.id
        ... )
    """
    if error_message is None:
        error_message = f"{model.__name__} não encontrado"
    
    entity = db.query(model).filter(
        getattr(model, id_field) == entity_id,
        getattr(model, user_field) == user_id
    ).first()
    
    if not entity:
        # ⚠️ IMPORTANTE: Sempre retorna 404, nunca 403
        # Não revela ao atacante se o ID existe para outro usuário
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_message
        )
    
    return entity


def get_by_id_user_or_none(
    db: Session,
    model: Type[T],
    entity_id: int,
    user_id: int,
    id_field: str = "id",
    user_field: str = "user_id"
) -> Optional[T]:
    """
    Versão segura que retorna None ao invés de lançar exceção.
    
    Útil quando você precisa verificar existência sem quebrar o fluxo.
    
    Returns:
        Entidade encontrada ou None
    """
    entity = db.query(model).filter(
        getattr(model, id_field) == entity_id,
        getattr(model, user_field) == user_id
    ).first()
    
    return entity


def validate_user_access(
    db: Session,
    model: Type[T],
    entity_id: int,
    user_id: int,
    id_field: str = "id",
    user_field: str = "user_id",
    error_message: Optional[str] = None
) -> bool:
    """
    Valida se o usuário tem acesso à entidade.
    
    Similar a get_by_id_user, mas retorna boolean.
    
    Returns:
        True se acesso é válido
        
    Raises:
        HTTPException 404: Se não tem acesso
    """
    entity = get_by_id_user(
        db=db,
        model=model,
        entity_id=entity_id,
        user_id=user_id,
        id_field=id_field,
        user_field=user_field,
        error_message=error_message
    )
    return entity is not None


def bulk_validate_user_access(
    db: Session,
    model: Type[T],
    entity_ids: list[int],
    user_id: int,
    id_field: str = "id",
    user_field: str = "user_id"
) -> list[int]:
    """
    Valida acesso a múltiplas entidades de uma vez.
    
    Útil para operações em lote (ex: deletar múltiplos itens).
    
    Args:
        entity_ids: Lista de IDs a validar
        
    Returns:
        Lista de IDs válidos (que pertencem ao usuário)
        
    Raises:
        HTTPException 404: Se NENHUM ID pertence ao usuário
    """
    if not entity_ids:
        return []
    
    entities = db.query(getattr(model, id_field)).filter(
        getattr(model, id_field).in_(entity_ids),
        getattr(model, user_field) == user_id
    ).all()
    
    valid_ids = [e[0] for e in entities]
    
    if not valid_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nenhum {model.__name__} válido encontrado"
        )
    
    return valid_ids


def get_related_entity(
    db: Session,
    parent_entity: Any,
    related_model: Type[T],
    related_id_field: str,
    user_id: int,
    user_field: str = "user_id",
    error_message: Optional[str] = None
) -> T:
    """
    Busca entidade relacionada garantindo isolamento.
    
    Útil quando você já tem a entidade pai validada e precisa buscar uma relacionada.
    
    Exemplo:
        >>> # Já temos venda validada
        >>> venda = get_by_id_user(db, Venda, venda_id, current_user.id)
        >>> 
        >>> # Buscar cliente da venda
        >>> cliente = get_related_entity(
        ...     db=db,
        ...     parent_entity=venda,
        ...     related_model=Cliente,
        ...     related_id_field=venda.cliente_id,
        ...     user_id=current_user.id
        ... )
    """
    if related_id_field is None:
        if error_message:
            raise HTTPException(404, error_message)
        raise HTTPException(404, f"{related_model.__name__} não vinculado")
    
    return get_by_id_user(
        db=db,
        model=related_model,
        entity_id=related_id_field,
        user_id=user_id,
        user_field=user_field,
        error_message=error_message
    )


# Funções auxiliares para casos especiais

def safe_get_conta_bancaria(db: Session, conta_id: int, user_id: int):
    """Helper específico para ContaBancaria"""
    from app.financeiro_models import ContaBancaria
    return get_by_id_user(
        db, ContaBancaria, conta_id, user_id,
        error_message="Conta bancária não encontrada"
    )


def safe_get_produto(db: Session, produto_id: int, user_id: int):
    """Helper específico para Produto"""
    from app.produtos_models import Produto
    return get_by_id_user(
        db, Produto, produto_id, user_id,
        error_message="Produto não encontrado"
    )


def safe_get_cliente(db: Session, cliente_id: int, user_id: int):
    """Helper específico para Cliente"""
    from app.models import Cliente
    return get_by_id_user(
        db, Cliente, cliente_id, user_id,
        error_message="Cliente não encontrado"
    )


def safe_get_venda(db: Session, venda_id: int, user_id: int):
    """Helper específico para Venda"""
    from app.vendas_models import Venda
    return get_by_id_user(
        db, Venda, venda_id, user_id,
        error_message="Venda não encontrada"
    )


def safe_get_caixa(db: Session, caixa_id: int, user_id: int, check_usuario_id: bool = True):
    """
    Helper específico para Caixa
    
    Args:
        check_usuario_id: Se True, valida Caixa.usuario_id (responsável pelo caixa)
                         Se False, valida apenas que pertence ao user_id geral
    """
    from app.caixa_models import Caixa
    
    if check_usuario_id:
        # Validar pelo responsável do caixa
        return get_by_id_user(
            db, Caixa, caixa_id, user_id,
            user_field="usuario_id",
            error_message="Caixa não encontrado"
        )
    else:
        # Validar pelo user_id geral (se existir no modelo)
        return get_by_id_user(
            db, Caixa, caixa_id, user_id,
            error_message="Caixa não encontrado"
        )
