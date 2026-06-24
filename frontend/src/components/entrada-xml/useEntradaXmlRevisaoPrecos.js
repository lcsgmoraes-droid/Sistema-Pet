import { useEffect, useState } from "react";
import { formatBRL } from "../../utils/formatters";
import {
  exportarRelatorioCustosMaioresCSV as exportarRelatorioCustosMaioresCSVArquivo,
  exportarRelatorioCustosMaioresPDF as exportarRelatorioCustosMaioresPDFArquivo,
} from "./entradaXmlRelatorioCustos";
import {
  BASE_CALCULO_MARGEM_OPCOES,
  aplicarOverridesPackNoPreview,
  normalizarProdutoPreview,
  obterCustoBasePreviewItem,
} from "./entradaXmlUtils";

const ACOES_PROCESSAMENTO_PADRAO = {
  lancar_estoque: true,
  atualizar_custo: true,
  atualizar_preco_venda: false,
  gerar_contas_pagar: true,
};

export default function useEntradaXmlRevisaoPrecos({
  api,
  carregarDados,
  multiplicadoresPack,
  notaSelecionada,
  salvarConferenciaAtual,
  setLoading,
  setMostrarDetalhes,
  setMostrarVisualizacao,
  setNotaSelecionada,
  toast,
}) {
  const [mostrarRevisaoPrecos, setMostrarRevisaoPrecos] = useState(false);
  const [previewProcessamento, setPreviewProcessamento] = useState(null);
  const [custosAjustados, setCustosAjustados] = useState({});
  const [inputsRevisaoCustos, setInputsRevisaoCustos] = useState({});
  const [precosAjustados, setPrecosAjustados] = useState({});
  const [inputsRevisaoPrecos, setInputsRevisaoPrecos] = useState({});
  const [filtroCusto, setFiltroCusto] = useState("todos");
  const [gerandoRelatorioCustos, setGerandoRelatorioCustos] = useState(false);
  const [baseCalculoMargem, setBaseCalculoMargem] = useState("nf");
  const [acoesProcessamento, setAcoesProcessamento] = useState(ACOES_PROCESSAMENTO_PADRAO);

  const calcularPrecoVenda = (custoNovo, margemDesejada) => {
    if (margemDesejada >= 100) return custoNovo * 2;
    return custoNovo / (1 - margemDesejada / 100);
  };

  const parseNumeroFlexivel = (valor) => {
    if (typeof valor === "number") {
      return Number.isFinite(valor) ? valor : 0;
    }

    let texto = String(valor || "").trim();
    if (!texto) return 0;

    texto = texto.replaceAll(/\s+/g, "");
    texto = texto.replaceAll(/[^\d,.-]/g, "");

    if (texto.includes(",") && texto.includes(".")) {
      if (texto.lastIndexOf(",") > texto.lastIndexOf(".")) {
        texto = texto.replaceAll(".", "").replace(",", ".");
      } else {
        texto = texto.replaceAll(",", "");
      }
    } else if (texto.includes(",")) {
      texto = texto.replaceAll(".", "").replace(",", ".");
    }

    const numero = Number.parseFloat(texto);
    return Number.isFinite(numero) ? numero : 0;
  };

  const calcularMargem = (precoVenda, custoNovo) => {
    if (precoVenda <= 0) return 0;
    return ((precoVenda - custoNovo) / precoVenda) * 100;
  };

  const obterCustoSistemaItem = (item) => {
    const itemId = item?.item_id ?? item?.id;
    const overrideRaw = custosAjustados[itemId] ?? custosAjustados[String(itemId)];
    const override = Number(overrideRaw);
    if (Number.isFinite(override) && override > 0) {
      return override;
    }
    return obterCustoBasePreviewItem(item);
  };

  const obterInfoBaseCalculoMargem = ({ custoNF = 0, custoSistema = 0 }) => {
    const custoNFNormalizado = Number(custoNF || 0);
    const custoSistemaNormalizado = Number(custoSistema || 0);

    if (baseCalculoMargem === "sistema") {
      return {
        value: "sistema",
        label: "Custo no sistema",
        valor: custoSistemaNormalizado > 0 ? custoSistemaNormalizado : custoNFNormalizado,
        fallback: !(custoSistemaNormalizado > 0),
        descricao:
          custoSistemaNormalizado > 0
            ? "Calculando sobre o custo informado no sistema."
            : "Sem custo informado no sistema; usando o custo da NF.",
      };
    }

    return {
      value: "nf",
      label: "Custo da NF",
      valor: custoNFNormalizado,
      fallback: false,
      descricao: "Calculando sobre o custo fiscal da NF.",
    };
  };

  const obterResumoCustoItem = (item) => {
    const produto = normalizarProdutoPreview(item);
    const custoAnterior = Number(produto.custo_anterior || 0);
    const custoNF = obterCustoBasePreviewItem(item);
    const custoSistema = obterCustoSistemaItem(item);
    const precoVendaAtual = Number(produto.preco_venda_atual || 0);
    const baseMargem = obterInfoBaseCalculoMargem({ custoNF, custoSistema });
    const variacaoCustoPercentual =
      custoAnterior > 0
        ? Number((((custoSistema - custoAnterior) / custoAnterior) * 100).toFixed(2))
        : 0;
    const margemReferencia = Number(
      produto.margem_atual ?? calcularMargem(precoVendaAtual, custoAnterior),
    );
    const margemProjetada = calcularMargem(precoVendaAtual, baseMargem.valor);

    return {
      produto,
      custoAnterior,
      custoNF,
      custoSistema,
      baseMargem,
      custoManual: Math.abs(custoSistema - custoNF) > 0.0001,
      variacaoCustoPercentual,
      precoVendaAtual,
      margemReferencia,
      margemProjetada,
    };
  };

  const processarNota = async (notaId) => {
    try {
      if (notaSelecionada?.id === notaId) {
        const conferenciaSalva = await salvarConferenciaAtual({ silencioso: true });
        if (!conferenciaSalva) {
          return;
        }
      }

      const response = await api.get(`/notas-entrada/${notaId}/preview-processamento`);

      const previewComOverrides = aplicarOverridesPackNoPreview(response.data, multiplicadoresPack);

      setBaseCalculoMargem("nf");
      setAcoesProcessamento({
        ...ACOES_PROCESSAMENTO_PADRAO,
        ...(previewComOverrides.acoes_processamento_sugeridas || {}),
      });
      setPreviewProcessamento(previewComOverrides);
      setMostrarRevisaoPrecos(true);
      setMostrarDetalhes(false);

      const custosIniciais = {};
      const inputsCustosIniciais = {};
      const precosIniciais = {};
      const inputsIniciais = {};
      previewComOverrides.itens.forEach((item) => {
        const itemId = item.item_id ?? item.id;
        const custoBase = obterCustoBasePreviewItem(item);
        const custoExistente = Number(custosAjustados[itemId] ?? custosAjustados[String(itemId)]);
        const custoInicial =
          Number.isFinite(custoExistente) && custoExistente > 0 ? custoExistente : custoBase;

        custosIniciais[itemId] = custoInicial;
        inputsCustosIniciais[itemId] = formatBRL(custoInicial);

        if (item.produto_vinculado) {
          const margemProjetada = Number(
            item.produto_vinculado.margem_projetada_custo_novo ??
              calcularMargem(item.produto_vinculado.preco_venda_atual, custoInicial),
          );
          precosIniciais[item.produto_vinculado.produto_id] = {
            preco_venda: item.produto_vinculado.preco_venda_atual,
            margem: margemProjetada,
          };
          inputsIniciais[item.produto_vinculado.produto_id] = {
            preco_venda: formatBRL(item.produto_vinculado.preco_venda_atual),
            margem: formatBRL(margemProjetada),
          };
        }
      });
      setCustosAjustados(custosIniciais);
      setInputsRevisaoCustos(inputsCustosIniciais);
      setPrecosAjustados(precosIniciais);
      setInputsRevisaoPrecos(inputsIniciais);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erro ao carregar preview");
    }
  };

  const confirmarProcessamento = async () => {
    setLoading(true);
    try {
      const precosParaAtualizar = [];
      Object.entries(precosAjustados).forEach(([produtoId, dados]) => {
        const itemOriginal = previewProcessamento.itens.find(
          (i) => i.produto_vinculado && i.produto_vinculado.produto_id == produtoId,
        );
        if (
          itemOriginal &&
          itemOriginal.produto_vinculado &&
          dados.preco_venda !== itemOriginal.produto_vinculado.preco_venda_atual
        ) {
          precosParaAtualizar.push({
            produto_id: Number.parseInt(produtoId),
            preco_venda: dados.preco_venda,
          });
        }
      });

      const overridesNaoDefault = Object.fromEntries(
        Object.entries(multiplicadoresPack).flatMap(([itemId, valor]) => {
          const multiplicador = Number.parseInt(valor, 10);

          if (!Number.isInteger(multiplicador) || multiplicador < 1 || multiplicador > 200) {
            return [];
          }

          return [[itemId, multiplicador]];
        }),
      );
      const custosOverride = Object.fromEntries(
        (previewProcessamento.itens || []).flatMap((item) => {
          if (!acoesProcessamento.atualizar_custo) {
            return [];
          }

          const itemId = item.item_id ?? item.id;
          const custoBase = obterCustoBasePreviewItem(item);
          const custoSistema = Number(custosAjustados[itemId] ?? custosAjustados[String(itemId)]);

          if (!Number.isFinite(custoSistema) || custoSistema <= 0) {
            return [];
          }

          if (Math.abs(custoSistema - custoBase) < 0.0001) {
            return [];
          }

          return [[itemId, Number(custoSistema.toFixed(4))]];
        }),
      );
      const response = await api.post(`/notas-entrada/${previewProcessamento.nota_id}/processar`, {
        lancar_estoque: Boolean(acoesProcessamento.lancar_estoque),
        atualizar_custo: Boolean(acoesProcessamento.atualizar_custo),
        atualizar_preco_venda: Boolean(acoesProcessamento.atualizar_preco_venda),
        gerar_contas_pagar: Boolean(acoesProcessamento.gerar_contas_pagar),
        precos_venda_override: acoesProcessamento.atualizar_preco_venda ? precosParaAtualizar : [],
        ...(Object.keys(overridesNaoDefault).length > 0
          ? { multiplicadores_override: overridesNaoDefault }
          : {}),
        ...(Object.keys(custosOverride).length > 0 ? { custos_override: custosOverride } : {}),
      });

      toast.success(
        `✅ Nota processada! ${response.data.itens_processados} itens lançados no estoque`,
        { duration: 5000 },
      );

      setMostrarDetalhes(false);
      setNotaSelecionada(null);
      setMostrarRevisaoPrecos(false);
      setPreviewProcessamento(null);
      setBaseCalculoMargem("nf");
      setCustosAjustados({});
      setInputsRevisaoCustos({});
      setInputsRevisaoPrecos({});
      setAcoesProcessamento(ACOES_PROCESSAMENTO_PADRAO);
      carregarDados();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erro ao processar nota");
    } finally {
      setLoading(false);
    }
  };

  const atualizarPrecoVenda = (produtoId, novoPrecoEntrada, custoNovo) => {
    const novoPreco = parseNumeroFlexivel(novoPrecoEntrada);
    const novaMargem = calcularMargem(novoPreco, custoNovo);
    setPrecosAjustados((prev) => ({
      ...prev,
      [produtoId]: {
        preco_venda: novoPreco,
        margem: novaMargem,
      },
    }));
    setInputsRevisaoPrecos((prev) => ({
      ...prev,
      [produtoId]: {
        preco_venda: String(novoPrecoEntrada ?? ""),
        margem: formatBRL(novaMargem),
      },
    }));
  };

  const atualizarMargem = (produtoId, novaMargemEntrada, custoNovo) => {
    const novaMargem = parseNumeroFlexivel(novaMargemEntrada);
    const novoPreco = calcularPrecoVenda(custoNovo, novaMargem);
    setPrecosAjustados((prev) => ({
      ...prev,
      [produtoId]: {
        preco_venda: novoPreco,
        margem: novaMargem,
      },
    }));
    setInputsRevisaoPrecos((prev) => ({
      ...prev,
      [produtoId]: {
        preco_venda: formatBRL(novoPreco),
        margem: String(novaMargemEntrada ?? ""),
      },
    }));
  };

  const normalizarCamposRevisaoPrecos = (produtoId) => {
    const dados = precosAjustados[produtoId];
    if (!dados) return;

    setInputsRevisaoPrecos((prev) => ({
      ...prev,
      [produtoId]: {
        preco_venda: formatBRL(dados.preco_venda),
        margem: formatBRL(dados.margem),
      },
    }));
  };

  const atualizarCustoSistema = (item, novoCustoEntrada) => {
    const itemId = item?.item_id ?? item?.id;
    const custoBase = obterCustoBasePreviewItem(item);
    const custoDigitado = parseNumeroFlexivel(novoCustoEntrada);
    const custoAplicado = custoDigitado > 0 ? custoDigitado : 0;

    setCustosAjustados((prev) => ({
      ...prev,
      [itemId]: custoAplicado,
    }));
    setInputsRevisaoCustos((prev) => ({
      ...prev,
      [itemId]: String(novoCustoEntrada ?? ""),
    }));

    const produto = normalizarProdutoPreview(item);
    if (!produto?.produto_id) {
      return;
    }

    const precoAtual = Number(
      precosAjustados[produto.produto_id]?.preco_venda ?? produto.preco_venda_atual ?? 0,
    );
    const baseMargem = obterInfoBaseCalculoMargem({
      custoNF: custoBase,
      custoSistema: custoAplicado || custoBase,
    });
    const margemAtualizada = calcularMargem(precoAtual, baseMargem.valor);

    setPrecosAjustados((prev) => ({
      ...prev,
      [produto.produto_id]: {
        preco_venda: precoAtual,
        margem: margemAtualizada,
      },
    }));
    setInputsRevisaoPrecos((prev) => ({
      ...prev,
      [produto.produto_id]: {
        preco_venda: prev?.[produto.produto_id]?.preco_venda ?? formatBRL(precoAtual),
        margem: formatBRL(margemAtualizada),
      },
    }));
  };

  const normalizarCamposRevisaoCustos = (item) => {
    const itemId = item?.item_id ?? item?.id;
    const custoBase = obterCustoBasePreviewItem(item);
    const custoAtual = Number(custosAjustados[itemId] ?? custosAjustados[String(itemId)]);
    const custoNormalizado = Number.isFinite(custoAtual) && custoAtual > 0 ? custoAtual : custoBase;

    setCustosAjustados((prev) => ({
      ...prev,
      [itemId]: custoNormalizado,
    }));
    setInputsRevisaoCustos((prev) => ({
      ...prev,
      [itemId]: formatBRL(custoNormalizado),
    }));

    const produto = normalizarProdutoPreview(item);
    if (!produto?.produto_id) {
      return;
    }

    const precoAtual = Number(
      precosAjustados[produto.produto_id]?.preco_venda ?? produto.preco_venda_atual ?? 0,
    );
    const baseMargem = obterInfoBaseCalculoMargem({
      custoNF: custoBase,
      custoSistema: custoNormalizado,
    });
    const margemAtualizada = calcularMargem(precoAtual, baseMargem.valor);
    setPrecosAjustados((prev) => ({
      ...prev,
      [produto.produto_id]: {
        preco_venda: precoAtual,
        margem: margemAtualizada,
      },
    }));
    setInputsRevisaoPrecos((prev) => ({
      ...prev,
      [produto.produto_id]: {
        preco_venda: prev?.[produto.produto_id]?.preco_venda ?? formatBRL(precoAtual),
        margem: formatBRL(margemAtualizada),
      },
    }));
  };

  useEffect(() => {
    if (!mostrarRevisaoPrecos || !previewProcessamento?.itens?.length) {
      return;
    }

    setPrecosAjustados((prev) => {
      let mudou = false;
      const proximo = { ...prev };

      previewProcessamento.itens.forEach((item) => {
        const produto = normalizarProdutoPreview(item);
        if (!produto?.produto_id) return;

        const resumoCusto = obterResumoCustoItem(item);
        const precoAtual = Number(
          prev[produto.produto_id]?.preco_venda ?? produto.preco_venda_atual ?? 0,
        );
        const margemAtualizada = calcularMargem(precoAtual, resumoCusto.baseMargem.valor);
        const atual = prev[produto.produto_id];

        if (
          !atual ||
          Math.abs(Number(atual.preco_venda || 0) - precoAtual) > 0.0001 ||
          Math.abs(Number(atual.margem || 0) - margemAtualizada) > 0.0001
        ) {
          proximo[produto.produto_id] = {
            preco_venda: precoAtual,
            margem: margemAtualizada,
          };
          mudou = true;
        }
      });

      return mudou ? proximo : prev;
    });

    setInputsRevisaoPrecos((prev) => {
      let mudou = false;
      const proximo = { ...prev };

      previewProcessamento.itens.forEach((item) => {
        const produto = normalizarProdutoPreview(item);
        if (!produto?.produto_id) return;

        const resumoCusto = obterResumoCustoItem(item);
        const precoAtual = Number(
          precosAjustados[produto.produto_id]?.preco_venda ?? produto.preco_venda_atual ?? 0,
        );
        const margemAtualizada = calcularMargem(precoAtual, resumoCusto.baseMargem.valor);
        const precoTextoAtual = prev?.[produto.produto_id]?.preco_venda ?? formatBRL(precoAtual);
        const margemTextoAtual = formatBRL(margemAtualizada);

        if (
          !prev?.[produto.produto_id] ||
          prev[produto.produto_id].preco_venda !== precoTextoAtual ||
          prev[produto.produto_id].margem !== margemTextoAtual
        ) {
          proximo[produto.produto_id] = {
            preco_venda: precoTextoAtual,
            margem: margemTextoAtual,
          };
          mudou = true;
        }
      });

      return mudou ? proximo : prev;
    });
  }, [baseCalculoMargem, mostrarRevisaoPrecos, previewProcessamento]);

  const exportarRelatorioCustosMaioresCSV = () =>
    exportarRelatorioCustosMaioresCSVArquivo({
      api,
      obterResumoCustoItem,
      previewProcessamento,
      setGerandoRelatorioCustos,
      toast,
    });

  const exportarRelatorioCustosMaioresPDF = () =>
    exportarRelatorioCustosMaioresPDFArquivo({
      api,
      obterResumoCustoItem,
      previewProcessamento,
      setGerandoRelatorioCustos,
      toast,
    });

  const voltarParaVisualizacao = () => {
    setMostrarRevisaoPrecos(false);
    setPreviewProcessamento(null);
    setInputsRevisaoPrecos({});
    setInputsRevisaoCustos({});
    setAcoesProcessamento(ACOES_PROCESSAMENTO_PADRAO);
    setBaseCalculoMargem("nf");
    if (notaSelecionada) {
      setMostrarVisualizacao(true);
    }
  };

  const setAcaoProcessamento = (acao, ativo) => {
    setAcoesProcessamento((prev) => ({
      ...prev,
      [acao]: Boolean(ativo),
    }));
  };

  return {
    acoesProcessamento,
    atualizarCustoSistema,
    atualizarMargem,
    atualizarPrecoVenda,
    baseCalculoMargem,
    baseCalculoMargemOpcoes: BASE_CALCULO_MARGEM_OPCOES,
    calcularPrecoVenda,
    carregarPreviewProcessamento: processarNota,
    confirmarProcessamento,
    exportarRelatorioCustosMaioresCSV,
    exportarRelatorioCustosMaioresPDF,
    filtroCusto,
    gerandoRelatorioCustos,
    inputsRevisaoCustos,
    inputsRevisaoPrecos,
    mostrarRevisaoPrecos,
    normalizarCamposRevisaoCustos,
    normalizarCamposRevisaoPrecos,
    obterResumoCustoItem,
    precosAjustados,
    previewProcessamento,
    processarNota,
    setBaseCalculoMargem,
    setAcaoProcessamento,
    setFiltroCusto,
    setMostrarRevisaoPrecos,
    setPreviewProcessamento,
    voltarParaVisualizacao,
  };
}
