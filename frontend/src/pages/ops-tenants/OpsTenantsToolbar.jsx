import { FiSearch } from "react-icons/fi";

import InputCombobox from "../../components/v2/InputCombobox/InputCombobox";
import InputTexto from "../../components/v2/InputTexto/InputTexto";
import SeletorOpcoes from "../../components/v2/SeletorOpcoes/SeletorOpcoes";
import { OPS_TENANT_TABS } from "../opsTenantsUtils";

import { STATUS_OPTIONS } from "./opsTenantsConstants";
import { formatNumber } from "./opsTenantsFormatters";

export default function OpsTenantsToolbar({
  activeTab,
  summaries,
  onChangeTab,
  search,
  status,
  onSearchChange,
  onStatusChange,
}) {
  const badges = {
    tenants: `${formatNumber(summaries.tenants.active)}/${formatNumber(summaries.tenants.total)}`,
    billing: summaries.billing.attention
      ? `${formatNumber(summaries.billing.attention)} atencao`
      : "ok",
    pilot: summaries.pilot.blocked
      ? `${formatNumber(summaries.pilot.blocked)} bloqueado(s)`
      : `${formatNumber(summaries.pilot.active)} ativo(s)`,
    usage: summaries.usage.imageStorage,
  };

  const opcoesAbas = OPS_TENANT_TABS.map((tab) => {
    const selecionada = tab.id === activeTab;
    return {
      valor: tab.id,
      rotulo: (
        <span className="flex items-center gap-1.5">
          {tab.label}
          <span
            className={
              selecionada
                ? "rounded-full bg-white/20 px-1.5 py-0.5 text-xs"
                : "rounded-full bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600 dark:bg-slate-700 dark:text-slate-300"
            }
          >
            {badges[tab.id]}
          </span>
        </span>
      ),
    };
  });

  return (
    <section className="flex flex-wrap items-center gap-3 rounded-lg border border-slate-200 bg-white p-3 shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <SeletorOpcoes opcoes={opcoesAbas} valorSelecionado={activeTab} aoSelecionar={onChangeTab} />

      <div className="ml-auto flex flex-1 flex-wrap items-center gap-3 sm:flex-none">
        <div className="min-w-[220px] flex-1 sm:w-72 sm:flex-none">
          <InputTexto
            id="ops-tenants-busca"
            type="search"
            value={search}
            onChange={onSearchChange}
            placeholder="Buscar por nome ou tenant id"
            left={<FiSearch className="h-4 w-4 text-slate-400" aria-hidden="true" />}
          />
        </div>
        <div className="w-36">
          <InputCombobox
            id="ops-tenants-status"
            opcoes={STATUS_OPTIONS}
            value={status}
            onChange={onStatusChange}
            placeholder="Status"
            permitirLimpar={false}
          />
        </div>
      </div>
    </section>
  );
}
