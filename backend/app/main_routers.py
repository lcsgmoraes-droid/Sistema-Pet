"""Router registration for the FastAPI application."""

from fastapi import Depends, FastAPI

from app.auth_routes_multitenant import router as auth_router
from app.clientes_routes import router as clientes_router
from app.pets_routes import router as pets_router  # Módulo dedicado de pets
from app.cadastros_routes import router as cadastros_router  # Espécies e Raças
from app.produtos_routes import router as produtos_router
from app.variacoes_routes import router as variacoes_router  # Sprint 2: Variações
from app.vendas_routes import router as vendas_router
from app.caixa_routes import router as caixa_router
from app.nfe_routes import router as nfe_router
from app.estoque_routes import router as estoque_router
from app.estoque_movimentacoes_manuais_routes import (
    router as estoque_movimentacoes_manuais_router,
)
from app.estoque_entrada_manual_routes import router as estoque_entrada_manual_router
from app.estoque_saida_manual_routes import router as estoque_saida_manual_router
from app.estoque_granel_routes import router as estoque_granel_router
from app.estoque_transferencia_routes import router as estoque_transferencia_router
from app.estoque_transferencia_parceiro_routes import (
    router as estoque_transferencia_parceiro_router,
)
from app.estoque_saida_full_routes import router as estoque_saida_full_router
from app.estoque_alertas_gerais_routes import router as estoque_alertas_gerais_router
from app.estoque_relatorios_routes import router as estoque_relatorios_router
from app.estoque_movimentacoes_edicao_routes import (
    router as estoque_movimentacoes_edicao_router,
)
from app.estoque_movimentacoes_consulta_routes import (
    router as estoque_movimentacoes_consulta_router,
)
from app.estoque_alertas_routes import router as estoque_alertas_router
from app.estoque_validade_routes import router as estoque_validade_router
from app.bling_sync_routes import router as bling_sync_router
from app.pedidos_compra_routes import router as pedidos_compra_router
from app.fornecedor_grupos_routes import router as fornecedor_grupos_router
from app.notas_entrada_routes import router as notas_entrada_router
from app.compras_pendencias_routes import router as compras_pendencias_router
from app.contas_pagar_routes import router as contas_pagar_router
from app.tipo_despesa_routes import router as tipo_despesa_router
from app.contas_receber_routes import router as contas_receber_router
from app.conciliacao_cartao_routes import router as conciliacao_cartao_router
from app.conciliacao_routes import router as conciliacao_router
from app.conciliacao_bancaria_routes import router as conciliacao_bancaria_router
from app.conciliacao_aba1_routes import router as conciliacao_aba1_router
from app.conciliacao_historico_routes import router as conciliacao_historico_router
from app.financeiro_routes import router as financeiro_router
from app.contas_bancarias_routes import router as contas_bancarias_router
from app.admin_routes import router as admin_router
from app.lancamentos_routes import router as lancamentos_router
from app.categorias_routes import router as categorias_router
from app.bling_routes import router as bling_router
from app.bling_oauth_routes import router as bling_oauth_router
from app.integracao_bling_pedido_routes import router as bling_pedido_router
from app.integracao_bling_nf_routes import router as bling_nf_router
from app.dashboard_routes import router as dashboard_router
from app.relatorio_vendas_routes import router as relatorio_vendas_router
from app.dre_routes import router as dre_router
from app.dre_canais_routes import router as dre_canais_router
from app.dre_plano_contas_routes import router as dre_plano_contas_router
from app.dre_classificacao_routes import router as dre_classificacao_router
from app.ia_routes import router as ia_router
from app.chat_routes import router as chat_router
from app.dre_ia_routes import router as dre_ia_router
from app.ia.aba7_extrato_routes import router as extrato_ia_router
from app.ia_fluxo_routes import router as ia_fluxo_router
from app.tributacao_routes import router as tributacao_router
from app.importacao_produtos import router as importacao_router
from app.importacao_pessoas import router as importacao_pessoas_router
from app.lembretes import router as lembretes_router
from app.calculadora_racao import router as calculadora_racao_router
from app.cliente_info_pdv import router as cliente_info_pdv_router
from app.opcoes_racao_routes import router as opcoes_racao_router
from app.analise_racoes_routes import (
    router as analise_racoes_router,
)  # Fase 4: Análises de Rações
from app.pdv_racoes_routes import (
    router as pdv_racoes_router,
)  # Fase 5: PDV Inteligente de Rações
from app.sugestoes_racoes_routes import (
    router as sugestoes_racoes_router,
)  # Fase 6: Sugestões Inteligentes
from app.ml_racoes_routes import router as ml_racoes_router  # Fase 7: Machine Learning
from app.formas_pagamento_routes import router as formas_pagamento_router
from app.operadoras_routes import router as operadoras_router
from app.comissoes_routes import router as comissoes_router
from app.analytics.api import router as analytics_router
from app.comissoes_demonstrativo_routes import router as comissoes_demonstrativo_router
from app.comissoes_avancadas_routes import router as comissoes_avancadas_router
from app.comissoes_diagnostico_routes import router as comissoes_diagnostico_router
from app.routers.relatorios_comissoes import router as relatorios_comissoes_router
from app.routes.acertos_routes import router as acertos_router
from app.audit.api import router as audit_router
from app.api.endpoints.whatsapp import (
    router as whatsapp_router,
)  # Sprint 3: WhatsApp IA

