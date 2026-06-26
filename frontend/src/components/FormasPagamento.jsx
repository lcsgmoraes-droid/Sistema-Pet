import { useState, useEffect } from "react";
import api from "../api";
import { toast } from "react-hot-toast";
import FormasPagamentoView from "./formasPagamento/FormasPagamentoView";
import { useAuth } from "../contexts/AuthContext";
import { useModulos } from "../contexts/ModulosContext";
import { getGuiaClassNames } from "../utils/guiaHighlight";

const DEFAULT_ICON_BY_TIPO = {
  dinheiro: "\uD83D\uDCB5",
  cartao_credito: "\uD83D\uDCB3",
  cartao_debito: "\uD83D\uDCB3",
  pix: "\uD83D\uDCF1",
  boleto: "\uD83D\uDCC4",
  transferencia: "\uD83C\uDFE6",
};

const tryRepairMojibake = (value) => {
  if (typeof value !== "string" || !value) return "";
  try {
    return decodeURIComponent(escape(value));
  } catch {
    return value;
  }
};

const normalizeText = (value) => {
  const repaired = tryRepairMojibake(value).trim();
  if (!repaired) return "";
  if (repaired.includes("\uFFFD")) return "";
  const sanitized = repaired
    .replace(/\?{2,}/g, " ")
    .replace(/\s{2,}/g, " ")
    .trim();
  return sanitized
    .replace(/Cr dito/gi, "Credito")
    .replace(/D bito/gi, "Debito")
    .replace(/Transfer ncia/gi, "Transferencia")
    .replace(/Banc ria/gi, "Bancaria");
};

const normalizeFormaIcon = (rawIcon, tipo) => {
  const repaired = normalizeText(rawIcon);
  const fallback = DEFAULT_ICON_BY_TIPO[tipo] || "\uD83D\uDCB3";

  if (!repaired) return fallback;
  if (repaired.includes("?") || repaired.includes("\u00F0") || repaired.includes("\u00C3")) {
    return fallback;
  }

  return repaired;
};

