import React from 'react';
import { Award, DollarSign, Package, Percent } from 'lucide-react';

const DashboardRacoesResumoCards = ({ resumo }) => {
  if (!resumo) return null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
        <div className="flex items-center justify-between mb-2">
          <Package className="h-5 w-5 text-blue-500" />
          <span className="text-xs text-gray-500">Rações Cadastradas</span>
        </div>
        <div className="text-2xl font-bold text-gray-900">{resumo.total_racoes}</div>
        <div className="text-sm text-gray-600 mt-1">
          {resumo.total_classificadas} classificadas ({resumo.percentual_classificadas}%)
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
        <div className="flex items-center justify-between mb-2">
          <Percent className="h-5 w-5 text-green-500" />
          <span className="text-xs text-gray-500">Margem Média</span>
        </div>
        <div className="text-2xl font-bold text-gray-900">{resumo.margem_media_geral}%</div>
        <div className="text-sm text-gray-600 mt-1">em {resumo.total_racoes} produtos</div>
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
        <div className="flex items-center justify-between mb-2">
          <DollarSign className="h-5 w-5 text-yellow-500" />
          <span className="text-xs text-gray-500">Faturamento Período</span>
        </div>
        <div className="text-2xl font-bold text-gray-900">
          R$ {resumo.faturamento_periodo.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
        </div>
        <div className="text-sm text-gray-600 mt-1">{resumo.marcas_cadastradas} marcas ativas</div>
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
        <div className="flex items-center justify-between mb-2">
          <Award className="h-5 w-5 text-purple-500" />
          <span className="text-xs text-gray-500">Mais Vendido</span>
        </div>
        {resumo.produto_mais_vendido ? (
          <>
            <div className="text-sm font-semibold text-gray-900 truncate">
              {resumo.produto_mais_vendido.nome}
            </div>
            <div className="text-xs text-gray-600 mt-1">
              {resumo.produto_mais_vendido.quantidade} unidades
            </div>
          </>
        ) : (
          <div className="text-sm text-gray-500">Sem dados de vendas</div>
        )}
      </div>
    </div>
  );
};

export default DashboardRacoesResumoCards;
