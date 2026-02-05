# 📄 CHANGES_PREPROD_SEED_CONTROL.md

## PRÉ-PRODUÇÃO — BLOCO 5: CONTROLE DE SEED DE DADOS

**Data:** 2026-02-05  
**Fase:** Pré-Produção  
**Prioridade:** P0 (Crítico)

---

## 🎯 OBJETIVO

Garantir que dados iniciais (seed):

1. **Rodem UMA única vez** (não duplicam dados)
2. **Sejam idempotentes** (podem rodar múltiplas vezes sem quebrar)
3. **Não contaminem produção** (controle de ambiente)

---

## ✅ ARQUIVO CRIADO

### `backend/app/db/seed_control.py`

**Propósito:** Módulo dedicado de controle de execução de seeds

**Estrutura:**

```
backend/app/db/seed_control.py
├── seed_if_needed()              # Função PRINCIPAL - aplica seed se necessário
├── is_seed_applied()             # Verifica se seed já foi aplicado
├── mark_seed_as_applied()        # Marca seed como aplicado
├── ensure_seed_version_table()   # Garante tabela existe
├── list_applied_seeds()          # Lista todos os seeds aplicados
├── reset_seed()                  # Remove registro de seed (DEV only)
├── get_seed_info()               # Obtém info de um seed
├── should_run_seed()             # Verifica se ambiente permite seed
└── run_seed_safely()             # Wrapper de alto nível (recomendado)
```

---

## 🗄️ ESTRATÉGIA ESCOLHIDA: Tabela `seed_version`

### Por que esta estratégia?

Escolhi usar uma **tabela dedicada** (`seed_version`) pelos seguintes motivos:

| Critério | Avaliação |
|----------|-----------|
| **Simplicidade** | ✅ Simples de implementar e entender |
| **Auditabilidade** | ✅ Histórico completo de quando/quem aplicou |
| **Flexibilidade** | ✅ Suporta múltiplos seeds nomeados |
| **Idempotência** | ✅ Fácil verificar se seed já foi aplicado |
| **Versionamento** | ✅ Facilita evolução de seeds ao longo do tempo |
| **Portabilidade** | ✅ Funciona em qualquer banco SQL |
| **Observabilidade** | ✅ Fácil consultar via SQL |

### Estrutura da Tabela

```sql
CREATE TABLE seed_version (
    seed_name VARCHAR(100) PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL,
    applied_by VARCHAR(100) NOT NULL DEFAULT 'system'
);
```

**Campos:**

- `seed_name`: Nome único do seed (ex: "initial_roles", "default_categories")
- `applied_at`: Timestamp UTC de quando foi aplicado
- `applied_by`: Quem aplicou (system, admin, CI/CD, etc.)

### Exemplo de Dados

```
seed_name           | applied_at                 | applied_by
--------------------|----------------------------|------------
initial_roles       | 2026-02-05 10:00:00.000    | system
default_categories  | 2026-02-05 10:00:05.123    | system
initial_users       | 2026-02-05 10:30:00.456    | admin
```

---

## 🔧 CÓDIGO COMPLETO

### Função Principal: `seed_if_needed()`

```python
def seed_if_needed(
    session: Session,
    seed_func: Callable[[Session], None],
    seed_name: str = "initial_data",
    force: bool = False
) -> bool:
    """
    Executa seed inicial apenas se ainda não foi executado.
    
    Esta é a função PRINCIPAL para aplicar seeds de forma controlada.
    
    Args:
        session: SQLAlchemy session
        seed_func: Função que aplica o seed (recebe session)
        seed_name: Nome do seed (para tracking)
        force: Se True, aplica mesmo se já foi aplicado
    
    Returns:
        True se seed foi aplicado, False se já estava aplicado
    
    Fluxo:
    ------
    1. Verifica se seed já foi aplicado
    2. Se JÁ aplicado e force=False: retorna False
    3. Se NÃO aplicado ou force=True:
       a. Executa seed_func(session)
       b. Marca seed como aplicado
       c. Retorna True
    """
    
    logger.info(f"🌱 Checking seed: {seed_name}")
    
    # Verificar se já foi aplicado
    already_applied = is_seed_applied(session, seed_name)
    
    if already_applied and not force:
        logger.info(f"⏭️  Seed '{seed_name}' already applied, skipping...")
        return False
    
    if already_applied and force:
        logger.warning(f"⚠️  FORCE mode: re-applying seed '{seed_name}'")
    
    # Aplicar seed
    try:
        logger.info(f"🌱 Applying seed: {seed_name}")
        seed_func(session)
        
        if not already_applied:
            mark_seed_as_applied(session, seed_name, applied_by="system")
        
        logger.info(f"✅ Seed '{seed_name}' applied successfully")
        return True
    
    except Exception as e:
        logger.error(f"❌ Error applying seed: {str(e)}")
        session.rollback()
        raise
```

