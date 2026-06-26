import ComissaoConfiguredItems from "./ComissaoConfiguredItems";
import ComissaoModalFooter from "./ComissaoModalFooter";
import ComissaoParceiroFields from "./ComissaoParceiroFields";
import ComissaoPendingConfigurations from "./ComissaoPendingConfigurations";
import ComissaoProductTree from "./ComissaoProductTree";
import ComissaoRulesPanel from "./ComissaoRulesPanel";
import ComissaoSelectedItemPanel from "./ComissaoSelectedItemPanel";
import { useComissaoModalController } from "./useComissaoModalController";

export default function ComissaoConfiguracaoModal({
  arvoreProdutos,
  configuracoes,
  funcionarioId,
  loading,
  onClose,
  onSave,
}) {
  const modal = useComissaoModalController({ funcionarioId, configuracoes, onSave });
  const canSaveFooter = Boolean(modal.itemSelecionado || modal.regrasAlteradas);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg w-full max-w-6xl max-h-[90vh] overflow-hidden flex flex-col">
        <div className="p-6 border-b flex justify-between items-center">
          <h2 className="text-2xl font-bold">Configuração de Comissão</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700 text-2xl">
            ×
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          <ComissaoParceiroFields
            dataFechamento={modal.dataFechamento}
            funcionarioId={funcionarioId}
            funcionarioSel={modal.funcionarioSel}
            funcionarios={modal.funcionarios}
            onSaveDataFechamento={modal.salvarDataFechamento}
            setDataFechamento={modal.setDataFechamento}
            setFuncionarioSel={modal.setFuncionarioSel}
          />

          <ComissaoRulesPanel regras={modal.regras} setRegra={modal.setRegra} />

          <div className="grid grid-cols-2 gap-6">
            <div>
              <h3 className="font-semibold mb-3">Seleção de Produtos</h3>
              <ComissaoConfiguredItems
                configuracao={modal.configuracao}
                onRemoveConfig={modal.removerConfiguracaoExistente}
                onSelectItem={modal.selecionarItem}
              />
              <ComissaoProductTree
                arvoreProdutos={arvoreProdutos}
                categoriasExpanded={modal.categoriasExpanded}
                itemJaAdicionado={modal.itemJaAdicionado}
                loading={loading}
                selecionarItem={modal.selecionarItem}
                temConfiguracao={modal.temConfiguracao}
                toggleCategoria={modal.toggleCategoria}
              />
            </div>

            <div>
              <h3 className="font-semibold mb-3">Configuração</h3>
              <ComissaoSelectedItemPanel
                adicionarConfiguracao={modal.adicionarConfiguracao}
                itemSelecionado={modal.itemSelecionado}
                salvarItem={modal.salvarItem}
                setItemSelecionado={modal.setItemSelecionado}
              />
              <ComissaoPendingConfigurations
                configuracoesParaSalvar={modal.configuracoesParaSalvar}
                onRemove={modal.removerConfiguracao}
                onSaveAll={modal.salvarTodasConfiguracoes}
                progressoSalvamento={modal.progressoSalvamento}
                salvando={modal.salvando}
              />
            </div>
          </div>
        </div>

        <ComissaoModalFooter
          canSaveFooter={canSaveFooter}
          itemSelecionado={modal.itemSelecionado}
          onClose={onClose}
          salvarItem={modal.salvarItem}
        />
      </div>
    </div>
  );
}
