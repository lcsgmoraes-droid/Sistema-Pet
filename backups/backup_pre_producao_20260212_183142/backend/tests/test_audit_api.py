"""
Testes da API de Auditoria - Fase 5.6
======================================

Validar endpoints read-only de auditoria.
"""

import pytest
from datetime import datetime, timedelta
from fastapi import status
from sqlalchemy.orm import Session
import json

from app.models import AuditLog, User
from app.audit.queries import (
    get_replays,
    get_replay_by_id,
    get_rebuilds,
    get_rebuild_by_id,
    get_audit_summary
)


# =============================
# Fixtures
# =============================

@pytest.fixture
def sample_replay_logs(db: Session):
    """Cria logs de replay de teste"""
    logs = []
    
    # Replay bem-sucedido
    log1 = AuditLog(
        action='replay_start',
        entity_type='event_store',
        details=json.dumps({
            'filters': {
                'event_type': 'VendaCriada',
                'batch_size': 1000
            }
        }),
        timestamp=datetime.now() - timedelta(hours=2)
    )
    db.add(log1)
    
    log2 = AuditLog(
        action='replay_end',
        entity_type='event_store',
        details=json.dumps({
            'stats': {
                'total_events': 150,
                'batches_processed': 1,
                'duration_seconds': 2.5
            }
        }),
        timestamp=datetime.now() - timedelta(hours=1, minutes=59)
    )
    db.add(log2)
    
    # Replay com erro
    log3 = AuditLog(
        action='replay_start',
        entity_type='event_store',
        details=json.dumps({
            'filters': {}
        }),
        timestamp=datetime.now() - timedelta(minutes=30)
    )
    db.add(log3)
    
    log4 = AuditLog(
        action='replay_end',
        entity_type='event_store',
        details=json.dumps({
            'error': 'Database connection lost',
            'stats': {
                'total_events': 0,
                'batches_processed': 0,
                'duration_seconds': 0.1
            }
        }),
        timestamp=datetime.now() - timedelta(minutes=29)
    )
    db.add(log4)
    
    db.commit()
    
    logs = [log1, log2, log3, log4]
    return logs


@pytest.fixture
def sample_rebuild_logs(db: Session):
    """Cria logs de rebuild de teste"""
    logs = []
    
    # Rebuild bem-sucedido
    log1 = AuditLog(
        action='rebuild_start',
        entity_type='read_models',
        details=json.dumps({
            'phase': 'creating_temp_schema'
        }),
        timestamp=datetime.now() - timedelta(hours=3)
    )
    db.add(log1)
    
    log2 = AuditLog(
        action='rebuild_read_models_success',
        entity_type='read_models',
        details=json.dumps({
            'duration_seconds': 45.2,
            'events_processed': 1500,
            'tables_updated': ['vendas_resumo_diario', 'performance_parceiro', 'receita_mensal'],
            'phase_reached': 'completed'
        }),
        timestamp=datetime.now() - timedelta(hours=2, minutes=59)
    )
    db.add(log2)
    
    log3 = AuditLog(
        action='schema_swap_success',
        entity_type='read_models',
        details=json.dumps({
            'duration_seconds': 0.5,
            'tables_updated': ['vendas_resumo_diario', 'performance_parceiro', 'receita_mensal']
        }),
        timestamp=datetime.now() - timedelta(hours=2, minutes=58)
    )
    db.add(log3)
    
    # Rebuild com falha
    log4 = AuditLog(
        action='rebuild_read_models_failure',
        entity_type='read_models',
        details=json.dumps({
            'error': 'Validation failed: missing data',
            'phase_reached': 'validating_temp_schema',
            'duration_seconds': 30.0
        }),
        timestamp=datetime.now() - timedelta(minutes=10)
    )
    db.add(log4)
    
    db.commit()
    
    logs = [log1, log2, log3, log4]
    return logs


# =============================
# Testes de Queries de Replay
# =============================

def test_get_replays_paginated(db: Session, sample_replay_logs):
    """Testa listagem paginada de replays"""
    result = get_replays(db=db, page=1, page_size=2)
    
    assert result.metadata.page == 1
    assert result.metadata.page_size == 2
    assert result.metadata.total_items == 4
    assert result.metadata.total_pages == 2
    assert result.metadata.has_next is True
    assert result.metadata.has_previous is False
    assert len(result.items) == 2


