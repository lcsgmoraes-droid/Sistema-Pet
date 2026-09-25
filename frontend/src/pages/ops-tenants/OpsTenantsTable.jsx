import { useState } from "react";
import { FiChevronDown, FiChevronLeft, FiChevronRight, FiPlusCircle } from "react-icons/fi";

import OpsAdicionarLojaModal from "./OpsAdicionarLojaModal";
import OpsTenantsBadge from "./OpsTenantsBadge";
import {
  ATTENTION_LABELS,
  attentionBadge,
  billingBadge,
  formatDate,
  shortId,
  statusBadge,
} from "./opsTenantsFormatters";

function TenantRow({ tenant, selected, onSelect }) {
  const pilot = tenant.pilot || {};

  return (
    <tr className={selected ? "bg-blue-50" : "bg-white hover:bg-slate-50"}>
      <td className="w-[28%] px-4 py-3 align-top">
        <button
          type="button"
          onClick={() => onSelect(tenant.id)}
          className="block min-w-0 text-left"
        >
          <div className="truncate text-sm font-bold text-slate-900" title={tenant.name}>
            {tenant.name}
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <span className="font-mono text-xs text-slate-500">{shortId(tenant.id)}</span>
            <OpsTenantsBadge className={statusBadge(tenant.status)}>
              {tenant.status || "active"}
            </OpsTenantsBadge>
          </div>
        </button>
      </td>
      <td className="px-4 py-3 align-top">
        <div className="flex flex-wrap gap-2">
          <OpsTenantsBadge className="border-blue-200 bg-blue-50 text-blue-700">
            {tenant.plan || "free"}
          </OpsTenantsBadge>
          <OpsTenantsBadge className={billingBadge(tenant.billing_status)}>
            {tenant.billing_status || "active"}
          </OpsTenantsBadge>
        </div>
        <div className="mt-2 text-xs text-slate-500">
          Origem {tenant.subscription_source || "manual"} |{" "}
          {formatDate(tenant.subscription_activated_at || tenant.created_at)}
        </div>
      </td>
      <td className="px-4 py-3 align-top">
        <div
          className="max-w-[210px] truncate text-sm font-semibold text-slate-800"
          title={tenant.principal_user?.email}
        >
          {tenant.principal_user?.nome || tenant.principal_user?.email || "-"}
        </div>
        <div className="mt-1 max-w-[210px] truncate text-xs text-slate-500">
          {tenant.principal_user?.email || "sem usuario principal"}
        </div>
      </td>
      <td className="px-4 py-3 align-top">
        <OpsTenantsBadge className={attentionBadge(pilot.attention_level)}>
          {ATTENTION_LABELS[pilot.attention_level] || ATTENTION_LABELS.healthy}
        </OpsTenantsBadge>
        <div className="mt-2 max-w-[240px] text-xs text-slate-600">
          {pilot.needs_follow_up
            ? pilot.next_action
            : `Ultima atividade: ${formatDate(pilot.last_activity_at)}`}
        </div>
      </td>
    </tr>
  );
}

function GroupHeaderRow({ group, collapsed, onToggle, onAddLoja }) {
  return (
    <tr className="bg-slate-50/80">
      <td colSpan={4} className="px-4 py-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <button
            type="button"
            onClick={onToggle}
            aria-expanded={!collapsed}
            aria-label={`${collapsed ? "Expandir" : "Recolher"} lojas de ${group.nome}`}
            className="flex min-w-0 items-center gap-2 text-left"
          >
            {collapsed ? (
              <FiChevronRight aria-hidden="true" className="h-4 w-4 shrink-0 text-slate-400" />
            ) : (
              <FiChevronDown aria-hidden="true" className="h-4 w-4 shrink-0 text-slate-400" />
            )}
            <span className="truncate text-sm font-bold text-slate-900">{group.nome}</span>
            <OpsTenantsBadge className="border-slate-200 bg-white text-slate-600">
              {group.lojaCount} loja{group.lojaCount === 1 ? "" : "s"}
            </OpsTenantsBadge>
          </button>
          <div className="flex flex-wrap items-center gap-2">
            {group.adimplente ? (
              <OpsTenantsBadge className="border-emerald-200 bg-emerald-50 text-emerald-700">
                Adimplente
              </OpsTenantsBadge>
            ) : (
              <>
                <OpsTenantsBadge className="border-rose-200 bg-rose-50 text-rose-700">
                  {group.inadimplentes.length} inadimplente
                  {group.inadimplentes.length === 1 ? "" : "s"}
                </OpsTenantsBadge>
                <span className="text-xs text-rose-700">
                  {group.inadimplentes.map((loja) => loja.name).join(", ")}
                </span>
              </>
            )}
            {group.grupoId != null ? (
              <button
                type="button"
                onClick={onAddLoja}
                className="inline-flex h-7 items-center gap-1 rounded-lg border border-blue-200 bg-blue-50 px-2 text-xs font-semibold text-blue-700 hover:bg-blue-100"
              >
                <FiPlusCircle className="h-3.5 w-3.5" />
                Adicionar loja
              </button>
            ) : null}
          </div>
        </div>
      </td>
    </tr>
  );
}

