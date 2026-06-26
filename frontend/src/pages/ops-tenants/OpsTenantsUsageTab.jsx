import { FiBox, FiDatabase, FiHardDrive } from "react-icons/fi";

import { formatStorageMb } from "../opsTenantsUtils";

import OpsTenantsBadge from "./OpsTenantsBadge";
import OpsTenantsMetricCard from "./OpsTenantsMetricCard";
import { formatNumber, shortId } from "./opsTenantsFormatters";

export default function OpsTenantsUsageTab({ items, summaries, loading }) {
  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-3">
        <OpsTenantsMetricCard
          icon={FiDatabase}
          label="Registros"
          value={formatNumber(summaries.usage.recordsTotal)}
          detail="Cadastros somados no filtro"
          tone="slate"
        />
        <OpsTenantsMetricCard
          icon={FiBox}
          label="Imagens"
          value={formatNumber(
            items.reduce((total, item) => total + Number(item?.usage?.image_count || 0), 0),
          )}
          detail="Produto_imagens registradas"
          tone="blue"
        />
        <OpsTenantsMetricCard
          icon={FiHardDrive}
          label="Uso imagens"
          value={summaries.usage.imageStorage}
          detail="Somatorio do campo tamanho"
          tone="amber"
        />
      </div>

      <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
        <div className="flex items-center justify-between gap-3 border-b border-slate-200 px-4 py-3">
          <div>
            <h2 className="text-base font-bold text-slate-900">Uso e cadastros</h2>
            <p className="text-sm text-slate-500">
              Volume operacional por tenant dentro do filtro atual.
            </p>
          </div>
          {loading ? (
            <OpsTenantsBadge className="border-blue-200 bg-blue-50 text-blue-700">
              carregando
            </OpsTenantsBadge>
          ) : (
            <OpsTenantsBadge className="border-slate-200 bg-slate-50 text-slate-700">
              {items.length} exibido(s)
            </OpsTenantsBadge>
          )}
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-[1100px] w-full divide-y divide-slate-200 text-left">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3 font-bold">Tenant</th>
                <th className="px-4 py-3 font-bold">Registros</th>
                <th className="px-4 py-3 font-bold">Produtos</th>
                <th className="px-4 py-3 font-bold">Clientes</th>
                <th className="px-4 py-3 font-bold">Pets</th>
                <th className="px-4 py-3 font-bold">Vendas</th>
                <th className="px-4 py-3 font-bold">Usuarios</th>
                <th className="px-4 py-3 font-bold">Imagens</th>
                <th className="px-4 py-3 font-bold">Uso imagens</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {items.length === 0 && !loading ? (
                <tr>
                  <td colSpan={9} className="px-4 py-10 text-center text-sm text-slate-500">
                    Nenhum tenant encontrado para o filtro atual.
                  </td>
                </tr>
              ) : (
                items.map((tenant) => {
                  const counts = tenant.counts || {};
                  const usage = tenant.usage || {};
                  return (
                    <tr key={tenant.id} className="bg-white hover:bg-slate-50">
                      <td className="px-4 py-3">
                        <div className="text-sm font-bold text-slate-900">{tenant.name}</div>
                        <div className="mt-1 font-mono text-[11px] text-slate-500">
                          {shortId(tenant.id)}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm font-bold text-slate-900">
                        {formatNumber(usage.records_total)}
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-700">
                        {formatNumber(counts.produtos)}
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-700">
                        {formatNumber(counts.clientes)}
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-700">
                        {formatNumber(counts.pets)}
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-700">
                        {formatNumber(counts.vendas)}
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-700">
                        {formatNumber(counts.usuarios)}
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-700">
                        {formatNumber(usage.image_count)}
                      </td>
                      <td className="px-4 py-3 text-sm font-semibold text-slate-900">
                        {formatStorageMb(usage.image_bytes)}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
