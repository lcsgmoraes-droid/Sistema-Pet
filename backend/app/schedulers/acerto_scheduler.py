"""
Scheduler Automático de Acertos Financeiros de Parceiros
Execução diária para processamento automático de acertos configurados
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from uuid import UUID
from sqlalchemy.orm import Session
import logging

from app.db import SessionLocal
from app.models import Cliente, Tenant
from app.services.acerto_service import AcertoService, EmailQueueService, EmailService
from app.tenancy.context import tenant_context
from app.tenancy.rls import sync_rls_tenant

logger = logging.getLogger(__name__)


class AcertoScheduler:
    """Scheduler para processamento automático de acertos"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.configurar_jobs()
    
    def configurar_jobs(self):
        """Configura jobs agendados"""
        
        # Job 1: Processar acertos diários (00:05)
        self.scheduler.add_job(
            func=self.processar_acertos_diarios,
            trigger=CronTrigger(hour=0, minute=5),
            id='acertos_diarios',
            name='Processar Acertos Diários',
            replace_existing=True
        )
        
        # Job 2: Processar fila de emails (a cada 5 minutos)
        self.scheduler.add_job(
            func=self.processar_fila_emails,
            trigger='interval',
            minutes=5,
            id='fila_emails',
            name='Processar Fila de Emails',
            replace_existing=True
        )
        
        # Job 3: Ajustar média de entregas (último dia do mês às 23:00)
        self.scheduler.add_job(
            func=self.ajustar_media_entregas_mensal,
            trigger=CronTrigger(day='last', hour=23, minute=0),
            id='ajustar_media_entregas',
            name='Ajustar Média de Entregas Mensal',
            replace_existing=True
        )
        
        logger.info("[OK] Jobs de acertos configurados:")
        logger.info("   - Acertos diarios: 00:05")
        logger.info("   - Fila de emails: a cada 5 minutos")
        logger.info("   - Ajuste media entregas: último dia do mês às 23:00")
    
    def _processar_acertos_diarios_por_tenant(self, db: Session, dia_hoje: int):
        tenant_rows = (
            db.query(Tenant.id)
            .filter(Tenant.status == "active")
            .order_by(Tenant.created_at.asc())
            .all()
        )

        acertos_gerados = 0
        acertos_pulados = 0
        erros = 0
        parceiros_total = 0

        for row in tenant_rows:
            tenant_id_raw = row[0] if isinstance(row, tuple) else getattr(row, "id", row)
            try:
                tenant_id = UUID(str(tenant_id_raw))
            except (TypeError, ValueError):
                logger.warning("[SCHEDULER] Ignorando tenant_id invalido em acertos: %s", tenant_id_raw)
                continue

            with tenant_context(tenant_id):
                sync_rls_tenant(db, tenant_id)
                parceiros_elegiveis = db.query(Cliente).filter(
                    Cliente.parceiro_ativo.is_(True),
                    Cliente.parceiro_notificar.is_(True),
                    Cliente.tenant_id == tenant_id,
                    Cliente.parceiro_dia_acerto == dia_hoje,
                    Cliente.parceiro_tipo_acerto.in_(['mensal', 'quinzenal', 'semanal'])
                ).all()

                parceiros_total += len(parceiros_elegiveis)
                logger.info(
                    "[INFO] Parceiros elegiveis hoje no tenant %s: %s",
                    tenant_id,
                    len(parceiros_elegiveis),
                )

                for parceiro in parceiros_elegiveis:
                    try:
                        logger.info(f"   Processando: {parceiro.nome} (ID: {parceiro.id})")

                        resultado = AcertoService.gerar_acerto(
                            db=db,
                            parceiro_id=parceiro.id,
                            tenant_id=tenant_id,
                            user_id=parceiro.user_id,
                            data_acerto=None,
                            forcar_manual=False
                        )

                        if resultado.get('idempotente'):
                            logger.info("      [SKIP] Acerto ja existente (idempotencia)")
                            acertos_pulados += 1
                            continue

                        logger.info(f"      [OK] Acerto gerado: ID {resultado['acerto_id']}")
                        logger.info(f"         Comissoes: {resultado['comissoes_fechadas']}")
                        logger.info(f"         Valor liquido: R$ {resultado['valor_liquido']:.2f}")

                        acertos_gerados += 1

                        if parceiro.parceiro_notificar and resultado.get('dados_email'):
                            try:
                                assunto, corpo_html, corpo_texto = EmailService.renderizar_template(
                                    db=db,
                                    codigo_template='ACERTO_PARCEIRO',
                                    placeholders=resultado['dados_email'],
                                    user_id=parceiro.user_id
                                )

                                destinatarios = []
                                if parceiro.parceiro_email_principal or parceiro.email:
                                    destinatarios.append(parceiro.parceiro_email_principal or parceiro.email)

                                if parceiro.parceiro_emails_copia:
                                    emails_copia = [
                                        e.strip()
                                        for e in parceiro.parceiro_emails_copia.split(',')
                                        if e.strip()
                                    ]
                                    destinatarios.extend(emails_copia)

                                if destinatarios:
                                    EmailQueueService.enfileirar_email(
                                        db=db,
                                        parceiro_id=parceiro.id,
                                        user_id=parceiro.user_id,
                                        assunto=assunto,
                                        corpo_html=corpo_html,
                                        corpo_texto=corpo_texto,
                                        destinatarios=destinatarios,
                                        acerto_id=resultado['acerto_id']
                                    )

                                    logger.info(f"      [EMAIL] Enfileirado para: {', '.join(destinatarios)}")

                            except Exception as e:
                                logger.error(f"      [ERROR] Erro ao enfileirar email: {str(e)}")

                    except Exception as e:
                        logger.error(f"   [ERROR] Erro ao processar {parceiro.nome}: {str(e)}")
                        erros += 1

        logger.info("=" * 60)
        logger.info("[DONE] Processamento concluido:")
        logger.info(f"   - Parceiros elegiveis: {parceiros_total}")
        logger.info(f"   - Acertos gerados: {acertos_gerados}")
        logger.info(f"   - Acertos pulados (idempotencia): {acertos_pulados}")
        logger.info(f"   - Erros: {erros}")
        logger.info("=" * 60)

    def processar_acertos_diarios(self):
        """
        Job executado diariamente às 00:05.
        Processa parceiros com acerto configurado para o dia atual.
        """
        logger.info("[SCHEDULER] Iniciando processamento de acertos diarios...")
        
        db = SessionLocal()
        dia_hoje = datetime.now().day
        
        try:
            self._processar_acertos_diarios_por_tenant(db, dia_hoje)
        except Exception as e:
            logger.error(f"[CRITICAL] Erro critico no processamento de acertos: {str(e)}")
            import traceback
            traceback.print_exc()
        
        finally:
            db.close()
    
    def processar_fila_emails(self):
        """
        Job executado a cada 5 minutos.
        Processa emails pendentes na fila.
        """
        db = SessionLocal()
        
        try:
            resultado = EmailQueueService.processar_fila_global(db, limite=20)
            
            if resultado['processados'] > 0:
                logger.info("[EMAIL] Fila de emails processada:")
                logger.info(f"   - Processados: {resultado['processados']}")
                logger.info(f"   - Enviados: {resultado['enviados']}")
                logger.info(f"   - Erros: {resultado['erros']}")
        
        except Exception as e:
            logger.error(f"[ERROR] Erro ao processar fila de emails: {str(e)}")
        
        finally:
            db.close()
    
    def ajustar_media_entregas_mensal(self):
        """
        Job executado no último dia do mês às 23:00.
        Ajusta a média de entregas configurada para entregadores funcionários com controla_rh.
        """
        from app.services.acerto_entrega_service import ajustar_media_entregas_mensal
        from app.models import Tenant
        
        logger.info("[SCHEDULER] Iniciando ajuste de média de entregas mensal...")
        
        db = SessionLocal()
        hoje = datetime.now()
        
        try:
            # Busca todos os tenants ativos
            tenants = db.query(Tenant).filter(Tenant.status == 'active').all()
            
            total_ajustados = 0
            
            for tenant in tenants:
                try:
                    logger.info(f"   Processando tenant: {tenant.name} (ID: {tenant.id})")
                    
                    resultados = ajustar_media_entregas_mensal(
                        db=db,
                        tenant_id=tenant.id,
                        mes=hoje.month,
                        ano=hoje.year
                    )
                    
                    ajustados = sum(1 for r in resultados if r["ajustado"])
                    total_ajustados += ajustados
                    
                    if ajustados > 0:
                        logger.info(f"      [OK] {ajustados} entregadores ajustados")
                        for r in resultados:
                            if r["ajustado"]:
                                logger.info(
                                    f"         - {r['entregador']}: "
                                    f"{r['media_anterior']} → {r['nova_media']} entregas/mês "
                                    f"({r['diferenca_percentual']}% diferença)"
                                )
                    
                except Exception as e:
                    logger.error(f"      [ERROR] Erro no tenant {tenant.id}: {str(e)}")
                    continue
            
            logger.info(f"[OK] Ajuste concluído. Total de entregadores ajustados: {total_ajustados}")
            
        except Exception as e:
            logger.error(f"[ERROR] Erro ao ajustar média de entregas: {str(e)}")
        
        finally:
            db.close()
    
    def start(self):
        """Inicia o scheduler"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("[START] Scheduler de acertos iniciado!")
    
    def shutdown(self):
        """Para o scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("[STOP] Scheduler de acertos parado!")


# Instância global do scheduler
acerto_scheduler = AcertoScheduler()
