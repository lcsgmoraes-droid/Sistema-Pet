import BanhoTosaHelpTooltip from "./BanhoTosaHelpTooltip";

export const initialServicoForm = {
  nome: "",
  categoria: "banho",
  descricao: "",
  duracao_padrao_minutos: "60",
  requer_banho: true,
  requer_tosa: false,
  requer_secagem: true,
  permite_pacote: true,
  ativo: true,
};

export function formFromServico(servico) {
  return {
    nome: servico.nome || "",
    categoria: servico.categoria || "banho",
    descricao: servico.descricao || "",
    duracao_padrao_minutos: String(servico.duracao_padrao_minutos || 60),
    requer_banho: Boolean(servico.requer_banho),
    requer_tosa: Boolean(servico.requer_tosa),
    requer_secagem: Boolean(servico.requer_secagem),
    permite_pacote: Boolean(servico.permite_pacote),
    ativo: Boolean(servico.ativo),
  };
}

export function payloadFromServicoForm(form) {
  return {
    ...form,
    nome: form.nome.trim(),
    descricao: form.descricao.trim() || null,
    duracao_padrao_minutos: Number(form.duracao_padrao_minutos || 60),
  };
}

export default function BanhoTosaServicoForm({
  form,
  editing,
  saving,
  onChangeField,
  onCancelEdit,
  onSubmit,
}) {
  return (
    <form
      onSubmit={onSubmit}
      className="rounded-3xl border border-white/80 bg-white p-6 shadow-sm"
    >
      <p className="text-xs font-bold uppercase tracking-[0.2em] text-orange-500">
        Catalogo
      </p>
      <h2 className="mt-2 text-xl font-black text-slate-900">
        {editing ? "Editar servico" : "Novo servico"}
      </h2>

      <div className="mt-5 space-y-4">
        <TextField label="Nome" value={form.nome} onChange={(value) => onChangeField("nome", value)} help="Nome que aparece na agenda, na fila e no fechamento para o PDV." />
        <label className="block">
          <span className="inline-flex items-center text-xs font-bold uppercase tracking-[0.12em] text-slate-500">
            Categoria
            <BanhoTosaHelpTooltip text="Agrupa servicos para relatorios e filtros: banho, tosa, combo, higiene ou outro." />
          </span>
          <select
            value={form.categoria}
            onChange={(event) => onChangeField("categoria", event.target.value)}
            className="mt-1 w-full rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-900 outline-none focus:border-orange-400 focus:bg-white focus:ring-2 focus:ring-orange-100"
          >
            <option value="banho">Banho</option>
            <option value="tosa">Tosa</option>
            <option value="combo">Combo</option>
            <option value="higiene">Higiene</option>
            <option value="outro">Outro</option>
          </select>
        </label>
        <TextField label="Duracao padrao (min)" type="number" value={form.duracao_padrao_minutos} onChange={(value) => onChangeField("duracao_padrao_minutos", value)} help="Tempo usado para prever fim do agendamento e ocupacao da equipe." />
        <TextField label="Descricao" value={form.descricao} onChange={(value) => onChangeField("descricao", value)} help="Explique o que esta incluso para padronizar a venda e o atendimento." />

        <div className="grid gap-2 sm:grid-cols-2">
          <CheckField label="Requer banho" checked={form.requer_banho} onChange={(value) => onChangeField("requer_banho", value)} help="Marca se o servico consome agua, shampoo e etapa de banho." />
          <CheckField label="Requer tosa" checked={form.requer_tosa} onChange={(value) => onChangeField("requer_tosa", value)} help="Marca se precisa de tosador, mesa ou etapa de tosa." />
          <CheckField label="Requer secagem" checked={form.requer_secagem} onChange={(value) => onChangeField("requer_secagem", value)} help="Marca se deve considerar secador/soprador no tempo e energia." />
          <CheckField label="Permite pacote" checked={form.permite_pacote} onChange={(value) => onChangeField("permite_pacote", value)} help="Permite vender creditos recorrentes desse servico." />
          <CheckField label="Ativo" checked={form.ativo} onChange={(value) => onChangeField("ativo", value)} help="Servicos inativos ficam fora da operacao, mas preservam historico." />
        </div>
      </div>

      <div className="mt-6 grid gap-2 sm:grid-cols-2">
        <button
          type="submit"
          disabled={saving}
          className="rounded-2xl bg-slate-900 px-5 py-3 text-sm font-bold text-white transition hover:bg-slate-700 disabled:opacity-60"
        >
          {saving ? "Salvando..." : editing ? "Salvar alteracoes" : "Cadastrar servico"}
        </button>
        {editing && (
          <button
            type="button"
            onClick={onCancelEdit}
            className="rounded-2xl border border-slate-200 bg-white px-5 py-3 text-sm font-bold text-slate-700 transition hover:border-orange-300 hover:text-orange-700"
          >
            Cancelar edicao
          </button>
        )}
      </div>
    </form>
  );
}

function TextField({ label, value, onChange, type = "text", help }) {
  return (
    <label className="block">
      <span className="inline-flex items-center text-xs font-bold uppercase tracking-[0.12em] text-slate-500">
        {label}
        <BanhoTosaHelpTooltip text={help} />
      </span>
      <input
        type={type}
        title={help || label}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 w-full rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-900 outline-none focus:border-orange-400 focus:bg-white focus:ring-2 focus:ring-orange-100"
      />
    </label>
  );
}

function CheckField({ label, checked, onChange, help }) {
  return (
    <label className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-700" title={help || label}>
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="h-4 w-4 rounded border-slate-300 text-orange-500"
      />
      {label}
      <BanhoTosaHelpTooltip text={help} />
    </label>
  );
}
