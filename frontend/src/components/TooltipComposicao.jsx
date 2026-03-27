import React, { useState } from 'react';
import PropTypes from 'prop-types';

function formatarValorFiscal(valor, casas = 2) {
  return Number(valor || 0).toLocaleString('pt-BR', {
    minimumFractionDigits: casas,
    maximumFractionDigits: casas,
  });
}

function TooltipComposicao({ custo, composicao, texto = 'Ver composição' }) {
  const [mostrando, setMostrando] = useState(false);

  if (!composicao?.componentes_unitario) {
    return null;
  }

  const comp = composicao.componentes_unitario;
  const linhas = [
    { label: 'Custo Bruto', valor: composicao.custo_bruto_unitario || 0, icon: '📦' },
    { label: 'Frete', valor: comp.valor_frete || 0, icon: '🚚', mostrar: comp.valor_frete > 0 },
    { label: 'Seguro', valor: comp.valor_seguro || 0, icon: '🛡️', mostrar: comp.valor_seguro > 0 },
    { label: 'Outras Despesas', valor: comp.valor_outras_despesas || 0, icon: '💰', mostrar: comp.valor_outras_despesas > 0 },
    { label: 'ICMS ST', valor: comp.valor_icms_st || 0, icon: '🏛️', mostrar: comp.valor_icms_st > 0 },
    { label: 'IPI', valor: comp.valor_ipi || 0, icon: '📋', mostrar: comp.valor_ipi > 0 },
    { label: 'Desconto', valor: -(comp.valor_desconto || 0), icon: '📉', mostrar: comp.valor_desconto > 0 },
  ].filter(l => l.mostrar !== false);

  return (
    <div className="relative inline-block">
      {/* Botao trigger */}
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setMostrando(!mostrando);
        }}
        className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-blue-100 text-blue-700 hover:bg-blue-200 transition-colors text-xs font-medium cursor-pointer"
        title="Clique para ver a composição detalhada do preço"
      >
        <span>ℹ️</span>
        <span>{texto}</span>
      </button>

      {/* Modal com overlay: clique fora fecha */}
      {mostrando && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center">
          <button
            type="button"
            aria-label="Fechar composição do preço"
            className="absolute inset-0 bg-black/10"
            onClick={() => setMostrando(false)}
          />

          <div className="relative z-[71] w-80 bg-white rounded-xl shadow-2xl border border-slate-200 p-4">
            {/* Cabecalho */}
            <div className="flex items-center justify-between mb-3 pb-2 border-b-2 border-slate-200">
              <h4 className="font-bold text-slate-800 flex items-center gap-2">
                <span className="text-lg" aria-hidden="true">📊</span>
                <span>Composição do Preço</span>
              </h4>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setMostrando(false);
                }}
                className="text-slate-500 hover:text-slate-700 font-bold"
              >
                ✕
              </button>
            </div>

            {/* Componentes */}
            <div className="space-y-2 mb-4 max-h-96 overflow-y-auto">
              {linhas.map((linha) => {
                const isNegativo = Number(linha.valor) < 0;
                const isDestaque = linha.label === 'Custo Bruto' || (composicao.custo_aquisicao_unitario && Math.abs(Number(composicao.custo_aquisicao_unitario) - Number(custo)) < 0.01);
                let valorCor = 'text-slate-700';
                if (isNegativo) {
                  valorCor = 'text-red-600';
                } else if (isDestaque) {
                  valorCor = 'text-emerald-700';
                }

                return (
                  <div
                    key={linha.label}
                    className={`flex items-center justify-between p-2 rounded-lg transition-colors ${
                      isDestaque ? 'bg-emerald-50 border border-emerald-200' : 'bg-slate-50 border border-slate-200'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-lg">{linha.icon}</span>
                      <span className={`text-sm font-medium ${isDestaque ? 'text-emerald-900' : 'text-slate-700'}`}>
                        {linha.label}
                      </span>
                    </div>
                    <span className={`font-bold ${valorCor}`}>
                      {isNegativo ? '- ' : '+ '}R$ {formatarValorFiscal(Math.abs(Number(linha.valor)), 4)}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* Divisor */}
            <div className="border-t-2 border-slate-300 my-2"></div>

            {/* Total */}
            <div className="bg-gradient-to-r from-emerald-100 to-emerald-50 border-2 border-emerald-300 rounded-lg p-3 text-center">
              <div className="text-xs text-emerald-700 font-medium mb-1">Custo de Aquisição (Unitário)</div>
              <div className="text-2xl font-bold text-emerald-700">
                R$ {formatarValorFiscal(composicao.custo_aquisicao_unitario || 0, 4)}
              </div>
            </div>

            {/* Info rateio */}
            {composicao.tem_rateio && (
              <div className="mt-2 text-xs text-blue-700 bg-blue-50 border border-blue-200 rounded-lg p-2">
                <span className="font-semibold">💡 Rateio aplicado:</span> Valores de frete/impostos que vieram so no total foram distribuidos proporcionalmente.
              </div>
            )}

            <div className="absolute top-2 right-10 text-xs text-slate-400">clique fora para fechar</div>
          </div>
        </div>
      )}
    </div>
  );
}

TooltipComposicao.propTypes = {
  custo: PropTypes.number,
  composicao: PropTypes.object,
  texto: PropTypes.string,
};

export default TooltipComposicao;