### Função de Verificação: `is_seed_applied()`

```python
def is_seed_applied(session: Session, seed_name: str = "initial_data") -> bool:
    """
    Verifica se um seed específico já foi aplicado.
    
    Returns:
        True se seed já foi aplicado, False caso contrário
    """
    try:
        ensure_seed_version_table(session)
        
        result = session.execute(
            text("SELECT COUNT(*) FROM seed_version WHERE seed_name = :name"),
            {"name": seed_name}
        )
        count = result.scalar()
        
        return count > 0
    
    except Exception as e:
        logger.error(f"❌ Error checking seed: {str(e)}")
        return False  # Em caso de erro, assumir NÃO aplicado
```

### Wrapper Seguro: `run_seed_safely()`

```python
def run_seed_safely(
    session: Session,
    seed_func: Callable[[Session], None],
    seed_name: str = "initial_data",
    env: Optional[str] = None,
    allow_prod: bool = False,
    force: bool = False
) -> bool:
    """
    Wrapper de alto nível que combina todas as verificações.
    
    Esta função:
    1. Verifica ambiente (DEV/TEST/PROD)
    2. Verifica se seed já foi aplicado
    3. Aplica seed de forma controlada
    
    Returns:
        True se seed foi aplicado, False caso contrário
    """
    
    # Verificar ambiente
    if env is not None:
        if not should_run_seed(env, allow_prod_seed=allow_prod):
            logger.warning(f"🚫 Seed blocked by environment policy")
            return False
    
    # Aplicar seed
    return seed_if_needed(session, seed_func, seed_name, force=force)
```

### Controle de Ambiente: `should_run_seed()`

```python
def should_run_seed(env: str, allow_prod_seed: bool = False) -> bool:
    """
    Determina se seed deve ser executado baseado no ambiente.
    
    Regras:
    -------
    - DEV: Sempre pode rodar seed ✅
    - TEST: Sempre pode rodar seed ✅
    - PROD: Apenas se allow_prod_seed=True ⚠️
    
    Returns:
        True se seed pode ser executado
    """
    env_lower = env.lower()
    
    if env_lower in ['development', 'dev']:
        logger.info("✅ Environment: DEV - seed allowed")
        return True
    
    if env_lower in ['test', 'testing']:
        logger.info("✅ Environment: TEST - seed allowed")
        return True
    
    if env_lower in ['production', 'prod']:
        if allow_prod_seed:
            logger.warning("⚠️  Environment: PROD - seed EXPLICITLY ALLOWED")
            return True
        else:
            logger.warning("❌ Environment: PROD - seed BLOCKED")
            return False
    
    # Ambiente desconhecido - bloquear
    logger.warning(f"❌ Environment: {env} - unknown, seed BLOCKED")
    return False
```

---

## 📖 COMO USAR

### Uso Básico: DEV/TEST

```python
from app.db import get_session
from app.db.seed_control import seed_if_needed

def apply_initial_roles(session):
    """Função que cria roles iniciais"""
    from app.models import Role
    
    # Criar roles (idempotente - verifica se já existe)
    roles = ["admin", "user", "moderator"]
    for role_name in roles:
        existing = session.query(Role).filter_by(name=role_name).first()
        if not existing:
            session.add(Role(name=role_name))
    
    session.commit()

# Aplicar seed
session = next(get_session())
seed_if_needed(session, apply_initial_roles, seed_name="initial_roles")
```

### Uso Seguro: Com Verificação de Ambiente

