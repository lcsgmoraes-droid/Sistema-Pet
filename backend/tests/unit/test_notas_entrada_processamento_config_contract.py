from app.notas_entrada.schemas import AtualizarPrecoRequest, ProcessarConfig


def test_processar_config_defaults_preservam_fluxo_atual():
    config = ProcessarConfig()

    assert config.lancar_estoque is True
    assert config.atualizar_custo is True
    assert config.atualizar_preco_venda is True
    assert config.gerar_contas_pagar is True
    assert config.precos_venda_override == []


def test_processar_config_aceita_precos_no_payload_final():
    config = ProcessarConfig(
        atualizar_preco_venda=True,
        precos_venda_override=[{"produto_id": 10, "preco_venda": 42.9}],
    )

    assert isinstance(config.precos_venda_override[0], AtualizarPrecoRequest)
    assert config.precos_venda_override[0].produto_id == 10
