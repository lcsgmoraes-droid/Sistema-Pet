import { useEffect, useMemo, useState } from "react";
import { toast } from "react-hot-toast";
import api from "../api";

const FORM_INICIAL = {
  nome: "",
  codigo: "",
  max_parcelas: 12,
  padrao: false,
  ativo: true,
  api_enabled: false,
  api_endpoint: "",
  api_token_encrypted: "",
  cor: "#00A868",
  icone: "💳",
};

function normalizarForm(operadora) {
  if (!operadora) {
    return { ...FORM_INICIAL };
  }

  return {
    nome: operadora.nome || "",
    codigo: operadora.codigo || "",
    max_parcelas: operadora.max_parcelas || 12,
    padrao: !!operadora.padrao,
    ativo: operadora.ativo !== false,
    api_enabled: !!operadora.api_enabled,
    api_endpoint: operadora.api_endpoint || "",
    api_token_encrypted: operadora.api_token_encrypted || "",
    cor: operadora.cor || "#00A868",
    icone: operadora.icone || "💳",
  };
}

export function useOperadorasCartaoPage() {
  const [operadoras, setOperadoras] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalAberto, setModalAberto] = useState(false);
  const [operadoraSelecionada, setOperadoraSelecionada] = useState(null);
  const [erro, setErro] = useState("");
  const [mostrarToken, setMostrarToken] = useState(false);
  const [formData, setFormData] = useState(FORM_INICIAL);

  const carregarOperadoras = async () => {
    try {
      setLoading(true);
      const response = await api.get("/operadoras-cartao");
      setOperadoras(response.data);
    } catch (error) {
      console.error("Erro ao carregar operadoras:", error);
      toast.error("Erro ao carregar operadoras de cartao");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    carregarOperadoras();
  }, []);

  const operadoraPadrao = useMemo(
    () => operadoras.find((operadora) => operadora.padrao && operadora.ativo),
    [operadoras]
  );

  const abrirModal = (operadora = null) => {
    setFormData(normalizarForm(operadora));
    setOperadoraSelecionada(operadora);
    setModalAberto(true);
    setErro("");
    setMostrarToken(false);
  };

  const fecharModal = () => {
    setModalAberto(false);
    setOperadoraSelecionada(null);
    setErro("");
    setMostrarToken(false);
    setFormData({ ...FORM_INICIAL });
  };

  const salvarOperadora = async (event) => {
    event.preventDefault();

    if (!formData.nome.trim()) {
      toast.error("Nome da operadora e obrigatorio");
      return;
    }

    if (formData.max_parcelas < 1 || formData.max_parcelas > 24) {
      toast.error("Parcelas devem estar entre 1 e 24");
      return;
    }

    try {
      const dadosEnvio = {
        ...formData,
        nome: formData.nome.trim(),
        codigo: formData.codigo?.trim()?.toUpperCase() || null,
        api_endpoint: formData.api_endpoint?.trim() || null,
        api_token_encrypted: formData.api_token_encrypted?.trim() || null,
      };

      if (operadoraSelecionada) {
        await api.put(`/operadoras-cartao/${operadoraSelecionada.id}`, dadosEnvio);
        toast.success("Operadora atualizada com sucesso!");
      } else {
        await api.post("/operadoras-cartao", dadosEnvio);
        toast.success("Operadora criada com sucesso!");
      }

      fecharModal();
      await carregarOperadoras();
    } catch (error) {
      console.error("Erro ao salvar:", error);
      const mensagem = error.response?.data?.detail || "Erro ao salvar operadora";
      setErro(mensagem);
      toast.error(mensagem);
    }
  };

  const excluirOperadora = async (id) => {
    const confirmar = window.confirm(
      "Deseja realmente excluir esta operadora? Ela sera desativada se houver vendas vinculadas."
    );
    if (!confirmar) return;

    try {
      await api.delete(`/operadoras-cartao/${id}`);
      toast.success("Operadora removida com sucesso!");
      await carregarOperadoras();
    } catch (error) {
      console.error("Erro ao excluir:", error);
      const mensagem = error.response?.data?.detail || "Erro ao excluir operadora";
      toast.error(mensagem);
    }
  };

  return {
    abrirModal,
    carregarOperadoras,
    erro,
    excluirOperadora,
    fecharModal,
    formData,
    loading,
    modalAberto,
    mostrarToken,
    operadoraPadrao,
    operadoraSelecionada,
    operadoras,
    salvarOperadora,
    setErro,
    setFormData,
    setMostrarToken,
  };
}
