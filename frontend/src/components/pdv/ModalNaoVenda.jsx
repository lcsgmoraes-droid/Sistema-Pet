import { BarChart3, ClipboardEdit, SearchX, X } from "lucide-react";
import { useState } from "react";

import NaoVendaRegistroForm from "./NaoVendaRegistroForm";
import NaoVendaRelatorio from "./NaoVendaRelatorio";

export default function ModalNaoVenda({ isOpen, onClose, clienteInicial }) {
  const [aba, setAba] = useState("registrar");

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-3">
      <div className="flex max-h-[94vh] w-full max-w-6xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-amber-100 p-2 text-amber-700">
              <SearchX className="h-6 w-6" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-900">Não venda e produto procurado</h2>
              <p className="text-sm text-slate-500">
                Registre rapidamente o que a loja deixou de vender e descubra os motivos.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
            title="Fechar"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="flex border-b border-slate-200 bg-slate-50 px-5">
          <button
            type="button"
            onClick={() => setAba("registrar")}
            className={`inline-flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-semibold ${
              aba === "registrar"
                ? "border-blue-600 text-blue-700"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            <ClipboardEdit className="h-4 w-4" /> Registrar agora
          </button>
          <button
            type="button"
            onClick={() => setAba("relatorio")}
            className={`inline-flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-semibold ${
              aba === "relatorio"
                ? "border-blue-600 text-blue-700"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            <BarChart3 className="h-4 w-4" /> Relatório
          </button>
        </div>

        <div className="flex-1 overflow-y-auto bg-slate-50/50 p-5">
          {aba === "registrar" ? (
            <NaoVendaRegistroForm clienteInicial={clienteInicial} onSaved={onClose} />
          ) : (
            <NaoVendaRelatorio />
          )}
        </div>
      </div>
    </div>
  );
}
