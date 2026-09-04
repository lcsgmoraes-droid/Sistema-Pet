import { useCallback, useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";

import api from "../../api";
import { formatMoneyBRL } from "../../utils/formatters";
import {
  extrairMensagemErroApiMovimentacao as extrairMensagemErroApi,
  formatarQuantidadeMovimentacao as formatarQuantidade,
  parseNumeroInputMovimentacao as parseNumeroInput,
} from "./movimentacoesProdutoUtils";
import {
  calcularQuantidadeDestinoFracionamento,
  montarPayloadFracionamentoClinico,
  resolverConfiguracaoVinculoFracionamento,
} from "./fracionamentoClinicoUtils";

export function useMovimentacoesProdutoFracionamento({ carregarDados, id, produto }) {
  const [aberto, setAberto] = useState(false);
  const [loading, setLoading] = useState(false);
  const [busca, setBusca] = useState("");
  const [produtosDestino, setProdutosDestino] = useState([]);
  const [vinculos, setVinculos] = useState([]);
  const [lotes, setLotes] = useState([]);
  const [produtoDestinoId, setProdutoDestinoId] = useState("");
  const [quantidadeOrigem, setQuantidadeOrigem] = useState("1");
  const [fatorConversao, setFatorConversao] = useState("");
  const [validadeDias, setValidadeDias] = useState("");
  const [loteOrigemId, setLoteOrigemId] = useState("");
  const [documento, setDocumento] = useState("");
  const [observacao, setObservacao] = useState("");

  const produtoBloqueado =
    produto?.tipo === "servico" ||
    produto?.tipo_produto === "PAI" ||
    (produto?.tipo_produto === "KIT" && produto?.tipo_kit === "VIRTUAL") ||
    Boolean(produto?.e_granel);
  const podeFracionarClinica = Boolean(produto) && !produtoBloqueado;
  const quantidadeDestino = calcularQuantidadeDestinoFracionamento(
    quantidadeOrigem,
    fatorConversao,
  );
  const custoDestinoUnitario =
    quantidadeDestino > 0
      ? (parseNumeroInput(quantidadeOrigem) * Number(produto?.preco_custo || 0)) / quantidadeDestino
      : 0;

  const produtosDisponiveis = useMemo(() => {
    const porId = new Map((produtosDestino || []).map((item) => [String(item.id), item]));
    vinculos.forEach((vinculo) => {
      const item = vinculo.produto_destino;
      if (item) porId.set(String(item.id), item);
    });
    return [...porId.values()];
  }, [produtosDestino, vinculos]);
  const produtoDestino = produtosDisponiveis.find(
    (item) => String(item.id) === String(produtoDestinoId),
  );

  const buscarProdutos = useCallback(
    async (termo = "") => {
      if (!id) return;
      const response = await api.get("/estoque/fracionamento-clinico/produtos", {
        params: { produto_origem_id: Number(id), busca: termo || undefined, limite: 40 },
      });
      setProdutosDestino(response.data || []);
    },
    [id],
  );

  function selecionarProdutoDestino(novoId, vinculosAtuais = vinculos) {
    setProdutoDestinoId(String(novoId));
    const vinculo = resolverConfiguracaoVinculoFracionamento(vinculosAtuais, novoId);
    setFatorConversao(vinculo?.fator_conversao ? String(vinculo.fator_conversao) : "");
    setValidadeDias(
      vinculo?.validade_apos_abertura_dias ? String(vinculo.validade_apos_abertura_dias) : "",
    );
    setObservacao(vinculo?.observacao || "");
  }

  async function abrirModal() {
    if (!podeFracionarClinica) {
      toast.error("Este produto nao pode ser destinado ao estoque clinico.");
      return;
    }
    setAberto(true);
    setLoading(true);
    setBusca("");
    setQuantidadeOrigem("1");
    setProdutoDestinoId("");
    setFatorConversao("");
    setValidadeDias("");
    setLoteOrigemId("");
    setDocumento("");
    setObservacao("");
    try {
      const [contexto] = await Promise.all([
        api.get(`/estoque/fracionamento-clinico/origens/${id}`),
        buscarProdutos(""),
      ]);
      const novosVinculos = contexto.data?.vinculos || [];
      setVinculos(novosVinculos);
      setLotes(contexto.data?.lotes || []);
      if (novosVinculos.length) {
        selecionarProdutoDestino(novosVinculos[0].produto_destino_id, novosVinculos);
      }
    } catch (error) {
      toast.error(extrairMensagemErroApi(error, "Erro ao preparar o fracionamento clinico"));
    } finally {
      setLoading(false);
    }
  }

  async function enviar(event) {
    event.preventDefault();
    if (!produtoDestinoId) {
      toast.error("Selecione o produto em ml ou unidade que recebera o saldo clinico.");
      return;
    }
    if (parseNumeroInput(quantidadeOrigem) <= 0 || parseNumeroInput(fatorConversao) <= 0) {
      toast.error("Informe a quantidade de embalagens e o conteudo de cada embalagem.");
      return;
    }
    try {
      setLoading(true);
      const response = await api.post(
        "/estoque/fracionamento-clinico/converter",
        montarPayloadFracionamentoClinico({
          produtoOrigemId: id,
          produtoDestinoId,
          quantidadeOrigem,
          fatorConversao,
          validadeAposAberturaDias: validadeDias,
          loteOrigemId,
          documento,
          observacao,
        }),
      );
      toast.success(
        `${formatarQuantidade(response.data.quantidade_origem)} ${produto?.unidade || "UN"} destinado(s) a clinica: ${formatarQuantidade(response.data.quantidade_destino)} ${produtoDestino?.unidade || "UN"}.`,
        { duration: 5000 },
      );
      setAberto(false);
      await carregarDados();
    } catch (error) {
      toast.error(extrairMensagemErroApi(error, "Erro ao destinar o produto a clinica"));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!aberto) return undefined;
    const timer = window.setTimeout(() => {
      buscarProdutos(busca).catch((error) => {
        toast.error(extrairMensagemErroApi(error, "Erro ao buscar produtos clinicos"));
      });
    }, 300);
    return () => window.clearTimeout(timer);
  }, [aberto, busca, buscarProdutos]);

  return {
    aberto,
    busca,
    custoDestinoUnitario,
    documento,
    enviar,
    fatorConversao,
    fechar: () => setAberto(false),
    formatMoney: formatMoneyBRL,
    formatarQuantidade,
    loading,
    loteOrigemId,
    lotes,
    observacao,
    onAbrir: abrirModal,
    onSelecionarProduto: selecionarProdutoDestino,
    podeFracionarClinica,
    produto,
    produtoDestino,
    produtoDestinoId,
    produtosDisponiveis,
    quantidadeDestino,
    quantidadeOrigem,
    setBusca,
    setDocumento,
    setFatorConversao,
    setLoteOrigemId,
    setObservacao,
    setQuantidadeOrigem,
    setValidadeDias,
    validadeDias,
  };
}
