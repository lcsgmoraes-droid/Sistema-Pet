const ModalDecisaoRascunho = ({
  contexto,
  estrategiaMesclaItens,
  setEstrategiaMesclaItens,
  onClose,
  onSelecionar,
}) => {
  const pedidoRascunho = contexto?.pedidoRascunho || {};
  const pedidoNovo = contexto?.pedidoNovo || {};
  const quantidadeItensRascunho = pedidoRascunho?.itens?.length || 0;
  const quantidadeItensPedidoNovo = pedidoNovo?.itens?.length || 0;
  const totalRascunhos = Number(contexto?.totalRascunhos || 1);
  const usandoMesmoRascunho = contexto?.tipo === 'atual';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
      <div className="w-full max-w-3xl rounded-2xl bg-white shadow-2xl">
        <div className="border-b border-gray-200 px-6 py-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">Consolidar rascunho do fornecedor</h2>
              <p className="mt-2 text-sm text-gray-600">
                Já existe um pedido em rascunho para este fornecedor. Escolha como o sistema deve tratar a nova sugestão.
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 hover:text-gray-700"
            >
              Fechar
            </button>
          </div>
        </div>

        <div className="grid gap-4 px-6 py-5 md:grid-cols-3">
          <div className="rounded-xl border border-indigo-200 bg-indigo-50 p-4">
            <div className="text-xs font-semibold uppercase tracking-wide text-indigo-700">Rascunho atual</div>
            <div className="mt-2 text-lg font-bold text-indigo-900">
              {pedidoRascunho?.numero_pedido || 'Rascunho em edição'}
            </div>
            <div className="mt-2 text-sm text-indigo-900">
              {quantidadeItensRascunho} item(ns) já no rascunho.
            </div>
            {totalRascunhos > 1 && (
              <div className="mt-3 text-xs text-indigo-700">
                Há {totalRascunhos} rascunhos deste fornecedor. O sistema vai usar o mais recente.
              </div>
            )}
          </div>

          <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
            <div className="text-xs font-semibold uppercase tracking-wide text-emerald-700">Pedido novo</div>
            <div className="mt-2 text-lg font-bold text-emerald-900">
              {quantidadeItensPedidoNovo} item(ns) montados agora
            </div>
            <div className="mt-2 text-sm text-emerald-900">
              Esses itens podem entrar no mesmo rascunho antes de abrir a sugestão inteligente.
            </div>
          </div>

          <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
            <div className="text-xs font-semibold uppercase tracking-wide text-amber-700">Objetivo</div>
            <div className="mt-2 text-sm text-amber-900">
              Consolidar tudo em um único pedido para o envio ao fornecedor ficar centralizado.
            </div>
          </div>
        </div>

        <div className="border-t border-gray-200 px-6 py-5">
          <div className="mb-5 rounded-xl border border-slate-200 bg-slate-50 p-4">
            <div className="text-sm font-semibold text-slate-900">Quando o mesmo produto já existir no rascunho</div>
            <div className="mt-3 grid gap-3 md:grid-cols-2">
              <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-slate-200 bg-white p-3">
                <input
                  type="radio"
                  name="estrategia-mescla-itens"
                  checked={estrategiaMesclaItens === 'somar'}
                  onChange={() => setEstrategiaMesclaItens('somar')}
                  className="mt-1"
                />
                <span>
                  <span className="block text-sm font-semibold text-slate-900">Somar quantidades</span>
                  <span className="mt-1 block text-sm text-slate-600">
                    Junta o item novo com o item já existente no mesmo pedido.
                  </span>
                </span>
              </label>

              <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-slate-200 bg-white p-3">
                <input
                  type="radio"
                  name="estrategia-mescla-itens"
                  checked={estrategiaMesclaItens === 'maior_quantidade'}
                  onChange={() => setEstrategiaMesclaItens('maior_quantidade')}
                  className="mt-1"
                />
                <span>
                  <span className="block text-sm font-semibold text-slate-900">Manter a maior quantidade</span>
                  <span className="mt-1 block text-sm text-slate-600">
                    Evita duplicidade e preserva a maior quantidade entre o rascunho e a nova entrada.
                  </span>
                </span>
              </label>
            </div>
          </div>

          <div className="grid gap-3 md:grid-cols-3">
            <button
              type="button"
              onClick={() => onSelecionar('mesclar')}
              className="rounded-xl border border-blue-200 bg-blue-50 p-4 text-left transition hover:bg-blue-100"
            >
              <div className="text-base font-semibold text-blue-900">Mesclar</div>
              <div className="mt-2 text-sm text-blue-800">
                Soma o pedido novo com o rascunho existente e depois aplica a sugestão no mesmo pedido.
              </div>
            </button>

            <button
              type="button"
              onClick={() => onSelecionar('substituir')}
              className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-left transition hover:bg-amber-100"
            >
              <div className="text-base font-semibold text-amber-900">Substituir</div>
              <div className="mt-2 text-sm text-amber-800">
                {usandoMesmoRascunho
                  ? 'Troca os itens atuais do rascunho pela nova sugestão selecionada.'
                  : 'Troca o conteúdo do rascunho pelo pedido novo que você está montando agora.'}
              </div>
            </button>

            <button
              type="button"
              onClick={() => onSelecionar('manter')}
              className="rounded-xl border border-gray-200 bg-gray-50 p-4 text-left transition hover:bg-gray-100"
            >
              <div className="text-base font-semibold text-gray-900">Manter rascunho</div>
              <div className="mt-2 text-sm text-gray-700">
                Abre ou mantém o rascunho atual sem aplicar uma nova sugestão agora.
              </div>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ModalDecisaoRascunho;