# from app.api.endpoints.whatsapp import router as whatsapp_router  # DESATIVADO - Conflita com novos modelos WhatsApp IA
from app.api.endpoints.segmentacao import router as segmentacao_router
from app.pdv_ai_routes import router as pdv_ai_router
from app.usuarios_routes import router as usuarios_router
from app.roles_routes import router as roles_router
from app.permissions_routes import router as permissions_router
from app.api.pdv_internal_routes import router as pdv_internal_router

# [DESATIVADO - PHASE 5] from app.api.opportunity_metrics_routes import router as opportunity_metrics_router
from app.api.racao_calculadora_routes import router as racao_calculadora_internal_router
from app.api.whatsapp_orchestrator_internal_routes import (
    router as whatsapp_orchestrator_internal_router,
)
from app.api.v1.fiscal_sugestao import router as fiscal_sugestao_router
from app.api.v1.produto_fiscal import router as produto_fiscal_router
from app.api.v1.pdv_fiscal import router as pdv_fiscal_router
from app.api.v1.produto_fiscal_v2 import router as produto_fiscal_v2_router
from app.api.v1.empresa_fiscal import router as empresa_fiscal_router
from app.simples_routes import router as simples_router
from app.auditoria_provisoes_routes import router as auditoria_provisoes_router
from app.projecao_caixa_routes import router as projecao_caixa_router
from app.simulacao_contratacao_routes import router as simulacao_contratacao_router
from app.cargos_routes import router as cargos_router
from app.funcionarios_routes import router as funcionarios_router
from app.empresa_config_routes import router as empresa_config_router
from app.pdv_indicadores_routes import router as pdv_indicadores_router
from app.empresa_routes import router as empresa_router
from app.api.endpoints.configuracoes_entrega import (
    router as configuracoes_entrega_router,
)
from app.api.endpoints.rotas_entrega import router as rotas_entrega_router
from app.api.endpoints.acertos_entrega import router as acertos_entrega_router
from app.api.endpoints.configuracao_custo_moto import (
    router as configuracao_custo_moto_router,
)
from app.api.endpoints.dashboard_entregas import (
    router as dashboard_entregas_router,
)  # ETAPA 11.1
from app.pendencia_estoque_routes import (
    router as pendencia_estoque_router,
)  # Sistema de Lista de Espera

