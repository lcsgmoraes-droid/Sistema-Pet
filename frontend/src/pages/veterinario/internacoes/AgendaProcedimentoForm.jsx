import { useNavigate } from "react-router-dom";

import CatalogoClinicoAutocomplete from "../../../components/veterinario/CatalogoClinicoAutocomplete";

const inputClass = "border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white";
const labelClass = "text-xs font-medium text-gray-600";

function Campo({ ajuda, label, children, className = "" }) {
  return (
    <label className={`flex flex-col gap-1 ${className}`}>
      <span className={labelClass}>
        {label}
        {ajuda ? (
          <span
            className="ml-1 inline-flex h-4 w-4 items-center justify-center rounded-full bg-slate-100 text-[10px] text-slate-500"
            title={ajuda}
          >
            ?
          </span>
        ) : null}
      </span>
      {children}
    </label>
  );
}

function doseReferenciaMedicamento(medicamento) {
  if (!medicamento) return "";
  if (medicamento.posologia_referencia) return medicamento.posologia_referencia;
  const min = medicamento.dose_minima_mg_kg ?? medicamento.dose_min_mgkg;
  const max = medicamento.dose_maxima_mg_kg ?? medicamento.dose_max_mgkg;
  if (min && max) return `${min} a ${max} mg/kg`;
  if (min || max) return `${min || max} mg/kg`;
  return "";
}

export default function AgendaProcedimentoForm({
  agendaForm,
  setAgendaForm,
  internacoesOrdenadas,
  internacaoSelecionadaAgenda,
  medicamentosCatalogo = [],
  procedimentosCatalogo = [],
  salvando,
  onAdicionarProcedimentoAgenda,
  onAbrirInsumoRapido,
}) {
  const navigate = useNavigate();

  function selecionarCatalogo(opcao) {
    if (!opcao?.valor) return;
    const [tipo, id] = opcao.valor.split(":");

    if (tipo === "med") {
      const medicamento = medicamentosCatalogo.find((item) => String(item.id) === String(id));
      if (!medicamento) return;
      setAgendaForm((prev) => ({
        ...prev,
        medicamento: medicamento.nome || opcao.label || prev.medicamento,
        dose: prev.dose || doseReferenciaMedicamento(medicamento),
        via: prev.via || medicamento.via_administracao || "oral",
        unidade_quantidade: prev.unidade_quantidade || medicamento.forma_farmaceutica || "",
      }));
      return;
    }

    const procedimento = procedimentosCatalogo.find((item) => String(item.id) === String(id));
    if (!procedimento) return;
    setAgendaForm((prev) => ({
      ...prev,
      medicamento: procedimento.nome || opcao.label || prev.medicamento,
      dose: prev.dose || procedimento.descricao || "",
      unidade_quantidade: prev.unidade_quantidade || "un",
    }));
  }

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-gray-700">Novo procedimento / lembrete</p>
          <p className="mt-1 text-xs text-gray-500">
            Agende medicacoes e procedimentos previstos para o internado. O campo principal e digitavel:
            busque no catalogo ou mantenha um texto manual quando ainda nao houver cadastro.
          </p>
        </div>
        <button
          type="button"
          onClick={() => onAbrirInsumoRapido(agendaForm.internacao_id)}
          className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs font-medium text-emerald-700 hover:bg-emerald-100"
        >
          + Lancar insumo rapido
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <Campo label="Internado / paciente">
          <select
            value={agendaForm.internacao_id}
            onChange={(event) => setAgendaForm((prev) => ({ ...prev, internacao_id: event.target.value }))}
            className={inputClass}
          >
            <option value="">Selecione o internado...</option>
            {internacoesOrdenadas.map((internacao) => (
              <option key={internacao.id} value={internacao.id}>
                {internacao.pet_nome ?? `Pet #${internacao.pet_id}`}
                {internacao.box ? ` (${internacao.box})` : ""}
              </option>
            ))}
          </select>
        </Campo>

        <Campo label="Horario programado">
          <input
            type="datetime-local"
            value={agendaForm.horario}
            onChange={(event) => setAgendaForm((prev) => ({ ...prev, horario: event.target.value }))}
            className={inputClass}
          />
        </Campo>

        <div>
          <CatalogoClinicoAutocomplete
            value={agendaForm.medicamento}
            onTextChange={(medicamento) => setAgendaForm((prev) => ({ ...prev, medicamento }))}
            onSelect={selecionarCatalogo}
            onCreate={() => navigate("/veterinario/catalogo")}
            medicamentos={medicamentosCatalogo}
            procedimentos={procedimentosCatalogo}
            placeholder="Digite medicamento, procedimento ou principio ativo..."
          />
        </div>

        <Campo
          label="Dose indicada / orientacao clinica"
          ajuda="Use este campo para a dose de bula ou a orientacao clinica, por exemplo: 12,5 mg/kg a cada 12h."
        >
          <input
            type="text"
            value={agendaForm.dose}
            onChange={(event) => setAgendaForm((prev) => ({ ...prev, dose: event.target.value }))}
            className={inputClass}
          />
        </Campo>

        <Campo
          label="Quantidade por aplicacao"
          ajuda="Quantidade aplicada ou baixada do estoque a cada execucao, por exemplo: 1 comprimido ou 0,5 mL."
        >
          <input
            type="number"
            min="0"
            step="0.01"
            value={agendaForm.quantidade_prevista}
            onChange={(event) => setAgendaForm((prev) => ({ ...prev, quantidade_prevista: event.target.value }))}
            className={inputClass}
          />
        </Campo>

        <Campo label="Unidade">
          <input
            type="text"
            value={agendaForm.unidade_quantidade}
            onChange={(event) => setAgendaForm((prev) => ({ ...prev, unidade_quantidade: event.target.value }))}
            className={inputClass}
          />
        </Campo>

        <Campo label="Via de administracao">
          <input
            type="text"
            value={agendaForm.via}
            onChange={(event) => setAgendaForm((prev) => ({ ...prev, via: event.target.value }))}
            className={inputClass}
          />
        </Campo>

        <Campo label="Baia / local">
          <input
            type="text"
            value={agendaForm.internacao_id ? (internacaoSelecionadaAgenda?.box || "Sem baia") : "Selecione um internado"}
            disabled
            className={`${inputClass} bg-gray-50 text-gray-600`}
          />
        </Campo>

        <Campo label="Lembrete antes (min)">
          <input
            type="number"
            min="0"
            value={agendaForm.lembrete_min}
            onChange={(event) => setAgendaForm((prev) => ({ ...prev, lembrete_min: event.target.value }))}
            className={inputClass}
          />
        </Campo>

        <Campo label="Observacoes da agenda" className="md:col-span-2">
          <input
            type="text"
            value={agendaForm.observacoes}
            onChange={(event) => setAgendaForm((prev) => ({ ...prev, observacoes: event.target.value }))}
            className={inputClass}
          />
        </Campo>

        <button
          type="button"
          onClick={onAdicionarProcedimentoAgenda}
          disabled={salvando}
          className="self-end bg-purple-600 hover:bg-purple-700 text-white rounded-lg px-3 py-2 text-sm disabled:opacity-60"
        >
          {salvando ? "Salvando..." : "Adicionar na agenda"}
        </button>
      </div>
    </div>
  );
}
