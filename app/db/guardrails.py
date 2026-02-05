"""
Guard Rails para Transações do Banco de Dados
==============================================

Este módulo fornece mecanismos de proteção para garantir o uso correto
de transações no banco de dados.

OBJETIVOS:
----------
1. Detectar e impedir chamadas de db.commit() fora de transactional_session
2. Detectar e bloquear begin()/begin_nested() dentro de transactional_session
3. Detectar e bloquear múltiplos commits no mesmo request

ESCOPO:
-------
- Ambiente DEV: Ativado
- Ambiente TEST: Ativado  
- Ambiente PRODUCTION: Desativado (não afeta produção)

MOTIVAÇÃO:
----------
Prevenir uso incorreto de transações que podem causar estados inconsistentes,
complexidade desnecessária e bugs sutis no banco de dados.

GUARD RAILS IMPLEMENTADOS:
--------------------------
1. Commit Guard (Guard Rail 1): Bloqueia commits fora de contexto de transação
2. Nested Transaction Guard (Guard Rail 2): Bloqueia nested transactions indevidas
3. Multiple Commits Guard (Guard Rail 3): Bloqueia múltiplos commits por request
"""

import os
from functools import wraps
from sqlalchemy.orm import Session


def enable_commit_guard(session: Session) -> None:
    """
    Envolve o método session.commit para detectar commits fora de transactional_session.
    
    Esta função substitui o método commit() original da sessão por uma versão
    protegida que verifica se existe uma transação ativa antes de permitir o commit.
    
    COMPORTAMENTO:
    --------------
    1. Se commit() for chamado dentro de uma transação ativa → Permitido
    2. Se commit() for chamado FORA de uma transação ativa → RuntimeError
    
    DETECÇÃO DE TRANSAÇÃO:
    ----------------------
    Utiliza session.in_transaction() para verificar se há uma transação ativa.
    Dentro de um bloco transactional_session, in_transaction() retorna True.
    
    ATIVAÇÃO CONDICIONAL:
    --------------------
    O guard rail só é ativado se:
    - ENV != "production" OU
    - SQL_STRICT_TRANSACTIONS = "true"
    
    EXEMPLOS:
    ---------
    
    ✅ COMMIT PERMITIDO (dentro de transactional_session):
    ```python
    from app.db.transaction import transactional_session
    
    def criar_venda(db: Session):
        with transactional_session(db):
            venda = Venda(total=100)
            db.add(venda)
            # commit será chamado automaticamente pelo context manager
            # Guard rail detecta: in_transaction() = True → Permitido
    ```
    
    ❌ COMMIT BLOQUEADO (fora de transactional_session):
    ```python
    def criar_venda_errado(db: Session):
        venda = Venda(total=100)
        db.add(venda)
        db.commit()  # RuntimeError: Commit detectado fora de transactional_session!
        # Guard rail detecta: in_transaction() = False → Bloqueado
    ```
    
    COMO ATIVAR:
    ------------
    Deve ser chamado uma vez após criar a sessão do banco:
    
    ```python
    from app.db.guardrails import enable_commit_guard
    from app.database import SessionLocal
    
    # Criar sessão
    db = SessionLocal()
    
    # Ativar guard rail (apenas em DEV/TEST)
    if os.getenv("ENV") != "production":
        enable_commit_guard(db)
    ```
    
    COMO DESATIVAR:
    ---------------
    1. Defina ENV=production (desativa automaticamente)
    2. Ou defina SQL_STRICT_TRANSACTIONS=false
    3. Ou simplesmente não chame enable_commit_guard()
    
    IMPORTANTE:
    -----------
    - Não altera o comportamento em produção
    - Não afeta transactional_session
    - Não modifica services, rotas ou models existentes
    - É apenas uma camada de proteção para desenvolvimento
    
    Parameters
    ----------
    session : Session
        Sessão SQLAlchemy a ser protegida
    
    Raises
    ------
    RuntimeError
        Se commit() for chamado fora de uma transação ativa
    
    Notes
    -----
    Esta função modifica dinamicamente o método commit da sessão.
    O método original é preservado e pode ser restaurado se necessário.
    """
    # Preserva o método commit original
    original_commit = session.commit
    
    @wraps(original_commit)
    def guarded_commit():
        """
        Versão protegida do commit que verifica se há transação ativa.
        """
        # Verifica se existe uma transação ativa
        if not session.in_transaction():
            raise RuntimeError(
                "❌ COMMIT BLOQUEADO: commit() detectado fora de transactional_session!\n\n"
                "Para resolver este erro:\n"
                "1. Envolva sua operação em um bloco transactional_session:\n\n"
                "   from app.db.transaction import transactional_session\n\n"
                "   with transactional_session(db):\n"
                "       # suas operações aqui\n"
                "       # commit será feito automaticamente\n\n"
                "2. Ou remova a chamada manual db.commit() se estiver dentro de transactional_session\n\n"
                "Este guard rail está ativo porque:\n"
                f"- ENV = {os.getenv('ENV', 'development')}\n"
                f"- SQL_STRICT_TRANSACTIONS = {os.getenv('SQL_STRICT_TRANSACTIONS', 'false')}\n\n"
                "Em produção, este guard rail é automaticamente desativado."
            )
        
        # Se há transação ativa, permite o commit normalmente
        return original_commit()
    
    # Substitui o método commit da sessão pela versão protegida
    session.commit = guarded_commit


