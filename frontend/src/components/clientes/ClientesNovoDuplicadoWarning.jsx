import { FiAlertCircle } from "react-icons/fi";

function ClientesNovoDuplicadoWarning({
  clienteDuplicado,
  isDocumentoUnico,
  onContinuarMesmoDuplicado,
  onEditarClienteExistente,
  onIrParaClienteExistente,
}) {
  if (!clienteDuplicado) return null;

  return (
    <div className="mb-4 p-4 bg-yellow-50 border-2 border-yellow-400 rounded-lg">
      <div className="flex items-start gap-3">
        <FiAlertCircle className="text-yellow-600 mt-1" size={24} />
        <div className="flex-1">
          <h4 className="font-semibold text-yellow-900 mb-2">Pessoa ja cadastrada!</h4>
          <p className="text-sm text-yellow-800 mb-3">
            Ja existe uma pessoa com o mesmo <strong>{clienteDuplicado.campo}</strong> cadastrado:
          </p>

          <div className="bg-white rounded-lg p-3 border border-yellow-300 mb-3">
            <p className="font-semibold text-gray-900">{clienteDuplicado.cliente.nome}</p>
            <p className="text-sm text-gray-600">Codigo: {clienteDuplicado.cliente.codigo}</p>
            {clienteDuplicado.cliente.cpf && (
              <p className="text-sm text-gray-600">CPF: {clienteDuplicado.cliente.cpf}</p>
            )}
            {clienteDuplicado.cliente.celular && (
              <p className="text-sm text-gray-600">Celular: {clienteDuplicado.cliente.celular}</p>
            )}
            {clienteDuplicado.cliente.telefone && (
              <p className="text-sm text-gray-600">Telefone: {clienteDuplicado.cliente.telefone}</p>
            )}
          </div>

          {isDocumentoUnico(clienteDuplicado.campo) ? (
            <div>
              <div className="bg-red-50 border border-red-300 rounded-lg p-4 mb-3">
                <p className="text-sm font-semibold text-red-900 mb-2">
                  Nao e possivel criar novo cadastro
                </p>
                <p className="text-sm text-red-800 mb-2">
                  {clienteDuplicado.campo.toUpperCase()} e um documento unico e ja esta cadastrado.
                </p>
                <p className="text-sm text-red-700">
                  Voce pode editar o cadastro existente ou visualiza-lo.
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={onEditarClienteExistente}
                  className="flex-1 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
                >
                  Editar cadastro existente
                </button>
                <button
                  onClick={onIrParaClienteExistente}
                  className="flex-1 px-3 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg text-sm font-medium transition-colors"
                >
                  Ver cadastro
                </button>
              </div>
            </div>
          ) : (
            <div>
              <p className="mb-3 text-xs text-yellow-800">
                Telefone e email podem ser compartilhados por familiares ou equipes. Continuar nao
                altera o cadastro existente.
              </p>
              <div className="flex gap-2">
                <button
                  onClick={onIrParaClienteExistente}
                  className="flex-1 px-3 py-2 bg-yellow-600 hover:bg-yellow-700 text-white rounded-lg text-sm font-medium transition-colors"
                >
                  Ver cadastro existente
                </button>
                <button
                  onClick={onContinuarMesmoDuplicado}
                  className="flex-1 px-3 py-2 bg-orange-500 hover:bg-orange-600 text-white rounded-lg text-sm font-medium transition-colors"
                >
                  Manter {clienteDuplicado.campo} nos dois
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default ClientesNovoDuplicadoWarning;