const PAGINACAO_VAZIA = { page: 1, pageSize: 10, totalGroups: 0, totalPages: 0 };

export default function OpsTenantsTable({
  groupedItems = [],
  pagination = PAGINACAO_VAZIA,
  onPageChange,
  loading,
  selectedTenant,
  onSelectTenant,
  onLojaAdded,
}) {
  const [expandedGroups, setExpandedGroups] = useState(() => new Set());
  const [modalGrupo, setModalGrupo] = useState(null);

  function toggleGroup(key) {
    setExpandedGroups((current) => {
      const next = new Set(current);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  }

  return (
    <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between gap-3 border-b border-slate-200 px-4 py-3">
        <div>
          <h2 className="text-base font-bold text-slate-900">Tenants</h2>
          <p className="text-sm text-slate-500">
            Agrupado por cliente, mais recentes primeiro. 10 clientes por pagina.
          </p>
        </div>
        {loading ? (
          <OpsTenantsBadge className="border-blue-200 bg-blue-50 text-blue-700">
            carregando
          </OpsTenantsBadge>
        ) : (
          <OpsTenantsBadge className="border-slate-200 bg-slate-50 text-slate-700">
            {pagination.totalGroups} cliente{pagination.totalGroups === 1 ? "" : "s"}
          </OpsTenantsBadge>
        )}
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-[860px] w-full divide-y divide-slate-200 text-left">
          <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-600">
            <tr>
              <th className="px-4 py-3 font-bold">Tenant</th>
              <th className="px-4 py-3 font-bold">Plano</th>
              <th className="px-4 py-3 font-bold">Principal</th>
              <th className="px-4 py-3 font-bold">Atencao</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {groupedItems.length === 0 && !loading ? (
              <tr>
                <td colSpan={4} className="px-4 py-10 text-center text-sm text-slate-500">
                  Nenhum tenant encontrado para o filtro atual.
                </td>
              </tr>
            ) : (
              groupedItems.map((group) => (
                <GroupRows
                  key={group.key}
                  group={group}
                  collapsed={!expandedGroups.has(group.key)}
                  onToggle={() => toggleGroup(group.key)}
                  onAddLoja={() => setModalGrupo(group)}
                  selectedTenant={selectedTenant}
                  onSelectTenant={onSelectTenant}
                />
              ))
            )}
          </tbody>
        </table>
      </div>

      {pagination.totalPages > 1 ? (
        <div className="flex items-center justify-between gap-3 border-t border-slate-200 px-4 py-3">
          <button
            type="button"
            onClick={() => onPageChange(pagination.page - 1)}
            disabled={pagination.page <= 1}
            className="inline-flex h-8 items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <FiChevronLeft className="h-3.5 w-3.5" aria-hidden="true" />
            Anterior
          </button>
          <span className="text-xs text-slate-500">
            Pagina {pagination.page} de {pagination.totalPages}
          </span>
          <button
            type="button"
            onClick={() => onPageChange(pagination.page + 1)}
            disabled={pagination.page >= pagination.totalPages}
            className="inline-flex h-8 items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Proxima
            <FiChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
        </div>
      ) : null}

      {modalGrupo ? (
        <OpsAdicionarLojaModal
          grupo={modalGrupo}
          onClose={() => setModalGrupo(null)}
          onCreated={onLojaAdded}
        />
      ) : null}
    </section>
  );
}

function GroupRows({ group, collapsed, onToggle, onAddLoja, selectedTenant, onSelectTenant }) {
  return (
    <>
      <GroupHeaderRow group={group} collapsed={collapsed} onToggle={onToggle} onAddLoja={onAddLoja} />
      {collapsed
        ? null
        : group.lojas.map((tenant) => (
            <TenantRow
              key={tenant.id}
              tenant={tenant}
              selected={selectedTenant?.id === tenant.id}
              onSelect={onSelectTenant}
            />
          ))}
    </>
  );
}
