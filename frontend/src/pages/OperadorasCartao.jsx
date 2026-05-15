import { AlertTriangle, CreditCard, Plus } from "lucide-react";
import OperadoraCartaoCard from "../components/operadorasCartao/OperadoraCartaoCard";
import OperadoraCartaoEmptyState from "../components/operadorasCartao/OperadoraCartaoEmptyState";
import OperadoraCartaoModal from "../components/operadorasCartao/OperadoraCartaoModal";
import OperadoraCartaoPadraoInfo from "../components/operadorasCartao/OperadoraCartaoPadraoInfo";
import ActionButton from "../components/ui/ActionButton";
import LoadingState from "../components/ui/LoadingState";
import PageHeader from "../components/ui/PageHeader";
import Panel from "../components/ui/Panel";
import { useOperadorasCartaoPage } from "../hooks/useOperadorasCartaoPage";
import { getGuiaClassNames } from "../utils/guiaHighlight";

function OperadorasCartao() {
  const guiaAtiva = new URLSearchParams(window.location.search).get("guia");
  const destacarOperadoras = guiaAtiva === "operadoras-cartao";
  const guiaClasses = getGuiaClassNames(destacarOperadoras);
  const {
    abrirModal,
    erro,
    excluirOperadora,
    fecharModal,
    formData,
    loading,
    modalAberto,
    mostrarToken,
    operadoraPadrao,
    operadoraSelecionada,
    operadoras,
    salvarOperadora,
    setErro,
    setFormData,
    setMostrarToken,
  } = useOperadorasCartaoPage();

  if (loading) {
    return <LoadingState className="h-64" label="Carregando operadoras..." />;
  }

  return (
    <div className="space-y-6 p-6">
      {destacarOperadoras && (
        <div className="rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-amber-900">
          Etapa da introducao guiada: comece por <strong>Nova Operadora</strong> e marque uma
          operadora ativa como padrao.
        </div>
      )}

      <PageHeader
        icon={CreditCard}
        title="Operadoras de Cartao"
        subtitle="Configure as operadoras de cartao disponiveis para o PDV."
        actions={
          <ActionButton
            onClick={() => abrirModal()}
            className={destacarOperadoras ? guiaClasses.action : ""}
            intent={destacarOperadoras ? "warning" : "create"}
            icon={Plus}
            size="md"
          >
            Nova Operadora
          </ActionButton>
        }
      />

      <Panel className="border-amber-200 bg-amber-50">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-medium text-amber-900 mb-1">Importante</h3>
            <ul className="text-sm text-amber-700 space-y-1">
              <li>- Pelo menos uma operadora deve estar marcada como padrao e ativa</li>
              <li>- O PDV usara a operadora padrao automaticamente para vendas com cartao</li>
              <li>- Operadoras com vendas vinculadas nao podem ser excluidas (apenas desativadas)</li>
            </ul>
          </div>
        </div>
      </Panel>

      <OperadoraCartaoPadraoInfo operadora={operadoraPadrao} />

      {operadoras.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {operadoras.map((operadora) => (
            <OperadoraCartaoCard
              key={operadora.id}
              operadora={operadora}
              onEditar={abrirModal}
              onExcluir={excluirOperadora}
            />
          ))}
        </div>
      ) : (
        <OperadoraCartaoEmptyState />
      )}

      <OperadoraCartaoModal
        erro={erro}
        formData={formData}
        modalAberto={modalAberto}
        mostrarToken={mostrarToken}
        onClose={fecharModal}
        onSubmit={salvarOperadora}
        onToggleMostrarToken={() => setMostrarToken((value) => !value)}
        operadoraSelecionada={operadoraSelecionada}
        setErro={setErro}
        setFormData={setFormData}
      />
    </div>
  );
}

export default OperadorasCartao;
