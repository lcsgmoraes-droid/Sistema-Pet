import { toast } from "react-hot-toast";
import api from "../../api";
import { normalizarColunasDocumentoPedido } from "./pedidoDocumentoColunas";
import { baixarArquivoResposta } from "./pedidoCompraUtils";

function extrairEmailFornecedor(fornecedor) {
  if (!fornecedor) return "";

  const candidatos = [
    fornecedor.email,
    fornecedor.email_principal,
    fornecedor.email_comercial,
    fornecedor.contato_email,
    fornecedor?.contato?.email,
  ];

  const emailValido = candidatos.find((valor) => typeof valor === "string" && valor.includes("@"));

  return (emailValido || "").trim();
}

function serializarQuantidadePorEmbalagem(item) {
  const unidadeCompra = item.unidade_compra || "UN";
  if (unidadeCompra === "UN") {
    return 1;
  }

  const quantidade = Number(item.quantidade_por_embalagem);
  return Number.isFinite(quantidade) && quantidade > 0 ? quantidade : null;
}

export function createPedidosCompraOperacoesController({
  aplicarPedidoNoFormulario,
  carregarDados,
  colunasDocumentoPedido,
  dadosEnvio,
  emailEnvioDisponivel,
  exportandoArquivo,
  fecharFormularioPedido,
  formData,
  obterFornecedorPorId,
  pedidoEditando,
  pedidoParaEnviar,
  pedidoParaExportar,
  pedidoSelecionado,
  pedidos,
  setColunasDocumentoPedido,
  setDadosEnvio,
  setExportandoArquivo,
  setLoading,
  setMostrarConfronto,
  setMostrarModalEnvio,
  setMostrarModalExportacao,
  setMostrarRecebimento,
  setPedidoConfronto,
  setPedidoParaEnviar,
  setPedidoParaExportar,
  setPedidoSelecionado,
}) {
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (formData.itens.length === 0) {
      toast.error("Adicione pelo menos 1 item ao pedido");
      return;
    }

    setLoading(true);
    try {
      const dadosEnvio = {
        ...formData,
        fornecedor_id: parseInt(formData.fornecedor_id),
        valor_frete: parseFloat(formData.valor_frete),
        valor_desconto: parseFloat(formData.valor_desconto),
        data_prevista_entrega: formData.data_prevista_entrega
          ? `${formData.data_prevista_entrega}T12:00:00`
          : null,
        itens: formData.itens.map((item) => ({
          produto_id: item.produto_id,
          quantidade_pedida: parseFloat(item.quantidade_pedida),
          unidade_compra: item.unidade_compra || "UN",
          quantidade_por_embalagem: serializarQuantidadePorEmbalagem(item),
          preco_unitario: parseFloat(item.preco_unitario),
          desconto_item: parseFloat(item.desconto_item || 0),
        })),
      };
      await api.post("/pedidos-compra/", dadosEnvio);

      toast.success("✅ Pedido criado com sucesso!");
      fecharFormularioPedido();
      carregarDados();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erro ao criar pedido");
    } finally {
      setLoading(false);
    }
  };

  const enviarPedido = async (pedido) => {
    const fornecedor = obterFornecedorPorId(pedido.fornecedor_id);
    const emailFornecedor = extrairEmailFornecedor(fornecedor);

    // Abrir modal de envio ao invés de enviar direto
    setPedidoParaEnviar(pedido.id);
    setDadosEnvio({
      email: emailFornecedor,
      whatsapp: "",
      formatos: {
        pdf: true,
        excel: false,
      },
    });
    setMostrarModalEnvio(true);
  };

  const atualizarColunasDocumento = (colunas) => {
    setColunasDocumentoPedido(normalizarColunasDocumentoPedido(colunas));
  };

  const abrirModalExportacao = (pedido, formato) => {
    setPedidoParaExportar({
      id: pedido.id,
      numero_pedido: pedido.numero_pedido,
      formato,
    });
    setMostrarModalExportacao(true);
  };

  const fecharModalExportacao = () => {
    if (exportandoArquivo) {
      return;
    }
    setMostrarModalExportacao(false);
    setPedidoParaExportar(null);
  };

  const confirmarEnvioPedido = async () => {
    if (!dadosEnvio.email && !dadosEnvio.whatsapp) {
      toast.error("Informe um e-mail ou WhatsApp");
      return;
    }

    if (!emailEnvioDisponivel) {
      toast.error("O servidor ainda não está configurado para enviar e-mails");
      return;
    }

    if (!dadosEnvio.formatos.pdf && !dadosEnvio.formatos.excel) {
      toast.error("Selecione pelo menos um formato (PDF ou Excel)");
      return;
    }

    if (normalizarColunasDocumentoPedido(colunasDocumentoPedido).length === 0) {
      toast.error("Selecione pelo menos uma coluna para o documento");
      return;
    }

    try {
      // Aqui você pode implementar o envio real por e-mail/WhatsApp no futuro
      // Por enquanto, apenas marca como enviado
      const response = await api.post(`/pedidos-compra/${pedidoParaEnviar}/enviar`, {
        email: dadosEnvio.email,
        whatsapp: dadosEnvio.whatsapp,
        formatos: dadosEnvio.formatos,
        colunas_exportacao: normalizarColunasDocumentoPedido(colunasDocumentoPedido),
      });

      const tipoEnvio = response?.data?.tipo_envio;
      if (tipoEnvio === "email") {
        toast.success("Pedido enviado por e-mail com sucesso");
      } else if (tipoEnvio === "manual") {
        toast.success("Pedido marcado como enviado manualmente");
      } else {
        toast.success(response?.data?.message || "Pedido processado com sucesso");
      }

      setMostrarModalEnvio(false);
      carregarDados();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erro ao enviar pedido");
    }
  };

  const marcarComoEnviadoManualmente = async () => {
    try {
      await api.post(`/pedidos-compra/${pedidoParaEnviar}/enviar`, {
        envio_manual: true,
      });

      toast.success("✅ Pedido marcado como enviado manualmente!");
      setMostrarModalEnvio(false);
      carregarDados();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erro ao marcar pedido");
    }
  };

  const confirmarPedido = async (id) => {
    try {
      await api.post(`/pedidos-compra/${id}/confirmar`, {});
      toast.success("✅ Pedido confirmado!");
      carregarDados();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erro ao confirmar pedido");
    }
  };

  const exportarPDF = async (id) => {
    const pedido = pedidos.find((item) => Number(item.id) === Number(id));
    if (!pedido) {
      toast.error("Pedido nao encontrado para exportacao");
      return;
    }
    abrirModalExportacao(pedido, "pdf");
  };

  const exportarExcel = async (id) => {
    const pedido = pedidos.find((item) => Number(item.id) === Number(id));
    if (!pedido) {
      toast.error("Pedido nao encontrado para exportacao");
      return;
    }
    abrirModalExportacao(pedido, "excel");
  };

  const confirmarExportacaoPedido = async () => {
    if (!pedidoParaExportar) {
      return;
    }

    const colunasNormalizadas = normalizarColunasDocumentoPedido(colunasDocumentoPedido);
    if (colunasNormalizadas.length === 0) {
      toast.error("Selecione pelo menos uma coluna para o documento");
      return;
    }

    const { id, formato } = pedidoParaExportar;
    const rota =
      formato === "pdf" ? `/pedidos-compra/${id}/export/pdf` : `/pedidos-compra/${id}/export/excel`;
    const fallback = formato === "pdf" ? `pedido_${id}.pdf` : `pedido_${id}.xlsx`;

    setExportandoArquivo(true);
    try {
      const response = await api.get(rota, {
        params: {
          colunas: colunasNormalizadas.join(","),
        },
        responseType: "blob",
      });
      baixarArquivoResposta(response, fallback);
      toast.success(`${formato.toUpperCase()} exportado com sucesso!`);
      fecharModalExportacao();
    } catch {
      toast.error(`Erro ao exportar ${formato.toUpperCase()}`);
    } finally {
      setExportandoArquivo(false);
    }
  };

  const verDetalhes = async (pedido) => {
    try {
      const response = await api.get(`/pedidos-compra/${pedido.id}`);
      setPedidoSelecionado(response.data);
      setMostrarRecebimento(true);
    } catch {
      toast.error("Erro ao carregar detalhes do pedido");
    }
  };

  const reverterStatus = async (id) => {
    if (!confirm("⚠️ Deseja reverter o status deste pedido para a etapa anterior?")) {
      return;
    }
    try {
      const response = await api.post(`/pedidos-compra/${id}/reverter`, {});
      toast.success(
        `⏪ Status revertido: ${response.data.status_anterior} → ${response.data.status_atual}`,
      );
      carregarDados();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erro ao reverter status");
    }
  };

  const cancelarPedido = async (pedido) => {
    const acao = pedido.status === "rascunho" ? "cancelar/excluir" : "cancelar";
    const motivo = window.prompt(
      `Informe o motivo para ${acao} o pedido ${pedido.numero_pedido}:`,
      "Cancelado pelo usuário",
    );

    if (!motivo) return;

    const motivoLimpo = motivo.trim();
    if (motivoLimpo.length < 10) {
      toast.error("Informe um motivo com pelo menos 10 caracteres");
      return;
    }

    try {
      await api.post(`/pedidos-compra/${pedido.id}/cancelar`, null, {
        params: { motivo: motivoLimpo },
      });
      toast.success("✅ Pedido cancelado com sucesso");
      carregarDados();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erro ao cancelar pedido");
    }
  };

  const abrirEdicao = async (pedido) => {
    if (pedido.status !== "rascunho") {
      toast.error("⚠️ Apenas pedidos em rascunho podem ser editados");
      return;
    }

    try {
      const response = await api.get(`/pedidos-compra/${pedido.id}`);

      const pedidoCompleto = response.data;
      await aplicarPedidoNoFormulario(pedidoCompleto, null, {
        mostrarToast: true,
        mensagemSucesso: "Modo de edição ativado",
      });
      return;
    } catch {
      toast.error("Erro ao carregar pedido para edição");
    }
  };

  const editarPedido = async (e) => {
    e.preventDefault();

    if (formData.itens.length === 0) {
      toast.error("⚠️ Adicione pelo menos um item ao pedido");
      return;
    }

    try {
      setLoading(true);

      const dadosEnvio = {
        ...formData,
        fornecedor_id: parseInt(formData.fornecedor_id),
        valor_frete: parseFloat(formData.valor_frete),
        valor_desconto: parseFloat(formData.valor_desconto),
        data_prevista_entrega: formData.data_prevista_entrega
          ? `${formData.data_prevista_entrega}T12:00:00`
          : null,
        itens: formData.itens.map((item) => ({
          produto_id: item.produto_id,
          quantidade_pedida: parseFloat(item.quantidade_pedida),
          unidade_compra: item.unidade_compra || "UN",
          quantidade_por_embalagem: serializarQuantidadePorEmbalagem(item),
          preco_unitario: parseFloat(item.preco_unitario),
          desconto_item: parseFloat(item.desconto_item || 0),
        })),
      };

      await api.put(`/pedidos-compra/${pedidoEditando.id}`, dadosEnvio);

      toast.success("✏️ Pedido atualizado com sucesso!");
      fecharFormularioPedido();
      carregarDados();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erro ao atualizar pedido");
    } finally {
      setLoading(false);
    }
  };

  const abrirRecebimento = async (pedido) => {
    try {
      const response = await api.get(`/pedidos-compra/${pedido.id}`);
      setPedidoSelecionado(response.data);
      setMostrarRecebimento(true);
    } catch {
      toast.error("Erro ao carregar detalhes do pedido");
    }
  };

  const abrirConfronto = async (pedido) => {
    try {
      const response = await api.get(`/pedidos-compra/${pedido.id}`);
      setPedidoConfronto(response.data);
      setMostrarConfronto(true);
    } catch {
      toast.error("Erro ao carregar detalhes do pedido");
    }
  };

  const receberPedido = async (itensRecebimento) => {
    try {
      await api.post(`/pedidos-compra/${pedidoSelecionado.id}/receber`, {
        itens: itensRecebimento,
      });
      toast.success("✅ Recebimento processado com sucesso!");
      setMostrarRecebimento(false);
      setPedidoSelecionado(null);
      carregarDados();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erro ao processar recebimento");
    }
  };

  return {
    handleSubmit,
    enviarPedido,
    atualizarColunasDocumento,
    fecharModalExportacao,
    confirmarEnvioPedido,
    marcarComoEnviadoManualmente,
    confirmarPedido,
    exportarPDF,
    exportarExcel,
    confirmarExportacaoPedido,
    verDetalhes,
    reverterStatus,
    cancelarPedido,
    abrirEdicao,
    editarPedido,
    abrirRecebimento,
    abrirConfronto,
    receberPedido,
  };
}