```python
from app.config import ENVIRONMENT
from app.db.seed_control import run_seed_safely

def apply_default_categories(session):
    """Função que cria categorias padrão"""
    from app.models import Category
    
    categories = ["Ração", "Brinquedos", "Higiene", "Acessórios"]
    for cat_name in categories:
        existing = session.query(Category).filter_by(name=cat_name).first()
        if not existing:
            session.add(Category(name=cat_name))
    
    session.commit()

# Aplicar com verificação de ambiente
session = next(get_session())
run_seed_safely(
    session,
    apply_default_categories,
    seed_name="default_categories",
    env=ENVIRONMENT  # Só roda em DEV/TEST
)
```

### Uso em Produção (Flag Explícita)

```python
# ⚠️  CUIDADO: Apenas use em produção se realmente necessário!
run_seed_safely(
    session,
    apply_critical_data,
    seed_name="critical_prod_data",
    env=ENVIRONMENT,
    allow_prod=True  # 🔓 Flag explícita para produção
)
```

### Forçar Re-aplicação (DEV)

```python
# Em DEV, se quiser re-aplicar um seed
seed_if_needed(
    session,
    apply_initial_roles,
    seed_name="initial_roles",
    force=True  # ⚠️  Re-aplica mesmo se já foi aplicado
)
```

---

## 🚀 COMO RODAR SEED MANUALMENTE

### Opção 1: Script Python

```python
# scripts/run_seed.py
"""
Script para aplicar seeds manualmente
"""
from app.db import get_session
from app.db.seed_control import run_seed_safely
from app.config import ENVIRONMENT

def apply_all_seeds(session):
    """Aplica todos os seeds necessários"""
    
    # Seed 1: Roles
    from app.seeds.roles import apply_initial_roles
    seed_if_needed(session, apply_initial_roles, seed_name="initial_roles")
    
    # Seed 2: Categories
    from app.seeds.categories import apply_default_categories
    seed_if_needed(session, apply_default_categories, seed_name="default_categories")
    
    # Seed 3: Users
    from app.seeds.users import apply_default_users
    seed_if_needed(session, apply_default_users, seed_name="default_users")

if __name__ == "__main__":
    session = next(get_session())
    
    try:
        run_seed_safely(
            session,
            apply_all_seeds,
            seed_name="all_seeds",
            env=ENVIRONMENT
        )
        print("✅ Seeds applied successfully!")
    
    except Exception as e:
        print(f"❌ Error applying seeds: {e}")
        session.rollback()
```

**Executar:**
```bash
cd backend
python scripts/run_seed.py
```

### Opção 2: Command Line (Flask-like)

```python
# app/cli/seed.py
"""
CLI commands para seeds
"""
import click
from app.db import get_session
from app.db.seed_control import run_seed_safely, list_applied_seeds, reset_seed
from app.config import ENVIRONMENT

@click.group()
def seed():
    """Comandos de seed"""
    pass

@seed.command()
@click.option('--force', is_flag=True, help='Force re-application')
@click.option('--allow-prod', is_flag=True, help='Allow in production')
def apply(force, allow_prod):
    """Aplica todos os seeds"""
    session = next(get_session())
    
    # ... aplicar seeds ...
    
    click.echo("✅ Seeds applied!")

@seed.command()
def list():
    """Lista seeds aplicados"""
    session = next(get_session())
    seeds = list_applied_seeds(session)
    
    for seed in seeds:
        click.echo(f"✓ {seed['seed_name']} - {seed['applied_at']}")

@seed.command()
@click.argument('seed_name')
def reset(seed_name):
    """Reseta um seed específico (DEV only)"""
    if ENVIRONMENT != 'development':
        click.echo("❌ Reset only allowed in DEV environment")
        return
    
    session = next(get_session())
    reset_seed(session, seed_name)
    click.echo(f"✅ Seed '{seed_name}' reset!")

if __name__ == '__main__':
    seed()
```

**Executar:**
```bash
cd backend
python -m app.cli.seed apply
python -m app.cli.seed list
python -m app.cli.seed reset initial_roles
```

### Opção 3: FastAPI Endpoint (Admin Only)

