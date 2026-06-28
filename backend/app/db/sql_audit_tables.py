"""Table catalog used by SQL audit risk classification."""

# Multi-tenant tables that require tenant filtering when accessed through raw SQL.
TENANT_TABLES = {
    # Comissoes
    "comissoes_itens",
    "comissoes_vendedores",
    "comissoes_configuracao",
    "comissoes_provisoes",
    "comissoes_estornos",
    # Vendas
    "vendas",
    "venda_baixas",
    "venda_itens",
    "venda_pagamentos",
    "vendas_itens",
    "vendas_pagamentos",
    # Estoque
    "produtos",
    "produto_bling_sync",
    "produto_bling_sync_queue",
    "produto_granel_vinculos",
    "produto_imagens",
    "produto_kit_componentes",
    "produtos_historico_precos",
    "locais_estoque",
    "estoque_movimentacoes",
    "estoque_reservas",
    # Financeiro
    "contas_pagar",
    "contas_receber",
    "ecommerce_payment_gateway_configs",
    "lancamentos_financeiros",
    "caixa_movimentacoes",
    "conciliacao_cartao",
    # Clientes/Pets
    "canal_descontos",
    "clientes",
    "pets",
    "agendamentos",
    # Notas fiscais
    "nota_fiscal_item_rateio_canal",
    "nota_fiscal_rateio_canal",
    "notas_entrada",
    "notas_entrada_itens",
    "notas_saida",
    "notas_saida_itens",
    # Pedidos
    "pedido_itens",
    "pedidos",
    "pedidos_compra",
    "pedidos_compra_itens",
    "pedidos_integrados",
    "pedidos_integrados_itens",
    # Configuracoes por tenant
    "usuarios",
    "funcionarios",
    "cargos",
    "permissions_users",
    # WhatsApp
    "whatsapp_messages",
    "whatsapp_contacts",
    "conversas_ia",
    "mensagens_chat",
    "contexto_financeiro_chat",
    # Relatorios
    "dre_categorias_analise",
    "dre_comparacoes",
    "dre_detalhe_canais",
    "dre_insights",
    "dre_lancamentos",
    "dre_periodos",
    "dre_plano_contas",
    "dre_produtos",
    "indices_mercado",
}

# System/global tables that do not require tenant filtering.
WHITELIST_TABLES = {
    # Autenticacao e controle
    "tenants",
    "permissions",
    "roles",
    "sessions",
    # Sistema
    "alembic_version",
    "migrations",
    # Catalogos globais
    "fiscal_catalogo_produtos",
    "fiscal_estado_padrao",
    # PostgreSQL system
    "pg_catalog",
    "information_schema",
}
