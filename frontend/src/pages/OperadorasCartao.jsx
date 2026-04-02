import { AlertTriangle, Plus } from "lucide-react";
import OperadoraCartaoCard from "../components/operadorasCartao/OperadoraCartaoCard";
import OperadoraCartaoEmptyState from "../components/operadorasCartao/OperadoraCartaoEmptyState";
import OperadoraCartaoModal from "../components/operadorasCartao/OperadoraCartaoModal";
import OperadoraCartaoPadraoInfo from "../components/operadorasCartao/OperadoraCartaoPadraoInfo";
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
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="p-6">
      {destacarOperadoras && (
        <div className="mb-4 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-amber-900">
          Etapa da introducao guiada: comece por <strong>Nova Operadora</strong> e marque uma
          operadora ativa como padrao.
        </div>
      )}

      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Operadoras de Cartao</h1>
        <p className="text-gray-600">
          Configure as operadoras de cartao disponiveis (Stone, Cielo, Rede, Getnet, etc)
        </p>
      </div>

      <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6">
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
      </div>

      <OperadoraCartaoPadraoInfo operadora={operadoraPadrao} />

      <div className="mb-6">
        <button
          onClick={() => abrirModal()}
          className={`text-white px-4 py-2 rounded-lg flex items-center gap-2 transition-colors ${
            destacarOperadoras
              ? `bg-amber-600 hover:bg-amber-700 ${guiaClasses.action}`
              : "bg-blue-600 hover:bg-blue-700"
          }`}
        >
          <Plus className="w-4 h-4" />
          Nova Operadora
        </button>
      </div>

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
