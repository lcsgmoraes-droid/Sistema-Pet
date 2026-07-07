from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def read_repo(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def contas_pagar_source() -> str:
    return "\n".join(
        read_repo(path)
        for path in (
            "frontend/src/components/ContasPagar.jsx",
            "frontend/src/components/contas-pagar/contasPagarHelpers.js",
            "frontend/src/components/contas-pagar/contasPagarFilterHelpers.js",
            "frontend/src/components/contas-pagar/contasPagarDisplayHelpers.js",
            "frontend/src/components/contas-pagar/ContasPagarFilters.jsx",
            "frontend/src/components/contas-pagar/ContasPagarAnalise.jsx",
            "frontend/src/components/contas-pagar/ContasPagarTable.jsx",
            "frontend/src/components/contas-pagar/ContasPagarModals.jsx",
            "frontend/src/components/contas-pagar/ContasPagarPagamentoLoteModal.jsx",
            "frontend/src/components/contas-pagar/useContasPagarSelection.js",
        )
    )


def modal_conta_pagar_source() -> str:
    return "\n".join(
        read_repo(path)
        for path in (
            "frontend/src/components/ModalNovaContaPagar.jsx",
            "frontend/src/components/modalNovaContaPagar/ModalNovaContaPagar.jsx",
            "frontend/src/components/modalNovaContaPagar/useModalNovaContaPagarController.js",
            "frontend/src/components/modalNovaContaPagar/contaPagarFormState.js",
            "frontend/src/components/modalNovaContaPagar/ModalNovaContaPagarDialog.jsx",
            "frontend/src/components/modalNovaContaPagar/ContaPagarBasicFields.jsx",
            "frontend/src/components/modalNovaContaPagar/ContaPagarRecorrenciaSection.jsx",
        )
    )


def test_contas_pagar_foi_dividido_em_componentes_menores():
    arquivos = {
        "frontend/src/components/ContasPagar.jsx": 1000,
        "frontend/src/components/contas-pagar/ContasPagarAnalise.jsx": 500,
        "frontend/src/components/contas-pagar/ContasPagarFilters.jsx": 400,
        "frontend/src/components/contas-pagar/ContasPagarTable.jsx": 500,
        "frontend/src/components/contas-pagar/ContasPagarModals.jsx": 700,
        "frontend/src/components/contas-pagar/ContasPagarPagamentoLoteModal.jsx": 220,
        "frontend/src/components/contas-pagar/contasPagarHelpers.js": 80,
        "frontend/src/components/contas-pagar/contasPagarFilterHelpers.js": 240,
        "frontend/src/components/contas-pagar/contasPagarDisplayHelpers.js": 90,
        "frontend/src/components/contas-pagar/useContasPagarSelection.js": 220,
    }

    for path, limite in arquivos.items():
        linhas = len(read_repo(path).splitlines())
        assert linhas < limite, f"{path} tem {linhas} linhas, limite {limite}"


def test_contas_pagar_tem_atalhos_de_periodo():
    source = contas_pagar_source()

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
    source = contas_pagar_source()

    assert "const [contaEdicao, setContaEdicao]" in source
    assert "abrirModalEdicao" in source
    assert "api.get(`/contas-pagar/${conta.id}`)" in source
    assert "Editar" in source
    assert "contaEdicao={contaEdicao}" in source


def test_modal_conta_pagar_suporta_modo_edicao():
    source = modal_conta_pagar_source()

    assert "contaEdicao" in source
    assert "isEditando" in source
    assert "api.patch(" in source
    assert "`/contas-pagar/${contaEdicao.id}`" in source
    assert "Editar Conta a Pagar" in source
    assert "Salvar Altera" in source


def test_contas_pagar_lista_edita_e_exclui_sem_botao_ver():
    source = contas_pagar_source()

    assert "excluirContaPagar" in source
    assert "api.delete(`/contas-pagar/${conta.id}`)" in source
    assert "Excluir" in source
    assert "abrirDetalhes" not in source
    assert "mostrarDetalhes" not in source
    assert 'title="Ver Detalhes"' not in source


def test_edicao_de_conta_pagar_expoe_recorrencia_no_modal():
    source = modal_conta_pagar_source()

    assert "eh_recorrente: Boolean(conta?.eh_recorrente)" in source
    assert 'tipo_recorrencia: conta?.tipo_recorrencia || "mensal"' in source
    assert "eh_recorrente: payload.eh_recorrente" in source
    assert (
        "tipo_recorrencia: payload.eh_recorrente ? payload.tipo_recorrencia : null"
        in source
    )

    recorrencia_source = read_repo(
        "frontend/src/components/modalNovaContaPagar/ContaPagarRecorrenciaSection.jsx"
    )
    assert "!isEditando" not in recorrencia_source


def test_contas_pagar_mantem_acoes_visiveis_com_textos_longos():
    source = contas_pagar_source()

    assert "contas-pagar-actions-cell" in source
    assert "sticky right-0" in source
    assert 'tableClassName="min-w-[1280px]"' in source
    assert "cellStyle: { width: 210, maxWidth: 210 }" in source
    assert "cellStyle: { width: 220, maxWidth: 220 }" in source


def test_contas_pagar_frontend_trata_recorrencia_em_lote():
    source = contas_pagar_source()
    modal_source = modal_conta_pagar_source()

    assert "carregarRecorrenciaExclusao" in source
    assert "recorrenciasSelecionadasExclusao" in source
    assert "confirmarExclusaoRecorrencia" in source
    assert '"/contas-pagar/recorrencias/excluir"' in source
    assert "Lançamentos da recorrência" in source

    assert "aplicar_recorrencia_futura" in modal_source
    assert "Aplicar alterações aos próximos lançamentos" in modal_source


def test_modal_conta_pagar_nao_envia_data_recorrencia_vazia():
    source = modal_conta_pagar_source()

    assert "normalizarDataOpcionalRecorrencia" in source
    assert "data_inicio_recorrencia:" in source
    assert (
        "normalizarDataOpcionalRecorrencia(payload.data_inicio_recorrencia)" in source
    )
    assert (
        "data_fim_recorrencia: normalizarDataOpcionalRecorrencia(payload.data_fim_recorrencia)"
        in source
    )


def test_contas_pagar_pagamento_envia_data_e_mostra_erros_legiveis():
    source = contas_pagar_source()
    abrir_modal = source.split("const abrirModalPagamento = (conta) => {", 1)[1].split(
        "const abrirModalEdicao",
        1,
    )[0]

    assert "data_pagamento: formatarDataISO(new Date())" in abrir_modal
    assert "extrairMensagemErroPagamento" in source
    assert "toast.error(extrairMensagemErroPagamento(error))" in source


def test_contas_pagar_pagamento_usa_formas_financeiras_validas():
    source = contas_pagar_source()
    carregar_formas = source.split("const carregarFormasPagamento = async () => {", 1)[
        1
    ].split(
        "const carregarDados = async () => {",
        1,
    )[0]

    assert (
        'api.get("/financeiro/formas-pagamento?apenas_ativas=true")' in carregar_formas
    )
    assert "/comissoes/formas-pagamento" not in carregar_formas
    assert "safeArray(response.data).map" in carregar_formas
    assert (
        "conta_bancaria_destino_id: forma.conta_bancaria_destino_id || null"
        in carregar_formas
    )


def test_contas_pagar_pagamento_nao_mostra_icone_textual_na_forma():
    source = read_repo("frontend/src/components/contas-pagar/ContasPagarModals.jsx")
    modal_pagamento = source.split("Forma de Pagamento</label>", 1)[1].split(
        "Conta Banc",
        1,
    )[0]

    assert "<option key={f.id} value={f.id}>" in modal_pagamento
    assert "{f.nome}" in modal_pagamento
    assert "{f.icone" not in modal_pagamento


def test_contas_pagar_pagamento_alerta_saldo_negativo_antes_de_baixar():
    source = contas_pagar_source()

    assert "confirmarSaldoNegativoPagamento" in source
    assert "Saldo insuficiente na conta bancaria" in source
    assert "ficara negativo" in source
    assert "window.confirm(mensagem)" in source


def test_contas_pagar_lista_tem_selecao_e_acoes_em_lote():
    source = contas_pagar_source()

    assert "contasSelecionadas" in source
    assert "contasSelecionadasObjetos" in source
    assert "alternarSelecaoConta" in source
    assert "selecionarTodasContasVisiveis" in source
    assert "contas-pagar-select-all" in source
    assert "contas-pagar-select-row" in source
    assert "Acoes em lote" in source
    assert "Pagar selecionados" in source
    assert "abrirPagamentoEmLote" in source
    assert "Editar selecionado" in source
    assert "Estornar pagamento" in source
    assert "Cancelar lancamento" in source
    assert "Excluir selecionados" in source


def test_contas_pagar_frontend_abre_hoje_e_oculta_taxas_cartao():
    source = contas_pagar_source()

    assert 'periodo_rapido: "hoje"' in source
    assert "criarFiltrosPadraoContasPagar" in source
    assert "ocultar_taxas_cartao" in source
    assert "Taxas de cartao" in source
    assert "Ocultar taxas" in source
    assert "filtrarTaxasCartao" in source


def test_contas_pagar_frontend_tem_modal_de_pagamento_em_lote():
    source = contas_pagar_source()

    assert "mostrarModalPagamentoLote" in source
    assert "dadosPagamentoLote" in source
    assert "registrarPagamentoEmLote" in source
    assert 'api.post("/contas-pagar/pagar-lote"' in source
    assert "Pagamento em lote" in source
    assert "Saldo total selecionado" in source
    assert "conta_ids: contasParaPagamentoLote.map" in source


def test_contas_pagar_frontend_tem_aba_analise_com_exclusao_de_fornecedor():
    source = contas_pagar_source()

    assert "ContasPagarAnalise" in source
    assert "abaAtivaContasPagar" in source
    assert "Lancamentos" in source
    assert "Analise" in source
    assert 'api.get("/contas-pagar/analise-abertos"' in source
    assert "fornecedor_modo" in source
    assert "fornecedor_ids" in source
    assert "Excluir selecionados" in source
    assert "Tudo menos" in source
    assert "proximos_12_meses" in source
    assert "agenda_mensal" in source


def test_contas_pagar_frontend_chama_endpoints_de_estorno_cancelamento_e_exclusao_em_lote():
    source = contas_pagar_source()

    assert "estornarContasSelecionadas" in source
    assert "cancelarContasSelecionadas" in source
    assert "excluirContasSelecionadas" in source
    assert "api.post(`/contas-pagar/${conta.id}/estornar`" in source
    assert "api.post(`/contas-pagar/${conta.id}/cancelar`" in source
    assert '"/contas-pagar/recorrencias/excluir"' in source


def test_modal_conta_pagar_pergunta_antes_de_replicar_nome_recorrente():
    source = modal_conta_pagar_source()

    assert "confirmarReplicacaoDescricao" in source
    assert "window.confirm" in source
    assert (
        "Deseja aplicar o novo nome aos próximos lançamentos desta recorrência?"
        in source
    )
