export default function ProdutosNovoTabs({ abaAtiva, onChangeAba, tipoProduto, tipoKit }) {
  const abas = [
    { id: 1, label: 'Características' },
    { id: 2, label: 'Imagens' },
    { id: 3, label: 'Estoque/Lotes' },
    { id: 4, label: 'Fornecedores' },
    { id: 5, label: 'Tributação' },
    { id: 6, label: '🔄 Recorrência' },
    { id: 7, label: '🥫 Ração' },
    ...(tipoProduto === 'PAI' ? [{ id: 8, label: '📦 Variações' }] : []),
    ...(tipoProduto === 'KIT' || (tipoProduto === 'VARIACAO' && tipoKit)
      ? [{ id: 9, label: '🧩 Composição' }]
      : []),
  ];

  return (
    <div className="mb-6 border-b border-gray-200">
      <nav className="flex gap-8">
        {abas.map((aba) => (
          <button
            key={aba.id}
            onClick={() => onChangeAba(aba.id)}
            className={`pb-4 px-1 border-b-2 font-medium text-sm transition-colors ${
              abaAtiva === aba.id
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            {aba.label}
          </button>
        ))}
      </nav>
    </div>
  );
}
