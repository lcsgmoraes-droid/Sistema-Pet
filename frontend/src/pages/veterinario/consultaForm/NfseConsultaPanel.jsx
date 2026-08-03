import { AlertTriangle, ExternalLink, FileCheck2, Receipt, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import CurrencyInput from "../../../components/CurrencyInput";
import { formatMoneyBRL } from "../../../utils/formatters";
import { vetApi } from "../vetApi";

const STATUS_LABELS = {
  sending: "Enviando",
  processing: "Processando na prefeitura",
  authorized: "Autorizada",
  cancelled: "Cancelada",
  authorization_error: "Erro na autorizacao",
  cancellation_error: "Erro no cancelamento",
  submission_error: "Falha no envio",
};

function errorMessage(error) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (detail?.message) {
    const fields = Array.isArray(detail.missing_fields) ? detail.missing_fields.join(", ") : "";
    return fields ? `${detail.message} Pendencias: ${fields}.` : detail.message;
  }
  return "Nao foi possivel consultar a NFS-e.";
}

export default function NfseConsultaPanel({ consultaId }) {
  const navigate = useNavigate();
  const [config, setConfig] = useState(null);
  const [document, setDocument] = useState(null);
  const [amount, setAmount] = useState(0);
  const [description, setDescription] = useState(
    `Atendimento veterinario - consulta ${consultaId}`,
  );
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!consultaId) return;
    setLoading(true);
    setError("");
    try {
      const [configResponse, documentResponse, proceduresResponse] = await Promise.all([
        vetApi.obterConfigNfse(),
        vetApi.obterNfseConsulta(consultaId),
        vetApi.listarProcedimentosConsulta(consultaId),
      ]);
      setConfig(configResponse.data);
      setDocument(documentResponse.data?.document || null);
      const procedures = Array.isArray(proceduresResponse.data) ? proceduresResponse.data : [];
      const total = procedures.reduce((sum, item) => sum + Number(item?.valor || 0), 0);
      setAmount(total);
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }, [consultaId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function issue() {
    setWorking(true);
    setError("");
    try {
      const response = await vetApi.emitirNfseConsulta(consultaId, {
        ...(amount > 0 ? { service_amount: amount } : {}),
        description: description.trim(),
      });
      setDocument(response.data);
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setWorking(false);
    }
  }

  async function sync() {
    if (!document?.id) return;
    setWorking(true);
    setError("");
    try {
      const response = await vetApi.sincronizarNfse(document.id);
      setDocument(response.data);
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setWorking(false);
    }
  }

  if (!consultaId) return null;

  return (
    <section className="rounded-xl border border-emerald-200 bg-white text-left shadow-sm">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-emerald-100 p-4">
        <div className="flex items-center gap-2">
          <Receipt size={20} className="text-emerald-600" />
          <div>
            <h2 className="font-semibold text-gray-900">Nota fiscal de servico</h2>
            <p className="text-xs text-gray-500">Emissao integrada ao prontuario finalizado</p>
          </div>
        </div>
        {document && (
          <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-800">
            {STATUS_LABELS[document.status] || document.status}
          </span>
        )}
      </header>

      <div className="space-y-4 p-4">
        {loading ? (
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <RefreshCw size={16} className="animate-spin" /> Consultando NFS-e...
          </div>
        ) : document ? (
          <>
            <div className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
              <div>
                <span className="block text-xs text-gray-500">Valor</span>
                <strong>{formatMoneyBRL(document.service_amount)}</strong>
              </div>
              <div>
                <span className="block text-xs text-gray-500">Numero da NFS-e</span>
                <strong>{document.invoice_number || "Aguardando autorizacao"}</strong>
              </div>
              {document.verification_code && (
                <div>
                  <span className="block text-xs text-gray-500">Codigo de verificacao</span>
                  <strong>{document.verification_code}</strong>
                </div>
              )}
              <div>
                <span className="block text-xs text-gray-500">Ambiente</span>
                <strong>{document.environment === "producao" ? "Producao" : "Homologacao"}</strong>
              </div>
            </div>

            {document.error_message && (
              <div className="flex gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                <AlertTriangle size={17} className="shrink-0" /> {document.error_message}
              </div>
            )}

            <div className="flex flex-wrap justify-end gap-2">
              {document.pdf_url && (
                <a
                  href={document.pdf_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
                >
                  PDF <ExternalLink size={14} />
                </a>
              )}
              {document.xml_url && (
                <a
                  href={document.xml_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
                >
                  XML <ExternalLink size={14} />
                </a>
              )}
              <button
                type="button"
                onClick={() => void sync()}
                disabled={working}
                className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm text-white hover:bg-emerald-700 disabled:opacity-50"
              >
                <RefreshCw size={15} className={working ? "animate-spin" : ""} />
                Sincronizar
              </button>
            </div>
          </>
        ) : config?.ready_for_homologation ? (
          <>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <label className="block">
                <span className="mb-1 block text-xs font-medium text-gray-600">
                  Valor dos servicos
                </span>
                <CurrencyInput
                  value={amount}
                  onChange={setAmount}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
                />
              </label>
              <label className="block sm:col-span-2">
                <span className="mb-1 block text-xs font-medium text-gray-600">Descricao</span>
                <textarea
                  rows="3"
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
                />
              </label>
            </div>
            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => void issue()}
                disabled={working || amount <= 0 || description.trim().length < 3}
                className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
              >
                <FileCheck2 size={16} />
                {working ? "Emitindo..." : "Emitir NFS-e de homologacao"}
              </button>
            </div>
          </>
        ) : (
          <div className="space-y-3">
            <div className="flex gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
              <AlertTriangle size={17} className="shrink-0" />
              Complete e valide a configuracao fiscal antes de emitir a nota.
            </div>
            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => navigate("/veterinario/configuracoes")}
                className="rounded-lg border border-emerald-300 px-4 py-2 text-sm text-emerald-700 hover:bg-emerald-50"
              >
                Abrir configuracao de NFS-e
              </button>
            </div>
          </div>
        )}

        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>
    </section>
  );
}
