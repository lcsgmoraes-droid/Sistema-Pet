import ActionButton from "../ui/ActionButton";

const RATEIO_OPCOES = [
  { value: "loja", label: "Loja" },
  { value: "online", label: "Online" },
  { value: "parcial", label: "Parcial" },
];

function EntradaXmlDetalhesFooter({
  carregarPreviewProcessamento,
  excluirNota,
  loading,
  notaSelecionada,
  reverterNota,
  salvarTipoRateio,
  setMostrarDetalhes,
  setNotaSelecionada,
  tipoRateio,
}) {
  if (notaSelecionada.status !== "pendente") {
    return null;
  }

  const produtosVinculados = notaSelecionada.itens.filter((item) => item.produto_id).length;
  const temProdutosVinculados = produtosVinculados > 0;

  return (
    <div className="shrink-0 space-y-2 border-t border-slate-200 bg-white px-4 py-2 md:px-5">
      <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
        <div className="flex flex-wrap items-center gap-2">
          <h4 className="mr-1 text-xs font-medium text-slate-600">
            Distribuicao (informativo para relatorios)
          </h4>
          {RATEIO_OPCOES.map((opcao) => {
            const ativo = tipoRateio === opcao.value;

            return (
              <ActionButton
                key={opcao.value}
                disabled={loading}
                intent="neutral"
                onClick={() => salvarTipoRateio(notaSelecionada.id, opcao.value)}
                size="xs"
                tone={ativo ? "solid" : "soft"}
              >
                {opcao.label}
              </ActionButton>
            );
          })}

          {(notaSelecionada.percentual_online > 0 || notaSelecionada.tipo_rateio) && (
            <div className="ml-auto flex gap-3 text-[11px] text-slate-500">
              <span>Online: {(notaSelecionada.percentual_online || 0).toFixed(0)}%</span>
              <span>Loja: {(notaSelecionada.percentual_loja || 100).toFixed(0)}%</span>
            </div>
          )}
        </div>

        {tipoRateio === "parcial" && (
          <div className="mt-2 text-[11px] text-slate-500">
            Defina a quantidade destinada ao <strong>estoque online</strong> em cada produto acima.
            O sistema calcula automaticamente a % baseado nos valores.
          </div>
        )}
      </div>

      <div className="flex items-center justify-between gap-3">
        <div className="text-xs text-slate-500">
          {produtosVinculados} de {notaSelecionada.itens.length} produtos vinculados
        </div>

        <div className="flex flex-wrap justify-end gap-2">
          {notaSelecionada.entrada_estoque_realizada ? (
            <ActionButton
              disabled={loading}
              intent="warning"
              onClick={() => reverterNota(notaSelecionada.id, notaSelecionada.numero_nota)}
              size="sm"
            >
              {loading ? "Revertendo..." : "Reverter Entrada"}
            </ActionButton>
          ) : (
            <>
              <ActionButton
                disabled={loading}
                intent="delete"
                onClick={() => excluirNota(notaSelecionada.id, notaSelecionada.numero_nota)}
                size="sm"
              >
                Excluir Nota
              </ActionButton>

              {temProdutosVinculados && (
                <ActionButton
                  disabled={loading}
                  intent="create"
                  onClick={() => carregarPreviewProcessamento(notaSelecionada.id)}
                  size="sm"
                >
                  {loading ? "Carregando revisao..." : "Revisar acoes e processar"}
                </ActionButton>
              )}
            </>
          )}

          <ActionButton
            intent="neutral"
            onClick={() => {
              setMostrarDetalhes(false);
              setNotaSelecionada(null);
            }}
            size="sm"
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
