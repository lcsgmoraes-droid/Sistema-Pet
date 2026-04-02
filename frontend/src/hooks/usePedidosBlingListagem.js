import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import api from '../api';
import { PEDIDOS_BLING_ABAS } from '../components/pedidosBling/pedidoBlingUtils';

export default function usePedidosBlingListagem() {
  const [searchParams] = useSearchParams();
  const [pedidos, setPedidos] = useState([]);
  const [total, setTotal] = useState(0);
  const [paginas, setPaginas] = useState(1);
  const [pagina, setPagina] = useState(1);
  const [statusFiltro, setStatusFiltro] = useState('');
  const [carregando, setCarregando] = useState(false);
  const buscaPedido = useMemo(() => (searchParams.get('pedido') || '').trim(), [searchParams]);

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      const params = { pagina, por_pagina: 20 };
      if (statusFiltro) params.status = statusFiltro;
      if (buscaPedido) params.busca = buscaPedido;
      const res = await api.get('/integracoes/bling/pedidos', { params });
      setPedidos(res.data.pedidos || []);
      setTotal(res.data.total || 0);
      setPaginas(res.data.paginas || 1);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Erro ao carregar pedidos');
    } finally {
      setCarregando(false);
    }
  }, [pagina, statusFiltro, buscaPedido]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  useEffect(() => {
    setPagina(1);
  }, [buscaPedido]);

  function mudarStatus(novoStatus) {
    setStatusFiltro(novoStatus);
    setPagina(1);
  }

  async function consolidarDuplicidade(pedido) {
    try {
      const response = await api.post(`/integracoes/bling/pedidos/${pedido.id}/consolidar-duplicidade`);
      const totalMesclados = response.data?.pedidos_mesclados?.length || 0;
      toast.success(`Duplicidade consolidada. ${totalMesclados} pedido(s) incorporado(s).`);
      await carregar();
    } catch (e) {
      const detail =
        typeof e.response?.data?.detail === 'string'
          ? e.response.data.detail
          : e.response?.data?.detail?.motivo || 'Erro ao consolidar duplicidade';
      toast.error(detail);
    }
  }

  async function reconciliarFluxo(pedido) {
    try {
      const response = await api.post(`/integracoes/bling/pedidos/${pedido.id}/reconciliar-fluxo`);
      toast.success(
        response.data?.nf_numero
          ? `Fluxo reconciliado com a NF ${response.data.nf_numero}.`
          : 'Fluxo reconciliado com sucesso.'
      );
      await carregar();
    } catch (e) {
      const detail =
        typeof e.response?.data?.detail === 'string'
          ? e.response.data.detail
          : e.response?.data?.detail?.motivo || 'Erro ao reconciliar fluxo do pedido';
      toast.error(detail);
    }
  }

  return {
    abas: PEDIDOS_BLING_ABAS,
    buscaPedido,
    carregando,
    carregar,
    consolidarDuplicidade,
    mudarStatus,
    pagina,
    paginas,
    pedidos,
    reconciliarFluxo,
    setPagina,
    statusFiltro,
    total,
  };
}