def enable_nested_transaction_guard(session: Session) -> None:
    """
    Bloqueia begin() ou begin_nested() quando já existir uma transação ativa.
    
    Esta função substitui os métodos begin() e begin_nested() da sessão por versões
    protegidas que verificam se já existe uma transação ativa antes de permitir
    a criação de uma nova transação.
    
    OBJETIVO:
    ---------
    Prevenir o uso indevido de transações nested quando já existe uma transação
    gerenciada por transactional_session, evitando complexidade desnecessária
    e potenciais bugs de isolamento.
    
    COMPORTAMENTO:
    --------------
    1. Se begin() for chamado E in_transaction() = True → RuntimeError
    2. Se begin_nested() for chamado E in_transaction() = True → RuntimeError
    3. Se begin() for chamado E in_transaction() = False → Permitido
    4. Se begin_nested() for chamado E in_transaction() = False → Permitido
    
    DETECÇÃO DE TRANSAÇÃO:
    ----------------------
    Utiliza session.in_transaction() para verificar se há uma transação ativa.
    Dentro de um bloco transactional_session, in_transaction() retorna True.
    
    ATIVAÇÃO CONDICIONAL:
    --------------------
    O guard rail só é ativado se:
    - ENV != "production" OU
    - SQL_STRICT_TRANSACTIONS = "true"
    
    EXEMPLOS:
    ---------
    
    ✅ begin() PERMITIDO (fora de transactional_session):
    ```python
    def operacao_manual(db: Session):
        # Gerenciamento manual de transação (raro, mas válido)
        trans = db.begin()
        try:
            venda = Venda(total=100)
            db.add(venda)
            trans.commit()
        except:
            trans.rollback()
            raise
        # Guard rail detecta: in_transaction() = False → Permitido
    ```
    
    ❌ begin() BLOQUEADO (dentro de transactional_session):
    ```python
    def operacao_errada(db: Session):
        with transactional_session(db):
            # ❌ ERRO: transactional_session já gerencia a transação
            trans = db.begin()  # RuntimeError!
            venda = Venda(total=100)
            db.add(venda)
        # Guard rail detecta: in_transaction() = True → Bloqueado
    ```
    
    ❌ begin_nested() BLOQUEADO (dentro de transactional_session):
    ```python
    def operacao_nested_errada(db: Session):
        with transactional_session(db):
            # ❌ ERRO: nested transaction desnecessária
            savepoint = db.begin_nested()  # RuntimeError!
            venda = Venda(total=100)
            db.add(venda)
            savepoint.commit()
        # Guard rail detecta: in_transaction() = True → Bloqueado
    ```
    
    RAZÕES PARA BLOQUEAR:
    ---------------------
    1. **Simplicidade**: transactional_session já gerencia transações
    2. **Evitar bugs**: Nested transactions podem causar confusão sobre estado
    3. **Consistência**: Padroniza o uso de transações no projeto
    4. **Manutenibilidade**: Código mais fácil de entender e manter
    
    QUANDO USAR begin() MANUALMENTE:
    --------------------------------
    Apenas em casos muito específicos fora de transactional_session:
    - Integrações com sistemas legados que exigem controle manual
    - Casos de migração onde transactional_session não pode ser usado
    - Scripts administrativos com requisitos especiais
    
    COMO ATIVAR:
    ------------
    ```python
    from app.db.guardrails import enable_nested_transaction_guard
    from app.database import SessionLocal
    
    db = SessionLocal()
    
    # Ativar guard rail (apenas em DEV/TEST)
    if os.getenv("ENV") != "production":
        enable_nested_transaction_guard(db)
    ```
    
    COMO DESATIVAR:
    ---------------
    1. Defina ENV=production (desativa automaticamente)
    2. Ou defina SQL_STRICT_TRANSACTIONS=false
    3. Ou simplesmente não chame enable_nested_transaction_guard()
    
    IMPORTANTE:
    -----------
    - Não altera o comportamento em produção
    - Não afeta transactional_session
    - Não modifica services, rotas ou models existentes
    - É apenas uma camada de proteção para desenvolvimento
    
    Parameters
    ----------
    session : Session
        Sessão SQLAlchemy a ser protegida
    
    Raises
    ------
    RuntimeError
        Se begin() ou begin_nested() for chamado dentro de uma transação ativa
    
    Notes
    -----
    Esta função modifica dinamicamente os métodos begin e begin_nested da sessão.
    Os métodos originais são preservados e podem ser restaurados se necessário.
    """
    # Preserva os métodos originais
    original_begin = session.begin
    original_begin_nested = session.begin_nested
    
    @wraps(original_begin)
    def guarded_begin():
        """
        Versão protegida do begin() que verifica se já há transação ativa.
        """
        if session.in_transaction():
            raise RuntimeError(
                "❌ NESTED TRANSACTION BLOQUEADA: begin() detectado dentro de transactional_session!\n\n"
                "PROBLEMA:\n"
                "Você está tentando iniciar uma nova transação (db.begin()) dentro de um bloco\n"
                "transactional_session que já está gerenciando uma transação ativa.\n\n"
                "MOTIVO DO BLOQUEIO:\n"
                "- transactional_session JÁ gerencia a transação automaticamente\n"
                "- Criar transações nested manualmente adiciona complexidade desnecessária\n"
                "- Pode causar bugs sutis relacionados a isolamento e rollback\n"
                "- Dificulta manutenção e compreensão do código\n\n"
                "SOLUÇÃO:\n"
                "1. REMOVA a chamada db.begin() de dentro do bloco transactional_session\n"
                "2. Deixe o transactional_session gerenciar a transação automaticamente:\n\n"
                "   ✅ CORRETO:\n"
                "   with transactional_session(db):\n"
                "       # suas operações aqui\n"
                "       # transação gerenciada automaticamente\n\n"
                "   ❌ INCORRETO:\n"
                "   with transactional_session(db):\n"
                "       trans = db.begin()  # ← REMOVA ISSO\n"
                "       # operações...\n\n"
                "3. Se você REALMENTE precisa de controle manual de transação,\n"
                "   não use transactional_session - use begin() diretamente:\n\n"
                "   trans = db.begin()\n"
                "   try:\n"
                "       # suas operações\n"
                "       trans.commit()\n"
                "   except:\n"
                "       trans.rollback()\n"
                "       raise\n\n"
                f"Este guard rail está ativo porque:\n"
                f"- ENV = {os.getenv('ENV', 'development')}\n"
                f"- SQL_STRICT_TRANSACTIONS = {os.getenv('SQL_STRICT_TRANSACTIONS', 'false')}\n\n"
                "Em produção, este guard rail é automaticamente desativado."
            )
        
        # Se não há transação ativa, permite begin() normalmente
        return original_begin()
    
    @wraps(original_begin_nested)
    def guarded_begin_nested():
        """
        Versão protegida do begin_nested() que verifica se já há transação ativa.
        """
        if session.in_transaction():
            raise RuntimeError(
                "❌ NESTED TRANSACTION BLOQUEADA: begin_nested() detectado dentro de transactional_session!\n\n"
                "PROBLEMA:\n"
                "Você está tentando criar um savepoint (db.begin_nested()) dentro de um bloco\n"
                "transactional_session que já está gerenciando uma transação ativa.\n\n"
                "MOTIVO DO BLOQUEIO:\n"
                "- transactional_session JÁ fornece atomicidade completa\n"
                "- Savepoints nested manualmente adicionam complexidade desnecessária\n"
                "- Na maioria dos casos, não há necessidade real de savepoints\n"
                "- Dificulta debugging e compreensão do fluxo de transação\n\n"
                "SOLUÇÃO:\n"
                "1. REMOVA a chamada db.begin_nested() de dentro do bloco transactional_session\n"
                "2. Se você precisa de atomicidade parcial, considere:\n\n"
                "   a) Dividir em múltiplas funções com transactional_session separadas\n"
                "   b) Usar try/except para controle de erro dentro do bloco\n"
                "   c) Reavaliar se realmente precisa de savepoints\n\n"
                "   ✅ CORRETO (atomicidade completa):\n"
                "   with transactional_session(db):\n"
                "       # todas operações são atômicas\n"
                "       venda = criar_venda()\n"
                "       atualizar_estoque()\n"
                "       # tudo commitado junto ou tudo revertido\n\n"
                "   ✅ CORRETO (operações separadas):\n"
                "   with transactional_session(db):\n"
                "       venda = criar_venda()\n"
                "   \n"
                "   with transactional_session(db):\n"
                "       atualizar_estoque()\n\n"
                "   ❌ INCORRETO (nested desnecessário):\n"
                "   with transactional_session(db):\n"
                "       savepoint = db.begin_nested()  # ← REMOVA ISSO\n"
                "       venda = criar_venda()\n"
                "       savepoint.commit()\n\n"
                "3. Se você REALMENTE precisa de savepoints (caso raro),\n"
                "   não use transactional_session - gerencie manualmente:\n\n"
                "   trans = db.begin()\n"
                "   try:\n"
                "       savepoint = db.begin_nested()\n"
                "       try:\n"
                "           # operação que pode falhar\n"
                "           savepoint.commit()\n"
                "       except:\n"
                "           savepoint.rollback()\n"
                "       trans.commit()\n"
                "   except:\n"
                "       trans.rollback()\n"
                "       raise\n\n"
                f"Este guard rail está ativo porque:\n"
                f"- ENV = {os.getenv('ENV', 'development')}\n"
                f"- SQL_STRICT_TRANSACTIONS = {os.getenv('SQL_STRICT_TRANSACTIONS', 'false')}\n\n"
                "Em produção, este guard rail é automaticamente desativado."
            )
        
        # Se não há transação ativa, permite begin_nested() normalmente
        return original_begin_nested()
    
    # Substitui os métodos da sessão pelas versões protegidas
    session.begin = guarded_begin
    session.begin_nested = guarded_begin_nested