```python
# app/routes/admin_seed_routes.py
"""
Endpoints administrativos para seeds
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.db.seed_control import list_applied_seeds, run_seed_safely
from app.config import ENVIRONMENT

router = APIRouter(prefix="/admin/seeds", tags=["Admin - Seeds"])

@router.get("/")
def get_applied_seeds(session: Session = Depends(get_session)):
    """Lista todos os seeds aplicados"""
    # TODO: Adicionar autenticação admin
    return list_applied_seeds(session)

@router.post("/apply/{seed_name}")
def apply_seed(
    seed_name: str,
    force: bool = False,
    allow_prod: bool = False,
    session: Session = Depends(get_session)
):
    """Aplica um seed específico"""
    # TODO: Adicionar autenticação admin
    
    if ENVIRONMENT == 'production' and not allow_prod:
        raise HTTPException(
            status_code=403,
            detail="Seeds blocked in production (use allow_prod=true to override)"
        )
    
    # ... aplicar seed ...
    
    return {"message": f"Seed '{seed_name}' applied"}
```

**Executar:**
```bash
curl -X POST http://localhost:8000/admin/seeds/apply/initial_roles
curl http://localhost:8000/admin/seeds/
```

---

## 🛡️ GARANTIAS FORNECIDAS

### 1️⃣ Idempotência

| Garantia | Status | Como? |
|----------|--------|-------|
| Seed não duplica dados | ✅ | Verificação via `is_seed_applied()` |
| Pode rodar múltiplas vezes | ✅ | Retorna False se já aplicado |
| Não quebra se rodar 2x | ✅ | Operações dentro do seed devem ser idempotentes |

**Exemplo de seed idempotente:**
```python
def apply_roles(session):
    roles = ["admin", "user"]
    
    for role_name in roles:
        # ✅ Verifica se já existe antes de criar
        existing = session.query(Role).filter_by(name=role_name).first()
        if not existing:
            session.add(Role(name=role_name))
    
    session.commit()
```

### 2️⃣ Controle de Ambiente

| Ambiente | Comportamento | Override? |
|----------|---------------|-----------|
| **DEV** | ✅ Sempre permitido | N/A |
| **TEST** | ✅ Sempre permitido | N/A |
| **PROD** | ❌ Bloqueado por padrão | `allow_prod=True` |
| **Desconhecido** | ❌ Bloqueado por segurança | Não |

**Proteção contra contaminação de produção:**
```python
# Em produção SEM flag explícita
run_seed_safely(session, seed_func, env="production")
# ❌ Bloqueado: "seed BLOCKED by environment policy"

# Em produção COM flag explícita
run_seed_safely(session, seed_func, env="production", allow_prod=True)
# ⚠️  Permitido com warning: "seed EXPLICITLY ALLOWED"
```

### 3️⃣ Rastreabilidade

| Aspecto | Status | Detalhe |
|---------|--------|---------|
| Histórico de aplicação | ✅ | Timestamp UTC registrado |
| Quem aplicou | ✅ | Campo `applied_by` |
| Listagem de seeds | ✅ | `list_applied_seeds()` |
| Consulta individual | ✅ | `get_seed_info()` |
| Logs estruturados | ✅ | Logging em todas as operações |

**Exemplo de auditoria:**
```python
>>> seeds = list_applied_seeds(session)
>>> for seed in seeds:
...     print(f"{seed['seed_name']}: {seed['applied_at']} by {seed['applied_by']}")

initial_roles: 2026-02-05 10:00:00 by system
default_categories: 2026-02-05 10:00:05 by system
admin_user: 2026-02-05 10:30:00 by CI/CD
```

### 4️⃣ Segurança

| Proteção | Status | Implementação |
|----------|--------|---------------|
| Bloqueio automático em PROD | ✅ | `should_run_seed()` |
| Flag explícita necessária | ✅ | `allow_prod=True` |
| Logs de warning em PROD | ✅ | Logger.warning() |
| Ambiente desconhecido bloqueado | ✅ | Default: bloquear |

### 5️⃣ Recuperação

| Funcionalidade | Status | Uso |
|----------------|--------|-----|
| Resetar seed | ✅ | `reset_seed()` - DEV only |
| Forçar re-aplicação | ✅ | `force=True` |
| Rollback em erro | ✅ | `session.rollback()` |
| Exceções propagadas | ✅ | Permite tratamento externo |

---

