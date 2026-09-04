import { Plus, RotateCcw, Trash2 } from "lucide-react";
import { TIPO_PROTOCOLO_DOSES, TIPO_RECOMPRA_CONTINUA } from "../../utils/produtoRecorrencia";

const ESPECIES = [
  ["both", "Cães e gatos"],
  ["dog", "Apenas cães"],
  ["cat", "Apenas gatos"],
];

const FASES = [
  ["all", "Todas as fases"],
  ["puppy", "Filhote"],
  ["adult", "Adulto"],
];

export default function ProdutosNovoRecorrenciaTab({
  adicionarRegraRecorrencia,
  atualizarDoseRecorrencia,
  atualizarQuantidadeDosesRecorrencia,
  atualizarRegraRecorrencia,
  formData,
  handleChange,
  removerRegraRecorrencia,
}) {
  const protocolos = formData.protocolos_recorrencia || [];

  return (
    <div className="space-y-6">
      <div className="rounded-lg border-l-4 border-purple-500 bg-purple-50 p-4">
        <h3 className="text-sm font-semibold text-purple-900">Recorrência inteligente</h3>
        <p className="mt-1 text-sm text-purple-800">
          Configure uma recompra contínua ou um protocolo com doses em dias diferentes. O mesmo
          produto pode ter protocolos distintos para filhotes e adultos, sem duplicar o estoque.
        </p>
        <p className="mt-2 text-xs text-purple-700">
          Os avisos são enviados pelo app. O disparo por WhatsApp fica preparado para ser ativado
          quando esse módulo estiver disponível.
        </p>
      </div>

      <label className="flex items-center rounded-lg bg-gray-50 p-4">
        <input
          type="checkbox"
          checked={Boolean(formData.tem_recorrencia)}
          onChange={(event) => handleChange("tem_recorrencia", event.target.checked)}
          className="h-5 w-5 rounded border-gray-300 text-purple-600 focus:ring-purple-500"
        />
        <span className="ml-3">
          <span className="block text-base font-medium text-gray-900">Produto com recorrência</span>
          <span className="block text-sm text-gray-500">
            Lembra a recompra, as próximas doses e, se configurado, o início de um novo protocolo.
          </span>
        </span>
      </label>

      {formData.tem_recorrencia && (
        <div className="space-y-5 border-t pt-6">
          <div className="flex flex-col gap-3 rounded-lg border border-gray-200 bg-white p-4 sm:flex-row">
            <button
              type="button"
              onClick={() => adicionarRegraRecorrencia(TIPO_RECOMPRA_CONTINUA)}
              className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg border border-purple-200 px-4 py-3 text-sm font-semibold text-purple-700 hover:bg-purple-50"
            >
              <Plus className="h-4 w-4" /> Recompra contínua
            </button>
            <button
              type="button"
              onClick={() => adicionarRegraRecorrencia(TIPO_PROTOCOLO_DOSES)}
              className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg bg-purple-600 px-4 py-3 text-sm font-semibold text-white hover:bg-purple-700"
            >
              <Plus className="h-4 w-4" /> Protocolo de doses
            </button>
          </div>

          {protocolos.length === 0 && (
            <div className="rounded-lg border border-dashed border-gray-300 p-8 text-center text-sm text-gray-500">
              Escolha acima como este produto deve gerar lembretes.
            </div>
          )}

          {protocolos.map((regra, index) => (
            <RegraRecorrenciaCard
              key={regra.id || `${regra.tipo}-${index}`}
              index={index}
              regra={regra}
              onAtualizar={atualizarRegraRecorrencia}
              onAtualizarDose={atualizarDoseRecorrencia}
              onAtualizarQuantidadeDoses={atualizarQuantidadeDosesRecorrencia}
              onRemover={removerRegraRecorrencia}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function RegraRecorrenciaCard({
  index,
  onAtualizar,
  onAtualizarDose,
  onAtualizarQuantidadeDoses,
  onRemover,
  regra,
}) {
  const protocoloDoses = regra.tipo === TIPO_PROTOCOLO_DOSES;
  return (
    <section className="space-y-5 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <label className="mb-1 block text-sm font-medium text-gray-700">Nome da regra</label>
          <input
            type="text"
            value={regra.nome}
            onChange={(event) => onAtualizar(index, "nome", event.target.value)}
            placeholder={protocoloDoses ? "Ex.: Vacina V10 - Filhote" : "Ex.: Antipulgas mensal"}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-purple-500"
          />
        </div>
        <button
          type="button"
          onClick={() => onRemover(index)}
          className="mt-6 rounded-lg p-2 text-red-600 hover:bg-red-50"
          title="Remover regra"
        >
          <Trash2 className="h-5 w-5" />
        </button>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <CampoSelect
          label="Compatibilidade por espécie"
          value={regra.especie_compativel}
          options={ESPECIES}
          onChange={(value) => onAtualizar(index, "especie_compativel", value)}
        />
        <CampoSelect
          label="Fase do pet"
          value={regra.fase_vida}
          options={FASES}
          onChange={(value) => onAtualizar(index, "fase_vida", value)}
          ajuda="Ajuda o PDV a sugerir o protocolo; o operador confirma na venda."
        />
      </div>

      {protocoloDoses ? (
        <ProgramacaoDoses
          index={index}
          regra={regra}
          onAtualizar={onAtualizar}
          onAtualizarDose={onAtualizarDose}
          onAtualizarQuantidadeDoses={onAtualizarQuantidadeDoses}
        />
      ) : (
        <RecompraContinua index={index} regra={regra} onAtualizar={onAtualizar} />
      )}

      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Observações / instruções
        </label>
        <textarea
          rows="2"
          value={regra.observacoes}
          onChange={(event) => onAtualizar(index, "observacoes", event.target.value)}
          placeholder="Orientações que ajudam a equipe a usar esta regra."
          className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-purple-500"
        />
      </div>
    </section>
  );
}

function RecompraContinua({ index, onAtualizar, regra }) {
  return (
    <div className="space-y-3 rounded-lg bg-purple-50 p-4">
      <div className="max-w-sm">
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Primeira previsão de recompra
        </label>
        <div className="flex items-center gap-2">
          <input
            type="number"
            min="1"
            max="3650"
            value={regra.intervalo_recompra_dias}
            onChange={(event) => onAtualizar(index, "intervalo_recompra_dias", event.target.value)}
            className="w-32 rounded-lg border border-gray-300 px-3 py-2 focus:ring-2 focus:ring-purple-500"
          />
          <span className="text-sm text-gray-600">dias após a venda</span>
        </div>
      </div>
      <label className="flex items-start gap-2 text-sm text-gray-700">
        <input
          type="checkbox"
          checked={regra.ajustar_ao_historico !== false}
          onChange={(event) => onAtualizar(index, "ajustar_ao_historico", event.target.checked)}
          className="mt-0.5 rounded border-gray-300 text-purple-600 focus:ring-purple-500"
        />
        Ajustar a previsão ao ciclo real de compras do cliente quando houver histórico suficiente.
      </label>
    </div>
  );
}

function ProgramacaoDoses({
  index,
  onAtualizar,
  onAtualizarDose,
  onAtualizarQuantidadeDoses,
  regra,
}) {
  return (
    <div className="space-y-5">
      <div className="max-w-xs">
        <label className="mb-1 block text-sm font-medium text-gray-700">Quantidade de doses</label>
        <input
          type="number"
          min="1"
          max="50"
          value={regra.doses.length}
          onChange={(event) => onAtualizarQuantidadeDoses(index, event.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:ring-2 focus:ring-purple-500"
        />
      </div>

      <div className="overflow-hidden rounded-lg border border-gray-200">
        {regra.doses.map((dose, doseIndex) => (
          <div
            key={dose.id || dose.numero_dose}
            className="grid items-center gap-2 border-b border-gray-100 px-4 py-3 last:border-b-0 sm:grid-cols-[120px_1fr]"
          >
            <span className="text-sm font-semibold text-gray-800">Dose {doseIndex + 1}</span>
            {doseIndex === 0 ? (
              <span className="text-sm text-gray-600">Dia 0 — no dia da venda</span>
            ) : (
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  min="1"
                  max="3650"
                  value={dose.dias_desde_inicio}
                  onChange={(event) => onAtualizarDose(index, doseIndex, event.target.value)}
                  className="w-28 rounded-lg border border-gray-300 px-3 py-2 focus:ring-2 focus:ring-purple-500"
                />
                <span className="text-sm text-gray-600">dias após o início</span>
              </div>
            )}
          </div>
        ))}
      </div>
      <p className="text-xs text-gray-500">
        Exemplo: dias 0, 14 e 21. As datas permanecem ligadas ao início, mesmo se uma dose for
        comprada antecipadamente.
      </p>

      <fieldset className="space-y-3 rounded-lg border border-purple-200 bg-purple-50 p-4">
        <legend className="px-1 text-sm font-semibold text-purple-900">
          Ao terminar o protocolo
        </legend>
        <label className="flex items-center gap-2 text-sm text-gray-700">
          <input
            type="radio"
            name={`fim-protocolo-${index}`}
            checked={!regra.oferecer_novo_protocolo}
            onChange={() => onAtualizar(index, "oferecer_novo_protocolo", false)}
          />
          Encerrar sem novo lembrete
        </label>
        <label className="flex flex-wrap items-center gap-2 text-sm text-gray-700">
          <input
            type="radio"
            name={`fim-protocolo-${index}`}
            checked={Boolean(regra.oferecer_novo_protocolo)}
            onChange={() => onAtualizar(index, "oferecer_novo_protocolo", true)}
          />
          <RotateCcw className="h-4 w-4 text-purple-600" />
          Oferecer um novo protocolo após
          <input
            type="number"
            min="1"
            max="3650"
            disabled={!regra.oferecer_novo_protocolo}
            value={regra.reiniciar_apos_dias}
            onFocus={() => onAtualizar(index, "oferecer_novo_protocolo", true)}
            onChange={(event) => onAtualizar(index, "reiniciar_apos_dias", event.target.value)}
            className="w-28 rounded-lg border border-gray-300 px-3 py-2 disabled:bg-gray-100"
            placeholder="Ex.: 180"
          />
          dias da última dose
        </label>
        <p className="text-xs text-purple-700">
          O prazo é livre; 180 dias é somente um exemplo e não será preenchido automaticamente.
        </p>
      </fieldset>
    </div>
  );
}

function CampoSelect({ ajuda, label, onChange, options, value }) {
  return (
    <div>
      <label className="mb-1 block text-sm font-medium text-gray-700">{label}</label>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-purple-500"
      >
        {options.map(([optionValue, text]) => (
          <option key={optionValue} value={optionValue}>
            {text}
          </option>
        ))}
      </select>
      {ajuda && <p className="mt-1 text-xs text-gray-500">{ajuda}</p>}
    </div>
  );
}
