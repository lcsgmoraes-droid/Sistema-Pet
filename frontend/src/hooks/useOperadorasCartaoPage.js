import { useEffect, useMemo, useState } from "react";
import { toast } from "react-hot-toast";
import api from "../api";
import { confirmarCorePet } from "../services/corepetDialog";

const FORM_INICIAL = {
  nome: "",
  codigo: "",
  max_parcelas: 12,
  padrao: false,
  ativo: true,
  bandeira_padrao: null,
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
    bandeira_padrao: operadora.bandeira_padrao || null,
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
  const [taxas, setTaxas] = useState([]);
  const [taxasLoading, setTaxasLoading] = useState(false);

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
    [operadoras],
  );

  const abrirModal = async (operadora = null) => {
    setFormData(normalizarForm(operadora));
    setOperadoraSelecionada(operadora);
    setTaxas([]);
    setModalAberto(true);
    setErro("");
    setMostrarToken(false);

    if (!operadora) return;

    try {
      setTaxasLoading(true);
      const response = await api.get(`/operadoras-cartao/${operadora.id}/taxas`, {
        params: { apenas_ativas: true },
      });
      setTaxas(response.data || []);
    } catch (error) {
      console.error("Erro ao carregar taxas da operadora:", error);
      const mensagem = error.response?.data?.detail || "Erro ao carregar tabela de taxas";
      setErro(mensagem);
      toast.error(mensagem);
    } finally {
      setTaxasLoading(false);
    }
  };

  const fecharModal = () => {
    setModalAberto(false);
    setOperadoraSelecionada(null);
    setErro("");
    setMostrarToken(false);
    setFormData({ ...FORM_INICIAL });
    setTaxas([]);
    setTaxasLoading(false);
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

    const taxaForaDoLimite = taxas.some(
      (taxa) => taxa.modalidade !== "debito" && Number(taxa.parcelas) > formData.max_parcelas,
    );
    if (taxaForaDoLimite) {
      toast.error("Remova as taxas acima do novo limite de parcelas antes de salvar");
      return;
    }

    const temTaxaLegada = [
      operadoraSelecionada?.taxa_debito,
      operadoraSelecionada?.taxa_credito_vista,
      operadoraSelecionada?.taxa_credito_parcelado,
    ].some((taxa) => taxa != null);
    if (formData.ativo && !taxas.length && !temTaxaLegada) {
      toast.error("Cadastre ao menos uma taxa antes de ativar a operadora");
      return;
    }

    if (
      formData.bandeira_padrao &&
      !taxas.some((taxa) => taxa.bandeira === formData.bandeira_padrao)
    ) {
      toast.error("A bandeira padrao precisa ter ao menos uma taxa configurada");
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

      let operadoraSalva;
      if (operadoraSelecionada) {
        const response = await api.put(`/operadoras-cartao/${operadoraSelecionada.id}`, dadosEnvio);
        operadoraSalva = response.data;
      } else {
        const response = await api.post("/operadoras-cartao", dadosEnvio);
        operadoraSalva = response.data;
        setOperadoraSelecionada(operadoraSalva);
      }

      await api.put(`/operadoras-cartao/${operadoraSalva.id}/taxas`, {
        taxas: taxas.map((taxa) => ({
          bandeira: taxa.bandeira,
          modalidade: taxa.modalidade,
          parcelas: Number(taxa.parcelas),
          taxa_percentual: Number(taxa.taxa_percentual || 0),
          taxa_fixa: Number(taxa.taxa_fixa || 0),
          prazo_recebimento_dias: Number(taxa.prazo_recebimento_dias || 0),
        })),
      });

      toast.success(
        operadoraSelecionada
          ? "Operadora atualizada com sucesso!"
          : "Operadora e taxas criadas com sucesso!",
      );

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
    const confirmar = await confirmarCorePet(
      "Deseja realmente excluir esta operadora? Ela sera desativada se houver vendas vinculadas.",
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
    setTaxas,
    taxas,
    taxasLoading,
  };
}
