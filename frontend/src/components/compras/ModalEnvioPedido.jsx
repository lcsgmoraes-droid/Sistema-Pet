import SeletorColunasDocumentoPedido from "./pedidoDocumentoColunas";

// Modal de Envio de Pedido
const ModalEnvioPedido = ({
  onClose,
  onEnviar,
  onEnvioManual,
  emailEnvioDisponivel,
  dadosEnvio,
  setDadosEnvio,
  colunasSelecionadas,
  onChangeColunas,
}) => {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-2xl w-full">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold text-gray-800">📤 Enviar Pedido ao Fornecedor</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <div className="space-y-4">
          {/* Campo E-mail */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              E-mail do Fornecedor
            </label>
            <input
              type="email"
              value={dadosEnvio.email}
              onChange={(e) => setDadosEnvio({ ...dadosEnvio, email: e.target.value })}
              placeholder="fornecedor@exemplo.com"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Campo WhatsApp */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              WhatsApp (futuro)
              <span className="ml-2 text-xs text-gray-500">(Em breve)</span>
            </label>
            <input
              type="tel"
              value={dadosEnvio.whatsapp}
              onChange={(e) => setDadosEnvio({ ...dadosEnvio, whatsapp: e.target.value })}
              placeholder="(00) 00000-0000"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg bg-gray-50"
              disabled
            />
          </div>

          {/* Seleção de Formatos */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Formatos para Envio
            </label>
            <div className="space-y-2">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={dadosEnvio.formatos.pdf}
                  onChange={(e) =>
                    setDadosEnvio({
                      ...dadosEnvio,
                      formatos: { ...dadosEnvio.formatos, pdf: e.target.checked },
                    })
                  }
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="ml-2 text-sm">📄 PDF</span>
              </label>
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={dadosEnvio.formatos.excel}
                  onChange={(e) =>
                    setDadosEnvio({
                      ...dadosEnvio,
                      formatos: { ...dadosEnvio.formatos, excel: e.target.checked },
                    })
                  }
                  className="rounded border-gray-300 text-green-600 focus:ring-green-500"
                />
                <span className="ml-2 text-sm">📊 Excel</span>
              </label>
            </div>
          </div>

          <SeletorColunasDocumentoPedido
            colunasSelecionadas={colunasSelecionadas}
            onChange={onChangeColunas}
            titulo="Conteudo do PDF / Excel"
            descricao="Use este ajuste quando quiser ocultar custos do fornecedor e enviar apenas codigo, descricao e quantidade."
          />

          {emailEnvioDisponivel === false && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
              O servidor ainda não está configurado para enviar e-mails automaticamente. Você pode
              marcar este pedido como enviado manualmente por enquanto.
            </div>
          )}

          {/* Botões de Ação */}
          <div className="flex flex-col gap-3 pt-4">
            <button
              onClick={onEnviar}
              disabled={!emailEnvioDisponivel}
              className="w-full border border-blue-200 bg-blue-50 text-blue-700 py-3 rounded-lg font-semibold hover:bg-blue-100 transition-colors disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-100 disabled:text-slate-400"
            >
              📧 Enviar por E-mail
            </button>

            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-300"></div>
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-2 bg-white text-gray-500">ou</span>
              </div>
            </div>

            <button
              onClick={onEnvioManual}
              className="w-full border border-slate-200 bg-slate-50 text-slate-700 py-3 rounded-lg font-semibold hover:bg-slate-100 transition-colors"
            >
              ✅ Já enviei manualmente
            </button>

            <button
              onClick={onClose}
              className="w-full border border-gray-300 text-gray-700 py-2 rounded-lg font-semibold hover:bg-gray-50"
            >
              ❌ Cancelar
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ModalEnvioPedido;
