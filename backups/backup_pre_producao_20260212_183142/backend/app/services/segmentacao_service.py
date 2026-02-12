"""
Serviço de Segmentação Automática de Clientes
Motor de regras baseado em métricas financeiras e comportamentais
"""

from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import json

from app.models import Cliente
from app.vendas_models import Venda
from app.financeiro_models import ContaReceber


class SegmentacaoService:
    """
    Service para calcular e aplicar segmentação automática de clientes
    
    Regras de Segmentação (v1):
    - VIP: total_compras_90d >= 2000 OU ticket_medio >= 300
    - Recorrente: compras_90d >= 3
    - Novo: primeira_compra <= 30 dias
    - Inativo: ultima_compra >= 90 dias
    - Endividado: total_em_aberto >= 500
    - Risco de churn: compras_90d < compras_90d_anteriores
    """
    
    # Constantes de configuração
    PERIODO_ATUAL_DIAS = 90
    PERIODO_ANTERIOR_DIAS = 90
    
    # Thresholds das regras
    VIP_TOTAL_MINIMO = 2000.00
    VIP_TICKET_MEDIO_MINIMO = 300.00
    RECORRENTE_COMPRAS_MINIMAS = 3
    NOVO_DIAS_MAXIMOS = 30
    INATIVO_DIAS_MINIMOS = 90
    ENDIVIDADO_VALOR_MINIMO = 500.00
    
    @staticmethod
    def calcular_metricas_cliente(
        cliente_id: int,
        tenant_id: UUID,
        db: Session
    ) -> Dict:
        """
        Calcula todas as métricas financeiras de um cliente
        
        Returns:
            Dict com métricas calculadas:
            - total_compras_90d: float
            - compras_90d: int
            - ticket_medio: float
            - ultima_compra_dias: int
            - primeira_compra_dias: int
            - total_em_aberto: float
            - compras_90d_anteriores: int
            - total_historico: float
            - total_compras_historico: int
        """
        hoje = date.today()
        data_limite_90d = hoje - timedelta(days=SegmentacaoService.PERIODO_ATUAL_DIAS)
        data_limite_180d = hoje - timedelta(days=SegmentacaoService.PERIODO_ATUAL_DIAS * 2)
        data_limite_novo = hoje - timedelta(days=SegmentacaoService.NOVO_DIAS_MAXIMOS)
        
        # 1. Vendas nos últimos 90 dias
        vendas_90d = db.query(
            func.sum(Venda.total).label('total'),
            func.count(Venda.id).label('quantidade')
        ).filter(
            Venda.cliente_id == cliente_id,
            Venda.tenant_id == tenant_id,
            Venda.status.in_(['finalizada']),
            Venda.data_venda >= data_limite_90d
        ).first()
        
        total_compras_90d = float(vendas_90d.total or 0)
        compras_90d = int(vendas_90d.quantidade or 0)
        
        # 2. Vendas entre 90 e 180 dias (período anterior)
        vendas_anteriores = db.query(
            func.count(Venda.id).label('quantidade')
        ).filter(
            Venda.cliente_id == cliente_id,
            Venda.tenant_id == tenant_id,
            Venda.status.in_(['finalizada']),
            Venda.data_venda >= data_limite_180d,
            Venda.data_venda < data_limite_90d
        ).first()
        
        compras_90d_anteriores = int(vendas_anteriores.quantidade or 0)
        
        # 3. Ticket médio
        ticket_medio = total_compras_90d / compras_90d if compras_90d > 0 else 0.0
        
        # 4. Última compra (dias desde última venda finalizada)
        ultima_venda = db.query(Venda).filter(
            Venda.cliente_id == cliente_id,
            Venda.tenant_id == tenant_id,
            Venda.status.in_(['finalizada'])
        ).order_by(Venda.data_venda.desc()).first()
        
        if ultima_venda:
            ultima_compra_date = ultima_venda.data_venda.date() if isinstance(ultima_venda.data_venda, datetime) else ultima_venda.data_venda
            ultima_compra_dias = (hoje - ultima_compra_date).days
        else:
            ultima_compra_dias = 9999  # Cliente sem compras
        
        # 5. Primeira compra (dias desde primeira venda)
        primeira_venda = db.query(Venda).filter(
            Venda.cliente_id == cliente_id,
            Venda.tenant_id == tenant_id,
            Venda.status.in_(['finalizada'])
        ).order_by(Venda.data_venda.asc()).first()
        
        if primeira_venda:
            primeira_compra_date = primeira_venda.data_venda.date() if isinstance(primeira_venda.data_venda, datetime) else primeira_venda.data_venda
            primeira_compra_dias = (hoje - primeira_compra_date).days
        else:
            primeira_compra_dias = 0
        
        # 6. Total em aberto (contas a receber pendentes)
        total_em_aberto_query = db.query(
            func.sum(
                ContaReceber.valor_original - func.coalesce(ContaReceber.valor_recebido, 0)
            ).label('total_aberto')
        ).filter(
            ContaReceber.cliente_id == cliente_id,
            ContaReceber.tenant_id == tenant_id,
            ContaReceber.status.in_(['pendente', 'vencido', 'parcial'])
        ).first()
        
        total_em_aberto = float(total_em_aberto_query.total_aberto or 0)
        
        # 7. Totais históricos (desde sempre)
        vendas_historico = db.query(
            func.sum(Venda.total).label('total'),
            func.count(Venda.id).label('quantidade')
        ).filter(
            Venda.cliente_id == cliente_id,
            Venda.tenant_id == tenant_id,
            Venda.status.in_(['finalizada'])
        ).first()
        
        total_historico = float(vendas_historico.total or 0)
        total_compras_historico = int(vendas_historico.quantidade or 0)
        
        return {
            'total_compras_90d': round(total_compras_90d, 2),
            'compras_90d': compras_90d,
            'ticket_medio': round(ticket_medio, 2),
            'ultima_compra_dias': ultima_compra_dias,
            'primeira_compra_dias': primeira_compra_dias,
            'total_em_aberto': round(total_em_aberto, 2),
            'compras_90d_anteriores': compras_90d_anteriores,
            'total_historico': round(total_historico, 2),
            'total_compras_historico': total_compras_historico
        }
    
    @staticmethod
    def aplicar_regras_segmentacao(metricas: Dict) -> Tuple[str, List[str]]:
        """
        Aplica regras de segmentação baseadas nas métricas
        
        Args:
            metricas: Dict com métricas calculadas
            
        Returns:
            Tuple (segmento_principal, lista_de_tags)
        """
        tags = []
        
        # Regra 1: VIP
        if (metricas['total_compras_90d'] >= SegmentacaoService.VIP_TOTAL_MINIMO or
            metricas['ticket_medio'] >= SegmentacaoService.VIP_TICKET_MEDIO_MINIMO):
            tags.append('VIP')
        
        # Regra 2: Recorrente
        if metricas['compras_90d'] >= SegmentacaoService.RECORRENTE_COMPRAS_MINIMAS:
            tags.append('Recorrente')
        
        # Regra 3: Novo
        if (metricas['primeira_compra_dias'] <= SegmentacaoService.NOVO_DIAS_MAXIMOS and
            metricas['primeira_compra_dias'] > 0):
            tags.append('Novo')
        
        # Regra 4: Inativo
        if metricas['ultima_compra_dias'] >= SegmentacaoService.INATIVO_DIAS_MINIMOS:
            tags.append('Inativo')
        
        # Regra 5: Endividado
        if metricas['total_em_aberto'] >= SegmentacaoService.ENDIVIDADO_VALOR_MINIMO:
            tags.append('Endividado')
        
        # Regra 6: Risco de Churn
        if (metricas['compras_90d'] > 0 and
            metricas['compras_90d_anteriores'] > 0 and
            metricas['compras_90d'] < metricas['compras_90d_anteriores']):
            tags.append('Risco')
        
        # Definir segmento principal (ordem de prioridade)
        if 'VIP' in tags:
            segmento_principal = 'VIP'
        elif 'Inativo' in tags:
            segmento_principal = 'Inativo'
        elif 'Risco' in tags:
            segmento_principal = 'Risco'
        elif 'Endividado' in tags:
            segmento_principal = 'Endividado'
        elif 'Recorrente' in tags:
            segmento_principal = 'Recorrente'
        elif 'Novo' in tags:
            segmento_principal = 'Novo'
        else:
            segmento_principal = 'Regular'
            tags.append('Regular')
        
        return segmento_principal, tags
    
    @staticmethod
    def recalcular_segmento_cliente(
        cliente_id: int,
        tenant_id: UUID,
        db: Session
    ) -> Dict:
        """
        Recalcula e persiste o segmento de um cliente
        
        Returns:
            Dict com resultado da segmentação:
            - cliente_id
            - segmento
            - tags
            - metricas
            - updated_at
        """
        # 1. Verificar se cliente existe
        cliente = db.query(Cliente).filter(
            Cliente.id == cliente_id,
            Cliente.tenant_id == tenant_id
        ).first()
        
        if not cliente:
            raise ValueError(f"Cliente {cliente_id} não encontrado")
        
        # Obter user_id do cliente
        user_id = cliente.user_id
        
        # 2. Calcular métricas
        metricas = SegmentacaoService.calcular_metricas_cliente(
            cliente_id=cliente_id,
            tenant_id=tenant_id,
            db=db
        )
        
        # 3. Aplicar regras de segmentação
        segmento_principal, tags = SegmentacaoService.aplicar_regras_segmentacao(metricas)
        
        # 4. Persistir no banco
        # Verificar se já existe registro
        from sqlalchemy import text
        
        check_query = text("""
            SELECT id FROM cliente_segmentos 
            WHERE cliente_id = :cliente_id AND tenant_id = :tenant_id
        """)
        
        existing = db.execute(
            check_query,
            {'cliente_id': cliente_id, 'tenant_id': tenant_id}
        ).fetchone()
        
        metricas_json = json.dumps(metricas)
        tags_json = json.dumps(tags)
        
        if existing:
            # Update
            update_query = text("""
                UPDATE cliente_segmentos
                SET segmento = :segmento,
                    metricas = :metricas,
                    tags = :tags,
                    user_id = :user_id,
                    updated_at = CURRENT_TIMESTAMP
                WHERE cliente_id = :cliente_id AND tenant_id = :tenant_id
            """)
            
            db.execute(
                update_query,
                {
                    'segmento': segmento_principal,
                    'metricas': metricas_json,
                    'tags': tags_json,
                    'user_id': user_id,
                    'cliente_id': cliente_id,
                    'tenant_id': tenant_id
                }
            )
        else:
            # Insert
            insert_query = text("""
                INSERT INTO cliente_segmentos 
                (cliente_id, user_id, tenant_id, segmento, metricas, tags, created_at, updated_at)
                VALUES 
                (:cliente_id, :user_id, :tenant_id, :segmento, :metricas, :tags, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """)
            
            db.execute(
                insert_query,
                {
                    'cliente_id': cliente_id,
                    'user_id': user_id,
                    'tenant_id': tenant_id,
                    'segmento': segmento_principal,
                    'metricas': metricas_json,
                    'tags': tags_json
                }
            )
        
        db.commit()
        
        return {
            'cliente_id': cliente_id,
            'cliente_nome': cliente.nome,
            'segmento': segmento_principal,
            'tags': tags,
            'metricas': metricas,
            'updated_at': datetime.now().isoformat()
        }
    
    @staticmethod
    def recalcular_todos_segmentos(
        tenant_id: UUID,
        db: Session,
        limit: Optional[int] = None
    ) -> Dict:
        """
        Recalcula segmentos de todos os clientes de um tenant
        
        Args:
            tenant_id: ID do tenant
            db: Sessão do banco
            limit: Limite de clientes a processar (None = todos)
            
        Returns:
            Dict com estatísticas do processamento
        """
        # Buscar clientes ativos
        query = db.query(Cliente).filter(
            Cliente.tenant_id == tenant_id,
            Cliente.ativo == True
        )
        
        if limit:
            query = query.limit(limit)
        
        clientes = query.all()
        
        resultados = {
            'total_processados': 0,
            'sucessos': 0,
            'erros': 0,
            'detalhes': [],
            'distribuicao_segmentos': {}
        }
        
        for cliente in clientes:
            try:
                resultado = SegmentacaoService.recalcular_segmento_cliente(
                    cliente_id=cliente.id,
                    tenant_id=tenant_id,
                    db=db
                )
                
                resultados['sucessos'] += 1
                resultados['detalhes'].append({
                    'cliente_id': cliente.id,
                    'nome': cliente.nome,
                    'segmento': resultado['segmento'],
                    'status': 'ok'
                })
                
                # Contar distribuição
                segmento = resultado['segmento']
                if segmento not in resultados['distribuicao_segmentos']:
                    resultados['distribuicao_segmentos'][segmento] = 0
                resultados['distribuicao_segmentos'][segmento] += 1
                
            except Exception as e:
                resultados['erros'] += 1
                resultados['detalhes'].append({
                    'cliente_id': cliente.id,
                    'nome': cliente.nome,
                    'status': 'erro',
                    'mensagem': str(e)
                })
            
            resultados['total_processados'] += 1
        
        return resultados
    
    @staticmethod
    def obter_segmento_cliente(
        cliente_id: int,
        tenant_id: UUID,
        db: Session
    ) -> Optional[Dict]:
        """
        Obtém o segmento atual de um cliente
        
        Returns:
            Dict com dados do segmento ou None se não existir
        """
        from sqlalchemy import text
        
        query = text("""
            SELECT 
                id,
                cliente_id,
                segmento,
                metricas,
                tags,
                created_at,
                updated_at
            FROM cliente_segmentos
            WHERE cliente_id = :cliente_id AND tenant_id = :tenant_id
        """)
        
        result = db.execute(
            query,
            {'cliente_id': cliente_id, 'tenant_id': tenant_id}
        ).fetchone()
        
        if not result:
            return None
        
        # PostgreSQL JSONB retorna dict/list diretamente (não string)
        # SQLite retorna string que precisa de json.loads()
        metricas = result[3]
        if isinstance(metricas, str):
            metricas = json.loads(metricas) if metricas else {}
        elif metricas is None:
            metricas = {}
            
        tags = result[4]
        if isinstance(tags, str):
            tags = json.loads(tags) if tags else []
        elif tags is None:
            tags = []
        
        return {
            'id': result[0],
            'cliente_id': result[1],
            'segmento': result[2],
            'metricas': metricas,
            'tags': tags,
            'created_at': result[5],
            'updated_at': result[6]
        }
    
    @staticmethod
    def listar_segmentos(
        tenant_id: UUID,
        db: Session,
        segmento_filtro: Optional[str] = None
    ) -> List[Dict]:
        """
        Lista todos os segmentos de clientes de um tenant
        
        Args:
            tenant_id: ID do tenant
            db: Sessão do banco
            segmento_filtro: Filtrar por segmento específico
            
        Returns:
            Lista de segmentos
        """
        from sqlalchemy import text
        
        if segmento_filtro:
            query = text("""
                SELECT 
                    cs.id,
                    cs.cliente_id,
                    c.nome as cliente_nome,
                    cs.segmento,
                    cs.tags,
                    cs.metricas,
                    cs.updated_at
                FROM cliente_segmentos cs
                JOIN clientes c ON cs.cliente_id = c.id
                WHERE cs.tenant_id = :tenant_id 
                AND cs.segmento = :segmento
                ORDER BY cs.updated_at DESC
            """)
            
            results = db.execute(
                query,
                {'tenant_id': tenant_id, 'segmento': segmento_filtro}
            ).fetchall()
        else:
            query = text("""
                SELECT 
                    cs.id,
                    cs.cliente_id,
                    c.nome as cliente_nome,
                    cs.segmento,
                    cs.tags,
                    cs.metricas,
                    cs.updated_at
                FROM cliente_segmentos cs
                JOIN clientes c ON cs.cliente_id = c.id
                WHERE cs.tenant_id = :tenant_id
                ORDER BY cs.updated_at DESC
            """)
            
            results = db.execute(query, {'tenant_id': tenant_id}).fetchall()
        
        segmentos = []
        for row in results:
            # PostgreSQL JSONB retorna dict/list diretamente
            tags = row[4]
            if isinstance(tags, str):
                tags = json.loads(tags) if tags else []
            elif tags is None:
                tags = []
                
            metricas = row[5]
            if isinstance(metricas, str):
                metricas = json.loads(metricas) if metricas else {}
            elif metricas is None:
                metricas = {}
            
            segmentos.append({
                'id': row[0],
                'cliente_id': row[1],
                'cliente_nome': row[2],
                'segmento': row[3],
                'tags': tags,
                'metricas': metricas,
                'updated_at': row[6]
            })
        
        return segmentos
