#!/bin/sh
# =============================================================================
# BACKUP SCRIPT - PostgreSQL Database Backup
# =============================================================================
# Script para backup manual do banco de dados PostgreSQL
# Uso: ./backup.sh [nome_do_backup]
# =============================================================================

set -e

# Configurações
BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="${1:-backup_${TIMESTAMP}}"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "${YELLOW}=====================================${NC}"
echo "${YELLOW}PostgreSQL Backup Script${NC}"
echo "${YELLOW}=====================================${NC}"

# Verificar variáveis de ambiente
if [ -z "$POSTGRES_USER" ] || [ -z "$POSTGRES_DB" ]; then
    echo "${RED}ERROR: POSTGRES_USER ou POSTGRES_DB não definidos${NC}"
    exit 1
fi

echo "${GREEN}Database:${NC} $POSTGRES_DB"
echo "${GREEN}User:${NC} $POSTGRES_USER"
echo "${GREEN}Backup name:${NC} $BACKUP_NAME"
echo ""

# Criar diretório de backup se não existir
mkdir -p "$BACKUP_DIR"

# Executar backup
echo "${YELLOW}[1/3] Executing pg_dump...${NC}"
pg_dump -h postgres -U "$POSTGRES_USER" -d "$POSTGRES_DB" -F c -f "$BACKUP_DIR/${BACKUP_NAME}.dump"

if [ $? -eq 0 ]; then
    echo "${GREEN}✓ Dump completed successfully${NC}"
else
    echo "${RED}✗ ERROR: Dump failed${NC}"
    exit 1
fi

# Comprimir backup
echo "${YELLOW}[2/3] Compressing backup...${NC}"
gzip "$BACKUP_DIR/${BACKUP_NAME}.dump"

if [ $? -eq 0 ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_DIR/${BACKUP_NAME}.dump.gz" | cut -f1)
    echo "${GREEN}✓ Compressed: ${BACKUP_SIZE}${NC}"
else
    echo "${RED}✗ ERROR: Compression failed${NC}"
    exit 1
fi

# Limpar backups antigos (opcional)
if [ ! -z "$BACKUP_RETENTION_DAYS" ]; then
    echo "${YELLOW}[3/3] Cleaning old backups (retention: ${BACKUP_RETENTION_DAYS} days)...${NC}"
    DELETED=$(find "$BACKUP_DIR" -name "backup_*.dump.gz" -mtime +${BACKUP_RETENTION_DAYS} -delete -print | wc -l)
    echo "${GREEN}✓ Deleted ${DELETED} old backup(s)${NC}"
else
    echo "${YELLOW}[3/3] Skipping cleanup (BACKUP_RETENTION_DAYS not set)${NC}"
fi

echo ""
echo "${GREEN}=====================================${NC}"
echo "${GREEN}Backup completed successfully!${NC}"
echo "${GREEN}File: ${BACKUP_DIR}/${BACKUP_NAME}.dump.gz${NC}"
echo "${GREEN}=====================================${NC}"
