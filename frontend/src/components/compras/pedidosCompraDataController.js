import { toast } from "react-hot-toast";
import api from "../../api";

export function createPedidosCompraDataController({
  filtrosPedidos,
  filtrosPedidosInicial,
  paginaPedidos,
  pedidosPorPagina,
  setEmailEnvioDisponivel,
  setFiltrosPedidos,
  setFornecedores,
  setGruposFornecedores,
  setLoadingListaPedidos,
  setPaginaPedidos,
  setPaginacaoPedidos,
  setPedidos,
  setPedidosPorPagina,
}) {
  const montarParametrosPedidos = (filtros = filtrosPedidosInicial, opcoes = {}) => {
    const params = {
      page: Number(opcoes.page || paginaPedidos || 1),
      page_size: Number(opcoes.pageSize || pedidosPorPagina || 20),
    };
    Object.entries(filtros).forEach(([chave, valor]) => {
      const texto = String(valor || "").trim();
      if (texto) {
        params[chave] = texto;
      }
    });
    return params;
  };

  const extrairListaResposta = (data, chaves = []) => {
    if (Array.isArray(data)) return data;
    for (const chave of chaves) {
      if (Array.isArray(data?.[chave])) {
        return data[chave];
      }
    }
    return data?.items || [];
  };

  const aplicarRespostaPedidos = (data, opcoes = {}) => {
    const lista = extrairListaResposta(data, ["pedidos"]);
    const total = Number(data?.total ?? lista.length);
    const pageSize = Number(data?.page_size || opcoes.pageSize || pedidosPorPagina || 20);
    const page = Number(data?.page || opcoes.page || paginaPedidos || 1);
    const pages = Number(data?.pages ?? (total > 0 ? Math.ceil(total / pageSize) : 0));

    setPedidos(lista);
    setPaginaPedidos(page);
    setPedidosPorPagina(pageSize);
    setPaginacaoPedidos({ total, page, page_size: pageSize, pages });
    return lista;
  };

  const atualizarFiltroPedidos = (campo, valor) => {
    setFiltrosPedidos((prev) => ({ ...prev, [campo]: valor }));
  };

  const aplicarFiltrosPedidos = (event) => {
    event?.preventDefault();
    setPaginaPedidos(1);
    carregarDados(filtrosPedidos, { apenasPedidos: true, page: 1 });
  };

  const limparFiltrosPedidos = () => {
    setFiltrosPedidos(filtrosPedidosInicial);
    setPaginaPedidos(1);
    carregarDados(filtrosPedidosInicial, { apenasPedidos: true, page: 1 });
  };

  const selecionarVisaoPedidos = (visao) => {
    const proximosFiltros = { ...filtrosPedidos, visao, status: "" };
    setFiltrosPedidos(proximosFiltros);
    setPaginaPedidos(1);
    carregarDados(proximosFiltros, { apenasPedidos: true, page: 1 });
  };

  const alterarPaginaPedidos = (page) => {
    setPaginaPedidos(page);
    carregarDados(filtrosPedidos, { apenasPedidos: true, page });
  };

  const alterarPedidosPorPagina = (pageSize) => {
    setPedidosPorPagina(pageSize);
    setPaginaPedidos(1);
    carregarDados(filtrosPedidos, { apenasPedidos: true, page: 1, pageSize });
  };

  const carregarDados = async (filtrosParaAplicar = filtrosPedidos, opcoes = {}) => {
    const params = montarParametrosPedidos(filtrosParaAplicar, opcoes);
    setLoadingListaPedidos(true);
    try {
      if (opcoes.apenasPedidos) {
        const pedidosRes = await api.get("/pedidos-compra/", { params });
        aplicarRespostaPedidos(pedidosRes.data, opcoes);
        return;
      }

      const [pedidosRes, fornecedoresRes, gruposRes, envioStatusRes] = await Promise.all([
        api.get("/pedidos-compra/", { params }),
        api.get("/clientes/?tipo_cadastro=fornecedor&apenas_ativos=true"),
        api.get("/fornecedor-grupos/"),
        api
          .get("/pedidos-compra/envio/status")
          .catch(() => ({ data: { email_configurado: false } })),
      ]);

      // Tratar resposta dos pedidos (pode ser array direto ou objeto paginado)
      aplicarRespostaPedidos(pedidosRes.data, opcoes);

      // Tratar resposta dos fornecedores
      const fornecedoresData = extrairListaResposta(fornecedoresRes.data, ["clientes"]);
      const gruposData = extrairListaResposta(gruposRes.data, ["grupos"]);

      setFornecedores(fornecedoresData);
      setGruposFornecedores(gruposData);
      setEmailEnvioDisponivel(Boolean(envioStatusRes?.data?.email_configurado));
      // NÃO carregar produtos aqui - apenas quando fornecedor for selecionado
    } catch (error) {
      console.error("Erro ao carregar dados:", error);
      toast.error("Erro ao carregar dados");
    } finally {
      setLoadingListaPedidos(false);
    }
  };

  return {
    alterarPaginaPedidos,
    alterarPedidosPorPagina,
    atualizarFiltroPedidos,
    aplicarFiltrosPedidos,
    limparFiltrosPedidos,
    selecionarVisaoPedidos,
    carregarDados,
  };
}
