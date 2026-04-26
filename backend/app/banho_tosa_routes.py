"""Agregador das rotas do modulo Banho & Tosa.

As rotas ficam separadas por responsabilidade para evitar arquivos grandes e
facilitar evolucao incremental do modulo.
"""

from fastapi import APIRouter

from app.banho_tosa_api.agenda_routes import router as agenda_router
from app.banho_tosa_api.agenda_capacity_routes import router as agenda_capacity_router
from app.banho_tosa_api.apoios_routes import router as apoios_router
from app.banho_tosa_api.atendimentos_routes import router as atendimentos_router
from app.banho_tosa_api.config_routes import router as config_router
from app.banho_tosa_api.custos_routes import router as custos_router
from app.banho_tosa_api.dashboard_routes import router as dashboard_router
from app.banho_tosa_api.insumos_routes import router as insumos_router
from app.banho_tosa_api.ocorrencias_routes import router as ocorrencias_router
from app.banho_tosa_api.pacotes_recorrencias_routes import router as pacotes_recorrencias_router
from app.banho_tosa_api.pacotes_routes import router as pacotes_router
from app.banho_tosa_api.parametros_routes import router as parametros_router
from app.banho_tosa_api.recursos_routes import router as recursos_router
from app.banho_tosa_api.relatorios_routes import router as relatorios_router
from app.banho_tosa_api.retornos_routes import router as retornos_router
from app.banho_tosa_api.retornos_templates_routes import router as retornos_templates_router
from app.banho_tosa_api.servicos_routes import router as servicos_router
from app.banho_tosa_api.taxi_routes import router as taxi_router
from app.banho_tosa_api.vendas_routes import router as vendas_router


router = APIRouter(prefix="/banho-tosa", tags=["Banho & Tosa"])

router.include_router(apoios_router)
router.include_router(config_router)
router.include_router(recursos_router)
router.include_router(servicos_router)
router.include_router(parametros_router)
router.include_router(agenda_router)
router.include_router(agenda_capacity_router)
router.include_router(atendimentos_router)
router.include_router(insumos_router)
router.include_router(ocorrencias_router)
router.include_router(custos_router)
router.include_router(taxi_router)
router.include_router(vendas_router)
router.include_router(pacotes_router)
router.include_router(pacotes_recorrencias_router)
router.include_router(relatorios_router)
router.include_router(retornos_router)
router.include_router(retornos_templates_router)
router.include_router(dashboard_router)
