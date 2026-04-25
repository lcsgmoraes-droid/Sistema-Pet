import { BedDouble, Calculator, MessageSquare, Syringe, X } from "lucide-react";
import { formatMoneyBRL, formatPercent } from "../../../utils/formatters";
import {
  css,
  obterResumoProcedimentoSelecionado,
} from "./consultaFormUtils";
import TimelineConsultaPanel from "./TimelineConsultaPanel";

function campo(label, obrigatorio = false) {
  return function renderCampo(children) {
    return (
      <div className="space-y-1">
        <label className="block text-xs font-medium text-gray-600">
          {label} {obrigatorio && <span className="text-red-400">*</span>}
        </label>
        {children}
      </div>
    );
  };
}

export default function DiagnosticoTratamentoSection({
  modoSomenteLeitura,
  form,
  setCampo,
  medicamentosCatalogo,
  procedimentosCatalogo,
  consultaIdAtual,
  timelineConsulta,
  carregandoTimeline,
  adicionarItem,
  removerItem,
  setItem,
  selecionarMedicamentoNoItem,
  recalcularDoseItem,
  adicionarProcedimento,
  removerProcedimento,
  setProcedimentoItem,
  selecionarProcedimentoCatalogo,
  abrirModalInsumoRapido,
  abrirFluxoConsulta,
  carregarTimelineConsulta,
  onOpenTimelineLink,
}) {
  return (
    <div className="space-y-4">
      <fieldset disabled={modoSomenteLeitura} className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-4 disabled:opacity-100">
        <h2 className="font-semibold text-gray-700">Diagnóstico e tratamento</h2>
        {campo("Diagnóstico")(
          <textarea value={form.diagnostico} onChange={(e) => setCampo("diagnostico", e.target.value)} className={css.textarea} placeholder="Diagnóstico principal e diferenciais..." />
        )}
        {campo("Prognóstico")(
          <select value={form.prognostico} onChange={(e) => setCampo("prognostico", e.target.value)} className={css.select}>
            <option value="">-</option>
            <option>Favorável</option><option>Reservado</option><option>Grave</option><option>Desfavorável</option>
          </select>
        )}
        {campo("Tratamento prescrito")(
          <textarea value={form.tratamento} onChange={(e) => setCampo("tratamento", e.target.value)} className={css.textarea} placeholder="Protocolo terapêutico, cuidados em casa..." />
        )}
        <div className="grid grid-cols-2 gap-3">
          {campo("Retorno em (dias)")(
            <input type="number" value={form.retorno_em_dias} onChange={(e) => setCampo("retorno_em_dias", e.target.value)} className={css.input} placeholder="ex: 15" />
          )}
        </div>
        {campo("Observações adicionais")(
          <textarea value={form.observacoes} onChange={(e) => setCampo("observacoes", e.target.value)} className={css.textarea} placeholder="Observações para o tutor, cuidados especiais..." />
        )}
      </fieldset>

      <fieldset disabled={modoSomenteLeitura} className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-3 disabled:opacity-100">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-gray-700">Prescrição (opcional)</h2>
          <button
            onClick={adicionarItem}
            className="text-xs text-blue-600 hover:text-blue-800 underline"
          >
            + Adicionar medicamento
          </button>
        </div>
        {form.prescricao_itens.length === 0 && (
          <p className="text-xs text-gray-400">Nenhum medicamento adicionado ainda.</p>
        )}
        {form.prescricao_itens.map((item, idx) => (
          <div key={idx} className="border border-gray-100 rounded-lg p-3 space-y-2 relative">
            <button
              onClick={() => removerItem(idx)}
              className="absolute top-2 right-2 text-gray-300 hover:text-red-400"
            >
              <X size={14} />
            </button>
            <div className="grid grid-cols-2 gap-2">
              <select
                value={item.medicamento_id || ""}
                onChange={(e) => selecionarMedicamentoNoItem(idx, e.target.value)}
                className={css.select}
              >
                <option value="">Selecionar do catálogo...</option>
                {medicamentosCatalogo.map((m) => (
                  <option key={m.id} value={m.id}>{m.nome}</option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => recalcularDoseItem(idx)}
                className="inline-flex items-center justify-center gap-2 px-3 py-2 text-xs border border-blue-200 text-blue-700 rounded-lg hover:bg-blue-50"
              >
                <Calculator size={14} />
                Calcular dose pelo peso
              </button>
            </div>
            {(item.dose_minima_mg_kg || item.dose_maxima_mg_kg) && (
              <p className="text-[11px] text-gray-500">
                Referência do catálogo: {item.dose_minima_mg_kg || "-"}
                {item.dose_maxima_mg_kg ? ` a ${item.dose_maxima_mg_kg}` : ""} mg/kg
              </p>
            )}
            <div className="grid grid-cols-2 gap-2">
              <input type="text" placeholder="Nome do medicamento" value={item.nome} onChange={(e) => setItem(idx, "nome", e.target.value)} className={css.input} />
              <input type="text" placeholder="Princípio ativo" value={item.principio_ativo} onChange={(e) => setItem(idx, "principio_ativo", e.target.value)} className={css.input} />
              <input type="text" placeholder="Dose (ex: 10 mg/kg)" value={item.dose_mg} onChange={(e) => setItem(idx, "dose_mg", e.target.value)} className={css.input} />
              <select value={item.via} onChange={(e) => setItem(idx, "via", e.target.value)} className={css.select}>
                <option value="oral">Oral</option>
                <option value="iv">IV</option><option value="im">IM</option>
                <option value="sc">SC</option><option value="topico">Tópico</option>
                <option value="oftalmico">Oftálmico</option>
              </select>
              <input type="text" placeholder="Frequência (ex: a cada 12h)" value={item.frequencia} onChange={(e) => setItem(idx, "frequencia", e.target.value)} className={css.input} />
              <input type="number" placeholder="Duração (dias)" value={item.duracao_dias} onChange={(e) => setItem(idx, "duracao_dias", e.target.value)} className={css.input} />
            </div>
            <input type="text" placeholder="Instruções ao tutor" value={item.instrucoes} onChange={(e) => setItem(idx, "instrucoes", e.target.value)} className={css.input} />
          </div>
        ))}
      </fieldset>

      <fieldset disabled={modoSomenteLeitura} className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-3 disabled:opacity-100">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-gray-700">Procedimentos realizados</h2>
          <div className="flex flex-wrap items-center gap-3">
            <button onClick={adicionarProcedimento} className="text-xs text-blue-600 hover:text-blue-800 underline">
              + Adicionar procedimento
            </button>
            <button
              type="button"
              onClick={abrirModalInsumoRapido}
              disabled={!consultaIdAtual}
              className="text-xs text-emerald-600 hover:text-emerald-800 underline disabled:opacity-50"
            >
              + Lançar insumo rápido
            </button>
          </div>
        </div>
        {form.procedimentos_realizados.length === 0 && (
          <p className="text-xs text-gray-400">Nenhum procedimento lançado ainda.</p>
        )}
        {form.procedimentos_realizados.map((item, idx) => {
          const resumo = obterResumoProcedimentoSelecionado(item, procedimentosCatalogo);

          return (
            <div key={`procedimento_${idx}`} className="border border-gray-100 rounded-lg p-3 space-y-2 relative">
              <button onClick={() => removerProcedimento(idx)} className="absolute top-2 right-2 text-gray-300 hover:text-red-400">
                <X size={14} />
              </button>
              <div className="grid grid-cols-2 gap-2">
                <select value={item.catalogo_id || ""} onChange={(e) => selecionarProcedimentoCatalogo(idx, e.target.value)} className={css.select}>
                  <option value="">Selecionar do catálogo...</option>
                  {procedimentosCatalogo.map((proc) => (
                    <option key={proc.id} value={proc.id}>{proc.nome}</option>
                  ))}
                </select>
                <input type="text" placeholder="Nome do procedimento" value={item.nome} onChange={(e) => setProcedimentoItem(idx, "nome", e.target.value)} className={css.input} />
                <input type="text" placeholder="Descrição" value={item.descricao} onChange={(e) => setProcedimentoItem(idx, "descricao", e.target.value)} className={css.input} />
                <input type="text" placeholder="Valor" value={item.valor} onChange={(e) => setProcedimentoItem(idx, "valor", e.target.value)} className={css.input} />
              </div>
              <input type="text" placeholder="Observações" value={item.observacoes} onChange={(e) => setProcedimentoItem(idx, "observacoes", e.target.value)} className={css.input} />
              {resumo.possuiCatalogo && (
                <div className="grid grid-cols-3 gap-2 rounded-lg bg-gray-50 border border-gray-200 px-3 py-2">
                  <div>
                    <p className="text-[11px] uppercase tracking-wide text-gray-400">Cobrado</p>
                    <p className="text-sm font-semibold text-gray-800">{formatMoneyBRL(resumo.valorCobrado)}</p>
                  </div>
                  <div>
                    <p className="text-[11px] uppercase tracking-wide text-gray-400">Custo est.</p>
                    <p className="text-sm font-semibold text-amber-700">{formatMoneyBRL(resumo.custoTotal)}</p>
                  </div>
                  <div>
                    <p className="text-[11px] uppercase tracking-wide text-gray-400">Margem est.</p>
                    <p className={`text-sm font-semibold ${resumo.margemValor < 0 ? "text-red-600" : "text-emerald-700"}`}>
                      {formatMoneyBRL(resumo.margemValor)}
                    </p>
                    <p className="text-[11px] text-gray-400">{formatPercent(resumo.margemPercentual)}</p>
                  </div>
                </div>
              )}
              <label className="flex items-center gap-2 text-xs text-gray-600">
                <input type="checkbox" checked={item.baixar_estoque !== false} onChange={(e) => setProcedimentoItem(idx, "baixar_estoque", e.target.checked)} />
                Baixar estoque automático dos insumos vinculados
              </label>
            </div>
          );
        })}
      </fieldset>

      <div className="rounded-xl border border-purple-100 bg-purple-50 px-4 py-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold text-purple-900">Fluxos vinculados à consulta</h3>
            <p className="text-xs text-purple-700">
              Use a consulta #{consultaIdAtual || "-"} como referência para exames, vacinas, IA e internação.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => abrirFluxoConsulta("/veterinario/assistente-ia")}
              disabled={!consultaIdAtual}
              className="inline-flex items-center gap-2 rounded-lg border border-purple-200 bg-white px-3 py-2 text-sm font-medium text-purple-700 hover:bg-purple-100 disabled:opacity-60"
            >
              <MessageSquare size={15} />
              IA da consulta
            </button>
            <button
              type="button"
              onClick={() => abrirFluxoConsulta("/veterinario/vacinas", { acao: "novo" })}
              disabled={!consultaIdAtual}
              className="inline-flex items-center gap-2 rounded-lg border border-purple-200 bg-white px-3 py-2 text-sm font-medium text-purple-700 hover:bg-purple-100 disabled:opacity-60"
            >
              <Syringe size={15} />
              Registrar vacina
            </button>
            <button
              type="button"
              onClick={() => abrirFluxoConsulta("/veterinario/internacoes", { abrir_nova: "1" })}
              disabled={!consultaIdAtual}
              className="inline-flex items-center gap-2 rounded-lg border border-purple-200 bg-white px-3 py-2 text-sm font-medium text-purple-700 hover:bg-purple-100 disabled:opacity-60"
            >
              <BedDouble size={15} />
              Encaminhar para internação
            </button>
          </div>
        </div>
        {!consultaIdAtual && (
          <p className="mt-3 text-xs text-purple-700">
            Salve o rascunho primeiro para liberar os outros fluxos já amarrados a esta consulta.
          </p>
        )}
      </div>

      <TimelineConsultaPanel
        consultaIdAtual={consultaIdAtual}
        carregandoTimeline={carregandoTimeline}
        timelineConsulta={timelineConsulta}
        onRefresh={() => carregarTimelineConsulta()}
        onOpenLink={onOpenTimelineLink}
      />
    </div>
  );
}
