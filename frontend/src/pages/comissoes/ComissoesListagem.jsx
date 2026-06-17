/**
 * DEMONSTRATIVO DE COMISSÕES - LISTAGEM
 *
 * ⚠️ IMPORTANTE: Esta tela consome dados de snapshots imutáveis.
 * Nenhum valor aqui é recalculado. Todos os dados vêm diretamente
 * da tabela comissoes_itens conforme registrado no momento da venda.
 *
 * Criado em: 22/01/2026
 */

import { useState, useEffect } from "react";
import { BarChart3, CheckCircle2, FileText, Filter, History, RotateCcw, X } from "lucide-react";
import { useNavigate } from "react-router-dom";
import api from "../../api";
import ActionButton from "../../components/ui/ActionButton";
import CopyableCode from "../../components/ui/CopyableCode";
import EmptyState from "../../components/ui/EmptyState";
import ErrorState from "../../components/ui/ErrorState";
import LoadingState from "../../components/ui/LoadingState";
import MetricCard from "../../components/ui/MetricCard";
import MetricGrid from "../../components/ui/MetricGrid";
import MoneyCell, { formatMoneyCellValue } from "../../components/ui/MoneyCell";
import NumberCell from "../../components/ui/NumberCell";
import SaleReference from "../../components/ui/SaleReference";
import StatusBadge from "../../components/ui/StatusBadge";
import { formatarDataHoraComissao } from "../../utils/comissoesDate";
import ComissaoDetalhe from "./ComissaoDetalhe";

