import { Download, History, Save, Search, ShieldCheck, UserSearch, X } from "lucide-react";
import ActionButton from "../../components/ui/ActionButton";
import CopyableCode from "../../components/ui/CopyableCode";
import CustomerIdentity from "../../components/ui/CustomerIdentity";
import EmptyState from "../../components/ui/EmptyState";
import StatusBadge from "../../components/ui/StatusBadge";
import { PREFERENCES } from "./lgpdConstants";
import { formatDate } from "./lgpdUtils";

function PreferenceToggle({ description, label, name, onChange, value }) {
  return (
    <label className="flex min-h-[70px] cursor-pointer items-start gap-3 rounded-lg border border-slate-200 bg-white p-3 transition-colors hover:border-blue-200 hover:bg-blue-50/40">
      <input
        type="checkbox"
        checked={Boolean(value)}
        onChange={(event) => onChange(name, event.target.checked)}
        className="mt-1 h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
      />
      <span className="min-w-0">
        <span className="block text-sm font-semibold text-slate-900">{label}</span>
        <span className="mt-1 block text-xs leading-snug text-slate-500">{description}</span>
      </span>
    </label>
  );
}

export default function LGPDPrivacyModal({
  carregarClientePrivacidade,
  consentimentos,
  dossie,
  exportarJson,
  loadingCliente,
  prefs,
  privacyModalOpen,
  resumoDossie,
  salvarPreferencias,
  saving,
  selectedClienteId,
  selectedCustomer,
  setPrefs,
  setPrivacyModalOpen,
}) {
  if (!privacyModalOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 p-4">
      <div className="flex max-h-[92vh] w-full max-w-5xl flex-col rounded-lg bg-white shadow-xl">
        <div className="flex items-start justify-between gap-3 border-b border-slate-200 p-4">
          <div>
            <h3 className="text-base font-semibold text-slate-950">Dossie e preferencias</h3>
            <p className="mt-1 text-sm text-slate-500">
              Use para exportar dados do titular ou ajustar consentimentos de comunicacao.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <ActionButton
              icon={Download}
              intent="neutral"
              tone="soft"
              onClick={exportarJson}
              disabled={!dossie}
            >
              Exportar JSON
            </ActionButton>
            <button
              type="button"
              onClick={() => setPrivacyModalOpen(false)}
              className="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
              aria-label="Fechar"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
        <div className="overflow-y-auto p-4">
          {!selectedClienteId ? (
            <EmptyState
              compact
              icon={UserSearch}
              title="Busque um titular primeiro"
              description="Feche esta janela, selecione a pessoa no passo 1 e volte aqui se precisar exportar ou ajustar preferencias."
            />
          ) : (
            <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
              <div className="space-y-3">
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    {selectedCustomer ? <CustomerIdentity customer={selectedCustomer} /> : null}
                    <StatusBadge intent={selectedCustomer?.ativo === false ? "neutral" : "success"}>
                      {selectedCustomer?.ativo === false ? "Inativo" : "Ativo"}
                    </StatusBadge>
                  </div>
                  <div className="mt-3 grid grid-cols-1 gap-2 text-xs text-slate-600 sm:grid-cols-2">
                    <span>Email: {selectedCustomer?.email || "-"}</span>
                    <span>
                      Telefone: {selectedCustomer?.telefone || selectedCustomer?.celular || "-"}
                    </span>
                    <span>Codigo: {selectedCustomer?.codigo || "-"}</span>
                    <span>Tipo: {selectedCustomer?.tipo_cadastro || "-"}</span>
                    <span>Gerado em: {formatDate(dossie?.generated_at)}</span>
                  </div>
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    <ActionButton
                      icon={Search}
                      intent="edit"
                      onClick={() => carregarClientePrivacidade()}
                      loading={loadingCliente}
                    >
                      Carregar dossie e consentimentos
                    </ActionButton>
                    <CopyableCode label="Titular" value={selectedClienteId} />
                  </div>
                </div>

                {resumoDossie.length ? (
                  <div className="grid grid-cols-2 gap-2">
                    {resumoDossie.map(([label, value]) => (
                      <div key={label} className="rounded-lg border border-slate-200 bg-white p-3">
                        <div className="text-xs font-medium text-slate-500">{label}</div>
                        <div className="mt-1 text-lg font-bold text-slate-950">{value}</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <EmptyState
                    compact
                    icon={UserSearch}
                    title="Dossie ainda nao carregado"
                    description="Clique em Carregar dossie e consentimentos para consultar os dados exportaveis."
                  />
                )}
              </div>

              <div className="space-y-4">
                {dossie ? (
                  <>
                    <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                      {PREFERENCES.map(([key, label, description]) => (
                        <PreferenceToggle
                          key={key}
                          name={key}
                          label={label}
                          description={description}
                          value={prefs[key]}
                          onChange={(name, value) =>
                            setPrefs((current) => ({ ...current, [name]: value }))
                          }
                        />
                      ))}
                    </div>

                    <ActionButton
                      icon={Save}
                      intent="edit"
                      onClick={salvarPreferencias}
                      loading={saving}
                    >
                      Salvar preferencias
                    </ActionButton>

                    <div className="rounded-lg border border-slate-200">
                      <div className="flex items-center gap-2 border-b border-slate-200 px-3 py-2 text-sm font-semibold text-slate-900">
                        <History className="h-4 w-4 text-slate-500" />
                        Historico recente
                      </div>
                      <div className="max-h-64 overflow-y-auto">
                        {consentimentos?.historico?.length ? (
                          consentimentos.historico.slice(0, 20).map((item) => (
                            <div
                              key={item.id}
                              className="border-b border-slate-100 px-3 py-2 text-xs last:border-b-0"
                            >
                              <div className="flex flex-wrap items-center justify-between gap-2">
                                <span className="font-medium text-slate-800">
                                  {item.consent_type}
                                </span>
                                <StatusBadge
                                  intent={
                                    item.consent_given && !item.revoked_at ? "success" : "danger"
                                  }
                                  size="xs"
                                >
                                  {item.consent_given && !item.revoked_at
                                    ? "Autorizado"
                                    : "Revogado"}
                                </StatusBadge>
                              </div>
                              <div className="mt-1 text-slate-500">
                                {formatDate(item.created_at)}
                              </div>
                              {item.consent_text ? (
                                <div className="mt-1 text-slate-500">{item.consent_text}</div>
                              ) : null}
                            </div>
                          ))
                        ) : (
                          <div className="p-4">
                            <EmptyState compact title="Sem historico de consentimento" />
                          </div>
                        )}
                      </div>
                    </div>
                  </>
                ) : (
                  <EmptyState
                    compact
                    icon={ShieldCheck}
                    title="Preferencias aguardando dossie"
                    description="Carregue os dados do titular para revisar consentimentos e exportar o JSON."
                  />
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
