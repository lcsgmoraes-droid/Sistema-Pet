import { useCallback, useEffect, useMemo, useState } from "react";
import { Download, ExternalLink, FileText, Loader2, RefreshCw, Stethoscope } from "lucide-react";
import toast from "react-hot-toast";
import { Link } from "react-router-dom";
import { baixarBlob, nfseManualApi } from "../services/nfseManualApi";

const FILTROS = [
  { value: "", label: "Todas" },
  { value: "draft", label: "Pendentes" },
  { value: "issued", label: "Emitidas" },
  { value: "cancelled", label: "Canceladas" },
];

const STATUS = {
  draft: { label: "Pendente", css: "bg-amber-100 text-amber-800" },
  issued: { label: "Emitida", css: "bg-emerald-100 text-emerald-800" },
  cancelled: { label: "Cancelada", css: "bg-gray-200 text-gray-700" },
};

function moeda(valor) {
  return Number(valor || 0).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
}

function dataHora(valor) {
  return valor ? new Date(valor).toLocaleString("pt-BR") : "—";
}

function detalheErro(error, fallback) {
  return error.response?.data?.detail || fallback;
}

export default function NfseManual() {
  const [documentos, setDocumentos] = useState([]);
  const [filtro, setFiltro] = useState("");
  const [carregando, setCarregando] = useState(true);
  const [processandoId, setProcessandoId] = useState(null);

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      const response = await nfseManualApi.listar(filtro);
      setDocumentos(response.data);
    } catch (error) {
      toast.error(detalheErro(error, "Não foi possível carregar as NFS-e."));
    } finally {
      setCarregando(false);
    }
  }, [filtro]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  const total = useMemo(
    () => documentos.reduce((soma, documento) => soma + Number(documento.service_amount || 0), 0),
    [documentos],
  );

  async function baixar(documento, tipo) {
    setProcessandoId(documento.id);
    try {
      const response = await nfseManualApi.baixarAnexo(documento.id, tipo);
      baixarBlob(response, `nfse-${documento.invoice_number || documento.id}.${tipo}`);
    } catch (error) {
      toast.error(detalheErro(error, "Não foi possível baixar o anexo."));
    } finally {
      setProcessandoId(null);
    }
  }

  async function cancelar(documento) {
    const motivo = window.prompt(
      "Informe o motivo. Use esta ação somente depois de cancelar a NFS-e na Prefeitura.",
    );
    if (!motivo) return;
    if (!window.confirm("Você confirma que a nota já foi cancelada no portal da Prefeitura?")) {
      return;
    }
    setProcessandoId(documento.id);
    try {
      await nfseManualApi.marcarCancelada(documento.id, { confirm: true, reason: motivo });
      toast.success("NFS-e marcada como cancelada.");
      await carregar();
    } catch (error) {
      toast.error(detalheErro(error, "Não foi possível atualizar a nota."));
    } finally {
      setProcessandoId(null);
    }
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold text-gray-900">
            <FileText className="h-7 w-7 text-blue-700" /> NFS-e de serviços
          </h1>
          <p className="mt-1 max-w-3xl text-sm text-gray-600">
            Acompanhe as notas preparadas no CorePet e emitidas manualmente no Simpliss. O CorePet
            não armazena a senha da Prefeitura.
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            to="/configuracoes/fiscal"
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium hover:bg-gray-50"
          >
            Configuração fiscal
          </Link>
          <button
            type="button"
            onClick={carregar}
            disabled={carregando}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-700 px-3 py-2 text-sm font-medium text-white hover:bg-blue-800 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${carregando ? "animate-spin" : ""}`} /> Atualizar
          </button>
        </div>
      </header>

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-gray-200 bg-white p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Exibidas</p>
          <p className="mt-1 text-2xl font-bold text-gray-900">{documentos.length}</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-4 sm:col-span-2 lg:col-span-3">
          <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
            Valor dos serviços exibidos
          </p>
          <p className="mt-1 text-2xl font-bold text-gray-900">{moeda(total)}</p>
        </div>
      </section>

      <nav className="flex flex-wrap gap-2" aria-label="Filtrar NFS-e">
        {FILTROS.map((item) => (
          <button
            key={item.value || "all"}
            type="button"
            onClick={() => setFiltro(item.value)}
            className={`rounded-full px-4 py-2 text-sm font-medium ${
              filtro === item.value
                ? "bg-blue-700 text-white"
                : "border border-gray-300 bg-white text-gray-700 hover:bg-gray-50"
            }`}
          >
            {item.label}
          </button>
        ))}
      </nav>

      {carregando ? (
        <div className="rounded-xl border border-gray-200 bg-white p-12 text-center text-gray-500">
          <Loader2 className="mx-auto mb-2 h-6 w-6 animate-spin" /> Carregando notas...
        </div>
      ) : documentos.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-300 bg-white p-12 text-center">
          <FileText className="mx-auto h-9 w-9 text-gray-400" />
          <p className="mt-3 font-medium text-gray-800">Nenhuma NFS-e neste filtro</p>
          <p className="mt-1 text-sm text-gray-500">
            A primeira pendência aparece quando os dados são preparados numa consulta finalizada.
          </p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50 text-left text-xs uppercase tracking-wide text-gray-500">
                <tr>
                  <th className="px-4 py-3">Situação</th>
                  <th className="px-4 py-3">Cliente / serviço</th>
                  <th className="px-4 py-3">NFS-e</th>
                  <th className="px-4 py-3">Valor</th>
                  <th className="px-4 py-3">Atualização</th>
                  <th className="px-4 py-3 text-right">Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {documentos.map((documento) => {
                  const status = STATUS[documento.status] || STATUS.draft;
                  return (
                    <tr key={documento.id} className="align-top hover:bg-gray-50">
                      <td className="px-4 py-4">
                        <span
                          className={`rounded-full px-2.5 py-1 text-xs font-semibold ${status.css}`}
                        >
                          {status.label}
                        </span>
                      </td>
                      <td className="max-w-md px-4 py-4">
                        <p className="font-medium text-gray-900">
                          {documento.customer_name || "Cliente"}
                        </p>
                        <p className="mt-1 line-clamp-2 text-gray-500">{documento.description}</p>
                      </td>
                      <td className="px-4 py-4">
                        <p className="font-medium text-gray-900">
                          {documento.invoice_number || "—"}
                        </p>
                        {documento.verification_code && (
                          <p className="mt-1 text-xs text-gray-500">
                            Cód. {documento.verification_code}
                          </p>
                        )}
                      </td>
                      <td className="whitespace-nowrap px-4 py-4 font-medium text-gray-900">
                        {moeda(documento.service_amount)}
                      </td>
                      <td className="whitespace-nowrap px-4 py-4 text-gray-600">
                        {dataHora(documento.issued_at || documento.updated_at)}
                      </td>
                      <td className="px-4 py-4">
                        <div className="flex min-w-max justify-end gap-1">
                          {documento.consultation_id && (
                            <Link
                              to={`/veterinario/consultas/${documento.consultation_id}`}
                              title="Abrir consulta"
                              className="rounded-lg p-2 text-blue-700 hover:bg-blue-50"
                            >
                              <Stethoscope className="h-4 w-4" />
                            </Link>
                          )}
                          {documento.portal_url && (
                            <a
                              href={documento.portal_url}
                              target="_blank"
                              rel="noreferrer"
                              title="Abrir portal de NFS-e"
                              className="rounded-lg p-2 text-blue-700 hover:bg-blue-50"
                            >
                              <ExternalLink className="h-4 w-4" />
                            </a>
                          )}
                          {documento.has_xml && (
                            <button
                              type="button"
                              onClick={() => baixar(documento, "xml")}
                              title="Baixar XML"
                              className="rounded-lg p-2 text-gray-700 hover:bg-gray-100"
                            >
                              <Download className="h-4 w-4" />
                            </button>
                          )}
                          {documento.has_pdf && (
                            <button
                              type="button"
                              onClick={() => baixar(documento, "pdf")}
                              title="Baixar PDF"
                              className="rounded-lg p-2 text-red-700 hover:bg-red-50"
                            >
                              <Download className="h-4 w-4" />
                            </button>
                          )}
                          {documento.status === "issued" && (
                            <button
                              type="button"
                              onClick={() => cancelar(documento)}
                              disabled={processandoId === documento.id}
                              className="rounded-lg px-2 py-1 text-xs font-medium text-red-700 hover:bg-red-50 disabled:opacity-50"
                            >
                              Marcar cancelada
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
