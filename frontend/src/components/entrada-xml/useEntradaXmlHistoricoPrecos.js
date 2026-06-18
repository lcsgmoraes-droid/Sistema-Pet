import { useState } from "react";

export default function useEntradaXmlHistoricoPrecos({ api, toast }) {
  const [mostrarHistoricoPrecos, setMostrarHistoricoPrecos] = useState(false);
  const [historicoPrecos, setHistoricoPrecos] = useState([]);
  const [produtoHistorico, setProdutoHistorico] = useState(null);
  const [carregandoHistorico, setCarregandoHistorico] = useState(false);

  const buscarHistoricoPrecos = async (produtoId, produtoNome) => {
    setCarregandoHistorico(true);
    setProdutoHistorico({ id: produtoId, nome: produtoNome });
    setMostrarHistoricoPrecos(true);

    try {
      const response = await api.get(`/produtos/${produtoId}/historico-precos`);
      setHistoricoPrecos(response.data);
    } catch {
      toast.error("Erro ao carregar historico de precos");
      setMostrarHistoricoPrecos(false);
    } finally {
      setCarregandoHistorico(false);
    }
  };

  const fecharHistoricoPrecos = () => {
    setMostrarHistoricoPrecos(false);
    setHistoricoPrecos([]);
    setProdutoHistorico(null);
  };

  return {
    buscarHistoricoPrecos,
    carregandoHistorico,
    fecharHistoricoPrecos,
    historicoPrecos,
    mostrarHistoricoPrecos,
    produtoHistorico,
  };
}
