# 🚀 GUIA RÁPIDO - POSTGRESQL

## ✅ Como Usar o Banco Corretamente

### Em Rotas/Endpoints
```python
from fastapi import Depends
from sqlalchemy.orm import Session
from app.db import get_session

@router.get("/exemplo")
def meu_endpoint(db: Session = Depends(get_session)):
    # db já está conectado ao PostgreSQL
    resultado = db.query(MeuModel).all()
    return resultado
```

### Em Scripts/Seeds
```python
from app.db import SessionLocal

def main():
    db = SessionLocal()
    try:
        # Suas operações
        novo_registro = MeuModel(nome="Teste")
        db.add(novo_registro)
        db.commit()
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
```

### Queries Raw SQL (se necessário)
```python
from sqlalchemy import text
from app.db import SessionLocal

db = SessionLocal()
result = db.execute(text("SELECT * FROM tabela WHERE id = :id"), {"id": 123})
rows = result.fetchall()
```

## ❌ O Que NÃO Fazer

```python
# ❌ NUNCA criar conexão SQLite
import sqlite3
conn = sqlite3.connect('petshop.db')  # ERRADO!

# ❌ NUNCA criar engine própria
from sqlalchemy import create_engine
engine = create_engine("sqlite:///./petshop.db")  # ERRADO!

# ❌ NUNCA usar get_db_connection()
from app.db import get_db_connection
conn = get_db_connection()  # ERRADO! Está bloqueada
```

## 🔧 Migrations com Alembic

```bash
# Criar nova migration
cd backend
alembic revision --autogenerate -m "descrição da mudança"

# Aplicar migrations
alembic upgrade head

# Reverter última migration
alembic downgrade -1

# Ver histórico
alembic history
```

## 🗄️ Conexão PostgreSQL

**Local (Desenvolvimento)**
```
Host: localhost
Port: 5432
Database: petshop_db
User: petshop_user
Password: petshop_password_2026
```

**Docker Compose**
```
Host: postgres  (nome do serviço)
Port: 5432
Database: petshop_db
User: petshop_user
Password: petshop_password_2026
```

## 🔍 Verificar Uso Correto

```bash
# Executar verificador
python backend/verificar_uso_sqlite.py

# Retorno esperado:
# ✅ Nenhum uso de SQLite detectado!
```

## 📚 Documentação Completa

- `_LEGADO_SQLITE_README.md` - Lista de arquivos legados
- `_RELATORIO_AUDITORIA_POSTGRESQL.md` - Relatório completo da auditoria

## 🆘 Problemas Comuns

### "ModuleNotFoundError: No module named 'psycopg2'"
```bash
pip install psycopg2-binary
```

### "connection refused" ao conectar PostgreSQL
```bash
# Iniciar PostgreSQL via Docker
docker-compose up -d postgres

# Verificar se está rodando
docker ps | grep postgres
```

### Migrations não aplicam
```bash
# Verificar estado atual
alembic current

# Forçar upgrade
alembic upgrade head

# Se necessário, marcar como aplicada
alembic stamp head
```

---
**Dúvidas?** Consulte `_LEGADO_SQLITE_README.md`
