# 🗄️ BACKUP & RESTORE RUNBOOK

**Sistema:** Pet Shop Management System  
**Banco de Dados:** PostgreSQL 15  
**Última Atualização:** 2026-02-05  
**Responsável:** Operações / DevOps  
**Criticidade:** P0 (Crítico)

---

## 📋 ÍNDICE

1. [Backup](#-backup)
2. [Restore](#-restore)
3. [Teste de Restore](#-teste-de-restore)
4. [Automação](#-automação)
5. [Segurança](#-segurança)
6. [Troubleshooting](#-troubleshooting)
7. [Contatos de Emergência](#-contatos-de-emergência)

---

## 💾 BACKUP

### Ferramenta Utilizada

**pg_dump** — Ferramenta oficial do PostgreSQL para backups lógicos

**Vantagens:**
- ✅ Portável entre versões do PostgreSQL
- ✅ Backup consistente sem lock de tabelas
- ✅ Formato customizado permite restore seletivo
- ✅ Compressão nativa
- ✅ Multi-tenant friendly (pode backupear schemas específicos)

**Desvantagens:**
- ⚠️ Não captura configurações do servidor PostgreSQL
- ⚠️ Requer mais espaço em disco para bancos grandes

---

### 📦 Tipos de Backup

#### 1. Backup Completo (Full Backup)

```bash
# Comando para backup completo do banco
pg_dump \
  -h localhost \
  -p 5432 \
  -U postgres \
  -d petshop_db \
  -F c \
  -b \
  -v \
  -f "/backups/petshop_db_$(date +%Y%m%d_%H%M%S).dump"
```

**Parâmetros:**
- `-h` : Host do PostgreSQL
- `-p` : Porta (padrão 5432)
- `-U` : Usuário do banco
- `-d` : Nome do banco de dados
- `-F c` : Formato custom (compactado e flexível)
- `-b` : Inclui large objects (BLOBs)
- `-v` : Modo verbose (logs detalhados)
- `-f` : Arquivo de saída

**Saída esperada:**
```
pg_dump: last built-in OID is 16383
pg_dump: reading extensions
pg_dump: identifying extension members
pg_dump: reading schemas
pg_dump: reading user-defined tables
pg_dump: reading user-defined functions
...
pg_dump: dumping contents of table public.usuarios
pg_dump: dumping contents of table public.vendas
pg_dump: dumping contents of table public.produtos
```

**Tamanho esperado:** ~500MB para 100k vendas (sem compressão externa)

---

#### 2. Backup Somente Schema

```bash
# Backup apenas da estrutura (sem dados)
pg_dump \
  -h localhost \
  -p 5432 \
  -U postgres \
  -d petshop_db \
  -s \
  -F c \
  -f "/backups/schema_only_$(date +%Y%m%d_%H%M%S).dump"
```

**Uso:** Ideal para criar ambientes de teste/desenvolvimento

---

#### 3. Backup Somente Dados

```bash
# Backup apenas dos dados (sem schema)
pg_dump \
  -h localhost \
  -p 5432 \
  -U postgres \
  -d petshop_db \
  -a \
  -F c \
  -f "/backups/data_only_$(date +%Y%m%d_%H%M%S).dump"
```

**Uso:** Quando apenas dados mudaram, não a estrutura

---

#### 4. Backup de Tabela Específica

```bash
# Backup de uma tabela crítica
pg_dump \
  -h localhost \
  -p 5432 \
  -U postgres \
  -d petshop_db \
  -t vendas \
  -F c \
  -f "/backups/vendas_$(date +%Y%m%d_%H%M%S).dump"
```

**Uso:** Backup pré-operação crítica em tabela específica

---

#### 5. Backup Multi-Tenant (Por Tenant)

```bash
# Backup de um tenant específico
# (assumindo tenant_id = 10)
pg_dump \
  -h localhost \
  -p 5432 \
  -U postgres \
  -d petshop_db \
  -t 'public.*' \
  --exclude-table='*_tenant_*' \
  -F c \
  -f "/backups/tenant_10_$(date +%Y%m%d_%H%M%S).dump"

# Depois extrair dados do tenant via WHERE
# (Requer script customizado com COPY)
```

⚠️ **Nota:** Backup por tenant requer estratégia customizada se os dados não estão em schemas separados.

---

### ⏰ Frequência Recomendada

| Tipo de Backup | Frequência | Retenção | Horário |
|----------------|------------|----------|---------|
| **Full Backup** | Diário | 30 dias | 02:00 AM |
| **Incremental** | A cada 6h | 7 dias | 08:00, 14:00, 20:00 |
| **Schema Only** | Pós-deploy | Permanente | On-demand |
| **Pré-Operação** | Antes de operações críticas | 7 dias | On-demand |

**Justificativa:**
- **02:00 AM:** Menor carga de usuários
- **30 dias:** Compliance e recuperação de incidentes
- **Incremental:** WAL archiving (Point-in-Time Recovery)

---

### 📁 Armazenamento

#### Locais de Armazenamento

```
Primário (Disco Local):
📁 /backups/postgresql/
   ├── daily/
   │   ├── petshop_db_20260205_020000.dump      (2.3 GB)
   │   ├── petshop_db_20260204_020000.dump      (2.1 GB)
   │   └── ...
   ├── hourly/
   │   ├── petshop_db_20260205_080000.dump      (2.3 GB)
   │   └── ...
   └── schema/
       └── schema_only_20260201_100000.dump     (5 MB)

Secundário (Cloud Storage):
☁️ AWS S3: s3://petshop-backups-prod/postgresql/
   ├── daily/
   └── monthly/

Terciário (Offsite):
💾 Tape Backup / Cold Storage
   └── Retenção: 7 anos (compliance)
```

#### Capacidade de Armazenamento

| Local | Capacidade | Uso Atual | Disponível |
|-------|------------|-----------|------------|
| Disco Local | 500 GB | 180 GB | 320 GB |
| AWS S3 | Ilimitado | 2.5 TB | Ilimitado |
| Tape | 10 TB | 5 TB | 5 TB |

**Alerta:** Quando uso local > 80% (400 GB), limpar backups antigos.

---

### 🔄 Retenção

```bash
# Política de retenção
Daily Backups:   30 dias (depois deletar)
Weekly Backups:  3 meses (domingo de cada semana)
Monthly Backups: 2 anos (dia 1º de cada mês)
Yearly Backups:  7 anos (compliance fiscal)
```

**Script de limpeza:**
```bash
#!/bin/bash
# cleanup_old_backups.sh

BACKUP_DIR="/backups/postgresql/daily"
RETENTION_DAYS=30

# Deletar backups com mais de 30 dias
find "$BACKUP_DIR" -name "*.dump" -mtime +$RETENTION_DAYS -delete

echo "✅ Old backups cleaned (retention: ${RETENTION_DAYS} days)"
```

---

### 🐳 Backup em Ambiente Docker

#### Backup do Container PostgreSQL

```bash
# Método 1: Exec no container
docker exec -t postgres_container \
  pg_dump -U postgres -d petshop_db -F c \
  > /backups/petshop_db_$(date +%Y%m%d_%H%M%S).dump

# Método 2: Via docker-compose
docker-compose exec -T db \
  pg_dump -U postgres -d petshop_db -F c \
  > /backups/petshop_db_$(date +%Y%m%d_%H%M%S).dump

# Método 3: Com volume montado
docker run --rm \
  --network sistema-pet_default \
  -v /backups:/backups \
  postgres:15 \
  pg_dump -h db -U postgres -d petshop_db -F c \
  -f /backups/petshop_db_$(date +%Y%m%d_%H%M%S).dump
```

**Recomendação:** Usar Método 3 para não depender do container principal.

---

### ✅ Validação do Backup

```bash
# 1. Verificar se arquivo foi criado
ls -lh /backups/petshop_db_*.dump

# 2. Verificar integridade do backup
pg_restore --list /backups/petshop_db_20260205_020000.dump | head -20

# Saída esperada:
# ;
# ; Archive created at 2026-02-05 02:00:00 -03
# ;     dbname: petshop_db
# ;     TOC Entries: 345
# ;     Compression: -1
# ;     Dump Version: 1.14-0
# ;     Format: CUSTOM
# ;     Integer: 4 bytes
# ;     Offset: 8 bytes
# ;     Dumped from database version: 15.4
# ;     Dumped by pg_dump version: 15.4

# 3. Verificar tamanho (deve ser > 0)
SIZE=$(stat -c%s "/backups/petshop_db_20260205_020000.dump")
if [ $SIZE -gt 1048576 ]; then
  echo "✅ Backup OK: $SIZE bytes"
else
  echo "❌ Backup suspeito: muito pequeno ($SIZE bytes)"
fi

# 4. Calcular checksum (para verificar corrupção)
sha256sum /backups/petshop_db_20260205_020000.dump > /backups/petshop_db_20260205_020000.dump.sha256
```

---

## 🔄 RESTORE

### ⚠️ PRÉ-REQUISITOS

Antes de fazer restore:

1. ✅ **Backup válido:** Verificar integridade do arquivo
2. ✅ **Espaço em disco:** Mínimo 2x o tamanho do backup
3. ✅ **PostgreSQL rodando:** Serviço ativo e acessível
4. ✅ **Permissões:** Usuário com privilégio CREATEDB
5. ✅ **Tempo de manutenção:** Janela agendada (downtime)
6. ✅ **Comunicação:** Stakeholders notificados
7. ✅ **Conexões encerradas:** Nenhum usuário conectado

---

### 🚨 CONEXÕES ATIVAS

**O que acontece com conexões ativas durante restore?**

❌ **Problema:** Restore FALHA se há conexões ativas no banco:
```
pg_restore: error: could not execute query: ERROR:  database "petshop_db" is being accessed by other users
```

✅ **Solução:** Encerrar todas as conexões antes de restore:

```sql
-- 1. Verificar conexões ativas
SELECT pid, usename, application_name, state, query_start
FROM pg_stat_activity
WHERE datname = 'petshop_db';

-- 2. Bloquear novas conexões
UPDATE pg_database SET datallowconn = false WHERE datname = 'petshop_db';

-- 3. Encerrar conexões existentes
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'petshop_db' AND pid <> pg_backend_pid();

-- 4. Confirmar que não há conexões
SELECT COUNT(*) FROM pg_stat_activity WHERE datname = 'petshop_db';
-- Deve retornar 0
```

---

### 📥 Restore Completo

#### Cenário 1: Restore em Banco NOVO

```bash
# 1. Criar banco novo (vazio)
createdb -h localhost -U postgres petshop_db_restored

# 2. Restaurar backup
pg_restore \
  -h localhost \
  -p 5432 \
  -U postgres \
  -d petshop_db_restored \
  -v \
  -j 4 \
  /backups/petshop_db_20260205_020000.dump

# Parâmetros:
# -v : Verbose (logs detalhados)
# -j 4 : Parallel restore (4 jobs) - ACELERA MUITO
# -d : Database de destino

# Saída esperada:
# pg_restore: connecting to database for restore
# pg_restore: creating SCHEMA "public"
# pg_restore: creating TABLE "public.usuarios"
# pg_restore: creating TABLE "public.vendas"
# ...
# pg_restore: processing data for table "public.usuarios"
# pg_restore: processing data for table "public.vendas"
```

**Tempo esperado:** 
- 10 GB: ~15 minutos (com -j 4)
- 100 GB: ~2-3 horas (com -j 8)

---

#### Cenário 2: Restore SOBRE Banco Existente (SOBRESCREVER)

⚠️ **CUIDADO:** Isso deleta o banco atual!

```bash
# 1. Backup de segurança do banco atual
pg_dump -h localhost -U postgres -d petshop_db -F c -f /backups/pre_restore_backup_$(date +%Y%m%d_%H%M%S).dump

# 2. Encerrar conexões (SQL acima)

# 3. Dropar banco
dropdb -h localhost -U postgres petshop_db

# 4. Recriar banco
createdb -h localhost -U postgres petshop_db

# 5. Restaurar backup
pg_restore \
  -h localhost \
  -U postgres \
  -d petshop_db \
  -v \
  -j 4 \
  /backups/petshop_db_20260205_020000.dump

# 6. Verificar (ver seção Validação)
```

---

#### Cenário 3: Restore Apenas de Tabela Específica

```bash
# 1. Listar conteúdo do backup
pg_restore --list /backups/petshop_db_20260205_020000.dump | grep "TABLE DATA"

# Saída:
# 3245; 1259 16384 TABLE DATA public vendas postgres
# 3246; 1259 16385 TABLE DATA public usuarios postgres

# 2. Restaurar apenas tabela "vendas"
pg_restore \
  -h localhost \
  -U postgres \
  -d petshop_db \
  -t vendas \
  -v \
  /backups/petshop_db_20260205_020000.dump

# ⚠️ CUIDADO: Isso ADICIONA dados, não substitui!
# Para substituir, truncar tabela antes:
# TRUNCATE TABLE vendas CASCADE;
```

---

#### Cenário 4: Restore Somente Schema

```bash
# Restaurar apenas estrutura (sem dados)
pg_restore \
  -h localhost \
  -U postgres \
  -d petshop_db_new \
  -s \
  -v \
  /backups/petshop_db_20260205_020000.dump
```

**Uso:** Criar ambiente de teste com estrutura identica à produção.

---

#### Cenário 5: Restore em Docker

```bash
# Método 1: Restore direto no container
docker exec -i postgres_container \
  pg_restore -U postgres -d petshop_db -v -j 4 \
  < /backups/petshop_db_20260205_020000.dump

# Método 2: Via docker-compose
docker-compose exec -T db \
  pg_restore -U postgres -d petshop_db -v \
  < /backups/petshop_db_20260205_020000.dump

# Método 3: Com volume montado (recomendado)
docker run --rm \
  --network sistema-pet_default \
  -v /backups:/backups \
  postgres:15 \
  pg_restore -h db -U postgres -d petshop_db -v -j 4 \
  /backups/petshop_db_20260205_020000.dump
```

---

### ⏱️ RTO (Recovery Time Objective)

**RTO Esperado:**

| Tamanho do Banco | Restore (sem -j) | Restore (com -j 4) | Validação | RTO Total |
|------------------|------------------|---------------------|-----------|-----------|
| 1 GB | 5 min | 2 min | 2 min | **4 min** |
| 10 GB | 30 min | 15 min | 5 min | **20 min** |
| 100 GB | 5 horas | 2.5 horas | 30 min | **3 horas** |
| 1 TB | 2 dias | 1 dia | 2 horas | **~26 horas** |

**Fatores que afetam RTO:**
- Velocidade do disco (SSD vs HDD)
- Paralelização (-j flag)
- Carga do servidor
- Índices e constraints (recriam após dados)

---

### ✅ Validação do Restore

Após restore, SEMPRE executar:

```bash
# 1. Conectar no banco
psql -h localhost -U postgres -d petshop_db_restored

# 2. Verificar tabelas
\dt
# Deve listar todas as tabelas esperadas

# 3. Contar registros críticos
SELECT COUNT(*) FROM vendas;
SELECT COUNT(*) FROM usuarios;
SELECT COUNT(*) FROM produtos;

# Comparar com backup original:
# - Vendas esperadas: ~50.000
# - Usuários esperados: ~1.200
# - Produtos esperados: ~800

# 4. Verificar integridade referencial
SELECT conname, conrelid::regclass, confrelid::regclass
FROM pg_constraint
WHERE contype = 'f';  -- Foreign keys
# Todas as FKs devem estar presentes

# 5. Verificar índices
SELECT schemaname, tablename, indexname
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;

# 6. Verificar última venda (dados recentes)
SELECT MAX(created_at) FROM vendas;
# Deve ser próximo ao horário do backup

# 7. Teste funcional básico
SELECT v.id, u.nome, v.valor_total, v.created_at
FROM vendas v
JOIN usuarios u ON v.usuario_id = u.id
ORDER BY v.created_at DESC
LIMIT 5;
# Deve retornar vendas recentes com dados corretos

# 8. Verificar sequences
SELECT sequencename, last_value
FROM pg_sequences
WHERE schemaname = 'public';
# Valores devem ser coerentes (não resetados)
```

---

## 🧪 TESTE DE RESTORE

### Por que testar restore?

> **"Backup não testado = sem backup"**

**Razões:**
- Backup pode estar corrompido
- Procedimento pode ter mudado
- Equipe pode não saber executar
- Tempo real de restore pode surpreender

---

### 📅 Frequência de Teste

| Tipo de Teste | Frequência | Responsável |
|---------------|------------|-------------|
| Teste completo | Mensal | DevOps + DBA |
| Teste parcial | Semanal | DevOps |
| Validação de integridade | Diário | Automático |

---

### 🔬 Procedimento de Teste de Restore

#### Teste Completo (Mensal)

```bash
#!/bin/bash
# test_restore.sh - Teste mensal de restore

set -e  # Parar em erro

echo "🧪 Iniciando teste de restore..."

# 1. Definir variáveis
BACKUP_FILE="/backups/petshop_db_20260205_020000.dump"
TEST_DB="petshop_db_test_restore"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="/logs/restore_test_${TIMESTAMP}.log"

# 2. Validar backup existe
if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Backup não encontrado: $BACKUP_FILE"
    exit 1
fi

echo "✅ Backup encontrado: $(ls -lh $BACKUP_FILE)"

# 3. Verificar integridade
pg_restore --list "$BACKUP_FILE" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Backup íntegro"
else
    echo "❌ Backup corrompido!"
    exit 1
fi

# 4. Criar banco de teste
echo "🔨 Criando banco de teste: $TEST_DB"
dropdb -h localhost -U postgres --if-exists "$TEST_DB"
createdb -h localhost -U postgres "$TEST_DB"

# 5. Iniciar cronômetro
START_TIME=$(date +%s)

# 6. Restaurar backup
echo "🔄 Restaurando backup..."
pg_restore \
  -h localhost \
  -U postgres \
  -d "$TEST_DB" \
  -v \
  -j 4 \
  "$BACKUP_FILE" > "$LOG_FILE" 2>&1

# 7. Calcular tempo
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
MINUTES=$((DURATION / 60))
SECONDS=$((DURATION % 60))

echo "⏱️  Restore concluído em: ${MINUTES}m ${SECONDS}s"

# 8. Validar dados
echo "🔍 Validando dados..."

# Contar registros
VENDAS_COUNT=$(psql -h localhost -U postgres -d "$TEST_DB" -t -c "SELECT COUNT(*) FROM vendas;")
USUARIOS_COUNT=$(psql -h localhost -U postgres -d "$TEST_DB" -t -c "SELECT COUNT(*) FROM usuarios;")

echo "📊 Registros encontrados:"
echo "   - Vendas: $VENDAS_COUNT"
echo "   - Usuários: $USUARIOS_COUNT"

# 9. Verificar dados recentes
LAST_VENDA=$(psql -h localhost -U postgres -d "$TEST_DB" -t -c "SELECT MAX(created_at) FROM vendas;")
echo "📅 Última venda no backup: $LAST_VENDA"

# 10. Limpar banco de teste
echo "🧹 Limpando banco de teste..."
dropdb -h localhost -U postgres "$TEST_DB"

# 11. Resultado final
echo ""
echo "✅ ====================================="
echo "✅  TESTE DE RESTORE CONCLUÍDO"
echo "✅ ====================================="
echo "📄 Log: $LOG_FILE"
echo "⏱️  RTO: ${MINUTES}m ${SECONDS}s"
echo "📊 Vendas: $VENDAS_COUNT | Usuários: $USUARIOS_COUNT"
echo ""
```

**Executar:**
```bash
chmod +x test_restore.sh
./test_restore.sh
```

---

#### Checklist Pós-Teste

- [ ] Backup foi restaurado sem erros
- [ ] Tempo de restore está dentro do RTO esperado
- [ ] Contagem de registros está correta
- [ ] Dados recentes estão presentes
- [ ] Foreign keys foram criadas
- [ ] Índices foram criados
- [ ] Sequences estão corretas
- [ ] Logs do teste foram salvos
- [ ] Banco de teste foi deletado
- [ ] Resultado foi documentado

---

### 📊 Registro de Testes

```
Data do Teste    | RTO Medido | Registros | Status | Observações
-----------------|------------|-----------|--------|------------------
2026-02-01       | 18m 23s    | 50k vendas| ✅ OK  | -
2026-01-01       | 16m 45s    | 48k vendas| ✅ OK  | -
2025-12-01       | 22m 10s    | 45k vendas| ⚠️ LENTO| Disco cheio (90%)
2025-11-01       | 15m 30s    | 42k vendas| ✅ OK  | -
```

---

### 🚨 Riscos Conhecidos

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| **Backup corrompido** | Baixa | Alto | Validação diária automatizada |
| **Espaço em disco insuficiente** | Média | Alto | Alerta quando > 80% |
| **RTO excede janela de manutenção** | Média | Alto | Teste mensal para prever |
| **Credenciais expiradas** | Baixa | Médio | Rotacionar com antecedência |
| **Versão incompatível do PostgreSQL** | Baixa | Alto | Documentar versão no backup |
| **Dados sensíveis não anonimizados** | Alta | Médio | Anonimizar antes de restore em dev |

---

## 🤖 AUTOMAÇÃO

### Script de Backup Automatizado

```bash
#!/bin/bash
# automated_backup.sh - Backup diário automatizado

set -e

# ===== CONFIGURAÇÕES =====
DB_HOST="localhost"
DB_PORT="5432"
DB_USER="postgres"
DB_NAME="petshop_db"
BACKUP_DIR="/backups/postgresql/daily"
S3_BUCKET="s3://petshop-backups-prod/postgresql/daily"
RETENTION_DAYS=30
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/petshop_db_${TIMESTAMP}.dump"
LOG_FILE="/logs/backup_${TIMESTAMP}.log"

# ===== PRÉ-VALIDAÇÕES =====
echo "🔍 Validando pré-requisitos..." | tee -a "$LOG_FILE"

# Verificar se diretório existe
mkdir -p "$BACKUP_DIR"

# Verificar espaço em disco (mínimo 50GB)
AVAILABLE_SPACE=$(df -BG "$BACKUP_DIR" | awk 'NR==2 {print $4}' | sed 's/G//')
if [ "$AVAILABLE_SPACE" -lt 50 ]; then
    echo "❌ Espaço insuficiente: ${AVAILABLE_SPACE}GB (mínimo: 50GB)" | tee -a "$LOG_FILE"
    exit 1
fi

echo "✅ Espaço disponível: ${AVAILABLE_SPACE}GB" | tee -a "$LOG_FILE"

# ===== BACKUP =====
echo "💾 Iniciando backup..." | tee -a "$LOG_FILE"
START_TIME=$(date +%s)

pg_dump \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  -F c \
  -b \
  -v \
  -f "$BACKUP_FILE" >> "$LOG_FILE" 2>&1

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo "✅ Backup concluído em ${DURATION}s" | tee -a "$LOG_FILE"

# ===== VALIDAÇÃO =====
echo "🔍 Validando backup..." | tee -a "$LOG_FILE"

# Verificar tamanho
SIZE=$(stat -c%s "$BACKUP_FILE")
SIZE_MB=$((SIZE / 1024 / 1024))

if [ "$SIZE" -lt 1048576 ]; then
    echo "❌ Backup suspeito: ${SIZE_MB}MB (muito pequeno)" | tee -a "$LOG_FILE"
    exit 1
fi

echo "✅ Tamanho do backup: ${SIZE_MB}MB" | tee -a "$LOG_FILE"

# Verificar integridade
pg_restore --list "$BACKUP_FILE" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Backup íntegro" | tee -a "$LOG_FILE"
else
    echo "❌ Backup corrompido!" | tee -a "$LOG_FILE"
    exit 1
fi

# Calcular checksum
sha256sum "$BACKUP_FILE" > "${BACKUP_FILE}.sha256"
echo "✅ Checksum gerado" | tee -a "$LOG_FILE"

# ===== UPLOAD PARA S3 =====
echo "☁️  Enviando para S3..." | tee -a "$LOG_FILE"
aws s3 cp "$BACKUP_FILE" "$S3_BUCKET/" >> "$LOG_FILE" 2>&1
aws s3 cp "${BACKUP_FILE}.sha256" "$S3_BUCKET/" >> "$LOG_FILE" 2>&1
echo "✅ Upload concluído" | tee -a "$LOG_FILE"

# ===== LIMPEZA =====
echo "🧹 Limpando backups antigos..." | tee -a "$LOG_FILE"
find "$BACKUP_DIR" -name "*.dump" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "*.sha256" -mtime +$RETENTION_DAYS -delete
echo "✅ Backups antigos removidos (retenção: ${RETENTION_DAYS} dias)" | tee -a "$LOG_FILE"

# ===== NOTIFICAÇÃO =====
echo "📧 Enviando notificação..." | tee -a "$LOG_FILE"

# Slack webhook (exemplo)
curl -X POST https://hooks.slack.com/services/YOUR/WEBHOOK/URL \
  -H 'Content-Type: application/json' \
  -d "{
    \"text\": \"✅ Backup concluído\",
    \"attachments\": [{
      \"color\": \"good\",
      \"fields\": [
        {\"title\": \"Banco\", \"value\": \"$DB_NAME\", \"short\": true},
        {\"title\": \"Tamanho\", \"value\": \"${SIZE_MB}MB\", \"short\": true},
        {\"title\": \"Duração\", \"value\": \"${DURATION}s\", \"short\": true},
        {\"title\": \"Arquivo\", \"value\": \"$BACKUP_FILE\", \"short\": false}
      ]
    }]
  }" >> "$LOG_FILE" 2>&1

echo "✅ ====================================="
echo "✅  BACKUP CONCLUÍDO COM SUCESSO"
echo "✅ ====================================="
echo "📄 Arquivo: $BACKUP_FILE"
echo "📏 Tamanho: ${SIZE_MB}MB"
echo "⏱️  Duração: ${DURATION}s"
echo "📄 Log: $LOG_FILE"
```

---

### Cron Job (Agendamento)

```bash
# Editar crontab
crontab -e

# Backup diário às 02:00 AM
0 2 * * * /scripts/automated_backup.sh >> /logs/cron_backup.log 2>&1

# Backup incremental a cada 6 horas
0 */6 * * * /scripts/incremental_backup.sh >> /logs/cron_incremental.log 2>&1

# Teste de restore mensal (1º dia do mês às 03:00 AM)
0 3 1 * * /scripts/test_restore.sh >> /logs/cron_test_restore.log 2>&1

# Limpeza de backups antigos (diário às 04:00 AM)
0 4 * * * /scripts/cleanup_old_backups.sh >> /logs/cron_cleanup.log 2>&1
```

**Verificar cron:**
```bash
# Listar cron jobs
crontab -l

# Ver logs do cron
tail -f /logs/cron_backup.log
```

---

### Monitoramento

#### Alertas Recomendados

```yaml
# Prometheus + Alertmanager (exemplo)
groups:
  - name: backup_alerts
    rules:
      - alert: BackupFailed
        expr: backup_status{job="postgresql"} == 0
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "Backup do PostgreSQL falhou"
          description: "Último backup falhou há {{ $value }} minutos"

      - alert: BackupTooOld
        expr: (time() - backup_last_success_timestamp{job="postgresql"}) > 86400
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "Backup muito antigo"
          description: "Último backup bem-sucedido há mais de 24h"

      - alert: BackupSizeAnomaly
        expr: abs(backup_size_bytes - avg_over_time(backup_size_bytes[7d])) / avg_over_time(backup_size_bytes[7d]) > 0.5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Tamanho do backup anômalo"
          description: "Tamanho do backup variou mais de 50% em relação à média de 7 dias"

      - alert: DiskSpaceLow
        expr: (node_filesystem_avail_bytes{mountpoint="/backups"} / node_filesystem_size_bytes{mountpoint="/backups"}) < 0.2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Espaço em disco baixo"
          description: "Apenas {{ $value | humanizePercentage }} de espaço disponível em /backups"
```

---

## 🔒 SEGURANÇA

### 🔑 Controle de Acesso

#### Quem tem acesso aos backups?

| Papel | Acesso | Justificativa |
|-------|--------|---------------|
| **DBA** | Leitura + Escrita | Responsável por backups |
| **DevOps Lead** | Leitura + Escrita | Operações de emergência |
| **DevOps** | Leitura | Troubleshooting |
| **Desenvolvedores** | Nenhum | Dados sensíveis |
| **Auditoria** | Leitura (logs apenas) | Compliance |

#### Permissões de Arquivo

```bash
# Definir permissões corretas
chmod 700 /backups/postgresql/
chmod 600 /backups/postgresql/*.dump
chown postgres:postgres /backups/postgresql/*.dump

# Verificar permissões
ls -la /backups/postgresql/
# drwx------ (700) - Apenas dono pode acessar
# -rw------- (600) - Apenas dono pode ler/escrever
```

---

### 🔐 Criptografia

#### Criptografia em Trânsito

```bash
# Backup com SSL/TLS
pg_dump \
  -h production-db.example.com \
  -p 5432 \
  -U postgres \
  -d petshop_db \
  "sslmode=require" \
  -F c \
  -f /backups/petshop_db_encrypted.dump
```

#### Criptografia em Repouso (Disco)

```bash
# Método 1: GPG (GNU Privacy Guard)
pg_dump \
  -h localhost \
  -U postgres \
  -d petshop_db \
  -F c | gpg --encrypt --recipient backup@petshop.com \
  > /backups/petshop_db_$(date +%Y%m%d_%H%M%S).dump.gpg

# Restore com GPG
gpg --decrypt /backups/petshop_db_20260205_020000.dump.gpg | \
  pg_restore -h localhost -U postgres -d petshop_db

# Método 2: OpenSSL
pg_dump \
  -h localhost \
  -U postgres \
  -d petshop_db \
  -F c | openssl enc -aes-256-cbc -salt -pbkdf2 -out /backups/petshop_db_$(date +%Y%m%d_%H%M%S).dump.enc

# Restore com OpenSSL
openssl enc -aes-256-cbc -d -pbkdf2 -in /backups/petshop_db_20260205_020000.dump.enc | \
  pg_restore -h localhost -U postgres -d petshop_db
```

**Recomendação:** Usar GPG para backups em cloud, OpenSSL para backups locais.

---

#### Criptografia no S3

```bash
# Upload com criptografia server-side (SSE-S3)
aws s3 cp /backups/petshop_db_20260205_020000.dump \
  s3://petshop-backups-prod/postgresql/daily/ \
  --sse AES256

# Upload com criptografia KMS
aws s3 cp /backups/petshop_db_20260205_020000.dump \
  s3://petshop-backups-prod/postgresql/daily/ \
  --sse aws:kms \
  --sse-kms-key-id arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012
```

---

### 🔍 Auditoria

#### Log de Acesso aos Backups

```bash
# Habilitar auditd (Linux)
auditctl -w /backups/postgresql/ -p rwxa -k backup_access

# Ver logs de acesso
ausearch -k backup_access

# Exemplo de saída:
# time->2026-02-05 10:30:00
# type=SYSCALL msg=audit(1738764600.123:456): arch=c000003e syscall=2 success=yes exit=3 a0=7fff12345678 a1=0 a2=0 a3=0 items=1 ppid=1234 pid=5678 auid=1000 uid=1000 gid=1000 euid=1000 suid=1000 fsuid=1000 egid=1000 sgid=1000 fsgid=1000 tty=pts0 ses=1 comm="pg_restore" exe="/usr/bin/pg_restore" subj=unconfined_u:unconfined_r:unconfined_t:s0-s0:c0.c1023 key="backup_access"
```

#### Registro de Backups

```sql
-- Tabela de auditoria de backups
CREATE TABLE backup_audit (
    id SERIAL PRIMARY KEY,
    backup_file VARCHAR(255) NOT NULL,
    backup_size_bytes BIGINT,
    backup_started_at TIMESTAMP NOT NULL,
    backup_finished_at TIMESTAMP NOT NULL,
    backup_duration_seconds INTEGER,
    backup_type VARCHAR(50), -- full, incremental, schema, data
    backup_status VARCHAR(20), -- success, failed, corrupted
    backup_location VARCHAR(255), -- local, s3, tape
    performed_by VARCHAR(100),
    restored_at TIMESTAMP,
    restored_by VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Inserir registro de backup
INSERT INTO backup_audit (
    backup_file,
    backup_size_bytes,
    backup_started_at,
    backup_finished_at,
    backup_duration_seconds,
    backup_type,
    backup_status,
    backup_location,
    performed_by
) VALUES (
    '/backups/petshop_db_20260205_020000.dump',
    2147483648, -- 2GB
    '2026-02-05 02:00:00',
    '2026-02-05 02:18:23',
    1103, -- 18m 23s
    'full',
    'success',
    's3://petshop-backups-prod/postgresql/daily/',
    'cron_automated'
);
```

---

### 🛡️ Proteção de Dados Sensíveis

#### Anonimização para Ambientes Não-Produtivos

```sql
-- Script de anonimização pós-restore (dev/test)
-- anonimizar_dados.sql

-- CPFs
UPDATE usuarios SET cpf = '000.000.000-00';

-- Emails
UPDATE usuarios SET email = CONCAT('user_', id, '@example.com');

-- Telefones
UPDATE usuarios SET telefone = '(11) 0000-0000';

-- Senhas (já hasheadas, mas pode resetar)
UPDATE usuarios SET password_hash = '$2b$12$anonimized_hash';

-- Endereços
UPDATE enderecos SET 
    logradouro = 'Rua Exemplo',
    numero = '123',
    complemento = NULL,
    bairro = 'Centro',
    cidade = 'São Paulo',
    estado = 'SP',
    cep = '00000-000';

-- Cartões de crédito (não deveria estar armazenado, mas...)
UPDATE pagamentos SET numero_cartao = NULL, cvv = NULL;

-- Logs sensíveis
TRUNCATE TABLE audit_logs WHERE log_data LIKE '%password%';

-- Confirmar
SELECT 'Anonimização concluída' AS resultado;
```

**Executar após restore em dev/test:**
```bash
# Restore
pg_restore -h localhost -U postgres -d petshop_db_dev /backups/latest.dump

# Anonimizar
psql -h localhost -U postgres -d petshop_db_dev -f scripts/anonimizar_dados.sql
```

---

## 🔧 TROUBLESHOOTING

### Problema 1: Backup falha com "disk full"

**Sintoma:**
```
pg_dump: error: could not write to file: No space left on device
```

**Solução:**
```bash
# 1. Verificar espaço
df -h /backups

# 2. Limpar backups antigos
find /backups -name "*.dump" -mtime +7 -delete

# 3. Mover backups antigos para S3
aws s3 sync /backups/postgresql/daily/ s3://petshop-backups-prod/postgresql/daily/
rm /backups/postgresql/daily/*.dump

# 4. Aumentar partição (se necessário)
sudo lvextend -L +100G /dev/vg0/backups
sudo resize2fs /dev/vg0/backups
```

---

### Problema 2: Restore falha com "role does not exist"

**Sintoma:**
```
pg_restore: error: could not execute query: ERROR:  role "app_user" does not exist
```

**Solução:**
```bash
# Método 1: Restaurar com opção --no-owner
pg_restore \
  -h localhost \
  -U postgres \
  -d petshop_db \
  --no-owner \
  --no-acl \
  /backups/latest.dump

# Método 2: Criar roles antes do restore
CREATE ROLE app_user WITH LOGIN PASSWORD 'senha';
CREATE ROLE readonly WITH LOGIN PASSWORD 'senha';
```

---

### Problema 3: Backup muito lento

**Sintoma:**
Backup demora mais de 2 horas para 10GB.

**Diagnóstico:**
```bash
# 1. Verificar I/O do disco
iostat -x 5

# 2. Verificar carga do PostgreSQL
SELECT * FROM pg_stat_activity;

# 3. Ver queries lentas
SELECT pid, query, state, wait_event, wait_event_type
FROM pg_stat_activity
WHERE state = 'active' AND query NOT LIKE '%pg_stat_activity%';
```

**Soluções:**
```bash
# 1. Usar compressão externa (mais rápido)
pg_dump -h localhost -U postgres -d petshop_db -F p | gzip > backup.sql.gz

# 2. Fazer backup em horário de menor carga
# (ajustar cron para 02:00 AM)

# 3. Usar pg_dump com -j (parallel - apenas custom format)
pg_dump -h localhost -U postgres -d petshop_db -F d -j 4 -f backup_dir/

# 4. Verificar se há queries travadas
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle in transaction' AND state_change < NOW() - INTERVAL '1 hour';
```

---

### Problema 4: Restore falha com "out of memory"

**Sintoma:**
```
pg_restore: error: out of memory
```

**Solução:**
```bash
# 1. Aumentar maintenance_work_mem temporariamente
psql -h localhost -U postgres -d petshop_db
ALTER SYSTEM SET maintenance_work_mem = '2GB';
SELECT pg_reload_conf();

# 2. Restaurar sem índices primeiro, depois criar
pg_restore -h localhost -U postgres -d petshop_db --disable-triggers /backups/latest.dump

# 3. Criar índices separadamente
psql -h localhost -U postgres -d petshop_db
CREATE INDEX CONCURRENTLY idx_vendas_usuario_id ON vendas(usuario_id);
CREATE INDEX CONCURRENTLY idx_vendas_created_at ON vendas(created_at);

# 4. Voltar maintenance_work_mem ao normal
ALTER SYSTEM RESET maintenance_work_mem;
SELECT pg_reload_conf();
```

---

### Problema 5: Backup não contém dados recentes

**Sintoma:**
Última venda no backup é de 2 dias atrás.

**Diagnóstico:**
```bash
# 1. Verificar data de modificação do backup
ls -lh /backups/*.dump

# 2. Ver logs do backup
tail -100 /logs/backup_*.log

# 3. Verificar cron
crontab -l
grep backup /var/log/syslog
```

**Soluções:**
```bash
# 1. Executar backup manualmente
/scripts/automated_backup.sh

# 2. Verificar se cron está rodando
systemctl status cron

# 3. Verificar se script tem permissão de execução
chmod +x /scripts/automated_backup.sh

# 4. Adicionar log de debugging no script
set -x  # No início do script
```

---

## 📞 CONTATOS DE EMERGÊNCIA

### Equipe Responsável

| Papel | Nome | Telefone | Email | Disponibilidade |
|-------|------|----------|-------|-----------------|
| **DBA Principal** | João Silva | (11) 98765-4321 | joao.silva@petshop.com | 24/7 |
| **DevOps Lead** | Maria Santos | (11) 98765-1234 | maria.santos@petshop.com | 24/7 |
| **DevOps** | Pedro Oliveira | (11) 98765-5678 | pedro.oliveira@petshop.com | Seg-Sex 9-18h |
| **Gerente de TI** | Ana Costa | (11) 98765-9999 | ana.costa@petshop.com | Seg-Sex 9-18h |

---

### Procedimento de Escalação

```
Nível 1 (0-15 min):
  ├─ DevOps on-call tenta resolver

Nível 2 (15-30 min):
  ├─ Escalar para DBA Principal
  └─ Notificar DevOps Lead

Nível 3 (30-60 min):
  ├─ Escalar para Gerente de TI
  ├─ Convocar call de emergência
  └─ Considerar acionamento de vendor (AWS, etc)

Nível 4 (60+ min):
  ├─ Escalar para C-level
  ├─ Preparar comunicado para clientes
  └─ Ativar plano de contingência
```

---

### Fornecedores

| Fornecedor | Serviço | Contato | SLA |
|------------|---------|---------|-----|
| **AWS** | S3 Storage | support.aws.com | 1h (Business) |
| **PostgreSQL Inc** | Consultoria | support@postgresql.org | 4h (Enterprise) |
| **Veeam** | Backup Software | +55 11 3000-0000 | 2h |

---

## 📚 REFERÊNCIAS

### Documentação Oficial

- [PostgreSQL Backup & Restore](https://www.postgresql.org/docs/current/backup.html)
- [pg_dump Documentation](https://www.postgresql.org/docs/current/app-pgdump.html)
- [pg_restore Documentation](https://www.postgresql.org/docs/current/app-pgrestore.html)
- [Continuous Archiving (WAL)](https://www.postgresql.org/docs/current/continuous-archiving.html)

### Ferramentas Recomendadas

- **pgBackRest** — Backup avançado com incremental e parallel
- **Barman** — Disaster recovery para PostgreSQL
- **WAL-G** — Archival and restoration tool
- **pg_probackup** — Backup e restore com validação

### Padrões de Mercado

- **RPO (Recovery Point Objective):** < 1 hora
- **RTO (Recovery Time Objective):** < 4 horas
- **Retenção Mínima:** 30 dias
- **Teste de Restore:** Mensal

---

## ✅ CHECKLIST RÁPIDO

### Antes de Produção

- [ ] Backup automatizado configurado (cron)
- [ ] Backup testado (restore bem-sucedido)
- [ ] Retenção configurada (30 dias)
- [ ] Upload para cloud configurado (S3)
- [ ] Monitoramento e alertas ativos
- [ ] Criptografia habilitada
- [ ] Permissões de acesso definidas
- [ ] Runbook revisado pela equipe
- [ ] Contatos de emergência atualizados
- [ ] Procedimento documentado e conhecido

### Durante Emergência

- [ ] Backup mais recente identificado
- [ ] Integridade do backup validada
- [ ] Stakeholders notificados
- [ ] Janela de manutenção agendada
- [ ] Conexões ativas encerradas
- [ ] Banco de dados backed up (antes de restore)
- [ ] Restore executado
- [ ] Dados validados
- [ ] Aplicação testada
- [ ] Usuários notificados (conclusão)
- [ ] Post-mortem agendado

---

## 🔄 MANUTENÇÃO DO RUNBOOK

**Este documento deve ser revisado:**
- Após cada incidente de restore
- Trimestralmente (checklist de atualização)
- Quando houver mudanças de infraestrutura
- Quando houver mudanças de versão do PostgreSQL
- Quando houver mudanças na equipe

**Última Revisão:** 2026-02-05  
**Próxima Revisão:** 2026-05-05  
**Responsável:** DevOps Lead

---

**FIM DO RUNBOOK**

