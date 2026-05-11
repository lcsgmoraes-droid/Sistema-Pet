const formatarMoeda = (valor) =>
  Number(valor || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

const OpcaoRascunho = ({ titulo, descricao, destaque, onClick, intent = 'slate' }) => {
  const estilos = {
    blue: 'border-blue-200 bg-blue-50 text-blue-900 hover:bg-blue-100',
    emerald: 'border-emerald-200 bg-emerald-50 text-emerald-900 hover:bg-emerald-100',
    amber: 'border-amber-200 bg-amber-50 text-amber-900 hover:bg-amber-100',
    slate: 'border-slate-200 bg-white text-slate-900 hover:bg-slate-50',
  };

  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-xl border p-4 text-left shadow-sm transition ${estilos[intent] || estilos.slate}`}
    >
      <div className="text-base font-semibold">{titulo}</div>
      <div className="mt-1 text-sm opacity-80">{descricao}</div>
      {destaque ? <div className="mt-3 text-xs font-semibold uppercase tracking-wide">{destaque}</div> : null}
    </button>
  );
};

const ModalDecisaoRascunho = ({
  contexto,
  onClose,
  onSelecionar,
}) => {
  const pedidoRascunho = contexto?.pedidoRascunho || {};
  const pedidoNovo = contexto?.pedidoNovo || {};
  const quantidadeItensRascunho = pedidoRascunho?.itens?.length || 0;
  const quantidadeItensPedidoNovo = pedidoNovo?.itens?.length || 0;
  const totalRascunhos = Number(contexto?.totalRascunhos || 1);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
      <div className="w-full max-w-2xl rounded-2xl bg-white shadow-2xl">
        <div className="border-b border-gray-200 px-6 py-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-xl font-bold text-gray-900">Ja existe rascunho deste fornecedor</h2>
              <p className="mt-1 text-sm text-gray-600">
                Escolha se quer reaproveitar o rascunho ou iniciar outro pedido para o mesmo fornecedor.
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg px-3 py-2 text-sm font-semibold text-gray-500 hover:bg-gray-100 hover:text-gray-700"
            >
              Fechar
            </button>
          </div>
        </div>

        <div className="grid gap-3 border-b border-gray-100 px-6 py-4 sm:grid-cols-3">
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
            <div className="text-xs font-semibold uppercase text-slate-500">Rascunho</div>
            <div className="mt-1 font-bold text-slate-900">{pedidoRascunho?.numero_pedido || 'Atual'}</div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
            <div className="text-xs font-semibold uppercase text-slate-500">Itens</div>
            <div className="mt-1 font-bold text-slate-900">{quantidadeItensRascunho} no rascunho</div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
            <div className="text-xs font-semibold uppercase text-slate-500">Total</div>
            <div className="mt-1 font-bold text-slate-900">{formatarMoeda(pedidoRascunho?.valor_total)}</div>
          </div>
        </div>

        <div className="space-y-4 px-6 py-5">
          {totalRascunhos > 1 ? (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
              Ha {totalRascunhos} rascunhos deste fornecedor. A tela vai usar o mais recente.
            </div>
          ) : null}

          <div className="grid gap-3 sm:grid-cols-2">
            <OpcaoRascunho
              intent="slate"
              titulo="Carregar rascunho"
              descricao="Abre o pedido anterior exatamente como esta, sem nova sugestao agora."
              destaque={`${quantidadeItensRascunho} item(ns)`}
              onClick={() => onSelecionar('carregar')}
            />
            <OpcaoRascunho
              intent="emerald"
              titulo="Sugerir mantendo quantidades"
              descricao="Roda a analise inteligente e preserva as quantidades ja preenchidas no rascunho."
              destaque="Revisar sem perder edicoes"
              onClick={() => onSelecionar('analisar_preservar')}
            />
            <OpcaoRascunho
              intent="amber"
              titulo="Sugerir e substituir"
              descricao="Roda uma nova analise e, ao confirmar, troca os itens do rascunho pelos selecionados."
              destaque="Recalcular do zero"
              onClick={() => onSelecionar('analisar_substituir')}
            />
            <OpcaoRascunho
              intent="blue"
              titulo="Comecar novo pedido"
              descricao="Mantem o rascunho antigo intacto e abre uma nova sugestao para outro pedido do fornecedor."
              destaque={`${quantidadeItensPedidoNovo} item(ns) no pedido atual`}
              onClick={() => onSelecionar('novo')}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default ModalDecisaoRascunho;
