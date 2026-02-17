# ⚠️ ARQUIVOS LEGADOS - SQLite

## ❌ NÃO UTILIZAR ESTES ARQUIVOS

Os arquivos abaixo são **LEGADOS** e usam SQLite. 
O sistema atual usa **EXCLUSIVAMENTE PostgreSQL**.

### Scripts de Migração SQLite (LEGADOS - NÃO EXECUTAR)

Estes scripts foram usados durante a transição SQLite → PostgreSQL:

- `check_estrutura.py` - ❌ LEGADO
- `check_products.py` - ❌ LEGADO  
- `check_tables.py` - ❌ LEGADO
- `check_dividas.py` - ❌ LEGADO
- `check_teste_produto.py` - ❌ LEGADO
- `fix_comissoes_fk.py` - ❌ LEGADO
- `fix_numero_parcelas.py` - ❌ LEGADO
- `fix_venda_pagamentos.py` - ❌ LEGADO
- `fix_categorias.py` - ❌ LEGADO
- `listar_tabelas_vendas.py` - ❌ LEGADO
- `listar_tabelas_comissoes.py` - ❌ LEGADO
- `listar_usuarios.py` - ❌ LEGADO
- `list_tables.py` - ❌ LEGADO
- `listar_tabelas.py` - ❌ LEGADO
- `inspecionar_db.py` - ❌ LEGADO
- `habilitar_wal.py` - ❌ LEGADO
- `corrigir_movimentacoes_caixa.py` - ❌ LEGADO
- `corrigir_status_vendas.py` - ❌ LEGADO
- `debug_ultima_venda.py` - ❌ LEGADO
- `popular_nfe_numero.py` - ❌ LEGADO
- `testar_demonstrativo_comissoes.py` - ❌ LEGADO
- `test_busca.py` - ❌ LEGADO
- `run_migration_sprint2.py` - ❌ LEGADO

### Migrations SQLite (LEGADOS - NÃO EXECUTAR)

- `migrate_add_acerto_config.py` - ❌ LEGADO
- `migrate_add_cest_notas_entrada.py` - ❌ LEGADO
- `migrate_add_cor.py` - ❌ LEGADO
- `migrate_add_deleted_at.py` - ❌ LEGADO
- `migrate_add_nfe_tipo.py` - ❌ LEGADO
- `migrate_add_nfe.py` - ❌ LEGADO
- `migrate_add_pet_codigo.py` - ❌ LEGADO
- `migrate_add_rastreabilidade_compensacao.py` - ❌ LEGADO
- `migrate_add_caixa_id_vendas.py` - ❌ LEGADO
- `migrate_add_campos_fiscais_xml.py` - ❌ LEGADO
- `migrate_add_numero_parcelas.py` - ❌ LEGADO
- `migrate_add_taxas_parcelas_antecipacao.py` - ❌ LEGADO
- `migrate_add_subcategoria_nome.py` - ❌ LEGADO
- `migrate_contas_bancarias.py` - ❌ LEGADO
- `migrate_create_acertos_tables.py` - ❌ LEGADO
- `migrate_create_email_envios.py` - ❌ LEGADO
- `migrate_comissoes.py` - ❌ LEGADO
- `migrate_venda_itens_pet.py` - ❌ LEGADO
- `migrate_simple.py` - ❌ LEGADO
- `migrate_notas_entrada.py` - ❌ LEGADO (linha 89 usa SQLite)
- `migration_produtos_pai_preco.py` - ❌ LEGADO
- `migration_create_kit_componentes.py` - ❌ LEGADO
- `migration_add_tipo_kit.py` - ❌ LEGADO
- `migration_comissoes_pagamento_parcial.py` - ❌ LEGADO
- `migrar_comissao_parcial.py` - ❌ LEGADO
- `migracao_data_cancelamento.py` - ❌ LEGADO
- `populate_racas.py` - ❌ LEGADO

## ✅ COMO USAR O BANCO CORRETAMENTE

### Para Scripts e Seeds

```python
# ✅ CORRETO - Usa PostgreSQL
from app.db import SessionLocal

def main():
    db = SessionLocal()
    try:
        # Suas operações aqui
        db.commit()
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
```

### ❌ NUNCA FAZER

```python
# ❌ ERRADO - Cria conexão SQLite
import sqlite3
conn = sqlite3.connect('petshop.db')

# ❌ ERRADO - Engine própria
from sqlalchemy import create_engine
engine = create_engine("sqlite:///./petshop.db")
```

## 📝 Migrations

Use **Alembic** para todas as migrations:

```bash
# Criar migration
alembic revision --autogenerate -m "descrição"

# Aplicar migrations
alembic upgrade head
```

## 🗄️ Arquivos de Banco (NÃO USAR)

- `petshop.db` - ❌ SQLite LEGADO
- `sistema.db` - ❌ SQLite LEGADO
- `db.sqlite3` - ❌ SQLite LEGADO

## ✅ Banco Atual

**PostgreSQL** via Docker Compose:
- Host: localhost (local) ou postgres (Docker)
- Port: 5432
- Database: petshop_db
- User: petshop_user
- Password: petshop_password_2026

Configurado em: `backend/.env`
