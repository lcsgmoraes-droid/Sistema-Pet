import { toast } from "react-hot-toast";
import api from "../../api";
import {
  clonarItensPedido,
  converterPedidoParaFormData,
  numeroSeguro,
  textoNumeroSeguro,
} from "./pedidoCompraUtils";

export function createPedidosCompraFormularioController({
  abrirModalSugestao,
  carregarProdutosFornecedor,
  contextoRascunhoSugestao,
  formData,
  formDataInicial,
  itemFormInicial,
  limparEstadosSugestao,
  modoEdicao,
  obterFornecedorPorId,
  obterGrupoDoFornecedor,
  obterParametrosGrupoFornecedor,
  pedidoEditando,
  setContextoRascunhoSugestao,
  setEstrategiaMesclaItens,
  setFornecedorTexto,
  setFormData,
  setIncluirGrupoFornecedor,
  setItemForm,
  setLoadingPrepararSugestao,
  setModoEdicao,
  setMostrarForm,
  setMostrarModalRascunhoSugestao,
  setMostrarSugestoesProduto,
  setPedidoEditando,
  setProdutos,
  setProdutoTexto,
}) {
  const limparFormularioPedido = () => {
    setFormData(formDataInicial);
    setItemForm(itemFormInicial);
    setEstrategiaMesclaItens("somar");
    setFornecedorTexto("");
    setProdutoTexto("");
    setProdutos([]);
    setIncluirGrupoFornecedor(false);
    setMostrarSugestoesProduto(false);
    limparEstadosSugestao();
  };

  const fecharFormularioPedido = () => {
    setMostrarForm(false);
    setModoEdicao(false);
    setPedidoEditando(null);
    limparFormularioPedido();
  };

  const abrirNovoFormulario = () => {
    setModoEdicao(false);
    setPedidoEditando(null);
    limparFormularioPedido();
    setMostrarForm(true);
  };

  const combinarCabecalhoPedido = (formBase, formAtual) => ({
    fornecedor_id: formBase.fornecedor_id || formAtual.fornecedor_id || "",
    data_prevista_entrega: formAtual.data_prevista_entrega || formBase.data_prevista_entrega || "",
    valor_frete:
      numeroSeguro(formAtual.valor_frete) > 0
        ? textoNumeroSeguro(formAtual.valor_frete, "0")
        : textoNumeroSeguro(formBase.valor_frete, "0"),
    valor_desconto:
      numeroSeguro(formAtual.valor_desconto) > 0
        ? textoNumeroSeguro(formAtual.valor_desconto, "0")
        : textoNumeroSeguro(formBase.valor_desconto, "0"),
    observacoes: formAtual.observacoes?.trim() || formBase.observacoes || "",
  });

  const obterSnapshotFormularioAtual = () => ({
    ...formData,
    fornecedor_id: formData.fornecedor_id?.toString() || "",
    data_prevista_entrega: formData.data_prevista_entrega || "",
    valor_frete: textoNumeroSeguro(formData.valor_frete, "0"),
    valor_desconto: textoNumeroSeguro(formData.valor_desconto, "0"),
    observacoes: formData.observacoes || "",
    itens: clonarItensPedido(formData.itens),
  });

  const aplicarPedidoNoFormulario = async (
    pedidoCompleto,
    formDataOverride = null,
    options = {},
  ) => {
    const { mensagemSucesso = "", mostrarToast = false } = options;
    const fornecedorId = Number(pedidoCompleto?.fornecedor_id);
    const fornecedorSelecionado = obterFornecedorPorId(fornecedorId);
    const proximoFormData = formDataOverride || converterPedidoParaFormData(pedidoCompleto);

    setModoEdicao(true);
    setPedidoEditando(pedidoCompleto);
    setFormData(proximoFormData);
    setFornecedorTexto(fornecedorSelecionado?.nome || "");
    setIncluirGrupoFornecedor(Boolean(obterGrupoDoFornecedor(fornecedorId)));
    setItemForm(itemFormInicial);
    setProdutoTexto("");
    setMostrarSugestoesProduto(false);
    setMostrarForm(true);
    limparEstadosSugestao();

    if (fornecedorId) {
      await carregarProdutosFornecedor(fornecedorId);
    }

    if (mostrarToast && mensagemSucesso) {
      toast.success(mensagemSucesso);
    }
  };

  const iniciarPedidoSeparadoComSnapshot = async (snapshot, fornecedorId, abrirSugestao = true) => {
    const fornecedorSelecionado = obterFornecedorPorId(fornecedorId);
    const proximoFormData = {
      ...formDataInicial,
      ...snapshot,
      fornecedor_id: fornecedorId ? String(fornecedorId) : "",
      itens: clonarItensPedido(snapshot?.itens || []),
    };

    setModoEdicao(false);
    setPedidoEditando(null);
    setFormData(proximoFormData);
    setFornecedorTexto(fornecedorSelecionado?.nome || "");
    setIncluirGrupoFornecedor(Boolean(obterGrupoDoFornecedor(fornecedorId)));
    setItemForm(itemFormInicial);
    setProdutoTexto("");
    setMostrarSugestoesProduto(false);
    setMostrarForm(true);
    limparEstadosSugestao();

    if (fornecedorId) {
      await carregarProdutosFornecedor(fornecedorId);
    }

    if (abrirSugestao) {
      await abrirModalSugestao(fornecedorId, "merge");
    }
  };

  const abrirFluxoSugestaoInteligente = async () => {
    if (!formData.fornecedor_id) {
      toast.error("Selecione um fornecedor primeiro");
      return;
    }

    const fornecedorId = Number(formData.fornecedor_id);
    const snapshotFormulario = obterSnapshotFormularioAtual();
    const editandoMesmoRascunho =
      modoEdicao &&
      pedidoEditando &&
      Number(pedidoEditando.id) > 0 &&
      Number(pedidoEditando.fornecedor_id) === fornecedorId &&
      pedidoEditando.status === "rascunho";

    if (editandoMesmoRascunho) {
      setContextoRascunhoSugestao({
        tipo: "atual",
        pedidoRascunho: pedidoEditando,
        pedidoNovo: snapshotFormulario,
        totalRascunhos: 1,
      });
      setMostrarModalRascunhoSugestao(true);
      return;
    }

    setLoadingPrepararSugestao(true);
    try {
      const response = await api.get(`/pedidos-compra/rascunho/fornecedor/${fornecedorId}`, {
        params: obterParametrosGrupoFornecedor(fornecedorId),
      });
      const pedidoRascunho = response?.data?.pedido || null;

      if (pedidoRascunho) {
        setContextoRascunhoSugestao({
          tipo: "externo",
          pedidoRascunho,
          pedidoNovo: snapshotFormulario,
          totalRascunhos: Number(response?.data?.total_rascunhos || 1),
        });
        setMostrarModalRascunhoSugestao(true);
        return;
      }

      await abrirModalSugestao(fornecedorId);
    } catch (error) {
      console.error("Erro ao verificar rascunho do fornecedor:", error);
      toast.error(error.response?.data?.detail || "Erro ao verificar rascunho do fornecedor");
    } finally {
      setLoadingPrepararSugestao(false);
    }
  };

  const fecharModalRascunho = () => {
    setMostrarModalRascunhoSugestao(false);
    setContextoRascunhoSugestao(null);
  };

  const decidirAcaoRascunhoSugestao = async (acao) => {
    const contexto = contextoRascunhoSugestao;
    if (!contexto) {
      return;
    }

    const { pedidoRascunho, pedidoNovo, tipo } = contexto;
    const fornecedorId = Number(pedidoRascunho?.fornecedor_id || pedidoNovo?.fornecedor_id);

    fecharModalRascunho();
    setLoadingPrepararSugestao(true);

    try {
      if (acao === "carregar" || acao === "manter") {
        if (tipo === "externo" && pedidoRascunho) {
          await aplicarPedidoNoFormulario(
            pedidoRascunho,
            converterPedidoParaFormData(pedidoRascunho),
            {
              mostrarToast: true,
              mensagemSucesso: "Rascunho existente carregado.",
            },
          );
        } else {
          toast("O rascunho atual foi mantido sem aplicar nova sugestao.");
        }
        return;
      }

      if (acao === "novo") {
        await iniciarPedidoSeparadoComSnapshot(pedidoNovo, fornecedorId, true);
        toast.success("Novo pedido iniciado para o mesmo fornecedor.");
        return;
      }

      const preservarQuantidades = acao === "analisar_preservar" || acao === "mesclar";
      const substituirItens = acao === "analisar_substituir" || acao === "substituir";
      setEstrategiaMesclaItens(preservarQuantidades ? "manter_existente" : "somar");

      if (tipo === "externo" && pedidoRascunho) {
        const formRascunho = converterPedidoParaFormData(pedidoRascunho);
        const itensConsolidados = clonarItensPedido(formRascunho.itens);
        const cabecalhoConsolidado = combinarCabecalhoPedido(formRascunho, pedidoNovo);

        await aplicarPedidoNoFormulario(
          pedidoRascunho,
          {
            ...formRascunho,
            ...cabecalhoConsolidado,
            itens: itensConsolidados,
          },
          {
            mostrarToast: true,
            mensagemSucesso: preservarQuantidades
              ? "Rascunho carregado. A sugestao vai manter quantidades ja preenchidas."
              : "Rascunho carregado. A sugestao vai substituir os itens ao confirmar.",
          },
        );

        setEstrategiaMesclaItens(preservarQuantidades ? "manter_existente" : "somar");
        await abrirModalSugestao(fornecedorId, substituirItens ? "replace" : "merge");
        return;
      }

      setEstrategiaMesclaItens(preservarQuantidades ? "manter_existente" : "somar");
      await abrirModalSugestao(fornecedorId, substituirItens ? "replace" : "merge");
    } catch (error) {
      console.error("Erro ao preparar consolidação do rascunho:", error);
      toast.error(error.response?.data?.detail || "Erro ao preparar a sugestão inteligente");
    } finally {
      setLoadingPrepararSugestao(false);
    }
  };

  return {
    limparFormularioPedido,
    fecharFormularioPedido,
    abrirNovoFormulario,
    aplicarPedidoNoFormulario,
    abrirFluxoSugestaoInteligente,
    fecharModalRascunho,
    decidirAcaoRascunhoSugestao,
  };
}
