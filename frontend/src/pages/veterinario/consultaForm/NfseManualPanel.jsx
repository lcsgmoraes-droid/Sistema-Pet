import { useCallback, useEffect, useState } from "react";
import {
  CheckCircle2,
  ClipboardCopy,
  Download,
  ExternalLink,
  FileText,
  Loader2,
  Upload,
} from "lucide-react";
import toast from "react-hot-toast";
import { Link } from "react-router-dom";
import { baixarBlob, nfseManualApi } from "../../../services/nfseManualApi";

const STATUS = {
  draft: { label: "Pendente de emissão", css: "bg-amber-100 text-amber-800" },
  issued: { label: "Emitida", css: "bg-emerald-100 text-emerald-800" },
  cancelled: { label: "Cancelada", css: "bg-gray-200 text-gray-700" },
};

function mensagemErro(error, fallback) {
  return error.response?.data?.detail || fallback;
}

export default function NfseManualPanel({ consultaId }) {
  const [documento, setDocumento] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [processando, setProcessando] = useState(false);
  const [rascunho, setRascunho] = useState({ service_amount: "", description: "" });
  const [registro, setRegistro] = useState({ invoice_number: "", verification_code: "" });

  const carregar = useCallback(async () => {
    if (!consultaId) return;
    setCarregando(true);
    try {
      const response = await nfseManualApi.obterPorConsulta(consultaId);
      setDocumento(response.data.document);
    } catch (error) {
      toast.error(mensagemErro(error, "Não foi possível consultar a NFS-e."));
    } finally {
      setCarregando(false);
    }
  }, [consultaId]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  useEffect(() => {
    if (!documento) return;
    setRascunho({
      service_amount: documento.service_amount ?? "",
      description: documento.description || "",
    });
    setRegistro({
      invoice_number: documento.invoice_number || "",
      verification_code: documento.verification_code || "",
    });
  }, [documento]);

  async function executar(acao, sucesso) {
    setProcessando(true);
    try {
      const response = await acao();
      if (response?.data) setDocumento(response.data);
      if (sucesso) toast.success(sucesso);
    } catch (error) {
      toast.error(mensagemErro(error, "Não foi possível concluir a ação."));
    } finally {
      setProcessando(false);
    }
  }

  function preparar() {
    executar(() => nfseManualApi.prepararConsulta(consultaId), "Dados da NFS-e preparados.");
  }

  function salvarRascunho() {
    executar(
      () =>
        nfseManualApi.atualizarRascunho(documento.id, {
          service_amount: Number(rascunho.service_amount),
          description: rascunho.description,
        }),
      "Rascunho atualizado.",
    );
  }

  function recarregarCadastros() {
    executar(
      () =>
        nfseManualApi.prepararConsulta(consultaId, {
          service_amount: Number(rascunho.service_amount),
          description: rascunho.description,
        }),
      "Dados cadastrais e fiscais atualizados no rascunho.",
    );
  }

  function registrarEmitida() {
    executar(
      () => nfseManualApi.registrarEmitida(documento.id, registro),
      "NFS-e registrada no CorePet.",
    );
  }

  async function copiarDados() {
    try {
      await navigator.clipboard.writeText(documento.copy_text);
      toast.success("Dados copiados. Agora é só colar no portal da Prefeitura.");
    } catch {
      toast.error("O navegador não permitiu copiar os dados.");
    }
  }

  async function enviarAnexo(tipo, event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    await executar(
      () => nfseManualApi.enviarAnexo(documento.id, tipo, file),
      tipo === "xml" ? "XML anexado e dados da nota atualizados." : "PDF anexado à nota.",
    );
  }

  async function baixarAnexo(tipo) {
    setProcessando(true);
    try {
      const response = await nfseManualApi.baixarAnexo(documento.id, tipo);
      baixarBlob(response, `nfse-${documento.invoice_number || documento.id}.${tipo}`);
    } catch (error) {
      toast.error(mensagemErro(error, "Não foi possível baixar o anexo."));
    } finally {
      setProcessando(false);
    }
  }

  if (!consultaId) return null;

  if (carregando) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-5 text-sm text-slate-500">
        <Loader2 className="mr-2 inline h-4 w-4 animate-spin" /> Carregando NFS-e...
      </div>
    );
  }

  if (!documento) {
    return (
      <section className="rounded-xl border border-blue-200 bg-blue-50 p-5 text-left">
        <div className="flex items-start gap-3">
          <FileText className="mt-0.5 h-6 w-6 text-blue-700" />
          <div className="flex-1">
            <h3 className="font-semibold text-blue-950">Emitir NFS-e pela Prefeitura</h3>
            <p className="mt-1 text-sm text-blue-800">
              O CorePet prepara os dados da consulta. A emissão continua no Simpliss, sem guardar
              senha ou certificado da Prefeitura.
            </p>
            <button
              type="button"
              onClick={preparar}
              disabled={processando}
              className="mt-4 rounded-lg bg-blue-700 px-4 py-2 text-sm font-medium text-white hover:bg-blue-800 disabled:opacity-50"
            >
              {processando ? "Preparando..." : "Preparar dados para emissão"}
            </button>
          </div>
        </div>
      </section>
    );
  }

  const status = STATUS[documento.status] || STATUS.draft;
  const faltantes = documento.snapshot?.missing_fields || [];
  const emitida = documento.status === "issued";
  const portalDisponivel = Boolean(documento.portal_url);

  return (
    <section className="space-y-4 rounded-xl border border-slate-200 bg-white p-5 text-left shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="flex items-center gap-2 font-semibold text-slate-900">
            <FileText className="h-5 w-5 text-blue-700" /> NFS-e manual assistida
          </h3>
          <p className="mt-1 text-sm text-slate-500">Referência {documento.reference}</p>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${status.css}`}>
          {status.label}
        </span>
      </div>

      {faltantes.length > 0 && documento.status === "draft" && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          <p className="font-medium">Complete estes dados antes de emitir:</p>
          <p className="mt-1">{faltantes.join(", ")}.</p>
          <Link to="/configuracoes/fiscal" className="mt-2 inline-block font-semibold underline">
            Abrir configuração fiscal
          </Link>
        </div>
      )}

      {documento.status === "draft" && (
        <div className="grid gap-3 md:grid-cols-[160px_1fr]">
          <label className="text-sm font-medium text-slate-700">
            Valor dos serviços
            <input
              type="number"
              min="0.01"
              step="0.01"
              value={rascunho.service_amount}
              onChange={(event) =>
                setRascunho((atual) => ({ ...atual, service_amount: event.target.value }))
              }
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            />
          </label>
          <label className="text-sm font-medium text-slate-700">
            Descrição do serviço
            <textarea
              rows="3"
              value={rascunho.description}
              onChange={(event) =>
                setRascunho((atual) => ({ ...atual, description: event.target.value }))
              }
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            />
          </label>
          <div className="md:col-start-2">
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={salvarRascunho}
                disabled={processando}
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium hover:bg-slate-50 disabled:opacity-50"
              >
                Salvar ajustes
              </button>
              <button
                type="button"
                onClick={recarregarCadastros}
                disabled={processando}
                className="rounded-lg px-3 py-2 text-sm font-medium text-blue-700 hover:bg-blue-50 disabled:opacity-50"
              >
                Recarregar cadastros
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={copiarDados}
          className="inline-flex items-center gap-2 rounded-lg bg-blue-700 px-3 py-2 text-sm font-medium text-white hover:bg-blue-800"
        >
          <ClipboardCopy className="h-4 w-4" /> Copiar dados
        </button>
        {portalDisponivel ? (
          <a
            href={documento.portal_url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 rounded-lg border border-blue-300 px-3 py-2 text-sm font-medium text-blue-800 hover:bg-blue-50"
          >
            <ExternalLink className="h-4 w-4" /> Abrir portal de NFS-e
          </a>
        ) : (
          <Link
            to="/configuracoes/fiscal"
            className="inline-flex items-center gap-2 rounded-lg border border-amber-300 px-3 py-2 text-sm font-medium text-amber-800 hover:bg-amber-50"
          >
            Configurar portal de NFS-e
          </Link>
        )}
      </div>

      {!emitida && documento.status !== "cancelled" && (
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <p className="text-sm font-semibold text-slate-800">Depois de emitir na Prefeitura</p>
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            <input
              value={registro.invoice_number}
              onChange={(event) =>
                setRegistro((atual) => ({ ...atual, invoice_number: event.target.value }))
              }
              placeholder="Número da NFS-e"
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
            <input
              value={registro.verification_code}
              onChange={(event) =>
                setRegistro((atual) => ({ ...atual, verification_code: event.target.value }))
              }
              placeholder="Código de verificação (opcional)"
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
          <button
            type="button"
            onClick={registrarEmitida}
            disabled={processando || !registro.invoice_number.trim()}
            className="mt-3 inline-flex items-center gap-2 rounded-lg bg-emerald-700 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-800 disabled:opacity-50"
          >
            <CheckCircle2 className="h-4 w-4" /> Registrar como emitida
          </button>
          <p className="mt-3 text-xs text-slate-500">
            Se você importar o XML, o CorePet tenta preencher o número, o código e o valor
            automaticamente.
          </p>
        </div>
      )}

      {emitida && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900">
          <span className="font-semibold">NFS-e {documento.invoice_number}</span>
          {documento.verification_code && ` · Código ${documento.verification_code}`}
        </div>
      )}

      <div className="flex flex-wrap gap-2 border-t border-slate-100 pt-4">
        <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium hover:bg-slate-50">
          <Upload className="h-4 w-4" /> Anexar XML
          <input
            type="file"
            accept=".xml,text/xml,application/xml"
            className="hidden"
            onChange={(event) => enviarAnexo("xml", event)}
          />
        </label>
        <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium hover:bg-slate-50">
          <Upload className="h-4 w-4" /> Anexar PDF
          <input
            type="file"
            accept=".pdf,application/pdf"
            className="hidden"
            onChange={(event) => enviarAnexo("pdf", event)}
          />
        </label>
        {documento.has_xml && (
          <button
            type="button"
            onClick={() => baixarAnexo("xml")}
            className="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-blue-700 hover:bg-blue-50"
          >
            <Download className="h-4 w-4" /> Baixar XML
          </button>
        )}
        {documento.has_pdf && (
          <button
            type="button"
            onClick={() => baixarAnexo("pdf")}
            className="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-blue-700 hover:bg-blue-50"
          >
            <Download className="h-4 w-4" /> Baixar PDF
          </button>
        )}
      </div>
    </section>
  );
}
