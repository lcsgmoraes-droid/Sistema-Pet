import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { formatMoneyBRL } from '../utils/formatters';

function formatarValorFiscal(valor, casas = 2) {
  return Number(valor || 0).toLocaleString('pt-BR', {
    minimumFractionDigits: casas,
    maximumFractionDigits: casas,
  });
}

function CardFiscal({ nota, item, composicao }) {
  const [expandido, setExpandido] = useState(true);

  if (!composicao) return null;

  const componentes = composicao.componentes_total || {};
  const linhas = [
    { label: 'Produto', valor: componentes.valor_produtos || 0, icon: '📦', color: 'blue' },
    { label: 'Frete', valor: componentes.valor_frete || 0, icon: '🚚', color: 'green', mostrar: componentes.valor_frete > 0 },
    { label: 'Seguro', valor: componentes.valor_seguro || 0, icon: '🛡️', color: 'purple', mostrar: componentes.valor_seguro > 0 },
    { label: 'Outras Despesas', valor: componentes.valor_outras_despesas || 0, icon: '💰', color: 'orange', mostrar: componentes.valor_outras_despesas > 0 },
    { label: 'Desconto', valor: -(componentes.valor_desconto || 0), icon: '📉', color: 'red', mostrar: componentes.valor_desconto > 0 },
    { label: 'ICMS ST', valor: componentes.valor_icms_st || 0, icon: '🏛️', color: 'indigo', mostrar: componentes.valor_icms_st > 0 },
    { label: 'IPI', valor: componentes.valor_ipi || 0, icon: '📋', color: 'amber', mostrar: componentes.valor_ipi > 0 },
  ].filter(l => l.mostrar !== false);

  const colorMap = {
    blue: 'from-blue-50 to-blue-100 border-blue-300',
    green: 'from-green-50 to-green-100 border-green-300',
    red: 'from-red-50 to-red-100 border-red-300',
    purple: 'from-purple-50 to-purple-100 border-purple-300',
    orange: 'from-orange-50 to-orange-100 border-orange-300',
    indigo: 'from-indigo-50 to-indigo-100 border-indigo-300',
    amber: 'from-amber-50 to-amber-100 border-amber-300',
  };

  const textColorMap = {
    blue: 'text-blue-700',
    green: 'text-green-700',
    red: 'text-red-700',
    purple: 'text-purple-700',
    orange: 'text-orange-700',
    indigo: 'text-indigo-700',
    amber: 'text-amber-700',
  };

  return (
    <div className="mt-4 rounded-xl border-2 border-gradient bg-gradient-to-br from-slate-50 to-slate-100 p-4 shadow-sm hover:shadow-md transition-shadow">
      {/* Header com toggle */}
      <div className="flex items-center justify-between cursor-pointer" onClick={() => setExpandido(!expandido)}>
        <div className="flex items-center gap-2">
          <span className="text-xl">📊</span>
          <h4 className="font-semibold text-slate-800">Composição Fiscal do Item</h4>
        </div>
        <span className={`text-lg transition-transform ${expandido ? 'rotate-180' : ''}`}>▼</span>
      </div>

      {expandido && (
        <>
          {/* Grid de componentes */}
          <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4">
            {linhas.map((linha) => {
              const colorGradient = colorMap[linha.color] || 'from-slate-50 to-slate-100';
              const textColor = textColorMap[linha.color] || 'text-slate-700';
              const isNegativo = Number(linha.valor) < 0;

              return (
                <div
                  key={linha.label}
                  className={`bg-gradient-to-br ${colorGradient} border rounded-lg p-3 text-center transition-transform hover:scale-105`}
                >
                  <div className="text-2xl mb-1">{linha.icon}</div>
                  <div className={`text-xs font-medium ${textColor} truncate`}>{linha.label}</div>
                  <div className={`text-sm font-bold mt-1 ${isNegativo ? 'text-red-600' : textColor}`}>
                    {isNegativo ? '- ' : ''}R$ {formatarValorFiscal(Math.abs(Number(linha.valor)), 2)}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Resumo final */}
          <div className="mt-4 border-t-2 border-slate-300 pt-3">
            <div className="flex items-center justify-between bg-gradient-to-r from-emerald-50 to-emerald-100 border-2 border-emerald-300 rounded-lg p-3">
              <div>
                <span className="text-xs text-emerald-700 font-medium block">Custo de Aquisição por Unidade</span>
                <span className="text-xs text-emerald-600 mt-1 block">
                  Qtd: {formatarValorFiscal(composicao.quantidade_efetiva || 1, 0)} un.
                </span>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold text-emerald-700">
                  R$ {formatarValorFiscal(composicao.custo_aquisicao_unitario || 0, 4)}
                </div>
                <div className="text-xs text-emerald-600 mt-1">
                  Total: {formatMoneyBRL(composicao.custo_aquisicao_total || 0)}
                </div>
              </div>
            </div>

            {/* Info de rateio */}
            {composicao.tem_rateio && (
              <div className="mt-2 rounded-lg bg-blue-50 border border-blue-200 p-2 text-xs text-blue-800">
                <span className="inline-block mr-1">ℹ️</span>
                Rateio proporcional aplicado para valores que vieram só no total da nota.
              </div>
            )}

            {/* Tributos informativos */}
            {(componentes.valor_icms > 0 || componentes.valor_pis > 0 || componentes.valor_cofins > 0) && (
              <div className="mt-2 rounded-lg bg-slate-100 border border-slate-300 p-2 text-xs">
                <div className="font-semibold text-slate-700 mb-1">Tributos Informativos (por unidade):</div>
                <div className="flex flex-wrap gap-2">
                  {componentes.valor_icms > 0 && (
                    <span className="bg-white px-2 py-1 rounded text-slate-600">ICMS: R$ {formatarValorFiscal(componentes.valor_icms / (composicao.quantidade_efetiva || 1), 4)}</span>
                  )}
                  {componentes.valor_pis > 0 && (
                    <span className="bg-white px-2 py-1 rounded text-slate-600">PIS: R$ {formatarValorFiscal(componentes.valor_pis / (composicao.quantidade_efetiva || 1), 4)}</span>
                  )}
                  {componentes.valor_cofins > 0 && (
                    <span className="bg-white px-2 py-1 rounded text-slate-600">COFINS: R$ {formatarValorFiscal(componentes.valor_cofins / (composicao.quantidade_efetiva || 1), 4)}</span>
                  )}
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

CardFiscal.propTypes = {
  nota: PropTypes.object,
  item: PropTypes.object,
  composicao: PropTypes.object,
};

export default CardFiscal;