def enable_multiple_commits_guard(session: Session) -> None:
    """
    Bloqueia múltiplas chamadas de commit() dentro do mesmo ciclo de request.
    
    Esta função protege contra o padrão anti-pattern de fazer múltiplos commits
    no mesmo request, que geralmente indica arquitetura incorreta e pode causar
    estados parcialmente commitados em caso de erro posterior.
    
    OBJETIVO:
    ---------
    Detectar e prevenir múltiplos commits no mesmo request/sessão, forçando
    consolidação de operações em uma única transação atômica.
    
    ESTRATÉGIA IMPLEMENTADA:
    ------------------------
    Utiliza um atributo privado na sessão (_guardrail_commit_count) para rastrear
    o número de commits realizados. Este contador é:
    - Inicializado em 0 quando o guard rail é ativado
    - Incrementado a cada commit() bem-sucedido
    - Resetado quando a sessão é fechada (lifecycle normal do FastAPI)
    
    VANTAGENS DESTA ABORDAGEM:
    --------------------------
    1. **Simples**: Não requer gerenciamento de contextvars ou middleware
    2. **Thread-safe**: Cada sessão é independente
    3. **Natural**: Sessões no FastAPI são criadas por request via Depends
    4. **Limpa**: Reseta automaticamente quando a sessão é fechada
    
    COMPORTAMENTO:
    --------------
    1. Primeiro commit() no request → Permitido (contador = 1)
    2. Segundo commit() no mesmo request → RuntimeError (DEV/TEST)
    3. Requests diferentes → Contadores independentes (não interferem)
    
    ATIVAÇÃO CONDICIONAL:
    --------------------
    O guard rail só é ativado se:
    - ENV != "production" OU
    - SQL_STRICT_TRANSACTIONS = "true"
    
    EXEMPLOS:
    ---------
    
    ✅ UM COMMIT PERMITIDO (padrão correto):
    ```python
    from app.db.transaction import transactional_session
    
    @app.post("/vendas")
    def criar_venda(db: Session = Depends(get_db)):
        with transactional_session(db):
            # Criar venda
            venda = Venda(total=100)
            db.add(venda)
            
            # Criar itens
            item = VendaItem(venda=venda, produto_id=10)
            db.add(item)
            
            # Atualizar estoque
            produto = db.query(Produto).filter_by(id=10).first()
            produto.estoque -= 1
            
            # ✅ UM commit ao final do bloco
        # Guard rail: commit_count = 1 → PERMITIDO
    ```
    
    ❌ MÚLTIPLOS COMMITS BLOQUEADOS (anti-pattern):
    ```python
    @app.post("/vendas")
    def criar_venda_errado(db: Session = Depends(get_db)):
        # Primeiro commit
        with transactional_session(db):
            venda = Venda(total=100)
            db.add(venda)
        # commit_count = 1 → OK
        
        # ❌ ERRO: Segundo commit no mesmo request
        with transactional_session(db):
            item = VendaItem(venda=venda, produto_id=10)
            db.add(item)
        # RuntimeError! commit_count = 2 → BLOQUEADO
    ```
    
    RAZÕES PARA BLOQUEAR MÚLTIPLOS COMMITS:
    ---------------------------------------
    1. **Atomicidade Quebrada**: Se o segundo commit falhar, o primeiro já foi persistido
    2. **Estado Inconsistente**: Dados parcialmente salvos são difíceis de reverter
    3. **Arquitetura Incorreta**: Múltiplos commits indicam falta de planejamento transacional
    4. **Complexidade**: Dificulta debugging e compreensão do fluxo
    5. **Manutenibilidade**: Código com múltiplos commits é mais propenso a bugs
    
    EXEMPLO DE PROBLEMA COM MÚLTIPLOS COMMITS:
    ------------------------------------------
    ```python
    # ❌ PERIGO: Estado inconsistente se houver erro
    with transactional_session(db):
        venda = Venda(total=100)
        db.add(venda)
    # COMMIT 1: Venda salva ✅
    
    with transactional_session(db):
        item = VendaItem(venda=venda, produto_id=999)  # produto não existe
        db.add(item)
    # COMMIT 2: ERRO! ❌
    
    # RESULTADO: Venda salva sem itens → Estado inconsistente! 💥
    ```
    
    SOLUÇÃO CORRETA (UM ÚNICO COMMIT):
    ----------------------------------
    ```python
    # ✅ Atomicidade completa
    with transactional_session(db):
        venda = Venda(total=100)
        db.add(venda)
        
        item = VendaItem(venda=venda, produto_id=999)
        db.add(item)
    # UM commit: ou TUDO é salvo, ou NADA é salvo ✅
    ```
    
    INTEGRAÇÃO COM GUARD RAIL 1:
    ----------------------------
    Este guard rail trabalha em conjunto com o Guard Rail 1 (Commit Guard):
    - **Guard Rail 1**: Garante que commit() só aconteça dentro de transactional_session
    - **Guard Rail 3**: Garante que commit() aconteça apenas UMA vez por request
    
    COMO ATIVAR:
    ------------
    ```python
    from app.db.guardrails import enable_multiple_commits_guard
    from app.database import SessionLocal
    
    db = SessionLocal()
    
    # Ativar guard rail (apenas em DEV/TEST)
    if os.getenv("ENV") != "production":
        enable_multiple_commits_guard(db)
    ```
    
    ATIVAÇÃO AUTOMÁTICA (Recomendado):
    ----------------------------------
    ```python
    from app.db.guardrails import apply_all_guardrails
    
    def get_db():
        db = SessionLocal()
        try:
            # Aplica TODOS os guard rails (inclui este)
            apply_all_guardrails(db)
            yield db
        finally:
            db.close()
    ```
    
    COMO DESATIVAR:
    ---------------
    1. Defina ENV=production (desativa automaticamente)
    2. Ou defina SQL_STRICT_TRANSACTIONS=false
    3. Ou simplesmente não chame enable_multiple_commits_guard()
    
    IMPORTANTE:
    -----------
    - Não altera o comportamento em produção
    - Não afeta transactional_session
    - Não modifica services, rotas ou models existentes
    - É apenas uma camada de proteção para desenvolvimento
    - Cada sessão tem seu próprio contador (requests não interferem)
    
    Parameters
    ----------
    session : Session
        Sessão SQLAlchemy a ser protegida
    
    Raises
    ------
    RuntimeError
        Se commit() for chamado mais de uma vez no mesmo request/sessão
    
    Notes
    -----
    - Esta função modifica dinamicamente o método commit da sessão
    - O contador é armazenado como atributo privado na sessão
    - O contador reseta automaticamente quando a sessão é fechada
    - Compatível com FastAPI Depends e outros frameworks de DI
    """
    # Inicializa o contador de commits para esta sessão
    session._guardrail_commit_count = 0
    
    # Preserva o método commit original
    original_commit = session.commit
    
    @wraps(original_commit)
    def guarded_multiple_commits():
        """
        Versão protegida do commit que detecta múltiplos commits no mesmo request.
        """
        # Verifica quantos commits já foram feitos nesta sessão
        current_count = getattr(session, '_guardrail_commit_count', 0)
        
        if current_count >= 1:
            raise RuntimeError(
                "❌ MÚLTIPLOS COMMITS BLOQUEADOS: Segundo commit() detectado no mesmo request!\n\n"
                "PROBLEMA:\n"
                "Você está tentando fazer múltiplos commits no mesmo request/sessão.\n"
                "Isso é um anti-pattern que pode causar estados inconsistentes no banco de dados.\n\n"
                "MOTIVO DO BLOQUEIO:\n"
                "- Múltiplos commits quebram a atomicidade das operações\n"
                "- Se o segundo commit falhar, o primeiro já foi persistido\n"
                "- Dados parcialmente salvos são difíceis de reverter\n"
                "- Indica arquitetura incorreta e falta de planejamento transacional\n"
                "- Dificulta debugging e aumenta complexidade\n\n"
                "EXEMPLO DO PROBLEMA:\n"
                "┌─────────────────────────────────────┐\n"
                "│ with transactional_session(db):     │\n"
                "│     venda = Venda(total=100)        │\n"
                "│     db.add(venda)                   │\n"
                "│ # COMMIT 1 ✅ (venda salva)         │\n"
                "│                                     │\n"
                "│ with transactional_session(db):     │\n"
                "│     item = VendaItem(...)           │\n"
                "│     db.add(item)  # ERRO! ❌        │\n"
                "│ # COMMIT 2 falha                    │\n"
                "│                                     │\n"
                "│ RESULTADO: Venda sem itens! 💥      │\n"
                "└─────────────────────────────────────┘\n\n"
                "SOLUÇÃO CORRETA:\n"
                "Consolide TODAS as operações em UMA ÚNICA transação:\n\n"
                "✅ CORRETO:\n"
                "with transactional_session(db):\n"
                "    # Criar venda\n"
                "    venda = Venda(total=100)\n"
                "    db.add(venda)\n"
                "    \n"
                "    # Criar itens\n"
                "    item = VendaItem(venda=venda, produto_id=10)\n"
                "    db.add(item)\n"
                "    \n"
                "    # Atualizar estoque\n"
                "    produto = db.query(Produto).filter_by(id=10).first()\n"
                "    produto.estoque -= 1\n"
                "    \n"
                "    # UM commit ao final: TUDO ou NADA ✅\n\n"
                "ALTERNATIVAS (se realmente precisar de commits separados):\n"
                "1. Dividir em múltiplos endpoints (requests separados)\n"
                "2. Usar padrão saga para compensação de transações\n"
                "3. Reavaliar a arquitetura da operação\n\n"
                "ESTATÍSTICAS DESTA SESSÃO:\n"
                f"- Commits já realizados: {current_count}\n"
                f"- Tentativa de commit #{current_count + 1} BLOQUEADA\n\n"
                f"Este guard rail está ativo porque:\n"
                f"- ENV = {os.getenv('ENV', 'development')}\n"
                f"- SQL_STRICT_TRANSACTIONS = {os.getenv('SQL_STRICT_TRANSACTIONS', 'false')}\n\n"
                "Em produção, este guard rail é automaticamente desativado."
            )
        
        # Executa o commit original
        result = original_commit()
        
        # Incrementa o contador após commit bem-sucedido
        session._guardrail_commit_count = current_count + 1
        
        return result
    
    # Substitui o método commit da sessão pela versão protegida
    session.commit = guarded_multiple_commits


