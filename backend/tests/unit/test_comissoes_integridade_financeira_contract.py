from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND = REPO_ROOT / "backend" / "app"


def _source(relative_path: str) -> str:
    return (BACKEND / relative_path).read_text(encoding="utf-8")


def test_fechamento_reutiliza_provisao_sem_duplicar_despesa():
    source = _source("comissoes_demonstrativo_fechamento.py")

    assert "status = 'fechada'" in source
    assert "conta_pagar_id" in source
    assert "comissao_provisionada" in source
    assert "ContaPagar(" not in source
    assert "LancamentoManual(" not in source


def test_pagamento_baixa_conta_existente_e_aceita_valor_parcial():
    source = _source("comissoes_avancadas/pagamento_routes.py")

    assert "payload: FecharComissaoComPagamento" in source
    assert "aplicar_pagamento_conta_pagar(" in source
    assert 'novo_status = "pago" if novo_saldo == 0 else "fechada"' in source
    assert "valor_solicitado > limite_pagamento" in source
    assert '"saldo_liquidavel": min(saldo, saldo_conta)' in source
    assert 'item["conta"].status == "pago"' in source
    assert "conta_bancaria_id: int" in _source("comissoes_avancadas_models.py")
    assert "ContaPagar(" not in source
    assert "comissoes_dividas" not in source


def test_estorno_cancela_provisao_e_reverte_dre_sem_commit_intermediario():
    estorno = _source("comissoes_estorno.py")
    financeiro = _source("comissoes_financeiro_service.py")
    provisao = _source("comissoes_provisao.py")

    assert "cancelar_provisoes_comissao_venda(" in estorno
    assert "valor=-valor" in financeiro
    assert 'status = "cancelado"' in financeiro
    assert "commit=False" in financeiro
    assert "commit=False" in provisao

    pagamento = _source("financeiro/contas_pagar_pagamento_service.py")
    recorrencia = pagamento.split("def _sincronizar_recorrencia_pos_pagamento(", 1)[1]
    assert "commit=False" in recorrencia


def test_configuracao_sistema_e_protegida_por_tenant():
    tenant_safe = _source("utils/tenant_safe_sql.py")
    models = _source("comissoes_models.py")

    assert '"comissoes_configuracoes_sistema"' in tenant_safe
    assert "WHERE {tenant_filter}" in models
    assert "ON CONFLICT (tenant_id) DO NOTHING" in models


def test_acerto_de_parceiro_fecha_comissoes_reais_e_valida_provisao():
    source = _source("services/acerto_service.py")

    assert "ComissaoItem.funcionario_id == parceiro_id" in source
    assert 'ComissaoItem.status == "pendente"' in source
    assert "ComissaoItem.data_criacao >= periodo_inicio" in source
    assert 'comissao.status = "fechada"' in source
    assert "comissao.data_fechamento = data_acerto.date()" in source
    assert "comissao.comissao_provisionada" in source
    assert '"status": "simulado"' not in source
