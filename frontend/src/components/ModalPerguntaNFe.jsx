import { useState } from "react";
import { CheckCircle, FileText, Printer } from "lucide-react";
import { useDadosCupomEmpresa } from "../hooks/useDadosCupomEmpresa";
import { usePersistentBooleanState } from "../hooks/usePersistentBooleanState";
import { concluirVendaComCupom } from "../utils/pdvCupomFinalizacao";
import { ehVendaCrediario } from "../utils/pdvReceipt";
import { CupomImpressao } from "./ImprimirCupom";

const IMPRESSAO_CUPOM_STORAGE_KEY = "pdv_imprimir_cupom_ao_finalizar";
const IMPRESSAO_CREDIARIO_STORAGE_KEY = "pdv_imprimir_crediario_ao_finalizar";

export default function ModalPerguntaNFe({
  cliente,
  erro = "",
  loading = false,
  onConfirmar,
  onEmitir,
  venda,
}) {
  const crediario = ehVendaCrediario(venda);
  const [imprimirCupom, setImprimirCupom] = usePersistentBooleanState(
    crediario ? IMPRESSAO_CREDIARIO_STORAGE_KEY : IMPRESSAO_CUPOM_STORAGE_KEY,
    crediario,
  );
  const [tipoNota, setTipoNota] = useState("nfce");
  const { carregandoEmpresa, dadosEmpresa } = useDadosCupomEmpresa();
  const clienteIdentificado = Boolean(cliente?.cpf || cliente?.cnpj);

  const handleConcluirSemNota = () => {
    concluirVendaComCupom({
      imprimirCupom,
      onConcluir: onConfirmar,
    });
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        <div className="p-6">
          <div className="flex items-center space-x-3 mb-4">
            <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
              <CheckCircle className="w-6 h-6 text-green-600" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-gray-900">Venda Finalizada!</h3>
              <p className="text-sm text-gray-500">
                Deseja emitir nota fiscal ou concluir com recibo?
              </p>
            </div>
          </div>

          {erro && (
            <div className="mb-4 whitespace-pre-line rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {erro}
            </div>
          )}

          <div className="space-y-3">
            <fieldset>
              <legend className="mb-2 text-sm font-semibold text-gray-800">Documento fiscal</legend>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  aria-pressed={tipoNota === "nfce"}
                  onClick={() => setTipoNota("nfce")}
                  disabled={loading}
                  className={`rounded-lg border px-3 py-3 text-left transition-colors disabled:opacity-50 ${
                    tipoNota === "nfce"
                      ? "border-green-600 bg-green-50 text-green-900"
                      : "border-gray-200 bg-white text-gray-700 hover:bg-gray-50"
                  }`}
                >
                  <span className="block text-sm font-bold">NFC-e · modelo 65</span>
                  <span className="mt-1 block text-xs">Padrão para venda no PDV</span>
                </button>
                <button
                  type="button"
                  aria-pressed={tipoNota === "nfe"}
                  onClick={() => setTipoNota("nfe")}
                  disabled={loading || !clienteIdentificado}
                  className={`rounded-lg border px-3 py-3 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
                    tipoNota === "nfe"
                      ? "border-blue-600 bg-blue-50 text-blue-900"
                      : "border-gray-200 bg-white text-gray-700 hover:bg-gray-50"
                  }`}
                >
                  <span className="block text-sm font-bold">NF-e · modelo 55</span>
                  <span className="mt-1 block text-xs">Escolha quando a venda exigir NF-e</span>
                </button>
              </div>
            </fieldset>

            <p className="rounded-lg bg-gray-50 px-3 py-2 text-xs text-gray-600">
              {tipoNota === "nfce"
                ? "Use para a venda presencial comum ao consumidor final."
                : "Use para vendas com entrega ou transporte, interestaduais, ou quando o cliente solicitar NF-e."}
              {!clienteIdentificado
                ? " Para emitir NF-e, selecione um cliente com CPF ou CNPJ."
                : ""}
            </p>

            <button
              type="button"
              onClick={() => onEmitir(tipoNota)}
              disabled={loading || (tipoNota === "nfe" && !clienteIdentificado)}
              className={`flex w-full items-center justify-center space-x-2 rounded-lg px-4 py-3 font-medium text-white transition-colors disabled:opacity-50 ${
                tipoNota === "nfce"
                  ? "bg-green-600 hover:bg-green-700"
                  : "bg-blue-600 hover:bg-blue-700"
              }`}
            >
              <FileText className="h-5 w-5" />
              <span>Emitir {tipoNota === "nfce" ? "NFC-e" : "NF-e"}</span>
            </button>

            <button
              onClick={handleConcluirSemNota}
              disabled={loading || (imprimirCupom && carregandoEmpresa)}
              className="flex w-full items-center justify-center space-x-2 rounded-lg bg-gray-100 px-4 py-3 font-medium text-gray-700 transition-colors hover:bg-gray-200 disabled:opacity-50"
            >
              <Printer className="h-5 w-5" />
              <span>
                {imprimirCupom
                  ? crediario
                    ? "Imprimir 2 vias e concluir"
                    : "Imprimir recibo e concluir"
                  : "Concluir sem nota fiscal"}
              </span>
            </button>

            <label
              className="flex cursor-pointer items-center justify-center gap-1.5 px-1 text-[11px] text-gray-400"
              title="Esta preferência fica salva neste computador"
            >
              <input
                type="checkbox"
                checked={imprimirCupom}
                onChange={(event) => setImprimirCupom(event.target.checked)}
                disabled={loading}
                className="h-3.5 w-3.5 rounded border-gray-300 text-gray-500 focus:ring-1 focus:ring-gray-400 disabled:opacity-50"
              />
              <span>
                {crediario
                  ? "Imprimir comprovante de crediário em 2 vias"
                  : "Imprimir recibo do PDV ao concluir"}
              </span>
            </label>
          </div>

          <CupomImpressao empresa={dadosEmpresa} portal venda={venda} />
        </div>
      </div>
    </div>
  );
}
