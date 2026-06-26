import { useEffect, useState } from "react";
import api from "../../api";
import { getGuiaClassNames } from "../../utils/guiaHighlight";

export function useComissoesPageController() {
  const guiaAtiva = new URLSearchParams(window.location.search).get("guia");
  const destacarComissoes = guiaAtiva === "comissao-func" || guiaAtiva === "comissao-regras";
  const guiaClasses = getGuiaClassNames(destacarComissoes);
  const [funcionarios, setFuncionarios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [funcionarioSelecionado, setFuncionarioSelecionado] = useState(null);
  const [configuracoes, setConfiguracoes] = useState([]);
  const [arvoreProdutos, setArvoreProdutos] = useState([]);
  const [loadingArvore, setLoadingArvore] = useState(false);
  const [error, setError] = useState(null);

  const carregarFuncionarios = async () => {
    try {
      setLoading(true);
      const response = await api.get("/comissoes/configuracoes/funcionarios");
      if (response.data.success) {
        setFuncionarios(response.data.data);
      }
    } catch (err) {
      console.error("Erro ao carregar parceiros:", err);
      setError("Erro ao carregar parceiros com comissões");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    carregarFuncionarios();
  }, []);

  const abrirModal = async (funcionarioId = null) => {
    setFuncionarioSelecionado(funcionarioId);
    setShowModal(true);
    setLoadingArvore(true);

    try {
      const arvoreResponse = await api.get("/comissoes/arvore-produtos");
      if (arvoreResponse.data.success) {
        setArvoreProdutos(arvoreResponse.data.data);
      }

      if (funcionarioId) {
        const configResponse = await api.get(
          `/comissoes/configuracoes/funcionario/${funcionarioId}`,
        );
        if (configResponse.data.success) {
          setConfiguracoes(configResponse.data.data);
        }
      }
    } catch (err) {
      console.error("Erro ao carregar dados:", err);
      setError("Erro ao carregar dados de configuração");
    } finally {
      setLoadingArvore(false);
    }
  };

  const fecharModal = () => {
    setShowModal(false);
    setFuncionarioSelecionado(null);
    setConfiguracoes([]);
    setArvoreProdutos([]);
    carregarFuncionarios();
  };

  const salvarModal = () => {
    carregarFuncionarios();
    fecharModal();
  };

  const duplicarConfiguracao = async (funcionarioOrigemId) => {
    const funcionarioDestinoId = prompt("Digite o ID do parceiro de destino:");
    if (!funcionarioDestinoId) return;

    try {
      const response = await api.post("/comissoes/configuracoes/duplicar", {
        funcionario_origem_id: parseInt(funcionarioOrigemId, 10),
        funcionario_destino_id: parseInt(funcionarioDestinoId, 10),
      });

      if (response.data.success) {
        alert(response.data.message);
        carregarFuncionarios();
      }
    } catch (err) {
      console.error("Erro ao duplicar configuração:", err);
      alert("Erro ao duplicar configuração");
    }
  };

  return {
    arvoreProdutos,
    abrirModal,
    configuracoes,
    destacarComissoes,
    duplicarConfiguracao,
    error,
    fecharModal,
    funcionarioSelecionado,
    funcionarios,
    guiaClasses,
    loading,
    loadingArvore,
    salvarModal,
    showModal,
  };
}
