"""
Varredura do registry ORM: isolamento multi-tenant por herança (ratchet).
=========================================================================

Por que este teste existe
--------------------------
O filtro global de tenant com fail-fast (app/tenancy/filters.py) só age sobre
modelos que herdam de ``BaseTenantModel``: ele injeta ``WHERE tenant_id = ?``
automaticamente e LEVANTA ``RuntimeError`` se uma query rodar sem tenant no
contexto.

Há duas formas de um modelo entrar nessa rede:
- herdar ``BaseTenantModel`` (modelos novos: traz id + timestamps + tenant_id); ou
- adotar o mixin ``TenantScoped`` (modelos legados que têm esquema próprio, ex.:
  ``id`` autoincrement e ``criado_em``/``atualizado_em``) — ``class X(TenantScoped, Base)``
  sem alterar o schema.

Modelos que têm coluna ``tenant_id`` mas herdam ``Base`` diretamente (sem o mixin)
ficam FORA dessa rede: não recebem o filtro automático e não disparam o fail-fast.
Eles dependem de um ``WHERE tenant_id == ...`` escrito à mão em cada query. Um único
esquecimento vaza dados entre tenants (lojas) — o pior bug possível num ERP.

Este teste percorre TODOS os modelos mapeados e garante, de forma mecânica, que
nenhum modelo NOVO com ``tenant_id`` escape de ``BaseTenantModel``.

Como funciona (padrão "ratchet" / catraca)
-------------------------------------------
- ``KNOWN_BASE_TENANT_DEBT`` é a fotografia da dívida atual (modelos que hoje têm
  ``tenant_id`` e ainda herdam ``Base`` direto). É a baseline tolerada.
- ``test_nenhum_modelo_novo_*`` FALHA se aparecer um modelo fora dessa baseline
  (ou seja, código novo que reintroduz o problema).
- ``test_baseline_de_debito_so_encolhe`` FALHA se um item da baseline já tiver
  sido corrigido mas não removido da lista — forçando a baseline a só diminuir.
- Meta de longo prazo: esvaziar ``KNOWN_BASE_TENANT_DEBT`` levando cada modelo
  para o filtro automático (via ``TenantScoped`` ou ``BaseTenantModel``), até a
  lista ficar vazia.

Ao migrar um modelo legado com esquema próprio: troque ``class X(Base)`` por
``class X(TenantScoped, Base)`` e remova a declaração própria de ``tenant_id``
(passa a vir do mixin). Se a definição de ``tenant_id`` for idêntica à do mixin
(UUID, NOT NULL, indexada), NÃO há mudança de schema/Alembic. Depois REMOVA a
tabela daqui.
"""
import importlib
import os

import pytest

# Garante defaults de ambiente caso o teste rode isolado (fora do conftest raiz).
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-min-32-chars-long-for-security")


# ---------------------------------------------------------------------------
# Baselines
# ---------------------------------------------------------------------------

# Tabelas que têm coluna tenant_id mas são INTENCIONALMENTE globais (não filtradas
# por tenant). Devem estar alinhadas com TENANT_WHITELIST_TABLES em
# app/tenancy/filters.py. Mantenha esta lista mínima e justificada.
INTENTIONALLY_GLOBAL_TENANT_TABLES = frozenset(
    {
        "user_sessions",  # sessões não são tenant-scoped (já na whitelist do filtro)
        # Observabilidade/operação: cross-tenant POR DESIGN, tenant_id é etiqueta
        # nullable. Lidas só pelo cockpit admin (/admin/observabilidade, protegido por
        # require_admin, com visão cross-tenant) e escritas pelo middleware de captura
        # de erros (roda inclusive antes de haver tenant, ex.: falha de login). Isolar
        # por tenant quebraria o painel de admin e a captura de eventos sem tenant.
        "ops_alerts",
        "ops_error_events",
        # Fila persistente de webhooks do Bling: o worker (process_pending_bling_pedido_
        # webhooks) faz claim cross-tenant SEM tenant no contexto (roda fora de request
        # HTTP); o webhook público enfileira sem sessão. tenant_id é etiqueta nullable.
        # Isolar por tenant quebraria o claim do worker (fail-fast em query sem contexto).
        "bling_pedido_webhook_events",
    }
)

