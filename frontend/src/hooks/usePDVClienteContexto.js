import { useEffect, useMemo, useState } from "react";
import api from "../api";
import { useModulos } from "../contexts/ModulosContext";
import { copyTextToClipboard } from "../utils/clipboard";
import { incluirPetNoClienteSelecionado } from "../utils/pdvClientePets";
import { criarAtualizadorSaldoCampanhas } from "../utils/pdvCampanhasRefresh";

export function usePDVClienteContexto({ vendaAtual, setVendaAtual }) {
  const { moduloAtivo } = useModulos();
  const moduloCampanhasAtivo = moduloAtivo("campanhas");
  const [copiadoClienteCampo, setCopiadoClienteCampo] = useState("");
  const [vendasEmAbertoInfo, setVendasEmAbertoInfo] = useState(null);
  const [saldoCampanhas, setSaldoCampanhas] = useState(null);
  const atualizadorCampanhas = useMemo(
    () =>
      criarAtualizadorSaldoCampanhas({
        buscarSaldo: async (clienteId, options) => {
          const response = await api.get(`/campanhas/clientes/${clienteId}/saldo`, options);
          return response.data;
        },
        onSaldo: setSaldoCampanhas,
        onInicio: (clienteId) =>
          setSaldoCampanhas((prev) => ({
            ...(String(prev?.customer_id) === String(clienteId) ? prev : {}),
            customer_id: clienteId,
            beneficios_atualizando: true,
            beneficios_erro_atualizacao: false,
            beneficios_consulta_limite: false,
          })),
        onErro: () =>
          setSaldoCampanhas((prev) => ({
            ...prev,
            beneficios_atualizando: false,
            beneficios_erro_atualizacao: true,
          })),
      }),
    [],
  );

  const carregarVendasEmAbertoCliente = async (clienteId) => {
    if (!clienteId) {
      setVendasEmAbertoInfo(null);
      return;
    }

    try {
      const response = await api.get(`/clientes/${clienteId}/vendas-em-aberto`);
      const resumo = response.data?.resumo;
      if (resumo?.total_vendas > 0 || resumo?.total_parcelas_crediario > 0) {
        setVendasEmAbertoInfo(resumo);
      } else {
        setVendasEmAbertoInfo(null);
      }
    } catch (error) {
      console.error("Erro ao verificar vendas em aberto:", error);
      setVendasEmAbertoInfo(null);
    }
  };

  const carregarSaldoCampanhasCliente = async (clienteId) => {
    if (!moduloCampanhasAtivo) {
      atualizadorCampanhas.cancelar();
      setSaldoCampanhas(null);
      return;
    }

    if (!clienteId) {
      atualizadorCampanhas.cancelar();
      setSaldoCampanhas(null);
      return;
    }

    await atualizadorCampanhas.atualizar(clienteId);
  };

  const limparClienteSelecionado = () => {
    atualizadorCampanhas.cancelar();
    setVendaAtual((prev) => ({
      ...prev,
      cliente: null,
      pet: null,
      itens: (prev.itens || []).map((item) => ({
        ...item,
        racao_data_prevista_fim: null,
        racao_prazo_estimado_dias: null,
      })),
    }));
    setSaldoCampanhas(null);
    setVendasEmAbertoInfo(null);
  };

  const selecionarPet = (pet) => {
    setVendaAtual((prev) => ({
      ...prev,
      cliente: pet ? incluirPetNoClienteSelecionado(prev.cliente, pet) : prev.cliente,
      pet,
    }));
  };

  const copiarCampoCliente = async (valor, campo) => {
    if (!valor) return;
    try {
      await copyTextToClipboard(valor);
      setCopiadoClienteCampo(campo);
      setTimeout(() => setCopiadoClienteCampo(""), 2000);
    } catch (error) {
      console.error("Erro ao copiar campo do cliente:", error);
    }
  };

  const recarregarVendasEmAbertoClienteAtual = async () => {
    await carregarVendasEmAbertoCliente(vendaAtual.cliente?.id);
  };

  const recarregarSaldoCampanhasClienteAtual = async () => {
    await carregarSaldoCampanhasCliente(vendaAtual.cliente?.id);
  };

  const recarregarContextoClientePorId = async (clienteId) => {
    if (!clienteId) {
      atualizadorCampanhas.cancelar();
      setSaldoCampanhas(null);
      setVendasEmAbertoInfo(null);
      return;
    }
    if (!moduloCampanhasAtivo) {
      setSaldoCampanhas(null);
    }
    await Promise.all([
      carregarVendasEmAbertoCliente(clienteId),
      moduloCampanhasAtivo ? carregarSaldoCampanhasCliente(clienteId) : Promise.resolve(),
    ]);
  };

  const recarregarContextoClienteAtual = async () => {
    await recarregarContextoClientePorId(vendaAtual.cliente?.id);
  };

  useEffect(() => {
    atualizadorCampanhas.cancelar();
    const clienteId = vendaAtual.cliente?.id;
    if (!clienteId) {
      setSaldoCampanhas(null);
      setVendasEmAbertoInfo(null);
      return () => atualizadorCampanhas.cancelar();
    }

    void recarregarContextoClientePorId(clienteId);
    return () => atualizadorCampanhas.cancelar();
  }, [moduloCampanhasAtivo, vendaAtual.cliente?.id]);

  return {
    copiadoClienteCampo,
    vendasEmAbertoInfo,
    saldoCampanhas,
    setSaldoCampanhas,
    carregarVendasEmAbertoCliente,
    carregarSaldoCampanhasCliente,
    limparClienteSelecionado,
    selecionarPet,
    copiarCampoCliente,
    recarregarVendasEmAbertoClienteAtual,
    recarregarSaldoCampanhasClienteAtual,
    recarregarContextoClientePorId,
    recarregarContextoClienteAtual,
  };
}
