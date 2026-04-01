export default function ProdutosNovoFornecedoresTab({
  fornecedores,
  formatarMoeda,
  handleAddFornecedor,
  handleDeleteFornecedor,
  handleEditFornecedor,
  isEdicao,
}) {
  if (!isEdicao) {
    return (
      <div className="text-center py-12 border-2 border-dashed border-gray-300 rounded-lg">
        <p className="text-gray-600">Salve o produto primeiro para vincular fornecedores</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold text-gray-900">Fornecedores do Produto</h3>

        <button
          type="button"
          onClick={handleAddFornecedor}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          + Adicionar Fornecedor
        </button>
      </div>

      {fornecedores.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <p className="text-lg mb-2">🏭 Nenhum fornecedor vinculado</p>
          <p className="text-sm">Clique em "Adicionar Fornecedor" para vincular fornecedores a este produto</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fornecedor</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Código</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Preço Custo</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Prazo (dias)</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Estoque</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Principal</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Ações</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {fornecedores.map((forn) => (
                <tr key={forn.id} className={!forn.ativo ? 'opacity-50' : ''}>
                  <td className="px-4 py-3">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{forn.fornecedor_nome}</p>
                      <p className="text-xs text-gray-500">{forn.fornecedor_cpf_cnpj}</p>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-900">{forn.codigo_fornecedor || '-'}</td>
                  <td className="px-4 py-3 text-sm text-gray-900 text-right">
                    {forn.preco_custo ? formatarMoeda(forn.preco_custo) : '-'}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-900 text-center">{forn.prazo_entrega || '-'}</td>
                  <td className="px-4 py-3 text-sm text-gray-900 text-center">{forn.estoque_fornecedor || '-'}</td>
                  <td className="px-4 py-3 text-center">
                    {forn.e_principal && (
                      <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">Principal</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right space-x-2">
                    <button
                      type="button"
                      onClick={() => handleEditFornecedor(forn)}
                      className="text-blue-600 hover:text-blue-800 text-sm"
                    >
                      Editar
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDeleteFornecedor(forn.id)}
                      className="text-red-600 hover:text-red-800 text-sm"
                    >
                      Excluir
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