def test_get_replays_filtered_by_status(db: Session, sample_replay_logs):
    """Testa filtro por status de replay"""
    # Buscar apenas replays bem-sucedidos
    result = get_replays(db=db, status='success')
    
    success_count = sum(1 for item in result.items if item.status == 'success')
    assert success_count > 0
    
    # Buscar apenas replays com falha
    result_failed = get_replays(db=db, status='failure')
    
    failure_count = sum(1 for item in result_failed.items if item.status == 'failure')
    assert failure_count > 0


def test_get_replays_filtered_by_date(db: Session, sample_replay_logs):
    """Testa filtro por data de replay"""
    # Buscar replays das últimas 2 horas
    start_date = datetime.now() - timedelta(hours=2)
    result = get_replays(db=db, start_date=start_date)
    
    assert result.metadata.total_items >= 2  # Pelo menos os 2 mais recentes


def test_get_replay_by_id_found(db: Session, sample_replay_logs):
    """Testa busca de replay por ID (encontrado)"""
    log_id = sample_replay_logs[1].id  # replay_end bem-sucedido
    
    replay = get_replay_by_id(db=db, replay_id=log_id)
    
    assert replay is not None
    assert replay.id == log_id
    assert replay.action == 'replay_end'
    assert replay.status == 'success'
    assert replay.stats is not None


def test_get_replay_by_id_not_found(db: Session):
    """Testa busca de replay por ID (não encontrado)"""
    replay = get_replay_by_id(db=db, replay_id=9999)
    
    assert replay is None


# =============================
# Testes de Queries de Rebuild
# =============================

def test_get_rebuilds_paginated(db: Session, sample_rebuild_logs):
    """Testa listagem paginada de rebuilds"""
    result = get_rebuilds(db=db, page=1, page_size=2)
    
    assert result.metadata.page == 1
    assert result.metadata.page_size == 2
    assert result.metadata.total_items == 4
    assert result.metadata.total_pages == 2
    assert len(result.items) == 2


def test_get_rebuilds_filtered_by_status(db: Session, sample_rebuild_logs):
    """Testa filtro por status de rebuild"""
    # Buscar apenas rebuilds bem-sucedidos
    result = get_rebuilds(db=db, status='success')
    
    success_count = sum(1 for item in result.items if item.status == 'success')
    assert success_count > 0
    
    # Buscar apenas rebuilds com falha
    result_failed = get_rebuilds(db=db, status='failure')
    
    failure_count = sum(1 for item in result_failed.items if item.status == 'failure')
    assert failure_count > 0


def test_get_rebuild_by_id_found(db: Session, sample_rebuild_logs):
    """Testa busca de rebuild por ID (encontrado)"""
    log_id = sample_rebuild_logs[1].id  # rebuild_read_models_success
    
    rebuild = get_rebuild_by_id(db=db, rebuild_id=log_id)
    
    assert rebuild is not None
    assert rebuild.id == log_id
    assert rebuild.action == 'rebuild_read_models_success'
    assert rebuild.status == 'success'
    assert rebuild.duration_seconds is not None
    assert rebuild.events_processed == 1500


# =============================
# Testes de Resumo (BI)
# =============================

def test_get_audit_summary_full(db: Session, sample_replay_logs, sample_rebuild_logs):
    """Testa resumo completo de auditoria"""
    summary = get_audit_summary(db=db)
    
    assert summary.total_replays >= 4
    assert summary.total_rebuilds >= 4
    assert summary.successful_replays >= 1
    assert summary.failed_replays >= 1
    assert summary.successful_rebuilds >= 2
    assert summary.failed_rebuilds >= 1
    assert summary.total_events_processed >= 150
    assert summary.last_replay_at is not None
    assert summary.last_rebuild_at is not None


def test_get_audit_summary_filtered_by_date(db: Session, sample_replay_logs, sample_rebuild_logs):
    """Testa resumo com filtro de data"""
    # Buscar apenas das últimas 2 horas
    start_date = datetime.now() - timedelta(hours=2)
    summary = get_audit_summary(db=db, start_date=start_date)
    
    # Deve ter menos itens que o total
    assert summary.total_replays >= 2
    assert summary.total_rebuilds >= 1


# =============================
# Testes de API (Autorização)
# =============================

