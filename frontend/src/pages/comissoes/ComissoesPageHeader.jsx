export default function ComissoesPageHeader({ destacarComissoes, guiaClasses, onNewCommission }) {
  return (
    <>
      {destacarComissoes && (
        <div className="mb-4 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-amber-900">
          Etapa da introducao guiada: clique em <strong>Nova Comissao</strong> para definir parceiro
          e regras por categoria, subcategoria ou produto.
        </div>
      )}

      <div className="mb-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-800">Cadastro de Comissões</h1>
            <p className="text-gray-600 mt-1">Gerencie as comissões dos parceiros</p>
          </div>
          <button
            onClick={onNewCommission}
            className={`text-white px-4 py-2 rounded-lg flex items-center gap-2 ${
              destacarComissoes
                ? `bg-amber-600 hover:bg-amber-700 ${guiaClasses.action}`
                : "bg-blue-600 hover:bg-blue-700"
            }`}
          >
            <span>+</span>
            Nova Comissão
          </button>
        </div>
      </div>
    </>
  );
}
