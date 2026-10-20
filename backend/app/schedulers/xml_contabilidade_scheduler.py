"""Execução periódica da caixa de saída contábil no worker líder da API."""

from apscheduler.schedulers.background import BackgroundScheduler


class XmlContabilidadeScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")
        self.scheduler.add_job(
            self.processar,
            "interval",
            seconds=30,
            id="xml_contabilidade",
            max_instances=1,
            coalesce=True,
        )

    @staticmethod
    def processar():
        from app.db import SessionLocal
        from app.services.xml_contabilidade_service import (
            executar_rotina_xml_contabilidade,
        )

        return executar_rotina_xml_contabilidade(SessionLocal)

    def start(self):
        if not self.scheduler.running:
            self.scheduler.start()

    def shutdown(self):
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
