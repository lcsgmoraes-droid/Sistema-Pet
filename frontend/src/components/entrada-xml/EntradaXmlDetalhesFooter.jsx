import ActionButton from '../ui/ActionButton';

const RATEIO_OPCOES = [
  { value: 'loja', label: 'Loja' },
  { value: 'online', label: 'Online' },
  { value: 'parcial', label: 'Parcial' },
];

function EntradaXmlDetalhesFooter({
  carregarPreviewProcessamento,
  excluirNota,
  loading,
  notaSelecionada,
  processarNota,
  reverterNota,
  salvarTipoRateio,
  setMostrarDetalhes,
  setNotaSelecionada,
  tipoRateio,
}) {
  if (notaSelecionada.status !== 'pendente') {
    return null;
  }

  const produtosVinculados = notaSelecionada.itens.filter((item) => item.produto_id).length;
  const temProdutosVinculados = produtosVinculados > 0;

  return (
    <div className="sticky bottom-0 space-y-3 border-t bg-white px-6 py-4">
      <div className="rounded border border-gray-200 bg-gray-50 p-3">
        <div className="mb-2 flex items-center justify-between">
          <h4 className="text-sm font-medium text-gray-700">
            Distribuicao (informativo para relatorios)
          </h4>
          <div className="text-xs text-gray-500">
            Estoque unificado - Classificacao apenas para analises
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          {RATEIO_OPCOES.map((opcao) => {
            const ativo = tipoRateio === opcao.value;

            return (
              <ActionButton
                key={opcao.value}
                disabled={loading}
                intent="neutral"
                onClick={() => salvarTipoRateio(notaSelecionada.id, opcao.value)}
                size="xs"
                tone={ativo ? 'solid' : 'soft'}
              >
                {opcao.label}
              </ActionButton>
            );
          })}

          {(notaSelecionada.percentual_online > 0 || notaSelecionada.tipo_rateio) && (
            <div className="ml-auto flex gap-3 text-xs text-gray-600">
              <span>Online: {(notaSelecionada.percentual_online || 0).toFixed(0)}%</span>
              <span>Loja: {(notaSelecionada.percentual_loja || 100).toFixed(0)}%</span>
            </div>
          )}
        </div>

        {tipoRateio === 'parcial' && (
          <div className="mt-2 rounded bg-gray-100 p-2 text-xs text-gray-600">
            Defina a quantidade destinada ao <strong>estoque online</strong> em cada produto acima.
            O sistema calcula automaticamente a % baseado nos valores.
          </div>
        )}
      </div>

      <div className="flex items-center justify-between gap-3">
        <div className="text-sm text-gray-600">
          {produtosVinculados} de {notaSelecionada.itens.length} produtos vinculados
        </div>

        <div className="flex flex-wrap justify-end gap-3">
          {notaSelecionada.entrada_estoque_realizada ? (
            <ActionButton
              disabled={loading}
              intent="warning"
              onClick={() => reverterNota(notaSelecionada.id, notaSelecionada.numero_nota)}
              size="md"
            >
              {loading ? 'Revertendo...' : 'Reverter Entrada'}
            </ActionButton>
          ) : (
            <>
              <ActionButton
                disabled={loading}
                intent="delete"
                onClick={() => excluirNota(notaSelecionada.id, notaSelecionada.numero_nota)}
                size="md"
              >
                Excluir Nota
              </ActionButton>

              {temProdutosVinculados && (
                <>
                  <ActionButton
                    disabled={loading}
                    intent="edit"
                    onClick={() => carregarPreviewProcessamento(notaSelecionada.id)}
                    size="md"
                  >
                    Ajuste de custo
                  </ActionButton>
                  <ActionButton
                    disabled={loading}
                    intent="create"
                    onClick={() => processarNota(notaSelecionada.id)}
                    size="md"
                  >
                    {loading ? 'Processando...' : 'Processar Nota'}
                  </ActionButton>
                </>
              )}
            </>
          )}

          <ActionButton
            intent="neutral"
            onClick={() => {
              setMostrarDetalhes(false);
              setNotaSelecionada(null);
            }}
            size="md"
            tone="soft"
          >
            Fechar
          </ActionButton>
        </div>
      </div>
    </div>
  );
}

export default EntradaXmlDetalhesFooter;
