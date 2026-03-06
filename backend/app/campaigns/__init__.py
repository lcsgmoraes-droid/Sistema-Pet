"""
Campaign Engine — Motor de Campanhas
=====================================

Pacote responsável por toda a lógica de campanhas do sistema:
- Fila de eventos (campaign_event_queue, SKIP LOCKED)
- Avaliação e execução de campanhas (Campaign Engine)
- Handlers por tipo de campanha
- Scheduler de jobs (APScheduler)
- Fila de notificações (e-mail + push FCM)

Fase 1: APScheduler embutido no FastAPI + fila na tabela campaign_event_queue.
Fase 2+: Migrar para Celery Beat + Redis sem alterar os handlers.
"""