# DÍVIDA ATUAL: modelos com tenant_id que ainda herdam Base direto (fora do filtro
# automático). Esta lista só pode ENCOLHER. Não adicione tabelas aqui para
# "passar" o teste — o objetivo é migrá-las para BaseTenantModel.
KNOWN_BASE_TENANT_DEBT = frozenset(
    {
        # app/campaigns/models.py
        # MIGRADOS para TenantScoped na Leva 1 (sem mudança de schema — a coluna
        # tenant_id foi mantida, pois já é UUID NOT NULL coberta por índice composto
        # ou é parte da PK; o mixin entra só como marcador do filtro):
        #   campaign_locks, campaign_run_log, customer_merge_logs,
        #   customer_rank_history, loyalty_stamps, notification_log.
        # Os demais seguem expostos (worker/scheduler consultam sem contexto de tenant
        # → exigem refatorar os jobs antes de migrar).
        "campaigns",
        "campaign_event_queue",
        "campaign_executions",
        "cashback_transactions",
        "coupons",
        "coupon_redemptions",
        "drawings",
        "drawing_entries",
        "notification_queue",
        # app/comissoes_models.py
        # comissoes_vendas → MIGRADO para TenantScoped (PR comissoes)
        "comissoes_itens",   # tenant_id NULLABLE: requer backfill + ALTER NOT NULL antes de migrar
        # app/conciliacao_models.py — MIGRADO para TenantScoped (PR conciliacao):
        #   adquirentes_templates, arquivos_evidencia, conciliacao_importacoes,
        #   conciliacao_metricas, empresa_parametros
        # app/duplicatas_ignoradas_models.py — MIGRADO para TenantScoped (PR opcoes/duplicatas)
        # app/ia/aba7_models.py
        "dre_periodos",  # tenant_id NULLABLE
        # app/kit_config_fiscal_models.py
        "kit_config_fiscal",
        # app/lgpd_models.py — data_subject_requests MIGRADO (Leva 2: String→UUID + TenantScoped)
        # app/models.py — assinaturas_modulos, ecommerce_notify_requests MIGRADOS (Leva 2: String→UUID)
        # app/models_configuracao_custo_moto.py
        "configuracoes_custo_moto",
        # app/opcoes_racao_models.py — MIGRADO para TenantScoped (PR opcoes/duplicatas):
        #   apresentacoes_peso, fases_publico, linhas_racao, portes_animal, sabores_proteina, tipos_tratamento
        # app/ops_models.py — ops_alerts, ops_error_events DECLARADOS INTENCIONALMENTE
        # GLOBAIS (observabilidade admin cross-tenant) → ver INTENTIONALLY_GLOBAL_TENANT_TABLES.
        # app/pedido_models.py — MIGRADOS (Leva 3: String→UUID + TenantScoped; checkout_real
        # passou a chamar set_current_tenant antes de consultar Pedido)
        # app/produto_config_fiscal_models.py
        "produto_config_fiscal",
        # app/simples_nacional_models.py — simples_nacional_mensal MIGRADO para
        # TenantScoped (tabela colocada sob o Alembic + tenant_id String->UUID; antes
        # nao existia em producao por falta de migration de criacao).
        # app/template_models.py
        "tenant_template_installs",
        "tenant_template_item_installs",
        # app/variacao_config_fiscal_models.py
        "variacao_config_fiscal",
        # app/bling_pedido_webhook_queue_models.py — bling_pedido_webhook_events
        # DECLARADO INTENCIONALMENTE GLOBAL (fila de worker cross-tenant) → ver
        # INTENTIONALLY_GLOBAL_TENANT_TABLES.
        # app/whatsapp/models.py
        "tenant_whatsapp_config",
        "whatsapp_ia_messages",
        "whatsapp_ia_metrics",
        "whatsapp_ia_sessions",
        # app/whatsapp/models_handoff.py
        "whatsapp_agents",
        "whatsapp_handoffs",
        "whatsapp_internal_notes",
        # app/whatsapp/security.py
        "data_access_logs",
        "data_deletion_requests",
        "data_privacy_consents",
        "security_audit_logs",
    }
)

# Subconjunto da dívida em que tenant_id é NULLABLE (risco extra: linhas sem dono).
# Ao tornar NOT NULL + herdar BaseTenantModel, remova daqui e de KNOWN_BASE_TENANT_DEBT.
KNOWN_NULLABLE_TENANT_DEBT = frozenset(
    {
        "comissoes_itens",
        "dre_periodos",
        # ops_alerts, ops_error_events e bling_pedido_webhook_events saíram daqui:
        # agora são INTENTIONALLY_GLOBAL (nullable é esperado em tabela global).
    }
)


