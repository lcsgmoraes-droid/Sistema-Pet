/**
 * Página de Movimentações de Estoque por Produto
 * Modelo inspirado no Bling
 */
import { useState, useEffect, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "../api";
import toast from "react-hot-toast";
import { formatBRL, formatMoneyBRL } from "../utils/formatters";
import MovimentacoesLancamentosTable from "./estoque/MovimentacoesLancamentosTable";
import MovimentacoesProdutoHeader from "./estoque/MovimentacoesProdutoHeader";
import MovimentacoesProdutoModals from "./estoque/MovimentacoesProdutoModals";
import {
  ESTILOS_CANAIS,
  LABELS_CANAIS,
  calcularTotaisMovimentacoes,
  calcularVendasPorCanalMovimentacoes,
  dataAtualIsoLocalMovimentacao as dataAtualIsoLocal,
  extrairMensagemErroApiMovimentacao as extrairMensagemErroApi,
  formatarQuantidadeMovimentacao as formatarQuantidade,
  getMotivoLabelMovimentacao,
  getOrigemMovimentacao,
  getSaldoAposLancamento,
  parseNumeroInputMovimentacao as parseNumeroInput,
  resolverEstoqueAtualMovimentacoes,
  resolverSaldoDisponivelMovimentacoes,
} from "./estoque/movimentacoesProdutoUtils";
import { montarMovimentoBalanco } from "./produtoBalanco/produtosBalancoUtils";
import VendasPorCanalPanel from "./estoque/VendasPorCanalPanel";
import { useMovimentacoesProdutoGranel } from "./estoque/useMovimentacoesProdutoGranel";
import { useModulos } from "../contexts/ModulosContext";

export default function MovimentacoesProduto() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { moduloAtivo } = useModulos();
  const moduloBlingAtivo = moduloAtivo("bling");

  const [produto, setProduto] = useState(null);
  const [movimentacoes, setMovimentacoes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [selectedIds, setSelectedIds] = useState([]);
  const [editingMovimentacao, setEditingMovimentacao] = useState(null);
  const [syncProduto, setSyncProduto] = useState(null);
  const [forcandoSync, setForcandoSync] = useState(false);
  const [forcandoVinculoBling, setForcandoVinculoBling] = useState(false);
  const [showReservasModal, setShowReservasModal] = useState(false);
  const [loadingReservas, setLoadingReservas] = useState(false);
  const [reservasAtivas, setReservasAtivas] = useState([]);
  // Modal de lançamento
  const [tipoLancamento, setTipoLancamento] = useState("entrada"); // entrada, saida, balanco
  const [formData, setFormData] = useState({
    quantidade: "",
    custo_unitario: "",
    observacao: "",
    lote: "",
    data_validade: "",
    data_fabricacao: "",
    motivo_saida: "saida_manual",
    gerar_despesa_uso_interno: false,
    descricao_despesa: "",
    data_competencia: dataAtualIsoLocal(),
  });
  useEffect(() => {
    carregarDados();
  }, [id, moduloBlingAtivo]);

  const carregarDados = async () => {
    try {
      setLoading(true);

      const [produtoRes, movRes] = await Promise.all([
        api.get(`/produtos/${id}`),
        api.get(`/estoque/movimentacoes/produto/${id}`),
      ]);

      const produtoData = produtoRes.data;
      setProduto(produtoData);
      setMovimentacoes(movRes.data);

      const termoBuscaSync = produtoData?.codigo || produtoData?.sku;
      if (!moduloBlingAtivo) {
        setSyncProduto(null);
        return;
      }

      if (termoBuscaSync) {
        try {
          const syncRes = await api.get("/estoque/sync/status", {
            params: { busca: termoBuscaSync },
          });
          const itemSync = (syncRes.data || []).find((item) => item.produto_id === Number(id));
          setSyncProduto(itemSync || null);
        } catch (syncError) {
          if (syncError?.response?.status !== 403) {
            console.warn("Nao foi possivel carregar status de sincronizacao:", syncError);
          }
          setSyncProduto(null);
        }
      } else {
        setSyncProduto(null);
      }
    } catch (error) {
      console.error("Erro ao carregar dados:", error);
      console.error("Detalhes do erro:", error.response?.data);
      toast.error(extrairMensagemErroApi(error, "Erro ao carregar dados do produto"));
    } finally {
      setLoading(false);
    }
  };

  const {
    abrirModalGranel,
    atualizarPrecoGranel,
    baseMargemGranel,
    baseMargemTexto,
    buscaGranel,
    custoKgGranel,
    diferencaPrecoGranel,
    granelDentroMargemEsperada,
    granelProdutos,
    granelSelecionadoId,
    granelVinculos,
    handleAlterarModoPrecoGranel,
    handleDesvincularGranel,
    handleSelecionarGranel,
    handleSubmitGranel,
    kgGranelPrevisto,
    loadingGranel,
    margemBaseGranel,
    margemCalculadaGranel,
    margemGranel,
    modoPrecoGranel,
    nomeGranelSelecionado,
    observacaoGranel,
    podeLancarGranel,
    pesoPacoteOrigem,
    precoMinimoEsperadoGranel,
    precoVendaAtualGranel,
    precoVendaGranel,
    precoVendaKgOrigem,
    precoVendaSugeridoGranel,
    produtoEhGranel,
    quantidadeGranel,
    quantidadeGranelNumero,
    setAtualizarPrecoGranel,
    setBuscaGranel,
    setMargemBaseGranel,
    setMargemGranel,
    setObservacaoGranel,
    setPrecoVendaGranel,
    setQuantidadeGranel,
    setShowGranelModal,
    showGranelModal,
  } = useMovimentacoesProdutoGranel({ carregarDados, id, produto });

  const handleForcarSyncProduto = async () => {
    if (!moduloBlingAtivo) {
      toast.error("Integração Bling não está disponível neste plano.");
      return;
    }

    if (!syncProduto?.bling_produto_id) {
      toast.error("Este produto ainda não está vinculado ao Bling para sincronização manual.");
      return;
    }

    try {
      setForcandoSync(true);
      const response = await api.post(`/estoque/sync/forcar/${id}`);
      const data = response?.data || {};
      if (data.rate_limited) {
        toast(data.message || "O Bling pediu uma pausa. O item ficou reagendado automaticamente.");
      } else {
        toast.success(data.message || "Sincronização manual enviada para este produto.");
      }
      await carregarDados();
    } catch (error) {
      toast.error(extrairMensagemErroApi(error, "Erro ao forçar sincronização do produto."));
    } finally {
      setForcandoSync(false);
    }
  };

  const handleForcarVinculoBling = async () => {
    if (!moduloBlingAtivo) {
      toast.error("Integração Bling não está disponível neste plano.");
      return;
    }

    try {
      setForcandoVinculoBling(true);
      const response = await api.post(`/estoque/sync/vincular-automatico/${id}`);
      const data = response?.data || {};
      toast.success(data.message || "Produto vinculado ao Bling pelo SKU.");
      await carregarDados();
    } catch (error) {
      toast.error(extrairMensagemErroApi(error, "Nao foi possivel vincular este SKU no Bling."));
    } finally {
      setForcandoVinculoBling(false);
    }
  };

  const handleAcaoPrincipalBling = () => {
    if (syncProduto?.bling_produto_id) {
      return handleForcarSyncProduto();
    }
    return handleForcarVinculoBling();
  };

  const abrirModalReservas = async () => {
    if (!produto || Number(produto.estoque_reservado || 0) <= 0) {
      return;
    }

    try {
      setLoadingReservas(true);
      const res = await api.get(`/estoque/produto/${id}/reservas-ativas`);
      setReservasAtivas(res.data?.pedidos || []);
      setShowReservasModal(true);
    } catch (error) {
      toast.error(extrairMensagemErroApi(error, "Erro ao carregar pedidos reservados"));
    } finally {
      setLoadingReservas(false);
    }
  };

  const abrirPedidoReservado = (pedido) => {
    const numeroPedido = pedido?.pedido_bling_numero || pedido?.pedido_bling_id;
    const destino = numeroPedido
      ? `/vendas/bling-pedidos?pedido=${encodeURIComponent(numeroPedido)}`
      : "/vendas/bling-pedidos";
    window.open(destino, "_blank", "noopener,noreferrer");
  };

  const abrirModal = (tipo, movimentacao = null) => {
    // ========== VALIDAÇÃO: KIT VIRTUAL não permite movimentação manual ==========
    if (produto?.tipo_produto === "KIT" && produto?.tipo_kit === "VIRTUAL" && !movimentacao) {
      toast.error(
        `❌ KIT VIRTUAL não permite movimentação manual de estoque.\n\n` +
          `O estoque deste kit é calculado automaticamente com base nos componentes.\n\n` +
          `Para alterar o estoque, movimente os produtos componentes individualmente.`,
        { duration: 6000 },
      );
      return;
    }

    setTipoLancamento(tipo);
    setEditingMovimentacao(movimentacao);

    if (movimentacao) {
      // Modo edição
      setFormData({
        quantidade: movimentacao.quantidade?.toString() || "",
        custo_unitario: movimentacao.custo_unitario?.toString() || "",
        observacao: movimentacao.observacao || "",
        lote: movimentacao.lote_id || "",
        data_validade: "",
        data_fabricacao: "",
        motivo_saida: movimentacao.motivo || "saida_manual",
        gerar_despesa_uso_interno: false,
        descricao_despesa: "",
        data_competencia: dataAtualIsoLocal(),
      });
    } else {
      // Modo novo
      setFormData({
        quantidade: "",
        custo_unitario: tipo === "entrada" ? produto?.preco_custo || "" : "",
        observacao: "",
        lote: "",
        data_validade: "",
        data_fabricacao: "",
        retornar_componentes: false, // Padrão: não retornar componentes
        motivo_saida: "saida_manual",
        gerar_despesa_uso_interno: tipo === "saida",
        descricao_despesa: produto?.nome
          ? `Material de uso interno - ${produto.nome}`
          : "Material de uso interno",
        data_competencia: dataAtualIsoLocal(),
      });
    }
    setShowModal(true);
  };

  const handleSelectAll = () => {
    if (selectedIds.length === movimentacoes.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(movimentacoes.map((m) => m.id));
    }
  };

  const handleSelectOne = (id) => {
    if (selectedIds.includes(id)) {
      setSelectedIds(selectedIds.filter((sid) => sid !== id));
    } else {
      setSelectedIds([...selectedIds, id]);
    }
  };

  const handleDelete = async () => {
    if (selectedIds.length === 0) {
      toast.error("Selecione pelo menos um lançamento");
      return;
    }

    if (!confirm(`Deseja realmente excluir ${selectedIds.length} lançamento(s)?`)) {
      return;
    }

    try {
      const responses = await Promise.all(
        selectedIds.map((id) => api.delete(`/estoque/movimentacoes/${id}`)),
      );

      // Verificar se algum teve componentes estornados
      const componentesEstornados = responses.flatMap((r) => r.data.componentes_estornados || []);

      if (componentesEstornados.length > 0) {
        toast.success(
          `${selectedIds.length} lançamento(s) excluído(s)!\n✅ ${componentesEstornados.length} componente(s) estornado(s)`,
          { duration: 5000 },
        );
      } else {
        toast.success(`${selectedIds.length} lançamento(s) excluído(s)`);
      }

      setSelectedIds([]);
      carregarDados();
    } catch (error) {
      console.error("Erro ao excluir:", error);
      toast.error(extrairMensagemErroApi(error, "Erro ao excluir lançamentos"));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      // Se está editando, usar endpoint PATCH
      if (editingMovimentacao) {
        const payload = {
          quantidade: parseFloat(formData.quantidade),
          custo_unitario: formData.custo_unitario ? parseFloat(formData.custo_unitario) : null,
          observacao: formData.observacao || null,
        };

        await api.patch(`/estoque/movimentacoes/${editingMovimentacao.id}`, payload);

        toast.success("Lançamento atualizado com sucesso!");
        setShowModal(false);
        setEditingMovimentacao(null);
        carregarDados();
        return;
      }

      // Criando novo lançamento
      if (tipoLancamento === "entrada" && produtoEhGranel) {
        toast.error('Entrada de granel deve partir do produto fechado em "Lancar granel".');
        return;
      }

      let endpoint = "/estoque/";
      let payload = {
        produto_id: parseInt(id),
        quantidade: parseNumeroInput(formData.quantidade),
        custo_unitario: formData.custo_unitario ? parseNumeroInput(formData.custo_unitario) : null,
        observacao: formData.observacao || null,
      };

      // Configurar endpoint e payload conforme tipo
      if (tipoLancamento === "entrada") {
        endpoint += "entrada";
        payload.tipo = "entrada";
        payload.motivo = "compra";
        payload.numero_lote = formData.lote || null;
        payload.data_validade = formData.data_validade || null;
        payload.data_fabricacao = formData.data_fabricacao || null;
      } else if (tipoLancamento === "saida") {
        endpoint += "saida";
        payload.tipo = "saida";
        payload.motivo = formData.motivo_saida || "saida_manual";
        payload.numero_lote = formData.lote || null;
        payload.data_validade = formData.data_validade || null;
        if (payload.motivo === "uso_interno") {
          payload.gerar_despesa_uso_interno = formData.gerar_despesa_uso_interno === true;
          payload.descricao_despesa =
            formData.descricao_despesa || `Material de uso interno - ${produto?.nome || "Produto"}`;
          payload.data_competencia = formData.data_competencia || dataAtualIsoLocal();
        }
        // Adicionar campo retornar_componentes para KIT FÍSICO
        if (produto?.tipo_produto === "KIT" && produto?.tipo_kit === "FISICO") {
          payload.retornar_componentes = formData.retornar_componentes === true;
        }
      } else if (tipoLancamento === "balanco") {
        // Balanço: definir estoque para o valor exato
        const novaQuantidade = parseNumeroInput(formData.quantidade);
        const movimentoBalanco = montarMovimentoBalanco(produto, novaQuantidade, {
          numeroLote: formData.lote,
          dataValidade: formData.data_validade,
        });

        if (movimentoBalanco.erro) {
          toast.error(movimentoBalanco.erro);
          return;
        }

        if (movimentoBalanco.semAlteracao) {
          toast("Sem alteracao: estoque ja esta nesse valor.", { icon: "i" });
          setShowModal(false);
          return;
        }

        endpoint = movimentoBalanco.endpoint;
        payload = {
          ...payload,
          ...movimentoBalanco.payload,
          tipo: movimentoBalanco.endpoint.endsWith("/entrada") ? "entrada" : "saida",
        };
      }

      const response = await api.post(endpoint, payload);

      // Mostrar indicador de variação de preço se for entrada
      if (tipoLancamento === "entrada" && response.data) {
        const { custo_anterior, custo_unitario, variacao_preco } = response.data;

        if (variacao_preco && custo_anterior !== null && custo_anterior !== undefined) {
          let mensagem = "Lançamento registrado!";

          if (variacao_preco === "aumento") {
            mensagem += ` ⬆️ Custo aumentou de R$ ${custo_anterior?.toFixed(2)} para R$ ${custo_unitario?.toFixed(2)}`;
            toast.error(mensagem, { duration: 5000 });
          } else if (variacao_preco === "reducao") {
            mensagem += ` ⬇️ Custo reduziu de R$ ${custo_anterior?.toFixed(2)} para R$ ${custo_unitario?.toFixed(2)}`;
            toast.success(mensagem, { duration: 5000 });
          } else if (variacao_preco === "estavel") {
            mensagem += ` Custo mantido em R$ ${custo_unitario?.toFixed(2)}`;
            toast(mensagem, { icon: "➖", duration: 3000 });
          }
        } else if (custo_unitario) {
          // Primeira entrada
          toast.success(`Lançamento registrado! Custo: R$ ${custo_unitario?.toFixed(2)}`, {
            duration: 3000,
          });
        } else {
          toast.success("Lançamento registrado com sucesso!");
        }
      } else {
        // Mostrar mensagem sobre componentes sensibilizados se houver
        if (
          response.data?.componentes_sensibilizados &&
          response.data.componentes_sensibilizados.length > 0
        ) {
          const qtdComponentes = response.data.componentes_sensibilizados.length;
          toast.success(
            `Lançamento registrado com sucesso!\n✅ ${qtdComponentes} componente(s) sensibilizado(s)`,
            { duration: 4000 },
          );
        } else {
          toast.success("Lançamento registrado com sucesso!");
        }
      }

      setShowModal(false);
      carregarDados();
    } catch (error) {
      console.error("Erro ao registrar lançamento:", error);
      toast.error(extrairMensagemErroApi(error, "Erro ao registrar lançamento"));
    }
  };

  const formatarData = (data) => {
    if (!data) return "-";
    // Converter para horário de Brasília (UTC-3)
    const dataUTC = new Date(data);
    const dataBrasilia = new Date(dataUTC.getTime() - 3 * 60 * 60 * 1000);
    return dataBrasilia.toLocaleString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      timeZone: "America/Sao_Paulo",
    });
  };

  const getMotivoLabel = getMotivoLabelMovimentacao;
  const getOrigem = getOrigemMovimentacao;
  const { totalEntradas, totalSaidas } = useMemo(
    () => calcularTotaisMovimentacoes(movimentacoes),
    [movimentacoes],
  );
  const vendasPorCanal = useMemo(
    () => calcularVendasPorCanalMovimentacoes(movimentacoes),
    [movimentacoes],
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-gray-500">Carregando...</div>
      </div>
    );
  }

  if (!produto) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-red-500">Produto não encontrado</div>
      </div>
    );
  }

  const estoqueAtual = resolverEstoqueAtualMovimentacoes(produto);
  const estoqueMinimo = produto.estoque_minimo || 0;
  const estoqueReservado = produto.estoque_reservado || 0;
  const saldoAposReserva = resolverSaldoDisponivelMovimentacoes(produto);
  const unidade = produto.unidade || "UN";

  const syncDisponivel = Boolean(syncProduto?.bling_produto_id);
  let syncStatusLabel = "Sem vínculo com Bling";
  if (syncDisponivel) {
    syncStatusLabel = syncProduto?.status || "ativo";
    if (syncProduto?.queue_status) {
      syncStatusLabel = `${syncStatusLabel} / fila ${syncProduto.queue_status}`;
    }
  }

  const handleIncluirLancamento = () => {
    if (produto?.tipo_produto === "KIT" && produto?.tipo_kit === "VIRTUAL") {
      toast.error(
        "KIT VIRTUAL nao permite movimentacao manual.\n\nMovimente os componentes individualmente.",
        { duration: 4000 },
      );
      return;
    }

    setTipoLancamento(produtoEhGranel ? "balanco" : "entrada");
    setShowModal(true);
  };

  return (
    <div className="mx-auto max-w-7xl space-y-4 p-4">
      <MovimentacoesProdutoHeader
        abrirModalReservas={abrirModalReservas}
        estoqueAtual={estoqueAtual}
        estoqueMinimo={estoqueMinimo}
        estoqueReservado={estoqueReservado}
        forcandoSync={forcandoSync}
        forcandoVinculoBling={forcandoVinculoBling}
        formatarQuantidade={formatarQuantidade}
        loadingReservas={loadingReservas}
        onAbrirPainelBling={() => navigate("/produtos/sinc-bling")}
        onForcarSyncProduto={handleAcaoPrincipalBling}
        onIncluirLancamento={handleIncluirLancamento}
        onLancarGranel={abrirModalGranel}
        onVoltarProdutos={() => navigate("/produtos")}
        podeLancarGranel={podeLancarGranel}
        produto={produto}
        saldoAposReserva={saldoAposReserva}
        mostrarControlesBling={moduloBlingAtivo}
        syncDisponivel={syncDisponivel}
        syncProduto={syncProduto}
        syncStatusLabel={syncStatusLabel}
        totalEntradas={totalEntradas}
        totalSaidas={totalSaidas}
        unidade={unidade}
      />

      <VendasPorCanalPanel
        estilosCanais={ESTILOS_CANAIS}
        formatMoney={formatMoneyBRL}
        formatQuantidade={formatBRL}
        labelsCanais={LABELS_CANAIS}
        vendasPorCanal={vendasPorCanal}
      />

      <MovimentacoesLancamentosTable
        abrirModal={abrirModal}
        formatarData={formatarData}
        formatarQuantidade={formatarQuantidade}
        getMotivoLabel={getMotivoLabel}
        getOrigem={getOrigem}
        getSaldoAposLancamento={getSaldoAposLancamento}
        handleDelete={handleDelete}
        handleSelectAll={handleSelectAll}
        handleSelectOne={handleSelectOne}
        labelsCanais={LABELS_CANAIS}
        movimentacoes={movimentacoes}
        navigate={navigate}
        produto={produto}
        selectedIds={selectedIds}
      />

      <MovimentacoesProdutoModals
        abrirPedidoReservado={abrirPedidoReservado}
        atualizarPrecoGranel={atualizarPrecoGranel}
        baseMargemGranel={baseMargemGranel}
        baseMargemTexto={baseMargemTexto}
        buscaGranel={buscaGranel}
        custoKgGranel={custoKgGranel}
        diferencaPrecoGranel={diferencaPrecoGranel}
        editingMovimentacao={editingMovimentacao}
        estoqueAtual={estoqueAtual}
        formData={formData}
        formatMoney={formatMoneyBRL}
        formatPercentual={formatBRL}
        formatarQuantidade={formatarQuantidade}
        granelDentroMargemEsperada={granelDentroMargemEsperada}
        granelProdutos={granelProdutos}
        granelSelecionadoId={granelSelecionadoId}
        granelVinculos={granelVinculos}
        handleAlterarModoPrecoGranel={handleAlterarModoPrecoGranel}
        handleDesvincularGranel={handleDesvincularGranel}
        handleSelecionarGranel={handleSelecionarGranel}
        handleSubmit={handleSubmit}
        handleSubmitGranel={handleSubmitGranel}
        kgGranelPrevisto={kgGranelPrevisto}
        loadingGranel={loadingGranel}
        margemBaseGranel={margemBaseGranel}
        margemCalculadaGranel={margemCalculadaGranel}
        margemGranel={margemGranel}
        modoPrecoGranel={modoPrecoGranel}
        nomeGranelSelecionado={nomeGranelSelecionado}
        observacaoGranel={observacaoGranel}
        onCloseGranel={() => setShowGranelModal(false)}
        onCloseLancamento={() => setShowModal(false)}
        onCloseReservas={() => setShowReservasModal(false)}
        precoMinimoEsperadoGranel={precoMinimoEsperadoGranel}
        precoVendaAtualGranel={precoVendaAtualGranel}
        precoVendaGranel={precoVendaGranel}
        precoVendaKgOrigem={precoVendaKgOrigem}
        precoVendaSugeridoGranel={precoVendaSugeridoGranel}
        produto={produto}
        produtoEhGranel={produtoEhGranel}
        quantidadeGranel={quantidadeGranel}
        quantidadeGranelNumero={quantidadeGranelNumero}
        reservasAtivas={reservasAtivas}
        setAtualizarPrecoGranel={setAtualizarPrecoGranel}
        setBuscaGranel={setBuscaGranel}
        setFormData={setFormData}
        setMargemBaseGranel={setMargemBaseGranel}
        setMargemGranel={setMargemGranel}
        setObservacaoGranel={setObservacaoGranel}
        setPrecoVendaGranel={setPrecoVendaGranel}
        setQuantidadeGranel={setQuantidadeGranel}
        setTipoLancamento={setTipoLancamento}
        showGranelModal={showGranelModal}
        showModal={showModal}
        showReservasModal={showReservasModal}
        tipoLancamento={tipoLancamento}
        pesoPacoteOrigem={pesoPacoteOrigem}
      />
    </div>
  );
}