## 📊 FLUXO DE EXECUÇÃO

### Cenário 1: Primeira Execução (Seed Não Aplicado)

```
┌─────────────────────────────────────┐
│ seed_if_needed(session, seed_func)  │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ is_seed_applied("initial_data")?    │
└──────────────┬──────────────────────┘
               │
          ┌────┴────┐
          │ NÃO     │
          └────┬────┘
               │
               ▼
┌─────────────────────────────────────┐
│ seed_func(session)                  │
│ [Cria dados iniciais]               │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ mark_seed_as_applied()              │
│ [INSERT INTO seed_version]          │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ ✅ SUCESSO                          │
│ return True                         │
└─────────────────────────────────────┘
```

**Logs:**
```
INFO: 🌱 Checking seed: initial_data
INFO: ○ Seed 'initial_data' not yet applied
INFO: 🌱 Applying seed: initial_data
INFO: ✅ Seed 'initial_data' marked as applied by system
INFO: ✅ Seed 'initial_data' applied successfully
```

### Cenário 2: Segunda Execução (Seed Já Aplicado)

```
┌─────────────────────────────────────┐
│ seed_if_needed(session, seed_func)  │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ is_seed_applied("initial_data")?    │
└──────────────┬──────────────────────┘
               │
          ┌────┴────┐
          │ SIM     │
          └────┬────┘
               │
               ▼
┌─────────────────────────────────────┐
│ ⏭️  SKIP                            │
│ return False                        │
└─────────────────────────────────────┘
```

**Logs:**
```
INFO: 🌱 Checking seed: initial_data
INFO: ✓ Seed 'initial_data' already applied
INFO: ⏭️  Seed 'initial_data' already applied, skipping...
```

### Cenário 3: Produção Sem Flag

```
┌─────────────────────────────────────┐
│ run_seed_safely(session, seed_func, │
│                 env="production")    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ should_run_seed("production")?      │
└──────────────┬──────────────────────┘
               │
          ┌────┴────┐
          │ NÃO     │ (allow_prod=False)
          └────┬────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 🚫 BLOCKED                          │
│ return False                        │
└─────────────────────────────────────┘
```

**Logs:**
```
WARNING: ❌ Environment: PROD - seed BLOCKED (use allow_prod_seed=True to override)
WARNING: 🚫 Seed 'initial_data' blocked by environment policy
```

---

## 🧪 EXEMPLOS DE SEED

### Exemplo 1: Roles Iniciais

```python
# app/seeds/roles.py
from sqlalchemy.orm import Session
from app.models import Role

def apply_initial_roles(session: Session):
    """
    Cria roles iniciais do sistema.
    
    Idempotente: Verifica se role já existe antes de criar.
    """
    roles = [
        {"name": "admin", "description": "Administrator"},
        {"name": "user", "description": "Regular user"},
        {"name": "moderator", "description": "Content moderator"}
    ]
    
    for role_data in roles:
        # ✅ Idempotente: verifica se já existe
        existing = session.query(Role).filter_by(name=role_data["name"]).first()
        
        if not existing:
            role = Role(**role_data)
            session.add(role)
            print(f"✓ Created role: {role_data['name']}")
        else:
            print(f"○ Role already exists: {role_data['name']}")
    
    session.commit()
```

**Executar:**
```python
from app.db import get_session
from app.db.seed_control import seed_if_needed
from app.seeds.roles import apply_initial_roles

session = next(get_session())
seed_if_needed(session, apply_initial_roles, seed_name="initial_roles")
```

### Exemplo 2: Categorias Padrão

```python
# app/seeds/categories.py
from sqlalchemy.orm import Session
from app.models import Category

def apply_default_categories(session: Session):
    """
    Cria categorias padrão de produtos.
    
    Idempotente: Usa upsert pattern.
    """
    categories = [
        {"name": "Ração", "slug": "racao"},
        {"name": "Brinquedos", "slug": "brinquedos"},
        {"name": "Higiene", "slug": "higiene"},
        {"name": "Acessórios", "slug": "acessorios"}
    ]
    
    for cat_data in categories:
        # ✅ Idempotente: UPDATE se existe, INSERT se não
        existing = session.query(Category).filter_by(slug=cat_data["slug"]).first()
        
        if existing:
            # Atualizar
            existing.name = cat_data["name"]
            print(f"↻ Updated category: {cat_data['name']}")
        else:
            # Criar
            category = Category(**cat_data)
            session.add(category)
            print(f"✓ Created category: {cat_data['name']}")
    
    session.commit()
```

