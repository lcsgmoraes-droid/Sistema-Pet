from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _source(relative_path: str) -> str:
    return (BACKEND_ROOT / relative_path).read_text(encoding="utf-8")


def test_baixa_contas_receber_da_venda_filtra_venda_e_forma_por_tenant():
    source = _source("app/financeiro/contas_receber_service.py")
    baixar = source.split("def baixar_contas_da_venda(", 1)[1].split(
        "def atualizar_lancamentos_venda(",
        1,
    )[0]

    assert "ContaReceber.tenant_id == tenant_id" in baixar
    assert "FormaPagamento.tenant_id == tenant_id" in baixar
    assert "FormaPagamento.ativo.is_(True)" in baixar


def test_lancamentos_da_venda_sao_baixados_no_tenant_correto():
    source = _source("app/financeiro/contas_receber_service.py")
    atualizar = source.split("def atualizar_lancamentos_venda(", 1)[1].split(
        "# ============================================================================\n# FUN",
        1,
    )[0]

    assert "LancamentoManual.tenant_id == tenant_id" in atualizar


def test_pagamento_conta_pagar_atualiza_lancamento_automatico_da_propria_conta():
    source = _source("app/financeiro/contas_pagar_pagamento_routes.py")
    registrar = source.split("async def registrar_pagamento(", 1)[1].split(
        "# ============================================================================\n# DASHBOARD / RESUMO",
        1,
    )[0]
    bloco_lancamento = registrar.split("# Buscar lan", 1)[1].split(
        "if lancamento:",
        1,
    )[0]

    assert "LancamentoManual.tenant_id == tenant_id" in bloco_lancamento
    assert 'LancamentoManual.documento == f"CONTA-PAGAR-{conta.id}"' in bloco_lancamento
    assert "LancamentoManual.observacoes" in bloco_lancamento
    assert 'f"Gerado automaticamente da conta a pagar #{conta.id}"' in bloco_lancamento
    assert "LancamentoManual.valor == conta.valor_original" not in bloco_lancamento


def test_dashboard_contas_pagar_soma_apenas_contas_do_tenant():
    source = _source("app/financeiro/contas_pagar_pagamento_routes.py")
    dashboard = source.split("def dashboard_contas_pagar(", 1)[1]

    assert dashboard.count("ContaPagar.tenant_id == tenant_id") >= 5


def test_lancamento_automatico_de_conta_pagar_registra_origem_e_tenant():
    source = _source("app/financeiro/contas_pagar_criacao_routes.py")
    bloco_integracao = source.split(
        "# INTEGRA",
        1,
    )[1].split("db.commit()", 1)[0]

    assert 'documento=f"CONTA-PAGAR-{conta_criada.id}"' in bloco_integracao
    assert "data_competencia=conta_criada.data_vencimento" in bloco_integracao
    assert "data_prevista=" not in bloco_integracao
    assert "data_efetivacao=" not in bloco_integracao
    assert "user_id=current_user.id" in bloco_integracao
    assert "tenant_id=tenant_id" in bloco_integracao


def test_lancamento_automatico_de_recorrencia_guarda_id_da_conta_gerada():
    source = _source("app/financeiro/contas_pagar_recorrencia.py")
    gerar = source.split("def _gerar_contas_recorrentes_ate_janela(", 1)[1].split(
        "def _garantir_janela_recorrencia_apos_pagamento(",
        1,
    )[0]

    assert "db.flush()" in gerar.split("lancamento = LancamentoManual(", 1)[0]
    assert 'f"Gerado automaticamente da conta a pagar #{nova_conta.id} ' in gerar
