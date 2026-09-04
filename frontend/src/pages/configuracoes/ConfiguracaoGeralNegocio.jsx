import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import toast from "react-hot-toast";
import { FiChevronLeft, FiCreditCard, FiSave, FiSliders, FiUsers } from "react-icons/fi";
import api from "../../api";
import {
  getGuiaAtiva,
  getGuiaClassNames,
  getGuiaHighlightIntensity,
  setGuiaHighlightIntensity,
} from "../../utils/guiaHighlight";

const DEFAULT_FORM = {
  margem_saudavel_minima: 30,
  margem_alerta_minima: 15,
  mensagem_venda_saudavel: "✅ Venda Saudavel! Margem excelente.",
  mensagem_venda_alerta: "⚠️ ATENCAO: Margem reduzida! Revisar preco.",
  mensagem_venda_critica: "🚨 CRITICO: Margem muito baixa! Venda com prejuizo!",
  aliquota_imposto_padrao: 7,
  caixa_compartilhado: false,
  dias_tolerancia_atraso: 5,
  crediario_encargos_automaticos: false,
  crediario_multa_percentual: 2,
  crediario_juros_mensal_percentual: 1,
  meta_faturamento_mensal: 0,
  alerta_estoque_percentual: 20,
  dias_produto_parado: 90,
};

const GUIA_MAP = {
  "empresa-margens-pdv": ["margem_saudavel_minima", "margem_alerta_minima"],
  "empresa-mensagens-pdv": [
    "mensagem_venda_saudavel",
    "mensagem_venda_alerta",
    "mensagem_venda_critica",
  ],
  "empresa-meta-faturamento": ["meta_faturamento_mensal"],
  "empresa-alertas-estoque": ["alerta_estoque_percentual", "dias_produto_parado"],
};

