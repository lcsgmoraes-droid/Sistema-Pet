import { FileText, Search, ShieldCheck, Trash2, UserSearch } from "lucide-react";
import PessoaSelector from "../../components/clientes/PessoaSelector";
import ActionButton from "../../components/ui/ActionButton";
import CopyableCode from "../../components/ui/CopyableCode";
import CustomerIdentity from "../../components/ui/CustomerIdentity";
import EmptyState from "../../components/ui/EmptyState";
import Panel from "../../components/ui/Panel";
import StatusBadge from "../../components/ui/StatusBadge";

export default function LGPDTitularPanel({
  abrirNovoPedidoAcesso,
  carregarClientePrivacidade,
  clienteTermo,
  clientesSugeridos,
  criarSolicitacaoExclusao,
  handleClienteTermoChange,
  handleSelectCliente,
  loadingCliente,
  saving,
  selectedClienteId,
  selectedCustomer,
  setPrivacyModalOpen,
}) {
  return (
    <Panel
      title="1. Buscar titular"
      subtitle="Pesquise a pessoa que fez o pedido LGPD. A busca inclui clientes, fornecedores, veterinarios, funcionarios, ativos e inativos."
    >
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(380px,0.8fr)]">
        <div className="space-y-3">
          <PessoaSelector
            id="lgpd-titular-search"
            minChars={2}
            name="lgpd_titular_search"
            onChange={handleClienteTermoChange}
            onSelect={handleSelectCliente}
            placeholder="Digite nome, codigo, CPF, email ou telefone do titular..."
            showSuggestions={clientesSugeridos.length > 0}
            suggestions={clientesSugeridos}
            value={clienteTermo}
            renderSuggestion={(cliente, index) => (
              <div
                key={cliente?.id || index}
                onClick={() => handleSelectCliente(cliente)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    handleSelectCliente(cliente);
                  }
                }}
                role="button"
                tabIndex={0}
                className="w-full cursor-pointer border-b px-4 py-3 text-left last:border-b-0 hover:bg-slate-50"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <CustomerIdentity customer={cliente} />
                  <StatusBadge intent={cliente?.ativo === false ? "neutral" : "success"} size="xs">
                    {cliente?.ativo === false ? "Inativo" : "Ativo"}
                  </StatusBadge>
                </div>
                <div className="mt-1 text-xs text-slate-500">
                  {cliente?.email || cliente?.telefone || cliente?.celular || "-"}
                </div>
              </div>
            )}
          />
          <div className="flex flex-wrap items-center gap-2">
            <ActionButton
              icon={Search}
              intent="edit"
              onClick={() => carregarClientePrivacidade()}
              loading={loadingCliente}
              disabled={!selectedClienteId}
            >
              Carregar dados LGPD
            </ActionButton>
            {selectedClienteId ? <CopyableCode label="Titular" value={selectedClienteId} /> : null}
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
          {selectedCustomer ? (
            <div className="space-y-3">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <CustomerIdentity customer={selectedCustomer} />
                <StatusBadge intent={selectedCustomer?.ativo === false ? "neutral" : "success"}>
                  {selectedCustomer?.ativo === false ? "Inativo" : "Ativo"}
                </StatusBadge>
              </div>
              <div className="grid grid-cols-1 gap-2 text-xs text-slate-600 sm:grid-cols-2">
                <span>Email: {selectedCustomer.email || "-"}</span>
                <span>
                  Telefone: {selectedCustomer.telefone || selectedCustomer.celular || "-"}
                </span>
                <span>Codigo: {selectedCustomer.codigo || "-"}</span>
                <span>Tipo: {selectedCustomer.tipo_cadastro || "-"}</span>
                <span>ID: {selectedCustomer.id || "-"}</span>
              </div>
              <div className="flex flex-wrap gap-2">
                <ActionButton
                  icon={Trash2}
                  intent="delete"
                  tone="soft"
                  onClick={criarSolicitacaoExclusao}
                  loading={saving}
                >
                  Abrir exclusao LGPD
                </ActionButton>
                <ActionButton
                  icon={FileText}
                  intent="neutral"
                  tone="soft"
                  onClick={abrirNovoPedidoAcesso}
                >
                  Registrar pedido LGPD
                </ActionButton>
                <ActionButton
                  icon={ShieldCheck}
                  intent="neutral"
                  tone="soft"
                  onClick={() => setPrivacyModalOpen(true)}
                >
                  Dossie e preferencias
                </ActionButton>
              </div>
            </div>
          ) : (
            <EmptyState
              compact
              icon={UserSearch}
              title="Nenhum titular selecionado"
              description="Pesquise a pessoa primeiro; depois aparecem as solicitacoes abertas e as acoes LGPD."
            />
          )}
        </div>
      </div>
    </Panel>
  );
}
