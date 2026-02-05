# ⚠️ IMPORTANTE: BANCO DE DADOS

## 📦 Qual banco o sistema usa?

**O banco de dados REAL é:** `petshop.db`

Configurado em: `backend/app/config.py` (linha 88)
```python
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "petshop.db")
```

**Como confirmar:** Ao iniciar o backend, ele mostra:
```
💾 Banco SQLite: petshop.db
   Tamanho: 0.70 MB
```

---

## 🚫 NÃO USAR `db.sqlite3`

O arquivo `db.sqlite3` **NÃO É USADO** pelo sistema!

### Por que essa confusão?
- Alguns exemplos e tutoriais usam `db.sqlite3`
- Scripts de migração antigos referenciam `db.sqlite3`
- Mas o sistema está configurado para usar `petshop.db`

---

## ✅ Como trabalhar com o banco correto

### 1. Backups
```powershell
Copy-Item petshop.db "petshop_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').db"
```

### 2. Migrações
Sempre use `petshop.db` nos scripts:
```python
DB_PATH = "petshop.db"  # ✅ CORRETO
# DB_PATH = "db.sqlite3"  # ❌ ERRADO
```

### 3. Verificar arquivo
```powershell
# Ver tamanho e data do banco real
Get-Item petshop.db | Select-Object Name, Length, LastWriteTime
```

### 4. Resetar banco (cuidado!)
```powershell
# Fazer backup antes!
Copy-Item petshop.db "petshop_backup.db"
Remove-Item petshop.db -Force
# Sistema recriará automaticamente ao iniciar
```

---

## 🔧 Como mudar o nome do banco

Se quiser usar `db.sqlite3`, edite `config.py`:

```python
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "db.sqlite3")  # Mudar aqui
```

Ou defina variável de ambiente:
```powershell
$env:SQLITE_DB_PATH = "db.sqlite3"
```

---

## 📋 Checklist antes de qualquer operação no banco

- [ ] Verificar qual banco está configurado em `config.py`
- [ ] Confirmar que o arquivo existe: `Test-Path petshop.db`
- [ ] Fazer backup antes de operações destrutivas
- [ ] Testar migração em cópia do banco primeiro
- [ ] Verificar tamanho do arquivo após operação

---

**Última atualização:** 09/01/2026  
**Motivo:** Confusão entre db.sqlite3 (não usado) e petshop.db (usado realmente)
