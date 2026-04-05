function MotivoBadge({ motivo }) {
  const isMesmoCpf = motivo === "mesmo_cpf";

  return (
    <span
      className={`px-2 py-0.5 rounded-full text-xs font-medium ${
        isMesmoCpf
          ? "bg-purple-100 text-purple-700"
          : "bg-blue-100 text-blue-700"
      }`}
    >
      {isMesmoCpf ? "Mesmo CPF" : "Mesmo Telefone"}
    </span>
  );
}

function ClienteCell({ cliente }) {
  return (
    <>
      <p className="font-medium text-gray-900">{cliente.nome}</p>
      {cliente.cpf && <p className="text-xs text-gray-400">CPF: {cliente.cpf}</p>}
      {cliente.telefone && (
        <p className="text-xs text-gray-400">Tel: {cliente.telefone}</p>
      )}
      <p className="text-xs text-gray-300">ID #{cliente.id}</p>
    </>
  );
}

function AcoesCell({ sugestao, confirmandoMerge, onConfirmarMerge }) {
  const chaveAParaB = `${sugestao.cliente_a.id}-${sugestao.cliente_b.id}`;
  const chaveBParaA = `${sugestao.cliente_b.id}-${sugestao.cliente_a.id}`;

  return (
    <div className="flex flex-col gap-1 items-center">
      <button
        onClick={() =>
          onConfirmarMerge(
            sugestao.cliente_a.id,
            sugestao.cliente_b.id,
            sugestao.motivo,
          )
        }
        disabled={confirmandoMerge === chaveAParaB}
        className="px-3 py-1 bg-purple-600 text-white rounded text-xs hover:bg-purple-700 disabled:opacity-50 w-full"
      >
        Unir A para B
      </button>
      <button
        onClick={() =>
          onConfirmarMerge(
            sugestao.cliente_b.id,
            sugestao.cliente_a.id,
            sugestao.motivo,
          )
        }
        disabled={confirmandoMerge === chaveBParaA}
        className="px-3 py-1 bg-gray-200 text-gray-700 rounded text-xs hover:bg-gray-300 disabled:opacity-50 w-full"
      >
        Unir B para A
      </button>
    </div>
  );
}

export default function CampanhasUnificacaoSugestoesTable({
  sugestoes,
  confirmandoMerge,
  onConfirmarMerge,
}) {
  if (sugestoes.length === 0) {
    return null;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 border-b">
          <tr>
            <th className="px-4 py-3 text-left font-medium text-gray-600">
              Motivo
            </th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">
              Cliente A
            </th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">
              Cliente B
            </th>
            <th className="px-4 py-3 text-center font-medium text-gray-600">
              Acao
            </th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {sugestoes.map((sugestao, index) => (
            <tr key={index} className="hover:bg-gray-50">
              <td className="px-4 py-3">
                <MotivoBadge motivo={sugestao.motivo} />
              </td>
              <td className="px-4 py-3">
                <ClienteCell cliente={sugestao.cliente_a} />
              </td>
              <td className="px-4 py-3">
                <ClienteCell cliente={sugestao.cliente_b} />
              </td>
              <td className="px-4 py-3 text-center">
                <AcoesCell
                  sugestao={sugestao}
                  confirmandoMerge={confirmandoMerge}
                  onConfirmarMerge={onConfirmarMerge}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
