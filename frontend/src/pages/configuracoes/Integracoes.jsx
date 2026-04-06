import { useState } from "react";
import { FiArrowLeft, FiCreditCard, FiPackage } from "react-icons/fi";
import BlingIntegracao from "./BlingIntegracao";
import StoneIntegracao from "./StoneIntegracao";

export default function Integracoes() {
  const [selecionada, setSelecionada] = useState(null);

  if (selecionada === "stone") {
    return (
      <div>
        <button
          onClick={() => setSelecionada(null)}
          className="mb-4 flex items-center gap-2 font-medium text-blue-600 transition hover:text-blue-700"
        >
          <FiArrowLeft /> Voltar as integracoes
        </button>
        <StoneIntegracao />
      </div>
    );
  }

  if (selecionada === "bling") {
    return (
      <div>
        <button
          onClick={() => setSelecionada(null)}
          className="mb-4 flex items-center gap-2 font-medium text-blue-600 transition hover:text-blue-700"
        >
          <FiArrowLeft /> Voltar as integracoes
        </button>
        <BlingIntegracao />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Integracoes</h1>
        <p className="mt-2 text-gray-600">
          Configure e gerencie as integracoes com servicos externos.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <div
          onClick={() => setSelecionada("stone")}
          className="cursor-pointer rounded-lg border-2 border-blue-100 bg-blue-50 p-6 shadow-sm transition-all hover:scale-105 hover:border-blue-300 hover:bg-blue-100 hover:shadow-md"
        >
          <div className="mb-4 flex items-center gap-3">
            <div className="rounded-lg bg-blue-600 p-3 text-white">
              <FiCreditCard className="h-6 w-6" />
            </div>
            <h3 className="text-xl font-semibold text-gray-900">Stone</h3>
          </div>
          <p className="mb-4 text-gray-700">
            Integracao com a plataforma de pagamentos.
          </p>
          <ul className="space-y-1 text-sm text-gray-600">
            <li>Stone Connect para maquininha e PDV</li>
            <li>Conciliacao financeira automatica</li>
            <li>PIX, debito e credito</li>
          </ul>
          <button className="mt-4 w-full rounded bg-blue-600 px-4 py-2 font-medium text-white transition hover:bg-blue-700">
            Configurar
          </button>
        </div>

        <div
          onClick={() => setSelecionada("bling")}
          className="cursor-pointer rounded-lg border-2 border-green-100 bg-green-50 p-6 shadow-sm transition-all hover:scale-105 hover:border-green-300 hover:bg-green-100 hover:shadow-md"
        >
          <div className="mb-4 flex items-center gap-3">
            <div className="rounded-lg bg-green-600 p-3 text-white">
              <FiPackage className="h-6 w-6" />
            </div>
            <h3 className="text-xl font-semibold text-gray-900">Bling v3</h3>
          </div>
          <p className="mb-4 text-gray-700">
            Integracao com o ERP Bling para sincronizacao de produtos e estoque.
          </p>
          <ul className="space-y-1 text-sm text-gray-600">
            <li>Sincronizacao de estoque</li>
            <li>Importacao de pedidos</li>
            <li>Renovacao automatica de token</li>
          </ul>
          <button className="mt-4 w-full rounded bg-green-600 px-4 py-2 font-medium text-white transition hover:bg-green-700">
            Configurar
          </button>
        </div>
      </div>

      <div className="mt-8 rounded-lg border border-gray-200 bg-gray-50 p-6">
        <h3 className="mb-3 font-semibold text-gray-900">Informacoes</h3>
        <p className="mb-3 text-sm text-gray-700">
          As integracoes funcionam de forma independente. Voce pode usar uma,
          ambas ou nenhuma, de acordo com as necessidades do seu negocio.
        </p>
        <ul className="list-inside list-disc space-y-2 text-sm text-gray-600">
          <li>
            <strong>Stone:</strong> use para pagamentos no PDV.
          </li>
          <li>
            <strong>Bling:</strong> use para sincronizar estoque e pedidos com
            o ERP.
          </li>
        </ul>
      </div>
    </div>
  );
}
