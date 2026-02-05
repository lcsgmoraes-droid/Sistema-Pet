"""
Exemplo de Uso - API de Auditoria (Fase 5.6)
=============================================

Demonstra como consultar logs de auditoria de replays e rebuilds.
"""

import requests
from datetime import datetime, timedelta
from typing import Optional


# =============================
# Configuração
# =============================

BASE_URL = "http://localhost:8000"
ADMIN_TOKEN = "seu_token_admin_aqui"  # Obter via /auth/login

headers = {
    "Authorization": f"Bearer {ADMIN_TOKEN}"
}


# =============================
# Funções de Consulta
# =============================

def listar_replays(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """
    Lista replays de eventos com paginação e filtros.
    
    Args:
        page: Número da página (1-indexed)
        page_size: Itens por página (max 100)
        status: Filtrar por status ('success', 'failure', 'in_progress')
        start_date: Data inicial
        end_date: Data final
    
    Returns:
        Resposta com items e metadata de paginação
    """
    params = {
        "page": page,
        "page_size": page_size
    }
    
    if status:
        params["status"] = status
    if start_date:
        params["start_date"] = start_date.isoformat()
    if end_date:
        params["end_date"] = end_date.isoformat()
    
    response = requests.get(
        f"{BASE_URL}/audit/replays",
        headers=headers,
        params=params
    )
    
    response.raise_for_status()
    return response.json()


def buscar_replay(replay_id: int):
    """
    Busca detalhes de um replay específico.
    
    Args:
        replay_id: ID do log de auditoria
    
    Returns:
        Detalhes do replay (filtros, stats, erro)
    """
    response = requests.get(
        f"{BASE_URL}/audit/replays/{replay_id}",
        headers=headers
    )
    
    response.raise_for_status()
    return response.json()


def listar_rebuilds(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """
    Lista rebuilds de read models com paginação e filtros.
    
    Args:
        page: Número da página (1-indexed)
        page_size: Itens por página (max 100)
        status: Filtrar por status ('success', 'failure')
        start_date: Data inicial
        end_date: Data final
    
    Returns:
        Resposta com items e metadata de paginação
    """
    params = {
        "page": page,
        "page_size": page_size
    }
    
    if status:
        params["status"] = status
    if start_date:
        params["start_date"] = start_date.isoformat()
    if end_date:
        params["end_date"] = end_date.isoformat()
    
    response = requests.get(
        f"{BASE_URL}/audit/rebuilds",
        headers=headers,
        params=params
    )
    
    response.raise_for_status()
    return response.json()


def buscar_rebuild(rebuild_id: int):
    """
    Busca detalhes de um rebuild específico.
    
    Args:
        rebuild_id: ID do log de auditoria
    
    Returns:
        Detalhes do rebuild (duração, eventos, tabelas, fase, erro)
    """
    response = requests.get(
        f"{BASE_URL}/audit/rebuilds/{rebuild_id}",
        headers=headers
    )
    
    response.raise_for_status()
    return response.json()


def obter_resumo(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """
    Obtém resumo agregado de auditoria (para BI/Analytics).
    
    Args:
        start_date: Data inicial do período
        end_date: Data final do período
    
    Returns:
        Estatísticas agregadas de replays e rebuilds
    """
    params = {}
    
    if start_date:
        params["start_date"] = start_date.isoformat()
    if end_date:
        params["end_date"] = end_date.isoformat()
    
    response = requests.get(
        f"{BASE_URL}/audit/summary",
        headers=headers,
        params=params if params else None
    )
    
    response.raise_for_status()
    return response.json()


# =============================
# Exemplos de Uso
# =============================

def exemplo_listar_todos_replays():
    """Exemplo: Listar todos os replays (paginado)"""
    print("📋 Listando todos os replays...")
    
    result = listar_replays(page=1, page_size=10)
    
    print(f"\n✅ Total de replays: {result['metadata']['total_items']}")
    print(f"📄 Página {result['metadata']['page']} de {result['metadata']['total_pages']}")
    
    for replay in result['items']:
        status_emoji = "✅" if replay['status'] == 'success' else "❌" if replay['status'] == 'failure' else "⏳"
        print(f"\n{status_emoji} Replay #{replay['id']}")
        print(f"   Ação: {replay['action']}")
        print(f"   Status: {replay['status']}")
        print(f"   Data: {replay['timestamp']}")
        
        if replay.get('stats'):
            stats = replay['stats']
            print(f"   Eventos processados: {stats.get('total_events', 'N/A')}")
            print(f"   Duração: {stats.get('duration_seconds', 'N/A')}s")
        
        if replay.get('error'):
            print(f"   ❌ Erro: {replay['error']}")


def exemplo_filtrar_replays_com_falha():
    """Exemplo: Listar apenas replays que falharam"""
    print("\n❌ Listando replays com falha...")
    
    result = listar_replays(status='failure')
    
    print(f"\n✅ Total de replays com falha: {result['metadata']['total_items']}")
    
    for replay in result['items']:
        print(f"\n❌ Replay #{replay['id']}")
        print(f"   Data: {replay['timestamp']}")
        print(f"   Erro: {replay.get('error', 'Erro não especificado')}")


def exemplo_replays_ultimos_7_dias():
    """Exemplo: Listar replays dos últimos 7 dias"""
    print("\n📅 Listando replays dos últimos 7 dias...")
    
    start_date = datetime.now() - timedelta(days=7)
    
    result = listar_replays(start_date=start_date)
    
    print(f"\n✅ Total de replays nos últimos 7 dias: {result['metadata']['total_items']}")
    
    for replay in result['items']:
        status_emoji = "✅" if replay['status'] == 'success' else "❌"
        print(f"{status_emoji} {replay['timestamp']} - {replay['action']}")


def exemplo_detalhes_replay_especifico():
    """Exemplo: Buscar detalhes de um replay específico"""
    print("\n🔍 Buscando detalhes de replay específico...")
    
    # Buscar um replay qualquer para usar como exemplo
    replays = listar_replays(page=1, page_size=1)
    
    if replays['items']:
        replay_id = replays['items'][0]['id']
        
        replay = buscar_replay(replay_id)
        
        print(f"\n✅ Replay #{replay['id']}")
        print(f"   Ação: {replay['action']}")
        print(f"   Status: {replay['status']}")
        print(f"   Data: {replay['timestamp']}")
        
        if replay.get('filters'):
            print(f"\n📋 Filtros aplicados:")
            for key, value in replay['filters'].items():
                print(f"   - {key}: {value}")
        
        if replay.get('stats'):
            print(f"\n📊 Estatísticas:")
            for key, value in replay['stats'].items():
                print(f"   - {key}: {value}")
    else:
        print("❌ Nenhum replay encontrado")


def exemplo_listar_rebuilds_bem_sucedidos():
    """Exemplo: Listar apenas rebuilds bem-sucedidos"""
    print("\n✅ Listando rebuilds bem-sucedidos...")
    
    result = listar_rebuilds(status='success')
    
    print(f"\n✅ Total de rebuilds bem-sucedidos: {result['metadata']['total_items']}")
    
    for rebuild in result['items']:
        print(f"\n✅ Rebuild #{rebuild['id']}")
        print(f"   Ação: {rebuild['action']}")
        print(f"   Data: {rebuild['timestamp']}")
        
        if rebuild.get('duration_seconds'):
            print(f"   Duração: {rebuild['duration_seconds']:.1f}s")
        
        if rebuild.get('events_processed'):
            print(f"   Eventos processados: {rebuild['events_processed']}")
        
        if rebuild.get('tables_updated'):
            print(f"   Tabelas atualizadas: {', '.join(rebuild['tables_updated'])}")


def exemplo_resumo_auditoria():
    """Exemplo: Obter resumo de auditoria para BI"""
    print("\n📊 Resumo de Auditoria (BI/Analytics)...")
    
    summary = obter_resumo()
    
    print(f"\n📋 Replays:")
    print(f"   Total: {summary['total_replays']}")
    print(f"   Bem-sucedidos: {summary['successful_replays']}")
    print(f"   Com falha: {summary['failed_replays']}")
    print(f"   Último em: {summary.get('last_replay_at', 'N/A')}")
    
    print(f"\n📋 Rebuilds:")
    print(f"   Total: {summary['total_rebuilds']}")
    print(f"   Bem-sucedidos: {summary['successful_rebuilds']}")
    print(f"   Com falha: {summary['failed_rebuilds']}")
    print(f"   Último em: {summary.get('last_rebuild_at', 'N/A')}")
    
    print(f"\n📊 Métricas Gerais:")
    print(f"   Total de eventos processados: {summary['total_events_processed']}")
    
    if summary.get('average_replay_duration'):
        print(f"   Duração média de replay: {summary['average_replay_duration']:.2f}s")
    
    if summary.get('average_rebuild_duration'):
        print(f"   Duração média de rebuild: {summary['average_rebuild_duration']:.2f}s")


def exemplo_resumo_mensal():
    """Exemplo: Obter resumo do mês atual"""
    print("\n📅 Resumo do Mês Atual...")
    
    # Primeiro dia do mês
    today = datetime.now()
    start_of_month = datetime(today.year, today.month, 1)
    
    summary = obter_resumo(start_date=start_of_month)
    
    print(f"\n📋 Estatísticas de {start_of_month.strftime('%B/%Y')}:")
    print(f"   Replays: {summary['total_replays']} (✅ {summary['successful_replays']} | ❌ {summary['failed_replays']})")
    print(f"   Rebuilds: {summary['total_rebuilds']} (✅ {summary['successful_rebuilds']} | ❌ {summary['failed_rebuilds']})")
    print(f"   Eventos processados: {summary['total_events_processed']}")


# =============================
# Casos de Uso (BI/Analytics)
# =============================

def caso_uso_bi_dashboard():
    """
    Caso de Uso: Dashboard de BI/Analytics
    
    Integrar com ferramentas como Metabase, Power BI, Tableau
    """
    print("\n" + "="*60)
    print("📊 CASO DE USO: Dashboard de BI/Analytics")
    print("="*60)
    
    # 1. Obter resumo geral
    summary = obter_resumo()
    
    print(f"\n📈 KPIs Principais:")
    print(f"   Taxa de sucesso de replays: {summary['successful_replays'] / max(summary['total_replays'], 1) * 100:.1f}%")
    print(f"   Taxa de sucesso de rebuilds: {summary['successful_rebuilds'] / max(summary['total_rebuilds'], 1) * 100:.1f}%")
    
    # 2. Análise de tendências
    print(f"\n📅 Últimas Operações:")
    print(f"   Último replay: {summary.get('last_replay_at', 'Nunca')}")
    print(f"   Último rebuild: {summary.get('last_rebuild_at', 'Nunca')}")
    
    # 3. Listar falhas recentes para análise
    print(f"\n❌ Falhas Recentes:")
    failed_replays = listar_replays(status='failure', page_size=5)
    
    for replay in failed_replays['items']:
        print(f"   - {replay['timestamp']}: {replay.get('error', 'Erro desconhecido')}")


def caso_uso_troubleshooting():
    """
    Caso de Uso: Troubleshooting de Falhas
    
    Investigar e debugar problemas em replays e rebuilds
    """
    print("\n" + "="*60)
    print("🔧 CASO DE USO: Troubleshooting de Falhas")
    print("="*60)
    
    # 1. Listar todas as falhas
    print("\n❌ Analisando falhas...")
    
    failed_replays = listar_replays(status='failure')
    failed_rebuilds = listar_rebuilds(status='failure')
    
    print(f"\n📊 Total de falhas:")
    print(f"   Replays: {failed_replays['metadata']['total_items']}")
    print(f"   Rebuilds: {failed_rebuilds['metadata']['total_items']}")
    
    # 2. Analisar padrões de erro
    print(f"\n🔍 Analisando padrões de erro...")
    
    error_patterns = {}
    
    for replay in failed_replays['items']:
        error = replay.get('error', 'Unknown')
        error_patterns[error] = error_patterns.get(error, 0) + 1
    
    print(f"\n📋 Erros mais comuns em replays:")
    for error, count in sorted(error_patterns.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"   - {error}: {count} ocorrências")


def caso_uso_governanca():
    """
    Caso de Uso: Governança e Auditoria
    
    Rastrear quem executou operações e quando
    """
    print("\n" + "="*60)
    print("🔒 CASO DE USO: Governança e Auditoria")
    print("="*60)
    
    # 1. Listar operações recentes
    print("\n📅 Operações dos últimos 30 dias:")
    
    start_date = datetime.now() - timedelta(days=30)
    
    replays = listar_replays(start_date=start_date)
    rebuilds = listar_rebuilds(start_date=start_date)
    
    print(f"\n📊 Resumo:")
    print(f"   Replays executados: {replays['metadata']['total_items']}")
    print(f"   Rebuilds executados: {rebuilds['metadata']['total_items']}")
    
    # 2. Timeline de operações
    print(f"\n📅 Timeline (últimas 10 operações):")
    
    all_operations = []
    
    for replay in replays['items'][:5]:
        all_operations.append({
            'timestamp': replay['timestamp'],
            'type': 'Replay',
            'status': replay['status']
        })
    
    for rebuild in rebuilds['items'][:5]:
        all_operations.append({
            'timestamp': rebuild['timestamp'],
            'type': 'Rebuild',
            'status': rebuild['status']
        })
    
    all_operations.sort(key=lambda x: x['timestamp'], reverse=True)
    
    for op in all_operations[:10]:
        status_emoji = "✅" if op['status'] == 'success' else "❌"
        print(f"   {status_emoji} {op['timestamp']} - {op['type']}")


# =============================
# Executar Exemplos
# =============================

if __name__ == "__main__":
    print("=" * 60)
    print("🔍 API DE AUDITORIA - EXEMPLOS DE USO")
    print("=" * 60)
    
    try:
        # Exemplos básicos
        exemplo_listar_todos_replays()
        print("\n" + "-" * 60)
        
        exemplo_filtrar_replays_com_falha()
        print("\n" + "-" * 60)
        
        exemplo_replays_ultimos_7_dias()
        print("\n" + "-" * 60)
        
        exemplo_detalhes_replay_especifico()
        print("\n" + "-" * 60)
        
        exemplo_listar_rebuilds_bem_sucedidos()
        print("\n" + "-" * 60)
        
        exemplo_resumo_auditoria()
        print("\n" + "-" * 60)
        
        exemplo_resumo_mensal()
        print("\n" + "-" * 60)
        
        # Casos de uso avançados
        caso_uso_bi_dashboard()
        print("\n" + "-" * 60)
        
        caso_uso_troubleshooting()
        print("\n" + "-" * 60)
        
        caso_uso_governanca()
        
        print("\n" + "=" * 60)
        print("✅ Todos os exemplos executados com sucesso!")
        print("=" * 60)
        
    except requests.exceptions.HTTPError as e:
        print(f"\n❌ Erro HTTP: {e.response.status_code}")
        print(f"   Detalhes: {e.response.json()}")
    
    except Exception as e:
        print(f"\n❌ Erro: {str(e)}")
