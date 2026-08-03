import {
  AlertTriangle,
  CheckCircle,
  ExternalLink,
  KeyRound,
  Receipt,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { vetApi } from "../vetApi";

const STATUS_LABELS = {
  pending_configuration: "Configuração pendente",
  validating: "Em homologação",
  active: "Ativa",
  suspended: "Suspensa",
};

function errorMessage(error) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (detail?.message) {
    const fields = Array.isArray(detail.missing_fields) ? detail.missing_fields.join(", ") : "";
    return fields ? `${detail.message} Pendências: ${fields}.` : detail.message;
  }
  return "Não foi possível atualizar a configuração da NFS-e.";
}

function StatusItem({ ok, children }) {
  return (
    <div className="flex items-start gap-2 text-sm text-gray-700">
      {ok ? (
        <CheckCircle size={17} className="mt-0.5 shrink-0 text-emerald-600" />
      ) : (
        <AlertTriangle size={17} className="mt-0.5 shrink-0 text-amber-600" />
      )}
      <span>{children}</span>
    </div>
  );
}

export default function NfseConfigSection() {
  const [config, setConfig] = useState(null);
  const [municipalLogin, setMunicipalLogin] = useState("");
  const [municipalPassword, setMunicipalPassword] = useState("");
  const [focusMasterToken, setFocusMasterToken] = useState("");
  const [focusHomologationToken, setFocusHomologationToken] = useState("");
  const [focusProductionToken, setFocusProductionToken] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setConfig((await vetApi.obterConfigNfse()).data);
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function run(action, successMessage) {
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const response = await action();
      setConfig(response.data);
      setMessage(successMessage);
      return true;
    } catch (requestError) {
      setError(errorMessage(requestError));
      return false;
    } finally {
      setSaving(false);
    }
  }

  async function saveMunicipalCredentials() {
    const saved = await run(
      () =>
        vetApi.salvarCredenciaisMunicipaisNfse({
          login: municipalLogin || undefined,
          password: municipalPassword || undefined,
        }),
      "Credenciais municipais salvas de forma criptografada.",
    );
    if (saved) {
      setMunicipalLogin("");
      setMunicipalPassword("");
    }
  }

  async function saveFocusCredentials() {
    const saved = await run(
      () =>
        vetApi.salvarCredenciaisFocusNfse({
          master_token: focusMasterToken || undefined,
          homologation_token: focusHomologationToken || undefined,
          production_token: focusProductionToken || undefined,
        }),
      "Tokens da Focus salvos de forma criptografada.",
    );
    if (saved) {
      setFocusMasterToken("");
      setFocusHomologationToken("");
      setFocusProductionToken("");
    }
  }

  async function chooseManual(completed = false) {
    await run(
      () =>
        vetApi.vincularEmpresaFocus({
          mode: "manual",
          confirm: true,
          manual_setup_completed: completed,
        }),
      completed ? "Cadastro manual na Focus marcado como concluído." : "Opção manual selecionada.",
    );
  }

  async function shareExistingCertificate() {
    const confirmed = window.confirm(
      "Autoriza enviar diretamente à Focus o certificado A1 e a senha que já estão no CorePet? Os dados não passarão pelo navegador.",
    );
    if (!confirmed) return;
    await run(
      () => vetApi.vincularEmpresaFocus({ mode: "reuse_existing", confirm: true }),
      "Empresa vinculada e certificado compartilhado diretamente com a Focus.",
    );
  }

  async function prevalidate() {
    await run(
      () => vetApi.preValidarConfigNfse(),
      "Configuração pronta para emitir em homologação.",
    );
  }

  const shareReady =
    config?.certificate?.valid &&
    config?.municipal_credentials_configured &&
    config?.master_token_configured;

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
            Os dados cadastrais vêm do cadastro da empresa e os parâmetros tributários vêm da
            configuração fiscal. Senhas e certificados nunca são devolvidos para esta tela.
          </p>
        </div>

        {loading || !config ? (
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <RefreshCw size={16} className="animate-spin" /> Carregando configuração fiscal...
          </div>
        ) : (
          <>
            <div className="rounded-lg border border-gray-200 p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h3 className="font-semibold text-gray-900">Parâmetros fiscais da empresa</h3>
                  <p className="text-xs text-gray-500">
                    {config.tax_regime || "Regime não informado"} · Item{" "}
                    {config.service_list_item || "pendente"}
                    {" · "}ISS {config.iss_rate ?? "pendente"}% · Retido:{" "}
                    {config.iss_withheld ? "sim" : "não"}
                  </p>
                </div>
                <Link
                  to="/configuracoes/fiscal"
                  className="rounded-lg border border-blue-300 px-3 py-2 text-sm text-blue-700 hover:bg-blue-50"
                >
                  Editar configuração fiscal
                </Link>
              </div>
            </div>

            <div className="rounded-lg border border-gray-200 p-4 space-y-4">
              <div>
                <h3 className="font-semibold text-gray-900">1. Conta própria e tokens da Focus</h3>
                <p className="mt-1 text-sm text-gray-600">
                  A assinatura é feita e paga diretamente à Focus. O plano Solo custa R$ 89,90/mês
                  para 1 CNPJ, inclui 100 documentos e oferece 30 dias de teste.
                </p>
              </div>
              <div className="rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800">
                Entrar ou concluir o cadastro na Focus não configura o CorePet automaticamente. No
                fluxo normal, cadastre a empresa no painel da Focus e depois copie os tokens para
                esta tela.
              </div>
              <ol className="list-decimal space-y-1 pl-5 text-sm text-gray-600">
                <li>Crie a conta própria da empresa na Focus.</li>
                <li>No painel da Focus, acesse Empresas e adicione a empresa emitente.</li>
                <li>Depois acesse Painel API &gt; Tokens.</li>
                <li>Cole abaixo os tokens de homologação e produção.</li>
              </ol>
              <a
                href={config.focus_signup_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700"
              >
                Criar conta própria na Focus <ExternalLink size={15} />
              </a>
              <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
                <input
                  type="password"
                  value={focusHomologationToken}
                  onChange={(event) => setFocusHomologationToken(event.target.value)}
                  autoComplete="new-password"
                  placeholder="Token de homologação"
                  className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
                <input
                  type="password"
                  value={focusProductionToken}
                  onChange={(event) => setFocusProductionToken(event.target.value)}
                  autoComplete="new-password"
                  placeholder="Token de produção"
                  className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
                <input
                  type="password"
                  value={focusMasterToken}
                  onChange={(event) => setFocusMasterToken(event.target.value)}
                  autoComplete="new-password"
                  placeholder="Token Principal de Produção (opcional)"
                  className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
              <button
                type="button"
                onClick={() => void saveFocusCredentials()}
                disabled={
                  saving || (!focusMasterToken && !focusHomologationToken && !focusProductionToken)
                }
                className="inline-flex w-fit items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                <KeyRound size={15} /> Salvar tokens
              </button>
              <StatusItem ok={config.homologation_token_configured}>
                Token de homologação para emitir notas de teste
              </StatusItem>
              <StatusItem ok={config.production_token_configured}>
                Token de produção para emitir notas com validade fiscal depois da homologação
              </StatusItem>
              <p className="text-xs leading-5 text-gray-500">
                Token Principal de Produção:{" "}
                {config.master_token_configured ? "configurado" : "não configurado"}. Ele é opcional
                e só é necessário para o cadastro automático da empresa via API.
              </p>
            </div>

            <div className="rounded-lg border border-gray-200 p-4 space-y-4">
              <div>
                <h3 className="font-semibold text-gray-900">2. Credenciais da prefeitura</h3>
                <p className="mt-1 text-sm text-gray-600">
                  Presidente Prudente exige certificado A1, login e senha do portal municipal.
                </p>
              </div>
              <StatusItem ok={config.municipal_credentials_configured}>
                Login e senha municipais{" "}
                {config.municipal_credentials_configured ? "configurados" : "pendentes"}
              </StatusItem>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <input
                  value={municipalLogin}
                  onChange={(event) => setMunicipalLogin(event.target.value)}
                  autoComplete="off"
                  placeholder="Login da prefeitura"
                  className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
                <input
                  type="password"
                  value={municipalPassword}
                  onChange={(event) => setMunicipalPassword(event.target.value)}
                  autoComplete="new-password"
                  placeholder="Senha da prefeitura"
                  className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
              <button
                type="button"
                onClick={() => void saveMunicipalCredentials()}
                disabled={saving || (!municipalLogin && !municipalPassword)}
                className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                <KeyRound size={15} /> Salvar credenciais
              </button>
            </div>

            <div className="rounded-lg border border-gray-200 p-4 space-y-4">
              <div>
                <h3 className="font-semibold text-gray-900">
                  3. Cadastro da empresa e certificado A1
                </h3>
                <p className="mt-1 text-sm text-gray-600">{config.certificate?.message}</p>
              </div>
              <StatusItem ok={config.certificate?.valid}>
                Certificado existente no CorePet validado contra o CNPJ da empresa
              </StatusItem>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3">
                  <h4 className="font-medium text-emerald-900">
                    Cadastro manual na Focus — recomendado
                  </h4>
                  <p className="mt-1 text-xs text-emerald-800">
                    Como a conta e a cobrança são da própria empresa, adicione o emitente no painel
                    da Focus, envie o A1 e informe as credenciais municipais por lá.
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => void chooseManual(false)}
                      disabled={saving}
                      className="rounded-lg bg-emerald-600 px-3 py-2 text-sm text-white hover:bg-emerald-700 disabled:opacity-50"
                    >
                      Usar cadastro manual
                    </button>
                    <button
                      type="button"
                      onClick={() => void chooseManual(true)}
                      disabled={saving || config.onboarding_method !== "manual"}
                      className="rounded-lg border border-emerald-300 bg-white px-3 py-2 text-sm text-emerald-700 hover:bg-emerald-100 disabled:opacity-50"
                    >
                      Já cadastrei a empresa na Focus
                    </button>
                  </div>
                </div>
                <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                  <h4 className="font-medium text-gray-900">Cadastro automático — opcional</h4>
                  <p className="mt-1 text-xs text-gray-600">
                    Se a Focus já disponibilizou o Token Principal de Produção, o CorePet pode
                    cadastrar a empresa e enviar o A1 diretamente após sua autorização.
                  </p>
                  <button
                    type="button"
                    onClick={() => void shareExistingCertificate()}
                    disabled={saving || !shareReady}
                    className="mt-3 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 disabled:opacity-50"
                  >
                    Autorizar cadastro automático
                  </button>
                  {!shareReady && (
                    <p className="mt-2 text-xs text-gray-500">
                      Requer A1 válido no CorePet, credenciais municipais e Token Principal de
                      Produção.
                    </p>
                  )}
                </div>
              </div>
            </div>

            {config.missing_fields?.length > 0 && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
                <div className="flex items-center gap-2 text-sm font-semibold text-amber-800">
                  <AlertTriangle size={17} /> Pendências para homologar
                </div>
                <ul className="mt-2 list-disc pl-5 text-sm text-amber-800">
                  {config.missing_fields.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            )}

            {config.ready_for_homologation && (
              <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">
                <CheckCircle size={18} /> Dados completos para emitir a nota de homologação.
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
                onClick={() => void prevalidate()}
                disabled={saving}
                className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
              >
                {saving ? "Validando..." : "Validar para homologação"}
              </button>
            </div>
          </>
        )}
      </div>
    </section>
  );
}
