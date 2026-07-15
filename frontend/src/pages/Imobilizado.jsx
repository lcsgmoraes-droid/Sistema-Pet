import { useCallback, useEffect, useState } from "react";
import toast from "react-hot-toast";
import {
  Archive,
  BadgeDollarSign,
  Building2,
  Calculator,
  Pencil,
  Plus,
  Search,
  Trash2,
  X,
} from "lucide-react";
import api from "../api";
import CurrencyInput from "../components/CurrencyInput";
import ActionButton from "../components/ui/ActionButton";
import DataTable from "../components/ui/DataTable";
import LoadingState from "../components/ui/LoadingState";
import MetricCard from "../components/ui/MetricCard";
import MetricGrid from "../components/ui/MetricGrid";
import PageHeader from "../components/ui/PageHeader";
import StatusBadge from "../components/ui/StatusBadge";
import { formatMoneyBRL } from "../utils/formatters";

const CATEGORIAS = [
  ["equipamentos", "Equipamentos"],
  ["moveis_utensilios", "Móveis e utensílios"],
  ["informatica", "Informática"],
  ["veiculos", "Veículos"],
  ["instalacoes", "Instalações"],
  ["maquinas", "Máquinas"],
  ["outros", "Outros"],
];

const STATUS = [
  ["ativo", "Ativo"],
  ["manutencao", "Em manutenção"],
  ["baixado", "Baixado"],
  ["vendido", "Vendido"],
];

const STATUS_INTENT = {
  ativo: "success",
  manutencao: "warning",
  baixado: "neutral",
  vendido: "info",
};

function hojeInput() {
  const hoje = new Date();
  return [
    hoje.getFullYear(),
    String(hoje.getMonth() + 1).padStart(2, "0"),
    String(hoje.getDate()).padStart(2, "0"),
  ].join("-");
}

function formularioVazio() {
  return {
    nome: "",
    codigo_patrimonial: "",
    categoria: "equipamentos",
    descricao: "",
    localizacao: "Loja fisica",
    fornecedor: "",
    documento: "",
    documento_url: "",
    quantidade: 1,
    data_aquisicao: hojeInput(),
    valor_aquisicao: 0,
    valor_residual: 0,
    valor_mercado: null,
    depreciar: true,
    vida_util_meses: 60,
    status: "ativo",
    data_baixa: "",
    motivo_baixa: "",
    observacoes: "",
  };
}

function labelDa(lista, valor) {
  return lista.find(([chave]) => chave === valor)?.[1] || valor || "-";
}

function formatarData(data) {
  if (!data) return "-";
  const [ano, mes, dia] = String(data).slice(0, 10).split("-");
  return `${dia}/${mes}/${ano}`;
}

function mensagemErro(error, fallback) {
  const detalhe = error?.response?.data?.detail;
  if (Array.isArray(detalhe)) return detalhe[0]?.msg || fallback;
  return detalhe || error?.message || fallback;
}

function Campo({ children, label, className = "" }) {
  return (
    <label className={`flex flex-col gap-1 text-sm font-medium text-slate-700 ${className}`}>
      <span>{label}</span>
      {children}
    </label>
  );
}

const inputClasses =
  "rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100";

