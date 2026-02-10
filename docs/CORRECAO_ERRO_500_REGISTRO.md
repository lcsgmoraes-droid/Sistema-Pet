# Correção do Erro 500 no Registro de Usuários

**Data:** 09/02/2026  
**Status:** ✅ RESOLVIDO

## Problema

Erro 500 (Internal Server Error) ao tentar registrar um novo usuário através do endpoint `/auth/register`.

### Mensagem de Erro
```
sqlalchemy.exc.IntegrityError: (psycopg2.errors.UniqueViolation) 
duplicate key value violates unique constraint "users_pkey"
DETAIL: Key (id)=(6) already exists.
```

## Causa Raiz

As **sequences do PostgreSQL** estavam dessincronizadas com os dados reais das tabelas. Isso ocorre quando:
1. Registros são inseridos manualmente com IDs específicos
2. Dados são importados sem atualizar as sequences
3. O sistema foi restaurado de um backup sem sincronizar sequences

## Solução Implementada

### 1. Correção Imediata
Resetamos as sequences das tabelas principais:

```sql
SELECT setval('users_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM users), false);
SELECT setval('roles_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM roles), false);
SELECT setval('user_tenants_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM user_tenants), false);
```

### 2. Script de Manutenção
Criado script `backend/scripts/reset_sequences.sql` que:
- Reseta TODAS as sequences do banco
- Pode ser executado em caso de problemas futuros
- Inclui VACUUM ANALYZE para otimização

### 3. Arquivo Batch para Facilitar
Criado `RESETAR_SEQUENCES.bat` na raiz do projeto:
- Executa automaticamente o script SQL
- Útil para desenvolvedores Windows
- Pode ser executado com duplo clique

## Como Usar

### Se o erro 500 aparecer novamente:

**Opção 1 - Windows (Fácil):**
```bash
# Da raiz do projeto
.\RESETAR_SEQUENCES.bat
```

**Opção 2 - PowerShell:**
```powershell
Get-Content "backend\scripts\reset_sequences.sql" | docker exec -i petshop-dev-postgres psql -U postgres -d petshop_dev
```

**Opção 3 - Manual (uma tabela específica):**
```powershell
docker exec -i petshop-dev-postgres psql -U postgres -d petshop_dev -c "SELECT setval('users_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM users), false);"
```

## Prevenção

### Boas Práticas:
1. **Nunca** inserir registros com IDs manuais em produção
2. Após importações de dados, sempre resetar sequences
3. Ao restaurar backups, executar o script de reset de sequences
4. Usar IDENTITY(ALWAYS=TRUE) nas colunas ID (já implementado)

### Monitoramento:
Verificar sequences dessincronizadas:
```sql
SELECT 
    schemaname,
    sequencename,
    last_value
FROM pg_sequences
WHERE schemaname = 'public'
ORDER BY sequencename;
```

## Testes Realizados

✅ Registro de novo usuário com email único  
✅ Criação automática de tenant  
✅ Criação automática de role "Administrador"  
✅ Vínculo usuário-tenant-role  
✅ Geração de access token  
✅ Retorno correto dos dados do usuário e tenant  

## Resultado

**Antes:** HTTP 500 - Duplicate key error  
**Depois:** HTTP 200 - Registro criado com sucesso

### Exemplo de Resposta Bem-Sucedida:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 8,
    "name": "Usuario Teste Final",
    "email": "teste.final@test.com",
    "is_active": true
  },
  "tenants": [
    {
      "id": "9a644b12-823d-4a97-a6f9-860a3a21be84",
      "name": "Pet Shop Teste",
      "role_id": 4
    }
  ]
}
```

## Arquivos Criados/Modificados

| Arquivo | Tipo | Descrição |
|---------|------|-----------|
| `backend/scripts/reset_sequences.sql` | SQL | Script para resetar todas sequences |
| `RESETAR_SEQUENCES.bat` | Batch | Atalho Windows para executar script |

## Observações

- O problema não era no código do endpoint de registro
- O endpoint estava funcionando corretamente
- Era apenas uma questão de sincronização de sequences
- Solução já testada e confirmada funcionando
