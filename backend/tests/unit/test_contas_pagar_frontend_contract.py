from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_contas_pagar_tem_atalhos_de_periodo():
    source = (REPO_ROOT / "frontend/src/components/ContasPagar.jsx").read_text(
        encoding="utf-8"
    )

    assert "PERIODOS_RAPIDOS_CONTAS_PAGAR" in source
    assert "Hoje" in source
    assert "Amanha" in source
    assert "Semana" in source
    assert "Mes" in source
    assert "calcularIntervaloPeriodoRapido" in source
    assert "aplicarPeriodoRapido" in source
    assert "periodo_rapido" in source
    assert "filtros.periodo_rapido === periodo.value" in source


def test_contas_pagar_lista_abre_edicao_de_lancamento():
    source = (REPO_ROOT / "frontend/src/components/ContasPagar.jsx").read_text(
        encoding="utf-8"
    )

    assert "const [contaEdicao, setContaEdicao]" in source
    assert "abrirModalEdicao" in source
    assert "api.get(`/contas-pagar/${conta.id}`)" in source
    assert "Editar" in source
    assert "contaEdicao={contaEdicao}" in source


def test_modal_conta_pagar_suporta_modo_edicao():
    source = (REPO_ROOT / "frontend/src/components/ModalNovaContaPagar.jsx").read_text(
        encoding="utf-8"
    )

    assert "contaEdicao" in source
    assert "isEditando" in source
    assert "api.patch(`/contas-pagar/${contaEdicao.id}`" in source
    assert "Editar Conta a Pagar" in source
    assert "Salvar Alteracoes" in source


def test_contas_pagar_lista_edita_e_exclui_sem_botao_ver():
    source = (REPO_ROOT / "frontend/src/components/ContasPagar.jsx").read_text(
        encoding="utf-8"
    )

    assert "excluirContaPagar" in source
    assert "api.delete(`/contas-pagar/${conta.id}`)" in source
    assert "Excluir" in source
    assert "abrirDetalhes" not in source
    assert "mostrarDetalhes" not in source
    assert 'title="Ver Detalhes"' not in source


def test_edicao_de_conta_pagar_expoe_recorrencia_no_modal():
    source = (REPO_ROOT / "frontend/src/components/ModalNovaContaPagar.jsx").read_text(
        encoding="utf-8"
    )

    assert "eh_recorrente: Boolean(conta?.eh_recorrente)" in source
    assert "tipo_recorrencia: conta?.tipo_recorrencia || 'mensal'" in source
    assert "eh_recorrente: payload.eh_recorrente" in source
    assert (
        "tipo_recorrencia: payload.eh_recorrente ? payload.tipo_recorrencia : null"
        in source
    )

    trecho_recorrencia = source.split("{/* Recorr", 1)[1].split("{/* Parcelamento", 1)[
        0
    ]
    assert "!isEditando" not in trecho_recorrencia


def test_contas_pagar_mantem_acoes_visiveis_com_textos_longos():
    source = (REPO_ROOT / "frontend/src/components/ContasPagar.jsx").read_text(
        encoding="utf-8"
    )

    assert "contas-pagar-actions-cell" in source
    assert "sticky right-0" in source
    assert 'tableClassName="min-w-[1280px]"' in source
    assert "cellStyle: { width: 210, maxWidth: 210 }" in source
    assert "cellStyle: { width: 220, maxWidth: 220 }" in source


def test_contas_pagar_frontend_trata_recorrencia_em_lote():
    source = (REPO_ROOT / "frontend/src/components/ContasPagar.jsx").read_text(
        encoding="utf-8"
    )
    modal_source = (
        REPO_ROOT / "frontend/src/components/ModalNovaContaPagar.jsx"
    ).read_text(encoding="utf-8")

    assert "carregarRecorrenciaExclusao" in source
    assert "recorrenciasSelecionadasExclusao" in source
    assert "confirmarExclusaoRecorrencia" in source
    assert "api.post('/contas-pagar/recorrencias/excluir'" in source
    assert "Lançamentos da recorrência" in source

    assert "aplicar_recorrencia_futura" in modal_source
    assert "Aplicar alterações aos próximos lançamentos" in modal_source


