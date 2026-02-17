"""
Infraestrutura de Transactions Explícitas
==========================================

Este módulo fornece utilitários para gerenciamento explícito de transactions
no sistema, garantindo commit/rollback automático.

IMPORTANTE: Esta infraestrutura é para casos específicos que necessitam
controle explícito de transaction. Na maioria dos casos, o SQLAlchemy
já gerencia transactions automaticamente.
"""

from contextlib import contextmanager
from sqlalchemy.orm import Session


@contextmanager
def transactional_session(db: Session):
    """
    Context manager para gerenciamento explícito de transactions.
    
    Garante que:
    - Se o bloco executar com sucesso → commit automático
    - Se houver exceção → rollback automático + re-raise da exceção
    
    QUANDO USAR:
    ------------
    ✅ Operações que exigem múltiplas mudanças atômicas
    ✅ Lógica complexa onde você precisa garantir atomicidade explícita
    ✅ Quando você precisa controlar o ponto exato de commit
    ✅ Operações bulk que devem ser "tudo ou nada"
    
    QUANDO NÃO USAR:
    ----------------
    ❌ Operações simples CRUD (já são atômicas por padrão)
    ❌ Dentro de outro transactional_session (evite nested transactions)
    ❌ Quando você já está usando FastAPI Depends que gerencia a sessão
    ❌ Para adicionar commits manuais dentro do bloco (deixe o context manager fazer)
    
    EXEMPLO CORRETO:
    ----------------
    ```python
    from app.db.transaction import transactional_session
    
    def transferir_saldo(db: Session, origem_id: int, destino_id: int, valor: float):
        with transactional_session(db):
            # Debita da origem
            origem = db.query(Conta).filter_by(id=origem_id).first()
            origem.saldo -= valor
            
            # Credita no destino
            destino = db.query(Conta).filter_by(id=destino_id).first()
            destino.saldo += valor
            
            # Registro de auditoria
            auditoria = LogTransferencia(
                origem_id=origem_id,
                destino_id=destino_id,
                valor=valor
            )
            db.add(auditoria)
            
            # Commit automático aqui se tudo OK
            # Rollback automático se houver erro em qualquer ponto
    ```
    
    EXEMPLO INCORRETO:
    ------------------
    ```python
    # ❌ NÃO FAÇA ISSO: commit manual dentro do context manager
    with transactional_session(db):
        conta.saldo += 100
        db.commit()  # ❌ ERRADO! O context manager já faz isso
    
    # ❌ NÃO FAÇA ISSO: nested transactions sem necessidade
    with transactional_session(db):
        with transactional_session(db):  # ❌ EVITE nested
            conta.saldo += 100
    
    # ❌ NÃO FAÇA ISSO: para operações simples que já são atômicas
    with transactional_session(db):
        conta = Conta(nome="Nova")
        db.add(conta)
        # ❌ Desnecessário para uma única operação
    ```
    
    GARANTIAS:
    ----------
    - Atomicidade: Todas as operações dentro do bloco são commitadas juntas
    - Isolamento: Mantém o nível de isolamento configurado no banco
    - Rollback automático: Qualquer exceção causa rollback de todas as mudanças
    - Re-raise: Exceções são propagadas após o rollback (não são suprimidas)
    
    Parameters
    ----------
    db : Session
        Sessão SQLAlchemy ativa
    
    Yields
    ------
    Session
        A mesma sessão, para uso no bloco with
    
    Raises
    ------
    Exception
        Qualquer exceção que ocorrer dentro do bloco será re-lançada
        após o rollback automático
    
    Notes
    -----
    Este context manager NÃO fecha a sessão. O gerenciamento do ciclo de vida
    da sessão deve ser feito pela camada de dependência (FastAPI Depends).
    """
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
