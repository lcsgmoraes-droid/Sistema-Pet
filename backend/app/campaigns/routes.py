"""
Agregador das rotas da API de campanhas.

Mantem o prefixo /campanhas e reexporta nomes historicos para compatibilidade
com testes e imports internos, enquanto a implementacao fica em modulos menores.
"""

from fastapi import APIRouter

from app.campaigns.beneficios_manuais_routes import (
    CashbackManualBody as CashbackManualBody,
    LancarCarimboManualBody as LancarCarimboManualBody,
    cashback_manual as cashback_manual,
    estornar_carimbo as estornar_carimbo,
    lancar_carimbo_manual as lancar_carimbo_manual,
    listar_carimbos_cliente as listar_carimbos_cliente,
    router as beneficios_manuais_router,
)
from app.campaigns.campaign_management_routes import (
    AtualizarParametrosBody as AtualizarParametrosBody,
    atualizar_parametros as atualizar_parametros,
    campaigns_health as campaigns_health,
    listar_campanhas as listar_campanhas,
    pausar_campanha as pausar_campanha,
    router as campaign_management_router,
)
from app.campaigns.clientes_routes import (
    buscar_clientes_campanhas as buscar_clientes_campanhas,
    extrato_campanhas_cliente as extrato_campanhas_cliente,
    extrato_cashback as extrato_cashback,
    gestor_clientes_por_tipo as gestor_clientes_por_tipo,
    relatorio_campanhas as relatorio_campanhas,
    router as clientes_router,
    saldo_cliente as saldo_cliente,
    sugestao_cashback as sugestao_cashback,
)
from app.campaigns.coupons_routes import (
    CriarCupomManualBody as CriarCupomManualBody,
    ResgateBody as ResgateBody,
    _build_manual_coupon_meta as _build_manual_coupon_meta,
    anular_cupom as anular_cupom,
    criar_cupom_manual as criar_cupom_manual,
    listar_cupons as listar_cupons,
    resgatar_cupom as resgatar_cupom,
    router as coupons_router,
)
from app.campaigns.dashboard_routes import (
    dashboard_campanhas as dashboard_campanhas,
    router as dashboard_router,
)
from app.campaigns.engajamento_routes import (
    EnviarDestaqueBody as EnviarDestaqueBody,
    EnvioInativosBody as EnvioInativosBody,
    EnvioLoteBody as EnvioLoteBody,
    RetencaoBody as RetencaoBody,
    _retencao_to_dict as _retencao_to_dict,
    calcular_destaque_mensal as calcular_destaque_mensal,
    criar_retencao as criar_retencao,
    deletar_retencao as deletar_retencao,
    editar_retencao as editar_retencao,
    enviar_destaque_mensal as enviar_destaque_mensal,
    envio_em_lote as envio_em_lote,
    envio_escalonado_inativos as envio_escalonado_inativos,
    listar_retencao as listar_retencao,
    router as engajamento_router,
    seed_campanhas as seed_campanhas,
)
from app.campaigns.ranking_routes import (
    CriarCampanhaBody as CriarCampanhaBody,
    RankingConfigBody as RankingConfigBody,
    SchedulerConfigBody as SchedulerConfigBody,
    criar_campanha as criar_campanha,
    deletar_campanha as deletar_campanha,
    get_ranking_config as get_ranking_config,
    get_scheduler_config as get_scheduler_config,
    listar_ranking as listar_ranking,
    recalcular_ranking as recalcular_ranking,
    router as ranking_router,
    salvar_ranking_config as salvar_ranking_config,
    salvar_scheduler_config as salvar_scheduler_config,
)
from app.campaigns.routes_common import (
    _current_user_id as _current_user_id,
    _resolver_customer_id_campanhas as _resolver_customer_id_campanhas,
    get_db as get_db,
)
from app.campaigns.sorteios_routes import router as sorteios_router
from app.campaigns.unificacao_routes import (
    ConfirmarMergeBody as ConfirmarMergeBody,
    _serialize_cliente_resumo as _serialize_cliente_resumo,
    confirmar_unificacao as confirmar_unificacao,
    desfazer_unificacao as desfazer_unificacao,
    listar_sugestoes_unificacao as listar_sugestoes_unificacao,
    router as unificacao_router,
)
from app.campaigns.validade_routes import (
    CampanhaValidadeConfigBody as CampanhaValidadeConfigBody,
    CampanhaValidadeExclusaoBody as CampanhaValidadeExclusaoBody,
    _serializar_exclusao_validade as _serializar_exclusao_validade,
    criar_exclusao_campanha_validade as criar_exclusao_campanha_validade,
    obter_config_campanha_validade as obter_config_campanha_validade,
    remover_exclusao_campanha_validade as remover_exclusao_campanha_validade,
    router as validade_router,
    salvar_config_campanha_validade as salvar_config_campanha_validade,
)


router = APIRouter(prefix="/campanhas", tags=["Campanhas"])
router.include_router(sorteios_router)
router.include_router(unificacao_router)
router.include_router(dashboard_router)
router.include_router(ranking_router)
router.add_api_route("", listar_campanhas, methods=["GET"])
router.include_router(campaign_management_router)
router.include_router(validade_router)
router.include_router(coupons_router)
router.include_router(clientes_router)
router.include_router(beneficios_manuais_router)
router.include_router(engajamento_router)