def test_modal_conta_pagar_nao_envia_data_recorrencia_vazia():
    source = (REPO_ROOT / "frontend/src/components/ModalNovaContaPagar.jsx").read_text(
        encoding="utf-8"
    )

    assert "normalizarDataOpcionalRecorrencia" in source
    assert (
        "data_inicio_recorrencia: normalizarDataOpcionalRecorrencia(payload.data_inicio_recorrencia)"
        in source
    )
    assert (
        "data_fim_recorrencia: normalizarDataOpcionalRecorrencia(payload.data_fim_recorrencia)"
        in source
    )


def test_contas_pagar_pagamento_envia_data_e_mostra_erros_legiveis():
    source = (REPO_ROOT / "frontend/src/components/ContasPagar.jsx").read_text(
        encoding="utf-8"
    )
    abrir_modal = source.split("const abrirModalPagamento = (conta) => {", 1)[1].split(
        "const abrirModalEdicao",
        1,
    )[0]

    assert "data_pagamento: formatarDataISO(new Date())" in abrir_modal
    assert "extrairMensagemErroPagamento" in source
    assert "toast.error(extrairMensagemErroPagamento(error))" in source


def test_contas_pagar_pagamento_usa_formas_financeiras_validas():
    source = (REPO_ROOT / "frontend/src/components/ContasPagar.jsx").read_text(
        encoding="utf-8"
    )
    carregar_formas = source.split("const carregarFormasPagamento = async () => {", 1)[
        1
    ].split(
        "const carregarDados = async () => {",
        1,
    )[0]

    assert (
        "api.get('/financeiro/formas-pagamento?apenas_ativas=true')" in carregar_formas
    )
    assert "/comissoes/formas-pagamento" not in carregar_formas
    assert "safeArray(response.data).map" in carregar_formas
    assert (
        "conta_bancaria_destino_id: forma.conta_bancaria_destino_id || null"
        in carregar_formas
    )


def test_contas_pagar_pagamento_nao_mostra_icone_textual_na_forma():
    source = (REPO_ROOT / "frontend/src/components/ContasPagar.jsx").read_text(
        encoding="utf-8"
    )
    modal_pagamento = source.split("Forma de Pagamento</label>", 1)[1].split(
        "Conta Banc",
        1,
    )[0]

    assert "<option key={f.id} value={f.id}>{f.nome}</option>" in modal_pagamento
    assert "{f.icone" not in modal_pagamento


def test_contas_pagar_pagamento_alerta_saldo_negativo_antes_de_baixar():
    source = (REPO_ROOT / "frontend/src/components/ContasPagar.jsx").read_text(
        encoding="utf-8"
    )

    assert "confirmarSaldoNegativoPagamento" in source
    assert "Saldo insuficiente na conta bancaria" in source
    assert "ficara negativo" in source
    assert "window.confirm(mensagem)" in source


def test_contas_pagar_lista_tem_selecao_e_acoes_em_lote():
    source = (REPO_ROOT / "frontend/src/components/ContasPagar.jsx").read_text(
        encoding="utf-8"
    )

    assert "contasSelecionadas" in source
    assert "alternarSelecaoConta" in source
    assert "selecionarTodasContasVisiveis" in source
    assert "contas-pagar-select-all" in source
    assert "contas-pagar-select-row" in source
    assert "Acoes em lote" in source
    assert "Editar selecionado" in source
    assert "Estornar pagamento" in source
    assert "Cancelar lancamento" in source
    assert "Excluir selecionados" in source


def test_contas_pagar_frontend_chama_endpoints_de_estorno_cancelamento_e_exclusao_em_lote():
    source = (REPO_ROOT / "frontend/src/components/ContasPagar.jsx").read_text(
        encoding="utf-8"
    )

    assert "estornarContasSelecionadas" in source
    assert "cancelarContasSelecionadas" in source
    assert "excluirContasSelecionadas" in source
    assert "api.post(`/contas-pagar/${conta.id}/estornar`" in source
    assert "api.post(`/contas-pagar/${conta.id}/cancelar`" in source
    assert "api.post('/contas-pagar/recorrencias/excluir'" in source


def test_modal_conta_pagar_pergunta_antes_de_replicar_nome_recorrente():
    source = (REPO_ROOT / "frontend/src/components/ModalNovaContaPagar.jsx").read_text(
        encoding="utf-8"
    )

    assert "confirmarReplicacaoDescricao" in source
    assert "window.confirm" in source
    assert (
        "Deseja aplicar o novo nome aos próximos lançamentos desta recorrência?"
        in source
    )