const ComissoesListagem = () => {
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

  // Formatar data para exibição
  const formatarData = (dataISO) => {
    return formatarDataHoraComissao(dataISO);
  };

  // Formatar valor monetário
  const formatarMoeda = (valor) => {
    return formatMoneyCellValue(valor);
  };

  // Badge de status com cores
  const renderizarStatus = (status) => {
    return <StatusBadge status={status} />;
  };

  // Badge de tipo de cálculo
  const renderizarTipoCalculo = (tipo) => {
    const labels = {
      percentual: "Percentual",
      lucro: "Lucro",
    };

    return (
      <StatusBadge intent={tipo === "lucro" ? "purple" : "info"}>
        {labels[tipo] || tipo || "-"}
      </StatusBadge>
    );
  };

  // Renderizar cards de resumo
  const renderizarCardsResumo = () => {
    if (loadingResumo) {
      return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="bg-white rounded-lg shadow p-6 animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-24 mb-3"></div>
              <div className="h-8 bg-gray-200 rounded w-32"></div>
            </div>
          ))}
        </div>
      );
    }

    if (erroResumo) {
      return (
        <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
          <p className="text-sm text-yellow-800">
            ⚠️ Não foi possível carregar o resumo financeiro
          </p>
        </div>
      );
    }

    if (!resumo) return null;

    const cards = [
      {
        titulo: "Total Gerado",
        valor: resumo.total_gerado,
        intent: "blue",
      },
      {
        titulo: "Total Pago",
        valor: resumo.total_pago,
        intent: "emerald",
      },
      {
        titulo: "Total Pendente",
        valor: resumo.total_pendente,
        intent: "amber",
      },
      {
        titulo: "Saldo a Pagar",
        valor: resumo.saldo_a_pagar,
        intent: "violet",
      },
    ];

    return (
      <MetricGrid className="mb-6">
        {cards.map((card, index) => (
          <MetricCard
            key={index}
            intent={card.intent}
            label={card.titulo}
            value={<MoneyCell value={card.valor} />}
          />
        ))}
      </MetricGrid>
    );
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

  // Renderizar painel de filtros
  const renderizarFiltros = () => {
    // Filtrar produtos e grupos
    const produtosFiltrados = (produtosDisponiveis || []).filter((p) =>
      p?.nome?.toLowerCase().includes(termoBuscaProduto.toLowerCase()),
    );

    const gruposFiltrados = (gruposDisponiveis || []).filter((g) =>
      g?.nome?.toLowerCase().includes(termoBuscaGrupo.toLowerCase()),
    );

    return (
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-gray-800">Filtros</h3>
          <span className="text-xs text-gray-500">
            {comissoes.length} registro{comissoes.length !== 1 ? "s" : ""} encontrado
            {comissoes.length !== 1 ? "s" : ""}
          </span>
        </div>

        {/* Filtro de Período */}
        <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <h4 className="text-sm font-semibold text-gray-700 mb-3">📅 Período</h4>
          <div className="flex gap-4 mb-3">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                value="ate_hoje"
                checked={tipoFiltroData === "ate_hoje"}
                onChange={(e) => {
                  setTipoFiltroData(e.target.value);
                  const hoje = new Date().toISOString().split("T")[0];
                  setFiltros((prev) => ({ ...prev, data_inicio: "", data_fim: hoje }));
                }}
                className="text-blue-600"
              />
              <span className="text-sm font-medium">Até hoje</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                value="personalizado"
                checked={tipoFiltroData === "personalizado"}
                onChange={(e) => setTipoFiltroData(e.target.value)}
                className="text-blue-600"
              />
              <span className="text-sm font-medium">Período personalizado</span>
            </label>
          </div>

          {tipoFiltroData === "personalizado" && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Data Início</label>
                <input
                  type="date"
                  value={filtros.data_inicio}
                  onChange={(e) => handleFiltroChange("data_inicio", e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Data Fim</label>
                <input
                  type="date"
                  value={filtros.data_fim}
                  onChange={(e) => handleFiltroChange("data_fim", e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
          {/* Funcionário (Autocomplete) */}
          <div className="relative autocomplete-container">
            <label className="block text-sm font-medium text-gray-700 mb-1">Funcionário</label>
            <input
              type="text"
              value={termoBuscaFuncionario}
              onChange={(e) => {
                setTermoBuscaFuncionario(e.target.value);
                setMostrarDropdownFuncionario(true);
                if (e.target.value === "") {
                  setFuncionarioSelecionado(null);
                  setFiltros((prev) => ({ ...prev, funcionario_id: "" }));
                }
              }}
              onFocus={() => setMostrarDropdownFuncionario(true)}
              disabled={loadingFuncionarios}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
              placeholder={loadingFuncionarios ? "Carregando..." : "Digite o nome"}
            />

            {mostrarDropdownFuncionario && termoBuscaFuncionario && (
              <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-auto">
                {funcionariosFiltrados.length > 0 ? (
                  funcionariosFiltrados.map((func) => (
                    <div
                      key={func.id}
                      onClick={() => selecionarFuncionario(func)}
                      className="px-3 py-2 hover:bg-blue-50 cursor-pointer transition-colors"
                    >
                      <div className="font-medium text-gray-900">{func.nome}</div>
                      <div className="text-xs text-gray-500">ID: {func.id}</div>
                    </div>
                  ))
                ) : (
                  <div className="px-3 py-2 text-gray-500 text-sm">
                    Nenhum funcionário encontrado
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Produto (Autocomplete) */}
          <div className="relative autocomplete-container">
            <label className="block text-sm font-medium text-gray-700 mb-1">Produto</label>
            <input
              type="text"
              value={termoBuscaProduto}
              onChange={(e) => {
                setTermoBuscaProduto(e.target.value);
                setMostrarDropdownProduto(true);
                if (e.target.value === "") {
                  setProdutoSelecionado(null);
                  setFiltros((prev) => ({ ...prev, produto_id: "" }));
                }
              }}
              onFocus={() => setMostrarDropdownProduto(true)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="Digite o nome do produto"
            />

            {mostrarDropdownProduto && termoBuscaProduto && (
              <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-auto">
                {produtosFiltrados.length > 0 ? (
                  produtosFiltrados.map((prod) => (
                    <div
                      key={prod.id}
                      onClick={() => selecionarProduto(prod)}
                      className="px-3 py-2 hover:bg-blue-50 cursor-pointer transition-colors"
                    >
                      <div className="font-medium text-gray-900">{prod.nome}</div>
                      <div className="text-xs text-gray-500">ID: {prod.id}</div>
                    </div>
                  ))
                ) : (
                  <div className="px-3 py-2 text-gray-500 text-sm">Nenhum produto encontrado</div>
                )}
              </div>
            )}
          </div>

          {/* Grupo/Categoria (Autocomplete) */}
          <div className="relative autocomplete-container">
            <label className="block text-sm font-medium text-gray-700 mb-1">Grupo/Categoria</label>
            <input
              type="text"
              value={termoBuscaGrupo}
              onChange={(e) => {
                setTermoBuscaGrupo(e.target.value);
                setMostrarDropdownGrupo(true);
                if (e.target.value === "") {
                  setGrupoSelecionado(null);
                  setFiltros((prev) => ({ ...prev, grupo_id: "" }));
                }
              }}
              onFocus={() => setMostrarDropdownGrupo(true)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="Digite o nome do grupo"
            />

            {mostrarDropdownGrupo && termoBuscaGrupo && (
              <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-auto">
                {gruposFiltrados.length > 0 ? (
                  gruposFiltrados.map((grupo) => (
                    <div
                      key={grupo.id}
                      onClick={() => selecionarGrupo(grupo)}
                      className="px-3 py-2 hover:bg-blue-50 cursor-pointer transition-colors"
                    >
                      <div className="font-medium text-gray-900">{grupo.nome}</div>
                      <div className="text-xs text-gray-500">ID: {grupo.id}</div>
                    </div>
                  ))
                ) : (
                  <div className="px-3 py-2 text-gray-500 text-sm">Nenhum grupo encontrado</div>
                )}
              </div>
            )}
          </div>

          {/* Status */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
            <select
              value={filtros.status}
              onChange={(e) => handleFiltroChange("status", e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Todos</option>
              <option value="pendente">Pendente</option>
              <option value="pago">Pago</option>
              <option value="estornado">Estornado</option>
            </select>
          </div>
        </div>

        {/* Botões de Ação */}
        <div className="flex gap-3">
          <ActionButton
            onClick={aplicarFiltros}
            disabled={loading}
            icon={Filter}
            intent="edit"
            size="md"
          >
            Filtrar
          </ActionButton>

          <ActionButton
            onClick={limparFiltros}
            disabled={loading}
            icon={X}
            intent="neutral"
            size="md"
            tone="soft"
          >
            Limpar Filtros
          </ActionButton>
        </div>
      </div>
    );
  };

  // Renderização de loading
  if (loading) {
    return <LoadingState className="min-h-screen" label="Carregando comissões..." />;
  }

  // Renderização de erro
  if (erro) {
    return (
      <div className="p-6">
        <ErrorState
          title="Erro ao carregar comissões"
          description={erro}
          action={
            <ActionButton icon={RotateCcw} intent="delete" onClick={carregarComissoes}>
              Tentar novamente
            </ActionButton>
          }
        />
      </div>
    );
  }

  // Renderização de lista vazia
  if (comissoes.length === 0) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold text-gray-800 mb-6">Demonstrativo de Comissões</h1>

        <EmptyState
          description="Ainda não há registros de comissões no sistema."
          icon={FileText}
          title="Nenhuma comissão encontrada"
        />
      </div>
    );
  }

  // Renderização da tabela
  return (
    <div className="p-6">
      {/* Cabeçalho */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Demonstrativo de Comissões</h1>
          <p className="text-gray-600 mt-1">Total de registros: {comissoes.length}</p>
        </div>

        <div className="flex gap-3">
          <ActionButton
            onClick={() => navigate("/comissoes/relatorios")}
            icon={BarChart3}
            intent="info"
            size="md"
            tone="soft"
          >
            Relatórios
          </ActionButton>

          <ActionButton
            onClick={() => navigate("/comissoes/fechamentos")}
            icon={History}
            intent="neutral"
            size="md"
            tone="soft"
          >
            Ver Histórico
          </ActionButton>
        </div>
      </div>

      {/* Cards de Resumo */}
      {renderizarCardsResumo()}

      {/* Filtros */}
      {renderizarFiltros()}

      {/* Barra de Ações de Fechamento */}
      {comissoesSelecionadas.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="h-5 w-5 text-blue-600" aria-hidden="true" />
            <span className="text-blue-800 font-medium">
              {comissoesSelecionadas.length} comissão(ões) selecionada(s)
            </span>
          </div>
          <div className="flex gap-2">
            <ActionButton
              onClick={() => setComissoesSelecionadas([])}
              icon={X}
              intent="neutral"
              tone="soft"
            >
              Limpar Seleção
            </ActionButton>
            <ActionButton
              onClick={abrirModalFechamento}
              disabled={loadingFechamento}
              icon={CheckCircle2}
              intent="create"
              loading={loadingFechamento}
            >
              Fechar Comissões
            </ActionButton>
          </div>
        </div>
      )}

      {/* Tabela */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left">
                  <input
                    type="checkbox"
                    checked={
                      comissoesSelecionadas.length > 0 &&
                      comissoesSelecionadas.length ===
                        comissoes.filter((c) => c.status === "pendente").length
                    }
                    onChange={toggleSelecionarTodas}
                    disabled={comissoes.filter((c) => c.status === "pendente").length === 0}
                    className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 cursor-pointer"
                    title="Selecionar todas pendentes"
                  />
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Data da Venda
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Número da Venda
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Produto ID
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Parcela
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Tipo de Cálculo
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Base de Cálculo
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  % Comissão
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Valor Comissão
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {comissoes.map((comissao) => (
                <tr key={comissao.id} className="hover:bg-blue-50 transition">
                  <td className="px-6 py-4 whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={comissoesSelecionadas.includes(comissao.id)}
                      onChange={() => toggleSelecaoComissao(comissao.id, comissao.status)}
                      disabled={comissao.status !== "pendente"}
                      className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed"
                      title={
                        comissao.status !== "pendente"
                          ? `Comissão ${comissao.status}`
                          : "Selecionar para fechamento"
                      }
                    />
                  </td>
                  <td
                    className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 cursor-pointer"
                    onClick={() => abrirDetalhe(comissao.id)}
                  >
                    {formatarData(comissao.data_venda)}
                  </td>
                  <td
                    className="px-6 py-4 whitespace-nowrap text-sm text-blue-600 font-medium cursor-pointer"
                    onClick={() => abrirDetalhe(comissao.id)}
                    title={`ID interno: #${comissao.venda_id}`}
                  >
                    <SaleReference
                      value={comissao.numero_venda || comissao.venda_id}
                      showPrefix={false}
                    />
                  </td>
                  <td
                    className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 cursor-pointer"
                    onClick={() => abrirDetalhe(comissao.id)}
                  >
                    <CopyableCode label="Produto" value={comissao.produto_id} />
                  </td>
                  <td
                    className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 cursor-pointer"
                    onClick={() => abrirDetalhe(comissao.id)}
                  >
                    {comissao.parcela_numero}
                  </td>
                  <td
                    className="px-6 py-4 whitespace-nowrap text-sm cursor-pointer"
                    onClick={() => abrirDetalhe(comissao.id)}
                  >
                    {renderizarTipoCalculo(comissao.tipo_calculo)}
                  </td>
                  <td
                    className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right font-medium cursor-pointer"
                    onClick={() => abrirDetalhe(comissao.id)}
                  >
                    <MoneyCell value={comissao.valor_base_calculo} />
                  </td>
                  <td
                    className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right cursor-pointer"
                    onClick={() => abrirDetalhe(comissao.id)}
                  >
                    <NumberCell value={comissao.percentual_comissao} decimals={1} suffix="%" />
                  </td>
                  <td
                    className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right font-bold cursor-pointer"
                    onClick={() => abrirDetalhe(comissao.id)}
                  >
                    <MoneyCell value={comissao.valor_comissao_gerada} />
                  </td>
                  <td
                    className="px-6 py-4 whitespace-nowrap text-sm cursor-pointer"
                    onClick={() => abrirDetalhe(comissao.id)}
                  >
                    {renderizarStatus(comissao.status)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Rodapé informativo */}
      <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <p className="text-sm text-blue-800">
          <strong>ℹ️ Informação:</strong> Os valores exibidos são snapshots imutáveis do momento da
          venda. Eles não são recalculados e refletem exatamente como a comissão foi gerada.
          <span className="ml-2 text-blue-600 font-medium">
            Clique em qualquer linha para ver mais detalhes.
          </span>
        </p>
      </div>

      {/* RODAPÉ FIXO COM RESUMO */}
      {comissoes.length > 0 && (
        <div className="fixed bottom-0 left-64 right-0 bg-gradient-to-r from-indigo-600 via-blue-600 to-indigo-600 text-white shadow-lg z-40 border-t border-indigo-300/30">
          <div className="max-w-7xl mx-auto px-8 py-3.5">
            <div className="flex items-center justify-between">
              {/* Período Selecionado */}
              <div className="flex items-center gap-8">
                <div>
                  <div className="text-[10px] font-semibold text-indigo-200 mb-0.5 tracking-wide uppercase">
                    📅 Período
                  </div>
                  <div className="text-sm font-bold text-white">
                    {tipoFiltroData === "ate_hoje" ? (
                      "Até hoje"
                    ) : (
                      <>
                        {filtros.data_inicio
                          ? new Date(filtros.data_inicio).toLocaleDateString("pt-BR")
                          : "Início"}
                        {" → "}
                        {filtros.data_fim
                          ? new Date(filtros.data_fim).toLocaleDateString("pt-BR")
                          : "Fim"}
                      </>
                    )}
                  </div>
                </div>

                {/* Filtros Ativos */}
                <div>
                  <div className="text-[10px] font-semibold text-indigo-200 mb-0.5 tracking-wide uppercase">
                    🔍 Filtros
                  </div>
                  <div className="text-sm font-bold text-white">
                    {funcionarioSelecionado && (
                      <span className="mr-2 bg-white/10 px-2 py-0.5 rounded">
                        👤 {funcionarioSelecionado.nome}
                      </span>
                    )}
                    {produtoSelecionado && (
                      <span className="mr-2 bg-white/10 px-2 py-0.5 rounded">
                        📦 {produtoSelecionado.nome}
                      </span>
                    )}
                    {grupoSelecionado && (
                      <span className="mr-2 bg-white/10 px-2 py-0.5 rounded">
                        📂 {grupoSelecionado.nome}
                      </span>
                    )}
                    {filtros.status && (
                      <span className="mr-2 bg-white/10 px-2 py-0.5 rounded">
                        ⚡ {filtros.status}
                      </span>
                    )}
                    {!funcionarioSelecionado &&
                      !produtoSelecionado &&
                      !grupoSelecionado &&
                      !filtros.status && <span className="text-indigo-200">Sem filtros</span>}
                  </div>
                </div>
              </div>

              {/* Total Calculado */}
              <div className="text-right">
                <div className="text-[10px] font-semibold text-indigo-200 mb-0.5 tracking-wide uppercase">
                  💰 Total Pendente (Filtrado)
                </div>
                <div className="text-3xl font-bold text-white drop-shadow-sm">
                  <MoneyCell value={calcularTotalFiltrado()} />
                </div>
                <div className="text-[11px] text-indigo-100 mt-0.5 font-medium">
                  {comissoes.filter((c) => c.status === "pendente").length} comissão(ões)
                  pendente(s)
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Espaçamento para o rodapé fixo */}
      {comissoes.length > 0 && <div className="h-24"></div>}

      {/* Modal de Detalhe */}
      {comissaoSelecionada && (
        <ComissaoDetalhe comissaoId={comissaoSelecionada} onClose={fecharDetalhe} />
      )}

      {/* Modal de Fechamento UNIFICADO */}
      {mostrarModalFechamento && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-bold text-gray-800">Fechar Comissões Selecionadas</h3>
              <button onClick={fecharModalFechamento} className="text-gray-400 hover:text-gray-600">
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>

            {/* Resumo de Comissões */}
            <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex justify-between items-center">
                <div>
                  <p className="text-sm text-gray-700 font-medium">
                    {comissoesSelecionadas.length} comissão(ões) selecionada(s)
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-gray-600">Valor Total</p>
                  <p className="text-2xl font-bold text-blue-600">
                    <MoneyCell value={calcularTotalSelecionado()} />
                  </p>
                </div>
              </div>
            </div>

            {/* SELEÇÃO DE TIPO DE FECHAMENTO */}
            <div className="mb-6">
              <label className="block text-sm font-bold text-gray-700 mb-3">
                ⚙️ Tipo de Fechamento
              </label>
              <div className="grid grid-cols-2 gap-4">
                <button
                  type="button"
                  onClick={() => setTipoPagamento("sem_pagar")}
                  className={`p-4 border-2 rounded-lg transition-all ${
                    tipoPagamento === "sem_pagar"
                      ? "border-blue-500 bg-blue-50 shadow-md"
                      : "border-gray-300 hover:border-blue-300"
                  }`}
                >
                  <div className="text-center">
                    <div className="text-3xl mb-2">📋</div>
                    <div className="font-bold text-gray-800">Fechar sem Pagar</div>
                    <div className="text-xs text-gray-600 mt-1">Apenas registrar fechamento</div>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => setTipoPagamento("com_pagamento")}
                  className={`p-4 border-2 rounded-lg transition-all ${
                    tipoPagamento === "com_pagamento"
                      ? "border-green-500 bg-green-50 shadow-md"
                      : "border-gray-300 hover:border-green-300"
                  }`}
                >
                  <div className="text-center">
                    <div className="text-3xl mb-2">💰</div>
                    <div className="font-bold text-gray-800">Fechar e Pagar</div>
                    <div className="text-xs text-gray-600 mt-1">Com lançamento financeiro</div>
                  </div>
                </button>
              </div>
            </div>

            {/* CAMPOS COMUNS */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                📅 Data do Fechamento/Pagamento <span className="text-red-500">*</span>
              </label>
              <input
                type="date"
                value={dataPagamento}
                onChange={(e) => setDataPagamento(e.target.value)}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            {/* CAMPOS CONDICIONAIS - PAGAMENTO */}
            {tipoPagamento === "com_pagamento" && (
              <div className="space-y-4 mb-4 p-4 bg-green-50 border border-green-200 rounded-lg">
                <h4 className="text-sm font-bold text-green-800 mb-3">💳 Dados do Pagamento</h4>

                {/* Valor Total (editável) */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    💵 Valor a Pagar (editável)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={valorTotalEditavel}
                    onChange={(e) => setValorTotalEditavel(parseFloat(e.target.value))}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
                  />
                  <p className="text-xs text-gray-600 mt-1">
                    Valor original: <MoneyCell value={calcularTotalSelecionado()} />
                  </p>
                </div>

                {/* Forma de Pagamento */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    💳 Forma de Pagamento <span className="text-red-500">*</span>
                  </label>
                  <select
                    value={formaPagamento}
                    onChange={(e) => setFormaPagamento(e.target.value)}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
                  >
                    <option value="">Selecione...</option>
                    {formasPagamentoDisponiveis.map((fp) => (
                      <option key={fp.id} value={fp.id}>
                        {fp.nome}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Conta Bancária */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    🏦 Conta Bancária <span className="text-red-500">*</span>
                  </label>
                  <select
                    value={contaBancariaId}
                    onChange={(e) => setContaBancariaId(e.target.value)}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
                  >
                    <option value="">Selecione...</option>
                    {contasBancarias.map((cb) => (
                      <option key={cb.id} value={cb.id}>
                        {cb.nome} ({cb.banco}) - Saldo: {formatarMoeda(cb.saldo || 0)}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            )}

            {/* Observações */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">📝 Observações</label>
              <textarea
                value={observacaoFechamento}
                onChange={(e) => setObservacaoFechamento(e.target.value)}
                rows={3}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Observações sobre o fechamento..."
              />
            </div>

            {/* Botões de Ação */}
            <div className="flex gap-3">
              <button
                onClick={fecharModalFechamento}
                disabled={loadingFechamento}
                className="flex-1 px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition disabled:opacity-50"
              >
                Cancelar
              </button>
              <button
                onClick={confirmarFechamento}
                disabled={
                  loadingFechamento ||
                  !dataPagamento ||
                  (tipoPagamento === "com_pagamento" && (!formaPagamento || !contaBancariaId))
                }
                className={`flex-1 px-4 py-2 rounded-lg transition disabled:opacity-50 flex items-center justify-center gap-2 ${
                  tipoPagamento === "com_pagamento"
                    ? "bg-green-600 hover:bg-green-700"
                    : "bg-blue-600 hover:bg-blue-700"
                } text-white`}
              >
                {loadingFechamento ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    Processando...
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                    {tipoPagamento === "com_pagamento"
                      ? "💰 Fechar e Pagar"
                      : "📋 Fechar sem Pagar"}
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ComissoesListagem;
