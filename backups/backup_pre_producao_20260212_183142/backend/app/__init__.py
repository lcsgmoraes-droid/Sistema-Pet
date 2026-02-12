# Backend App Package

# Importar todos os models para que o SQLAlchemy os registre
from app import models
from app import produtos_models
from app import financeiro_models
from app import rotas_entrega_models  # Sistema de entregas
from app import opportunities_models  # FASE 2: Métricas de Oportunidade
from app import opportunity_events_models  # FASE 2: Persistência de Eventos
# IA models - NECESSÁRIO para relationships no User model e HistoricoAtualizacaoDRE
from app.ia import aba7_models, aba7_extrato_models
# DRE models também necessários
from app import dre_plano_contas_models

# RBAC models já estão em app.models
