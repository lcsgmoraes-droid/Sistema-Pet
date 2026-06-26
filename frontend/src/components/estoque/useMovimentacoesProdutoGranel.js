import { useEffect, useState } from "react";
import toast from "react-hot-toast";

import api from "../../api";
import { formatMoneyBRL } from "../../utils/formatters";
import {
  extrairMensagemErroApiMovimentacao as extrairMensagemErroApi,
  formatarQuantidadeMovimentacao as formatarQuantidade,
  parseNumeroInputMovimentacao as parseNumeroInput,
} from "./movimentacoesProdutoUtils";

export function useMovimentacoesProdutoGranel({ carregarDados, id, produto }) {
  const [showGranelModal, setShowGranelModal] = useState(false);
  const [granelVinculos, setGranelVinculos] = useState([]);
  const [granelProdutos, setGranelProdutos] = useState([]);
  const [granelSelecionadoId, setGranelSelecionadoId] = useState("");
  const [buscaGranel, setBuscaGranel] = useState("");
  const [quantidadeGranel, setQuantidadeGranel] = useState("");
  const [observacaoGranel, setObservacaoGranel] = useState("");
  const [loadingGranel, setLoadingGranel] = useState(false);
  const [modoPrecoGranel, setModoPrecoGranel] = useState("margem");
  const [margemBaseGranel, setMargemBaseGranel] = useState("preco_venda_kg");
  const [margemGranel, setMargemGranel] = useState("20");
  const [precoVendaGranel, setPrecoVendaGranel] = useState("");
  const [atualizarPrecoGranel, setAtualizarPrecoGranel] = useState(true);

  const produtoEhGranel =
    Boolean(produto?.e_granel) || (produto?.nome || "").toLowerCase().includes("granel");
  const pesoPacoteOrigem = parseNumeroInput(produto?.peso_embalagem);
  const produtoBloqueiaGranel =
    produto?.tipo_produto === "PAI" ||
    (produto?.tipo_produto === "KIT" && produto?.tipo_kit === "VIRTUAL");
  const podeLancarGranel = Boolean(produto) && !produtoEhGranel && !produtoBloqueiaGranel;
  const quantidadeGranelNumero = Number(quantidadeGranel || 0);
  const kgGranelPrevisto =
    quantidadeGranelNumero > 0 ? quantidadeGranelNumero * pesoPacoteOrigem : 0;
  const custoKgGranel =
    pesoPacoteOrigem > 0 ? Number(produto?.preco_custo || 0) / pesoPacoteOrigem : 0;
  const precoVendaKgOrigem =
    pesoPacoteOrigem > 0 ? Number(produto?.preco_venda || 0) / pesoPacoteOrigem : 0;
  const vinculoGranelSelecionado = granelVinculos.find(
    (vinculo) => String(vinculo.produto_granel_id) === String(granelSelecionadoId),
  );
  const produtoGranelSelecionado = granelProdutos.find(
    (item) => String(item.id) === String(granelSelecionadoId),
  );
  const nomeGranelSelecionado =
    vinculoGranelSelecionado?.produto_granel_nome || produtoGranelSelecionado?.nome || "";
  const precoVendaAtualGranel = Number(
    vinculoGranelSelecionado?.produto_granel_preco_venda ??
      produtoGranelSelecionado?.preco_venda ??
      0,
  );
  const baseMargemGranel =
    margemBaseGranel === "preco_venda_kg" ? precoVendaKgOrigem : custoKgGranel;
  const margemGranelNumero = parseNumeroInput(margemGranel);
  const precoVendaInformadoGranel = parseNumeroInput(precoVendaGranel);
  const precoVendaSugeridoGranel =
    modoPrecoGranel === "margem"
      ? baseMargemGranel * (1 + margemGranelNumero / 100)
      : precoVendaInformadoGranel;
  const margemCalculadaGranel =
    baseMargemGranel > 0 && precoVendaSugeridoGranel > 0
      ? (precoVendaSugeridoGranel / baseMargemGranel - 1) * 100
      : 0;
  const precoMinimoEsperadoGranel = precoVendaKgOrigem > 0 ? precoVendaKgOrigem * 1.2 : 0;
  const granelDentroMargemEsperada =
    precoMinimoEsperadoGranel > 0 ? precoVendaSugeridoGranel >= precoMinimoEsperadoGranel : true;
  const diferencaPrecoGranel = precoVendaSugeridoGranel - precoVendaAtualGranel;
  const baseMargemTexto =
    margemBaseGranel === "preco_venda_kg" ? "venda/kg do pacote pai" : "custo/kg do pacote pai";

  const carregarVinculosGranel = async () => {
    if (!id) return [];

    const response = await api.get(`/estoque/granel/vinculos/origem/${id}`);
    const vinculos = response.data || [];
    setGranelVinculos(vinculos);
    if (vinculos.length === 1) {
      setGranelSelecionadoId(String(vinculos[0].produto_granel_id));
    }
    return vinculos;
  };

  const buscarProdutosGranel = async (termo = "") => {
    const response = await api.get("/estoque/granel/produtos", {
      params: {
        busca: termo || undefined,
        limite: 30,
      },
    });
    setGranelProdutos(response.data || []);
  };

  const abrirModalGranel = async () => {
    if (!podeLancarGranel) {
      toast.error("Este produto nao permite lancamento de granel.");
      return;
    }

    if (pesoPacoteOrigem <= 0) {
      toast.error("Preencha o peso da embalagem na aba Racao antes de lancar granel.");
      return;
    }

    setQuantidadeGranel("");
    setObservacaoGranel("");
    setBuscaGranel("");
    setModoPrecoGranel("margem");
    setMargemBaseGranel("preco_venda_kg");
    setMargemGranel("20");
    setPrecoVendaGranel("");
    setAtualizarPrecoGranel(true);
    setShowGranelModal(true);
    setLoadingGranel(true);
    try {
      await Promise.all([carregarVinculosGranel(), buscarProdutosGranel("")]);
    } catch (error) {
      toast.error(extrairMensagemErroApi(error, "Erro ao carregar vinculos de granel"));
    } finally {
      setLoadingGranel(false);
    }
  };

  const handleSubmitGranel = async (e) => {
    e.preventDefault();

    if (!granelSelecionadoId) {
      toast.error("Selecione o produto granel que vai receber os kg.");
      return;
    }

    if (!quantidadeGranelNumero || quantidadeGranelNumero <= 0) {
      toast.error("Informe a quantidade de pacotes abertos.");
      return;
    }

    try {
      setLoadingGranel(true);
      const response = await api.post("/estoque/granel/converter", {
        produto_origem_id: Number(id),
        produto_granel_id: Number(granelSelecionadoId),
        quantidade_pacotes: quantidadeGranelNumero,
        atualizar_preco_venda_granel: Boolean(atualizarPrecoGranel && precoVendaSugeridoGranel > 0),
        preco_venda_granel:
          atualizarPrecoGranel && precoVendaSugeridoGranel > 0
            ? Number(precoVendaSugeridoGranel.toFixed(2))
            : null,
        observacao: observacaoGranel || null,
      });

      const precoAtualizadoMsg = response.data.preco_venda_granel_atualizado
        ? ` Preco do granel: ${formatMoneyBRL(response.data.preco_venda_granel_novo)}.`
        : "";
      toast.success(
        `Granel lancado: ${formatarQuantidade(response.data.quantidade_granel_kg)} kg a partir de ${formatarQuantidade(response.data.quantidade_pacotes)} pacote(s).${precoAtualizadoMsg}`,
        { duration: 5000 },
      );
      setShowGranelModal(false);
      await carregarDados();
    } catch (error) {
      toast.error(extrairMensagemErroApi(error, "Erro ao lancar granel"));
    } finally {
      setLoadingGranel(false);
    }
  };

  const handleAlterarModoPrecoGranel = (modo) => {
    setModoPrecoGranel(modo);
    if (modo === "preco" && !precoVendaGranel) {
      const precoBase =
        precoVendaAtualGranel > 0 ? precoVendaAtualGranel : precoVendaSugeridoGranel;
      setPrecoVendaGranel(precoBase > 0 ? precoBase.toFixed(2) : "");
    }
    if (modo === "margem" && !margemGranel) {
      setMargemGranel("20");
    }
  };

  const handleSelecionarGranel = (produtoGranelId, precoAtual = 0) => {
    setGranelSelecionadoId(String(produtoGranelId));
    if (modoPrecoGranel === "preco" && Number(precoAtual || 0) > 0) {
      setPrecoVendaGranel(Number(precoAtual).toFixed(2));
    }
  };

  const handleDesvincularGranel = async (vinculoId) => {
    if (!confirm("Desvincular este produto granel da origem?")) {
      return;
    }

    try {
      await api.delete(`/estoque/granel/vinculos/${vinculoId}`);
      toast.success("Vinculo removido.");
      await carregarVinculosGranel();
    } catch (error) {
      toast.error(extrairMensagemErroApi(error, "Erro ao desvincular granel"));
    }
  };

  useEffect(() => {
    if (!showGranelModal) return undefined;

    const timer = setTimeout(
      async () => {
        try {
          await buscarProdutosGranel(buscaGranel.trim());
        } catch (error) {
          console.error("Erro ao buscar produtos granel:", error);
        }
      },
      buscaGranel.trim() ? 250 : 0,
    );

    return () => clearTimeout(timer);
  }, [showGranelModal, buscaGranel]);

  return {
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
  };
}