export default function Imobilizado() {
  const [dados, setDados] = useState({ items: [], resumo: {} });
  const [loading, setLoading] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [excluindoId, setExcluindoId] = useState(null);
  const [filtros, setFiltros] = useState({
    busca: "",
    categoria: "",
    status: "em_posse",
  });
  const [modal, setModal] = useState({ aberto: false, id: null, form: formularioVazio() });

  const carregar = useCallback(async () => {
    setLoading(true);
    try {
      const params = Object.fromEntries(
        Object.entries(filtros).filter(([, valor]) => String(valor || "").trim()),
      );
      const response = await api.get("/financeiro/imobilizado", { params });
      setDados(response.data || { items: [], resumo: {} });
    } catch (error) {
      console.error("Erro ao carregar imobilizado:", error);
      toast.error(mensagemErro(error, "Não foi possível carregar o imobilizado."));
    } finally {
      setLoading(false);
    }
  }, [filtros]);

  useEffect(() => {
    const timer = globalThis.setTimeout(carregar, 250);
    return () => globalThis.clearTimeout(timer);
  }, [carregar]);

  const abrirNovo = () => {
    setModal({ aberto: true, id: null, form: formularioVazio() });
  };

  const abrirEdicao = (bem) => {
    setModal({
      aberto: true,
      id: bem.id,
      form: {
        ...formularioVazio(),
        ...bem,
        data_aquisicao: String(bem.data_aquisicao || "").slice(0, 10),
        data_baixa: bem.data_baixa ? String(bem.data_baixa).slice(0, 10) : "",
        valor_aquisicao: Number(bem.valor_aquisicao || 0),
        valor_residual: Number(bem.valor_residual || 0),
        valor_mercado: bem.valor_mercado == null ? null : Number(bem.valor_mercado),
      },
    });
  };

  const atualizarForm = (campo, valor) => {
    setModal((atual) => ({
      ...atual,
      form: {
        ...atual.form,
        [campo]: valor,
        ...(campo === "status" && !["baixado", "vendido"].includes(valor)
          ? { data_baixa: "", motivo_baixa: "" }
          : {}),
      },
    }));
  };

  const salvar = async (event) => {
    event.preventDefault();
    const form = modal.form;
    if (!form.nome.trim()) {
      toast.error("Informe o nome do bem.");
      return;
    }
    if (["baixado", "vendido"].includes(form.status) && !form.data_baixa) {
      toast.error("Informe a data da baixa ou venda.");
      return;
    }

    const vazioParaNulo = (valor) => (String(valor ?? "").trim() ? valor : null);
    const payload = {
      ...form,
      nome: form.nome.trim(),
      codigo_patrimonial: vazioParaNulo(form.codigo_patrimonial),
      descricao: vazioParaNulo(form.descricao),
      localizacao: vazioParaNulo(form.localizacao),
      fornecedor: vazioParaNulo(form.fornecedor),
      documento: vazioParaNulo(form.documento),
      documento_url: vazioParaNulo(form.documento_url),
      data_baixa: vazioParaNulo(form.data_baixa),
      motivo_baixa: vazioParaNulo(form.motivo_baixa),
      observacoes: vazioParaNulo(form.observacoes),
      quantidade: Number(form.quantidade || 1),
      vida_util_meses: form.depreciar ? Number(form.vida_util_meses || 60) : null,
      valor_mercado: form.valor_mercado == null ? null : Number(form.valor_mercado),
    };

    setSalvando(true);
    try {
      if (modal.id) {
        await api.put(`/financeiro/imobilizado/${modal.id}`, payload);
        toast.success("Bem atualizado.");
      } else {
        await api.post("/financeiro/imobilizado", payload);
        toast.success("Bem cadastrado.");
      }
      setModal({ aberto: false, id: null, form: formularioVazio() });
      await carregar();
    } catch (error) {
      console.error("Erro ao salvar bem:", error);
      toast.error(mensagemErro(error, "Não foi possível salvar o bem."));
    } finally {
      setSalvando(false);
    }
  };

  const excluir = async (bem) => {
    if (!globalThis.confirm(`Excluir definitivamente "${bem.nome}"?`)) return;
    setExcluindoId(bem.id);
    try {
      await api.delete(`/financeiro/imobilizado/${bem.id}`);
      toast.success("Bem excluido.");
      await carregar();
    } catch (error) {
      toast.error(mensagemErro(error, "Não foi possível excluir o bem."));
    } finally {
      setExcluindoId(null);
    }
  };

  const columns = [
    {
      key: "nome",
      header: "Bem",
      render: (bem) => (
        <div className="min-w-52">
          <div className="font-semibold text-slate-900">{bem.nome}</div>
          <div className="text-xs text-slate-500">
            {bem.codigo_patrimonial || `ID ${bem.id}`} - {labelDa(CATEGORIAS, bem.categoria)}
          </div>
        </div>
      ),
    },
    { key: "localizacao", header: "Local", accessor: (bem) => bem.localizacao || "-" },
    { key: "quantidade", header: "Qtd.", align: "right" },
    {
      key: "aquisicao",
      header: "Aquisição",
      align: "right",
      render: (bem) => (
        <div className="whitespace-nowrap text-right">
          <div>{formatMoneyBRL(bem.valor_aquisicao)}</div>
          <div className="text-xs text-slate-500">{formatarData(bem.data_aquisicao)}</div>
        </div>
      ),
    },
    {
      key: "contabil",
      header: "Valor contábil",
      align: "right",
      render: (bem) => (
        <div className="whitespace-nowrap text-right">
          <div className="font-medium">{formatMoneyBRL(bem.valor_contabil)}</div>
          <div className="text-xs text-slate-500">-{formatMoneyBRL(bem.depreciacao_acumulada)}</div>
        </div>
      ),
    },
    {
      key: "mercado",
      header: "Valor de mercado",
      align: "right",
      render: (bem) =>
        bem.valor_mercado == null ? (
          <span className="text-xs text-amber-700">Não informado</span>
        ) : (
          formatMoneyBRL(bem.valor_mercado)
        ),
    },
    {
      key: "status",
      header: "Situação",
      render: (bem) => (
        <StatusBadge intent={STATUS_INTENT[bem.status]}>{labelDa(STATUS, bem.status)}</StatusBadge>
      ),
    },
    {
      key: "acoes",
      header: "Acoes",
      render: (bem) => (
        <div className="flex gap-1">
          <ActionButton icon={Pencil} size="xs" tone="ghost" onClick={() => abrirEdicao(bem)}>
            Editar
          </ActionButton>
          <ActionButton
            icon={Trash2}
            intent="delete"
            loading={excluindoId === bem.id}
            size="xs"
            tone="ghost"
            onClick={() => excluir(bem)}
          >
            Excluir
          </ActionButton>
        </div>
      ),
    },
  ];

  const resumo = dados.resumo || {};

  return (
    <div className="space-y-5 p-4 md:p-6">
      <PageHeader
        icon={Building2}
        title="Imobilizado"
        subtitle="Controle os bens duráveis, a depreciação e o valor estimado do patrimônio."
        actions={
          <ActionButton icon={Plus} intent="create" onClick={abrirNovo}>
            Novo bem
          </ActionButton>
        }
      />

      <MetricGrid>
        <MetricCard
          icon={<Archive size={20} />}
          intent="blue"
          label="Bens cadastrados"
          value={`${resumo.total_registros || 0} ${resumo.total_registros === 1 ? "registro" : "registros"}`}
          subtitle={`${resumo.total_itens || 0} ${resumo.total_itens === 1 ? "item físico" : "itens físicos"}`}
        />
        <MetricCard
          icon={<BadgeDollarSign size={20} />}
          intent="violet"
          label="Valor de aquisição"
          value={formatMoneyBRL(resumo.valor_aquisicao)}
        />
        <MetricCard
          icon={<Calculator size={20} />}
          intent="slate"
          label="Valor contábil"
          value={formatMoneyBRL(resumo.valor_contabil)}
          subtitle={`Depreciação: ${formatMoneyBRL(resumo.depreciacao_acumulada)}`}
        />
        <MetricCard
          icon={<BadgeDollarSign size={20} />}
          intent="emerald"
          label="Valor de mercado"
          value={formatMoneyBRL(resumo.valor_mercado_informado)}
          subtitle={`${resumo.registros_sem_valor_mercado || 0} sem avaliacao`}
        />
      </MetricGrid>

      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="grid gap-3 md:grid-cols-[1fr_220px_190px]">
          <label className="relative">
            <Search className="absolute left-3 top-2.5 text-slate-400" size={18} />
            <input
              className={`${inputClasses} w-full pl-10`}
              placeholder="Buscar por nome, código ou local..."
              value={filtros.busca}
              onChange={(event) => setFiltros((f) => ({ ...f, busca: event.target.value }))}
            />
          </label>
          <select
            className={inputClasses}
            value={filtros.categoria}
            onChange={(event) => setFiltros((f) => ({ ...f, categoria: event.target.value }))}
          >
            <option value="">Todas as categorias</option>
            {CATEGORIAS.map(([valor, label]) => (
              <option key={valor} value={valor}>
                {label}
              </option>
            ))}
          </select>
          <select
            className={inputClasses}
            value={filtros.status}
            onChange={(event) => setFiltros((f) => ({ ...f, status: event.target.value }))}
          >
            <option value="em_posse">Em posse da empresa</option>
            <option value="">Todas, incluindo baixados</option>
            {STATUS.map(([valor, label]) => (
              <option key={valor} value={valor}>
                {label}
              </option>
            ))}
          </select>
        </div>
        <div className="mt-4">
          {loading ? (
            <LoadingState message="Carregando imobilizado..." />
          ) : (
            <DataTable columns={columns} data={dados.items || []} getRowKey={(bem) => bem.id} />
          )}
        </div>
      </section>

      {modal.aberto && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-3">
          <form
            className="max-h-[94vh] w-full max-w-4xl overflow-y-auto rounded-2xl bg-white shadow-2xl"
            onSubmit={salvar}
          >
            <div className="sticky top-0 z-10 flex items-center justify-between border-b bg-white px-5 py-4">
              <div>
                <h2 className="text-lg font-bold text-slate-900">
                  {modal.id ? "Editar bem" : "Cadastrar bem"}
                </h2>
                <p className="text-xs text-slate-500">
                  Valores do conjunto cadastrado, não unitários.
                </p>
              </div>
              <button type="button" onClick={() => setModal((m) => ({ ...m, aberto: false }))}>
                <X className="text-slate-500" />
              </button>
            </div>

            <div className="grid gap-4 p-5 md:grid-cols-2 lg:grid-cols-3">
              <Campo label="Nome do bem" className="lg:col-span-2">
                <input
                  className={inputClasses}
                  required
                  value={modal.form.nome}
                  onChange={(e) => atualizarForm("nome", e.target.value)}
                />
              </Campo>
              <Campo label="Código patrimonial">
                <input
                  className={inputClasses}
                  value={modal.form.codigo_patrimonial || ""}
                  onChange={(e) => atualizarForm("codigo_patrimonial", e.target.value)}
                />
              </Campo>
              <Campo label="Categoria">
                <select
                  className={inputClasses}
                  value={modal.form.categoria}
                  onChange={(e) => atualizarForm("categoria", e.target.value)}
                >
                  {CATEGORIAS.map(([valor, label]) => (
                    <option key={valor} value={valor}>
                      {label}
                    </option>
                  ))}
                </select>
              </Campo>
              <Campo label="Localização">
                <input
                  className={inputClasses}
                  value={modal.form.localizacao || ""}
                  onChange={(e) => atualizarForm("localizacao", e.target.value)}
                />
              </Campo>
              <Campo label="Quantidade">
                <input
                  className={inputClasses}
                  min="1"
                  type="number"
                  value={modal.form.quantidade}
                  onChange={(e) => atualizarForm("quantidade", e.target.value)}
                />
              </Campo>
              <Campo label="Data de aquisição">
                <input
                  className={inputClasses}
                  required
                  type="date"
                  value={modal.form.data_aquisicao}
                  onChange={(e) => atualizarForm("data_aquisicao", e.target.value)}
                />
              </Campo>
              <Campo label="Valor de aquisição (total)">
                <CurrencyInput
                  className={inputClasses}
                  value={modal.form.valor_aquisicao}
                  onChange={(valor) => atualizarForm("valor_aquisicao", valor)}
                />
              </Campo>
              <Campo label="Valor de mercado estimado">
                <CurrencyInput
                  className={inputClasses}
                  value={modal.form.valor_mercado || 0}
                  onChange={(valor) => atualizarForm("valor_mercado", valor)}
                />
              </Campo>
              <Campo label="Valor residual">
                <CurrencyInput
                  className={inputClasses}
                  value={modal.form.valor_residual}
                  onChange={(valor) => atualizarForm("valor_residual", valor)}
                />
              </Campo>
              <Campo label="Vida útil (meses)">
                <input
                  className={inputClasses}
                  disabled={!modal.form.depreciar}
                  min="1"
                  type="number"
                  value={modal.form.vida_util_meses || ""}
                  onChange={(e) => atualizarForm("vida_util_meses", e.target.value)}
                />
              </Campo>
              <Campo label="Situação">
                <select
                  className={inputClasses}
                  value={modal.form.status}
                  onChange={(e) => atualizarForm("status", e.target.value)}
                >
                  {STATUS.map(([valor, label]) => (
                    <option key={valor} value={valor}>
                      {label}
                    </option>
                  ))}
                </select>
              </Campo>
              <label className="flex items-center gap-2 self-end pb-2 text-sm font-medium text-slate-700">
                <input
                  type="checkbox"
                  checked={modal.form.depreciar}
                  onChange={(e) => atualizarForm("depreciar", e.target.checked)}
                />
                Calcular depreciação automaticamente
              </label>
              <Campo label="Fornecedor">
                <input
                  className={inputClasses}
                  value={modal.form.fornecedor || ""}
                  onChange={(e) => atualizarForm("fornecedor", e.target.value)}
                />
              </Campo>
              <Campo label="Nota fiscal / documento">
                <input
                  className={inputClasses}
                  value={modal.form.documento || ""}
                  onChange={(e) => atualizarForm("documento", e.target.value)}
                />
              </Campo>
              <Campo label="Link do documento">
                <input
                  className={inputClasses}
                  type="url"
                  value={modal.form.documento_url || ""}
                  onChange={(e) => atualizarForm("documento_url", e.target.value)}
                />
              </Campo>
              {["baixado", "vendido"].includes(modal.form.status) && (
                <>
                  <Campo label="Data da baixa/venda">
                    <input
                      className={inputClasses}
                      required
                      type="date"
                      value={modal.form.data_baixa || ""}
                      onChange={(e) => atualizarForm("data_baixa", e.target.value)}
                    />
                  </Campo>
                  <Campo label="Motivo da baixa" className="md:col-span-2">
                    <input
                      className={inputClasses}
                      value={modal.form.motivo_baixa || ""}
                      onChange={(e) => atualizarForm("motivo_baixa", e.target.value)}
                    />
                  </Campo>
                </>
              )}
              <Campo label="Descrição" className="md:col-span-2 lg:col-span-3">
                <textarea
                  className={inputClasses}
                  rows="2"
                  value={modal.form.descricao || ""}
                  onChange={(e) => atualizarForm("descricao", e.target.value)}
                />
              </Campo>
              <Campo label="Observações" className="md:col-span-2 lg:col-span-3">
                <textarea
                  className={inputClasses}
                  rows="3"
                  value={modal.form.observacoes || ""}
                  onChange={(e) => atualizarForm("observacoes", e.target.value)}
                />
              </Campo>
            </div>

            <div className="sticky bottom-0 flex justify-end gap-2 border-t bg-white px-5 py-4">
              <ActionButton tone="soft" onClick={() => setModal((m) => ({ ...m, aberto: false }))}>
                Cancelar
              </ActionButton>
              <ActionButton intent="edit" loading={salvando} type="submit">
                Salvar bem
              </ActionButton>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
