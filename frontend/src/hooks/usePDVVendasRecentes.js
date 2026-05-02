import { useEffect, useRef, useState } from "react";
import api from "../api";
import { listarVendas } from "../api/vendas";
import { debugLog } from "../utils/debug";

export function usePDVVendasRecentes() {
  const [vendasRecentes, setVendasRecentes] = useState([]);
  const [filtroVendas, setFiltroVendas] = useState("24h");
  const [filtroStatus, setFiltroStatus] = useState("todas");
  const [confirmandoRetirada, setConfirmandoRetirada] = useState({
    vendaId: null,
    nome: "",
  });
  const [filtroTemEntrega, setFiltroTemEntrega] = useState(false);
  const [buscaNumeroVenda, setBuscaNumeroVenda] = useState("");
  const [driveAguardando, setDriveAguardando] = useState([]);
  const [driveAlertVisible, setDriveAlertVisible] = useState(false);
  const vendasPollingRef = useRef(false);
  const drivePollingRef = useRef(false);

  const carregarVendasRecentes = async ({ force = false } = {}) => {
    if (vendasPollingRef.current) return;
    if (!force && document.visibilityState === "hidden") return;

    vendasPollingRef.current = true;
    try {
      const hoje = new Date();
      let dataInicio;

      if (filtroVendas === "24h") {
        dataInicio = new Date(hoje.getTime() - 24 * 60 * 60 * 1000);
      } else if (filtroVendas === "7d") {
        dataInicio = new Date(hoje.getTime() - 7 * 24 * 60 * 60 * 1000);
      } else {
        dataInicio = new Date(hoje.getTime() - 30 * 24 * 60 * 60 * 1000);
      }

      const params = {
        data_inicio: dataInicio.toISOString().split("T")[0],
        data_fim: hoje.toISOString().split("T")[0],
        per_page: 50,
      };

      if (buscaNumeroVenda.trim()) {
        params.busca = buscaNumeroVenda.trim();
        delete params.data_inicio;
        delete params.data_fim;
      } else {
        if (filtroStatus === "pago") {
          params.status = "finalizada";
        } else if (filtroStatus === "aberta") {
          params.status = "aberta";
        }

        if (filtroTemEntrega === true) {
          params.tem_entrega = true;
        }
      }

      debugLog("📊 Parâmetros de busca de vendas:", params);
      const resultado = await listarVendas(params);
      setVendasRecentes(resultado.vendas || []);
    } catch (error) {
      console.error("Erro ao carregar vendas:", error);
    } finally {
      vendasPollingRef.current = false;
    }
  };

  const confirmarDriveEntregue = async (pedidoId) => {
    try {
      await api.post(`/ecommerce-drive/pedido/${pedidoId}/entregue`);
      const proximosPedidos = driveAguardando.filter(
        (pedido) => pedido.pedido_id !== pedidoId,
      );
      setDriveAguardando(proximosPedidos);
      setDriveAlertVisible(proximosPedidos.length > 0);
    } catch (error) {
      console.error("Erro ao confirmar drive entregue:", error);
    }
  };

  const abrirConfirmacaoRetirada = (event, vendaId) => {
    event.stopPropagation();
    setConfirmandoRetirada({ vendaId, nome: "" });
  };

  const confirmarRetirada = async (event, vendaId) => {
    event.stopPropagation();
    try {
      await api.post(`/vendas/${vendaId}/marcar-entregue`, {
        retirado_por: confirmandoRetirada.nome.trim() || null,
      });
      setConfirmandoRetirada({ vendaId: null, nome: "" });
      await carregarVendasRecentes({ force: true });
    } catch (error) {
      console.error("Erro ao confirmar retirada:", error);
    }
  };

  const fecharDriveAlert = () => {
    setDriveAlertVisible(false);
  };

  useEffect(() => {
    void carregarVendasRecentes({ force: true });

    const intervalo = setInterval(() => {
      void carregarVendasRecentes();
    }, 60000);

    return () => clearInterval(intervalo);
  }, [filtroVendas, filtroStatus, filtroTemEntrega, buscaNumeroVenda]);

  useEffect(() => {
    const verificarDrive = async ({ force = false } = {}) => {
      if (drivePollingRef.current) return;
      if (!force && document.visibilityState === "hidden") return;

      drivePollingRef.current = true;
      try {
        const response = await api.get("/ecommerce-drive/aguardando");
        const lista = response.data?.pedidos || [];
        setDriveAguardando(lista);
        setDriveAlertVisible(lista.length > 0);
      } catch {
        // Nao interrompe o PDV se o polling do drive falhar.
      } finally {
        drivePollingRef.current = false;
      }
    };

    void verificarDrive({ force: true });
    const intervalo = setInterval(() => {
      void verificarDrive();
    }, 60000);

    return () => clearInterval(intervalo);
  }, []);

  return {
    vendasRecentes,
    filtroVendas,
    setFiltroVendas,
    filtroStatus,
    setFiltroStatus,
    confirmandoRetirada,
    setConfirmandoRetirada,
    filtroTemEntrega,
    setFiltroTemEntrega,
    buscaNumeroVenda,
    setBuscaNumeroVenda,
    driveAguardando,
    driveAlertVisible,
    carregarVendasRecentes,
    confirmarDriveEntregue,
    abrirConfirmacaoRetirada,
    confirmarRetirada,
    fecharDriveAlert,
  };
}
