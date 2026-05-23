import { useEffect, useRef, useState } from 'react';
import PropTypes from 'prop-types';
import { AlertTriangle, FileText, Upload, X } from 'lucide-react';
import ActionButton from '../ui/ActionButton';
import IconActionButton from '../ui/IconActionButton';
import FornecedorSelector, { getFornecedorNome } from '../fornecedores/FornecedorSelector';

export default function EntradaPdfUploadModal({
  aberto,
  loading,
  onClose,
  onImportar,
}) {
  const [arquivo, setArquivo] = useState(null);
  const [erro, setErro] = useState('');
  const [fornecedorSelecionado, setFornecedorSelecionado] = useState(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (!aberto) {
      setArquivo(null);
      setErro('');
      setFornecedorSelecionado(null);
      if (inputRef.current) {
        inputRef.current.value = '';
      }
    }
  }, [aberto]);

  if (!aberto) return null;

  const handleArquivoChange = (event) => {
    const file = event.target.files?.[0] || null;
    setErro('');
    if (file && !file.name.toLowerCase().endsWith('.pdf')) {
      setArquivo(null);
      setErro('Selecione um arquivo PDF.');
      return;
    }
    setArquivo(file);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setErro('');

    if (!fornecedorSelecionado?.id) {
      setErro('Selecione o fornecedor antes de importar.');
      return;
    }

    if (!arquivo) {
      setErro('Selecione o arquivo PDF do pedido.');
      return;
    }

    try {
      await onImportar({
        file: arquivo,
        fornecedorId: fornecedorSelecionado.id,
      });
      onClose();
    } catch {
      // O hook ja mostra a mensagem do backend.
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <form
        onSubmit={handleSubmit}
        className="flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-lg bg-white shadow-xl"
      >
        <div className="flex items-center justify-between border-b px-6 py-4">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-red-50 text-red-700">
              <FileText className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <h2 className="text-xl font-bold text-slate-900">Importar pedido em PDF</h2>
              <p className="text-sm text-slate-500">Entrada de produtos a partir de pedido ou romaneio.</p>
            </div>
          </div>
          <IconActionButton
            aria-label="Fechar importacao por PDF"
            icon={X}
            intent="neutral"
            onClick={onClose}
            size="md"
            tone="ghost"
          />
        </div>

        <div className="space-y-5 overflow-y-auto px-6 py-5">
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
            <div className="mb-2 flex items-center gap-2 font-semibold">
              <AlertTriangle className="h-4 w-4" />
              O PDF nao substitui a NF-e
            </div>
            <p>
              O sistema importa itens, quantidades, valores e parcelas quando existirem. Chave fiscal,
              CFOP, NCM, impostos, lotes e validacao SEFAZ nao vem automaticamente pelo PDF.
            </p>
          </div>

          <FornecedorSelector
            fornecedorId={fornecedorSelecionado?.id}
            fornecedorSelecionado={fornecedorSelecionado}
            label="Fornecedor do pedido"
            onClear={() => setFornecedorSelecionado(null)}
            onFornecedorCriado={setFornecedorSelecionado}
            onSelect={setFornecedorSelecionado}
            placeholder="Busque o fornecedor cadastrado..."
            required
          />

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">
              Arquivo PDF <span className="text-red-600">*</span>
            </label>
            <input
              ref={inputRef}
              type="file"
              accept=".pdf,application/pdf"
              onChange={handleArquivoChange}
              className="hidden"
            />
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              className="flex min-h-[88px] w-full items-center justify-between gap-4 rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 py-3 text-left transition hover:border-blue-400 hover:bg-blue-50"
            >
              <div className="flex min-w-0 items-center gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-white text-blue-700 shadow-sm">
                  <Upload className="h-5 w-5" />
                </div>
                <div className="min-w-0">
                  <div className="truncate text-sm font-semibold text-slate-900">
                    {arquivo ? arquivo.name : 'Selecionar PDF'}
                  </div>
                  <div className="text-xs text-slate-500">
                    {arquivo ? `${(arquivo.size / 1024).toFixed(1)} KB` : 'Pedido digital enviado pelo fornecedor'}
                  </div>
                </div>
              </div>
              <span className="shrink-0 rounded-md bg-white px-3 py-1 text-xs font-semibold text-blue-700 shadow-sm">
                PDF
              </span>
            </button>
          </div>

          {fornecedorSelecionado ? (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
              Fornecedor selecionado: <strong>{getFornecedorNome(fornecedorSelecionado)}</strong>
            </div>
          ) : null}

          {erro ? (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {erro}
            </div>
          ) : null}
        </div>

        <div className="flex justify-end gap-3 border-t bg-white px-6 py-4">
          <ActionButton
            type="button"
            intent="neutral"
            tone="soft"
            onClick={onClose}
            disabled={loading}
          >
            Cancelar
          </ActionButton>
          <ActionButton
            type="submit"
            icon={Upload}
            intent="pdf"
            loading={loading}
          >
            Importar PDF
          </ActionButton>
        </div>
      </form>
    </div>
  );
}

EntradaPdfUploadModal.propTypes = {
  aberto: PropTypes.bool.isRequired,
  loading: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  onImportar: PropTypes.func.isRequired,
};
