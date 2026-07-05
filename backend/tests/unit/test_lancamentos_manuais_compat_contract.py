from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _source(relative_path: str) -> str:
    return (BACKEND_ROOT / relative_path).read_text(encoding="utf-8")


def _function(source: str, signature: str, next_marker: str) -> str:
    return source.split(signature, 1)[1].split(next_marker, 1)[0]


def test_lancamento_manual_mapeia_api_legacy_para_modelo_atual():
    source = _source("app/lancamentos_routes.py")
    criar = _function(
        source,
        "def criar_lancamento_manual(",
        '@router.get("/manuais"',
    )
    bloco_modelo = criar.split("novo_lancamento = LancamentoManual(", 1)[1].split(
        "db.add(novo_lancamento)",
        1,
    )[0]

    assert "data_prevista=" not in bloco_modelo
    assert "data_efetivacao=" not in bloco_modelo
    assert "data_competencia=data_prevista or data_lancamento" in bloco_modelo
    assert "realizado_em=realizado_em" in bloco_modelo
    assert "user_id=current_user.id" in bloco_modelo
    assert "tenant_id=tenant_id" in bloco_modelo


def test_lancamento_manual_respostas_usam_colunas_existentes():
    source = _source("app/lancamentos_routes.py")
    response = source.split("def _build_lancamento_manual_response(", 1)[1].split(
        "def _build_lancamento_recorrente_response(",
        1,
    )[0]

    assert ".data_prevista" not in response
    assert ".data_efetivacao" not in response
    assert ".criado_em" not in response
    assert ".atualizado_em" not in response
    assert "lancamento.data_competencia" in response
    assert "lancamento.realizado_em" in response
    assert "lancamento.created_at" in response
    assert "lancamento.updated_at" in response


def test_lancamento_manual_crud_isola_tenant():
    source = _source("app/lancamentos_routes.py")

    listar = _function(
        source,
        "def listar_lancamentos_manuais(",
        '@router.get("/manuais/{lancamento_id}"',
    )
    obter = _function(
        source,
        "def obter_lancamento_manual(",
        '@router.put("/manuais/{lancamento_id}"',
    )
    atualizar = _function(
        source,
        "def atualizar_lancamento_manual(",
        '@router.delete("/manuais/{lancamento_id}"',
    )
    excluir = _function(
        source,
        "def excluir_lancamento_manual(",
        "# ============= LAN",
    )

    assert "LancamentoManual.tenant_id == tenant_id" in listar
    assert "LancamentoManual.tenant_id == tenant_id" in obter
    assert "LancamentoManual.tenant_id == tenant_id" in atualizar
    assert "LancamentoManual.tenant_id == tenant_id" in excluir
    assert "lancamento.updated_at = datetime.utcnow()" in atualizar


def test_lancamento_recorrente_crud_e_geracao_isolam_tenant():
    source = _source("app/lancamentos_routes.py")
    criar = _function(
        source,
        "def criar_lancamento_recorrente(",
        '@router.get("/recorrentes"',
    )
    listar = _function(
        source,
        "def listar_lancamentos_recorrentes(",
        '@router.get("/recorrentes/{lancamento_id}"',
    )
    gerar = _function(
        source,
        "def gerar_proximas_parcelas(",
        "# ============= FUN",
    )

    assert "gerar_automaticamente=" not in criar
    assert "ativo=lancamento.gerar_automaticamente" in criar
    assert "user_id=current_user.id" in criar
    assert "tenant_id=tenant_id" in criar
    assert "LancamentoRecorrente.tenant_id == tenant_id" in listar
    assert "LancamentoRecorrente.tenant_id == tenant_id" in gerar
    assert "LancamentoManual.tenant_id == tenant_id" in gerar
    assert "data_prevista=" not in gerar
    assert "data_competencia=proxima_data" in gerar
    assert "user_id=current_user.id" in gerar
    assert "tenant_id=tenant_id" in gerar


def test_conta_receber_criacao_explica_tenant_em_contas_e_lancamentos():
    source = _source("app/contas_receber_criacao_routes.py")
    criacao = _function(
        source,
        "async def criar_conta_receber(",
        "# ============================================================================\n# LISTAR",
    )
    bloco_lancamento = criacao.split("lancamento = LancamentoManual(", 1)[1].split(
        "db.add(lancamento)",
        1,
    )[0]

    assert criacao.count("tenant_id=tenant_id") >= 4
    assert "data_prevista=" not in bloco_lancamento
    assert "data_efetivacao=" not in bloco_lancamento
    assert "data_competencia=conta_criada.data_vencimento" in bloco_lancamento
    assert 'documento=f"CONTA-RECEBER-{conta_criada.id}"' in bloco_lancamento
    assert "user_id=current_user.id" in bloco_lancamento
    assert "tenant_id=tenant_id" in bloco_lancamento


def test_conta_receber_recorrencia_processa_apenas_tenant_atual():
    source = _source("app/contas_receber_recorrencias_routes.py")
    processar = source.split("async def processar_recorrencias_contas_receber(", 1)[1]
    bloco_lancamento = processar.split("lancamento = LancamentoManual(", 1)[1].split(
        "db.add(lancamento)",
        1,
    )[0]

    assert "current_user, tenant_id = user_and_tenant" in processar
    assert processar.count("ContaReceber.tenant_id == tenant_id") >= 2
    assert "tenant_id=tenant_id" in processar
    assert "db.flush()" in processar.split("lancamento = LancamentoManual(", 1)[0]
    assert "data_prevista=" not in bloco_lancamento
    assert "data_efetivacao=" not in bloco_lancamento
    assert "data_competencia=nova_data_vencimento" in bloco_lancamento
    assert 'documento=f"CONTA-RECEBER-{nova_conta.id}"' in bloco_lancamento
    assert "user_id=current_user.id" in bloco_lancamento
    assert "tenant_id=tenant_id" in bloco_lancamento
