import { AlertTriangle, CheckCircle, Receipt, RefreshCw, Save, ShieldCheck } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { vetApi } from "../vetApi";

const STATUS_LABELS = {
  pending_configuration: "Configuracao pendente",
  validating: "Em homologacao",
  active: "Ativa",
  suspended: "Suspensa",
};

function errorMessage(error) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (detail?.message) {
    const fields = Array.isArray(detail.missing_fields) ? detail.missing_fields.join(", ") : "";
    return fields ? `${detail.message} Pendencias: ${fields}.` : detail.message;
  }
  return "Nao foi possivel atualizar a configuracao da NFS-e.";
}

function formFromConfig(config) {
  return {
    service_list_item: config?.service_list_item || "5.01",
    cnae_code: config?.cnae_code || "",
    iss_rate: config?.iss_rate ?? "",
    iss_withheld: Boolean(config?.iss_withheld),
    operation_nature: config?.operation_nature || "1",
    special_tax_regime: config?.special_tax_regime || "",
    simple_national: config?.simple_national ?? true,
    cultural_incentive: Boolean(config?.cultural_incentive),
  };
}

export default function NfseConfigSection() {
  const [config, setConfig] = useState(null);
  const [form, setForm] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await vetApi.obterConfigNfse();
      setConfig(response.data);
      setForm(formFromConfig(response.data));
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  function change(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function save(prevalidate = false) {
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const response = await vetApi.atualizarConfigNfse({
        ...form,
        environment: "homologacao",
        service_list_item: form.service_list_item.trim() || null,
        cnae_code: form.cnae_code.trim() || null,
        iss_rate: form.iss_rate === "" ? null : Number(String(form.iss_rate).replace(",", ".")),
        special_tax_regime: form.special_tax_regime || null,
      });
      let updated = response.data;
      if (prevalidate) {
        updated = (await vetApi.preValidarConfigNfse()).data;
      }
      setConfig(updated);
      setForm(formFromConfig(updated));
      setMessage(prevalidate ? "Configuracao pronta para homologacao." : "Configuracao salva.");
    } catch (requestError) {
      setError(errorMessage(requestError));
      try {
        const refreshed = (await vetApi.obterConfigNfse()).data;
        setConfig(refreshed);
        setForm(formFromConfig(refreshed));
      } catch {
        // Mantem a mensagem original e o formulario atual.
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="bg-white rounded-xl border border-gray-200 shadow-sm">
      <header className="flex flex-wrap items-center justify-between gap-3 p-5 border-b border-gray-100">
        <div className="flex items-center gap-3">
          <Receipt size={22} className="text-emerald-600" />
          <div>
            <h2 className="text-lg font-semibold text-gray-900">NFS-e integrada</h2>
            <p className="text-xs text-gray-500">Focus NFe + Simpliss de Presidente Prudente</p>
          </div>
        </div>
        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">
          {STATUS_LABELS[config?.status] || "Carregando"}
        </span>
      </header>

      <div className="p-5 space-y-5">
        <div className="flex gap-3 rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800">
          <ShieldCheck size={20} className="shrink-0" />
          <p>
            Esta etapa usa somente homologacao. Certificado, senha e token nao devem ser digitados
            nesta tela nem enviados por chat.
          </p>
        </div>

        {loading || !form ? (
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <RefreshCw size={16} className="animate-spin" /> Carregando configuracao fiscal...
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <label className="block">
                <span className="block text-xs font-medium text-gray-600 mb-1">
                  Item da lista de servicos
                </span>
                <input
                  value={form.service_list_item}
                  onChange={(event) => change("service_list_item", event.target.value)}
                  placeholder="Ex.: 5.01"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
                />
                <span className="mt-1 block text-xs text-gray-500">
                  Confirmar com a contabilidade antes da primeira nota.
                </span>
              </label>

              <label className="block">
                <span className="block text-xs font-medium text-gray-600 mb-1">
                  Aliquota de ISS (%)
                </span>
                <input
                  type="number"
                  min="0"
                  max="100"
                  step="0.01"
                  value={form.iss_rate}
                  onChange={(event) => change("iss_rate", event.target.value)}
                  placeholder="Ex.: 2,00"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
                />
              </label>

              <label className="block">
                <span className="block text-xs font-medium text-gray-600 mb-1">CNAE</span>
                <input
                  value={form.cnae_code}
                  onChange={(event) => change("cnae_code", event.target.value)}
                  placeholder="Opcional para o municipio"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
                />
              </label>

              <label className="block">
                <span className="block text-xs font-medium text-gray-600 mb-1">
                  Regime especial de tributacao
                </span>
                <select
                  value={form.special_tax_regime}
                  onChange={(event) => change("special_tax_regime", event.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
                >
                  <option value="">Nao informado</option>
                  <option value="5">MEI - Simples Nacional</option>
                  <option value="6">ME/EPP - Simples Nacional</option>
                  <option value="3">Sociedade de profissionais</option>
                  <option value="1">Microempresa municipal</option>
                </select>
              </label>
            </div>

            <div className="flex flex-wrap gap-5 text-sm text-gray-700">
              <label className="inline-flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={form.simple_national}
                  onChange={(event) => change("simple_national", event.target.checked)}
                  className="h-4 w-4 accent-emerald-600"
                />
                Optante pelo Simples Nacional
              </label>
              <label className="inline-flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={form.iss_withheld}
                  onChange={(event) => change("iss_withheld", event.target.checked)}
                  className="h-4 w-4 accent-emerald-600"
                />
                ISS retido pelo tomador
              </label>
            </div>

            {config?.missing_fields?.length > 0 && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
                <div className="flex items-center gap-2 text-sm font-semibold text-amber-800">
                  <AlertTriangle size={17} /> Pendencias para homologar
                </div>
                <ul className="mt-2 list-disc pl-5 text-sm text-amber-800">
                  {config.missing_fields.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            )}

            {config?.ready_for_homologation && (
              <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">
                <CheckCircle size={18} /> Dados completos para emitir a nota de homologacao.
              </div>
            )}

            {error && <p className="text-sm text-red-600">{error}</p>}
            {message && <p className="text-sm text-emerald-700">{message}</p>}

            <div className="flex flex-wrap justify-end gap-2">
              <button
                type="button"
                onClick={() => void load()}
                disabled={saving}
                className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                <RefreshCw size={15} /> Atualizar status
              </button>
              <button
                type="button"
                onClick={() => void save(false)}
                disabled={saving}
                className="inline-flex items-center gap-2 rounded-lg border border-emerald-300 px-4 py-2 text-sm text-emerald-700 hover:bg-emerald-50 disabled:opacity-50"
              >
                <Save size={15} /> Salvar
              </button>
              <button
                type="button"
                onClick={() => void save(true)}
                disabled={saving}
                className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
              >
                {saving ? "Validando..." : "Validar para homologacao"}
              </button>
            </div>
          </>
        )}
      </div>
    </section>
  );
}