export default function ConfiguracaoGeralNegocio() {
  const location = useLocation();
  const [loading, setLoading] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [guiaAtiva, setGuiaAtiva] = useState("");
  const [intensidade, setIntensidade] = useState(getGuiaHighlightIntensity());
  const [form, setForm] = useState(DEFAULT_FORM);

  useEffect(() => {
    setGuiaAtiva(getGuiaAtiva(location.search));
  }, [location.search]);

  useEffect(() => {
    async function carregar() {
      try {
        const res = await api.get("/empresa/config/");
        const data = res.data || {};

        setForm({
          ...DEFAULT_FORM,
          ...data,
          margem_saudavel_minima: Number(data.margem_saudavel_minima ?? 30),
          margem_alerta_minima: Number(data.margem_alerta_minima ?? 15),
          aliquota_imposto_padrao: Number(data.aliquota_imposto_padrao ?? 7),
          caixa_compartilhado: Boolean(data.caixa_compartilhado),
          dias_tolerancia_atraso: Number(data.dias_tolerancia_atraso ?? 5),
          crediario_encargos_automaticos: Boolean(data.crediario_encargos_automaticos),
          crediario_multa_percentual: Number(data.crediario_multa_percentual ?? 2),
          crediario_juros_mensal_percentual: Number(data.crediario_juros_mensal_percentual ?? 1),
          meta_faturamento_mensal: Number(data.meta_faturamento_mensal ?? 0),
          alerta_estoque_percentual: Number(data.alerta_estoque_percentual ?? 20),
          dias_produto_parado: Number(data.dias_produto_parado ?? 90),
        });
      } catch (error) {
        console.error("Erro ao carregar configuração geral:", error);
        const detalhe = error?.response?.data?.detail;
        toast.error(detalhe || "Erro ao carregar configuracoes gerais");
      } finally {
        setLoading(false);
      }
    }

    carregar();
  }, []);

  const isCampoGuia = (campo) => GUIA_MAP[guiaAtiva]?.includes(campo);

  const campoClass = (campo) => {
    const guiaClasses = getGuiaClassNames(isCampoGuia(campo));
    return `w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${guiaClasses.input}`;
  };

  const blocoClass = (campos = []) => {
    const ativo = campos.some((campo) => isCampoGuia(campo));
    const guiaClasses = getGuiaClassNames(ativo);
    return `bg-white rounded-lg shadow-md p-6 ${guiaClasses.box}`;
  };

  const onChange = (name, value, numeric = false) => {
    setForm((prev) => ({
      ...prev,
      [name]: numeric ? Number(value) : value,
    }));
  };

  const salvar = async () => {
    if (form.margem_alerta_minima < 0 || form.margem_saudavel_minima < 0) {
      toast.error("Margens nao podem ser negativas");
      return;
    }

    if (form.margem_alerta_minima >= form.margem_saudavel_minima) {
      toast.error("A margem amarela deve ser menor que a margem verde");
      return;
    }

    if (form.crediario_multa_percentual < 0 || form.crediario_multa_percentual > 2) {
      toast.error("A multa do crediario deve ficar entre 0% e 2%");
      return;
    }

    if (form.crediario_juros_mensal_percentual < 0) {
      toast.error("Os juros do crediario nao podem ser negativos");
      return;
    }

    setSalvando(true);
    try {
      await api.put("/empresa/config/", {
        margem_saudavel_minima: Number(form.margem_saudavel_minima),
        margem_alerta_minima: Number(form.margem_alerta_minima),
        mensagem_venda_saudavel: form.mensagem_venda_saudavel,
        mensagem_venda_alerta: form.mensagem_venda_alerta,
        mensagem_venda_critica: form.mensagem_venda_critica,
        aliquota_imposto_padrao: Number(form.aliquota_imposto_padrao),
        caixa_compartilhado: Boolean(form.caixa_compartilhado),
        dias_tolerancia_atraso: Number(form.dias_tolerancia_atraso),
        crediario_encargos_automaticos: Boolean(form.crediario_encargos_automaticos),
        crediario_multa_percentual: Number(form.crediario_multa_percentual),
        crediario_juros_mensal_percentual: Number(form.crediario_juros_mensal_percentual),
        meta_faturamento_mensal: Number(form.meta_faturamento_mensal),
        alerta_estoque_percentual: Number(form.alerta_estoque_percentual),
        dias_produto_parado: Number(form.dias_produto_parado),
      });
      toast.success("Configuracoes gerais salvas com sucesso");
    } catch (error) {
      console.error("Erro ao salvar configuração geral:", error);
      const detalhe = error?.response?.data?.detail;
      toast.error(detalhe || "Erro ao salvar configuracoes gerais");
    } finally {
      setSalvando(false);
    }
  };

  const atualizarIntensidade = (value) => {
    setIntensidade(value);
    setGuiaHighlightIntensity(value);
    globalThis.dispatchEvent(new Event("guia-highlight-updated"));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto" />
          <p className="mt-4 text-gray-600">Carregando configuracoes gerais...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div>
        <Link
          to="/configuracoes"
          className="inline-flex items-center text-blue-600 hover:text-blue-700 mb-4"
        >
          <FiChevronLeft className="mr-1" />
          Voltar para Configuracoes
        </Link>
        <h1 className="text-3xl font-bold text-gray-900">Configuracoes Gerais do Negocio</h1>
        <p className="text-gray-600 mt-2">
          Defina margens do PDV, mensagens de alerta e metas operacionais.
        </p>
      </div>

      {guiaAtiva && (
        <div className="rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-amber-900 text-sm">
          Etapa da introducao guiada ativa. Os campos importantes desta etapa estao destacados.
        </div>
      )}

      <div className="rounded-lg bg-white p-6 shadow-md">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-3xl">
            <h2 className="flex items-center gap-2 text-xl font-semibold text-gray-800">
              <FiUsers /> Caixa compartilhado
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-gray-600">
              Quando ativado, a empresa trabalha com um unico caixa aberto. O primeiro usuario abre
              o caixa e os demais passam a usa-lo automaticamente ao entrar no PDV.
            </p>
          </div>
          <label className="inline-flex cursor-pointer items-center gap-3 rounded-lg border border-gray-200 px-4 py-3">
            <input
              type="checkbox"
              checked={form.caixa_compartilhado}
              onChange={(e) => onChange("caixa_compartilhado", e.target.checked)}
              className="h-4 w-4"
            />
            <span className="text-sm font-semibold text-gray-800">Compartilhar entre usuarios</span>
          </label>
        </div>
        <p className="mt-4 rounded-lg bg-blue-50 px-4 py-3 text-sm text-blue-800">
          Cada venda, suprimento, sangria, despesa e devolucao continua registrando qual usuario
          realizou a operacao. Qualquer usuario com acesso ao caixa podera fecha-lo.
        </p>
      </div>

      <div className="bg-white rounded-lg shadow-md p-4">
        <div className="flex items-center gap-2 mb-2 text-gray-800 font-semibold">
          <FiSliders />
          Intensidade do destaque da guia
        </div>
        <div className="flex gap-3">
          {[
            { id: "suave", label: "Suave" },
            { id: "media", label: "Media" },
            { id: "forte", label: "Forte" },
          ].map((opcao) => (
            <label key={opcao.id} className="inline-flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="intensidade-guia"
                checked={intensidade === opcao.id}
                onChange={() => atualizarIntensidade(opcao.id)}
              />
              <span>{opcao.label}</span>
            </label>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="flex items-center gap-2 text-xl font-semibold text-gray-800">
              <FiCreditCard /> Crediario e atraso
            </h2>
            <p className="mt-1 text-sm text-gray-600">
              A multa e cobrada uma vez. Os juros mensais sao calculados proporcionalmente por dia.
            </p>
          </div>
          <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-gray-200 px-3 py-2">
            <input
              type="checkbox"
              checked={form.crediario_encargos_automaticos}
              onChange={(e) => onChange("crediario_encargos_automaticos", e.target.checked)}
              className="h-4 w-4"
            />
            <span className="text-sm font-semibold text-gray-800">Cobrar automaticamente</span>
          </label>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <div>
            <label
              htmlFor="dias-tolerancia-atraso"
              className="mb-1 block text-sm font-medium text-gray-700"
            >
              Tolerancia apos o vencimento (dias)
            </label>
            <input
              id="dias-tolerancia-atraso"
              type="number"
              min="0"
              value={form.dias_tolerancia_atraso}
              onChange={(e) => onChange("dias_tolerancia_atraso", e.target.value, true)}
              className={campoClass("dias_tolerancia_atraso")}
            />
          </div>
          <div>
            <label
              htmlFor="crediario-multa"
              className="mb-1 block text-sm font-medium text-gray-700"
            >
              Multa unica (%)
            </label>
            <input
              id="crediario-multa"
              type="number"
              min="0"
              max="2"
              step="0.01"
              value={form.crediario_multa_percentual}
              onChange={(e) => onChange("crediario_multa_percentual", e.target.value, true)}
              className={campoClass("crediario_multa_percentual")}
            />
          </div>
          <div>
            <label
              htmlFor="crediario-juros"
              className="mb-1 block text-sm font-medium text-gray-700"
            >
              Juros ao mes (%)
            </label>
            <input
              id="crediario-juros"
              type="number"
              min="0"
              step="0.01"
              value={form.crediario_juros_mensal_percentual}
              onChange={(e) => onChange("crediario_juros_mensal_percentual", e.target.value, true)}
              className={campoClass("crediario_juros_mensal_percentual")}
            />
          </div>
        </div>
        <p className="mt-4 text-xs leading-relaxed text-gray-500">
          Informe estas condicoes ao cliente na venda a prazo. A multa de mora fica limitada a 2% no
          sistema.
        </p>
      </div>

      <div className={blocoClass(["margem_saudavel_minima", "margem_alerta_minima"])}>
        <h2 className="text-xl font-semibold text-gray-800 mb-4">Analise de Margem do PDV</h2>
        <p className="text-sm text-gray-600 mb-4">
          Verde: margem igual ou acima de "Margem Saudavel". Amarelo: entre "Margem Alerta" e
          "Margem Saudavel". Vermelho: abaixo de "Margem Alerta".
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label
              htmlFor="margem-saudavel-minima"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Margem Saudavel (verde) %
            </label>
            <input
              id="margem-saudavel-minima"
              type="number"
              min="0"
              max="100"
              step="0.01"
              value={form.margem_saudavel_minima}
              onChange={(e) => onChange("margem_saudavel_minima", e.target.value, true)}
              className={campoClass("margem_saudavel_minima")}
            />
          </div>
          <div>
            <label
              htmlFor="margem-alerta-minima"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Margem Alerta (amarelo) %
            </label>
            <input
              id="margem-alerta-minima"
              type="number"
              min="0"
              max="100"
              step="0.01"
              value={form.margem_alerta_minima}
              onChange={(e) => onChange("margem_alerta_minima", e.target.value, true)}
              className={campoClass("margem_alerta_minima")}
            />
          </div>
        </div>
      </div>

      <div
        className={blocoClass([
          "mensagem_venda_saudavel",
          "mensagem_venda_alerta",
          "mensagem_venda_critica",
        ])}
      >
        <h2 className="text-xl font-semibold text-gray-800 mb-4">Mensagens da Analise do PDV</h2>
        <div className="space-y-4">
          <div>
            <label
              htmlFor="mensagem-venda-saudavel"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Mensagem da venda verde
            </label>
            <input
              id="mensagem-venda-saudavel"
              type="text"
              value={form.mensagem_venda_saudavel}
              onChange={(e) => onChange("mensagem_venda_saudavel", e.target.value)}
              className={campoClass("mensagem_venda_saudavel")}
            />
          </div>
          <div>
            <label
              htmlFor="mensagem-venda-alerta"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Mensagem da venda amarela
            </label>
            <input
              id="mensagem-venda-alerta"
              type="text"
              value={form.mensagem_venda_alerta}
              onChange={(e) => onChange("mensagem_venda_alerta", e.target.value)}
              className={campoClass("mensagem_venda_alerta")}
            />
          </div>
          <div>
            <label
              htmlFor="mensagem-venda-critica"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Mensagem da venda vermelha
            </label>
            <input
              id="mensagem-venda-critica"
              type="text"
              value={form.mensagem_venda_critica}
              onChange={(e) => onChange("mensagem_venda_critica", e.target.value)}
              className={campoClass("mensagem_venda_critica")}
            />
          </div>
        </div>
      </div>

      <div
        className={blocoClass([
          "meta_faturamento_mensal",
          "alerta_estoque_percentual",
          "dias_produto_parado",
        ])}
      >
        <h2 className="text-xl font-semibold text-gray-800 mb-4">Metas e Alertas Operacionais</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label
              htmlFor="meta-faturamento-mensal"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Meta de faturamento mensal (R$)
            </label>
            <input
              id="meta-faturamento-mensal"
              type="number"
              min="0"
              step="0.01"
              value={form.meta_faturamento_mensal}
              onChange={(e) => onChange("meta_faturamento_mensal", e.target.value, true)}
              className={campoClass("meta_faturamento_mensal")}
            />
          </div>
          <div>
            <label
              htmlFor="aliquota-imposto-padrao"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Aliquota padrao de imposto %
            </label>
            <input
              id="aliquota-imposto-padrao"
              type="number"
              min="0"
              max="100"
              step="0.01"
              value={form.aliquota_imposto_padrao}
              onChange={(e) => onChange("aliquota_imposto_padrao", e.target.value, true)}
              className={campoClass("aliquota_imposto_padrao")}
            />
          </div>
          <div>
            <label
              htmlFor="alerta-estoque-percentual"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Alerta de estoque (%)
            </label>
            <input
              id="alerta-estoque-percentual"
              type="number"
              min="1"
              max="100"
              value={form.alerta_estoque_percentual}
              onChange={(e) => onChange("alerta_estoque_percentual", e.target.value, true)}
              className={campoClass("alerta_estoque_percentual")}
            />
          </div>
          <div>
            <label
              htmlFor="dias-produto-parado"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Produto parado (dias)
            </label>
            <input
              id="dias-produto-parado"
              type="number"
              min="1"
              value={form.dias_produto_parado}
              onChange={(e) => onChange("dias_produto_parado", e.target.value, true)}
              className={campoClass("dias_produto_parado")}
            />
          </div>
        </div>
      </div>

      <div className="flex justify-end">
        <button
          onClick={salvar}
          disabled={salvando}
          className="inline-flex items-center px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
        >
          <FiSave className="mr-2" />
          {salvando ? "Salvando..." : "Salvar Configuracoes"}
        </button>
      </div>
    </div>
  );
}