def test_list_replays_requires_admin(client, db: Session, sample_replay_logs):
    """Testa que listar replays requer permissão de admin"""
    # Tentar sem autenticação
    response = client.get("/audit/replays")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_list_replays_non_admin_forbidden(client, db: Session, normal_user_token, sample_replay_logs):
    """Testa que usuário não-admin não pode acessar"""
    headers = {"Authorization": f"Bearer {normal_user_token}"}
    response = client.get("/audit/replays", headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_list_replays_admin_success(client, db: Session, admin_user_token, sample_replay_logs):
    """Testa que admin pode listar replays"""
    headers = {"Authorization": f"Bearer {admin_user_token}"}
    response = client.get("/audit/replays", headers=headers)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert 'items' in data
    assert 'metadata' in data
    assert data['metadata']['total_items'] >= 4


def test_list_rebuilds_admin_success(client, db: Session, admin_user_token, sample_rebuild_logs):
    """Testa que admin pode listar rebuilds"""
    headers = {"Authorization": f"Bearer {admin_user_token}"}
    response = client.get("/audit/rebuilds", headers=headers)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert 'items' in data
    assert 'metadata' in data
    assert data['metadata']['total_items'] >= 4


def test_get_replay_by_id_admin_success(client, db: Session, admin_user_token, sample_replay_logs):
    """Testa que admin pode buscar replay por ID"""
    log_id = sample_replay_logs[1].id
    headers = {"Authorization": f"Bearer {admin_user_token}"}
    response = client.get(f"/audit/replays/{log_id}", headers=headers)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data['id'] == log_id
    assert data['action'] == 'replay_end'


def test_get_replay_by_id_not_found(client, db: Session, admin_user_token):
    """Testa busca de replay inexistente"""
    headers = {"Authorization": f"Bearer {admin_user_token}"}
    response = client.get("/audit/replays/9999", headers=headers)
    
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_get_summary_admin_success(client, db: Session, admin_user_token, sample_replay_logs, sample_rebuild_logs):
    """Testa que admin pode acessar resumo de auditoria"""
    headers = {"Authorization": f"Bearer {admin_user_token}"}
    response = client.get("/audit/summary", headers=headers)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert 'total_replays' in data
    assert 'total_rebuilds' in data
    assert 'successful_replays' in data
    assert 'failed_replays' in data
    assert data['total_replays'] >= 4


# =============================
# Testes de Paginação
# =============================

def test_pagination_parameters(client, db: Session, admin_user_token, sample_replay_logs):
    """Testa parâmetros de paginação"""
    headers = {"Authorization": f"Bearer {admin_user_token}"}
    
    # Página 1 com 2 itens
    response = client.get("/audit/replays?page=1&page_size=2", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data['metadata']['page'] == 1
    assert data['metadata']['page_size'] == 2
    assert len(data['items']) <= 2
    
    # Página 2
    response = client.get("/audit/replays?page=2&page_size=2", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data['metadata']['page'] == 2


def test_pagination_max_page_size(client, db: Session, admin_user_token, sample_replay_logs):
    """Testa limite máximo de página"""
    headers = {"Authorization": f"Bearer {admin_user_token}"}
    
    # Tentar 101 itens (máximo é 100)
    response = client.get("/audit/replays?page_size=101", headers=headers)
    
    # Deve retornar erro de validação
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# =============================
# Testes de Filtros
# =============================

def test_filter_by_status(client, db: Session, admin_user_token, sample_replay_logs):
    """Testa filtro por status"""
    headers = {"Authorization": f"Bearer {admin_user_token}"}
    
    # Filtrar por success
    response = client.get("/audit/replays?status=success", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    # Todos os itens devem ter status success
    for item in data['items']:
        assert item['status'] == 'success'


def test_filter_by_date_range(client, db: Session, admin_user_token, sample_replay_logs):
    """Testa filtro por intervalo de data"""
    headers = {"Authorization": f"Bearer {admin_user_token}"}
    
    # Definir intervalo das últimas 2 horas
    start_date = (datetime.now() - timedelta(hours=2)).isoformat()
    end_date = datetime.now().isoformat()
    
    response = client.get(
        f"/audit/replays?start_date={start_date}&end_date={end_date}",
        headers=headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data['metadata']['total_items'] >= 2


# =============================
# Testes de Read-Only
# =============================

def test_no_mutation_endpoints(client, db: Session, admin_user_token):
    """Testa que não existem endpoints de mutação"""
    headers = {"Authorization": f"Bearer {admin_user_token}"}
    
    # Tentar POST
    response = client.post("/audit/replays", json={}, headers=headers)
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    
    # Tentar PUT
    response = client.put("/audit/replays/1", json={}, headers=headers)
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    
    # Tentar DELETE
    response = client.delete("/audit/replays/1", headers=headers)
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