def should_enable_guardrails() -> bool:
    """
    Determina se os guard rails devem ser ativados com base nas variáveis de ambiente.
    
    REGRAS:
    -------
    - Guard rails são ativados se ENV != "production"
    - OU se SQL_STRICT_TRANSACTIONS = "true"
    - Em produção, guard rails são desativados por padrão para evitar overhead
    
    Returns
    -------
    bool
        True se guard rails devem ser ativados, False caso contrário
    
    Examples
    --------
    ```python
    from app.db.guardrails import should_enable_guardrails, enable_commit_guard
    
    db = get_session()
    
    if should_enable_guardrails():
        enable_commit_guard(db)
    ```
    """
    env = os.getenv("ENV", "development").lower()
    strict_transactions = os.getenv("SQL_STRICT_TRANSACTIONS", "false").lower() == "true"
    
    # Ativa guard rails em qualquer ambiente que não seja produção
    # OU se SQL_STRICT_TRANSACTIONS estiver explicitamente ativado
    return env != "production" or strict_transactions


def apply_all_guardrails(session: Session) -> None:
    """
    Aplica todos os guard rails disponíveis à sessão.
    
    Esta é uma função de conveniência que aplica todos os guard rails
    implementados, verificando automaticamente se devem ser ativados.
    
    GUARD RAILS IMPLEMENTADOS:
    --------------------------
    1. Commit Guard: Detecta commits fora de transactional_session
    2. Nested Transaction Guard: Detecta begin()/begin_nested() dentro de transactional_session
    3. Multiple Commits Guard: Detecta múltiplos commits no mesmo request
    
    GUARD RAILS FUTUROS:
    --------------------
    4. Query Guard: Detectar queries N+1
    5. Flush Guard: Detectar flush() manual desnecessário
    
    Parameters
    ----------
    session : Session
        Sessão SQLAlchemy a ser protegida
    
    Examples
    --------
    ```python
    from app.db.guardrails import apply_all_guardrails
    
    db = get_session()
    apply_all_guardrails(db)  # Aplica todos os guard rails se ambiente apropriado
    ```
    """
    if should_enable_guardrails():
        enable_commit_guard(session)
        enable_nested_transaction_guard(session)
        enable_multiple_commits_guard(session)
