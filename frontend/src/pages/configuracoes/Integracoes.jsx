import { useState } from "react";
import { FiArrowLeft, FiCreditCard, FiPackage } from "react-icons/fi";
import StoneIntegracao from "./StoneIntegracao";
import BlingIntegracao from "./BlingIntegracao";

/**
 * Página de menu para escolher qual integração configurar:
 * - Stone (maquininha de pagamento)
 * - Bling (ERP com estoque e pedidos)
 */
export default function Integracoes() {
  const [selecionada, setSelecionada] = useState(null);

  if (selecionada === "stone") {
    return (
      <div>
        <button
          onClick={() => setSelecionada(null)}
          className="mb-4 flex items-center gap-2 text-blue-600 hover:text-blue-700 font-medium transition"
        >
          <FiArrowLeft /> Voltar às integrações
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
          className="mb-4 flex items-center gap-2 text-blue-600 hover:text-blue-700 font-medium transition"
        >
          <FiArrowLeft /> Voltar às integrações
        </button>
        <BlingIntegracao />
      </div>
    );
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Integrações</h1>
        <p className="text-gray-600 mt-2">
          Configure e gerencie as integrações com serviços externos
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Card Stone */}
        <div
          onClick={() => setSelecionada("stone")}
          className="cursor-pointer p-6 rounded-lg border-2 border-blue-100 bg-blue-50 hover:bg-blue-100 hover:border-blue-300 transition-all transform hover:scale-105 shadow-sm hover:shadow-md"
        >
          <div className="flex items-center gap-3 mb-4">
            <div className="p-3 rounded-lg bg-blue-600 text-white">
              <FiCreditCard className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-semibold text-gray-900">Stone</h3>
          </div>
          <p className="text-gray-700 mb-4">
            Integração com a plataforma de pagamentos (Pagar.me).
          </p>
          <ul className="text-sm text-gray-600 space-y-1">
            <li>✓ Stone Connect (maquininha / PDV)</li>
            <li>✓ Conciliação financeira automática</li>
            <li>✓ PIX, débito e crédito</li>
          </ul>
          <button className="mt-4 w-full px-4 py-2 rounded bg-blue-600 text-white font-medium hover:bg-blue-700 transition">
            Configurar
          </button>
        </div>

        {/* Card Bling */}
        <div
          onClick={() => setSelecionada("bling")}
          className="cursor-pointer p-6 rounded-lg border-2 border-green-100 bg-green-50 hover:bg-green-100 hover:border-green-300 transition-all transform hover:scale-105 shadow-sm hover:shadow-md"
        >
          <div className="flex items-center gap-3 mb-4">
            <div className="p-3 rounded-lg bg-green-600 text-white">
              <FiPackage className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-semibold text-gray-900">Bling v3</h3>
          </div>
          <p className="text-gray-700 mb-4">
            Integração com o ERP Bling para sincronização de produtos e estoque.
          </p>
          <ul className="text-sm text-gray-600 space-y-1">
            <li>✓ Sincronização de estoque</li>
            <li>✓ Importação de pedidos</li>
            <li>✓ Renovação automática de token</li>
          </ul>
          <button className="mt-4 w-full px-4 py-2 rounded bg-green-600 text-white font-medium hover:bg-green-700 transition">
            Configurar
          </button>
        </div>
      </div>

      {/* Informações gerais */}
      <div className="mt-8 p-6 bg-gray-50 rounded-lg border border-gray-200">
        <h3 className="font-semibold text-gray-900 mb-3">ℹ️ Informações</h3>
        <p className="text-sm text-gray-700 mb-3">
          As integrações funcionam de forma independente. Você pode usar uma, ambas ou nenhuma,
          de acordo com as necessidades do seu negócio.
        </p>
        <ul className="text-sm text-gray-600 space-y-2 list-disc list-inside">
          <li>
            <strong>Stone:</strong> Use para receber pagamentos por maquininha ou PIX no PDV
          </li>
          <li>
            <strong>Bling:</strong> Use para sincronizar estoque e pedidos com seu ERP Bling
          </li>
        </ul>
      </div>
    </div>
  );
}