const FormasPagamento = () => {
  const guiaAtiva = new URLSearchParams(window.location.search).get("guia");
  const destacarFormasPagamento = guiaAtiva === "formas-pagamento";
  const guiaClasses = getGuiaClassNames(destacarFormasPagamento);
  const { user } = useAuth();
  const { moduloAtivo, modulosAtivos } = useModulos();
  const financeiroErpAtivo =
    Boolean(user) && Array.isArray(modulosAtivos) && moduloAtivo("financeiro_erp");
  const [formas, setFormas] = useState([]);
  const [contasBancarias, setContasBancarias] = useState([]);
  const [operadoras, setOperadoras] = useState([]);
  const [loading, setLoading] = useState(true);
  const [mostrarModal, setMostrarModal] = useState(false);
  const [editando, setEditando] = useState(null);

  const [formData, setFormData] = useState({
    nome: "",
    tipo: "dinheiro",
    taxa_percentual: 0,
    taxa_fixa: 0,
    prazo_dias: 0,
    operadora: "",
    operadora_id: null,
    gera_contas_receber: false,
    split_parcelas: false,
    conta_bancaria_destino_id: null,
    requer_nsu: false,
    tipo_cartao: "",
    bandeira: "",
    ativo: true,
    permite_parcelamento: false,
    parcelas_maximas: 1,
    taxas_por_parcela: {},
    permite_antecipacao: false,
    dias_recebimento_antecipado: null,
    taxa_antecipacao_percentual: null,
    icone: DEFAULT_ICON_BY_TIPO.cartao_credito,
    cor: "#3B82F6",
  });

  useEffect(() => {
    carregarDados();
  }, [financeiroErpAtivo]);

  const carregarDados = async () => {
    try {
      const [formasRes, bancariasRes, operadorasRes] = await Promise.allSettled([
        api.get(`/financeiro/formas-pagamento?apenas_ativas=false`),
        financeiroErpAtivo
          ? api.get(`/contas-bancarias?apenas_ativas=true`)
          : Promise.resolve({ data: [] }),
        api.get(`/operadoras-cartao?apenas_ativas=true`),
      ]);

      if (formasRes.status === "fulfilled") {
        const formasNormalizadas = (formasRes.value.data || []).map((forma) => ({
          ...forma,
          nome: normalizeText(forma.nome) || forma.nome,
          operadora: normalizeText(forma.operadora) || forma.operadora,
          icone: normalizeFormaIcon(forma.icone, forma.tipo),
        }));
        setFormas(formasNormalizadas);
      }

      if (bancariasRes.status === "fulfilled") {
        setContasBancarias(bancariasRes.value.data || []);
      }

      if (operadorasRes.status === "fulfilled") {
        setOperadoras(operadorasRes.value.data || []);
      } else {
        setOperadoras([]);
        console.warn("Operadoras indisponiveis no ambiente atual. Usando lista vazia.");
      }
    } catch (error) {
      console.error("Erro ao carregar dados:", error);
      toast.error("Erro ao carregar formas de pagamento");
    } finally {
      setLoading(false);
    }
  };

  const abrirModal = (forma = null) => {
    if (forma) {
      setEditando(forma.id);

      // Parse taxas_por_parcela se for string JSON
      let taxasPorParcela = {};
      if (forma.taxas_por_parcela) {
        try {
          taxasPorParcela =
            typeof forma.taxas_por_parcela === "string"
              ? JSON.parse(forma.taxas_por_parcela)
              : forma.taxas_por_parcela;
        } catch (e) {
          console.error("Erro ao parsear taxas_por_parcela:", e);
        }
      }

      setFormData({
        nome: normalizeText(forma.nome) || forma.nome,
        tipo: forma.tipo,
        taxa_percentual: forma.taxa_percentual,
        taxa_fixa: forma.taxa_fixa,
        prazo_dias: forma.prazo_dias,
        operadora: normalizeText(forma.operadora) || forma.operadora || "",
        operadora_id: forma.operadora_id || null,
        gera_contas_receber: forma.gera_contas_receber,
        split_parcelas: forma.split_parcelas,
        conta_bancaria_destino_id: forma.conta_bancaria_destino_id,
        requer_nsu: forma.requer_nsu,
        tipo_cartao: forma.tipo_cartao || "",
        bandeira: forma.bandeira || "",
        ativo: forma.ativo,
        permite_parcelamento: forma.permite_parcelamento,
        parcelas_maximas: forma.parcelas_maximas,
        taxas_por_parcela: taxasPorParcela,
        permite_antecipacao: forma.permite_antecipacao || false,
        dias_recebimento_antecipado: forma.dias_recebimento_antecipado ?? null,
        taxa_antecipacao_percentual: forma.taxa_antecipacao_percentual ?? null,
        icone: normalizeFormaIcon(forma.icone, forma.tipo),
        cor: forma.cor || "#3B82F6",
      });
    } else {
      setEditando(null);
      setFormData({
        nome: "",
        tipo: "dinheiro",
        taxa_percentual: 0,
        taxa_fixa: 0,
        prazo_dias: 0,
        operadora: "",
        operadora_id: null,
        gera_contas_receber: false,
        split_parcelas: false,
        conta_bancaria_destino_id: null,
        requer_nsu: false,
        tipo_cartao: "",
        bandeira: "",
        ativo: true,
        permite_parcelamento: false,
        parcelas_maximas: 1,
        taxas_por_parcela: {},
        permite_antecipacao: false,
        dias_recebimento_antecipado: null,
        taxa_antecipacao_percentual: null,
        icone: DEFAULT_ICON_BY_TIPO.cartao_credito,
        cor: "#3B82F6",
      });
    }
    setMostrarModal(true);
  };

  const salvar = async () => {
    try {
      // Preparar dados para envio - converter taxas_por_parcela para JSON string
      const dadosParaEnviar = {
        ...formData,
        taxas_por_parcela:
          Object.keys(formData.taxas_por_parcela).length > 0
            ? JSON.stringify(formData.taxas_por_parcela)
            : null,
      };

      if (editando) {
        await api.put(`/financeiro/formas-pagamento/${editando}`, dadosParaEnviar);
        toast.success("Forma de pagamento atualizada!");
      } else {
        await api.post(`/financeiro/formas-pagamento`, dadosParaEnviar);
        toast.success("Forma de pagamento criada!");
      }

      setMostrarModal(false);
      carregarDados();
    } catch (error) {
      console.error("Erro ao salvar:", error);
      toast.error("Erro ao salvar forma de pagamento");
    }
  };

  const excluir = async (id) => {
    if (!confirm("Deseja realmente excluir esta forma de pagamento?")) return;

    try {
      await api.delete(`/financeiro/formas-pagamento/${id}`);
      toast.success("Forma de pagamento excluida!");
      carregarDados();
    } catch (error) {
      console.error("Erro ao excluir:", error);
      toast.error("Erro ao excluir forma de pagamento");
    }
  };

  const tiposDisponiveis = [
    { value: "dinheiro", label: "Dinheiro", icone: "\uD83D\uDCB5" },
    { value: "cartao_credito", label: "Cartao de Credito", icone: "\uD83D\uDCB3" },
    { value: "cartao_debito", label: "Cartao de Debito", icone: "\uD83D\uDCB3" },
    { value: "pix", label: "PIX", icone: "\uD83D\uDCF1" },
    { value: "boleto", label: "Boleto", icone: "\uD83D\uDCC4" },
    { value: "transferencia", label: "Transferencia", icone: "\uD83C\uDFE6" },
  ];

  return (
    <FormasPagamentoView
      abrirModal={abrirModal}
      contasBancarias={contasBancarias}
      destacarFormasPagamento={destacarFormasPagamento}
      editando={editando}
      excluir={excluir}
      financeiroErpAtivo={financeiroErpAtivo}
      formData={formData}
      formas={formas}
      guiaClasses={guiaClasses}
      loading={loading}
      mostrarModal={mostrarModal}
      operadoras={operadoras}
      salvar={salvar}
      setFormData={setFormData}
      setMostrarModal={setMostrarModal}
      tiposDisponiveis={tiposDisponiveis}
    />
  );
};

export default FormasPagamento;
