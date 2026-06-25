import { toast } from "react-hot-toast";
import api from "../../api";

export function createPedidosCompraDataController({
  filtrosPedidos,
  filtrosPedidosInicial,
  setEmailEnvioDisponivel,
  setFiltrosPedidos,
  setFornecedores,
  setGruposFornecedores,
  setLoadingListaPedidos,
  setPedidos,
}) {
  const montarParametrosPedidos = (filtros = filtrosPedidosInicial) => {
    const params = { limit: 100 };
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

  const atualizarFiltroPedidos = (campo, valor) => {
    setFiltrosPedidos((prev) => ({ ...prev, [campo]: valor }));
  };

  const aplicarFiltrosPedidos = (event) => {
    event?.preventDefault();
    carregarDados(filtrosPedidos, { apenasPedidos: true });
  };

  const limparFiltrosPedidos = () => {
    setFiltrosPedidos(filtrosPedidosInicial);
    carregarDados(filtrosPedidosInicial, { apenasPedidos: true });
  };

  const selecionarFiltroStatus = (statusPedido) => {
    const proximosFiltros = { ...filtrosPedidos, status: statusPedido };
    setFiltrosPedidos(proximosFiltros);
    carregarDados(proximosFiltros, { apenasPedidos: true });
  };

  const carregarDados = async (filtrosParaAplicar = filtrosPedidos, opcoes = {}) => {
    const params = montarParametrosPedidos(filtrosParaAplicar);
    setLoadingListaPedidos(true);
    try {
      if (opcoes.apenasPedidos) {
        const pedidosRes = await api.get("/pedidos-compra/", { params });
        setPedidos(extrairListaResposta(pedidosRes.data, ["pedidos"]));
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
      const pedidosData = extrairListaResposta(pedidosRes.data, ["pedidos"]);

      // Tratar resposta dos fornecedores
      const fornecedoresData = extrairListaResposta(fornecedoresRes.data, ["clientes"]);
      const gruposData = extrairListaResposta(gruposRes.data, ["grupos"]);

      setPedidos(pedidosData);
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
    atualizarFiltroPedidos,
    aplicarFiltrosPedidos,
    limparFiltrosPedidos,
    selecionarFiltroStatus,
    carregarDados,
  };
}
