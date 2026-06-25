import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../../../api";
import { formatMoneyCellValue } from "../../../components/ui/MoneyCell";

export default function useComissoesListagemController() {
  const navigate = useNavigate();
  // Estados - Listagem
  const [comissoes, setComissoes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState(null);

  // Estados - Resumo
  const [resumo, setResumo] = useState(null);
  const [loadingResumo, setLoadingResumo] = useState(true);
  const [erroResumo, setErroResumo] = useState(null);

  // Estados - Detalhe
  const [comissaoSelecionada, setComissaoSelecionada] = useState(null);

  // Estados - Filtros
  const [filtros, setFiltros] = useState({
    funcionario_id: "",
    status: "",
    data_inicio: "",
    data_fim: "",
    venda_id: "",
    produto_id: "", // NOVO
    grupo_id: "", // NOVO
  });

  // Estados - Filtros Avançados
  const [tipoFiltroData, setTipoFiltroData] = useState("ate_hoje"); // 'ate_hoje', 'personalizado'
  const [produtosDisponiveis, setProdutosDisponiveis] = useState([]);
  const [gruposDisponiveis, setGruposDisponiveis] = useState([]);
  const [produtoSelecionado, setProdutoSelecionado] = useState(null);
  const [grupoSelecionado, setGrupoSelecionado] = useState(null);
  const [termoBuscaProduto, setTermoBuscaProduto] = useState("");
  const [termoBuscaGrupo, setTermoBuscaGrupo] = useState("");
  const [mostrarDropdownProduto, setMostrarDropdownProduto] = useState(false);
  const [mostrarDropdownGrupo, setMostrarDropdownGrupo] = useState(false);

  // Estados - Autocomplete de Funcionários
  const [funcionariosDisponiveis, setFuncionariosDisponiveis] = useState([]);
  const [funcionarioSelecionado, setFuncionarioSelecionado] = useState(null);
  const [loadingFuncionarios, setLoadingFuncionarios] = useState(false);
  const [termoBuscaFuncionario, setTermoBuscaFuncionario] = useState("");
  const [mostrarDropdownFuncionario, setMostrarDropdownFuncionario] = useState(false);

  // Estados - Fechamento de Comissões
  const [comissoesSelecionadas, setComissoesSelecionadas] = useState([]);
  const [mostrarModalFechamento, setMostrarModalFechamento] = useState(false);
  const [dataPagamento, setDataPagamento] = useState("");
  const [observacaoFechamento, setObservacaoFechamento] = useState("");
  const [loadingFechamento, setLoadingFechamento] = useState(false);

  // NOVOS Estados para Modal de Fechamento Avançado
  const [tipoPagamento, setTipoPagamento] = useState("sem_pagar"); // 'sem_pagar', 'com_pagamento'
  const [formaPagamento, setFormaPagamento] = useState("");
  const [contaBancariaId, setContaBancariaId] = useState("");
  const [valorTotalEditavel, setValorTotalEditavel] = useState(0);
  const [formasPagamentoDisponiveis, setFormasPagamentoDisponiveis] = useState([]);
  const [contasBancarias, setContasBancarias] = useState([]);

  // Funcionário fixo para resumo (será parametrizável depois)
  const FUNCIONARIO_ID = 1;

  // Carregar comissões e resumo ao montar o componente
  useEffect(() => {
    console.log("[ComissoesListagem] Iniciando carregamento...");

    const init = async () => {
      try {
        await carregarComissoes();
        await carregarResumo();
        await carregarFuncionarios();
        await carregarProdutos();
        await carregarGrupos();
        await carregarFormasPagamento();
        await carregarContasBancarias();
      } catch (err) {
        console.error("[ComissoesListagem] Erro no carregamento inicial:", err);
      }
    };

    init();

    // Setar filtro de data padrão "até hoje"
    const hoje = new Date().toISOString().split("T")[0];
    setFiltros((prev) => ({
      ...prev,
      data_fim: hoje,
    }));
  }, []);

  // Fechar dropdown ao clicar fora
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (mostrarDropdownFuncionario && !event.target.closest(".autocomplete-container")) {
        setMostrarDropdownFuncionario(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [mostrarDropdownFuncionario]);

  const carregarComissoes = async () => {
    console.log("[carregarComissoes] Iniciando...");
    try {
      setLoading(true);
      setErro(null);

      // Construir query params a partir dos filtros
      const params = new URLSearchParams();

      if (filtros.funcionario_id) {
        params.append("funcionario_id", filtros.funcionario_id);
      }
      if (filtros.status) {
        params.append("status", filtros.status);
      }
      if (filtros.data_inicio) {
        params.append("data_inicio", filtros.data_inicio);
      }
      if (filtros.data_fim) {
        params.append("data_fim", filtros.data_fim);
      }
      if (filtros.venda_id) {
        params.append("venda_id", filtros.venda_id);
      }

      const queryString = params.toString();
      const url = queryString ? `/comissoes?${queryString}` : "/comissoes";

      const response = await api.get(url);

      if (response.data.success) {
        setComissoes(response.data.lista);
      } else {
        setErro("Erro ao carregar comissões");
      }
    } catch (error) {
      console.error("Erro ao carregar comissões:", error);
      setErro(error.response?.data?.detail || "Erro ao conectar com o servidor");
    } finally {
      setLoading(false);
      console.log("[carregarComissoes] Finalizado");
    }
  };

  const carregarResumo = async () => {
    try {
      setLoadingResumo(true);
      setErroResumo(null);

      const response = await api.get(`/comissoes/resumo?funcionario_id=${FUNCIONARIO_ID}`);

      if (response.data.success) {
        setResumo(response.data.resumo);
      } else {
        setErroResumo("Erro ao carregar resumo");
      }
    } catch (error) {
      console.error("Erro ao carregar resumo:", error);
      setErroResumo(error.response?.data?.detail || "Erro ao carregar resumo");
    } finally {
      setLoadingResumo(false);
    }
  };

  const carregarFuncionarios = async () => {
    try {
      setLoadingFuncionarios(true);

      const response = await api.get("/comissoes/funcionarios");

      if (response.data.success) {
        // Aceitar tanto 'lista' quanto 'data' para compatibilidade
        const lista = Array.isArray(response.data.lista)
          ? response.data.lista
          : Array.isArray(response.data.data)
            ? response.data.data
            : [];
        setFuncionariosDisponiveis(lista);
      }
    } catch (error) {
      console.error("Erro ao carregar funcionários:", error);
      // Em caso de erro, garantir array vazio
      setFuncionariosDisponiveis([]);
    } finally {
      setLoadingFuncionarios(false);
    }
  };

  const carregarProdutos = async () => {
    try {
      const response = await api.get("/produtos/");
      if (response.data) {
        setProdutosDisponiveis(Array.isArray(response.data) ? response.data : []);
      }
    } catch (error) {
      console.error("Erro ao carregar produtos:", error);
      setProdutosDisponiveis([]);
    }
  };

  const carregarGrupos = async () => {
    try {
      const response = await api.get("/categorias-financeiras");
      if (response.data) {
        setGruposDisponiveis(Array.isArray(response.data) ? response.data : []);
      }
    } catch (error) {
      console.error("Erro ao carregar grupos:", error);
      setGruposDisponiveis([]);
    }
  };

  const carregarFormasPagamento = async () => {
    console.log("[carregarFormasPagamento] Iniciando...");
    try {
      const response = await api.get("/comissoes/formas-pagamento");
      if (response.data) {
        setFormasPagamentoDisponiveis(Array.isArray(response.data) ? response.data : []);
      }
    } catch (error) {
      console.error("[carregarFormasPagamento] Erro:", error);
    } finally {
      console.log("[carregarFormasPagamento] Finalizado");
    }
  };

  const carregarContasBancarias = async () => {
    try {
      const response = await api.get("/contas-bancarias");
      if (response.data) {
        setContasBancarias(
          Array.isArray(response.data) ? response.data.filter((c) => c.ativa) : [],
        );
      }
    } catch (error) {
      console.error("Erro ao carregar contas bancárias:", error);
    }
  };

  // Calcular total das comissões pendentes filtradas (para rodapé)
  const calcularTotalFiltrado = () => {
    const comissoesPendentes = comissoes.filter((c) => c.status === "pendente");
    return comissoesPendentes.reduce((sum, c) => sum + (c.valor_comissao_gerada || 0), 0);
  };

  // Calcular total das comissões selecionadas
  const calcularTotalSelecionado = () => {
    const comissoesSel = comissoes.filter((c) => comissoesSelecionadas.includes(c.id));
    return comissoesSel.reduce((sum, c) => sum + (c.valor_comissao_gerada || 0), 0);
  };

  // Abrir detalhe da comissão
  const abrirDetalhe = (comissaoId) => {
    setComissaoSelecionada(comissaoId);
  };

  // Fechar detalhe
  const fecharDetalhe = () => {
    setComissaoSelecionada(null);
  };

  // Atualizar campo de filtro
  const handleFiltroChange = (campo, valor) => {
    setFiltros((prev) => ({
      ...prev,
      [campo]: valor,
    }));
  };

  // Aplicar filtros
  const aplicarFiltros = () => {
    carregarComissoes();
  };

  // Limpar filtros
  const limparFiltros = () => {
    const filtrosLimpos = {
      funcionario_id: "",
      status: "",
      data_inicio: "",
      data_fim: "",
      venda_id: "",
      produto_id: "",
      grupo_id: "",
    };
    setFiltros(filtrosLimpos);
    setFuncionarioSelecionado(null);
    setProdutoSelecionado(null);
    setGrupoSelecionado(null);
    setTermoBuscaFuncionario("");
    setTermoBuscaProduto("");
    setTermoBuscaGrupo("");
    setTipoFiltroData("ate_hoje");

    // Setar "até hoje" novamente
    const hoje = new Date().toISOString().split("T")[0];
    setTimeout(() => {
      const loadSemFiltros = async () => {
        try {
          setLoading(true);
          const response = await api.get(`/comissoes?data_fim=${hoje}`);
          if (response.data.success) {
            setComissoes(response.data.lista);
          }
        } catch (error) {
          console.error("Erro:", error);
        } finally {
          setLoading(false);
        }
      };
      loadSemFiltros();
    }, 100);
  };

  // Selecionar produto do autocomplete
  const selecionarProduto = (produto) => {
    setProdutoSelecionado(produto);
    setTermoBuscaProduto(produto.nome);
    setMostrarDropdownProduto(false);
    setFiltros((prev) => ({ ...prev, produto_id: produto.id }));
  };

  // Selecionar grupo do autocomplete
  const selecionarGrupo = (grupo) => {
    setGrupoSelecionado(grupo);
    setTermoBuscaGrupo(grupo.nome);
    setMostrarDropdownGrupo(false);
    setFiltros((prev) => ({ ...prev, grupo_id: grupo.id }));
  };

  // Selecionar funcionário do autocomplete
  const selecionarFuncionario = (funcionario) => {
    setFuncionarioSelecionado(funcionario);
    setTermoBuscaFuncionario(funcionario.nome);
    setMostrarDropdownFuncionario(false);
    // Atualizar filtros com o ID do funcionário
    setFiltros((prev) => ({
      ...prev,
      funcionario_id: funcionario.id,
    }));
  };

  // Filtrar funcionários pela busca (proteção defensiva)
  const funcionariosFiltrados = (funcionariosDisponiveis || []).filter((func) =>
    func?.nome?.toLowerCase().includes(termoBuscaFuncionario.toLowerCase()),
  );

  // ========== FUNÇÕES DE FECHAMENTO ==========

  // Toggle seleção de comissão individual
  const toggleSelecaoComissao = (comissaoId, status) => {
    // Não permitir selecionar comissões já pagas ou estornadas
    if (status !== "pendente") return;

    setComissoesSelecionadas((prev) => {
      if (prev.includes(comissaoId)) {
        return prev.filter((id) => id !== comissaoId);
      } else {
        return [...prev, comissaoId];
      }
    });
  };

  // Selecionar/desselecionar todas as comissões pendentes
  const toggleSelecionarTodas = () => {
    const comissoesPendentes = comissoes.filter((c) => c.status === "pendente");

    if (comissoesSelecionadas.length === comissoesPendentes.length) {
      // Se todas estão selecionadas, desselecionar
      setComissoesSelecionadas([]);
    } else {
      // Selecionar todas pendentes
      setComissoesSelecionadas(comissoesPendentes.map((c) => c.id));
    }
  };

  // Abrir modal de fechamento
  const abrirModalFechamento = () => {
    // Setar data padrão como hoje
    const hoje = new Date().toISOString().split("T")[0];
    setDataPagamento(hoje);
    setObservacaoFechamento("");
    setTipoPagamento("sem_pagar");
    setFormaPagamento("");
    setContaBancariaId("");

    // Calcular total das comissões selecionadas
    const total = calcularTotalSelecionado();
    setValorTotalEditavel(total);

    setMostrarModalFechamento(true);
  };

  // Fechar modal
  const fecharModalFechamento = () => {
    setMostrarModalFechamento(false);
    setDataPagamento("");
    setObservacaoFechamento("");
  };

  // Confirmar fechamento
  const confirmarFechamento = async () => {
    if (!dataPagamento) {
      alert("Por favor, informe a data de pagamento");
      return;
    }

    if (tipoPagamento === "com_pagamento" && !contaBancariaId) {
      alert("Por favor, selecione a conta bancária para o pagamento");
      return;
    }

    try {
      setLoadingFechamento(true);

      let response;

      if (tipoPagamento === "sem_pagar") {
        // Fechamento simples (sem pagamento)
        response = await api.post("/comissoes/fechar", {
          comissoes_ids: comissoesSelecionadas,
          data_pagamento: dataPagamento,
          observacao: observacaoFechamento || null,
        });
      } else {
        // Fechamento com pagamento (usando endpoint avançado)
        const params = new URLSearchParams({
          valor_pago: valorTotalEditavel.toString(),
          forma_pagamento: formaPagamento || "nao_informado",
          data_pagamento: dataPagamento,
        });

        if (contaBancariaId) {
          params.append("conta_bancaria_id", contaBancariaId);
        }

        if (observacaoFechamento) {
          params.append("observacoes", observacaoFechamento);
        }

        // Adicionar IDs das comissões
        comissoesSelecionadas.forEach((id) => {
          params.append("comissoes_ids", id);
        });

        response = await api.post(`/comissoes/fechar-com-pagamento?${params.toString()}`);
      }

      if (response.data.success) {
        // Feedback de sucesso
        const valorTotal =
          tipoPagamento === "sem_pagar"
            ? response.data.valor_total_fechamento
            : response.data.valor_total_pago;

        alert(
          `✅ ${response.data.total_processadas} comissão(ões) fechada(s) com sucesso!\n\n` +
            `Valor total: ${formatarMoeda(valorTotal)}\n` +
            `Modo: ${tipoPagamento === "sem_pagar" ? "Sem pagamento (para pagar depois)" : "Com pagamento no ato"}`,
        );

        // Recarregar dados
        await carregarComissoes();
        await carregarResumo();

        // Limpar seleção e fechar modal
        setComissoesSelecionadas([]);
        fecharModalFechamento();
      }
    } catch (error) {
      console.error("Erro ao fechar comissões:", error);
      alert("❌ Erro ao fechar comissões: " + (error.response?.data?.detail || error.message));
    } finally {
      setLoadingFechamento(false);
    }
  };

  const formatarMoeda = (valor) => {
    return formatMoneyCellValue(valor);
  };

  const irParaRelatorios = () => navigate("/comissoes/relatorios");
  const irParaHistoricoFechamentos = () => navigate("/comissoes/fechamentos");

  return {
    abrirDetalhe,
    abrirModalFechamento,
    aplicarFiltros,
    calcularTotalFiltrado,
    calcularTotalSelecionado,
    carregarComissoes,
    comissaoSelecionada,
    comissoes,
    comissoesSelecionadas,
    confirmarFechamento,
    contaBancariaId,
    contasBancarias,
    dataPagamento,
    erro,
    erroResumo,
    fecharDetalhe,
    fecharModalFechamento,
    filtros,
    formaPagamento,
    formasPagamentoDisponiveis,
    formatarMoeda,
    funcionarioSelecionado,
    funcionariosFiltrados,
    grupoSelecionado,
    gruposDisponiveis,
    handleFiltroChange,
    irParaHistoricoFechamentos,
    irParaRelatorios,
    limparFiltros,
    loading,
    loadingFechamento,
    loadingFuncionarios,
    loadingResumo,
    mostrarDropdownFuncionario,
    mostrarDropdownGrupo,
    mostrarDropdownProduto,
    mostrarModalFechamento,
    observacaoFechamento,
    produtoSelecionado,
    produtosDisponiveis,
    resumo,
    selecionarFuncionario,
    selecionarGrupo,
    selecionarProduto,
    setComissoesSelecionadas,
    setContaBancariaId,
    setDataPagamento,
    setFiltros,
    setFormaPagamento,
    setFuncionarioSelecionado,
    setGrupoSelecionado,
    setMostrarDropdownFuncionario,
    setMostrarDropdownGrupo,
    setMostrarDropdownProduto,
    setObservacaoFechamento,
    setProdutoSelecionado,
    setTermoBuscaFuncionario,
    setTermoBuscaGrupo,
    setTermoBuscaProduto,
    setTipoFiltroData,
    setTipoPagamento,
    setValorTotalEditavel,
    termoBuscaFuncionario,
    termoBuscaGrupo,
    termoBuscaProduto,
    tipoFiltroData,
    tipoPagamento,
    toggleSelecaoComissao,
    toggleSelecionarTodas,
    valorTotalEditavel,
  };
}
