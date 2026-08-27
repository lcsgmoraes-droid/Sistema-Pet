import { useEffect, useMemo, useState } from "react";
import { CalendarClock, Trash2, X } from "lucide-react";
import { useEscapeToClose } from "../../utils/modalEscape";
import {
  adicionarDiasDataLocal,
  calcularDataFimPorPrazo,
  dataLocalParaISO,
  formatarDataFimRacao,
  validarDataFimRacao,
} from "./pdvPrevisaoFimRacao";

const PRAZOS_RAPIDOS = [7, 15, 30, 45, 60, 90];

export default function ModalPrevisaoFimRacao({ cliente, item, onClose, onSalvar }) {
  const [modo, setModo] = useState("prazo");
  const [prazo, setPrazo] = useState("30");
  const [dataPrevista, setDataPrevista] = useState("");
  const [erro, setErro] = useState("");

  useEscapeToClose({ isOpen: Boolean(item), onClose });

  useEffect(() => {
    if (!item) return;
    const temData = Boolean(item.racao_data_prevista_fim);
    setModo(temData ? "data" : "prazo");
    setPrazo(String(item.racao_prazo_estimado_dias || 30));
    setDataPrevista(item.racao_data_prevista_fim || dataLocalParaISO(adicionarDiasDataLocal(30)));
    setErro("");
  }, [item]);

  const dataCalculada = useMemo(
    () => (modo === "data" ? dataPrevista : calcularDataFimPorPrazo(prazo)),
    [dataPrevista, modo, prazo],
  );
  const temPrevisao = Boolean(item?.racao_data_prevista_fim || item?.racao_prazo_estimado_dias);

  if (!item) return null;

  function salvar(event) {
    event.preventDefault();
    if (modo === "data") {
      if (!validarDataFimRacao(dataPrevista)) {
        setErro("Escolha uma data posterior a hoje.");
        return;
      }
      onSalvar({
        racao_data_prevista_fim: dataPrevista,
        racao_prazo_estimado_dias: null,
      });
      return;
    }

    const dias = Number.parseInt(prazo, 10);
    if (!Number.isInteger(dias) || dias < 1 || dias > 365) {
      setErro("Informe um prazo entre 1 e 365 dias.");
      return;
    }
    onSalvar({
      racao_data_prevista_fim: null,
      racao_prazo_estimado_dias: dias,
    });
  }

  return (
    <div
      className="fixed inset-0 z-[70] flex items-center justify-center bg-black/50 p-4"
      onMouseDown={(event) => event.target === event.currentTarget && onClose()}
    >
      <form
        aria-modal="true"
        className="w-full max-w-lg overflow-hidden rounded-2xl bg-white shadow-2xl"
        onSubmit={salvar}
        role="dialog"
      >
        <div className="flex items-start justify-between border-b border-slate-200 px-5 py-4">
          <div className="flex min-w-0 items-start gap-3">
            <div className="rounded-xl bg-teal-100 p-2 text-teal-700">
              <CalendarClock className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <h3 className="text-lg font-bold text-slate-900">Quando esta ração deve acabar?</h3>
              <p className="mt-0.5 truncate text-sm text-slate-500" title={item.produto_nome}>
                {item.produto_nome}
              </p>
            </div>
          </div>
          <button
            aria-label="Fechar"
            className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
            data-modal-close
            onClick={onClose}
            type="button"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-5 p-5">
          <div className="rounded-xl border border-teal-200 bg-teal-50 p-3 text-sm text-teal-900">
            O aviso ficará ligado a <strong>{cliente?.nome}</strong> e aparecerá em
            <strong> Lembretes</strong> depois que a venda for finalizada.
          </div>

          <div className="grid grid-cols-2 gap-2 rounded-xl bg-slate-100 p-1">
            <button
              className={`rounded-lg px-3 py-2 text-sm font-semibold ${
                modo === "prazo" ? "bg-white text-teal-700 shadow-sm" : "text-slate-600"
              }`}
              onClick={() => {
                setModo("prazo");
                setErro("");
              }}
              type="button"
            >
              Prazo em dias
            </button>
            <button
              className={`rounded-lg px-3 py-2 text-sm font-semibold ${
                modo === "data" ? "bg-white text-teal-700 shadow-sm" : "text-slate-600"
              }`}
              onClick={() => {
                setModo("data");
                setErro("");
              }}
              type="button"
            >
              Data prevista
            </button>
          </div>

          {modo === "prazo" ? (
            <div className="space-y-3">
              <label className="block text-sm font-semibold text-slate-700" htmlFor="prazo-racao">
                Em quantos dias costuma acabar?
              </label>
              <div className="flex items-center gap-2">
                <input
                  autoFocus
                  className="h-11 w-28 rounded-lg border border-slate-300 px-3 text-center text-lg font-bold focus:border-teal-500 focus:ring-2 focus:ring-teal-200"
                  id="prazo-racao"
                  max="365"
                  min="1"
                  onChange={(event) => {
                    setPrazo(event.target.value);
                    setErro("");
                  }}
                  type="number"
                  value={prazo}
                />
                <span className="text-sm text-slate-600">dias após a compra</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {PRAZOS_RAPIDOS.map((dias) => (
                  <button
                    className={`rounded-full border px-3 py-1.5 text-xs font-semibold ${
                      String(dias) === String(prazo)
                        ? "border-teal-600 bg-teal-600 text-white"
                        : "border-slate-300 bg-white text-slate-600 hover:border-teal-400"
                    }`}
                    key={dias}
                    onClick={() => {
                      setPrazo(String(dias));
                      setErro("");
                    }}
                    type="button"
                  >
                    {dias} dias
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <label className="block text-sm font-semibold text-slate-700" htmlFor="data-racao">
                Data em que deve acabar
              </label>
              <input
                autoFocus
                className="h-11 w-full rounded-lg border border-slate-300 px-3 focus:border-teal-500 focus:ring-2 focus:ring-teal-200"
                id="data-racao"
                min={dataLocalParaISO(adicionarDiasDataLocal(1))}
                onChange={(event) => {
                  setDataPrevista(event.target.value);
                  setErro("");
                }}
                type="date"
                value={dataPrevista}
              />
            </div>
          )}

          {dataCalculada && (
            <div className="rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-700">
              Previsão registrada: <strong>{formatarDataFimRacao(dataCalculada)}</strong>
            </div>
          )}
          {erro && <p className="text-sm font-medium text-red-600">{erro}</p>}
        </div>

        <div className="flex flex-wrap justify-between gap-2 border-t border-slate-200 bg-slate-50 px-5 py-4">
          {temPrevisao ? (
            <button
              className="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold text-red-600 hover:bg-red-50"
              onClick={() =>
                onSalvar({
                  racao_data_prevista_fim: null,
                  racao_prazo_estimado_dias: null,
                })
              }
              type="button"
            >
              <Trash2 className="h-4 w-4" /> Remover aviso
            </button>
          ) : (
            <span />
          )}
          <div className="flex gap-2">
            <button
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-white"
              onClick={onClose}
              type="button"
            >
              Cancelar
            </button>
            <button
              className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-700"
              type="submit"
            >
              Salvar aviso
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