# ============================================================================
# WHATSAPP + IA - SPRINT 2 & 4 & 6 & 7
# ============================================================================
from app.whatsapp.webhook import router as whatsapp_webhook_router
from app.routers.whatsapp_config import router as whatsapp_config_router
from app.routers.whatsapp_handoff import router as whatsapp_handoff_router  # Sprint 4
from app.routers.whatsapp_websocket import (
    router as whatsapp_websocket_router,
)  # Sprint 5: WebSocket
from app.routes.whatsapp_routes import (
    router as whatsapp_api_router,
)  # Sprint 6: Tools & Tests
from app.whatsapp.analytics_router import (
    router as whatsapp_analytics_router,
)  # Sprint 7: Analytics
from app.whatsapp.security_router import (
    router as whatsapp_security_router,
)  # Sprint 8: Security & LGPD
from app.health_router import router as health_router  # Sprint 9: Health & Monitoring
from app.admin_fix_routes import router as admin_fix_router  # Correções administrativas
from app.routes.health_routes import (
    router as health_check_router,
)  # FASE 8: Healthcheck + Readiness
from app.routes.error_events_routes import (
    router as error_events_router,
)  # Observabilidade operacional
from app.routes.ops_tenants_routes import (
    router as ops_tenants_router,
)  # Gestao operacional de tenants
from app.lgpd_routes import router as lgpd_router  # LGPD operacional

# ============================================================================
# E-COMMERCE - Loja Pública
# ============================================================================
from app.routes.ecommerce import router as ecommerce_router
from app.routes.ecommerce_auth import router as ecommerce_auth_router
from app.routes.ecommerce_public import router as ecommerce_public_router
from app.routes.ecommerce_cart import router as ecommerce_cart_router
from app.routes.ecommerce_checkout import router as ecommerce_checkout_router
from app.routes.app_banho_tosa_routes import router as app_banho_tosa_router
from app.routes.app_mobile_routes import router as app_mobile_router
from app.routes.app_privacy_routes import router as app_privacy_router
from app.routes.app_vet_routes import router as app_vet_router
from app.routes.ecommerce_webhooks import router as ecommerce_webhooks_router
from app.routes.ecommerce_aparencia_routes import router as ecommerce_aparencia_router
from app.routes.ecommerce_config_routes import router as ecommerce_config_router
from app.routes.ecommerce_payment_config_routes import (
    public_router as ecommerce_payment_config_public_router,
)
from app.routes.ecommerce_payment_config_routes import (
    router as ecommerce_payment_config_router,
)
from app.routes.ecommerce_notify_routes import router as ecommerce_notify_router
from app.routes.ecommerce_analytics_routes import router as ecommerce_analytics_router
from app.routes.ecommerce_entregador import router as ecommerce_entregador_router
from app.routes.ecommerce_drive_routes import router as ecommerce_drive_router
from app.routes.product_images_public import router as product_images_public_router
from app.routes.sefaz_routes import router as sefaz_router
from app.routes.modulos_routes import router as modulos_router
from app.security.module_access import require_active_module
from app.veterinario_routes import router as veterinario_router  # Módulo Veterinário
from app.banho_tosa_routes import router as banho_tosa_router  # Modulo Banho & Tosa

# ============================================================================
# CAMPANHAS — Motor de Campanhas (Fase 1)
# ============================================================================
from app.campaigns.routes import router as campaigns_router
from app.routes.canal_descontos_routes import router as canal_descontos_router


def _module_dependencies(modulo: str, *, allow_ecommerce_customer: bool = False):
    return [
        Depends(
            require_active_module(
                modulo, allow_ecommerce_customer=allow_ecommerce_customer
            )
        )
    ]