### Exemplo 3: Usuário Admin

```python
# app/seeds/admin_user.py
from sqlalchemy.orm import Session
from app.models import User, Role
from app.security import hash_password

def apply_admin_user(session: Session):
    """
    Cria usuário admin padrão.
    
    ⚠️  Use apenas em DEV!
    Em produção, admin deve ser criado manualmente com senha segura.
    """
    # Verificar se admin já existe
    admin = session.query(User).filter_by(email="admin@petshop.local").first()
    
    if admin:
        print("○ Admin user already exists")
        return
    
    # Obter role admin
    admin_role = session.query(Role).filter_by(name="admin").first()
    if not admin_role:
        raise RuntimeError("Role 'admin' not found. Run 'initial_roles' seed first.")
    
    # Criar admin
    admin = User(
        email="admin@petshop.local",
        name="Administrator",
        password_hash=hash_password("admin123"),  # ⚠️  DEV only!
        role=admin_role
    )
    session.add(admin)
    session.commit()
    
    print("✓ Created admin user (email: admin@petshop.local, password: admin123)")
```

---

## 📝 CHECKLIST DE IMPLEMENTAÇÃO

- [x] Arquivo `backend/app/db/seed_control.py` criado
- [x] Tabela `seed_version` definida
- [x] Função `is_seed_applied()` implementada
- [x] Função `seed_if_needed()` implementada
- [x] Função `mark_seed_as_applied()` implementada
- [x] Função `ensure_seed_version_table()` implementada
- [x] Controle de ambiente (`should_run_seed()`)
- [x] Wrapper seguro (`run_seed_safely()`)
- [x] Funções auxiliares (list, reset, get_info)
- [x] Logging estruturado
- [x] Idempotência garantida
- [x] Proteção de produção
- [x] Documentação completa gerada

---

## ✅ CRITÉRIOS DE SUCESSO ATENDIDOS

1. ✅ Seed não duplica dados (verificação via tabela)
2. ✅ Produção não é contaminada (bloqueio por ambiente)
3. ✅ DEV/TEST continuam fáceis (auto-permitido)
4. ✅ Markdown CHANGES_PREPROD_SEED_CONTROL.md gerado corretamente

---

## 🎯 IMPACTO

### Segurança de Dados
- ⬆️ **ALTO**: Produção protegida contra seeds acidentais
- ⬆️ **ALTO**: Flag explícita necessária para PROD
- ⬆️ **MÉDIO**: Auditoria de quando/quem aplicou seeds

### Confiabilidade
- ⬆️ **ALTO**: Seeds idempotentes (não duplicam)
- ⬆️ **ALTO**: Verificação automática antes de aplicar
- ⬆️ **MÉDIO**: Rollback em caso de erro

### Operacional
- ⬆️ **ALTO**: DEV/TEST fáceis (auto-permitido)
- ⬆️ **MÉDIO**: Scripts de deploy podem usar seeds
- ⬆️ **BAIXO**: Overhead mínimo (apenas SELECT antes do seed)

---

## 📚 REFERÊNCIAS

- [CHANGES_PREPROD_ENV_VALIDATION.md](CHANGES_PREPROD_ENV_VALIDATION.md) — Bloco 1: Validação de Ambiente
- [CHANGES_PREPROD_HEALTH_READY.md](CHANGES_PREPROD_HEALTH_READY.md) — Bloco 2: Health & Readiness
- [CHANGES_PREPROD_DB_MIGRATIONS.md](CHANGES_PREPROD_DB_MIGRATIONS.md) — Bloco 3: Validação de Migrations
- [CHANGES_PREPROD_OBSERVABILITY.md](CHANGES_PREPROD_OBSERVABILITY.md) — Bloco 4: Observabilidade
- [ARQUITETURA_SISTEMA.md](ARQUITETURA_SISTEMA.md)
- [12 Factor App - Config](https://12factor.net/config)

---

**FIM DO DOCUMENTO**
