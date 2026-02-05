#!/bin/sh
# =============================================================================
# RESTORE SCRIPT - PostgreSQL Database Restore
# =============================================================================
# Script para restaurar backup do banco de dados PostgreSQL
# Uso: ./restore.sh <arquivo_backup.dump.gz>
# =============================================================================

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

BACKUP_FILE="$1"

# Validações
if [ -z "$BACKUP_FILE" ]; then
    echo "${RED}ERROR: Backup file not specified${NC}"
    echo "Usage: $0 <backup_file.dump.gz>"
    echo ""
    echo "Available backups:"
    ls -lh /backups/*.dump.gz 2>/dev/null || echo "  No backups found in /backups/"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "${RED}ERROR: File not found: $BACKUP_FILE${NC}"
    exit 1
fi

echo "${YELLOW}=====================================${NC}"
echo "${YELLOW}PostgreSQL Restore Script${NC}"
echo "${YELLOW}=====================================${NC}"
echo "${RED}⚠️  WARNING: This will OVERWRITE the current database!${NC}"
echo ""
echo "${GREEN}Database:${NC} $POSTGRES_DB"
echo "${GREEN}Backup file:${NC} $BACKUP_FILE"
echo ""
read -p "Continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "${YELLOW}Restore cancelled${NC}"
    exit 0
fi

# Descomprimir se for .gz
DUMP_FILE="$BACKUP_FILE"
if [[ "$BACKUP_FILE" == *.gz ]]; then
    echo "${YELLOW}[1/4] Decompressing backup...${NC}"
    gunzip -c "$BACKUP_FILE" > /tmp/restore.dump
    DUMP_FILE="/tmp/restore.dump"
    echo "${GREEN}✓ Decompressed${NC}"
fi

# Dropar conexões ativas
echo "${YELLOW}[2/4] Terminating active connections...${NC}"
psql -h postgres -U "$POSTGRES_USER" -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$POSTGRES_DB' AND pid <> pg_backend_pid();" > /dev/null 2>&1
echo "${GREEN}✓ Connections terminated${NC}"

# Dropar e recriar database
echo "${YELLOW}[3/4] Recreating database...${NC}"
psql -h postgres -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE IF EXISTS $POSTGRES_DB;"
psql -h postgres -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE $POSTGRES_DB;"
echo "${GREEN}✓ Database recreated${NC}"

# Restaurar backup
echo "${YELLOW}[4/4] Restoring backup...${NC}"
pg_restore -h postgres -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --role="$POSTGRES_USER" "$DUMP_FILE"

if [ $? -eq 0 ]; then
    echo "${GREEN}✓ Restore completed successfully${NC}"
else
    echo "${RED}✗ ERROR: Restore failed (some warnings may be normal)${NC}"
fi

# Limpar arquivo temporário
if [[ "$BACKUP_FILE" == *.gz ]]; then
    rm -f /tmp/restore.dump
fi

echo ""
echo "${GREEN}=====================================${NC}"
echo "${GREEN}Restore completed!${NC}"
echo "${GREEN}=====================================${NC}"
