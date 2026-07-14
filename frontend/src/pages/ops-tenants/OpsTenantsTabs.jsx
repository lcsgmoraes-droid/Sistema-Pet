import { OPS_TENANT_TABS } from "../opsTenantsUtils";

import { formatNumber } from "./opsTenantsFormatters";

function TabButton({ tab, active, badge, onClick }) {
  return (
    <button
      type="button"
      onClick={() => onClick(tab.id)}
      className={[
        "inline-flex h-10 items-center gap-2 rounded-lg border px-3 text-sm font-semibold transition",
        active
          ? "border-blue-600 bg-blue-600 text-white shadow-sm"
          : "border-slate-200 bg-white text-slate-600 hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700",
      ].join(" ")}
    >
      <span>{tab.label}</span>
      {badge ? (
        <span
          className={
            active
              ? "rounded-full bg-white/20 px-2 py-0.5 text-xs"
              : "rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500"
          }
        >
          {badge}
        </span>
      ) : null}
    </button>
  );
}

export default function OpsTenantsTabs({ activeTab, summaries, onChange }) {
  const badges = {
    tenants: `${formatNumber(summaries.tenants.active)}/${formatNumber(summaries.tenants.total)}`,
    catalog: summaries.catalog.pending ? `${formatNumber(summaries.catalog.pending)} pend.` : "ok",
    billing: summaries.billing.attention
      ? `${formatNumber(summaries.billing.attention)} atencao`
      : "ok",
    pilot: summaries.pilot.blocked
      ? `${formatNumber(summaries.pilot.blocked)} bloqueado(s)`
      : `${formatNumber(summaries.pilot.active)} ativo(s)`,
    usage: summaries.usage.imageStorage,
  };

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-2 shadow-sm">
      <div className="flex flex-wrap gap-2">
        {OPS_TENANT_TABS.map((tab) => (
          <TabButton
            key={tab.id}
            tab={tab}
            active={activeTab === tab.id}
            badge={badges[tab.id]}
            onClick={onChange}
          />
        ))}
      </div>
    </section>
  );
}