# ---------------------------------------------------------------------------
# Introspecção
# ---------------------------------------------------------------------------

def _load_all_models():
    """Força o registro de todos os modelos importando app.main (entrypoint real)."""
    try:
        importlib.import_module("app.main")
    except ModuleNotFoundError as exc:  # ambiente local sem alembic, p.ex.
        if exc.name in {"alembic", "alembic.config"}:
            pytest.skip(
                "Nao foi possivel importar app.main (alembic ausente); "
                "varredura de modelos pulada neste ambiente."
            )
        raise


def _exposed_tenant_models() -> dict:
    """
    Retorna {tablename: (nome_da_classe, tenant_id_nullable)} para todo modelo
    mapeado que tem coluna tenant_id mas NAO herda de BaseTenantModel.
    """
    from app.base_models import BaseTenantModel, TenantScoped
    from app.db import Base

    exposed = {}
    for mapper in Base.registry.mappers:
        cls = mapper.class_
        # "Protegido" = coberto pelo filtro automatico: herda BaseTenantModel
        # (modelos modernos) ou adota o mixin TenantScoped (legados).
        if issubclass(cls, (BaseTenantModel, TenantScoped)):
            continue
        columns = {col.key for col in mapper.columns}
        if "tenant_id" not in columns:
            continue
        tenant_col = mapper.columns["tenant_id"]
        table_name = getattr(cls, "__tablename__", cls.__name__)
        exposed[table_name] = (cls.__name__, bool(tenant_col.nullable))
    return exposed


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------

def test_nenhum_modelo_novo_com_tenant_id_herda_base_direto():
    """Falha se um modelo NOVO com tenant_id herdar Base em vez de BaseTenantModel."""
    _load_all_models()
    exposed = _exposed_tenant_models()
    permitido = INTENTIONALLY_GLOBAL_TENANT_TABLES | KNOWN_BASE_TENANT_DEBT
    novos = {t: exposed[t] for t in exposed if t not in permitido}

    assert not novos, (
        "Modelo(s) com coluna 'tenant_id' herdando Base diretamente foram "
        "introduzidos fora da baseline. Eles NAO entram no filtro automatico de "
        "tenant (app/tenancy/filters.py) e podem vazar dados entre lojas.\n"
        "Corrija herdando de BaseTenantModel (e tenant_id NOT NULL). Se a tabela "
        "for INTENCIONALMENTE global, adicione-a a INTENTIONALLY_GLOBAL_TENANT_TABLES "
        "e a TENANT_WHITELIST_TABLES, com justificativa.\n"
        f"Novos expostos: {sorted(novos)}"
    )


def test_baseline_de_debito_so_encolhe():
    """Garante que a baseline de divida nao tenha itens ja corrigidos (catraca)."""
    _load_all_models()
    exposed_tables = set(_exposed_tenant_models())
    ja_corrigidos = sorted(KNOWN_BASE_TENANT_DEBT - exposed_tables)

    assert not ja_corrigidos, (
        "Estas tabelas constam na baseline KNOWN_BASE_TENANT_DEBT mas nao estao "
        "mais expostas (provavelmente ja migradas para BaseTenantModel ou removidas). "
        "Remova-as de KNOWN_BASE_TENANT_DEBT para a baseline so encolher:\n"
        f"{ja_corrigidos}"
    )


def test_tenant_id_nullable_apenas_na_baseline_conhecida():
    """Falha se um novo modelo exposto tiver tenant_id NULLABLE fora da baseline."""
    _load_all_models()
    exposed = _exposed_tenant_models()
    nullable_agora = {
        table
        for table, (_, nullable) in exposed.items()
        if nullable and table not in INTENTIONALLY_GLOBAL_TENANT_TABLES
    }
    novos_nullable = sorted(nullable_agora - KNOWN_NULLABLE_TENANT_DEBT)

    assert not novos_nullable, (
        "Modelo(s) com tenant_id NULLABLE fora da baseline conhecida. tenant_id "
        "deve ser NOT NULL em tabelas tenant-scoped (linha sem dono = risco de "
        "vazamento/dados orfaos).\n"
        f"Novos nullable: {novos_nullable}"
    )