def register_routers(app: FastAPI) -> None:
    """Register application routers in the same precedence order used by main.py."""
    app.include_router(health_check_router, tags=["Infrastructure"])
    app.include_router(error_events_router)
    app.include_router(ops_tenants_router)
    app.include_router(product_images_public_router)

    app.include_router(auth_router, tags=["Autenticação Multi-Tenant"])
    app.include_router(usuarios_router, tags=["Usuários & RBAC"])
    app.include_router(roles_router, tags=["Roles & RBAC"])
    app.include_router(permissions_router, tags=["Permissions & RBAC"])
    app.include_router(clientes_router, tags=["Clientes & Pets"])
    app.include_router(pets_router, tags=["Gestão de Pets"])  # Módulo dedicado separado
    app.include_router(
        veterinario_router,
        tags=["Veterinário"],
        dependencies=_module_dependencies("veterinario"),
    )  # Módulo Veterinário
    app.include_router(
        banho_tosa_router,
        tags=["Banho & Tosa"],
        dependencies=_module_dependencies("banho_tosa"),
    )  # Modulo Banho & Tosa
    app.include_router(
        cadastros_router, tags=["Cadastros - Espécies & Raças"]
    )  # Cadastros básicos
    app.include_router(cliente_info_pdv_router, tags=["Clientes & Pets"])
    app.include_router(
        importacao_router, prefix="/produtos", tags=["Importação de Produtos"]
    )  # ANTES de produtos_router!
    app.include_router(importacao_pessoas_router, tags=["Importação de Pessoas"])
    app.include_router(produtos_router, tags=["Produtos"])
    app.include_router(opcoes_racao_router, tags=["Opções de Ração"])
    app.include_router(
        analise_racoes_router, tags=["Análises de Rações"]
    )  # Fase 4: Dashboard de Análise
    app.include_router(
        pdv_racoes_router, tags=["PDV - Rações Inteligentes"]
    )  # Fase 5: Alertas e Sugestões
    app.include_router(
        sugestoes_racoes_router, tags=["Sugestões Inteligentes - Rações"]
    )  # Fase 6: Detecção e Otimização
    app.include_router(
        ml_racoes_router, tags=["Machine Learning - Rações"]
    )  # Fase 7: Aprendizado e Previsão
    app.include_router(variacoes_router, tags=["Produtos - Variações"])  # Sprint 2
    app.include_router(calculadora_racao_router, tags=["Calculadora de Ração"])
    app.include_router(lembretes_router, tags=["Lembretes de Recorrência"])
    app.include_router(
        relatorio_vendas_router, tags=["Relatório de Vendas"]
    )  # ANTES de vendas_router!
    app.include_router(vendas_router, tags=["Vendas & PDV"])
    app.include_router(caixa_router, tags=["Controle de Caixa"])
    app.include_router(
        nfe_router,
        tags=["Nota Fiscal Eletrônica (NF-e)"],
        dependencies=_module_dependencies("fiscal"),
    )
    app.include_router(estoque_router, tags=["Gestão de Estoque"])
    app.include_router(
        estoque_movimentacoes_manuais_router, tags=["Estoque - Movimentacoes Manuais"]
    )
    app.include_router(estoque_entrada_manual_router, tags=["Estoque - Entrada Manual"])
    app.include_router(estoque_saida_manual_router, tags=["Estoque - Saida Manual"])
    app.include_router(estoque_granel_router, tags=["Estoque - Granel"])
    app.include_router(estoque_transferencia_router, tags=["Estoque - Transferencia"])
    app.include_router(
        estoque_transferencia_parceiro_router, tags=["Estoque - Transferencia Parceiro"]
    )
    app.include_router(estoque_saida_full_router, tags=["Estoque - Saida FULL"])
    app.include_router(estoque_alertas_gerais_router, tags=["Estoque - Alertas Gerais"])
    app.include_router(estoque_relatorios_router, tags=["Estoque - Relatorios"])
    app.include_router(
        estoque_movimentacoes_edicao_router, tags=["Estoque - Movimentacoes Edicao"]
    )
    app.include_router(
        estoque_movimentacoes_consulta_router, tags=["Estoque - Movimentacoes Consulta"]
    )
    app.include_router(estoque_validade_router, tags=["Estoque - Validade"])
    app.include_router(estoque_alertas_router, tags=["Estoque - Alertas Negativo"])
    app.include_router(
        bling_sync_router,
        tags=["Sincronização Bling"],
        dependencies=_module_dependencies("bling"),
    )
    app.include_router(fornecedor_grupos_router, tags=["Grupos de Fornecedores"])
    app.include_router(
        pedidos_compra_router,
        tags=["Pedidos de Compra"],
        dependencies=_module_dependencies("compras"),
    )
    app.include_router(
        notas_entrada_router,
        tags=["Notas de Entrada (XML)"],
        dependencies=_module_dependencies("compras"),
    )
    app.include_router(
        compras_pendencias_router,
        tags=["Compras - Pendencias"],
        dependencies=_module_dependencies("compras"),
    )
    app.include_router(
        contas_pagar_router,
        tags=["Financeiro - Contas a Pagar"],
        dependencies=_module_dependencies("financeiro_erp"),
    )
    app.include_router(tipo_despesa_router, tags=["Cadastros - Tipo de Despesa"])
    app.include_router(
        contas_receber_router,
        tags=["Financeiro - Contas a Receber"],
        dependencies=_module_dependencies("financeiro_erp"),
    )
    app.include_router(
        conciliacao_cartao_router,
        tags=["Financeiro - Conciliação de Cartão"],
        dependencies=_module_dependencies("financeiro_erp"),
    )
    app.include_router(
        conciliacao_bancaria_router,
        tags=["Conciliação Bancária - OFX"],
        dependencies=_module_dependencies("financeiro_erp"),
    )
    app.include_router(
        conciliacao_router,
        tags=["Conciliação de Pagamentos"],
        dependencies=_module_dependencies("financeiro_erp"),
    )
    app.include_router(
        conciliacao_aba1_router,
        tags=["Conciliação Vendas - Aba 1 V2"],
        dependencies=_module_dependencies("financeiro_erp"),
    )
    app.include_router(
        conciliacao_historico_router,
        tags=["Conciliação - Histórico"],
        dependencies=_module_dependencies("financeiro_erp"),
    )
    app.include_router(admin_router, tags=["Administração"])
    app.include_router(formas_pagamento_router, tags=["Formas de Pagamento & PDV"])
    app.include_router(operadoras_router, tags=["Operadoras de Cartão"])
    app.include_router(
        comissoes_router, tags=["Comissões"], dependencies=_module_dependencies("comissoes")
    )
    app.include_router(
        comissoes_demonstrativo_router,
        tags=["Comissões - Demonstrativo"],
        dependencies=_module_dependencies("comissoes"),
    )
    app.include_router(
        comissoes_avancadas_router,
        tags=["Comissões - Avançadas"],
        dependencies=_module_dependencies("comissoes"),
    )
    app.include_router(
        comissoes_diagnostico_router,
        tags=["Comissões - Diagnóstico"],
        dependencies=_module_dependencies("comissoes"),
    )
    app.include_router(
        relatorios_comissoes_router,
        tags=["Comissões - Relatórios Analíticos"],
        dependencies=_module_dependencies("comissoes"),
    )
    app.include_router(
        acertos_router,
        prefix="/acertos",
        tags=["Acertos Financeiros de Parceiros"],
        dependencies=_module_dependencies("financeiro_erp"),
    )

    app.include_router(
        dre_router,
        tags=["Financeiro - DRE"],
        dependencies=_module_dependencies("financeiro_erp"),
    )
    app.include_router(
        dre_canais_router,
        tags=["Financeiro - DRE por Canal"],
        dependencies=_module_dependencies("financeiro_erp"),
    )
    app.include_router(
        dre_plano_contas_router, dependencies=_module_dependencies("financeiro_erp")
    )
    app.include_router(
        dre_classificacao_router,
        tags=["DRE - Classificação Automática"],
        dependencies=_module_dependencies("financeiro_erp"),
    )
    app.include_router(
        contas_bancarias_router,
        tags=["Financeiro - Contas Bancárias"],
        dependencies=_module_dependencies("financeiro_erp"),
    )
    app.include_router(financeiro_router, tags=["Financeiro - Configurações"])
    app.include_router(
        lancamentos_router,
        tags=["Financeiro - Lançamentos"],
        dependencies=_module_dependencies("financeiro_erp"),
    )
    app.include_router(categorias_router, tags=["Financeiro - Categorias"])
    app.include_router(
        bling_router, tags=["Integração Bling"], dependencies=_module_dependencies("bling")
    )
    app.include_router(
        bling_oauth_router, tags=["Bling OAuth"], dependencies=_module_dependencies("bling")
    )
    app.include_router(
        bling_pedido_router,
        tags=["Integração Bling - Pedido"],
        dependencies=_module_dependencies("bling"),
    )
    app.include_router(
        bling_nf_router,
        tags=["Integração Bling - NF"],
        dependencies=_module_dependencies("bling"),
    )
    app.include_router(dashboard_router, tags=["Dashboard Financeiro"])
    app.include_router(
        ia_router,
        tags=["IA - Fluxo de Caixa"],
        dependencies=_module_dependencies("financeiro_erp"),
    )
    app.include_router(
        chat_router,
        tags=["IA - Chat Financeiro"],
        dependencies=_module_dependencies("financeiro_erp"),
    )
    app.include_router(
        dre_ia_router,
        tags=["IA - DRE Inteligente"],
        dependencies=_module_dependencies("financeiro_erp"),
    )
    app.include_router(
        extrato_ia_router,
        tags=["IA - Extrato Bancário (ABA 7)"],
        dependencies=_module_dependencies("financeiro_erp"),
    )
    app.include_router(
        ia_fluxo_router,
        tags=["IA - Fluxo Inteligente"],
        dependencies=_module_dependencies("financeiro_erp"),
    )
    app.include_router(analytics_router, tags=["Analytics - CQRS Read Models"])
    app.include_router(audit_router, tags=["Auditoria (Read-Only)"])
    app.include_router(tributacao_router, tags=["Tributação e Impostos"])
    app.include_router(
        whatsapp_router,
        tags=["WhatsApp IA - Sprint 3"],
        dependencies=_module_dependencies("whatsapp"),
    )  # ✅ REATIVADO Sprint 3
    # app.include_router(whatsapp_router, tags=["WhatsApp CRM"])  # DESATIVADO - Usar novos endpoints WhatsApp IA
    app.include_router(
        segmentacao_router,
        tags=["Segmentação de Clientes"],
        dependencies=_module_dependencies("campanhas"),
    )
    app.include_router(pdv_ai_router, tags=["PDV - IA Contextual"])
    app.include_router(pdv_internal_router, tags=["PDV - Internal API"])
    app.include_router(
        racao_calculadora_internal_router, tags=["Calculadora de Ração - Internal API"]
    )
    app.include_router(
        whatsapp_orchestrator_internal_router,
        tags=["WhatsApp - Internal Orchestrator"],
        dependencies=_module_dependencies("whatsapp"),
    )
    app.include_router(fiscal_sugestao_router, tags=["Fiscal - Sugestões Inteligentes"])
    app.include_router(produto_fiscal_router, tags=["Produto - Fiscal"])
    app.include_router(pdv_fiscal_router, tags=["PDV - Fiscal em Tempo Real"])
    app.include_router(produto_fiscal_v2_router, tags=["Produto - Fiscal V2"])
    app.include_router(empresa_fiscal_router, tags=["Empresa - Configuração Fiscal"])
    app.include_router(
        simples_router,
        tags=["Simples Nacional - Fechamento Mensal"],
        dependencies=_module_dependencies("financeiro_erp"),
    )
    app.include_router(
        auditoria_provisoes_router,
        tags=["Auditoria - Provisões"],
        dependencies=_module_dependencies("financeiro_erp"),
    )
    app.include_router(
        projecao_caixa_router,
        tags=["Projeção de Caixa - IA Determinística"],
        dependencies=_module_dependencies("financeiro_erp"),
    )
    app.include_router(
        simulacao_contratacao_router,
        tags=["Simulação de Contratação - IA Determinística"],
        dependencies=_module_dependencies("rh"),
    )
    app.include_router(
        cargos_router, tags=["RH - Cargos"], dependencies=_module_dependencies("rh")
    )
    app.include_router(
        funcionarios_router,
        tags=["RH - Funcionários"],
        dependencies=_module_dependencies("rh"),
    )
    app.include_router(empresa_config_router, tags=["Empresa - Configuração Geral"])
    app.include_router(pdv_indicadores_router, tags=["PDV - Indicadores e Margens"])
    app.include_router(empresa_router, tags=["Empresa - Configurações"])
    app.include_router(
        configuracoes_entrega_router,
        tags=["Configurações - Entregas"],
        dependencies=_module_dependencies("entregas"),
    )
    app.include_router(
        rotas_entrega_router,
        tags=["Entregas - Rotas"],
        dependencies=_module_dependencies("entregas", allow_ecommerce_customer=True),
    )
    app.include_router(
        acertos_entrega_router,
        tags=["Entregas - Acertos Financeiros"],
        dependencies=_module_dependencies("entregas"),
    )
    app.include_router(
        configuracao_custo_moto_router,
        tags=["Custos - Moto da Loja"],
        dependencies=_module_dependencies("entregas"),
    )
    app.include_router(
        dashboard_entregas_router, dependencies=_module_dependencies("entregas")
    )  # ETAPA 11.1 - Dashboard Financeiro (tags no router)
    app.include_router(
        pendencia_estoque_router, tags=["Pendências de Estoque - Lista de Espera"]
    )

    # ============================================================================
    # WHATSAPP + IA - SPRINT 2 & 4 & 5 & 6 & 7
    # ============================================================================
    app.include_router(whatsapp_webhook_router)  # Webhooks 360dialog (sem auth)
    app.include_router(
        whatsapp_config_router, dependencies=_module_dependencies("whatsapp")
    )  # Configuração (com auth)
    app.include_router(
        whatsapp_handoff_router, dependencies=_module_dependencies("whatsapp")
    )  # Sprint 4: Human Handoff (com auth)
    app.include_router(whatsapp_websocket_router)  # Sprint 5: WebSocket Real-time
    app.include_router(
        whatsapp_api_router, dependencies=_module_dependencies("whatsapp")
    )  # Sprint 6: Tools & Tests (com auth)
    app.include_router(
        whatsapp_analytics_router, dependencies=_module_dependencies("whatsapp")
    )  # Sprint 7: Analytics & Reports (com auth)
    app.include_router(
        whatsapp_security_router, dependencies=_module_dependencies("whatsapp")
    )  # Sprint 8: Security & LGPD (com auth)
    app.include_router(lgpd_router)  # LGPD operacional geral (com auth)
    app.include_router(health_router)  # Sprint 9: Health & Monitoring (sem auth)
    app.include_router(admin_fix_router)  # Correções administrativas

    # ============================================================================
    # E-COMMERCE - Loja Pública
    # ============================================================================
    app.include_router(ecommerce_router)
    app.include_router(ecommerce_auth_router)
    app.include_router(ecommerce_entregador_router)
    app.include_router(ecommerce_public_router)
    app.include_router(ecommerce_cart_router)
    app.include_router(ecommerce_checkout_router)
    app.include_router(ecommerce_webhooks_router)
    app.include_router(
        ecommerce_aparencia_router, dependencies=_module_dependencies("ecommerce")
    )
    app.include_router(
        ecommerce_config_router, dependencies=_module_dependencies("ecommerce")
    )
    app.include_router(ecommerce_payment_config_public_router)
    app.include_router(
        ecommerce_payment_config_router, dependencies=_module_dependencies("ecommerce")
    )
    app.include_router(ecommerce_notify_router)
    app.include_router(
        ecommerce_analytics_router, dependencies=_module_dependencies("ecommerce")
    )
    app.include_router(
        ecommerce_drive_router, dependencies=_module_dependencies("ecommerce")
    )  # Drive pickup — PDV + cliente
    app.include_router(
        sefaz_router, dependencies=_module_dependencies("compras")
    )  # SEFAZ — consulta NF-e por chave
    app.include_router(app_mobile_router)  # App Mobile - Rotas dos clientes
    app.include_router(app_vet_router)  # App Mobile - Veterinario operacional
    app.include_router(app_privacy_router)  # App Mobile - Privacidade/LGPD
    app.include_router(app_banho_tosa_router)  # App Mobile - Banho & Tosa
    app.include_router(
        campaigns_router, dependencies=_module_dependencies("campanhas")
    )  # Motor de Campanhas
    app.include_router(
        canal_descontos_router, dependencies=_module_dependencies("campanhas")
    )  # Descontos Globais por Canal (Ecommerce / App)
    app.include_router(modulos_router)  # Módulos Premium
