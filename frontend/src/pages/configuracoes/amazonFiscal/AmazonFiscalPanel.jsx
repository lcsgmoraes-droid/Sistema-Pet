import { useState } from "react";
import { Link, Pencil, Plus, RefreshCw } from "lucide-react";
import BotaoInteracao from "../../../components/v2/BotaoInteracao/BotaoInteracao";
import AmazonFiscalAccountForm from "./AmazonFiscalAccountForm";
import AmazonFiscalMappings from "./AmazonFiscalMappings";
import AmazonFiscalOrderDialog from "./AmazonFiscalOrderDialog";
import AmazonFiscalOrders from "./AmazonFiscalOrders";
import { FISCAL_SCOPES, formatFiscalDate } from "./amazonFiscalUtils";
import useAmazonFiscal from "./useAmazonFiscal";

export default function AmazonFiscalPanel({ scopes = [] }) {
  const fiscal = useAmazonFiscal();
  const [editingAccount, setEditingAccount] = useState(null);
  const [mappingAccount, setMappingAccount] = useState(null);
  const hasFiscalScopes = FISCAL_SCOPES.every((scope) => scopes.includes(scope));
  return (
    <section className="mt-6 space-y-5 rounded-xl border border-slate-200 bg-white p-4 text-slate-800 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">NF-e de pedidos Amazon</h2>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
            Configure e ative o fluxo por conta Amazon (Seller ID) desta empresa. CNPJ, SKUs,
            descontos, emissão e autorização de envio do XML são definidos aqui no CorePet.
          </p>
        </div>
        <BotaoInteracao
          icon={RefreshCw}
          tamanho="pequeno"
          loading={fiscal.refreshing}
          onClick={fiscal.refresh}
        >
          Atualizar caixa fiscal
        </BotaoInteracao>
      </div>
      {!hasFiscalScopes && (
        <p className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950/20 dark:text-amber-200">
          Esta conexão ainda não possui todas as permissões fiscais. No EcommerceAI, solicite uma
          nova conexão com preparação, emissão e consulta de NF-e e aprove essas permissões aqui. As
          conexões antigas mantêm o acesso já autorizado.
        </p>
      )}
      {fiscal.error && !fiscal.detailOpen && !editingAccount && (
        <p role="alert" className="text-sm text-red-700 dark:text-red-300">
          {fiscal.error}
        </p>
      )}
      {fiscal.message && (
        <p role="status" className="text-sm text-emerald-700 dark:text-emerald-300">
          {fiscal.message}
        </p>
      )}
      {fiscal.loading ? (
        <p role="status">Carregando configuração e pedidos fiscais...</p>
      ) : (
        <>
          <section className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="font-semibold">Contas e produtos</h3>
              <BotaoInteracao
                icon={Plus}
                disabled={fiscal.busy}
                onClick={() => setEditingAccount({})}
              >
                Cadastrar conta fiscal Amazon
              </BotaoInteracao>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr>
                    <th className="p-2">Ações</th>
                    <th className="p-2">Seller ID / CNPJ</th>
                    <th className="p-2">Automação</th>
                    <th className="p-2">Descontos</th>
                  </tr>
                </thead>
                <tbody>
                  {fiscal.accounts.map((account) => (
                    <tr
                      key={account.id}
                      className="border-t border-slate-200 dark:border-slate-700"
                    >
                      <td className="space-x-2 p-2">
                        <BotaoInteracao
                          icon={Pencil}
                          tamanho="pequeno"
                          disabled={fiscal.busy}
                          onClick={() => setEditingAccount(account)}
                        >
                          Configurar
                        </BotaoInteracao>
                        <BotaoInteracao
                          icon={Link}
                          tamanho="pequeno"
                          disabled={fiscal.busy}
                          onClick={() => setMappingAccount(account)}
                        >
                          Mapear SKUs
                        </BotaoInteracao>
                      </td>
                      <td className="p-2">
                        <p>{account.seller_id}</p>
                        <p className="text-xs text-slate-500 dark:text-slate-400">
                          {account.emitter_cnpj}
                        </p>
                      </td>
                      <td className="p-2">
                        <p>
                          Fluxo:{" "}
                          {!account.active
                            ? "Desativado"
                            : !hasFiscalScopes
                              ? "Aguardando permissões fiscais"
                              : "Ativado"}
                        </p>
                        <p>
                          Emissão:{" "}
                          {account.active && account.auto_issue_enabled
                            ? hasFiscalScopes
                              ? "Automática após validação"
                              : "Aguardando permissões fiscais"
                            : "Com confirmação por pedido"}
                        </p>
                        <p>
                          Envio XML:{" "}
                          {!account.upload_enabled
                            ? "Desativado"
                            : !hasFiscalScopes
                              ? "Aguardando permissões fiscais"
                              : "Habilitado"}
                        </p>
                        <p className="text-xs text-slate-500 dark:text-slate-400">
                          Corte: {formatFiscalDate(account.activated_at)}
                        </p>
                      </td>
                      <td className="p-2">
                        {account.discount_policy === "buyer_payment_total"
                          ? "Ajustar ao pagamento documentado"
                          : "Somente descontos de origem"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!fiscal.accounts.length && (
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Cadastre a loja Amazon e vincule os SKUs antes de emitir.
              </p>
            )}
          </section>
          <AmazonFiscalOrders fiscal={fiscal} />
        </>
      )}
      {editingAccount && (
        <AmazonFiscalAccountForm
          account={editingAccount}
          hasFiscalScopes={hasFiscalScopes}
          busy={fiscal.busy}
          error={fiscal.error}
          onClose={() => setEditingAccount(null)}
          onSave={async (form) => {
            if (await fiscal.saveAccount(form)) setEditingAccount(null);
          }}
        />
      )}
      {mappingAccount && (
        <AmazonFiscalMappings
          key={mappingAccount.id}
          account={mappingAccount}
          onClose={() => setMappingAccount(null)}
          onChanged={fiscal.refresh}
        />
      )}
      {fiscal.detailOpen && (
        <AmazonFiscalOrderDialog key={fiscal.detail?.id || "loading"} fiscal={fiscal} />
      )}
    </section>
  );
}
